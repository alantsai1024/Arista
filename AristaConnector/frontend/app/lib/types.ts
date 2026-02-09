export type DeviceOperationalStatus = 'online' | 'degraded' | 'offline' | 'unknown'
export type TimelineSeverity = 'critical' | 'warning' | 'info'
export type TimelineRange = '1h' | '6h' | '24h' | 'all'

export interface Device {
  id: string
  hostname: string | null
  ip: string
  port: number
  username: string
  interval_sec: number
  enabled: boolean
  created_at: string
  updated_at: string | null
}

export interface DeviceRecentStats {
  total_events_last_hour?: number
  events_by_type?: Record<string, number>
  last_event_at?: string | null
  latency_ms?: number | null
}

export interface DeviceStatus {
  device_id: string
  status: string
  last_seen: string | null
  online: boolean
  recent_stats?: DeviceRecentStats
}

export interface DeviceLatency {
  device_id: string
  hostname: string | null
  ip: string
  latency_ms: number | null
}

export interface FleetHealth {
  total_devices: number
  online_devices: number
  offline_devices: number
  degraded_devices: number
  devices: DeviceStatus[]
  top_latency_devices: DeviceLatency[]
}

export interface EventResponse {
  id: string
  device_id: string
  event_type: string
  message: string | null
  metadata: unknown
  created_at: string
}

export interface TimelineEvent extends EventResponse {
  metadataObject: Record<string, unknown> | null
  severity: TimelineSeverity
  chainGroupId: string
  chainIndex: number
}

export interface DeviceListRow {
  id: string
  hostname: string | null
  ip: string
  port: number
  username: string
  intervalSec: number
  enabled: boolean
  status: DeviceOperationalStatus
  online: boolean
  lastSeen: string | null
  latencyMs: number | null
  eventsLastHour: number
  eventsByType: Record<string, number>
  lastEventAt: string | null
}

export interface ConnectionTestResponse {
  success: boolean
  message: string
  hostname: string | null
}

export interface DeviceCreatePayload {
  hostname?: string | null
  ip: string
  port: number
  username: string
  password: string
  interval_sec: number
  enabled: boolean
}

export interface DeviceUpdatePayload {
  hostname?: string | null
  ip?: string
  port?: number
  username?: string
  password?: string
  interval_sec?: number
  enabled?: boolean
}

export interface ExportPayload<T> {
  scope: string
  generatedAt: string
  rows: T[]
}

