/**
 * Plan:
 * - Date range filter narrows results.
 * - Keyword search filters by Description.
 * - Multi-filter combinations work.
 * - Empty state appears for no matches.
 */

import { test, expect } from '@playwright/test';

test('Date range and keyword filters', async ({ page }) => {
  await page.goto('http://127.0.0.1:5001/');

  // Initially both rows visible
  await expect(page.locator('#transactionTableBody')).toContainText('Sale A');
  await expect(page.locator('#transactionTableBody')).toContainText('Office Supplies');

  // Date range to only include 2024-01-01
  await page.locator('#startDate').fill('2024-01-01');
  await page.locator('#endDate').fill('2024-01-01');
  await page.locator('button#applyFilters').click();
  await expect(page.locator('#transactionTableBody')).toContainText('Sale A');
  await expect(page.locator('#transactionTableBody')).not.toContainText('Office Supplies');

  // Keyword filter 'Office'
  await page.locator('#startDate').fill('');
  await page.locator('#endDate').fill('');
  await page.locator('#keywordFilter').fill('Office');
  await page.locator('button#applyFilters').click();
  await expect(page.locator('#transactionTableBody')).toContainText('Office Supplies');
});

test('Multi-filter and empty state', async ({ page }) => {
  await page.goto('http://127.0.0.1:5001/');
  // Combine filters that will match nothing
  await page.locator('#entityFilter').fill('NoSuchEntity');
  await page.locator('#minAmount').fill('99999');
  await page.locator('button#applyFilters').click();
  await expect(page.locator('#transactionTableBody')).toContainText('No transactions found');
});

