"use client"

import { useEffect, useMemo } from "react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export type Periodicity = "month" | "quarter" | "year"
export const ALL_PERIODS = "__all__"

const RU_MONTHS = [
  "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]

const PERIODICITY_OPTIONS: { value: Periodicity; label: string }[] = [
  { value: "month", label: "Ежемесячный" },
  { value: "quarter", label: "Ежеквартальный" },
  { value: "year", label: "Годовой" },
]

interface PeriodOption {
  value: string                 // anchor month YYYY-MM (last month of window)
  label: string
}

function monthOptions(periods: string[]): PeriodOption[] {
  return periods.map((ym) => {
    const [y, m] = ym.split("-").map(Number)
    return { value: ym, label: `${RU_MONTHS[m - 1]} ${y}` }
  })
}

function quarterOptions(periods: string[]): PeriodOption[] {
  const setYM = new Set(periods)
  const out: PeriodOption[] = []
  const seen = new Set<string>()
  for (const ym of periods) {
    const [y, m] = ym.split("-").map(Number)
    const q = Math.ceil(m / 3)
    const lastMonth = q * 3
    const key = `${y}-Q${q}`
    if (seen.has(key)) continue
    const months = [lastMonth - 2, lastMonth - 1, lastMonth].map(
      (mm) => `${y}-${String(mm).padStart(2, "0")}`
    )
    if (!months.every((mm) => setYM.has(mm))) continue
    seen.add(key)
    out.push({
      value: `${y}-${String(lastMonth).padStart(2, "0")}`,
      label: `${q} кв. ${y}`,
    })
  }
  return out
}

function yearOptions(periods: string[]): PeriodOption[] {
  const setYM = new Set(periods)
  const out: PeriodOption[] = []
  const seen = new Set<number>()
  for (const ym of periods) {
    const [y] = ym.split("-").map(Number)
    if (seen.has(y)) continue
    const months = Array.from({ length: 12 }, (_, i) =>
      `${y}-${String(i + 1).padStart(2, "0")}`
    )
    if (!months.every((mm) => setYM.has(mm))) continue
    seen.add(y)
    out.push({ value: `${y}-12`, label: `${y}` })
  }
  return out
}

export function buildPeriodOptions(
  periods: string[],
  periodicity: Periodicity
): PeriodOption[] {
  // Сортируем от свежего к старому: новые периоды сверху списка.
  let opts: PeriodOption[]
  if (periodicity === "month") opts = monthOptions(periods)
  else if (periodicity === "quarter") opts = quarterOptions(periods)
  else opts = yearOptions(periods)
  return [...opts].reverse()
}

interface PeriodPickerProps {
  availablePeriods: string[]
  period: string
  periodicity: Periodicity
  onPeriodChange: (period: string) => void
  onPeriodicityChange: (periodicity: Periodicity) => void
  allowAll?: boolean            // adds "Все периоды" option (used on /alerts)
  /** "stacked" — label above (default), "inline" — label as muted prefix span. */
  variant?: "stacked" | "inline"
}

/**
 * Renders TWO inline-block groups (Тип отчёта + Период) side-by-side as a
 * Fragment. The parent decides the outer flex layout.
 */
export function PeriodPicker({
  availablePeriods,
  period,
  periodicity,
  onPeriodChange,
  onPeriodicityChange,
  allowAll = false,
  variant = "stacked",
}: PeriodPickerProps) {
  const validPeriods = useMemo(
    () => availablePeriods.filter((p) => p.length > 0),
    [availablePeriods]
  )
  const options = useMemo(
    () => buildPeriodOptions(validPeriods, periodicity),
    [validPeriods, periodicity]
  )

  // Reset to a sensible default when periodicity changes (or initial load).
  useEffect(() => {
    if (period === ALL_PERIODS && allowAll) return
    if (options.length === 0) {
      onPeriodChange(allowAll ? ALL_PERIODS : "")
      return
    }
    const stillValid = options.some((o) => o.value === period)
    if (!stillValid) {
      // options отсортированы desc по дате (свежий первый) — берём самое свежее.
      onPeriodChange(options[0].value)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options])

  const hasOptions = options.length > 0

  if (variant === "inline") {
    return (
      <>
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">Тип отчёта:</span>
          <Select
            value={periodicity}
            onValueChange={(v) => onPeriodicityChange(v as Periodicity)}
          >
            <SelectTrigger className="w-[180px] bg-input">
              <SelectValue placeholder="Тип" />
            </SelectTrigger>
            <SelectContent>
              {PERIODICITY_OPTIONS.map((t) => (
                <SelectItem key={t.value} value={t.value}>
                  {t.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-muted-foreground">Период:</span>
          {hasOptions ? (
            <Select value={period} onValueChange={onPeriodChange}>
              <SelectTrigger className="w-[180px] bg-input">
                <SelectValue placeholder="Период" />
              </SelectTrigger>
              <SelectContent>
                {allowAll && (
                  <SelectItem value={ALL_PERIODS}>Все периоды</SelectItem>
                )}
                {options.map((o) => (
                  <SelectItem key={o.value} value={o.value}>
                    {o.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <span className="rounded-md border border-border bg-input px-3 py-1.5 text-sm text-muted-foreground">
              {validPeriods.length === 0 ? "загрузка…" : "нет полных периодов"}
            </span>
          )}
        </div>
      </>
    )
  }

  // stacked variant (label above) — for /reports form
  return (
    <>
      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-muted-foreground">Тип отчёта</label>
        <Select
          value={periodicity}
          onValueChange={(v) => onPeriodicityChange(v as Periodicity)}
        >
          <SelectTrigger className="w-[200px] bg-input">
            <SelectValue placeholder="Тип отчёта" />
          </SelectTrigger>
          <SelectContent>
            {PERIODICITY_OPTIONS.map((t) => (
              <SelectItem key={t.value} value={t.value}>
                {t.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-muted-foreground">Период</label>
        {hasOptions ? (
          <Select value={period} onValueChange={onPeriodChange}>
            <SelectTrigger className="w-[200px] bg-input">
              <SelectValue placeholder="Период" />
            </SelectTrigger>
            <SelectContent>
              {allowAll && (
                <SelectItem value={ALL_PERIODS}>Все периоды</SelectItem>
              )}
              {options.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <span className="rounded-md border border-border bg-input px-3 py-1.5 text-sm text-muted-foreground">
            {validPeriods.length === 0 ? "загрузка…" : "нет полных периодов"}
          </span>
        )}
      </div>
    </>
  )
}
