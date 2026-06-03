"use client"

import { useEffect, useState } from "react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { fetchMeta, fetchTrend, type TrendResponse } from "@/lib/api"

const INDICATORS = [
  { code: "accidents", label: "Число ДТП" },
  { code: "severity", label: "Коэффициент тяжести" },
  { code: "social_risk", label: "Социальный риск" },
  { code: "network_freq", label: "Частота на км сети" },
]

/** Years that have all 12 months in the available list — these can be plotted as a full-year chart. */
function fullYearOptions(periods: string[]): number[] {
  const setYM = new Set(periods)
  const seen = new Set<number>()
  const out: number[] = []
  for (const ym of periods) {
    const [y] = ym.split("-").map(Number)
    if (seen.has(y)) continue
    const months = Array.from({ length: 12 }, (_, i) =>
      `${y}-${String(i + 1).padStart(2, "0")}`
    )
    if (!months.every((mm) => setYM.has(mm))) continue
    seen.add(y)
    out.push(y)
  }
  return out
}

type AlertLevel = "critical" | "warning" | "info"

const ALERT_COLOR: Record<AlertLevel, string> = {
  critical: "oklch(0.55 0.22 25)",   // красный
  warning:  "oklch(0.75 0.16 85)",   // жёлтый
  info:     "oklch(0.65 0.18 250)",  // синий
}

interface CustomDotProps {
  cx?: number
  cy?: number
  payload?: { alert_level?: AlertLevel | null }
}

const CustomDot = ({ cx, cy, payload }: CustomDotProps) => {
  const level = payload?.alert_level
  if (level && level in ALERT_COLOR) {
    const color = ALERT_COLOR[level]
    return (
      <circle cx={cx} cy={cy} r={6} fill={color} stroke={color} strokeWidth={2} />
    )
  }
  return (
    <circle cx={cx} cy={cy} r={4} fill="oklch(0.65 0.18 145)" />
  )
}

/** "807.27" / "1.66" — единый формат для подписей UCL/CL/LCL. */
function fmtRef(n: number): string {
  return Math.abs(n) >= 100 ? n.toFixed(1) : n.toFixed(2)
}

const REF_COLOR = {
  ucl: "oklch(0.55 0.22 25)",   // красный
  cl:  "oklch(0.75 0.16 85)",   // жёлтый
  lcl: "oklch(0.65 0.18 145)",  // зелёный
} as const

/** Кастомный рендер тика оси Y: на LCL/CL/UCL — цветная подпись со значением,
 * на yMin/yMax — обычное число. Так пользователь видит границы и диапазон
 * данных, без лишних промежуточных тиков. */
interface YTickProps {
  x?: number
  y?: number
  payload?: { value: number }
  ucl: number
  cl: number
  lcl: number
  fontSize?: number
}

function YAxisRefTick({ x, y, payload, ucl, cl, lcl, fontSize = 10 }: YTickProps) {
  if (!payload) return null
  const v = payload.value
  const near = (a: number, b: number) => Math.abs(a - b) < 1e-6
  let fill = "oklch(0.65 0 0)"
  if (near(v, ucl)) fill = REF_COLOR.ucl
  else if (near(v, cl))  fill = REF_COLOR.cl
  else if (near(v, lcl)) fill = REF_COLOR.lcl
  return (
    <text x={x} y={y} dy={4} textAnchor="end" fill={fill} fontSize={fontSize}>
      {fmtRef(v)}
    </text>
  )
}

