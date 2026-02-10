import { expect, test, type Locator } from '@playwright/test'

interface MockDevice {
  id: string
  hostname: string | null
  ip: string
  port: number
  username: string
  interval_sec: number
  enabled: boolean
  created_at: string
  updated_at: string | null
}

async function setInputValue(locator: Locator, value: string) {
  await locator.evaluate((element: HTMLInputElement, newValue: string) => {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value')?.set
    setter?.call(element, newValue)
    element.dispatchEvent(new Event('input', { bubbles: true }))
    element.dispatchEvent(new Event('change', { bubbles: true }))
  }, value)
}

test.beforeEach(async ({ page }) => {
  let devices: MockDevice[] = [
    {
      id: 'device-1',
      hostname: 'leaf-01',
      ip: '192.168.56.2',
      port: 443,
      username: 'admin',
      interval_sec: 10,
      enabled: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: null,
    },
    {
      id: 'device-2',
      hostname: 'leaf-02',
      ip: '192.168.56.3',
      port: 443,
      username: 'admin',
      interval_sec: 20,
      enabled: true,
      created_at: '2026-01-01T00:00:00Z',
      updated_at: null,
    },
  ]

  const statusMap: Record<string, { status: string; online: boolean; latency: number | null; events: number }> = {
    'device-1': { status: 'online', online: true, latency: 32, events: 24 },
    'device-2': { status: 'ip_conflict', online: false, latency: 88, events: 11 },
  }

  await page.route('**://localhost:8000/health/fleet', async (route) => {
    const payload = {
      total_devices: devices.length,
      online_devices: devices.filter((device) => statusMap[device.id]?.status === 'online').length,
      degraded_devices: devices.filter((device) => statusMap[device.id]?.status === 'degraded').length,
      offline_devices: devices.filter((device) => {
        const status = statusMap[device.id]?.status ?? 'unknown'
        return status !== 'online' && status !== 'degraded'
      }).length,
      devices: devices.map((device) => ({
        device_id: device.id,
        status: statusMap[device.id]?.status ?? 'unknown',
        last_seen: new Date().toISOString(),
        online: statusMap[device.id]?.online ?? false,
        recent_stats: {
          total_events_last_hour: statusMap[device.id]?.events ?? 0,
          events_by_type: { poll_success: 8, poll_error: 2 },
          last_event_at: new Date().toISOString(),
          latency_ms: statusMap[device.id]?.latency ?? null,
        },
      })),
      top_latency_devices: devices.map((device) => ({
        device_id: device.id,
        hostname: device.hostname,
        ip: device.ip,
        latency_ms: statusMap[device.id]?.latency ?? null,
      })),
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(payload),
    })
  })

  await page.route('**://localhost:8000/devices**', async (route) => {
    const request = route.request()
    const method = request.method()
    const url = new URL(request.url())
    const path = url.pathname

    if (path === '/devices' && method === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(devices),
      })
      return
    }

    if (path === '/devices' && method === 'POST') {
      const body = request.postDataJSON() as {
        hostname?: string
        ip: string
        port: number
        username: string
        interval_sec: number
        enabled: boolean
      }
      const id = `device-${devices.length + 1}`
      const created: MockDevice = {
        id,
        hostname: body.hostname ?? null,
        ip: body.ip,
        port: body.port,
        username: body.username,
        interval_sec: body.interval_sec,
        enabled: body.enabled,
        created_at: new Date().toISOString(),
        updated_at: null,
      }
      devices = [...devices, created]
      statusMap[id] = { status: 'online', online: true, latency: 55, events: 0 }
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(created) })
      return
    }

    const idMatch = path.match(/^\/devices\/([^/]+)$/)
    if (idMatch && method === 'PATCH') {
      const id = idMatch[1]
      const payload = request.postDataJSON() as Partial<MockDevice>
      devices = devices.map((device) => {
        if (device.id !== id) return device
        return {
          ...device,
          ...payload,
          updated_at: new Date().toISOString(),
        }
      })
      const updated = devices.find((device) => device.id === id)
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(updated),
      })
      return
    }

    if (idMatch && method === 'DELETE') {
      const id = idMatch[1]
      devices = devices.filter((device) => device.id !== id)
      delete statusMap[id]
      await route.fulfill({ status: 204, body: '' })
      return
    }

    const testMatch = path.match(/^\/devices\/([^/]+)\/test-connection$/)
    if (testMatch && method === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          message: 'connection ok',
          hostname: 'mock-host',
        }),
      })
      return
    }

    await route.fulfill({ status: 404, body: 'not found' })
  })
})

test('devices page supports CRUD operations, test connection, and export', async ({ page }) => {
  await page.goto('/devices')

  await expect(page.locator('h1')).toContainText('設備管理中心')
  await expect(page.getByTestId('devices-table')).toBeVisible()
  await expect(page.locator('table').getByText('leaf-01')).toBeVisible()
  await expect(page.locator('table').getByText('IP 衝突')).toBeVisible()

  await page.getByRole('button', { name: '新增設備' }).dispatchEvent('click')
  const modal = page.locator('div.fixed.inset-0').last()
  await expect(modal).toBeVisible()
  await setInputValue(modal.getByLabel('Hostname'), 'leaf-03')
  await setInputValue(modal.getByLabel('IP'), '10.10.10.10')
  await setInputValue(modal.getByLabel('Username'), 'admin')
  await setInputValue(modal.getByLabel('Password'), 'secret123')
  await page.getByRole('button', { name: '建立設備' }).dispatchEvent('click')
  await expect(page.locator('table').getByText('10.10.10.10')).toBeVisible()

  const row = page.locator('tr', { hasText: '10.10.10.10' })
  await row.getByRole('button', { name: '切換啟用狀態' }).click()
  await expect(row.getByText('否')).toBeVisible()

  await row.getByRole('button', { name: '連線測試' }).click()
  await expect(page.getByText('連線測試成功')).toBeVisible()

  await row.getByRole('button', { name: '刪除設備' }).dispatchEvent('click')
  await page.getByRole('button', { name: '刪除', exact: true }).dispatchEvent('click')
  await expect(page.locator('table').getByText('10.10.10.10')).toHaveCount(0)

  await page.getByRole('button', { name: /CSV/i }).dispatchEvent('click')
  await expect(page.getByText('已匯出 CSV')).toBeVisible()
})

test('devices page can filter ip_conflict status', async ({ page }) => {
  await page.goto('/devices')

  const statusFilter = page.locator('label:has-text("狀態") select').first()
  await statusFilter.selectOption('ip_conflict')
  await expect(statusFilter).toHaveValue('ip_conflict')
  await expect(page.locator('table').getByText('leaf-02')).toBeVisible()
  await expect(page.locator('table').getByText('leaf-01')).toHaveCount(0)
})
