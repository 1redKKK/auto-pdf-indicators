"use client"

import { useEffect, useMemo, useState } from "react"
import { DashboardLayout } from "@/components/dashboard/dashboard-layout"
import { AlertsFilters, ALL_PERIODS } from "@/components/alerts/alerts-filters"
import { AlertsTable, type Alert } from "@/components/alerts/alerts-table"
import { AlertDetailPanel } from "@/components/alerts/alert-detail-panel"
import {
  acknowledgeAlert,
  fetchAlerts,
  fetchMeta,
  unacknowledgeAlert,
  type AlertItem,
} from "@/lib/api"
import type { Periodicity } from "@/components/dashboard/filters-panel"

const LEVEL_MAP = {
  critical: "CRITICAL",
  warning: "WARNING",
  info: "INFO",
} as const

function toUiAlert(item: AlertItem): Alert {
  return {
    id: item.id,
    createdAt: new Date(item.datetime),
    region: item.region === "moscow" ? "Москва" : item.region,
    indicator: item.indicator_label,
    indicatorCode: item.indicator,
    level: LEVEL_MAP[item.level],
    rule: item.rule_label,
    actualValue: item.value,
    threshold: item.threshold,
    isAcknowledged: item.status === "acknowledged",
    message: item.description,
  }
}

const PERIODICITY_MONTHS: Record<Periodicity, number> = {
  month: 1,
  quarter: 3,
  year: 12,
}

// Resolve (period anchor, periodicity) into [startUTC, endUTC).
function resolveWindow(
  period: string,
  periodicity: Periodicity,
): { start: Date; end: Date } | null {
  if (period === ALL_PERIODS) return null
  const [y, m] = period.split("-").map(Number)
  if (!y || !m) return null
  const months = PERIODICITY_MONTHS[periodicity]
  const end = new Date(Date.UTC(y, m, 1))
  const start = new Date(Date.UTC(y, m - months, 1))
  return { start, end }
}

