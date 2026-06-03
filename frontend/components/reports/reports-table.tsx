"use client"

import { Download, FileText, Loader2, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { downloadReportUrl, type ReportItem } from "@/lib/api"

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(1)} КБ`
  return `${(kb / 1024).toFixed(2)} МБ`
}

function formatDate(iso: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return d.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export interface PendingReportRow {
  id: string                  // synthetic id, e.g. "pending-1734567890"
  title: string
  region_label: string
  period_label: string
  progress: number            // 0..100
}

interface ReportsTableProps {
  reports: ReportItem[]
  pending?: PendingReportRow | null
  loading?: boolean
  onDelete?: (reportId: string) => void
}

export function ReportsTable({ reports, pending = null, loading = false, onDelete }: ReportsTableProps) {
  return (
    <div className="rounded-lg border border-border bg-card">
      <div className="border-b border-border px-4 py-3">
        <h2 className="text-lg font-semibold text-foreground">Ранее сформированные отчёты</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border bg-muted/30">
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Заголовок
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Регион
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Период
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Дата генерации
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Размер
              </th>
              <th className="px-4 py-3 text-center text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Действия
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {pending && (
              <tr className="bg-status-info/5">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-status-info/10">
                      <Loader2 className="h-4 w-4 animate-spin text-status-info" />
                    </div>
                    <div className="flex w-full max-w-[280px] flex-col">
                      <span className="text-sm font-medium text-foreground">{pending.title}</span>
                      <Progress value={pending.progress} className="mt-1.5 h-1.5" />
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 text-sm text-foreground">{pending.region_label}</td>
                <td className="px-4 py-3 text-sm text-foreground">{pending.period_label}</td>
                <td className="px-4 py-3 text-sm text-muted-foreground">—</td>
                <td className="px-4 py-3 text-right text-sm tabular-nums text-muted-foreground">—</td>
                <td className="px-4 py-3 text-center">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-status-info/15 px-2.5 py-0.5 text-xs font-medium text-status-info">
                    Формируется… {Math.round(pending.progress)}%
                  </span>
                </td>
              </tr>
            )}
            {reports.map((report) => (
              <tr key={report.id} className="transition-colors hover:bg-muted/20">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-status-critical/10">
                      <FileText className="h-4 w-4 text-status-critical" />
                    </div>
                    <span className="text-sm font-medium text-foreground">{report.title}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-sm text-foreground">{report.region_label}</td>
                <td className="px-4 py-3 text-sm text-foreground">{report.period_label}</td>
                <td className="px-4 py-3 text-sm text-muted-foreground">
                  {formatDate(report.generated_at)}
                </td>
                <td className="px-4 py-3 text-right text-sm tabular-nums text-muted-foreground">
                  {formatBytes(report.size_bytes)}
                </td>
                <td className="px-4 py-3 text-center">
                  <div className="inline-flex items-center gap-1">
                    <Button variant="ghost" size="sm" asChild>
                      <a
                        href={downloadReportUrl(report.id)}
                        download={report.file_name}
                        className="inline-flex items-center gap-1.5"
                      >
                        <Download className="h-4 w-4" />
                        Скачать
                      </a>
                    </Button>
                    {onDelete && (
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="Удалить отчёт"
                        title="Удалить отчёт"
                        className="h-8 w-8 text-status-critical hover:bg-status-critical/10"
                        onClick={() => {
                          if (confirm(`Удалить «${report.title}»?`)) {
                            onDelete(report.id)
                          }
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {!loading && !pending && reports.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
            <FileText className="h-6 w-6 text-muted-foreground" />
          </div>
          <h3 className="mt-4 text-sm font-medium text-foreground">Нет сформированных отчётов</h3>
          <p className="mt-1 text-sm text-muted-foreground">
            Используйте форму выше для генерации нового отчёта
          </p>
        </div>
      )}

      {loading && (
        <div className="px-4 py-6 text-center text-sm text-muted-foreground">
          Загрузка списка отчётов…
        </div>
      )}
    </div>
  )
}
