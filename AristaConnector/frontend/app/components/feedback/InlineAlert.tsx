import { AlertTriangle, Info, TriangleAlert } from 'lucide-react'
import { cn } from '@/app/lib/format'

type AlertVariant = 'warning' | 'info' | 'error'

interface InlineAlertProps {
  title: string
  details?: string[]
  variant?: AlertVariant
}

function variantClass(variant: AlertVariant) {
  if (variant === 'error') return 'border-rose-200 bg-rose-50 text-rose-900'
  if (variant === 'warning') return 'border-amber-200 bg-amber-50 text-amber-900'
  return 'border-sky-200 bg-sky-50 text-sky-900'
}

function variantIcon(variant: AlertVariant) {
  if (variant === 'error') return TriangleAlert
  if (variant === 'warning') return AlertTriangle
  return Info
}

export default function InlineAlert({ title, details = [], variant = 'warning' }: InlineAlertProps) {
  const Icon = variantIcon(variant)
  return (
    <div className={cn('rounded-2xl border p-4', variantClass(variant))}>
      <div className="flex items-start gap-3">
        <Icon className="mt-0.5 h-5 w-5 shrink-0" />
        <div className="space-y-2">
          <p className="text-sm font-semibold">{title}</p>
          {details.length > 0 && (
            <ul className="space-y-1 text-xs">
              {details.map((detail) => (
                <li key={detail}>{detail}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}

