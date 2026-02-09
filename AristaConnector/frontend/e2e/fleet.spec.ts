import { test, expect } from '@playwright/test';

// Mock counter for testing
let mockCounter = 0;

test.beforeEach(async ({ page }) => {
  // Intercept API calls and return mock data
  await page.route('**/health/fleet', async (route) => {
    mockCounter++;
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total_devices: 3,
        online_devices: 2 + (mockCounter % 2), // Alternates between 2 and 3
        offline_devices: 1 - (mockCounter % 2), // Alternates between 1 and 0
        degraded_devices: 0,
        devices: [
          {
            device_id: 'device-1',
            status: 'online',
            last_seen: new Date().toISOString(),
            online: true,
            recent_stats: {
              total_events_last_hour: 10 + mockCounter,
              latency_ms: 50 + mockCounter,
            },
          },
          {
            device_id: 'device-2',
            status: 'online',
            last_seen: new Date().toISOString(),
            online: true,
            recent_stats: {
              total_events_last_hour: 20 + mockCounter,
              latency_ms: 60 + mockCounter,
            },
          },
          {
            device_id: 'device-3',
            status: 'offline',
            last_seen: null,
            online: false,
            recent_stats: {
              total_events_last_hour: 5 + mockCounter,
              latency_ms: null,
            },
          },
        ],
        top_latency_devices: [],
      }),
    });
  });

  await page.route('**/devices', async (route) => {
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
    });
  });
});

test('fleet page renders and updates', async ({ page }) => {
  // Navigate to fleet page
  await page.goto('/fleet');

  // Wait for page to load
  await expect(page.locator('h1')).toContainText('設備機群');

  // Verify summary cards are rendered
  await expect(page.locator('text=總設備數')).toBeVisible();
  await expect(page.locator('text=線上')).toBeVisible();
  await expect(page.getByText('離線', { exact: true })).toBeVisible();

  // Verify table is rendered
  const table = page.locator('table');
  await expect(table).toBeVisible();

  // Verify table headers
  await expect(page.locator('text=主機名稱')).toBeVisible();
  await expect(page.locator('text=IP 位址')).toBeVisible();
  await expect(page.locator('text=狀態')).toBeVisible();
  await expect(page.locator('text=最後看到')).toBeVisible();
  await expect(page.locator('text=平均延遲')).toBeVisible();
  await expect(page.locator('text=事件/10秒')).toBeVisible();

  // Verify devices are in table
  await expect(page.locator('table').getByText('switch-01', { exact: true })).toBeVisible();
  await expect(page.locator('table').getByText('switch-02', { exact: true })).toBeVisible();
  await expect(page.locator('table').getByText('switch-03', { exact: true })).toBeVisible();

  // Get initial values
  const initialOnlineCount = await page.locator('text=線上').locator('..').locator('text=/\\d+/').textContent();
  
  // Wait 12 seconds for refresh (10s interval + 2s buffer)
  await page.waitForTimeout(12000);

  // Verify values have changed (mock counter increments)
  const updatedOnlineCount = await page.locator('text=線上').locator('..').locator('text=/\\d+/').textContent();
  
  // Values should have changed due to mock counter
  expect(initialOnlineCount).not.toBe(updatedOnlineCount);
});

test('fleet page stays usable when health API fails', async ({ page }) => {
  await page.unroute('**/health/fleet');
  await page.route('**/health/fleet', async (route) => {
    await route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'service unavailable' }),
    });
  });

  await page.goto('/fleet');

  await expect(page.locator('h1')).toContainText('設備機群');
  await expect(page.locator('text=管理者告警')).toBeVisible();
  await expect(page.getByText('/health/fleet 回應異常')).toBeVisible();
  await expect(page.locator('table').getByText('switch-01', { exact: true })).toBeVisible();
  await expect(page.locator('text=unknown').first()).toBeVisible();
});

test('fleet page still shows health data when devices API fails', async ({ page }) => {
  await page.unroute('**/devices');
  await page.route('**/devices', async (route) => {
    await route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ detail: 'service unavailable' }),
    });
  });

  await page.goto('/fleet');

  await expect(page.locator('text=總設備數')).toBeVisible();
  await expect(page.locator('text=管理者告警')).toBeVisible();
  await expect(page.getByText('/devices 回應異常')).toBeVisible();
  await expect(page.locator('text=device-1')).toBeVisible();
});

test('fleet page table row click navigates to device detail', async ({ page }) => {
  await page.goto('/fleet');

  // Wait for table to load
  await expect(page.locator('text=switch-01')).toBeVisible();

  // Mock device detail endpoints
  await page.route('**/devices/device-1', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'device-1',
        hostname: 'switch-01',
        ip: '192.168.1.1',
        port: 443,
        username: 'admin',
        interval_sec: 10,
        enabled: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: null,
      }),
    });
  });

  await page.route('**/devices/device-1/status', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        device_id: 'device-1',
        status: 'online',
        last_seen: new Date().toISOString(),
        online: true,
        recent_stats: {
          total_events_last_hour: 10,
          latency_ms: 50,
        },
      }),
    });
  });

  await page.route('**/devices/device-1/events*', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  // Click on first device row
  await page.locator('text=switch-01').click();

  // Verify navigation to device detail page
  await expect(page).toHaveURL(/\/devices\/device-1/);
  await expect(page.locator('h1')).toContainText('switch-01');
});
