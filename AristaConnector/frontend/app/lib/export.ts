import type { DeviceListRow, ExportPayload, TimelineEvent } from './types'
import { buildFileTimestamp, formatDateTime, formatLatency, statusLabel } from './format'

interface PdfRuntime {
  jsPDF: (typeof import('jspdf'))['default']
  autoTable: (typeof import('jspdf-autotable'))['default']
}

let cachedPdfRuntime: Promise<PdfRuntime> | null = null

function loadPdfRuntime() {
  if (!cachedPdfRuntime) {
    cachedPdfRuntime = Promise.all([
      import('jspdf'),
      import('jspdf-autotable'),
    ]).then(([jspdfModule, autoTableModule]) => ({
      jsPDF: jspdfModule.default,
      autoTable: autoTableModule.default,
    }))
  }
  return cachedPdfRuntime
}

function triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

function toCsv(rows: Array<Record<string, unknown>>) {
  if (rows.length === 0) return ''
  const headers = Object.keys(rows[0])
  const lines = [
    headers.join(','),
    ...rows.map((row) => headers.map((header) => {
      const value = row[header]
      const text = value === undefined || value === null ? '' : String(value)
      const escaped = text.replace(/"/g, '""')
      return `"${escaped}"`
    }).join(',')),
  ]
  return lines.join('\n')
}

function downloadJson(payload: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], {
    type: 'application/json;charset=utf-8',
  })
  triggerDownload(blob, filename)
}

function downloadCsv(csv: string, filename: string) {
  const blob = new Blob([`\uFEFF${csv}`], { type: 'text/csv;charset=utf-8' })
  triggerDownload(blob, filename)
}

export function exportDevicesCsv(rows: DeviceListRow[]) {
  const mapped = rows.map((row) => ({
    hostname: row.hostname ?? '',
    ip: row.ip,
    status: row.status,
    enabled: row.enabled ? 'true' : 'false',
    latency_ms: row.latencyMs ?? '',
    events_last_hour: row.eventsLastHour,
    interval_sec: row.intervalSec,
    last_seen: row.lastSeen ?? '',
  }))
  const filename = `arista-devices-${buildFileTimestamp()}.csv`
  downloadCsv(toCsv(mapped), filename)
}

export function exportDevicesJson(rows: DeviceListRow[]) {
  const payload: ExportPayload<DeviceListRow> = {
    scope: 'devices',
    generatedAt: new Date().toISOString(),
    rows,
  }
  const filename = `arista-devices-${buildFileTimestamp()}.json`
  downloadJson(payload, filename)
}

export async function exportDevicesPdf(rows: DeviceListRow[]) {
  const { jsPDF, autoTable } = await loadPdfRuntime()
  const doc = new jsPDF({ orientation: 'landscape' })
  doc.setFontSize(16)
  doc.text('Arista Devices Report', 14, 16)
  doc.setFontSize(10)
  doc.text(`Generated at: ${new Date().toLocaleString('zh-TW')}`, 14, 22)

  autoTable(doc, {
    startY: 28,
    head: [['Hostname', 'IP', 'Status', 'Enabled', 'Latency', 'Events/hr', 'Interval', 'Last Seen']],
    body: rows.map((row) => [
      row.hostname ?? '',
      row.ip,
      row.status,
      row.enabled ? 'true' : 'false',
      formatLatency(row.latencyMs),
      String(row.eventsLastHour),
      `${row.intervalSec}s`,
      formatDateTime(row.lastSeen),
    ]),
    styles: { fontSize: 9, cellPadding: 2.5 },
    headStyles: { fillColor: [15, 67, 133], textColor: [255, 255, 255] },
  })

  doc.save(`arista-devices-${buildFileTimestamp()}.pdf`)
}

export function exportEventsCsv(deviceLabel: string, events: TimelineEvent[]) {
  const mapped = events.map((event) => ({
    created_at: event.created_at,
    event_type: event.event_type,
    severity: event.severity,
    chain_group_id: event.chainGroupId,
    chain_index: event.chainIndex,
    message: event.message ?? '',
    metadata: JSON.stringify(event.metadataObject ?? {}),
  }))
  downloadCsv(toCsv(mapped), `arista-${deviceLabel}-events-${buildFileTimestamp()}.csv`)
}

export function exportEventsJson(deviceLabel: string, events: TimelineEvent[]) {
  const payload: ExportPayload<TimelineEvent> = {
    scope: `device-events:${deviceLabel}`,
    generatedAt: new Date().toISOString(),
    rows: events,
  }
  downloadJson(payload, `arista-${deviceLabel}-events-${buildFileTimestamp()}.json`)
}

export async function exportEventsPdf(deviceLabel: string, events: TimelineEvent[]) {
  const { jsPDF, autoTable } = await loadPdfRuntime()
  const doc = new jsPDF()
  doc.setFontSize(16)
  doc.text(`Device Events - ${deviceLabel}`, 14, 16)
  doc.setFontSize(10)
  doc.text(`Generated at: ${new Date().toLocaleString('zh-TW')}`, 14, 22)
  autoTable(doc, {
    startY: 28,
    head: [['Time', 'Type', 'Severity', 'Chain', 'Message']],
    body: events.map((event) => [
      formatDateTime(event.created_at),
      event.event_type,
      event.severity,
      `${event.chainGroupId} #${event.chainIndex}`,
      event.message ?? '',
    ]),
    styles: { fontSize: 8, cellPadding: 2.3 },
    headStyles: { fillColor: [15, 67, 133], textColor: [255, 255, 255] },
  })

  const summaryY = ((doc as unknown as { lastAutoTable?: { finalY?: number } }).lastAutoTable?.finalY ?? 36) + 10
  doc.setFontSize(10)
  doc.text(`Total events: ${events.length}`, 14, summaryY)
  doc.text(
    `Critical events: ${events.filter((event) => event.severity === 'critical').length}`,
    14,
    summaryY + 6,
  )
  doc.save(`arista-${deviceLabel}-events-${buildFileTimestamp()}.pdf`)
}

export async function exportFleetSnapshotPdf(summary: {
  total: number
  online: number
  degraded: number
  offline: number
}, anomalies: DeviceListRow[]) {
  const { jsPDF, autoTable } = await loadPdfRuntime()
  const doc = new jsPDF({ orientation: 'landscape' })
  doc.setFontSize(16)
  doc.text('Fleet Summary Report', 14, 16)
  doc.setFontSize(10)
  doc.text(`Generated at: ${new Date().toLocaleString('zh-TW')}`, 14, 22)
  doc.text(`Total: ${summary.total}`, 14, 30)
  doc.text(`Online: ${summary.online}`, 50, 30)
  doc.text(`Degraded: ${summary.degraded}`, 88, 30)
  doc.text(`Offline: ${summary.offline}`, 132, 30)

  autoTable(doc, {
    startY: 36,
    head: [['Hostname', 'IP', 'Status', 'Latency', 'Last Seen']],
    body: anomalies.map((row) => [
      row.hostname ?? '',
      row.ip,
      statusLabel(row.status),
      formatLatency(row.latencyMs),
      formatDateTime(row.lastSeen),
    ]),
    styles: { fontSize: 9 },
    headStyles: { fillColor: [15, 67, 133], textColor: [255, 255, 255] },
  })

  doc.save(`arista-fleet-${buildFileTimestamp()}.pdf`)
}
