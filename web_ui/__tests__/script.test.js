/**
 * Plan:
 * - Evaluate script.js into JSDOM context and expose key functions to global.
 * - Test buildFilterQuery from various inputs.
 * - Test clearFilters resets inputs and triggers loadTransactions.
 * - Test renderTransactionTable renders rows and empty state.
 * - Test updateTableInfo updates counts with currentTransactions.
 * - Test formatCurrency and formatDate edge cases.
 * - Test loadTransactions constructs fetch URL and updates table placeholders.
 */

const fs = require('fs');
const path = require('path');
const { getByText, getByRole } = require('@testing-library/dom');

function loadScriptExposeGlobals() {
  const scriptPath = path.join(__dirname, '..', 'static', 'script.js');
  let code = fs.readFileSync(scriptPath, 'utf-8');
  // Expose functions to global for testing
  code += '\n' + [
    'global.buildFilterQuery = buildFilterQuery;',
    'global.clearFilters = clearFilters;',
    'global.renderTransactionTable = renderTransactionTable;',
    'global.updateTableInfo = updateTableInfo;',
    'global.formatCurrency = formatCurrency;',
    'global.formatDate = formatDate;',
    'global.loadTransactions = loadTransactions;',
  ].join('\n');
  // Evaluate in this context
  // Provide window alias
  global.window = global;
  eval(code);
}

beforeEach(() => {
  document.body.innerHTML = `
    <div>
      <input id="entityFilter" value="" />
      <select id="transactionType"><option value="">All</option><option value="Revenue">Revenue</option></select>
      <input id="sourceFile" />
      <input id="needsReview" />
      <input id="minAmount" />
      <input id="maxAmount" />
      <input id="startDate" />
      <input id="endDate" />
      <input id="keywordFilter" />
      <button id="applyFilters"></button>
      <button id="clearFilters"></button>
      <button id="refreshData"></button>
      <button id="filterTodos"></button>
      <button id="filter2025"></button>
      <button id="filter2024"></button>
      <button id="filterYTD"></button>
      <table>
        <tbody id="transactionTableBody"></tbody>
      </table>
      <div id="tableInfo"></div>
    </div>
  `;
  loadScriptExposeGlobals();
});

test('buildFilterQuery builds query string from inputs', () => {
  document.getElementById('entityFilter').value = 'EntityA';
  document.getElementById('transactionType').value = 'Revenue';
  document.getElementById('sourceFile').value = 'file1.csv';
  document.getElementById('needsReview').value = 'true';
  document.getElementById('minAmount').value = '10';
  document.getElementById('maxAmount').value = '99';
  document.getElementById('startDate').value = '2024-01-01';
  document.getElementById('endDate').value = '2024-12-31';
  document.getElementById('keywordFilter').value = 'office';
  const qs = global.buildFilterQuery();
  expect(qs).toContain('entity=EntityA');
  expect(qs).toContain('transaction_type=Revenue');
  expect(qs).toContain('source_file=file1.csv');
  expect(qs).toContain('needs_review=true');
  expect(qs).toContain('min_amount=10');
  expect(qs).toContain('max_amount=99');
  expect(qs).toContain('start_date=2024-01-01');
  expect(qs).toContain('end_date=2024-12-31');
  expect(qs).toContain('keyword=office');
});

test('clearFilters resets inputs and triggers reload', () => {
  document.getElementById('entityFilter').value = 'X';
  document.getElementById('transactionType').value = 'Revenue';
  document.getElementById('sourceFile').value = 'foo.csv';
  document.getElementById('needsReview').value = 'true';
  document.getElementById('minAmount').value = '1';
  document.getElementById('maxAmount').value = '2';
  document.getElementById('startDate').value = '2024-01-01';
  document.getElementById('endDate').value = '2024-01-31';
  document.getElementById('keywordFilter').value = 'word';

  const calls = [];
  global.loadTransactions = () => calls.push('loaded');
  global.clearFilters();

  ['entityFilter','transactionType','sourceFile','needsReview','minAmount','maxAmount','startDate','endDate','keywordFilter']
    .forEach(id => expect(document.getElementById(id).value).toBe(''));
  expect(calls).toEqual(['loaded']);
});

test('renderTransactionTable renders rows and empty state', () => {
  const tbody = document.getElementById('transactionTableBody');
  global.renderTransactionTable([]);
  expect(tbody.innerHTML).toMatch(/No transactions/);

  const rows = [
    { Date: '2024-01-01', Description: 'Sale', Amount: 100, classified_entity: 'Entity', confidence: 0.9, source_file: 'a.csv', id: 't1' },
    { Date: '2024-01-02', Description: 'Expense', Amount: -5, classified_entity: 'Entity', confidence: 0.5, source_file: 'b.csv', id: 't2' }
  ];
  global.renderTransactionTable(rows);
  expect(tbody.querySelectorAll('tr').length).toBe(2);
  expect(tbody.innerHTML).toMatch(/Sale/);
  expect(tbody.innerHTML).toMatch(/Expense/);
  // Positive/negative classes applied
  expect(tbody.innerHTML).toMatch(/class=\"positive\"/);
  expect(tbody.innerHTML).toMatch(/class=\"negative\"/);
});

test('updateTableInfo shows counts', () => {
  const info = document.getElementById('tableInfo');
  // Use currentTransactions global to emulate state
  global.currentTransactions = [{},{}];
  global.updateTableInfo([{}]);
  expect(info.textContent).toMatch(/Showing 1 of 2/);
  global.updateTableInfo([{},{}]);
  expect(info.textContent).toMatch(/Showing 2 transactions/);
});

test('format helpers', () => {
  expect(global.formatCurrency(10)).toMatch(/\$10/);
  expect(global.formatCurrency(-10)).toMatch(/\$10/);
  expect(global.formatDate('2024-01-02')).toBeTruthy();
  expect(global.formatDate(null)).toBe('N/A');
});

test('loadTransactions builds fetch URL and updates DOM', async () => {
  document.getElementById('entityFilter').value = 'EntityA';
  // Placeholders used by loadTransactions on error/success
  const tbody = document.getElementById('transactionTableBody');
  const info = document.getElementById('tableInfo');

  global.fetch = jest.fn().mockResolvedValue({
    json: async () => ([{ Date: '2024-01-01', Description: 'Sale', Amount: 1, classified_entity: 'E', source_file: 'f.csv', id: 'x' }])
  });

  await global.loadTransactions();
  expect(global.fetch).toHaveBeenCalled();
  const url = global.fetch.mock.calls[0][0];
  expect(url).toMatch(/\/api\/transactions\?/);
  expect(tbody.innerHTML).toMatch(/Sale/);
  expect(info.textContent).toMatch(/Showing 1 transactions/);
});

