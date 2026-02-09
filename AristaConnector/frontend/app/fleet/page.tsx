'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AlertTriangle, RefreshCw, Router, ShieldAlert, Wifi, WifiOff } from 'lucide-react'
import {
  getFleetSnapshot,
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

export default function FleetPage() {
  const router = useRouter()
  const { pushToast } = useToast()
  const [health, setHealth] = useState<FleetHealth | null>(null)
  const [rows, setRows] = useState<DeviceListRow[]>([])
  const [warnings, setWarnings] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [trend, setTrend] = useState<HealthTrendPoint[]>([])

  async function fetchData() {
    try {
      setRefreshing(true)
      const snapshot = await getFleetSnapshot()
      const availableDevices = snapshot.devices ?? []
      const availableHealth = snapshot.health ?? buildUnknownHealth(availableDevices)
      const mergedRows = mergeDeviceRows(availableDevices, availableHealth.devices)

      setRows(mergedRows)
      setHealth(availableHealth)
      setWarnings(snapshot.warnings)
      setTrend((prev) => [
        ...prev.slice(-23),
        {
          time: trendLabel(),
          online: availableHealth.online_devices,
          degraded: availableHealth.degraded_devices,
          offline: availableHealth.offline_devices,
        },
      ])
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知錯誤'
      setWarnings([`機群資料讀取失敗：${message}`])
      pushToast({ type: 'error', title: '機群資料讀取失敗', description: message })
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
  }, [])

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

  if (loading || !health) return loadingContent

  return (
    <main className="mx-auto min-h-[calc(100vh-4rem)] max-w-7xl space-y-6 px-4 py-7 sm:px-6 lg:px-8">
      <section className="card-surface bg-brand-gradient overflow-hidden p-6 text-white">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-white/80">Arista Fleet Console</p>
            <h1 className="font-display mt-2 text-3xl font-semibold text-balance">現代化監控總覽</h1>
            <p className="mt-2 text-sm text-white/85">
              上次更新：{formatRelativeTime(new Date().toISOString())}，每 10 秒輪詢同步
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="btn-secondary border-white/35 bg-white/10 text-white hover:bg-white/20"
              onClick={() => {
                exportFleetSnapshotPdf(
                  {
                    total: health.total_devices,
                    online: health.online_devices,
                    degraded: health.degraded_devices,
                    offline: health.offline_devices,
                  },
                  anomalyRows,
                )
                pushToast({ type: 'success', title: '已匯出 Fleet PDF' })
              }}
            >
              匯出 Fleet PDF
            </button>
            <button
              type="button"
              className="btn-secondary border-white/35 bg-white/10 text-white hover:bg-white/20"
              onClick={() => void fetchData()}
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
        <KpiCard title="總設備" value={health.total_devices} tone="neutral" icon={Router} subtitle="設備 inventory" />
        <KpiCard title="在線" value={health.online_devices} tone="online" icon={Wifi} subtitle="last_seen within threshold" />
        <KpiCard title="降級" value={health.degraded_devices} tone="degraded" icon={AlertTriangle} subtitle="重試中設備" />
        <KpiCard title="離線" value={health.offline_devices} tone="offline" icon={WifiOff} subtitle="超過離線門檻" />
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <StatusDonutChart online={health.online_devices} degraded={health.degraded_devices} offline={health.offline_devices} />
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

