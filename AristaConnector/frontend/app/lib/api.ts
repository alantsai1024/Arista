import {
  DEFAULT_FETCH_TIMEOUT_MS,
  normalizeStatus,
} from './format'
import type {
  ConnectionTestResponse,
  Device,
  DeviceCreatePayload,
  DeviceListRow,
  DeviceStatus,
  DeviceUpdatePayload,
  EventResponse,
  FleetHealth,
} from './types'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export class ApiError extends Error {
  status: number | null

  constructor(message: string, status: number | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

function withTimeout(timeoutMs: number) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)
  return { controller, timeout }
}

async function parseError(response: Response) {
  try {
    const payload = await response.json()
    if (typeof payload?.detail === 'string') return payload.detail
  } catch {
    // no-op
  }
  return `${response.status} ${response.statusText}`
}

export async function fetchJson<T>(path: string, init: RequestInit = {}, timeoutMs = DEFAULT_FETCH_TIMEOUT_MS): Promise<T> {
  const { controller, timeout } = withTimeout(timeoutMs)
  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(init.headers ?? {}),
      },
    })
    if (!response.ok) {
      const message = await parseError(response)
      throw new ApiError(message, response.status)
    }
    return await response.json() as T
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError(`請求逾時（>${timeoutMs}ms）`, null)
    }
    if (error instanceof ApiError) {
      throw error
    }
    if (error instanceof Error) {
      throw new ApiError(error.message, null)
    }
    throw new ApiError('未知錯誤', null)
  } finally {
    clearTimeout(timeout)
  }
}

export async function listDevices() {
  return fetchJson<Device[]>('/devices')
}

export async function getDevice(deviceId: string) {
  return fetchJson<Device>(`/devices/${deviceId}`)
}

export async function createDevice(payload: DeviceCreatePayload) {
  return fetchJson<Device>('/devices', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function updateDevice(deviceId: string, payload: DeviceUpdatePayload) {
  return fetchJson<Device>(`/devices/${deviceId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export async function deleteDevice(deviceId: string) {
  const { controller, timeout } = withTimeout(DEFAULT_FETCH_TIMEOUT_MS)
  try {
    const response = await fetch(`${API_URL}/devices/${deviceId}`, {
      method: 'DELETE',
      signal: controller.signal,
    })
    if (!response.ok) {
      const message = await parseError(response)
      throw new ApiError(message, response.status)
    }
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof Error) throw new ApiError(error.message, null)
    throw new ApiError('刪除設備失敗', null)
  } finally {
    clearTimeout(timeout)
  }
}

export async function testDeviceConnection(deviceId: string) {
  return fetchJson<ConnectionTestResponse>(`/devices/${deviceId}/test-connection`, {
    method: 'POST',
  })
}

export async function getDeviceStatus(deviceId: string) {
  return fetchJson<DeviceStatus>(`/devices/${deviceId}/status`)
}

export async function getDeviceEvents(deviceId: string, limit = 100) {
  return fetchJson<EventResponse[]>(`/devices/${deviceId}/events?limit=${limit}`)
}

export async function getFleetHealth() {
  return fetchJson<FleetHealth>('/health/fleet')
}

export async function getFleetSnapshot() {
  const warnings: string[] = []
  const [devicesResult, healthResult] = await Promise.allSettled([listDevices(), getFleetHealth()])

  const devices = devicesResult.status === 'fulfilled' ? devicesResult.value : null
  const health = healthResult.status === 'fulfilled' ? healthResult.value : null

  if (devicesResult.status === 'rejected') warnings.push(`/devices 讀取失敗：${devicesResult.reason.message ?? '未知錯誤'}`)
  if (healthResult.status === 'rejected') warnings.push(`/health/fleet 讀取失敗：${healthResult.reason.message ?? '未知錯誤'}`)

  if (!devices && !health) {
    throw new ApiError('目前無法取得機群資料')
  }

  return { devices, health, warnings }
}

export function mergeDeviceRows(devices: Device[], statuses: DeviceStatus[]): DeviceListRow[] {
  const statusMap = new Map(statuses.map((status) => [status.device_id, status]))
  return devices.map((device) => {
    const status = statusMap.get(device.id)
    const recent = status?.recent_stats
    return {
      id: device.id,
      hostname: device.hostname,
      ip: device.ip,
      port: device.port,
      username: device.username,
      intervalSec: device.interval_sec,
      enabled: device.enabled,
      status: normalizeStatus(status?.status),
      online: status?.online ?? false,
      lastSeen: status?.last_seen ?? null,
      latencyMs: recent?.latency_ms ?? null,
      eventsLastHour: recent?.total_events_last_hour ?? 0,
      eventsByType: recent?.events_by_type ?? {},
      lastEventAt: recent?.last_event_at ?? null,
    }
  })
}

