'use client'

import { useEffect, useMemo, useState } from 'react'
import { X } from 'lucide-react'
import type { Device, DeviceCreatePayload, DeviceUpdatePayload } from '@/app/lib/types'

type Mode = 'create' | 'edit'

interface DeviceFormModalProps {
  open: boolean
  mode: Mode
  initialDevice?: Device | null
  submitting: boolean
  onClose: () => void
  onSubmit: (payload: DeviceCreatePayload | DeviceUpdatePayload) => Promise<void>
}

interface FormState {
  hostname: string
  ip: string
  port: number
  username: string
  password: string
  interval_sec: number
  enabled: boolean
}

const initialState: FormState = {
  hostname: '',
  ip: '',
  port: 443,
  username: '',
  password: '',
  interval_sec: 10,
  enabled: true,
}

export default function DeviceFormModal({
  open,
  mode,
  initialDevice,
  submitting,
  onClose,
  onSubmit,
}: DeviceFormModalProps) {
  const [form, setForm] = useState<FormState>(initialState)
  const [errors, setErrors] = useState<string[]>([])

  useEffect(() => {
    if (!open) return
    if (mode === 'edit' && initialDevice) {
      setForm({
        hostname: initialDevice.hostname ?? '',
        ip: initialDevice.ip,
        port: initialDevice.port,
        username: initialDevice.username,
        password: '',
        interval_sec: initialDevice.interval_sec,
        enabled: initialDevice.enabled,
      })
      setErrors([])
      return
    }
    setForm(initialState)
    setErrors([])
  }, [open, mode, initialDevice])

  const title = useMemo(() => (mode === 'create' ? '新增設備' : '編輯設備'), [mode])

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const validationErrors: string[] = []
    if (!form.ip.trim()) validationErrors.push('IP 不可為空')
    if (!form.username.trim()) validationErrors.push('帳號不可為空')
    if (mode === 'create' && !form.password.trim()) validationErrors.push('建立設備時必須輸入密碼')
    if (form.interval_sec < 5 || form.interval_sec > 300) validationErrors.push('輪詢間隔需在 5 到 300 秒')

    if (validationErrors.length > 0) {
      setErrors(validationErrors)
      return
    }

    if (mode === 'create') {
      await onSubmit({
        hostname: form.hostname.trim() || null,
        ip: form.ip.trim(),
        port: Number(form.port),
        username: form.username.trim(),
        password: form.password,
        interval_sec: Number(form.interval_sec),
        enabled: form.enabled,
      })
      return
    }

    const payload: DeviceUpdatePayload = {
      hostname: form.hostname.trim() || null,
      ip: form.ip.trim(),
      port: Number(form.port),
      username: form.username.trim(),
      interval_sec: Number(form.interval_sec),
      enabled: form.enabled,
    }
    if (form.password.trim()) payload.password = form.password
    await onSubmit(payload)
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-40">
      <div className="absolute inset-0 bg-slate-900/30" onClick={onClose} />
      <div className="absolute left-1/2 top-1/2 w-full max-w-2xl -translate-x-1/2 -translate-y-1/2 rounded-3xl border border-slate-200 bg-white p-6 shadow-2xl">
        <header className="mb-5 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">{title}</h2>
            <p className="text-sm text-slate-500">欄位直接對應後端 `/devices` API</p>
          </div>
          <button type="button" className="rounded-lg border border-slate-200 p-2" onClick={onClose}>
            <X className="h-4 w-4" />
          </button>
        </header>

        {errors.length > 0 && (
          <div className="mb-4 rounded-2xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
            {errors.map((error) => (
              <p key={error}>{error}</p>
            ))}
          </div>
        )}

        <form className="grid grid-cols-1 gap-4 md:grid-cols-2" onSubmit={handleSubmit}>
          <label className="field-group md:col-span-2">
            <span className="field-label">Hostname</span>
            <input
              className="field-input"
              value={form.hostname}
              onChange={(e) => setForm((prev) => ({ ...prev, hostname: e.target.value }))}
              placeholder="例如 leaf-01"
            />
          </label>

          <label className="field-group">
            <span className="field-label">IP</span>
            <input
              className="field-input"
              value={form.ip}
              required
              onChange={(e) => setForm((prev) => ({ ...prev, ip: e.target.value }))}
              placeholder="192.168.56.2"
            />
          </label>

          <label className="field-group">
            <span className="field-label">Port</span>
            <input
              className="field-input"
              value={form.port}
              type="number"
              min={1}
              max={65535}
              onChange={(e) => setForm((prev) => ({ ...prev, port: Number(e.target.value) }))}
            />
          </label>

          <label className="field-group">
            <span className="field-label">Username</span>
            <input
              className="field-input"
              value={form.username}
              required
              onChange={(e) => setForm((prev) => ({ ...prev, username: e.target.value }))}
              placeholder="admin"
            />
          </label>

          <label className="field-group">
            <span className="field-label">Password {mode === 'edit' ? '(留空不改)' : ''}</span>
            <input
              className="field-input"
              value={form.password}
              type="password"
              required={mode === 'create'}
              onChange={(e) => setForm((prev) => ({ ...prev, password: e.target.value }))}
            />
          </label>

          <label className="field-group">
            <span className="field-label">Interval (sec)</span>
            <input
              className="field-input"
              value={form.interval_sec}
              type="number"
              min={5}
              max={300}
              onChange={(e) => setForm((prev) => ({ ...prev, interval_sec: Number(e.target.value) }))}
            />
          </label>

          <label className="field-group">
            <span className="field-label">Enabled</span>
            <select
              className="field-input"
              value={String(form.enabled)}
              onChange={(e) => setForm((prev) => ({ ...prev, enabled: e.target.value === 'true' }))}
            >
              <option value="true">啟用</option>
              <option value="false">停用</option>
            </select>
          </label>

          <div className="mt-2 flex justify-end gap-2 md:col-span-2">
            <button type="button" className="btn-secondary" onClick={onClose}>取消</button>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? '送出中...' : mode === 'create' ? '建立設備' : '儲存變更'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

