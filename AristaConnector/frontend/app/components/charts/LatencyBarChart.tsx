'use client'

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { formatLatency } from '@/app/lib/format'
import type { DeviceListRow } from '@/app/lib/types'

interface LatencyBarChartProps {
  rows: DeviceListRow[]
}

export default function LatencyBarChart({ rows }: LatencyBarChartProps) {
  const data = [...rows]
    .filter((row) => row.latencyMs !== null)
    .sort((a, b) => (b.latencyMs ?? 0) - (a.latencyMs ?? 0))
    .slice(0, 8)
    .map((row) => ({
      name: row.hostname || row.ip,
      latency: Number((row.latencyMs ?? 0).toFixed(2)),
    }))

  return (
    <section className="card-surface p-5">
      <header className="mb-3">
        <h3 className="text-base font-semibold text-slate-900">高延遲設備</h3>
        <p className="text-xs text-slate-500">Top 8 latency (ms)</p>
      </header>
      <div className="h-64 w-full" data-testid="latency-bar-chart">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 12 }}>
            <CartesianGrid stroke="#e7edf4" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 12 }} stroke="#7d8da3" />
            <YAxis
              type="category"
              dataKey="name"
              width={110}
              tick={{ fontSize: 11 }}
              stroke="#7d8da3"
            />
            <Tooltip
              formatter={(value) => [formatLatency(Number(value ?? 0)), '延遲']}
              contentStyle={{ borderRadius: '12px', border: '1px solid #dbe6f0' }}
            />
            <Bar dataKey="latency" fill="#2f7ed9" radius={[0, 8, 8, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}
