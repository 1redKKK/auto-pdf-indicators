"use client"

import { cn } from "@/lib/utils"

const RU_MONTHS_LONG = [
  "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]

function periodLabel(d: Date): string {
  // alert.createdAt — UTC midnight; используем UTC-методы чтобы не зависеть от локали браузера
  return `${RU_MONTHS_LONG[d.getUTCMonth()]} ${d.getUTCFullYear()}`
}

export type AlertLevel = "CRITICAL" | "WARNING" | "INFO"

export interface Alert {
  id: string
  createdAt: Date
  region: string
  indicator: string                 // human label, e.g. "Число ДТП"
  indicatorCode: string             // backend code, e.g. "accidents"
  level: AlertLevel
  rule: string
  actualValue: number
  threshold: number
  isAcknowledged: boolean
  message: string
}

interface AlertsTableProps {
  alerts: Alert[]
  onRowClick: (alert: Alert) => void
}

const levelStyles: Record<AlertLevel, { bg: string; text: string; dot: string }> = {
  CRITICAL: {
    bg: "bg-status-critical/10",
    text: "text-status-critical",
    dot: "bg-status-critical",
  },
  WARNING: {
    bg: "bg-status-warning/10",
    text: "text-status-warning",
    dot: "bg-status-warning",
  },
  INFO: {
    bg: "bg-status-info/10",
    text: "text-status-info",
    dot: "bg-status-info",
  },
}

const levelLabels: Record<AlertLevel, string> = {
  CRITICAL: "Критическое",
  WARNING: "Предупреждение",
  INFO: "Информация",
}

export function AlertsTable({ alerts, onRowClick }: AlertsTableProps) {
  return (
    <div className="overflow-hidden rounded-lg border border-border bg-card">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-muted/30">
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Период
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Регион
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Показатель
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Уровень
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Правило
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Значение
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Порог
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Статус
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {alerts.map((alert) => (
              <tr
                key={alert.id}
                onClick={() => onRowClick(alert)}
                className={cn(
                  "cursor-pointer transition-colors hover:bg-muted/20",
                  !alert.isAcknowledged && "bg-status-warning/5"
                )}
              >
                <td className="whitespace-nowrap px-4 py-3 text-sm text-foreground">
                  {periodLabel(alert.createdAt)}
                </td>
                <td className="px-4 py-3 text-sm text-foreground">{alert.region}</td>
                <td className="px-4 py-3 text-sm text-foreground">{alert.indicator}</td>
                <td className="px-4 py-3 text-center">
                  <span
                    className={cn(
                      "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
                      levelStyles[alert.level].bg,
                      levelStyles[alert.level].text
                    )}
                  >
                    <span className={cn("h-1.5 w-1.5 rounded-full", levelStyles[alert.level].dot)} />
                    {levelLabels[alert.level]}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm font-mono text-muted-foreground">{alert.rule}</td>
                <td className="px-4 py-3 text-right text-sm tabular-nums text-foreground">
                  {alert.actualValue.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-right text-sm tabular-nums text-muted-foreground">
                  {alert.threshold.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-center">
                  <span
                    className={cn(
                      "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
                      alert.isAcknowledged
                        ? "bg-muted text-muted-foreground"
                        : "bg-status-info/20 text-status-info"
                    )}
                  >
                    {alert.isAcknowledged ? "Рассмотрено" : "Новое"}
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
