'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AlertTriangle, RefreshCw, Router, ShieldAlert, Wifi, WifiOff } from 'lucide-react'
import {
  getFleetHealth,
  getFleetSnapshot,
  listDevices,
  mergeDeviceRows,
} from '@/app/lib/api'
import {
  POLLING_INTERVAL_MS,
  formatRelativeTime,
} from '@/app/lib/format'
import { exportFleetSnapshotPdf } from '@/app/lib/export'
import type { Device, DeviceListRow, DeviceStatus, FleetHealth } from '@/app/lib/types'
import KpiCard from '@/app/components/charts/KpiCard'
import StatusDonutChart from '@/app/components/charts/StatusDonutChart'
import LatencyBarChart from '@/app/components/charts/LatencyBarChart'
import EventTypeBarChart from '@/app/components/charts/EventTypeBarChart'
import HealthTrendSparkline, { HealthTrendPoint } from '@/app/components/charts/HealthTrendSparkline'
import InlineAlert from '@/app/components/feedback/InlineAlert'
import AnomalyTable from '@/app/components/tables/AnomalyTable'
import { useToast } from '@/app/components/feedback/ToastProvider'

const BACKGROUND_POLLING_INTERVAL_MS = 30_000
const DEVICE_REFRESH_INTERVAL_MS = 60_000

function buildUnknownHealth(devices: Device[]): FleetHealth {
  const statuses: DeviceStatus[] = devices.map((device) => ({
    device_id: device.id,
    status: 'unknown',
    online: false,
    last_seen: null,
    recent_stats: {
      total_events_last_hour: 0,
      events_by_type: {},
      last_event_at: null,
      latency_ms: null,
    },
  }))
  return {
    total_devices: devices.length,
    online_devices: 0,
    degraded_devices: 0,
    offline_devices: devices.length,
    devices: statuses,
    top_latency_devices: [],
  }
}

function aggregateEventTypes(rows: DeviceListRow[]) {
  return rows.reduce<Record<string, number>>((acc, row) => {
    Object.entries(row.eventsByType).forEach(([eventType, count]) => {
      acc[eventType] = (acc[eventType] ?? 0) + count
    })
    return acc
  }, {})
}

