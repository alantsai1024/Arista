import { cn, statusLabel } from '@/app/lib/format'

interface StatusBadgeProps {
  status: string
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold',
        status === 'online' && 'border-emerald-300 bg-emerald-100 text-emerald-800',
        status === 'degraded' && 'border-amber-300 bg-amber-100 text-amber-800',
        status === 'offline' && 'border-rose-300 bg-rose-100 text-rose-800',
        status === 'ip_conflict' && 'border-fuchsia-300 bg-fuchsia-100 text-fuchsia-800',
        status !== 'online' && status !== 'degraded' && status !== 'offline' && status !== 'ip_conflict' && 'border-slate-300 bg-slate-100 text-slate-700',
      )}
    >
      {statusLabel(status)}
    </span>
  )
}