export function TrendChart() {
  const [selectedIndicator, setSelectedIndicator] = useState("accidents")
  const [availableYears, setAvailableYears] = useState<number[]>([])
  const [year, setYear] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<TrendResponse | null>(null)

  useEffect(() => {
    let cancelled = false
    const init = async () => {
      try {
        const meta = await fetchMeta()
        if (cancelled) return
        const periods = (meta.available_periods ?? []).filter((p) => p.length > 0)
        const years = fullYearOptions(periods)
        setAvailableYears(years)
        if (years.length > 0) setYear(years[years.length - 1])
      } catch {
        // если meta не загрузилась — оставим year=null, тренд возьмёт кеш по умолчанию
      }
    }
    init()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        setLoading(true)
        setError(null)
        const endPeriod = year ? `${year}-12` : undefined
        const trend = await fetchTrend(selectedIndicator, endPeriod)
        if (!cancelled) setData(trend)
      } catch (err) {
        if (cancelled) return
        const message = err instanceof Error ? err.message : "Failed to load trend"
        setError(message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [selectedIndicator, year])

  const hasYears = availableYears.length > 0 && year !== null

  return (
    <div className="flex h-full flex-col rounded-lg border border-border bg-card p-4">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-foreground">Контрольная карта</h3>
        <div className="flex flex-wrap items-center gap-2">
          {hasYears && (
            <Select
              value={String(year)}
              onValueChange={(v) => setYear(Number(v))}
            >
              <SelectTrigger className="w-[120px] bg-input">
                <SelectValue placeholder="Год" />
              </SelectTrigger>
              <SelectContent>
                {availableYears.map((y) => (
                  <SelectItem key={y} value={String(y)}>
                    {y}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Select value={selectedIndicator} onValueChange={setSelectedIndicator}>
            <SelectTrigger className="w-[180px] bg-input">
              <SelectValue placeholder="Выберите показатель" />
            </SelectTrigger>
            <SelectContent>
              {INDICATORS.map((item) => (
                <SelectItem key={item.code} value={item.code}>
                  {item.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {error && (
        <div className="rounded bg-status-critical/10 p-2 text-xs text-status-critical">
          {error}
        </div>
      )}

      <div className="flex-1">
        {loading ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-muted-foreground">Загрузка...</p>
          </div>
        ) : data ? (() => {
          const values = data.points.map((p) => p.value).filter((v) => Number.isFinite(v))
          const dataMin = values.length ? Math.min(...values) : data.lcl
          const dataMax = values.length ? Math.max(...values) : data.ucl
          const yMin = Math.max(0, Math.floor(Math.min(dataMin, data.lcl) * 90) / 100)
          const yMax = Math.ceil(Math.max(dataMax, data.ucl) * 110) / 100
          const yTicks = [yMin, data.lcl, data.cl, data.ucl, yMax]
          return (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data.points} margin={{ top: 20, right: 36, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.28 0.01 260)" />
              <XAxis
                dataKey="month_label"
                stroke="oklch(0.65 0 0)"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                interval={0}
                tickFormatter={(v: string) => v.split(" ")[0]}
              />
              <YAxis
                stroke="oklch(0.65 0 0)"
                fontSize={12}
                tickLine={false}
                axisLine={false}
                domain={[yMin, yMax]}
                ticks={yTicks}
                width={56}
                interval={0}
                tick={(props) => (
                  <YAxisRefTick {...props} ucl={data.ucl} cl={data.cl} lcl={data.lcl} fontSize={11} />
                )}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "oklch(0.18 0.01 260)",
                  border: "1px solid oklch(0.28 0.01 260)",
                  borderRadius: "8px",
                  color: "oklch(0.95 0 0)",
                }}
                labelStyle={{ color: "oklch(0.65 0 0)" }}
                separator=""
                formatter={(value: number) => [value, ""]}
              />
              <ReferenceLine
                y={data.ucl} stroke={REF_COLOR.ucl} strokeDasharray="5 5"
                label={{ value: "UCL", position: "right", fill: REF_COLOR.ucl, fontSize: 10 }}
              />
              <ReferenceLine
                y={data.cl} stroke={REF_COLOR.cl} strokeDasharray="5 5"
                label={{ value: "CL", position: "right", fill: REF_COLOR.cl, fontSize: 10 }}
              />
              <ReferenceLine
                y={data.lcl} stroke={REF_COLOR.lcl} strokeDasharray="5 5"
                label={{ value: "LCL", position: "right", fill: REF_COLOR.lcl, fontSize: 10 }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="oklch(0.55 0.15 250)"
                strokeWidth={2}
                dot={({ cx, cy, payload, key }) => (
                  <CustomDot key={key} cx={cx} cy={cy} payload={payload} />
                )}
                activeDot={{ r: 6, fill: "oklch(0.55 0.15 250)" }}
              />
            </LineChart>
          </ResponsiveContainer>
          )
        })() : null}
      </div>

      <div className="mt-4 flex flex-wrap gap-4 text-xs">
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full bg-status-critical" />
          <span className="text-muted-foreground">UCL — верхняя граница</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full bg-status-warning" />
          <span className="text-muted-foreground">CL — центральная линия</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="h-3 w-3 rounded-full bg-status-success" />
          <span className="text-muted-foreground">LCL — нижняя граница</span>
        </div>
      </div>
    </div>
  )
}
