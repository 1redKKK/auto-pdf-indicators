"use client"

import { useEffect, useRef, useState } from "react"
import { DashboardLayout } from "@/components/dashboard/dashboard-layout"
import { ReportForm } from "@/components/reports/report-form"
import { ReportsTable, type PendingReportRow } from "@/components/reports/reports-table"
import {
  deleteReport,
  fetchMeta,
  fetchReports,
  generateReport,
  type ReportItem,
  type ReportPeriodicity,
} from "@/lib/api"

const RU_MONTHS = [
  "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]
function periodLabelFor(period: string, periodicity: ReportPeriodicity): string {
  const [y, m] = period.split("-").map(Number)
  if (periodicity === "month") return `${RU_MONTHS[m - 1]} ${y}`
  if (periodicity === "quarter") {
    const q = Math.ceil(m / 3)
    return `${q} кв. ${y}`
  }
  return String(y)
}

const PERIODICITY_LABEL: Record<ReportPeriodicity, string> = {
  month: "Ежемесячный отчёт",
  quarter: "Ежеквартальный отчёт",
  year: "Годовой отчёт",
}

// Целевая длительность фейк-прогресса (мс). Реальная генерация ~5 сек,
// у нас бар доходит до ~95% за 8 сек, остальное — после ответа.
const FAKE_PROGRESS_MS = 8000
const FAKE_PROGRESS_TICK = 150
const FAKE_PROGRESS_CAP = 95

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportItem[]>([])
  const [availablePeriods, setAvailablePeriods] = useState<string[]>([])
  const [loadingList, setLoadingList] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState<PendingReportRow | null>(null)
  const progressTimerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    let cancelled = false
    const init = async () => {
      try {
        const [meta, list] = await Promise.all([fetchMeta(), fetchReports()])
        if (cancelled) return
        setAvailablePeriods(meta.available_periods ?? [])
        setReports(list.reports)
      } catch (err) {
        if (cancelled) return
        const message = err instanceof Error ? err.message : "Не удалось загрузить данные"
        setError(message)
      } finally {
        if (!cancelled) setLoadingList(false)
      }
    }
    init()
    return () => {
      cancelled = true
    }
  }, [])

  // Чистим интервал при unmount.
  useEffect(() => {
    return () => {
      if (progressTimerRef.current) clearInterval(progressTimerRef.current)
    }
  }, [])

  const startFakeProgress = (initial: PendingReportRow) => {
    setPending(initial)
    if (progressTimerRef.current) clearInterval(progressTimerRef.current)
    const startedAt = Date.now()
    progressTimerRef.current = setInterval(() => {
      const elapsed = Date.now() - startedAt
      const target = Math.min(FAKE_PROGRESS_CAP, (elapsed / FAKE_PROGRESS_MS) * 100)
      setPending((prev) => (prev ? { ...prev, progress: target } : null))
    }, FAKE_PROGRESS_TICK)
  }

  const stopFakeProgress = () => {
    if (progressTimerRef.current) {
      clearInterval(progressTimerRef.current)
      progressTimerRef.current = null
    }
  }

  const handleGenerate = async (params: {
    period: string
    periodicity: ReportPeriodicity
  }) => {
    setError(null)
    const tempId = `pending-${Date.now()}`
    startFakeProgress({
      id: tempId,
      title: PERIODICITY_LABEL[params.periodicity],
      region_label: "Москва",
      period_label: periodLabelFor(params.period, params.periodicity),
      progress: 0,
    })

    try {
      await generateReport({
        region: "moscow",
        period: params.period,
        periodicity: params.periodicity,
      })
      // Скачком к 100%, потом небольшая пауза для визуального завершения.
      stopFakeProgress()
      setPending((prev) => (prev ? { ...prev, progress: 100 } : null))
      const list = await fetchReports()
      setReports(list.reports)
      // Уберём pending после короткой задержки, чтобы 100% успело отобразиться.
      setTimeout(() => setPending(null), 400)
    } catch (err) {
      stopFakeProgress()
      setPending(null)
      const message = err instanceof Error ? err.message : "Не удалось сформировать отчёт"
      setError(message)
      throw err   // прокидываем дальше чтобы ReportForm сбросил спиннер на кнопке
    }
  }

  const handleDelete = async (reportId: string) => {
    setError(null)
    try {
      await deleteReport(reportId)
      setReports((prev) => prev.filter((r) => r.id !== reportId))
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось удалить отчёт"
      setError(message)
    }
  }

  return (
    <DashboardLayout unreadAlertsCount={0}>
      <div className="flex flex-col gap-6 p-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Отчёты</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Генерация и скачивание PDF-отчётов по безопасности дорожного движения
          </p>
        </div>

        {error && (
          <div className="rounded-lg border border-status-critical/30 bg-status-critical/10 p-4 text-sm text-foreground">
            {error}
          </div>
        )}

        <ReportForm availablePeriods={availablePeriods} onGenerate={handleGenerate} />

        <ReportsTable
          reports={reports}
          pending={pending}
          loading={loadingList}
          onDelete={handleDelete}
        />
      </div>
    </DashboardLayout>
  )
}
