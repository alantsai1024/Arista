'use client'

interface FleetHealthProps {
  health: {
    total_devices: number
    online_devices: number
    offline_devices: number
    devices: Array<{
      device_id: number
      status: string
      last_seen: string | null
      online: boolean
    }>
  }
}

export default function FleetHealth({ health }: FleetHealthProps) {
  const onlinePercentage = health.total_devices > 0 
    ? Math.round((health.online_devices / health.total_devices) * 100) 
    : 0

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 mb-6">
      <h2 className="text-2xl font-semibold mb-4">機群健康狀態</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-blue-50 dark:bg-blue-900 p-4 rounded">
          <div className="text-sm text-gray-600 dark:text-gray-300">總設備數</div>
          <div className="text-3xl font-bold text-blue-600 dark:text-blue-300">
            {health.total_devices}
          </div>
        </div>
        
        <div className="bg-green-50 dark:bg-green-900 p-4 rounded">
          <div className="text-sm text-gray-600 dark:text-gray-300">線上設備</div>
          <div className="text-3xl font-bold text-green-600 dark:text-green-300">
            {health.online_devices}
          </div>
        </div>
        
        <div className="bg-red-50 dark:bg-red-900 p-4 rounded">
          <div className="text-sm text-gray-600 dark:text-gray-300">離線設備</div>
          <div className="text-3xl font-bold text-red-600 dark:text-red-300">
            {health.offline_devices}
          </div>
        </div>
        
        <div className="bg-purple-50 dark:bg-purple-900 p-4 rounded">
          <div className="text-sm text-gray-600 dark:text-gray-300">線上率</div>
          <div className="text-3xl font-bold text-purple-600 dark:text-purple-300">
            {onlinePercentage}%
          </div>
        </div>
      </div>
      
      <div className="mt-4">
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div 
            className="bg-green-600 h-2.5 rounded-full transition-all"
            style={{ width: `${onlinePercentage}%` }}
          ></div>
        </div>
      </div>
    </div>
  )
}
