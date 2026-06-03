"use client"

import { cn } from "@/lib/utils"
import type { HotspotItem } from "@/lib/api"

interface HotspotsTableProps {
  hotspots: HotspotItem[]
  periodLabel?: string
  loading?: boolean
  error?: string | null
  onRowClick?: (hotspot: HotspotItem) => void
}

export function HotspotsTable({
  hotspots,
  periodLabel = "",
  loading = false,
  error = null,
  onRowClick,
}: HotspotsTableProps) {
  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h3 className="text-sm font-semibold text-foreground">Топ-5 очагов аварийности</h3>
        {periodLabel && (
          <span className="text-xs text-muted-foreground">{periodLabel}</span>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-muted/30">
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Наименование участка
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-muted-foreground">
                ДТП
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-muted-foreground">
                К. тяжести
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-muted-foreground">
                ДТП/мес
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Статус
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {loading && (
              <tr>
                <td className="px-4 py-3 text-sm text-muted-foreground" colSpan={5}>
                  Загрузка данных...
                </td>
              </tr>
            )}
            {!loading && error && (
              <tr>
                <td className="px-4 py-3 text-sm text-status-critical" colSpan={5}>
                  {error}
                </td>
              </tr>
            )}
            {!loading && !error && hotspots.length === 0 && (
              <tr>
                <td className="px-4 py-3 text-sm text-muted-foreground" colSpan={5}>
                  Нет данных за выбранный период
                </td>
              </tr>
            )}
            {!loading && !error && hotspots.map((hotspot) => (
              <tr
                key={`${hotspot.rank}-${hotspot.name}`}
                onClick={() => onRowClick?.(hotspot)}
                className="cursor-pointer transition-colors hover:bg-muted/20"
                title="Кликните чтобы центрировать карту на очаге"
              >
                <td className="px-4 py-3 text-sm font-medium text-foreground">
                  {hotspot.name}
                </td>
                <td className="px-4 py-3 text-right text-sm tabular-nums text-foreground">
                  {hotspot.accidents_count}
                </td>
                <td className="px-4 py-3 text-right text-sm tabular-nums text-foreground">
                  {hotspot.severity_coef.toFixed(1)}
                </td>
                <td className="px-4 py-3 text-right text-sm tabular-nums text-foreground">
                  {hotspot.frequency.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-center">
                  <span
                    className={cn(
                      "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
                      hotspot.status === "active"
                        ? "bg-status-critical/20 text-status-critical"
                        : "bg-status-warning/20 text-status-warning"
                    )}
                  >
                    {hotspot.status === "active" ? "Активен" : "Потенциальный"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