function trendLabel() {
  return new Date().toLocaleTimeString('zh-TW', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

interface WarningMap {
  devices?: string
  health?: string
  snapshot?: string
}

export default function FleetPage() {
  const router = useRouter()
  const { pushToast } = useToast()

  const [devices, setDevices] = useState<Device[]>([])
  const [health, setHealth] = useState<FleetHealth | null>(null)
  const [warningsBySource, setWarningsBySource] = useState<WarningMap>({})
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string | null>(null)
  const [trend, setTrend] = useState<HealthTrendPoint[]>([])

  const healthRef = useRef<FleetHealth | null>(null)
  const fullSnapshotInFlightRef = useRef(false)
  const healthPollInFlightRef = useRef(false)
  const devicePollInFlightRef = useRef(false)

  useEffect(() => {
    healthRef.current = health
  }, [health])

  const getHealthPollingDelay = useCallback(() => (
    typeof document !== 'undefined' && document.hidden
      ? BACKGROUND_POLLING_INTERVAL_MS
      : POLLING_INTERVAL_MS
  ), [])

  const applyHealth = useCallback((nextHealth: FleetHealth) => {
    setHealth(nextHealth)
    setLastUpdatedAt(new Date().toISOString())
    setTrend((prev) => [
      ...prev.slice(-23),
      {
        time: trendLabel(),
        online: nextHealth.online_devices,
        degraded: nextHealth.degraded_devices,
        offline: nextHealth.offline_devices,
      },
    ])
  }, [])

  const setWarning = useCallback((key: keyof WarningMap, value: string | null) => {
    setWarningsBySource((prev) => {
      const next = { ...prev }
      if (value) next[key] = value
      else delete next[key]
      return next
    })
  }, [])

  const fetchFullSnapshot = useCallback(async (notifyOnError: boolean) => {
    if (fullSnapshotInFlightRef.current) return
    fullSnapshotInFlightRef.current = true

    try {
      setRefreshing(true)
      const snapshot = await getFleetSnapshot()
      const availableDevices = snapshot.devices ?? []
      const availableHealth = snapshot.health ?? buildUnknownHealth(availableDevices)

      setDevices(availableDevices)
      applyHealth(availableHealth)

      const devicesWarning = snapshot.warnings.find((warning) => warning.includes('/devices')) ?? null
      const healthWarning = snapshot.warnings.find((warning) => warning.includes('/health/fleet')) ?? null

      setWarning('devices', devicesWarning)
      setWarning('health', healthWarning)
      setWarning('snapshot', null)
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知錯誤'
      setWarning('snapshot', `機群資料讀取失敗：${message}`)
      if (notifyOnError) {
        pushToast({ type: 'error', title: '機群資料讀取失敗', description: message })
      }
    } finally {
      fullSnapshotInFlightRef.current = false
      setLoading(false)
      setRefreshing(false)
    }
  }, [applyHealth, pushToast, setWarning])

  const fetchHealthOnly = useCallback(async () => {
    if (fullSnapshotInFlightRef.current) return

    try {
      const latestHealth = await getFleetHealth()
      applyHealth(latestHealth)
      setWarning('health', null)
      setWarning('snapshot', null)
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知錯誤'
      setWarning('health', `/health/fleet 讀取失敗：${message}`)
    }
  }, [applyHealth, setWarning])

  const fetchDevicesOnly = useCallback(async () => {
    if (fullSnapshotInFlightRef.current) return

    try {
      const latestDevices = await listDevices()
      setDevices(latestDevices)
      setLastUpdatedAt(new Date().toISOString())

      if (!healthRef.current) {
        applyHealth(buildUnknownHealth(latestDevices))
      }

      setWarning('devices', null)
      setWarning('snapshot', null)
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知錯誤'
      setWarning('devices', `/devices 讀取失敗：${message}`)
    }
  }, [applyHealth, setWarning])

  useEffect(() => {
    void fetchFullSnapshot(true)
  }, [fetchFullSnapshot])

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
      if (healthPollInFlightRef.current) {
        scheduleNext(getHealthPollingDelay())
        return
      }

      healthPollInFlightRef.current = true
      try {
        await fetchHealthOnly()
      } finally {
        healthPollInFlightRef.current = false
        scheduleNext(getHealthPollingDelay())
      }
    }

    const handleVisibilityChange = () => {
      if (timer) clearTimeout(timer)
      scheduleNext(getHealthPollingDelay())
    }

    scheduleNext(getHealthPollingDelay())
    document.addEventListener('visibilitychange', handleVisibilityChange)

    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [fetchHealthOnly, getHealthPollingDelay])

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | null = null

    const scheduleNext = () => {
      if (cancelled) return
      timer = setTimeout(() => {
        void run()
      }, DEVICE_REFRESH_INTERVAL_MS)
    }

    const run = async () => {
      if (cancelled) return
      if (devicePollInFlightRef.current) {
        scheduleNext()
        return
      }

      devicePollInFlightRef.current = true
      try {
        await fetchDevicesOnly()
      } finally {
        devicePollInFlightRef.current = false
        scheduleNext()
      }
    }

    scheduleNext()
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [fetchDevicesOnly])

  const effectiveHealth = useMemo(
    () => health ?? buildUnknownHealth(devices),
    [health, devices],
  )

  const rows = useMemo(
    () => mergeDeviceRows(devices, effectiveHealth.devices),
    [devices, effectiveHealth],
  )

  const warnings = useMemo(
    () => Object.values(warningsBySource).filter((warning): warning is string => Boolean(warning)),
    [warningsBySource],
  )

  const anomalyRows = useMemo(
    () => rows.filter((row) => row.status !== 'online'),
    [rows],
  )
  const eventTypeCounts = useMemo(() => aggregateEventTypes(rows), [rows])

  const loadingContent = (
    <main className="mx-auto min-h-[calc(100vh-4rem)] max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
      <div className="card-surface flex min-h-[320px] items-center justify-center">
        <div className="text-center">
          <p className="text-base font-semibold text-slate-700">載入 Fleet Dashboard...</p>
          <p className="mt-1 text-sm text-slate-500">正在同步 `/health/fleet` 與 `/devices`</p>
        </div>
      </div>
    </main>
  )

  if (loading) return loadingContent

  return (
    <main className="mx-auto min-h-[calc(100vh-4rem)] max-w-7xl space-y-6 px-4 py-7 sm:px-6 lg:px-8">
      <section className="card-surface overflow-hidden p-6">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Arista Fleet Console</p>
            <h1 className="font-display mt-2 text-3xl font-semibold text-balance">現代化監控總覽</h1>
            <p className="mt-2 text-sm text-slate-600">
              上次更新：{formatRelativeTime(lastUpdatedAt)}，健康每 10 秒、設備清單每 60 秒（背景分頁 30 秒）
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="btn-secondary"
              onClick={async () => {
                try {
                  await exportFleetSnapshotPdf(
                    {
                      total: effectiveHealth.total_devices,
                      online: effectiveHealth.online_devices,
                      degraded: effectiveHealth.degraded_devices,
                      offline: effectiveHealth.offline_devices,
                    },
                    anomalyRows,
                  )
                  pushToast({ type: 'success', title: '已匯出 Fleet PDF' })
                } catch (error) {
                  const message = error instanceof Error ? error.message : '未知錯誤'
                  pushToast({ type: 'error', title: 'Fleet PDF 匯出失敗', description: message })
                }
              }}
            >
              匯出 Fleet PDF
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => void fetchFullSnapshot(true)}
              disabled={refreshing}
            >
              <span className="inline-flex items-center gap-2">
                <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
                {refreshing ? '更新中' : '手動刷新'}
              </span>
            </button>
          </div>
        </div>
      </section>

      {warnings.length > 0 && (
        <InlineAlert title="資料來源警告" details={warnings} variant="warning" />
      )}

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4" data-testid="fleet-kpi-cards">
        <KpiCard title="總設備" value={effectiveHealth.total_devices} tone="neutral" icon={Router} subtitle="設備 inventory" />
        <KpiCard title="在線" value={effectiveHealth.online_devices} tone="online" icon={Wifi} subtitle="last_seen within threshold" />
        <KpiCard title="降級" value={effectiveHealth.degraded_devices} tone="degraded" icon={AlertTriangle} subtitle="重試中設備" />
        <KpiCard title="離線" value={effectiveHealth.offline_devices} tone="offline" icon={WifiOff} subtitle="超過離線門檻" />
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <StatusDonutChart online={effectiveHealth.online_devices} degraded={effectiveHealth.degraded_devices} offline={effectiveHealth.offline_devices} />
        <LatencyBarChart rows={rows} />
        <EventTypeBarChart data={eventTypeCounts} />
        <HealthTrendSparkline data={trend} />
      </section>

      {anomalyRows.length > 0 ? (
        <AnomalyTable rows={anomalyRows} onOpenDetail={(deviceId) => router.push(`/devices/${deviceId}`)} />
      ) : (
        <section className="card-surface p-6">
          <div className="flex items-center gap-3 text-emerald-700">
            <ShieldAlert className="h-5 w-5" />
            <p className="text-sm font-semibold">目前沒有異常設備，整體狀態穩定。</p>
          </div>
        </section>
      )}
    </main>
  )
}
