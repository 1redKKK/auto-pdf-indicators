"use client"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import {
  ALL_PERIODS,
  PeriodPicker,
  type Periodicity,
} from "@/components/period-picker"

export { ALL_PERIODS }

const levels = [
  { value: "all", label: "Все уровни" },
  { value: "critical", label: "Критические" },
  { value: "warning", label: "Предупреждения" },
  { value: "info", label: "Информация" },
]

interface AlertsFiltersProps {
  level: string
  availablePeriods: string[]
  period: string
  periodicity: Periodicity
  onLevelChange: (level: string) => void
  onPeriodChange: (period: string) => void
  onPeriodicityChange: (periodicity: Periodicity) => void
  onReset: () => void
}

export function AlertsFilters({
  level,
  availablePeriods,
  period,
  periodicity,
  onLevelChange,
  onPeriodChange,
  onPeriodicityChange,
  onReset,
}: AlertsFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-4 rounded-lg border border-border bg-card p-4">
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-muted-foreground">Уровень:</span>
        <Select value={level} onValueChange={onLevelChange}>
          <SelectTrigger className="w-[160px] bg-input">
            <SelectValue placeholder="Выберите уровень" />
          </SelectTrigger>
          <SelectContent>
            {levels.map((item) => (
              <SelectItem key={item.value} value={item.value}>
                {item.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

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
        allowAll
        variant="inline"
      />

      <Button variant="outline" size="sm" className="ml-auto" onClick={onReset}>
        Сбросить фильтры
      </Button>
    </div>
  )
}
