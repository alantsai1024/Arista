import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.route('**://localhost:8000/devices/device-1', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'device-1',
        hostname: 'leaf-01',
        ip: '192.168.56.2',
        port: 443,
        username: 'admin',
        interval_sec: 10,
        enabled: true,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: null,
      }),
    })
  })

  await page.route('**://localhost:8000/devices/device-1/status', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        device_id: 'device-1',
        status: 'degraded',
        last_seen: '2026-01-01T10:03:00Z',
        online: false,
        recent_stats: {
          total_events_last_hour: 22,
          events_by_type: { poll_success: 10, poll_error: 10, device_offline: 2 },
          last_event_at: '2026-01-01T10:10:00Z',
          latency_ms: 120.4,
        },
      }),
    })
  })

  await page.route('**://localhost:8000/devices/device-1/events*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'ev-1',
          device_id: 'device-1',
          event_type: 'poll_success',
          message: 'ok',
          metadata: { command: 'show version' },
          created_at: '2026-01-01T10:00:00Z',
        },
        {
          id: 'ev-2',
          device_id: 'device-1',
          event_type: 'poll_error',
          message: 'timeout',
          metadata: { error: 'timeout' },
          created_at: '2026-01-01T10:01:00Z',
        },
        {
          id: 'ev-3',
          device_id: 'device-1',
          event_type: 'poll_error',
          message: 'timeout retry',
          metadata: { error: 'timeout retry' },
          created_at: '2026-01-01T10:02:00Z',
        },
        {
          id: 'ev-4',
          device_id: 'device-1',
          event_type: 'device_offline',
          message: 'device is offline',
          metadata: { reason: 'no heartbeat' },
          created_at: '2026-01-01T10:10:00Z',
        },
      ]),
    })
  })
})

test('device detail renders timeline, metadata drawer, filters, and export', async ({ page }) => {
  await page.goto('/devices/device-1?range=all')

  await expect(page.locator('h1')).toContainText('leaf-01')
  await expect(page.getByTestId('device-event-timeline')).toBeVisible()
  await expect(page.getByText('chain-2 #1')).toBeVisible()

  await page.getByTestId('device-event-timeline').getByText('poll_error').first().click()
  await expect(page.getByText('metadata JSON')).toBeVisible()
  await expect(page.getByRole('complementary').getByText('timeout', { exact: true })).toBeVisible()
  await page.getByRole('complementary').getByRole('button').first().click()

  await page.getByLabel('事件類型').selectOption('poll_error')
  await expect(page).toHaveURL(/type=poll_error/)

  await page.getByRole('button', { name: 'PDF' }).dispatchEvent('click')
  await expect(page.getByText('已匯出 PDF')).toBeVisible()
})
