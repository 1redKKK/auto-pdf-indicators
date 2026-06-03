"use client"

import { useEffect, useState } from "react"
import { X, Check, RotateCcw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { Alert, AlertLevel } from "./alerts-table"
import { fetchTrend, type TrendResponse } from "@/lib/api"
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

const levelStyles: Record<AlertLevel, { bg: string; text: string }> = {
  CRITICAL: { bg: "bg-status-critical/10", text: "text-status-critical" },
  WARNING: { bg: "bg-status-warning/10", text: "text-status-warning" },
  INFO: { bg: "bg-status-info/10", text: "text-status-info" },
}

const levelLabels: Record<AlertLevel, string> = {
  CRITICAL: "Критическое отклонение",
  WARNING: "Предупреждение",
  INFO: "Информация",
}

/** Цвета подсвеченной точки на мини-карте — синхронны со списком уровней. */
const LEVEL_DOT_COLOR: Record<AlertLevel, string> = {
  CRITICAL: "oklch(0.55 0.22 25)",   // красный
  WARNING:  "oklch(0.75 0.16 85)",   // жёлтый
  INFO:     "oklch(0.65 0.18 250)",  // синий
}

function fmtRef(n: number): string {
  return Math.abs(n) >= 100 ? n.toFixed(1) : n.toFixed(2)
}

const REF_COLOR = {
  ucl: "oklch(0.55 0.22 25)",   // красный
  cl:  "oklch(0.75 0.16 85)",   // жёлтый
  lcl: "oklch(0.65 0.18 145)",  // зелёный
} as const

interface YTickProps {
  x?: number
  y?: number
  payload?: { value: number }
  ucl: number
  cl: number
  lcl: number
  fontSize?: number
}

function YAxisRefTick({ x, y, payload, ucl, cl, lcl, fontSize = 9 }: YTickProps) {
  if (!payload) return null
  const v = payload.value
  const near = (a: number, b: number) => Math.abs(a - b) < 1e-6
  let fill = "oklch(0.65 0 0)"
  if (near(v, ucl)) fill = REF_COLOR.ucl
  else if (near(v, cl))  fill = REF_COLOR.cl
  else if (near(v, lcl)) fill = REF_COLOR.lcl
  return (
    <text x={x} y={y} dy={3} textAnchor="end" fill={fill} fontSize={fontSize}>
      {fmtRef(v)}
    </text>
  )
}

const RU_MONTHS_LONG = [
  "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
]

function periodLabel(d: Date): string {
  return `${RU_MONTHS_LONG[d.getUTCMonth()]} ${d.getUTCFullYear()}`
}

interface AlertDetailPanelProps {
  alert: Alert
  onClose: () => void
  onAcknowledge: (alertId: string) => void
  onUnacknowledge: (alertId: string) => void
}

interface DotProps {
  cx?: number
  cy?: number
  payload?: { isHighlighted?: boolean }
  highlightColor: string
}

function ChartDot({ cx, cy, payload, highlightColor }: DotProps) {
  if (payload?.isHighlighted) {
    return (
      <circle
        cx={cx}
        cy={cy}
        r={6}
        fill={highlightColor}
        stroke={highlightColor}
        strokeWidth={2}
      />
    )
  }
  return (
    <circle
      cx={cx}
      cy={cy}
      r={3}
      fill="oklch(0.55 0.15 250)"
    />
  )
}

export function AlertDetailPanel({ alert, onClose, onAcknowledge, onUnacknowledge }: AlertDetailPanelProps) {
  const [trend, setTrend] = useState<TrendResponse | null>(null)
  const [trendError, setTrendError] = useState<string | null>(null)

  // Без end_period тренд возвращает дефолтный (последний) год — для алерта
  // из 2024 это давало график 2025 и подсвеченная точка терялась.
  const alertYear = alert.createdAt.getUTCFullYear()

  useEffect(() => {
    let cancelled = false
    setTrend(null)
    setTrendError(null)
    const load = async () => {
      try {
        const data = await fetchTrend(alert.indicatorCode, `${alertYear}-12`)
        if (!cancelled) setTrend(data)
      } catch (err) {
        if (cancelled) return
        const msg = err instanceof Error ? err.message : "Не удалось загрузить тренд"
        setTrendError(msg)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [alert.indicatorCode, alertYear])

  const alertMonthLabel = periodLabel(alert.createdAt)
  const alertDateIso = alert.createdAt.toISOString().slice(0, 10)
  const chartData = trend?.points.map((p) => ({
    ...p,
    isHighlighted: p.date === alertDateIso,
  })) ?? []
  const highlightColor = LEVEL_DOT_COLOR[alert.level]

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-96 border-l border-border bg-card shadow-xl">
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h2 className="text-lg font-semibold text-foreground">Детали предупреждения</h2>
        <Button variant="ghost" size="icon" onClick={onClose} className="h-8 w-8">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex flex-col gap-6 p-4">
        <div
          className={cn(
            "rounded-lg border px-4 py-3",
            levelStyles[alert.level].bg,
            alert.level === "CRITICAL" && "border-status-critical/30",
            alert.level === "WARNING" && "border-status-warning/30",
            alert.level === "INFO" && "border-status-info/30"
          )}
        >
          <span className={cn("text-sm font-medium", levelStyles[alert.level].text)}>
            {levelLabels[alert.level]}
          </span>
        </div>

        <div className="flex flex-col gap-3">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Период:</span>
            <span className="font-medium text-foreground">{alertMonthLabel}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Регион:</span>
            <span className="font-medium text-foreground">{alert.region}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Показатель:</span>
            <span className="font-medium text-foreground">{alert.indicator}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Правило:</span>
            <span className="font-mono text-foreground">{alert.rule}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Фактическое значение:</span>
            <span className="font-semibold tabular-nums text-foreground">
              {alert.actualValue.toFixed(2)}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">Пороговое значение:</span>
            <span className="tabular-nums text-muted-foreground">{alert.threshold.toFixed(2)}</span>
          </div>
        </div>

        <div className="rounded-lg bg-muted/30 p-3">
          <p className="text-sm leading-relaxed text-foreground">{alert.message}</p>
        </div>

        <div className="rounded-lg border border-border p-3">
          <h4 className="mb-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Контрольная карта
          </h4>
          {trendError ? (
            <div className="flex h-32 items-center justify-center text-xs text-status-critical">
              {trendError}
            </div>
          ) : !trend ? (
            <div className="flex h-32 items-center justify-center text-xs text-muted-foreground">
              Загрузка…
            </div>
          ) : (
            <div className="h-40">
              {(() => {
                const values = chartData.map((p) => p.value).filter((v) => Number.isFinite(v))
                const dataMin = values.length ? Math.min(...values) : trend.lcl
                const dataMax = values.length ? Math.max(...values) : trend.ucl
                const yMin = Math.max(0, Math.floor(Math.min(dataMin, trend.lcl) * 90) / 100)
                const yMax = Math.ceil(Math.max(dataMax, trend.ucl) * 110) / 100
                const yTicks = [yMin, trend.lcl, trend.cl, trend.ucl, yMax]
                return (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 8, right: 26, left: 4, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="oklch(0.28 0.01 260)" />
                  <XAxis
                    dataKey="month_label"
                    stroke="oklch(0.65 0 0)"
                    fontSize={9}
                    tickLine={false}
                    axisLine={false}
                    interval={0}
                    minTickGap={0}
                    tickFormatter={(v: string) => v.split(" ")[0]}
                  />
                  <YAxis
                    stroke="oklch(0.65 0 0)"
                    tickLine={false}
                    axisLine={false}
                    domain={[yMin, yMax]}
                    ticks={yTicks}
                    interval={0}
                    width={48}
                    tick={(props) => (
                      <YAxisRefTick {...props} ucl={trend.ucl} cl={trend.cl} lcl={trend.lcl} fontSize={9} />
                    )}
                  />
                  <ReferenceLine
                    y={trend.ucl} stroke={REF_COLOR.ucl} strokeDasharray="3 3"
                    label={{ value: "UCL", position: "right", fill: REF_COLOR.ucl, fontSize: 9 }}
                  />
                  <ReferenceLine
                    y={trend.cl} stroke={REF_COLOR.cl} strokeDasharray="3 3"
                    label={{ value: "CL", position: "right", fill: REF_COLOR.cl, fontSize: 9 }}
                  />
                  <ReferenceLine
                    y={trend.lcl} stroke={REF_COLOR.lcl} strokeDasharray="3 3"
                    label={{ value: "LCL", position: "right", fill: REF_COLOR.lcl, fontSize: 9 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="value"
                    stroke="oklch(0.55 0.15 250)"
                    strokeWidth={2}
                    dot={({ cx, cy, payload, key }) => (
                      <ChartDot key={key} cx={cx} cy={cy} payload={payload} highlightColor={highlightColor} />
                    )}
                    activeDot={{ r: 5 }}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "oklch(0.18 0.01 260)",
                      border: "1px solid oklch(0.28 0.01 260)",
                      borderRadius: "6px",
                      fontSize: "12px",
                    }}
                    separator=""
                    formatter={(value: number) => [value, ""]}
                  />
                </LineChart>
              </ResponsiveContainer>
                )
              })()}
            </div>
          )}
        </div>

        {!alert.isAcknowledged ? (
          <Button
            onClick={() => onAcknowledge(alert.id)}
            className="w-full bg-primary hover:bg-primary/90"
          >
            <Check className="mr-2 h-4 w-4" />
            Отметить как рассмотренное
          </Button>
        ) : (
          <div className="flex flex-col gap-2">
            <div className="rounded-lg bg-muted/30 px-4 py-3 text-center text-sm text-muted-foreground">
              Предупреждение рассмотрено
            </div>
            <Button
              variant="outline"
              onClick={() => onUnacknowledge(alert.id)}
              className="w-full"
            >
              <RotateCcw className="mr-2 h-4 w-4" />
              Вернуть в нерассмотренные
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
