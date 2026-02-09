'use client'

import { useEffect, useMemo, useState } from 'react'
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

function asRange(value: string | null): TimelineRange {
  if (value === '1h' || value === '6h' || value === '24h' || value === 'all') return value
  return '24h'
}

function fileFriendlyLabel(input: string) {
  return input.replace(/[^a-zA-Z0-9-_]/g, '_')
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
  const [warnings, setWarnings] = useState<string[]>([])

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

  async function fetchData() {
    try {
      setRefreshing(true)
      const [deviceRes, statusRes, eventsRes] = await Promise.allSettled([
        getDevice(deviceId),
        getDeviceStatus(deviceId),
        getDeviceEvents(deviceId, 100),
      ])
      const issues: string[] = []

      if (deviceRes.status === 'fulfilled') setDevice(deviceRes.value)
      else issues.push(`設備資料失敗：${deviceRes.reason.message ?? '未知錯誤'}`)

      if (statusRes.status === 'fulfilled') setStatus(statusRes.value)
      else issues.push(`狀態資料失敗：${statusRes.reason.message ?? '未知錯誤'}`)

      if (eventsRes.status === 'fulfilled') {
        setTimeline(buildTimelineEvents(eventsRes.value))
      } else {
        issues.push(`事件資料失敗：${eventsRes.reason.message ?? '未知錯誤'}`)
      }

      setWarnings(issues)
      if (issues.length > 0) {
        pushToast({
          type: 'error',
          title: '設備資料載入有部分失敗',
          description: issues.join(' | '),
        })
      }
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    void fetchData()
    const timer = setInterval(() => {
      void fetchData()
    }, POLLING_INTERVAL_MS)
    return () => clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deviceId])

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
      <section className="card-surface bg-brand-gradient p-6 text-white">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <button
              type="button"
              className="mb-3 rounded-xl border border-white/35 px-3 py-1 text-xs text-white/90 hover:bg-white/15"
              onClick={() => router.push('/devices')}
            >
              返回設備管理
            </button>
            <h1 className="font-display text-3xl font-semibold">{device.hostname || device.ip}</h1>
            <p className="mt-1 text-sm text-white/85">ID: {device.id}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="btn-secondary border-white/40 bg-white/10 text-white hover:bg-white/20"
              onClick={() => {
                exportEventsCsv(deviceLabel, filteredTimeline)
                pushToast({ type: 'success', title: '已匯出 CSV' })
              }}
            >
              <span className="inline-flex items-center gap-1.5"><Download className="h-4 w-4" />CSV</span>
            </button>
            <button
              type="button"
              className="btn-secondary border-white/40 bg-white/10 text-white hover:bg-white/20"
              onClick={() => {
                exportEventsJson(deviceLabel, filteredTimeline)
                pushToast({ type: 'success', title: '已匯出 JSON' })
              }}
            >
              <span className="inline-flex items-center gap-1.5"><Download className="h-4 w-4" />JSON</span>
            </button>
            <button
              type="button"
              className="btn-secondary border-white/40 bg-white/10 text-white hover:bg-white/20"
              onClick={() => {
                exportEventsPdf(deviceLabel, filteredTimeline)
                pushToast({ type: 'success', title: '已匯出 PDF' })
              }}
            >
              <span className="inline-flex items-center gap-1.5"><Download className="h-4 w-4" />PDF</span>
            </button>
            <button
              type="button"
              className="btn-secondary border-white/40 bg-white/10 text-white hover:bg-white/20"
              onClick={() => void fetchData()}
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
