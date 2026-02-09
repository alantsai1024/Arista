'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams, usePathname, useRouter, useSearchParams } from 'next/navigation'
import { Download, RefreshCw } from 'lucide-react'
import { getDevice, getDeviceEvents, getDeviceStatus } from '@/app/lib/api'
import { POLLING_INTERVAL_MS, formatDateTime, formatLatency, queryStringFromRecord } from '@/app/lib/format'
import type { Device, DeviceStatus, TimelineEvent, TimelineRange } from '@/app/lib/types'
import { buildTimeBuckets, buildTimelineEvents, countEventsByType, filterTimelineEvents } from '@/app/lib/timeline'
import EventTypePieChart from '@/app/components/charts/EventTypePieChart'
import EventVolumeChart from '@/app/components/charts/EventVolumeChart'
import EventTimeline from '@/app/components/timeline/EventTimeline'
import MetadataDrawer from '@/app/components/timeline/MetadataDrawer'
import InlineAlert from '@/app/components/feedback/InlineAlert'
import StatusBadge from '@/app/components/ui/StatusBadge'
import { useToast } from '@/app/components/feedback/ToastProvider'
import { exportEventsCsv, exportEventsJson, exportEventsPdf } from '@/app/lib/export'

const BACKGROUND_POLLING_INTERVAL_MS = 30_000
const EVENT_FETCH_LIMIT = 50

function asRange(value: string | null): TimelineRange {
  if (value === '1h' || value === '6h' || value === '24h' || value === 'all') return value
  return '24h'
}

function fileFriendlyLabel(input: string) {
  return input.replace(/[^a-zA-Z0-9-_]/g, '_')
}

interface WarningMap {
  device?: string
  status?: string
  events?: string
}

interface FetchOptions {
  includeDevice: boolean
  notifyOnError: boolean
  showRefreshing: boolean
}

