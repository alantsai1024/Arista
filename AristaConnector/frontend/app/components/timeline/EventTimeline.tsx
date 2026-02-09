import { formatDateTime, cn } from '@/app/lib/format'
import type { TimelineEvent } from '@/app/lib/types'

interface EventTimelineProps {
  events: TimelineEvent[]
  activeEventId: string | null
  onSelectEvent: (event: TimelineEvent) => void
}

function severityStyles(severity: TimelineEvent['severity']) {
  if (severity === 'critical') {
    return {
      dot: 'bg-rose-500 shadow-[0_0_0_5px_rgba(224,90,90,0.18)]',
      panel: 'border-rose-200 bg-rose-50/60',
      label: 'text-rose-700',
    }
  }
  if (severity === 'warning') {
    return {
      dot: 'bg-amber-500 shadow-[0_0_0_5px_rgba(212,168,47,0.16)]',
      panel: 'border-amber-200 bg-amber-50/60',
      label: 'text-amber-700',
    }
  }
  return {
    dot: 'bg-sky-500 shadow-[0_0_0_5px_rgba(47,126,217,0.16)]',
    panel: 'border-sky-200 bg-sky-50/60',
    label: 'text-sky-700',
  }
}

export default function EventTimeline({ events, activeEventId, onSelectEvent }: EventTimelineProps) {
  return (
    <section className="card-surface p-5" data-testid="device-event-timeline">
      <header className="mb-4">
        <h3 className="text-base font-semibold text-slate-900">事件時間鏈</h3>
        <p className="text-xs text-slate-500">同類型且 120 秒內的事件會歸在同一個 chain group</p>
      </header>
      <div className="space-y-4">
        {events.length === 0 && (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-sm text-slate-500">
            此篩選條件下沒有事件。
          </div>
        )}
        {events.map((event) => {
          const styles = severityStyles(event.severity)
          const selected = activeEventId === event.id
          return (
            <article key={event.id} className="relative pl-10">
              <span className="absolute left-[9px] top-8 h-full w-px bg-slate-200" />
              <span className={cn('absolute left-0 top-2 h-5 w-5 rounded-full', styles.dot)} />
              <button
                type="button"
                onClick={() => onSelectEvent(event)}
                className={cn(
                  'w-full rounded-2xl border px-4 py-3 text-left transition',
                  styles.panel,
                  selected && 'ring-2 ring-sky-400/50',
                )}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className={cn('text-xs font-semibold uppercase tracking-wide', styles.label)}>
                    {event.event_type}
                  </span>
                  <span className="rounded-full bg-white px-2 py-0.5 text-[11px] text-slate-600">
                    {event.chainGroupId} #{event.chainIndex}
                  </span>
                  <span className="text-xs text-slate-500">{formatDateTime(event.created_at)}</span>
                </div>
                <p className="mt-2 text-sm text-slate-700">{event.message || '無 message'}</p>
              </button>
            </article>
          )
        })}
      </div>
    </section>
  )
}

