'use client'

import { useEffect, useMemo, useState } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table'
import { Download, Pencil, Plug, Plus, Trash2 } from 'lucide-react'
import {
  createDevice,
  deleteDevice,
  getFleetSnapshot,
  mergeDeviceRows,
  testDeviceConnection,
  updateDevice,
} from '@/app/lib/api'
import {
  clampNumber,
  formatLatency,
  formatRelativeTime,
  queryStringFromRecord,
  toNumber,
} from '@/app/lib/format'
import type { Device, DeviceCreatePayload, DeviceListRow, DeviceUpdatePayload } from '@/app/lib/types'
import StatusBadge from '@/app/components/ui/StatusBadge'
import InlineAlert from '@/app/components/feedback/InlineAlert'
import DeviceFormModal from '@/app/components/forms/DeviceFormModal'
import ConfirmDialog from '@/app/components/forms/ConfirmDialog'
import { useToast } from '@/app/components/feedback/ToastProvider'
import { exportDevicesCsv, exportDevicesJson, exportDevicesPdf } from '@/app/lib/export'

interface QueryState {
  q: string
  status: string
  enabled: string
  sort: string
  page: number
  pageSize: number
}

const DEFAULT_QUERY: QueryState = {
  q: '',
  status: 'all',
  enabled: 'all',
  sort: 'hostname.asc',
  page: 1,
  pageSize: 10,
}

function parseQuery(searchParams: Pick<URLSearchParams, 'get'>): QueryState {
  const pageSize = clampNumber(toNumber(searchParams.get('pageSize'), DEFAULT_QUERY.pageSize), 5, 100)
  return {
    q: searchParams.get('q') ?? DEFAULT_QUERY.q,
    status: searchParams.get('status') ?? DEFAULT_QUERY.status,
    enabled: searchParams.get('enabled') ?? DEFAULT_QUERY.enabled,
    sort: searchParams.get('sort') ?? DEFAULT_QUERY.sort,
    page: clampNumber(toNumber(searchParams.get('page'), DEFAULT_QUERY.page), 1, 10000),
    pageSize,
  }
}

function sortingFromQuery(sort: string): SortingState {
  const [column, direction] = sort.split('.')
  return [{ id: column || 'hostname', desc: direction === 'desc' }]
}

function queryFromSorting(sorting: SortingState): string {
  const first = sorting[0]
  if (!first) return 'hostname.asc'
  return `${first.id}.${first.desc ? 'desc' : 'asc'}`
}

