"use client"

import { useEffect, useRef } from "react"
import L from "leaflet"
import "leaflet/dist/leaflet.css"
import "leaflet.heat"
import type { HeatmapPoint, HeatmapSeverity, HotspotItem } from "@/lib/api"

const SEVERITY_STYLE: Record<HeatmapSeverity, { fill: string; stroke: string; radius: number; opacity: number }> = {
  fatal:   { fill: "#ef4444", stroke: "#b91c1c", radius: 7, opacity: 0.85 },
  serious: { fill: "#f97316", stroke: "#c2410c", radius: 6, opacity: 0.75 },
  minor:   { fill: "#3b82f6", stroke: "#1e40af", radius: 5, opacity: 0.55 },
}

const SEVERITY_WEIGHT: Record<HeatmapSeverity, number> = {
  fatal: 1.0,
  serious: 0.6,
  minor: 0.3,
}

interface InteractiveMapProps {
  center: [number, number]
  zoom: number
  points: HeatmapPoint[]
  showMarkers: boolean
  showHeat: boolean
  hotspots?: HotspotItem[]                   // top-N очаги поверх heat/scatter
  hotspotsPeriodLabel?: string               // период по которому посчитан очаг
  flyTo?: { lat: number; lon: number; zoom?: number; key: string } | null
  fullscreen?: boolean
}

delete (L.Icon.Default.prototype as { _getIconUrl?: unknown })._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
})

type HeatLayer = L.Layer & { setLatLngs: (latlngs: Array<[number, number, number]>) => void }
type LeafletWithHeat = typeof L & {
  heatLayer: (latlngs: Array<[number, number, number]>, options?: Record<string, unknown>) => HeatLayer
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (ch) => {
    switch (ch) {
      case "&": return "&amp;"
      case "<": return "&lt;"
      case ">": return "&gt;"
      case '"': return "&quot;"
      case "'": return "&#39;"
      default: return ch
    }
  })
}

const SEVERITY_LABEL: Record<HeatmapSeverity, string> = {
  fatal: "С погибшими",
  serious: "Тяжёлый",
  minor: "Лёгкий",
}

function formatDateTime(iso: string): string {
  // 'YYYY-MM-DD HH:MM:SS' → 'DD.MM.YYYY HH:MM'
  const [date, time = ""] = iso.split(" ")
  const [y, m, d] = date.split("-")
  const hm = time.slice(0, 5)
  return `${d}.${m}.${y}${hm ? " " + hm : ""}`
}

function buildScatterPopup(p: HeatmapPoint): string {
  const sev = SEVERITY_LABEL[p.severity]
  const sevColor = SEVERITY_STYLE[p.severity].fill
  const place = p.address || p.district || "—"
  const type = p.crash_type ? escapeHtml(p.crash_type) : "—"
  // K_T (формула 2.3 ВКР) для одной аварии: killed/(killed+injured)*100.
  // Если жертв нет вообще → прочерк.
  const total = p.dead + p.injured
  const kT = total > 0 ? ((p.dead / total) * 100).toFixed(2) : "—"
  // Статус для одной аварии: «С погибшими» если dead>0, иначе «Без погибших»
  const isFatal = p.dead > 0
  const statusLabel = isFatal ? "С погибшими" : "Без погибших"
  const statusColor = isFatal ? "#b91c1c" : "#a16207"
  return `
    <div style="min-width: 230px;">
      <div style="display:flex; align-items:center; gap:6px; margin-bottom:6px;">
        <span style="display:inline-block; width:10px; height:10px; border-radius:50%; background:${sevColor};"></span>
        <strong style="font-size:13px;">${sev}</strong>
      </div>
      <p style="margin: 2px 0; font-size: 12px;"><strong>${formatDateTime(p.datetime)}</strong></p>
      <p style="margin: 2px 0; font-size: 12px;">${escapeHtml(place)}</p>
      <p style="margin: 2px 0; font-size: 12px;">Тип: ${type}</p>
      <p style="margin: 2px 0; font-size: 12px;">Погибло: <strong>${p.dead}</strong>, ранено: <strong>${p.injured}</strong></p>
      <p style="margin: 2px 0; font-size: 12px;">К. тяжести: <strong>${kT}</strong></p>
      <p style="margin: 4px 0 0; font-size: 12px;">Статус: <strong style="color:${statusColor};">${statusLabel}</strong></p>
    </div>
  `
}

