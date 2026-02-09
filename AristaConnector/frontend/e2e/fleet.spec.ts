import { expect, test } from '@playwright/test'

let mockCounter = 0

test.beforeEach(async ({ page }) => {
  await page.route('**://localhost:8000/devices', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'device-1',
          hostname: 'switch-01',
          ip: '192.168.1.1',
          port: 443,
          username: 'admin',
          interval_sec: 10,
          enabled: true,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: null,
        },
        {
          id: 'device-2',
          hostname: 'switch-02',
          ip: '192.168.1.2',
          port: 443,
          username: 'admin',
          interval_sec: 10,
          enabled: true,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: null,
        },
        {
          id: 'device-3',
          hostname: 'switch-03',
          ip: '192.168.1.3',
          port: 443,
          username: 'admin',
          interval_sec: 10,
          enabled: true,
          created_at: '2024-01-01T00:00:00Z',
          updated_at: null,
        },
      ]),
    })
  })

  await page.route('**://localhost:8000/health/fleet', async (route) => {
    mockCounter += 1
    const online = 1 + (mockCounter % 2)
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total_devices: 3,
        online_devices: online,
        degraded_devices: 1,
        offline_devices: 3 - online - 1,
        devices: [
          {
            device_id: 'device-1',
            status: online === 2 ? 'online' : 'offline',
            last_seen: new Date().toISOString(),
            online: online === 2,
            recent_stats: {
              total_events_last_hour: 40 + mockCounter,
              events_by_type: { poll_success: 30, poll_error: 10 },
              latency_ms: 30 + mockCounter,
            },
          },
          {
            device_id: 'device-2',
            status: 'degraded',
            last_seen: new Date().toISOString(),
            online: false,
            recent_stats: {
              total_events_last_hour: 20 + mockCounter,
              events_by_type: { poll_success: 12, poll_error: 8 },
              latency_ms: 80 + mockCounter,
            },
          },
          {
            device_id: 'device-3',
            status: 'offline',
            last_seen: null,
            online: false,
            recent_stats: {
              total_events_last_hour: 10 + mockCounter,
              events_by_type: { poll_error: 10 },
              latency_ms: null,
            },
          },
        ],
        top_latency_devices: [
          { device_id: 'device-2', hostname: 'switch-02', ip: '192.168.1.2', latency_ms: 88 },
        ],
      }),
    })
  })
})

test('fleet dashboard renders charts and anomaly table', async ({ page }) => {
  await page.goto('/fleet')

  await expect(page.locator('h1')).toContainText('現代化監控總覽')
  await expect(page.getByTestId('fleet-kpi-cards')).toBeVisible()
  await expect(page.getByTestId('status-donut-chart')).toBeVisible()
  await expect(page.getByTestId('latency-bar-chart')).toBeVisible()
  await expect(page.getByTestId('event-type-bar-chart')).toBeVisible()
  await expect(page.getByTestId('health-trend-sparkline')).toBeVisible()
  await expect(page.getByText('異常設備表')).toBeVisible()
  await expect(page.locator('table').getByText('switch-03')).toBeVisible()
})

test('fleet dashboard auto refresh updates KPI values', async ({ page }) => {
  await page.goto('/fleet')

  const kpiCards = page.getByTestId('fleet-kpi-cards').locator('article')
  const initialOnline = await kpiCards.nth(1).locator('p').nth(1).textContent()
  await page.waitForTimeout(12000)
  const refreshedOnline = await kpiCards.nth(1).locator('p').nth(1).textContent()
  expect(refreshedOnline).not.toEqual(initialOnline)
})

test('fleet dashboard still works when health API fails', async ({ page }) => {
  await page.unroute('**://localhost:8000/health/fleet')
  await page.route('**://localhost:8000/health/fleet', async (route) => {
    await route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'service unavailable' }),
    })
  })

  await page.goto('/fleet')

  await expect(page.locator('h1')).toContainText('現代化監控總覽')
  await expect(page.getByText('資料來源警告')).toBeVisible()
  await expect(page.getByText('/health/fleet 讀取失敗')).toBeVisible()
  await expect(page.locator('table').getByText('switch-01')).toBeVisible()
})

test('anomaly row click opens device detail page', async ({ page }) => {
  await page.route('**://localhost:8000/devices/device-3', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'device-3',
        hostname: 'switch-03',
        ip: '192.168.1.3',
        port: 443,
        username: 'admin',
        interval_sec: 10,
        enabled: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: null,
      }),
    })
  })

  await page.route('**://localhost:8000/devices/device-3/status', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        device_id: 'device-3',
        status: 'offline',
        last_seen: null,
        online: false,
        recent_stats: { total_events_last_hour: 9, latency_ms: null },
      }),
    })
  })

  await page.route('**://localhost:8000/devices/device-3/events*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'ev-1',
          device_id: 'device-3',
          event_type: 'poll_error',
          message: 'connection timeout',
          metadata: { error: 'timeout' },
          created_at: '2026-01-01T10:00:00Z',
        },
      ]),
    })
  })

  await page.goto('/fleet')
  await page.locator('table').getByText('switch-03').click()
  await expect(page).toHaveURL(/\/devices\/device-3/)
  await expect(page.locator('h1')).toContainText('switch-03')
  await expect(page.getByTestId('device-event-timeline')).toBeVisible()
})
