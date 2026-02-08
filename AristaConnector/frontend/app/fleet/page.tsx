'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface DeviceStatus {
  device_id: string
  status: string
  last_seen: string | null
  online: boolean
  recent_stats?: {
    total_events_last_hour?: number
    events_by_type?: Record<string, number>
    last_event_at?: string | null
    latency_ms?: number | null
  }
}

interface DeviceLatency {
  device_id: string
  hostname: string | null
  ip: string
  latency_ms: number | null
}

interface FleetHealth {
  total_devices: number
  online_devices: number
  offline_devices: number
  degraded_devices: number
  devices: DeviceStatus[]
  top_latency_devices: DeviceLatency[]
}

interface Device {
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

export default function FleetPage() {
  const router = useRouter()
  const [health, setHealth] = useState<FleetHealth | null>(null)
  const [devices, setDevices] = useState<Device[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [deviceRankings, setDeviceRankings] = useState<Map<string, number>>(new Map())
  const [highlightedDevices, setHighlightedDevices] = useState<Set<string>>(new Set())

  const fetchData = async () => {
    try {
      setRefreshing(true)
      const [healthRes, devicesRes] = await Promise.all([
        fetch(`${API_URL}/health/fleet`),
        fetch(`${API_URL}/devices`)
      ])
      
      if (healthRes.ok && devicesRes.ok) {
        const healthData: FleetHealth = await healthRes.json()
        const devicesData = await devicesRes.json()

        // Older /health/fleet payload may not include recent_stats per device.
        // Fallback to /devices/{id}/status so table metrics remain accurate.
        const needsStatusFallback = healthData.devices.some((d) => !d.recent_stats)
        let mergedStatuses = healthData.devices

        if (needsStatusFallback && Array.isArray(devicesData) && devicesData.length > 0) {
          const statusResults = await Promise.allSettled(
            devicesData.map(async (device: Device) => {
              const res = await fetch(`${API_URL}/devices/${device.id}/status`)
              if (!res.ok) throw new Error(`status fetch failed: ${device.id}`)
              const status: DeviceStatus = await res.json()
              return status
            })
          )

          const statusMap = new Map<string, DeviceStatus>()
          statusResults.forEach((result) => {
            if (result.status === 'fulfilled') {
              statusMap.set(result.value.device_id, result.value)
            }
          })

          mergedStatuses = healthData.devices.map((status) => statusMap.get(status.device_id) ?? status)
        }
        
        // Check for ranking changes
        const newRankings = new Map<string, number>()
        mergedStatuses.forEach((d: DeviceStatus, index: number) => {
          newRankings.set(d.device_id, index)
        })
        
        // Find devices that moved
        const moved = new Set<string>()
        deviceRankings.forEach((oldRank, deviceId) => {
          const newRank = newRankings.get(deviceId)
          if (newRank !== undefined && newRank !== oldRank) {
            moved.add(deviceId)
          }
        })
        
        if (moved.size > 0) {
          setHighlightedDevices(moved)
          setTimeout(() => setHighlightedDevices(new Set()), 2000) // Highlight for 2 seconds
        }
        
        setDeviceRankings(newRankings)
        setHealth({
          ...healthData,
          devices: mergedStatuses,
        })
        setDevices(devicesData)
      }
    } catch (error) {
      console.error('Failed to fetch data:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000) // Refresh every 10 seconds
    return () => clearInterval(interval)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Create device map for quick lookup
  const deviceMap = new Map(devices.map(d => [d.id, d]))

  // Calculate events per 10s (approximate from last hour)
  const getEventsPer10s = (deviceId: string): number | null => {
    const status = health?.devices.find(d => d.device_id === deviceId)
    const totalEvents = status?.recent_stats?.total_events_last_hour
    if (typeof totalEvents !== 'number') return null
    // 3600 seconds/hour -> events per 10 seconds = events_per_hour / 360
    return Math.round((totalEvents / 360) * 10) / 10
  }

  // Format last seen
  const formatLastSeen = (lastSeen: string | null): string => {
    if (!lastSeen) return 'Never'
    const date = new Date(lastSeen)
    if (Number.isNaN(date.getTime())) return 'N/A'
    const now = new Date()
    const diff = Math.floor((now.getTime() - date.getTime()) / 1000)
    
    if (diff < 0) return date.toLocaleString()
    if (diff < 60) return `${diff}s ago`
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    return date.toLocaleString()
  }

  // Get status badge color
  const getStatusColor = (status: string): string => {
    switch (status) {
      case 'online':
        return 'bg-green-100 text-green-800 border-green-200'
      case 'degraded':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200'
      case 'offline':
        return 'bg-red-100 text-red-800 border-red-200'
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">載入中...</div>
      </div>
    )
  }

  return (
    <main className="min-h-screen p-8 bg-gray-50">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-4xl font-bold">設備機群</h1>
          <div className="flex items-center gap-4">
            {refreshing && (
              <div className="flex items-center gap-2 text-gray-600">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                <span className="text-sm">更新中...</span>
              </div>
            )}
            <button
              onClick={fetchData}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded"
            >
              手動刷新
            </button>
          </div>
        </div>

        {/* Summary Cards */}
        {health && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-600 mb-1">總設備數</div>
              <div className="text-3xl font-bold text-gray-900">{health.total_devices}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-600 mb-1">線上</div>
              <div className="text-3xl font-bold text-green-600">{health.online_devices}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-600 mb-1">降級</div>
              <div className="text-3xl font-bold text-yellow-600">{health.degraded_devices}</div>
            </div>
            <div className="bg-white rounded-lg shadow p-6">
              <div className="text-sm text-gray-600 mb-1">離線</div>
              <div className="text-3xl font-bold text-red-600">{health.offline_devices}</div>
            </div>
          </div>
        )}

        {/* Devices Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    主機名稱
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    IP 位址
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    狀態
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    最後看到
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    平均延遲 (ms)
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    事件/10秒
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {health?.devices.map((deviceStatus) => {
                  const device = deviceMap.get(deviceStatus.device_id)
                  if (!device) return null
                  
                  const isHighlighted = highlightedDevices.has(deviceStatus.device_id)
                  const latency = deviceStatus.recent_stats?.latency_ms
                  const eventsPer10s = getEventsPer10s(deviceStatus.device_id)
                  const lastSeen = deviceStatus.last_seen ?? deviceStatus.recent_stats?.last_event_at ?? null
                  
                  return (
                    <tr
                      key={deviceStatus.device_id}
                      className={`hover:bg-gray-50 cursor-pointer transition-all duration-300 ${
                        isHighlighted ? 'bg-yellow-50 border-l-4 border-yellow-400' : ''
                      }`}
                      onClick={() => router.push(`/devices/${deviceStatus.device_id}`)}
                    >
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {device.hostname || 'N/A'}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">{device.ip}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full border ${getStatusColor(deviceStatus.status)}`}>
                          {deviceStatus.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatLastSeen(lastSeen)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {latency === null || latency === undefined ? 'N/A' : latency.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {eventsPer10s === null ? 'N/A' : eventsPer10s.toFixed(1)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </main>
  )
}