export function InteractiveMap({
  center,
  zoom,
  points,
  showMarkers,
  showHeat,
  hotspots = [],
  hotspotsPeriodLabel = "",
  flyTo = null,
  fullscreen,
}: InteractiveMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const markersLayerRef = useRef<L.LayerGroup | null>(null)
  const heatLayerRef = useRef<HeatLayer | null>(null)
  const hotspotLayerRef = useRef<L.LayerGroup | null>(null)
  const hotspotMarkersRef = useRef<Map<number, L.Marker>>(new Map())

  // preferCanvas НЕ ставим — scatter-точки рендерятся как SVG-кружки,
  // тогда у них нормально меняется курсор на pointer и надёжно ловятся
  // клики (canvas-renderer этого не даёт). Heat-layer всё равно использует
  // свой canvas независимо от настройки.
  useEffect(() => {
    if (map.current || !mapContainer.current) return
    map.current = L.map(mapContainer.current).setView(center, zoom)
    map.current.attributionControl.setPrefix(
      '<a href="https://leafletjs.com/" target="_blank" rel="noopener">Leaflet</a>'
    )
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map.current)
  }, [center, zoom])

  // Scatter (per-DTP markers).
  useEffect(() => {
    if (!map.current) return
    if (markersLayerRef.current) {
      markersLayerRef.current.clearLayers()
      markersLayerRef.current.remove()
      markersLayerRef.current = null
    }
    if (!showMarkers || points.length === 0) return

    const layer = L.layerGroup()
    for (const p of points) {
      const style = SEVERITY_STYLE[p.severity]
      const marker = L.circleMarker([p.lat, p.lon], {
        radius: style.radius,
        fillColor: style.fill,
        color: style.stroke,
        weight: 1,
        fillOpacity: style.opacity,
        opacity: style.opacity,
      })
      marker.bindPopup(buildScatterPopup(p), { minWidth: 220 })
      marker.addTo(layer)
    }
    layer.addTo(map.current)
    markersLayerRef.current = layer
  }, [points, showMarkers])

  // Heat layer.
  useEffect(() => {
    if (!map.current) return
    if (heatLayerRef.current) {
      heatLayerRef.current.remove()
      heatLayerRef.current = null
    }
    if (!showHeat || points.length === 0) return

    const latlngs: Array<[number, number, number]> = points.map((p) => [
      p.lat,
      p.lon,
      SEVERITY_WEIGHT[p.severity],
    ])
    const heat = (L as LeafletWithHeat).heatLayer(latlngs, {
      radius: 22,
      blur: 18,
      maxZoom: 14,
      max: 1.0,
      minOpacity: 0.35,
      gradient: {
        0.2: "#3b82f6",
        0.4: "#22c55e",
        0.6: "#eab308",
        0.8: "#f97316",
        1.0: "#ef4444",
      },
    })
    heat.addTo(map.current)
    heatLayerRef.current = heat
  }, [points, showHeat])

  // Hotspot markers (top-5 with popup) — рисуются поверх heat/scatter.
  useEffect(() => {
    if (!map.current) return
    hotspotMarkersRef.current.clear()
    if (hotspotLayerRef.current) {
      hotspotLayerRef.current.clearLayers()
      hotspotLayerRef.current.remove()
      hotspotLayerRef.current = null
    }
    if (hotspots.length === 0) return

    const layer = L.layerGroup()
    for (const h of hotspots) {
      const isActive = h.status === "active"
      const html = `
        <div style="
          display: flex;
          align-items: center;
          justify-content: center;
          width: 32px;
          height: 32px;
          border-radius: 50%;
          background-color: ${isActive ? "rgb(239, 68, 68)" : "rgb(234, 179, 8)"};
          border: 2px solid white;
          box-shadow: 0 4px 6px rgba(0, 0, 0, 0.35);
          font-weight: bold;
          color: white;
          font-size: 12px;
        ">${h.rank}</div>
      `
      const icon = L.divIcon({
        html,
        className: "",
        iconSize: [32, 32],
        iconAnchor: [16, 16],
        popupAnchor: [0, -16],
      })
      const marker = L.marker([h.lat, h.lon], { icon, title: h.name })
      const dominantType = h.dominant_type ? escapeHtml(h.dominant_type) : "—"
      const periodLine = hotspotsPeriodLabel
        ? `<p style="margin: 2px 0; font-size: 12px; color:#555;">Период: <strong>${escapeHtml(hotspotsPeriodLabel)}</strong></p>`
        : ""
      marker.bindPopup(`
        <div style="min-width: 240px;">
          <h4 style="font-weight: bold; margin: 0 0 4px;">${escapeHtml(h.name)}</h4>
          <p style="margin: 2px 0; font-size: 12px;">№ <strong>${h.rank}</strong> из ${hotspots.length} очагов аварийности</p>
          ${periodLine}
          <p style="margin: 2px 0; font-size: 12px;">Преобладающий тип: <strong>${dominantType}</strong></p>
          <p style="margin: 2px 0; font-size: 12px;">ДТП: <strong>${h.accidents_count}</strong></p>
          <p style="margin: 2px 0; font-size: 12px;">Погибло: <strong>${h.killed}</strong>, ранено: <strong>${h.injured}</strong></p>
          <p style="margin: 2px 0; font-size: 12px;">К. тяжести: <strong>${h.severity_coef.toFixed(2)}</strong></p>
          <p style="margin: 2px 0; font-size: 12px;">ДТП/мес: <strong>${h.frequency.toFixed(2)}</strong></p>
          <p style="margin: 2px 0; font-size: 12px;">Частота на км сети: <strong>${h.frequency_per_km.toFixed(4)}</strong> ДТП/км</p>
          <p style="margin: 4px 0 0; font-size: 12px;">Статус: <strong style="color: ${isActive ? "#b91c1c" : "#a16207"};">${isActive ? "Активен" : "Потенциальный"}</strong></p>
        </div>
      `)
      marker.addTo(layer)
      hotspotMarkersRef.current.set(h.rank, marker)
    }
    layer.addTo(map.current)
    hotspotLayerRef.current = layer
  }, [hotspots, hotspotsPeriodLabel])

  // Fly-to + open popup при изменении flyTo.key (используем key чтобы повторный
  // клик по той же строке снова центрировал карту).
  useEffect(() => {
    if (!map.current || !flyTo) return
    const targetZoom = flyTo.zoom ?? 15
    map.current.flyTo([flyTo.lat, flyTo.lon], targetZoom, { duration: 0.8 })
    // Если есть маркер очага в этой точке — открыть popup
    for (const marker of hotspotMarkersRef.current.values()) {
      const pos = marker.getLatLng()
      if (Math.abs(pos.lat - flyTo.lat) < 1e-5 && Math.abs(pos.lng - flyTo.lon) < 1e-5) {
        marker.openPopup()
        break
      }
    }
  }, [flyTo])

  // Перерасчёт размеров при смене контейнера (fullscreen toggle).
  useEffect(() => {
    if (!map.current) return
    const id = requestAnimationFrame(() => map.current?.invalidateSize())
    return () => cancelAnimationFrame(id)
  }, [fullscreen])

  return (
    <div
      ref={mapContainer}
      style={{ width: "100%", height: "100%", backgroundColor: "#1a1a2e" }}
    />
  )
}
