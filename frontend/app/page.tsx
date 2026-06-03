"use client"

import { useEffect, useState } from "react"
import { DashboardLayout } from "@/components/dashboard/dashboard-layout"
import { FiltersPanel, type Periodicity } from "@/components/dashboard/filters-panel"
import { KpiCard } from "@/components/dashboard/kpi-card"
import { MapView } from "@/components/dashboard/map-view"
import { TrendChart } from "@/components/dashboard/trend-chart"
import { HotspotsTable } from "@/components/dashboard/hotspots-table"
import {
  fetchHotspots,
  fetchIndicators,
  fetchMeta,
  type HotspotItem,
  type IndicatorsResponse,
  type MetaResponse,
} from "@/lib/api"
import type { KpiStatus } from "@/components/dashboard/kpi-card"

function formatValue(v: number, unit?: string): string {
  if (unit === "шт." || unit === "чел.") {
    return Math.round(v).toString()
  }
  return Number(v.toFixed(2)).toString()
}

function calculateStatus(isImprovement: boolean | null, deltaPct: number | null): KpiStatus {
  if (isImprovement === true) return "success"
  if (deltaPct !== null && Math.abs(deltaPct) < 5) return "warning"
  return "critical"
}

interface FlyTo {
  lat: number
  lon: number
  zoom?: number
  key: string
}

export default function IndicatorsPage() {
  const [meta, setMeta] = useState<MetaResponse | null>(null)
  const [period, setPeriod] = useState<string>("")
  const [periodicity, setPeriodicity] = useState<Periodicity>("month")
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<IndicatorsResponse | null>(null)
  const [hotspots, setHotspots] = useState<HotspotItem[]>([])
  const [hotspotsPeriodLabel, setHotspotsPeriodLabel] = useState("")
  const [hotspotsLoading, setHotspotsLoading] = useState(true)
  const [hotspotsError, setHotspotsError] = useState<string | null>(null)
  const [flyTo, setFlyTo] = useState<FlyTo | null>(null)

  useEffect(() => {
    let cancelled = false
    const init = async () => {
      try {
        const m = await fetchMeta()
        if (cancelled) return
        setMeta(m)
        const last = m.available_periods[m.available_periods.length - 1]
        if (last) setPeriod(last)
      } catch (err) {
        if (cancelled) return
        const message = err instanceof Error ? err.message : "Не удалось загрузить метаданные"
        setError(message)
      }
    }
    init()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        setLoading(true)
        setError(null)
        const indicators = period
          ? await fetchIndicators({ period, periodicity })
          : await fetchIndicators()
        if (cancelled) return
        setData(indicators)
      } catch (err) {
        if (cancelled) return
        const message = err instanceof Error ? err.message : "Failed to load indicators"
        setError(message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [period, periodicity])

  // Hotspots — общий источник для карты и таблицы.
  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        setHotspotsLoading(true)
        setHotspotsError(null)
        const data = await fetchHotspots({
          limit: 5,
          period: period || undefined,
          periodicity,
        })
        if (cancelled) return
        setHotspots(data.hotspots)
        setHotspotsPeriodLabel(data.period_label)
      } catch (err) {
        if (cancelled) return
        const message = err instanceof Error ? err.message : "Не удалось загрузить очаги"
        setHotspotsError(message)
      } finally {
        if (!cancelled) setHotspotsLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [period, periodicity])

  const handleHotspotClick = (h: HotspotItem) => {
    // key включает Date.now() чтобы повторный клик по той же строке снова
    // триггерил flyTo (иначе useEffect в карте не сработает).
    setFlyTo({ lat: h.lat, lon: h.lon, zoom: 15, key: `${h.rank}-${Date.now()}` })
  }

  return (
    <DashboardLayout unreadAlertsCount={0}>
      <div className="flex flex-col gap-6 p-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Показатели</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Оперативный мониторинг состояния безопасности дорожного движения
          </p>
        </div>

        {error && (
          <div className="rounded-lg border border-status-critical/30 bg-status-critical/10 p-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-foreground">Ошибка загрузки</h3>
                <p className="mt-1 text-sm text-muted-foreground">{error}</p>
              </div>
              <button
                onClick={() => window.location.reload()}
                className="rounded px-3 py-2 text-sm font-medium text-status-critical hover:bg-status-critical/20"
              >
                Повторить
              </button>
            </div>
          </div>
        )}

        <FiltersPanel
          availablePeriods={meta?.available_periods ?? []}
          period={period}
          periodicity={periodicity}
          onPeriodChange={setPeriod}
          onPeriodicityChange={setPeriodicity}
        />

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {loading
            ? Array.from({ length: 4 }).map((_, i) => (
                <div
                  key={i}
                  className="rounded-lg border border-border bg-card p-4 animate-pulse"
                >
                  <div className="h-4 w-24 rounded bg-muted" />
                  <div className="mt-4 h-8 w-32 rounded bg-muted" />
                </div>
              ))
            : data?.cards.map((card) => (
                <KpiCard
                  key={card.code}
                  title={card.label}
                  value={formatValue(card.value, card.unit)}
                  unit={card.unit || undefined}
                  change={card.delta_pct ?? undefined}
                  baseline={card.delta_abs !== null ? card.value - card.delta_abs : undefined}
                  status={calculateStatus(card.is_improvement, card.delta_pct)}
                />
              ))}
        </div>

        <div className="grid h-[450px] grid-cols-1 gap-6 lg:grid-cols-5">
          <div className="lg:col-span-3">
            <MapView
              period={period || undefined}
              periodicity={periodicity}
              hotspots={hotspots}
              hotspotsPeriodLabel={hotspotsPeriodLabel}
              flyTo={flyTo}
            />
          </div>
          <div className="lg:col-span-2">
            <TrendChart />
          </div>
        </div>

        <HotspotsTable
          hotspots={hotspots}
          periodLabel={hotspotsPeriodLabel}
          loading={hotspotsLoading}
          error={hotspotsError}
          onRowClick={handleHotspotClick}
        />
      </div>
    </DashboardLayout>
  )
}
