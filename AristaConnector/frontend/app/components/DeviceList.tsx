'use client'

import { useState } from 'react'

interface Device {
  id: number
  hostname: string
  ip_address: string
  port: number
  enabled: string
  created_at: string
}

interface DeviceListProps {
  devices: Device[]
  onRefresh: () => void
}

export default function DeviceList({ devices, onRefresh }: DeviceListProps) {
  const [showAddForm, setShowAddForm] = useState(false)
  const [formData, setFormData] = useState({
    hostname: '',
    ip_address: '',
    username: '',
    password: '',
    port: 443,
    enabled: 'true'
  })

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const response = await fetch(`${API_URL}/devices`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      })
      
      if (response.ok) {
        setShowAddForm(false)
        setFormData({
          hostname: '',
          ip_address: '',
          username: '',
          password: '',
          port: 443,
          enabled: 'true'
        })
        onRefresh()
      } else {
        const error = await response.json()
        alert(`錯誤: ${error.detail || '無法建立設備'}`)
      }
    } catch (error) {
      console.error('Failed to create device:', error)
      alert('無法建立設備')
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-semibold">設備列表</h2>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded"
        >
          {showAddForm ? '取消' : '新增設備'}
        </button>
      </div>

      {showAddForm && (
        <form onSubmit={handleSubmit} className="mb-6 p-4 bg-gray-50 dark:bg-gray-700 rounded">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">主機名稱</label>
              <input
                type="text"
                required
                value={formData.hostname}
                onChange={(e) => setFormData({ ...formData, hostname: e.target.value })}
                className="w-full px-3 py-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">IP 位址</label>
              <input
                type="text"
                required
                value={formData.ip_address}
                onChange={(e) => setFormData({ ...formData, ip_address: e.target.value })}
                className="w-full px-3 py-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">使用者名稱</label>
              <input
                type="text"
                required
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                className="w-full px-3 py-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">密碼</label>
              <input
                type="password"
                required
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full px-3 py-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">連接埠</label>
              <input
                type="number"
                required
                value={formData.port}
                onChange={(e) => setFormData({ ...formData, port: parseInt(e.target.value) })}
                className="w-full px-3 py-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">啟用</label>
              <select
                value={formData.enabled}
                onChange={(e) => setFormData({ ...formData, enabled: e.target.value })}
                className="w-full px-3 py-2 border rounded"
              >
                <option value="true">是</option>
                <option value="false">否</option>
              </select>
            </div>
          </div>
          <button
            type="submit"
            className="mt-4 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded"
          >
            建立設備
          </button>
        </form>
      )}

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b">
              <th className="text-left p-2">ID</th>
              <th className="text-left p-2">主機名稱</th>
              <th className="text-left p-2">IP 位址</th>
              <th className="text-left p-2">連接埠</th>
              <th className="text-left p-2">狀態</th>
              <th className="text-left p-2">建立時間</th>
            </tr>
          </thead>
          <tbody>
            {devices.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center p-4 text-gray-500">
                  尚無設備
                </td>
              </tr>
            ) : (
              devices.map((device) => (
                <tr key={device.id} className="border-b hover:bg-gray-50 dark:hover:bg-gray-700">
                  <td className="p-2">{device.id}</td>
                  <td className="p-2">{device.hostname}</td>
                  <td className="p-2">{device.ip_address}</td>
                  <td className="p-2">{device.port}</td>
                  <td className="p-2">
                    <span className={`px-2 py-1 rounded text-sm ${
                      device.enabled === 'true' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {device.enabled === 'true' ? '啟用' : '停用'}
                    </span>
                  </td>
                  <td className="p-2">
                    {new Date(device.created_at).toLocaleString('zh-TW')}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
