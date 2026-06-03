"use client"

import { PeriodPicker, type Periodicity } from "@/components/period-picker"

export type { Periodicity }

interface FiltersPanelProps {
  availablePeriods: string[]
  period: string
  periodicity: Periodicity
  onPeriodChange: (period: string) => void
  onPeriodicityChange: (periodicity: Periodicity) => void
}

export function FiltersPanel({
  availablePeriods,
  period,
  periodicity,
  onPeriodChange,
  onPeriodicityChange,
}: FiltersPanelProps) {
  return (
    <div className="flex flex-wrap items-center gap-4 rounded-lg border border-border bg-card p-4">
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-muted-foreground">Регион:</span>
        <span className="rounded-md border border-border bg-input px-3 py-1.5 text-sm">
          Москва
        </span>
      </div>

      <PeriodPicker
        availablePeriods={availablePeriods}
        period={period}
        periodicity={periodicity}
        onPeriodChange={onPeriodChange}
        onPeriodicityChange={onPeriodicityChange}
        variant="inline"
      />
    </div>
  )
}
