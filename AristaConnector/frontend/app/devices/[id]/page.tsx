'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

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

interface Event {
  id: string
  device_id: string
  event_type: string
  message: string | null
  metadata: any
  created_at: string
}

export default function DeviceDetailPage() {
  const params = useParams()
  const router = useRouter()
  const deviceId = params.id as string
  
  const [device, setDevice] = useState<Device | null>(null)
  const [status, setStatus] = useState<DeviceStatus | null>(null)
  const [events, setEvents] = useState<Event[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set())

  const fetchData = async () => {
    try {
      const [deviceRes, statusRes, eventsRes] = await Promise.all([
        fetch(`${API_URL}/devices/${deviceId}`),
        fetch(`${API_URL}/devices/${deviceId}/status`),
        fetch(`${API_URL}/devices/${deviceId}/events?limit=50`)
      ])
      
      if (deviceRes.ok) {
        const deviceData = await deviceRes.json()
        setDevice(deviceData)
      }
      
      if (statusRes.ok) {
        const statusData = await statusRes.json()
        setStatus(statusData)
      }
      
      if (eventsRes.ok) {
        const eventsData = await eventsRes.json()
        setEvents(eventsData)
      }
    } catch (error) {
      console.error('Failed to fetch data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (deviceId) {
      fetchData()
      const interval = setInterval(fetchData, 10000) // Refresh every 10 seconds
      return () => clearInterval(interval)
    }
  }, [deviceId]) // eslint-disable-line react-hooks/exhaustive-deps

  const formatLastSeen = (lastSeen: string | null): string => {
    if (!lastSeen) return 'Never'
    const date = new Date(lastSeen)
    return date.toLocaleString()
  }

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

  const toggleEventExpansion = (eventId: string) => {
    const newExpanded = new Set(expandedEvents)
    if (newExpanded.has(eventId)) {
      newExpanded.delete(eventId)
    } else {
      newExpanded.add(eventId)
    }
    setExpandedEvents(newExpanded)
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">載入中...</div>
      </div>
    )
  }

  if (!device) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl text-red-600">設備未找到</div>
      </div>
    )
  }

  return (
    <main className="min-h-screen p-8 bg-gray-50">
      <div className="max-w-7xl mx-auto">
        <div className="mb-6">
          <button
            onClick={() => router.back()}
            className="mb-4 text-blue-600 hover:text-blue-800"
          >
            ← 返回機群
          </button>
          <h1 className="text-4xl font-bold">{device.hostname || device.ip}</h1>
        </div>

        {/* Device Info */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-2xl font-semibold mb-4">設備資訊</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-sm text-gray-600">IP 位址</div>
              <div className="text-lg font-medium">{device.ip}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">連接埠</div>
              <div className="text-lg font-medium">{device.port}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">輪詢間隔</div>
              <div className="text-lg font-medium">{device.interval_sec} 秒</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">狀態</div>
              <div className="text-lg font-medium">
                <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full border ${getStatusColor(status?.status || 'unknown')}`}>
                  {status?.status || 'unknown'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Status Info */}
        {status && (
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <h2 className="text-2xl font-semibold mb-4">狀態資訊</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-600">最後看到</div>
                <div className="text-lg font-medium">{formatLastSeen(status.last_seen)}</div>
              </div>
              <div>
                <div className="text-sm text-gray-600">線上狀態</div>
                <div className="text-lg font-medium">
                  {status.online ? (
                    <span className="text-green-600">線上</span>
                  ) : (
                    <span className="text-red-600">離線</span>
                  )}
                </div>
              </div>
              {status.recent_stats && (
                <>
                  <div>
                    <div className="text-sm text-gray-600">平均延遲</div>
                    <div className="text-lg font-medium">
                      {status.recent_stats.latency_ms
                        ? `${status.recent_stats.latency_ms.toFixed(2)} ms`
                        : 'N/A'}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">過去一小時事件數</div>
                    <div className="text-lg font-medium">
                      {status.recent_stats.total_events_last_hour || 0}
                    </div>
                  </div>
                </>
              )}
            </div>
            {status.recent_stats?.events_by_type && (
              <div className="mt-4">
                <div className="text-sm text-gray-600 mb-2">事件類型統計</div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(status.recent_stats.events_by_type).map(([type, count]) => (
                    <span
                      key={type}
                      className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm"
                    >
                      {type}: {count}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Recent Events */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-semibold mb-4">最近 50 個事件</h2>
          <div className="space-y-2">
            {events.length === 0 ? (
              <div className="text-gray-500 text-center py-8">尚無事件</div>
            ) : (
              events.map((event) => {
                const isExpanded = expandedEvents.has(event.id)
                let metadataObj = null
                try {
                  if (typeof event.metadata === 'string') {
                    metadataObj = JSON.parse(event.metadata)
                  } else {
                    metadataObj = event.metadata
                  }
                } catch {
                  metadataObj = event.metadata
                }

                return (
                  <div
                    key={event.id}
                    className="border rounded-lg p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium">
                            {event.event_type}
                          </span>
                          <span className="text-sm text-gray-500">
                            {new Date(event.created_at).toLocaleString()}
                          </span>
                        </div>
                        {event.message && (
                          <div className="text-sm text-gray-700 mb-2">{event.message}</div>
                        )}
                        {isExpanded && metadataObj && (
                          <div className="mt-2 p-3 bg-gray-100 rounded text-xs font-mono overflow-auto">
                            <pre>{JSON.stringify(metadataObj, null, 2)}</pre>
                          </div>
                        )}
                      </div>
                      {metadataObj && (
                        <button
                          onClick={() => toggleEventExpansion(event.id)}
                          className="ml-4 px-3 py-1 text-sm text-blue-600 hover:text-blue-800"
                        >
                          {isExpanded ? '收起' : '展開 JSON'}
                        </button>
                      )}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      </div>
    </main>
  )
}
