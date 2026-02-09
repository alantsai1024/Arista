'use client'

import { memo, useMemo } from 'react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

const palette = ['#2f7ed9', '#2ca26b', '#d4a82f', '#b67ed6', '#f97316', '#10b981', '#ef4444']

interface EventTypePieChartProps {
  data: Record<string, number>
}

function EventTypePieChart({ data }: EventTypePieChartProps) {
  const rows = useMemo(() => Object.entries(data).map(([name, value]) => ({ name, value })), [data])

  if (rows.length === 0) {
    return (
      <section className="card-surface p-5">
        <h3 className="text-base font-semibold text-slate-900">事件分布</h3>
        <p className="mt-4 text-sm text-slate-500">目前沒有可用事件資料。</p>
      </section>
    )
  }

  return (
    <section className="card-surface p-5">
      <header className="mb-3">
        <h3 className="text-base font-semibold text-slate-900">事件分布</h3>
        <p className="text-xs text-slate-500">依事件類型彙整</p>
      </header>
      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={rows} dataKey="value" nameKey="name" innerRadius={50} outerRadius={88} isAnimationActive={false}>
              {rows.map((row, index) => (
                <Cell key={row.name} fill={palette[index % palette.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => [`${value ?? 0} 筆`, '事件']}
              contentStyle={{ borderRadius: '12px', border: '1px solid #dbe6f0' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

export default memo(EventTypePieChart)
