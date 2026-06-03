from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    APP_NAME: str = "M10 ИГИС-БДД API"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/m10"
    DATA_RAW_PATH: str = "data/raw/moskva_full.geojson"
    DATA_PROCESSED_PATH: str = "data/processed/moscow_3y.parquet"
    REPORTS_DIR: str = "storage/reports"
    REPORTS_INDEX_PATH: str = "app/reports/index.json"
    ALERTS_STATE_PATH: str = "app/reports/alerts_state.json"
    TARGET_REGION: str = "Москва"
    MONTHS_LOOKBACK: int = 24                # visible range in months
    HIDDEN_BASELINE_MONTHS: int = 12         # extra months loaded as trailing-baseline pool only
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://localhost:3001",
    ]


settings = Settings()
