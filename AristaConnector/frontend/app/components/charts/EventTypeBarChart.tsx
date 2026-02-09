'use client'

import { memo, useMemo } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

interface EventTypeBarChartProps {
  data: Record<string, number>
}

function EventTypeBarChart({ data }: EventTypeBarChartProps) {
  const chartData = useMemo(() => Object.entries(data).map(([type, count]) => ({
    type,
    count,
  })), [data])

  return (
    <section className="card-surface p-5">
      <header className="mb-3">
        <h3 className="text-base font-semibold text-slate-900">事件類型統計</h3>
        <p className="text-xs text-slate-500">彙整所有設備最近一小時事件</p>
      </header>
      <div className="h-64 w-full" data-testid="event-type-bar-chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
            <CartesianGrid stroke="#e7edf4" />
            <XAxis dataKey="type" stroke="#7d8da3" tick={{ fontSize: 12 }} />
            <YAxis stroke="#7d8da3" tick={{ fontSize: 12 }} />
            <Tooltip
              formatter={(value) => [`${value ?? 0} 筆`, '事件數']}
              contentStyle={{ borderRadius: '12px', border: '1px solid #dbe6f0' }}
            />
            <Legend />
            <Bar dataKey="count" fill="#5f8fca" radius={[8, 8, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

export default memo(EventTypeBarChart)
