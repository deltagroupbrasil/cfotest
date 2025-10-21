/**
 * Plan:
 * - Seed SQLite DB for app_db with one transaction.
 * - Start app_db (done in CI) on port 5002.
 * - Navigate to dashboard, verify seeded row appears.
 * - Apply filters to narrow to the seeded row.
 */

import { test, expect } from '@playwright/test';

test('app_db dashboard shows seeded DB row and filters work', async ({ page }) => {
  await page.goto('http://127.0.0.1:5002/');

  // Seeded row should be visible
  await expect(page.locator('#transactionTableBody')).toContainText('E2E Seed Row');

  // Filter by entity
  await page.locator('#entityFilter').fill('EntityE2E');
  await page.locator('button#applyFilters').click();
  await expect(page.locator('#transactionTableBody')).toContainText('E2E Seed Row');
});