export default function DeviceDetailPage() {
  const params = useParams()
  const deviceId = params.id as string
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const router = useRouter()
  const { pushToast } = useToast()

  const range = asRange(searchParams.get('range'))
  const type = searchParams.get('type') || 'all'

  const [device, setDevice] = useState<Device | null>(null)
  const [status, setStatus] = useState<DeviceStatus | null>(null)
  const [timeline, setTimeline] = useState<TimelineEvent[]>([])
  const [selectedEvent, setSelectedEvent] = useState<TimelineEvent | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [warningsBySource, setWarningsBySource] = useState<WarningMap>({})

  const fetchInFlightRef = useRef(false)

  const setWarning = useCallback((key: keyof WarningMap, value: string | null) => {
    setWarningsBySource((prev) => {
      const next = { ...prev }
      if (value) next[key] = value
      else delete next[key]
      return next
    })
  }, [])

  const getPollingDelay = useCallback(() => (
    typeof document !== 'undefined' && document.hidden
      ? BACKGROUND_POLLING_INTERVAL_MS
      : POLLING_INTERVAL_MS
  ), [])

  function updateQuery(next: Record<string, string | undefined>) {
    const merged = Object.fromEntries(searchParams.entries()) as Record<string, string>
    Object.entries(next).forEach(([key, value]) => {
      if (!value || value === 'all') {
        delete merged[key]
      } else {
        merged[key] = value
      }
    })
    const query = queryStringFromRecord(merged)
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false })
  }

  const fetchData = useCallback(async (options: FetchOptions) => {
    if (fetchInFlightRef.current) return
    fetchInFlightRef.current = true

    if (options.showRefreshing) setRefreshing(true)

    try {
      const [deviceRes, statusRes, eventsRes] = await Promise.allSettled([
        options.includeDevice ? getDevice(deviceId) : Promise.resolve(null),
        getDeviceStatus(deviceId),
        getDeviceEvents(deviceId, EVENT_FETCH_LIMIT),
      ])

      const issues: string[] = []

      if (options.includeDevice) {
        if (deviceRes.status === 'fulfilled' && deviceRes.value) {
          setDevice(deviceRes.value)
          setWarning('device', null)
        } else if (deviceRes.status === 'rejected') {
          const message = deviceRes.reason?.message ?? '未知錯誤'
          const issue = `設備資料失敗：${message}`
          issues.push(issue)
          setWarning('device', issue)
        }
      }

      if (statusRes.status === 'fulfilled') {
        setStatus(statusRes.value)
        setWarning('status', null)
      } else {
        const message = statusRes.reason?.message ?? '未知錯誤'
        const issue = `狀態資料失敗：${message}`
        issues.push(issue)
        setWarning('status', issue)
      }

      if (eventsRes.status === 'fulfilled') {
        setTimeline(buildTimelineEvents(eventsRes.value))
        setWarning('events', null)
      } else {
        const message = eventsRes.reason?.message ?? '未知錯誤'
        const issue = `事件資料失敗：${message}`
        issues.push(issue)
        setWarning('events', issue)
      }

      if (issues.length > 0 && options.notifyOnError) {
        pushToast({
          type: 'error',
          title: '設備資料載入有部分失敗',
          description: issues.join(' | '),
        })
      }
    } finally {
      fetchInFlightRef.current = false
      setLoading(false)
      if (options.showRefreshing) setRefreshing(false)
    }
  }, [deviceId, pushToast, setWarning])

  useEffect(() => {
    setLoading(true)
    setStatus(null)
    setTimeline([])
    setSelectedEvent(null)
    setWarningsBySource({})

    void fetchData({
      includeDevice: true,
      notifyOnError: true,
      showRefreshing: true,
    })
  }, [deviceId, fetchData])

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | null = null

    const scheduleNext = (delay: number) => {
      if (cancelled) return
      timer = setTimeout(() => {
        void run()
      }, delay)
    }

    const run = async () => {
      if (cancelled) return

      await fetchData({
        includeDevice: false,
        notifyOnError: false,
        showRefreshing: false,
      })

      scheduleNext(getPollingDelay())
    }

    const handleVisibilityChange = () => {
      if (timer) clearTimeout(timer)
      scheduleNext(getPollingDelay())
    }

    scheduleNext(getPollingDelay())
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [fetchData, getPollingDelay])

  const warnings = useMemo(
    () => Object.values(warningsBySource).filter((warning): warning is string => Boolean(warning)),
    [warningsBySource],
  )

  const filteredTimeline = useMemo(
    () => filterTimelineEvents(timeline, range, type),
    [timeline, range, type],
  )
  const eventTypeStats = useMemo(() => countEventsByType(filteredTimeline), [filteredTimeline])
  const bucketData = useMemo(() => buildTimeBuckets(filteredTimeline, 10), [filteredTimeline])
  const eventTypes = useMemo(
    () => ['all', ...Array.from(new Set(timeline.map((event) => event.event_type)))],
    [timeline],
  )
  const deviceLabel = fileFriendlyLabel(device?.hostname || device?.ip || deviceId)

  if (loading) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <section className="card-surface flex min-h-[300px] items-center justify-center">
          <p className="text-sm text-slate-600">載入設備詳情中...</p>
        </section>
      </main>
    )
  }

  if (!device) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <section className="card-surface p-6 text-sm text-rose-700">找不到設備資料或設備已刪除。</section>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-7xl space-y-5 px-4 py-7 sm:px-6 lg:px-8">
      <section className="card-surface p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <button
              type="button"
              className="mb-3 rounded-xl border border-slate-300 px-3 py-1 text-xs text-slate-700 hover:bg-slate-50"
              onClick={() => router.push('/devices')}
            >
              返回設備管理
            </button>
            <h1 className="font-display text-3xl font-semibold text-slate-900">{device.hostname || device.ip}</h1>
            <p className="mt-1 text-sm text-slate-600">ID: {device.id}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                exportEventsCsv(deviceLabel, filteredTimeline)
                pushToast({ type: 'success', title: '已匯出 CSV' })
              }}
            >
              <span className="inline-flex items-center gap-1.5"><Download className="h-4 w-4" />CSV</span>
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => {
                exportEventsJson(deviceLabel, filteredTimeline)
                pushToast({ type: 'success', title: '已匯出 JSON' })
              }}
            >
              <span className="inline-flex items-center gap-1.5"><Download className="h-4 w-4" />JSON</span>
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={async () => {
                try {
                  await exportEventsPdf(deviceLabel, filteredTimeline)
                  pushToast({ type: 'success', title: '已匯出 PDF' })
                } catch (error) {
                  const message = error instanceof Error ? error.message : '未知錯誤'
                  pushToast({ type: 'error', title: 'PDF 匯出失敗', description: message })
                }
              }}
            >
              <span className="inline-flex items-center gap-1.5"><Download className="h-4 w-4" />PDF</span>
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => void fetchData({
                includeDevice: true,
                notifyOnError: true,
                showRefreshing: true,
              })}
              disabled={refreshing}
            >
              <span className="inline-flex items-center gap-1.5">
                <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                刷新
              </span>
            </button>
          </div>
        </div>
      </section>

      {warnings.length > 0 && (
        <InlineAlert title="部分資料來源失敗" details={warnings} variant="warning" />
      )}

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-4">
        <article className="card-surface p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">狀態</p>
          <div className="mt-2"><StatusBadge status={status?.status ?? 'unknown'} /></div>
          <p className="mt-2 text-xs text-slate-500">online = {status?.online ? 'true' : 'false'}</p>
        </article>
        <article className="card-surface p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">IP / Port</p>
          <p className="mt-2 text-sm font-semibold text-slate-900">{device.ip}:{device.port}</p>
          <p className="mt-2 text-xs text-slate-500">建立時間：{formatDateTime(device.created_at)}</p>
        </article>
        <article className="card-surface p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Latency</p>
          <p className="mt-2 text-sm font-semibold text-slate-900">{formatLatency(status?.recent_stats?.latency_ms)}</p>
          <p className="mt-2 text-xs text-slate-500">輪詢間隔：{device.interval_sec} 秒</p>
        </article>
        <article className="card-surface p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">事件</p>
          <p className="mt-2 text-sm font-semibold text-slate-900">{status?.recent_stats?.total_events_last_hour ?? 0} / hr</p>
          <p className="mt-2 text-xs text-slate-500">last_seen：{formatDateTime(status?.last_seen ?? null)}</p>
        </article>
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <EventTypePieChart data={eventTypeStats} />
        <EventVolumeChart data={bucketData} />
      </section>

      <section className="card-surface p-4">
        <div className="flex flex-wrap items-end gap-3">
          <label className="field-group">
            <span className="field-label">時間範圍</span>
            <select
              className="field-input"
              value={range}
              onChange={(event) => updateQuery({ range: event.target.value })}
            >
              <option value="1h">最近 1 小時</option>
              <option value="6h">最近 6 小時</option>
              <option value="24h">最近 24 小時</option>
              <option value="all">全部</option>
            </select>
          </label>
          <label className="field-group">
            <span className="field-label">事件類型</span>
            <select
              className="field-input"
              value={type}
              onChange={(event) => updateQuery({ type: event.target.value })}
            >
              {eventTypes.map((eventType) => (
                <option key={eventType} value={eventType}>{eventType === 'all' ? '全部類型' : eventType}</option>
              ))}
            </select>
          </label>
        </div>
      </section>

      <EventTimeline
        events={filteredTimeline}
        activeEventId={selectedEvent?.id ?? null}
        onSelectEvent={setSelectedEvent}
      />

      <MetadataDrawer event={selectedEvent} onClose={() => setSelectedEvent(null)} />
    </main>
  )
}
