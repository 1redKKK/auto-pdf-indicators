"use client"

import { useState } from "react"
import { FileText, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { PeriodPicker, type Periodicity } from "@/components/period-picker"
import type { ReportPeriodicity } from "@/lib/api"

interface ReportFormProps {
  availablePeriods: string[]
  onGenerate: (params: { period: string; periodicity: ReportPeriodicity }) => Promise<void>
}

export function ReportForm({ availablePeriods, onGenerate }: ReportFormProps) {
  const [periodicity, setPeriodicity] = useState<Periodicity>("month")
  const [period, setPeriod] = useState("")
  const [isGenerating, setIsGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canGenerate = period.length > 0 && !isGenerating

  const handleGenerate = async () => {
    if (!period) return
    setIsGenerating(true)
    setError(null)
    try {
      await onGenerate({ period, periodicity })
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Не удалось сформировать отчёт"
      setError(msg)
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <h2 className="mb-6 text-lg font-semibold text-foreground">Сформировать новый отчёт</h2>

      <div className="flex flex-wrap items-end gap-4">
        <div className="flex flex-col gap-2">
          <label className="text-sm font-medium text-muted-foreground">Регион</label>
          <span className="rounded-md border border-border bg-input px-3 py-1.5 text-sm">
            Москва
          </span>
        </div>

        <PeriodPicker
          availablePeriods={availablePeriods}
          period={period}
          periodicity={periodicity}
          onPeriodChange={setPeriod}
          onPeriodicityChange={setPeriodicity}
        />

        <Button
          onClick={handleGenerate}
          disabled={!canGenerate}
          className="bg-primary hover:bg-primary/90"
        >
          {isGenerating ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Формирование…
            </>
          ) : (
            <>
              <FileText className="mr-2 h-4 w-4" />
              Сформировать отчёт
            </>
          )}
        </Button>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-status-critical/30 bg-status-critical/10 px-4 py-3 text-sm text-foreground">
          {error}
        </div>
      )}
    </div>
  )
}
