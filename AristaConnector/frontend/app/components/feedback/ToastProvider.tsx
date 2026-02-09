'use client'

import { CheckCircle2, CircleAlert, Info, X } from 'lucide-react'
import React, { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { cn } from '@/app/lib/format'

type ToastType = 'success' | 'error' | 'info'

interface ToastItem {
  id: string
  type: ToastType
  title: string
  description?: string
}

interface ToastContextValue {
  pushToast: (toast: Omit<ToastItem, 'id'>) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

function typeIcon(type: ToastType) {
  if (type === 'success') return CheckCircle2
  if (type === 'error') return CircleAlert
  return Info
}

function typeClass(type: ToastType) {
  if (type === 'success') return 'border-emerald-200 bg-emerald-50 text-emerald-900'
  if (type === 'error') return 'border-rose-200 bg-rose-50 text-rose-900'
  return 'border-sky-200 bg-sky-50 text-sky-900'
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((item) => item.id !== id))
  }, [])

  const pushToast = useCallback((toast: Omit<ToastItem, 'id'>) => {
    const id = `${Date.now()}-${Math.random().toString(16).slice(2)}`
    setToasts((prev) => [...prev, { ...toast, id }])
    setTimeout(() => removeToast(id), 4500)
  }, [removeToast])

  const value = useMemo(() => ({ pushToast }), [pushToast])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed right-5 top-20 z-50 flex w-[360px] flex-col gap-3">
        {toasts.map((toast) => {
          const Icon = typeIcon(toast.type)
          return (
            <div
              key={toast.id}
              className={cn(
                'pointer-events-auto rounded-2xl border px-4 py-3 shadow-lg backdrop-blur animate-fade-up',
                typeClass(toast.type),
              )}
            >
              <div className="flex items-start gap-3">
                <Icon className="mt-0.5 h-5 w-5 shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-semibold">{toast.title}</p>
                  {toast.description && (
                    <p className="mt-1 text-xs opacity-80">{toast.description}</p>
                  )}
                </div>
                <button
                  type="button"
                  className="rounded-md p-1 hover:bg-black/5"
                  onClick={() => removeToast(toast.id)}
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast 必須在 ToastProvider 內使用')
  }
  return context
}

