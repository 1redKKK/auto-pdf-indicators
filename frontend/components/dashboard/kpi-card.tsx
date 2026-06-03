"use client"

import { ArrowUp, ArrowDown } from "lucide-react"
import { cn } from "@/lib/utils"

export type KpiStatus = "success" | "warning" | "critical"

interface KpiCardProps {
  title: string
  value: string | number
  unit?: string
  change?: number
  baseline?: number          // raw baseline value used for % calculation
  status?: KpiStatus
}

export function KpiCard({ title, value, unit, change, baseline, status = "success" }: KpiCardProps) {
  const statusColors: Record<KpiStatus, string> = {
    success: "bg-status-success/10 border-status-success/30",
    warning: "bg-status-warning/10 border-status-warning/30",
    critical: "bg-status-critical/10 border-status-critical/30",
  }

  const statusDot: Record<KpiStatus, string> = {
    success: "bg-status-success",
    warning: "bg-status-warning",
    critical: "bg-status-critical",
  }

  return (
    <div
      className={cn(
        "rounded-lg border p-4 transition-colors",
        statusColors[status]
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-muted-foreground">{title}</span>
        <span className={cn("h-2 w-2 rounded-full", statusDot[status])} />
      </div>
      <div className="mt-2 flex items-baseline gap-2">
        <span className="text-3xl font-bold text-foreground">{value}</span>
        {unit && <span className="text-sm text-muted-foreground">{unit}</span>}
      </div>
      {change !== undefined && (
        <div
          className="mt-2 flex items-center gap-1"
          title={baseline !== undefined ? `База (12 мес до выбранного периода): ${baseline.toFixed(4)}` : undefined}
        >
          {change >= 0 ? (
            <ArrowUp className="h-4 w-4 text-status-critical" />
          ) : (
            <ArrowDown className="h-4 w-4 text-status-success" />
          )}
          <span
            className={cn(
              "text-sm font-medium",
              change >= 0 ? "text-status-critical" : "text-status-success"
            )}
          >
            {Math.abs(change)}%
          </span>
          <span className="text-xs text-muted-foreground">к пред. периоду</span>
          {baseline !== undefined && (
            <span className="ml-1 text-xs text-muted-foreground/70">(база: {baseline.toFixed(2)})</span>
          )}
        </div>
      )}
    </div>
  )
}
