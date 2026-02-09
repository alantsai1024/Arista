import { formatLatency, formatRelativeTime } from '@/app/lib/format'
import type { DeviceListRow } from '@/app/lib/types'
import StatusBadge from '@/app/components/ui/StatusBadge'

interface AnomalyTableProps {
  rows: DeviceListRow[]
  onOpenDetail: (deviceId: string) => void
}

export default function AnomalyTable({ rows, onOpenDetail }: AnomalyTableProps) {
  return (
    <section className="card-surface p-0 overflow-hidden">
      <header className="border-b border-slate-200 px-5 py-4">
        <h3 className="text-base font-semibold text-slate-900">異常設備表</h3>
        <p className="text-xs text-slate-500">點擊列可進入設備詳情與時間鏈</p>
      </header>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px]">
          <thead className="bg-slate-50 text-left">
            <tr className="text-xs uppercase tracking-wide text-slate-500">
              <th className="px-4 py-3">主機</th>
              <th className="px-4 py-3">IP</th>
              <th className="px-4 py-3">狀態</th>
              <th className="px-4 py-3">最後上線</th>
              <th className="px-4 py-3">延遲</th>
              <th className="px-4 py-3">事件/hr</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-sm text-slate-500">
                  目前沒有異常設備
                </td>
              </tr>
            )}
            {rows.map((row) => (
              <tr
                key={row.id}
                className="cursor-pointer border-t border-slate-200 text-sm hover:bg-slate-50"
                onClick={() => onOpenDetail(row.id)}
              >
                <td className="px-4 py-3 font-medium text-slate-900">{row.hostname || row.id}</td>
                <td className="px-4 py-3 text-slate-700">{row.ip}</td>
                <td className="px-4 py-3"><StatusBadge status={row.status} /></td>
                <td className="px-4 py-3 text-slate-700">{formatRelativeTime(row.lastSeen || row.lastEventAt)}</td>
                <td className="px-4 py-3 text-slate-700">{formatLatency(row.latencyMs)}</td>
                <td className="px-4 py-3 text-slate-700">{row.eventsLastHour}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

