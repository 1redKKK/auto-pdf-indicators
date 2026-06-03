// Default to relative URL: works when frontend is served by FastAPI on the
// same origin (production / single-command run). For dev (npm run dev on
// :3000 ↔ uvicorn on :8000) override via NEXT_PUBLIC_API_BASE.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "/api/m10"

export interface Period {
  baseline_start: string
  baseline_end: string
  report_start: string
  report_end: string
  baseline_months: number
  report_months: number
}

export interface KpiCardData {
  code: string
  label: string
  unit: string
  value: number
  delta_abs: number | null
  delta_pct: number | null
  is_improvement: boolean | null
}

export interface IndicatorsResponse {
  region: string
  period: Period
  last_calculated_at: string
  cards: KpiCardData[]
}

export interface TrendPoint {
  date: string
  month_label: string
  value: number
  out_of_control: boolean
  alert_level: "info" | "warning" | "critical" | null
}

export interface TrendResponse {
  indicator: string
  label: string
  unit: string
  chart_type: "c-chart" | "u-chart" | "i-chart"
  cl: number
  ucl: number
  lcl: number
  points: TrendPoint[]
  baseline_months: number
  report_months: number
}

export type ApiAlertLevel = "critical" | "warning" | "info"
export type ApiAlertStatus = "new" | "acknowledged"
export type ApiAlertType = "A" | "B" | "C"

export interface AlertItem {
  id: string
  datetime: string
  region: string
  indicator: string
  indicator_label: string
  rule: string
  rule_label: string
  level: ApiAlertLevel
  level_label: string
  type: ApiAlertType
  value: number
  threshold: number
  status: ApiAlertStatus
  description: string
}

export interface AlertsResponse {
  total: number
  alerts: AlertItem[]
}

export interface AlertAcknowledgeResponse {
  id: string
  status: ApiAlertStatus
  acknowledged_at: string
}

export type HotspotStatus = "active" | "potential"

export interface HotspotItem {
  rank: number
  name: string
  lat: number
  lon: number
  accidents_count: number
  killed: number
  injured: number
  severity_coef: number
  frequency: number               // ДТП/мес
  frequency_per_km: number        // K_L (ДТП/км сети)
  status: HotspotStatus
}

export interface HotspotsResponse {
  hotspots: HotspotItem[]
  period_label: string
  period_months: number
}

export interface MetaPeriod {
  baseline_start: string
  baseline_end: string
  report_start: string
  report_end: string
  baseline_months: number
  report_months: number
}

export interface MetaResponse {
  region: string
  total_records: number
  date_range: { from: string | null; to: string | null }
  last_updated: string | null
  months_available: number
  period: MetaPeriod
  available_periods: string[]
}

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" })
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(`API ${res.status}: ${text || res.statusText}`)
  }
  return res.json() as Promise<T>
}

export async function fetchMeta(): Promise<MetaResponse> {
  return fetchJson<MetaResponse>("/meta")
}

export async function fetchIndicators(params?: {
  period?: string
  periodicity?: "month" | "quarter" | "year"
}): Promise<IndicatorsResponse> {
  const query = new URLSearchParams()
  if (params?.period) query.set("period", params.period)
  if (params?.periodicity) query.set("periodicity", params.periodicity)
  const suffix = query.toString()
  return fetchJson<IndicatorsResponse>(`/indicators${suffix ? `?${suffix}` : ""}`)
}

export async function fetchTrend(
  indicator: string,
  endPeriod?: string,
): Promise<TrendResponse> {
  const query = new URLSearchParams({ indicator })
  if (endPeriod) query.set("end_period", endPeriod)
  return fetchJson<TrendResponse>(`/trend?${query.toString()}`)
}

export async function fetchAlerts(params?: {
  status?: "new" | "acknowledged" | "all"
  level?: "critical" | "warning" | "info" | "all"
  limit?: number
}): Promise<AlertsResponse> {
  const query = new URLSearchParams()
  if (params?.status) query.set("status", params.status)
  if (params?.level) query.set("level", params.level)
  if (typeof params?.limit === "number") query.set("limit", String(params.limit))
  const suffix = query.toString()
  return fetchJson<AlertsResponse>(`/alerts${suffix ? `?${suffix}` : ""}`)
}

export async function acknowledgeAlert(alertId: string): Promise<AlertAcknowledgeResponse> {
  const res = await fetch(`${API_BASE}/alerts/${encodeURIComponent(alertId)}/acknowledge`, {
    method: "PATCH",
  })
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(`API ${res.status}: ${text || res.statusText}`)
  }
  return res.json() as Promise<AlertAcknowledgeResponse>
}

export async function unacknowledgeAlert(alertId: string): Promise<AlertAcknowledgeResponse> {
  const res = await fetch(`${API_BASE}/alerts/${encodeURIComponent(alertId)}/unacknowledge`, {
    method: "PATCH",
  })
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(`API ${res.status}: ${text || res.statusText}`)
  }
  return res.json() as Promise<AlertAcknowledgeResponse>
}

export async function fetchHotspots(params?: {
  limit?: number
  period?: string
  periodicity?: "month" | "quarter" | "year"
}): Promise<HotspotsResponse> {
  const query = new URLSearchParams()
  query.set("limit", String(params?.limit ?? 5))
  if (params?.period) query.set("period", params.period)
  if (params?.periodicity) query.set("periodicity", params.periodicity)
  return fetchJson<HotspotsResponse>(`/hotspots/top?${query.toString()}`)
}

// --- Reports ---

export type ReportPeriodicity = "month" | "quarter" | "year"

export interface ReportItem {
  id: string
  title: string
  region: string
  region_label: string
  period: string
  periodicity: ReportPeriodicity
  period_label: string
  generated_at: string
  file_name: string
  size_bytes: number
}

export interface ReportsResponse {
  total: number
  reports: ReportItem[]
}

export interface ReportGenerateRequest {
  region: string
  period: string
  periodicity: ReportPeriodicity
}

export async function fetchReports(): Promise<ReportsResponse> {
  return fetchJson<ReportsResponse>("/reports")
}

export async function generateReport(req: ReportGenerateRequest): Promise<ReportItem> {
  const res = await fetch(`${API_BASE}/reports/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(`API ${res.status}: ${text || res.statusText}`)
  }
  return res.json() as Promise<ReportItem>
}

export function downloadReportUrl(reportId: string): string {
  return `${API_BASE}/reports/${encodeURIComponent(reportId)}/download`
}

export async function deleteReport(reportId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/reports/${encodeURIComponent(reportId)}`, {
    method: "DELETE",
  })
  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(`API ${res.status}: ${text || res.statusText}`)
  }
}

// --- Heatmap ---

export type HeatmapSeverity = "fatal" | "serious" | "minor"

export interface HeatmapPoint {
  lat: number
  lon: number
  severity: HeatmapSeverity
  datetime: string
  address?: string | null
  district?: string | null
  crash_type?: string | null
  dead: number
  injured: number
}

export interface HeatmapResponse {
  total: number
  period_label: string
  period_months: number
  points: HeatmapPoint[]
}

export async function fetchHeatmap(params?: {
  period?: string
  periodicity?: ReportPeriodicity
  limit?: number
}): Promise<HeatmapResponse> {
  const query = new URLSearchParams()
  if (params?.period) query.set("period", params.period)
  if (params?.periodicity) query.set("periodicity", params.periodicity)
  if (params?.limit) query.set("limit", String(params.limit))
  const suffix = query.toString()
  return fetchJson<HeatmapResponse>(`/heatmap${suffix ? `?${suffix}` : ""}`)
}