const RU_MONTHS_LONG = [
  "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]

// Используется в search чтобы найти алерт по тексту вроде «декабрь 2025».
function formatAlertPeriod(d: Date): string {
  return `${RU_MONTHS_LONG[d.getUTCMonth()]} ${d.getUTCFullYear()}`
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [levelFilter, setLevelFilter] = useState<"all" | "critical" | "warning" | "info">("all")
  const [statusFilter, setStatusFilter] = useState<"all" | "new" | "acknowledged">("all")
  const [availablePeriods, setAvailablePeriods] = useState<string[]>([])
  const [period, setPeriod] = useState<string>(ALL_PERIODS)
  const [periodicity, setPeriodicity] = useState<Periodicity>("month")
  const [search, setSearch] = useState("")

  useEffect(() => {
    let cancelled = false
    const init = async () => {
      try {
        const meta = await fetchMeta()
        if (cancelled) return
        setAvailablePeriods(meta.available_periods ?? [])
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
    const loadAlerts = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await fetchAlerts({ level: levelFilter, status: statusFilter, limit: 200 })
        if (cancelled) return
        setAlerts(data.alerts.map(toUiAlert))
      } catch (err) {
        const message = err instanceof Error ? err.message : "Не удалось загрузить предупреждения"
        setError(message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadAlerts()
    return () => {
      cancelled = true
    }
  }, [levelFilter, statusFilter])

  const handleAcknowledge = async (alertId: string) => {
    try {
      await acknowledgeAlert(alertId)
      setAlerts((prev) =>
        prev.map((alert) =>
          alert.id === alertId ? { ...alert, isAcknowledged: true } : alert
        )
      )
      if (selectedAlert?.id === alertId) {
        setSelectedAlert({ ...selectedAlert, isAcknowledged: true })
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось подтвердить предупреждение"
      setError(message)
    }
  }

  const handleUnacknowledge = async (alertId: string) => {
    try {
      await unacknowledgeAlert(alertId)
      setAlerts((prev) =>
        prev.map((alert) =>
          alert.id === alertId ? { ...alert, isAcknowledged: false } : alert
        )
      )
      if (selectedAlert?.id === alertId) {
        setSelectedAlert({ ...selectedAlert, isAcknowledged: false })
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось вернуть предупреждение в нерассмотренные"
      setError(message)
    }
  }

  const filteredAlerts = useMemo(() => {
    let result = alerts
    const window = resolveWindow(period, periodicity)
    if (window) {
      result = result.filter((a) => a.createdAt >= window.start && a.createdAt < window.end)
    }
    const query = search.trim().toLowerCase()
    if (query) {
      result = result.filter((a) => {
        const periodStr = formatAlertPeriod(a.createdAt).toLowerCase()
        return (
          a.indicator.toLowerCase().includes(query)
          || a.rule.toLowerCase().includes(query)
          || a.message.toLowerCase().includes(query)
          || a.region.toLowerCase().includes(query)
          || periodStr.includes(query)
        )
      })
    }
    return result
  }, [alerts, period, periodicity, search])

  const unreadCount = filteredAlerts.filter((a) => !a.isAcknowledged).length

  const handleReset = () => {
    setLevelFilter("all")
    setStatusFilter("all")
    setPeriod(ALL_PERIODS)
    setPeriodicity("month")
    setSearch("")
  }

  return (
    <DashboardLayout unreadAlertsCount={unreadCount}>
      <div className="flex flex-col gap-6 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Предупреждения</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Автоматически сгенерированные уведомления о статистических аномалиях
            </p>
          </div>
          {unreadCount > 0 && (
            <div className="flex items-center gap-2 rounded-lg bg-status-warning/10 px-3 py-2">
              <span className="h-2 w-2 rounded-full bg-status-warning" />
              <span className="text-sm font-medium text-status-warning">
                {unreadCount} нерассмотренных
              </span>
            </div>
          )}
        </div>

        {error && (
          <div className="rounded-lg border border-status-critical/30 bg-status-critical/10 p-4 text-sm text-foreground">
            {error}
          </div>
        )}

        <AlertsFilters
          level={levelFilter}
          availablePeriods={availablePeriods}
          period={period}
          periodicity={periodicity}
          onLevelChange={(level) =>
            setLevelFilter((level as "all" | "critical" | "warning" | "info") || "all")
          }
          onPeriodChange={setPeriod}
          onPeriodicityChange={setPeriodicity}
          onReset={handleReset}
        />

        <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <div className="relative">
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Поиск по показателю, правилу, описанию"
              className="h-9 w-[320px] rounded-md border border-border bg-input px-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-ring focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>
          <span className="ml-2">Статус:</span>
          <button
            onClick={() => setStatusFilter("all")}
            className={statusFilter === "all" ? "font-semibold text-foreground" : ""}
          >
            Все
          </button>
          <button
            onClick={() => setStatusFilter("new")}
            className={statusFilter === "new" ? "font-semibold text-foreground" : ""}
          >
            Новые
          </button>
          <button
            onClick={() => setStatusFilter("acknowledged")}
            className={statusFilter === "acknowledged" ? "font-semibold text-foreground" : ""}
          >
            Рассмотренные
          </button>
        </div>

        {loading ? (
          <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
            Загрузка предупреждений...
          </div>
        ) : filteredAlerts.length === 0 ? (
          <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
            Нет предупреждений по текущим фильтрам
          </div>
        ) : (
          <AlertsTable alerts={filteredAlerts} onRowClick={setSelectedAlert} />
        )}

        {selectedAlert && (
          <AlertDetailPanel
            alert={selectedAlert}
            onClose={() => setSelectedAlert(null)}
            onAcknowledge={handleAcknowledge}
            onUnacknowledge={handleUnacknowledge}
          />
        )}
      </div>
    </DashboardLayout>
  )
}
