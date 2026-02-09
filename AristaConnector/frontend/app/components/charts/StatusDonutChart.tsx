'use client'

import { memo } from 'react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

interface StatusDonutChartProps {
  online: number
  degraded: number
  offline: number
}

const COLORS = ['#2ca26b', '#d4a82f', '#e05a5a']

function StatusDonutChart({ online, degraded, offline }: StatusDonutChartProps) {
  const data = [
    { name: '在線', value: online },
    { name: '降級', value: degraded },
    { name: '離線', value: offline },
  ]

  return (
    <section className="card-surface p-5">
      <header className="mb-3">
        <h3 className="text-base font-semibold text-slate-900">狀態分布</h3>
        <p className="text-xs text-slate-500">依照 fleet health 即時統計</p>
      </header>
      <div className="h-64 w-full" data-testid="status-donut-chart">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius={56}
              outerRadius={90}
              paddingAngle={4}
              isAnimationActive={false}
            >
              {data.map((entry, index) => (
                <Cell key={entry.name} fill={COLORS[index]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value) => [value ?? 0, '設備數']}
              contentStyle={{
                borderRadius: '14px',
                border: '1px solid #dbe6f0',
                backgroundColor: '#ffffff',
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

export default memo(StatusDonutChart)
