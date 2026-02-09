'use client'

import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export interface HealthTrendPoint {
  time: string
  online: number
  degraded: number
  offline: number
}

interface HealthTrendSparklineProps {
  data: HealthTrendPoint[]
}

export default function HealthTrendSparkline({ data }: HealthTrendSparklineProps) {
  return (
    <section className="card-surface p-5">
      <header className="mb-3">
        <h3 className="text-base font-semibold text-slate-900">健康趨勢</h3>
        <p className="text-xs text-slate-500">最近輪詢樣本變化</p>
      </header>
      <div className="h-64 w-full" data-testid="health-trend-sparkline">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 4, left: -22, bottom: 0 }}>
            <defs>
              <linearGradient id="onlineGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2ca26b" stopOpacity={0.55} />
                <stop offset="95%" stopColor="#2ca26b" stopOpacity={0.08} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#e7edf4" strokeDasharray="3 3" />
            <XAxis dataKey="time" tick={{ fontSize: 11 }} stroke="#7d8da3" />
            <YAxis tick={{ fontSize: 11 }} stroke="#7d8da3" />
            <Tooltip contentStyle={{ borderRadius: '12px', border: '1px solid #dbe6f0' }} />
            <Area type="monotone" dataKey="online" stroke="#2ca26b" strokeWidth={2} fill="url(#onlineGradient)" />
            <Area type="monotone" dataKey="degraded" stroke="#d4a82f" strokeWidth={1.7} fill="transparent" />
            <Area type="monotone" dataKey="offline" stroke="#e05a5a" strokeWidth={1.7} fill="transparent" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

