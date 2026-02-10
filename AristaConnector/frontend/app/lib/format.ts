import clsx from 'clsx'

export const POLLING_INTERVAL_MS = 10_000
export const DEFAULT_FETCH_TIMEOUT_MS = 8_000

export function cn(...inputs: Array<string | false | null | undefined>) {
  return clsx(inputs)
}

export function formatDateTime(value: string | null | undefined) {
  if (!value) return 'N/A'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'N/A'
  return date.toLocaleString('zh-TW')
}

export function formatRelativeTime(value: string | null | undefined) {
  if (!value) return '尚無資料'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return 'N/A'
  const now = Date.now()
  const diffSeconds = Math.floor((now - date.getTime()) / 1000)
  if (diffSeconds < 0) return formatDateTime(value)
  if (diffSeconds < 60) return `${diffSeconds} 秒前`
  if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)} 分鐘前`
  if (diffSeconds < 86_400) return `${Math.floor(diffSeconds / 3600)} 小時前`
  return formatDateTime(value)
}

export function formatLatency(value: number | null | undefined) {
  if (value === null || value === undefined) return 'N/A'
  return `${value.toFixed(2)} ms`
}

export function formatEventsPerHour(value: number | null | undefined) {
  if (value === null || value === undefined) return 'N/A'
  return `${value}/hr`
}

export function formatEventsPer10Seconds(value: number | null | undefined) {
  if (value === null || value === undefined) return 'N/A'
  return `${(value / 360).toFixed(1)}`
}

export function statusLabel(status: string) {
  switch (status) {
    case 'online':
      return '在線'
    case 'degraded':
      return '降級'
    case 'offline':
      return '離線'
    case 'ip_conflict':
      return 'IP 衝突'
    default:
      return '未知'
  }
}

export function normalizeStatus(status: string | null | undefined) {
  if (status === 'online' || status === 'degraded' || status === 'offline' || status === 'ip_conflict') return status
  return 'unknown'
}

export function toNumber(value: string | null | undefined, fallback: number) {
  if (!value) return fallback
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) return fallback
  return parsed
}

export function clampNumber(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value))
}

export function queryStringFromRecord(record: Record<string, string | number | undefined>) {
  const params = new URLSearchParams()
  Object.entries(record).forEach(([key, value]) => {
    if (value === undefined || value === '') return
    params.set(key, String(value))
  })
  return params.toString()
}

export function buildFileTimestamp(date = new Date()) {
  const year = String(date.getFullYear())
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  const second = String(date.getSeconds()).padStart(2, '0')
  return `${year}${month}${day}-${hour}${minute}${second}`
}