export default function DevicesPage() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { pushToast } = useToast()

  const [rows, setRows] = useState<DeviceListRow[]>([])
  const [devices, setDevices] = useState<Device[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [warnings, setWarnings] = useState<string[]>([])
  const [formMode, setFormMode] = useState<'create' | 'edit'>('create')
  const [formOpen, setFormOpen] = useState(false)
  const [formBusy, setFormBusy] = useState(false)
  const [targetDevice, setTargetDevice] = useState<Device | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<DeviceListRow | null>(null)
  const [deleteBusy, setDeleteBusy] = useState(false)
  const [queryState, setQueryState] = useState<QueryState>(DEFAULT_QUERY)
  const searchKey = searchParams.toString()

  useEffect(() => {
    const parsed = parseQuery(new URLSearchParams(searchKey))
    setQueryState((prev) => {
      if (
        prev.q === parsed.q
        && prev.status === parsed.status
        && prev.enabled === parsed.enabled
        && prev.sort === parsed.sort
        && prev.page === parsed.page
        && prev.pageSize === parsed.pageSize
      ) {
        return prev
      }
      return parsed
    })
  }, [searchKey])

  function updateQuery(patch: Partial<QueryState>) {
    setQueryState((prev) => {
      const next = { ...prev, ...patch }
      if (
        next.q === prev.q
        && next.status === prev.status
        && next.enabled === prev.enabled
        && next.sort === prev.sort
        && next.page === prev.page
        && next.pageSize === prev.pageSize
      ) {
        return prev
      }

      const query = queryStringFromRecord({
        q: next.q || undefined,
        status: next.status !== 'all' ? next.status : undefined,
        enabled: next.enabled !== 'all' ? next.enabled : undefined,
        sort: next.sort !== 'hostname.asc' ? next.sort : undefined,
        page: next.page !== 1 ? next.page : undefined,
        pageSize: next.pageSize !== 10 ? next.pageSize : undefined,
      })
      const currentQuery = searchKey
      if (query !== currentQuery) {
        router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false })
      }
      return next
    })
  }

  async function fetchData() {
    try {
      setRefreshing(true)
      const snapshot = await getFleetSnapshot()
      const sourceDevices = snapshot.devices ?? []
      setDevices(sourceDevices)
      setRows(mergeDeviceRows(sourceDevices, snapshot.health?.devices ?? []))
      setWarnings(snapshot.warnings)
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知錯誤'
      setWarnings([message])
      pushToast({ type: 'error', title: '載入設備管理失敗', description: message })
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => {
    void fetchData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const columnFilters = useMemo<ColumnFiltersState>(() => {
    const filters: ColumnFiltersState = []
    if (queryState.status !== 'all') filters.push({ id: 'status', value: queryState.status })
    if (queryState.enabled !== 'all') filters.push({ id: 'enabled', value: queryState.enabled === 'true' })
    return filters
  }, [queryState.status, queryState.enabled])

  const columns = useMemo<ColumnDef<DeviceListRow>[]>(() => [
    {
      accessorKey: 'hostname',
      header: 'Hostname',
      cell: ({ row }) => (
        <button
          type="button"
          className="font-medium text-slate-900 hover:text-brand-600"
          onClick={() => router.push(`/devices/${row.original.id}`)}
        >
          {row.original.hostname || row.original.id}
        </button>
      ),
    },
    {
      accessorKey: 'ip',
      header: 'IP',
      cell: ({ getValue }) => <span className="font-mono text-xs">{String(getValue())}</span>,
    },
    {
      accessorKey: 'status',
      header: '狀態',
      filterFn: (row, id, filterValue) => row.getValue(id) === filterValue,
      cell: ({ getValue }) => <StatusBadge status={String(getValue())} />,
    },
    {
      accessorKey: 'latencyMs',
      header: 'Latency',
      cell: ({ getValue }) => formatLatency(getValue<number | null>()),
    },
    {
      accessorKey: 'eventsLastHour',
      header: 'Events/hr',
      cell: ({ getValue }) => <span>{String(getValue<number>())}</span>,
    },
    {
      accessorKey: 'intervalSec',
      header: 'Interval',
      cell: ({ getValue }) => <span>{String(getValue<number>())}s</span>,
    },
    {
      accessorKey: 'enabled',
      header: '啟用',
      filterFn: (row, id, filterValue) => row.getValue(id) === filterValue,
      cell: ({ getValue }) => (
        <span className={`rounded-full px-2 py-1 text-xs font-semibold ${getValue<boolean>() ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-600'}`}>
          {getValue<boolean>() ? '是' : '否'}
        </span>
      ),
    },
    {
      accessorKey: 'lastSeen',
      header: '最後上線',
      cell: ({ row }) => <span className="text-xs text-slate-600">{formatRelativeTime(row.original.lastSeen || row.original.lastEventAt)}</span>,
    },
    {
      id: 'actions',
      header: '操作',
      cell: ({ row }) => (
        <div className="flex flex-wrap gap-1">
          <button type="button" className="icon-btn" onClick={() => {
            const match = devices.find((item) => item.id === row.original.id) || null
            setTargetDevice(match)
            setFormMode('edit')
            setFormOpen(true)
          }} aria-label="編輯設備">
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button type="button" className="icon-btn" onClick={() => void handleToggleEnabled(row.original)} aria-label="切換啟用狀態">
            {row.original.enabled ? '停用' : '啟用'}
          </button>
          <button type="button" className="icon-btn" onClick={() => void handleTestConnection(row.original)} aria-label="連線測試">
            <Plug className="h-3.5 w-3.5" />
          </button>
          <button type="button" className="icon-btn text-rose-600 hover:text-rose-700" onClick={() => setDeleteTarget(row.original)} aria-label="刪除設備">
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      ),
    },
  // eslint-disable-next-line react-hooks/exhaustive-deps
  ], [devices, router])

  const sortingState = useMemo(() => sortingFromQuery(queryState.sort), [queryState.sort])
  const paginationState = useMemo(
    () => ({
      pageIndex: queryState.page - 1,
      pageSize: queryState.pageSize,
    }),
    [queryState.page, queryState.pageSize],
  )

  const table = useReactTable({
    data: rows,
    columns,
    state: {
      globalFilter: queryState.q,
      columnFilters,
      sorting: sortingState,
      pagination: paginationState,
    },
    globalFilterFn: (row, _, filterValue) => {
      const keyword = String(filterValue).toLowerCase().trim()
      if (!keyword) return true
      const source = `${row.original.hostname ?? ''} ${row.original.ip}`.toLowerCase()
      return source.includes(keyword)
    },
    onSortingChange: (updater) => {
      const current = sortingState
      const next = typeof updater === 'function' ? updater(current) : updater
      const nextSort = queryFromSorting(next)
      if (nextSort === queryState.sort) return
      updateQuery({ sort: nextSort, page: 1 })
    },
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  })

  async function handleCreateOrUpdate(payload: DeviceCreatePayload | DeviceUpdatePayload) {
    try {
      setFormBusy(true)
      if (formMode === 'create') {
        await createDevice(payload as DeviceCreatePayload)
        pushToast({ type: 'success', title: '設備已建立' })
      } else if (targetDevice) {
        await updateDevice(targetDevice.id, payload as DeviceUpdatePayload)
        pushToast({ type: 'success', title: '設備已更新' })
      }
      setFormOpen(false)
      await fetchData()
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知錯誤'
      pushToast({ type: 'error', title: '操作失敗', description: message })
    } finally {
      setFormBusy(false)
    }
  }

  async function handleToggleEnabled(row: DeviceListRow) {
    try {
      await updateDevice(row.id, { enabled: !row.enabled })
      pushToast({ type: 'success', title: row.enabled ? '設備已停用' : '設備已啟用' })
      await fetchData()
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知錯誤'
      pushToast({ type: 'error', title: '切換啟用狀態失敗', description: message })
    }
  }

  async function handleTestConnection(row: DeviceListRow) {
    try {
      const result = await testDeviceConnection(row.id)
      pushToast({
        type: result.success ? 'success' : 'error',
        title: result.success ? '連線測試成功' : '連線測試失敗',
        description: result.message,
      })
      await fetchData()
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知錯誤'
      pushToast({ type: 'error', title: '連線測試失敗', description: message })
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return
    try {
      setDeleteBusy(true)
      await deleteDevice(deleteTarget.id)
      setDeleteTarget(null)
      pushToast({ type: 'success', title: '設備已刪除' })
      await fetchData()
    } catch (error) {
      const message = error instanceof Error ? error.message : '未知錯誤'
      pushToast({ type: 'error', title: '刪除失敗', description: message })
    } finally {
      setDeleteBusy(false)
    }
  }

  const filteredRows = table.getFilteredRowModel().rows.map((item) => item.original)
  const pagedRows = table.getRowModel().rows

  if (loading) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-7 sm:px-6 lg:px-8">
        <section className="card-surface flex min-h-[320px] items-center justify-center text-sm text-slate-600">
          載入設備管理中...
        </section>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-7xl space-y-5 px-4 py-7 sm:px-6 lg:px-8">
      <section className="card-surface p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Device Operations</p>
            <h1 className="font-display mt-2 text-3xl font-semibold">設備管理中心</h1>
            <p className="mt-1 text-sm text-slate-600">
              支援查詢、排序、分頁、CRUD、連線測試與 CSV/JSON/PDF 匯出
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" className="btn-secondary" onClick={() => {
              setTargetDevice(null)
              setFormMode('create')
              setFormOpen(true)
            }}>
              <span className="inline-flex items-center gap-1.5"><Plus className="h-4 w-4" />新增設備</span>
            </button>
            <button type="button" className="btn-secondary" onClick={() => {
              exportDevicesCsv(filteredRows)
              pushToast({ type: 'success', title: '已匯出 CSV' })
            }}>
              <span className="inline-flex items-center gap-1.5"><Download className="h-4 w-4" />CSV</span>
            </button>
            <button type="button" className="btn-secondary" onClick={() => {
              exportDevicesJson(filteredRows)
              pushToast({ type: 'success', title: '已匯出 JSON' })
            }}>
              <span className="inline-flex items-center gap-1.5"><Download className="h-4 w-4" />JSON</span>
            </button>
            <button type="button" className="btn-secondary" onClick={async () => {
              try {
                await exportDevicesPdf(filteredRows)
                pushToast({ type: 'success', title: '已匯出 PDF' })
              } catch (error) {
                const message = error instanceof Error ? error.message : '未知錯誤'
                pushToast({ type: 'error', title: 'PDF 匯出失敗', description: message })
              }
            }}>
              <span className="inline-flex items-center gap-1.5"><Download className="h-4 w-4" />PDF</span>
            </button>
            <button type="button" className="btn-secondary" onClick={() => void fetchData()}>
              {refreshing ? '更新中...' : '刷新資料'}
            </button>
          </div>
        </div>
      </section>

      {warnings.length > 0 && <InlineAlert title="資料來源警告" details={warnings} variant="warning" />}

      <section className="card-surface p-4">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
          <label className="field-group md:col-span-2">
            <span className="field-label">搜尋</span>
            <input
              className="field-input"
              value={queryState.q}
              placeholder="hostname 或 IP"
              onChange={(event) => updateQuery({ q: event.target.value, page: 1 })}
            />
          </label>
          <label className="field-group">
            <span className="field-label">狀態</span>
            <select className="field-input" value={queryState.status} onChange={(event) => updateQuery({ status: event.target.value, page: 1 })}>
              <option value="all">全部</option>
              <option value="online">在線</option>
              <option value="degraded">降級</option>
              <option value="offline">離線</option>
              <option value="ip_conflict">IP 衝突</option>
              <option value="unknown">未知</option>
            </select>
          </label>
          <label className="field-group">
            <span className="field-label">啟用</span>
            <select className="field-input" value={queryState.enabled} onChange={(event) => updateQuery({ enabled: event.target.value, page: 1 })}>
              <option value="all">全部</option>
              <option value="true">已啟用</option>
              <option value="false">已停用</option>
            </select>
          </label>
          <label className="field-group">
            <span className="field-label">每頁筆數</span>
            <select className="field-input" value={String(queryState.pageSize)} onChange={(event) => updateQuery({ pageSize: Number(event.target.value), page: 1 })}>
              <option value="10">10</option>
              <option value="20">20</option>
              <option value="50">50</option>
            </select>
          </label>
        </div>
      </section>

      <section className="card-surface overflow-hidden" data-testid="devices-table">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[1150px]">
            <thead className="bg-slate-50">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-3 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500"
                    >
                      {header.isPlaceholder ? null : (
                        <button
                          type="button"
                          onClick={header.column.getToggleSortingHandler()}
                          className="inline-flex items-center gap-1"
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
                        </button>
                      )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {pagedRows.length === 0 && (
                <tr>
                  <td colSpan={columns.length} className="px-3 py-8 text-center text-sm text-slate-500">
                    沒有符合條件的設備。
                  </td>
                </tr>
              )}
              {pagedRows.map((row) => (
                <tr key={row.id} className="border-t border-slate-200 text-sm hover:bg-slate-50">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-3 py-3 align-top">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between border-t border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
          <p>
            共 {filteredRows.length} 筆，頁 {queryState.page} / {Math.max(table.getPageCount(), 1)}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              className="btn-secondary py-1.5"
              onClick={() => updateQuery({ page: Math.max(1, queryState.page - 1) })}
              disabled={!table.getCanPreviousPage()}
            >
              上一頁
            </button>
            <button
              type="button"
              className="btn-secondary py-1.5"
              onClick={() => updateQuery({ page: queryState.page + 1 })}
              disabled={!table.getCanNextPage()}
            >
              下一頁
            </button>
          </div>
        </div>
      </section>

      <DeviceFormModal
        open={formOpen}
        mode={formMode}
        initialDevice={targetDevice}
        submitting={formBusy}
        onClose={() => setFormOpen(false)}
        onSubmit={handleCreateOrUpdate}
      />

      <ConfirmDialog
        open={!!deleteTarget}
        title="刪除設備"
        description={deleteTarget ? `確定刪除 ${deleteTarget.hostname || deleteTarget.ip}？` : ''}
        confirmLabel="刪除"
        busy={deleteBusy}
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />
    </main>
  )
}

