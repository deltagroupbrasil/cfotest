/**
 * Plan:
 * - Seed a MASTER_TRANSACTIONS.csv with sample rows.
 * - Start Flask app (web_ui.app) on port 5001 using sqlite mode.
 * - Open dashboard, verify elements, apply filters, and assert rows render.
 */

import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import child_process from 'child_process';

const ROOT = process.cwd();
const CSV_PATH = path.join(ROOT, 'MASTER_TRANSACTIONS.csv');

test.beforeAll(async () => {
  // Seed CSV used by web_ui/app.py
  const csv = [
    'Date,Description,Amount,classified_entity,confidence,source_file',
    '2024-01-01,Sale A,100,EntityA,0.9,seed.csv',
    '2024-01-02,Office Supplies,-30,EntityB,0.7,seed.csv'
  ].join('\n');
  fs.writeFileSync(CSV_PATH, csv, 'utf-8');
});

test('Dashboard filters and table rendering', async ({ page }) => {
  await page.goto('http://127.0.0.1:5001/');
  // Basic UI elements
  await expect(page.locator('button#applyFilters')).toBeVisible();
  await expect(page.locator('button#clearFilters')).toBeVisible();

  // Apply needsReview true to filter one row (confidence < 0.8)
  await page.locator('#needsReview').fill('true');
  await page.locator('button#applyFilters').click();

  // Expect a row matching Office Supplies
  await expect(page.locator('#transactionTableBody')).toContainText('Office Supplies');

  // Clear filters and expect both rows
  await page.locator('button#clearFilters').click();
  await expect(page.locator('#transactionTableBody')).toContainText('Sale A');
  await expect(page.locator('#transactionTableBody')).toContainText('Office Supplies');
});

