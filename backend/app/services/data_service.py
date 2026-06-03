import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
from typing import Optional

import ijson
import pandas as pd
from dateutil import parser as date_parser

from app.config.settings import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DataService:
    """Singleton service for loading and managing crash data."""

    _instance: Optional["DataService"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.df = None
            cls._instance.loaded_at = None
        return cls._instance

    def load(self) -> None:
        """Load data from cache or process raw GeoJSON."""
        if os.path.exists(settings.DATA_PROCESSED_PATH):
            try:
                self.df = pd.read_parquet(settings.DATA_PROCESSED_PATH)
                self._crop_to_complete_window()
                self.loaded_at = datetime.now()
                logger.info(
                    f"Loaded from cache: {len(self.df)} rows from {settings.DATA_PROCESSED_PATH}"
                )
                return
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}. Processing raw data...")

        # Process raw GeoJSON
        self._process_raw_geojson()
        self._crop_to_complete_window()

    def _crop_to_complete_window(self) -> None:
        """Crop df to (MONTHS_LOOKBACK + HIDDEN_BASELINE_MONTHS) months ending
        at the latest complete calendar year.

        Rationale: year-periodicity reports / charts need full Jan–Dec spans,
        so we drop the "tail of the next year" (e.g. partial Jan 2026) entirely.
        - If max_dt is in December (with day>=28) → that year is complete, keep it.
        - Otherwise → end at January 1 of max_dt's year (drop that partial year).
        - Start = end − total_months.
        """
        if self.df is None or self.df.empty:
            return
        target_total = settings.MONTHS_LOOKBACK + settings.HIDDEN_BASELINE_MONTHS

        max_dt = self.df["datetime"].max()
        if max_dt.month == 12 and max_dt.day >= 28:
            window_end = pd.Timestamp(year=max_dt.year + 1, month=1, day=1)
        else:
            window_end = pd.Timestamp(year=max_dt.year, month=1, day=1)
        window_start = window_end - relativedelta(months=target_total)

        before = len(self.df)
        self.df = self.df[
            (self.df["datetime"] >= window_start) & (self.df["datetime"] < window_end)
        ].reset_index(drop=True)
        logger.info(
            f"Cropped to [{window_start.date()}, {window_end.date()}): "
            f"{before} -> {len(self.df)} rows"
        )

    def _process_raw_geojson(self) -> None:
        """Stream and process raw GeoJSON file."""
        records = []
        skipped = 0
        now = datetime.now()
        # Loaded range = visible range + hidden baseline pool + grace buffer
        # (so we have enough data after cropping to the latest complete month).
        total_lookback = settings.MONTHS_LOOKBACK + settings.HIDDEN_BASELINE_MONTHS + 6
        cutoff_date = now - relativedelta(months=total_lookback)

        logger.info(f"Processing raw GeoJSON: {settings.DATA_RAW_PATH}")

        try:
            with open(settings.DATA_RAW_PATH, "rb") as f:
                for feature in ijson.items(f, "features.item"):
                    try:
                        props = feature.get("properties", {})
                        geom = feature.get("geometry", {})

                        # Filter by parent region
                        parent_region = props.get("parent_region", "")
                        if parent_region != settings.TARGET_REGION:
                            skipped += 1
                            continue

                        # Parse datetime
                        dt_str = props.get("datetime")
                        if not dt_str:
                            skipped += 1
                            continue

                        try:
                            crash_datetime = date_parser.parse(str(dt_str))
                        except Exception:
                            skipped += 1
                            continue

                        # Filter by date range
                        if crash_datetime < cutoff_date:
                            skipped += 1
                            continue

                        # Extract coordinates
                        coords = geom.get("coordinates", [])
                        if len(coords) < 2:
                            skipped += 1
                            continue

                        lon = float(coords[0])
                        lat = float(coords[1])

                        # Extract counts
                        dead_count = int(props.get("dead_count") or 0)
                        injured_count = int(props.get("injured_count") or 0)

                        # Determine severity
                        severity_raw = props.get("severity", "")
                        if dead_count > 0:
                            severity = "fatal"
                        elif injured_count >= 3:
                            severity = "serious"
                        else:
                            severity = "minor"

                        # Build record
                        record = {
                            "crash_id": props.get("id"),
                            "datetime": crash_datetime,
                            "year": crash_datetime.year,
                            "month": crash_datetime.month,
                            "year_month": crash_datetime.strftime("%Y-%m"),
                            "lat": lat,
                            "lon": lon,
                            "dead_count": dead_count,
                            "injured_count": injured_count,
                            "severity": severity,
                            "severity_raw": severity_raw,
                            "district": props.get("region"),
                            "crash_type": props.get("category", "unknown"),
                            "road_condition": (
                                props.get("road_conditions")[0]
                                if props.get("road_conditions")
                                else None
                            ),
                            "address": props.get("address"),
                        }

                        records.append(record)

                    except Exception as e:
                        logger.debug(f"Skipped feature: {e}")
                        skipped += 1
                        continue

        except FileNotFoundError:
            logger.error(f"GeoJSON file not found: {settings.DATA_RAW_PATH}")
            raise

        # Create DataFrame
        if not records:
            logger.error("No valid records extracted from GeoJSON")
            self.df = pd.DataFrame()
            return

        self.df = pd.DataFrame(records)
        self.loaded_at = datetime.now()

        logger.info(
            f"Filtered: {len(records)} features (Moscow, last {total_lookback} months = {settings.MONTHS_LOOKBACK} visible + {settings.HIDDEN_BASELINE_MONTHS} hidden baseline), skipped {skipped}"
        )

        # Save to cache
        os.makedirs(os.path.dirname(settings.DATA_PROCESSED_PATH), exist_ok=True)
        self.df.to_parquet(
            settings.DATA_PROCESSED_PATH, engine="pyarrow", compression="snappy"
        )
        logger.info(f"Saved cache to {settings.DATA_PROCESSED_PATH}")

    def get_df(self) -> pd.DataFrame:
        """Return the loaded DataFrame."""
        return self.df if self.df is not None else pd.DataFrame()

    def get_meta(self) -> dict:
        """Return metadata about loaded data."""
        if self.df is None or len(self.df) == 0:
            return {
                "region": settings.TARGET_REGION,
                "total_records": 0,
                "date_range": {"from": None, "to": None},
                "last_updated": None,
                "months_available": 0,
            }

        date_min = self.df["datetime"].min()
        date_max = self.df["datetime"].max()
        months_available = len(self.df["year_month"].unique())

        return {
            "region": settings.TARGET_REGION,
            "total_records": len(self.df),
            "date_range": {
                "from": date_min.strftime("%Y-%m-%d"),
                "to": date_max.strftime("%Y-%m-%d"),
            },
            "last_updated": self.loaded_at.isoformat() if self.loaded_at else None,
            "months_available": months_available,
        }


data_service = DataService()
