'use client'

import { memo } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

interface EventVolumeChartProps {
  data: Array<{
    time: string
    total: number
    critical: number
  }>
}

function EventVolumeChart({ data }: EventVolumeChartProps) {
  return (
    <section className="card-surface p-5">
      <header className="mb-3">
        <h3 className="text-base font-semibold text-slate-900">時間分箱趨勢</h3>
        <p className="text-xs text-slate-500">每 10 分鐘事件總量與高風險事件量</p>
      </header>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ left: -18, right: 12 }}>
            <CartesianGrid stroke="#e7edf4" />
            <XAxis dataKey="time" stroke="#7d8da3" tick={{ fontSize: 11 }} />
            <YAxis stroke="#7d8da3" tick={{ fontSize: 11 }} />
            <Tooltip contentStyle={{ borderRadius: '12px', border: '1px solid #dbe6f0' }} />
            <Legend />
            <Bar dataKey="total" name="總事件" fill="#2f7ed9" radius={[6, 6, 0, 0]} isAnimationActive={false} />
            <Bar dataKey="critical" name="高風險" fill="#e05a5a" radius={[6, 6, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

export default memo(EventVolumeChart)
