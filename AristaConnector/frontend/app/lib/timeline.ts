import type { EventResponse, TimelineEvent, TimelineRange, TimelineSeverity } from './types'

const HIGH_RISK_EVENT_TYPES = new Set(['poll_error', 'device_offline'])
const WARNING_EVENT_TYPES = new Set(['degraded'])
const CHAIN_THRESHOLD_MS = 120_000

function parseMetadata(metadata: unknown) {
  if (!metadata) return null
  if (typeof metadata === 'object') return metadata as Record<string, unknown>
  if (typeof metadata === 'string') {
    try {
      const parsed = JSON.parse(metadata)
      if (parsed && typeof parsed === 'object') return parsed as Record<string, unknown>
      return { raw: metadata }
    } catch {
      return { raw: metadata }
    }
  }
  return { raw: metadata }
}

export function severityFromEventType(eventType: string): TimelineSeverity {
  if (HIGH_RISK_EVENT_TYPES.has(eventType)) return 'critical'
  if (WARNING_EVENT_TYPES.has(eventType)) return 'warning'
  return 'info'
}

export function buildTimelineEvents(events: EventResponse[]) {
  const sorted = [...events].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
  let lastEventType = ''
  let lastTimestamp = 0
  let activeChainId = ''
  let chainNumber = 0
  let chainIndex = 0

  return sorted.map((event) => {
    const ts = new Date(event.created_at).getTime()
    if (
      event.event_type === lastEventType
      && activeChainId
      && ts - lastTimestamp <= CHAIN_THRESHOLD_MS
    ) {
      chainIndex += 1
    } else {
      chainNumber += 1
      chainIndex = 0
      activeChainId = `chain-${chainNumber}`
    }

    lastEventType = event.event_type
    lastTimestamp = ts

    return {
      ...event,
      metadataObject: parseMetadata(event.metadata),
      severity: severityFromEventType(event.event_type),
      chainGroupId: activeChainId,
      chainIndex,
    } satisfies TimelineEvent
  })
}

export function filterTimelineEvents(events: TimelineEvent[], range: TimelineRange, eventType: string) {
  const now = Date.now()
  let threshold = 0
  if (range === '1h') threshold = now - 3_600_000
  if (range === '6h') threshold = now - 21_600_000
  if (range === '24h') threshold = now - 86_400_000

  return events.filter((event) => {
    if (eventType !== 'all' && event.event_type !== eventType) return false
    if (range === 'all') return true
    return new Date(event.created_at).getTime() >= threshold
  })
}

export function countEventsByType(events: TimelineEvent[]) {
  return events.reduce<Record<string, number>>((acc, event) => {
    acc[event.event_type] = (acc[event.event_type] ?? 0) + 1
    return acc
  }, {})
}

export function buildTimeBuckets(events: TimelineEvent[], bucketMinutes = 10) {
  const buckets = new Map<number, { total: number; critical: number }>()
  const bucketMs = bucketMinutes * 60_000

  events.forEach((event) => {
    const ts = new Date(event.created_at).getTime()
    const bucketTime = Math.floor(ts / bucketMs) * bucketMs
    const current = buckets.get(bucketTime) ?? { total: 0, critical: 0 }
    current.total += 1
    if (event.severity === 'critical') current.critical += 1
    buckets.set(bucketTime, current)
  })

  return Array.from(buckets.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([bucket, counts]) => ({
      time: new Date(bucket).toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit', hour12: false }),
      total: counts.total,
      critical: counts.critical,
    }))
}
