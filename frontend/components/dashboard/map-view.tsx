"use client"

import dynamic from "next/dynamic"
import { useEffect, useState } from "react"
import { Layers, MapPin, Maximize2, Minimize2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  fetchHeatmap,
  type HeatmapPoint,
  type HotspotItem,
  type ReportPeriodicity,
} from "@/lib/api"
import { cn } from "@/lib/utils"

const DynamicMap = dynamic(() => import("./interactive-map").then((mod) => mod.InteractiveMap), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center bg-[oklch(0.15_0.01_260)] text-muted-foreground">
      Загрузка карты...
    </div>
  ),
})

const MOSCOW_CENTER: [number, number] = [55.7558, 37.6173]
const MOSCOW_ZOOM = 11

interface MapViewProps {
  period?: string
  periodicity?: ReportPeriodicity
  hotspots?: HotspotItem[]
  hotspotsPeriodLabel?: string
  flyTo?: { lat: number; lon: number; zoom?: number; key: string } | null
}

export function MapView({
  period,
  periodicity = "month",
  hotspots = [],
  hotspotsPeriodLabel = "",
  flyTo = null,
}: MapViewProps) {
  const [points, setPoints] = useState<HeatmapPoint[]>([])
  const [periodLabel, setPeriodLabel] = useState<string>("")
  const [total, setTotal] = useState(0)
  const [showHeat, setShowHeat] = useState(true)
  const [showMarkers, setShowMarkers] = useState(true)        // оба слоя ON по умолчанию
  const [fullscreen, setFullscreen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await fetchHeatmap({ period, periodicity })
        if (cancelled) return
        setPoints(data.points)
        setTotal(data.total)
        setPeriodLabel(data.period_label)
      } catch (err) {
        if (cancelled) return
        const message = err instanceof Error ? err.message : "Не удалось загрузить точки ДТП"
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

  // ESC выходит из fullscreen
  useEffect(() => {
    if (!fullscreen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setFullscreen(false)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [fullscreen])

  return (
    <div
      className={cn(
        "flex flex-col rounded-lg border border-border bg-card",
        fullscreen ? "fixed inset-0 z-[2000] rounded-none" : "h-full"
      )}
    >
      <div className="flex items-center justify-between border-b border-border p-3">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-foreground">Карта ДТП</h3>
          {periodLabel && (
            <span className="text-xs text-muted-foreground">
              {periodLabel} ·{" "}
              {points.length < total
                ? `${points.length} из ${total} (выборка)`
                : `${total} ДТП`}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={showHeat ? "default" : "outline"}
            size="sm"
            onClick={() => setShowHeat((v) => !v)}
            className="h-8 text-xs"
          >
            <Layers className="mr-1.5 h-3.5 w-3.5" />
            Тепловая карта
          </Button>
          <Button
            variant={showMarkers ? "default" : "outline"}
            size="sm"
            onClick={() => setShowMarkers((v) => !v)}
            className="h-8 text-xs"
          >
            <MapPin className="mr-1.5 h-3.5 w-3.5" />
            Точки
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => setFullscreen((v) => !v)}
            className="h-8 w-8"
            aria-label={fullscreen ? "Свернуть карту" : "Развернуть карту"}
            title={fullscreen ? "Свернуть (Esc)" : "На весь экран"}
          >
            {fullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      <div className="relative flex-1 overflow-hidden">
        {error ? (
          <div className="flex h-full items-center justify-center px-4 text-center text-xs text-status-critical">
            {error}
          </div>
        ) : (
          <>
            <DynamicMap
              center={MOSCOW_CENTER}
              zoom={MOSCOW_ZOOM}
              points={points}
              showMarkers={showMarkers}
              showHeat={showHeat}
              hotspots={hotspots}
              hotspotsPeriodLabel={hotspotsPeriodLabel}
              flyTo={flyTo}
              fullscreen={fullscreen}
            />
            {!loading && total === 0 && (
              <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
                <div className="rounded-lg border border-border bg-card/90 px-4 py-3 text-sm text-muted-foreground">
                  Нет ДТП за выбранный период
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {!loading && points.length > 0 && (
        <div className="flex flex-wrap items-center gap-3 border-t border-border px-3 py-2 text-xs text-muted-foreground">
          {showMarkers && (
            <>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: "#ef4444" }} />
                С погибшими
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: "#f97316" }} />
                Тяжёлые (≥3 раненых)
              </span>
              <span className="flex items-center gap-1.5">
                <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: "#3b82f6" }} />
                Лёгкие
              </span>
            </>
          )}
          {showHeat && !showMarkers && (
            <span>Цвет: концентрация ДТП (синий — низкая, красный — высокая)</span>
          )}
        </div>
      )}
    </div>
  )
}
