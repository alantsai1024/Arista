'use client'

import { X } from 'lucide-react'
import { formatDateTime } from '@/app/lib/format'
import type { TimelineEvent } from '@/app/lib/types'

interface MetadataDrawerProps {
  event: TimelineEvent | null
  onClose: () => void
}

export default function MetadataDrawer({ event, onClose }: MetadataDrawerProps) {
  return (
    <div className={`fixed inset-0 z-40 ${event ? 'pointer-events-auto' : 'pointer-events-none'}`}>
      <div
        className={`absolute inset-0 bg-slate-900/40 backdrop-blur-[1px] transition-opacity ${event ? 'opacity-100' : 'opacity-0'}`}
        onClick={onClose}
      />
      <aside
        className={`absolute right-0 top-0 h-full w-full max-w-lg transform border-l border-slate-200 bg-white shadow-2xl transition-transform ${
          event ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        <header className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
          <div>
            <p className="text-sm font-semibold text-slate-900">事件 Metadata</p>
            <p className="text-xs text-slate-500">{event ? formatDateTime(event.created_at) : ''}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50 hover:text-slate-700"
          >
            <X className="h-4 w-4" />
          </button>
        </header>
        <div className="space-y-3 overflow-y-auto p-5">
          {event ? (
            <>
              <div className="rounded-xl bg-slate-50 p-3">
                <p className="text-xs text-slate-500">Event Type</p>
                <p className="text-sm font-semibold text-slate-900">{event.event_type}</p>
              </div>
              <div className="rounded-xl bg-slate-50 p-3">
                <p className="text-xs text-slate-500">Message</p>
                <p className="text-sm text-slate-800">{event.message || '無 message'}</p>
              </div>
              <div className="rounded-xl bg-slate-950 p-3">
                <p className="mb-2 text-xs text-slate-300">metadata JSON</p>
                <pre className="max-h-[65vh] overflow-auto text-xs text-emerald-200">
                  {JSON.stringify(event.metadataObject ?? {}, null, 2)}
                </pre>
              </div>
            </>
          ) : (
            <p className="text-sm text-slate-500">選擇一筆事件即可查看 metadata。</p>
          )}
        </div>
      </aside>
    </div>
  )
}

