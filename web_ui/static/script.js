// Delta CFO Agent - Dashboard JavaScript

let currentTransactions = [];

document.addEventListener('DOMContentLoaded', function() {
    // Load initial data
    loadTransactions();

    // Set up event listeners
    setupEventListeners();
});

function setupEventListeners() {
    // Filter button
    document.getElementById('applyFilters').addEventListener('click', loadTransactions);

    // Clear filters button
    document.getElementById('clearFilters').addEventListener('click', clearFilters);

    // Refresh button
    document.getElementById('refreshData').addEventListener('click', loadTransactions);

    // Quick filter buttons
    document.getElementById('filterTodos').addEventListener('click', () => {
        document.getElementById('needsReview').value = 'true';
        loadTransactions();
    });

    document.getElementById('filter2025').addEventListener('click', () => {
        document.getElementById('startDate').value = '2025-01-01';
        document.getElementById('endDate').value = '2025-12-31';
        loadTransactions();
    });

    document.getElementById('filter2024').addEventListener('click', () => {
        document.getElementById('startDate').value = '2024-01-01';
        document.getElementById('endDate').value = '2024-12-31';
        loadTransactions();
    });

    document.getElementById('filterYTD').addEventListener('click', () => {
        const now = new Date();
        document.getElementById('startDate').value = '2025-01-01';
        document.getElementById('endDate').value = now.toISOString().split('T')[0];
        loadTransactions();
    });
}

function clearFilters() {
    // Clear all filter inputs
    document.getElementById('entityFilter').value = '';
    document.getElementById('transactionType').value = '';
    document.getElementById('sourceFile').value = '';
    document.getElementById('needsReview').value = '';
    document.getElementById('minAmount').value = '';
    document.getElementById('maxAmount').value = '';
    document.getElementById('startDate').value = '';
    document.getElementById('endDate').value = '';
    document.getElementById('keywordFilter').value = '';

    // Reload transactions
    loadTransactions();
}

function buildFilterQuery() {
    const params = new URLSearchParams();

    const entity = document.getElementById('entityFilter').value;
    if (entity) params.append('entity', entity);

    const transactionType = document.getElementById('transactionType').value;
    if (transactionType) params.append('transaction_type', transactionType);

    const sourceFile = document.getElementById('sourceFile').value;
    if (sourceFile) params.append('source_file', sourceFile);

    const needsReview = document.getElementById('needsReview').value;
    if (needsReview) params.append('needs_review', needsReview);

    const minAmount = document.getElementById('minAmount').value;
    if (minAmount) params.append('min_amount', minAmount);

    const maxAmount = document.getElementById('maxAmount').value;
    if (maxAmount) params.append('max_amount', maxAmount);

    const startDate = document.getElementById('startDate').value;
    if (startDate) params.append('start_date', startDate);

    const endDate = document.getElementById('endDate').value;
    if (endDate) params.append('end_date', endDate);

    const keyword = document.getElementById('keywordFilter').value;
    if (keyword) params.append('keyword', keyword);

    return params.toString();
}

async function loadTransactions() {
    try {
        const query = buildFilterQuery();
        const url = `/api/transactions?${query}`;

        const response = await fetch(url);
        const transactions = await response.json();

        currentTransactions = transactions;
        renderTransactionTable(transactions);
        updateTableInfo(transactions);

    } catch (error) {
        console.error('Error loading transactions:', error);
        document.getElementById('transactionTableBody').innerHTML =
            '<tr><td colspan="7" class="loading">Error loading transactions</td></tr>';
    }
}

function renderTransactionTable(transactions) {
    const tbody = document.getElementById('transactionTableBody');

    if (transactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading">No transactions found</td></tr>';
        return;
    }

    tbody.innerHTML = transactions.map(transaction => {
        const amount = parseFloat(transaction.Amount || 0);
        const amountClass = amount > 0 ? 'positive' : amount < 0 ? 'negative' : '';
        const formattedAmount = Math.abs(amount).toLocaleString('en-US', {
            style: 'currency',
            currency: 'USD'
        });

        const confidence = transaction.confidence ?
            (parseFloat(transaction.confidence) * 100).toFixed(0) + '%' : 'N/A';

        const confidenceClass = transaction.confidence && parseFloat(transaction.confidence) < 0.8 ?
            'warning' : '';

        return `
            <tr>
                <td>${transaction.Date || 'N/A'}</td>
                <td>${transaction.Description || 'N/A'}</td>
                <td class="${amountClass}">${formattedAmount}</td>
                <td>${transaction.classified_entity || 'N/A'}</td>
                <td class="${confidenceClass}">${confidence}</td>
                <td>${transaction.source_file || 'N/A'}</td>
                <td>
                    <button class="btn-secondary btn-sm" onclick="viewTransaction('${transaction.id || ''}')">
                        View
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function updateTableInfo(transactions) {
    const info = document.getElementById('tableInfo');
    const count = transactions.length;
    const total = currentTransactions.length;

    if (count === total) {
        info.textContent = `Showing ${count} transactions`;
    } else {
        info.textContent = `Showing ${count} of ${total} transactions`;
    }
}

function viewTransaction(id) {
    // Placeholder for transaction detail view
    alert(`View transaction: ${id}`);
}

// Format currency values
function formatCurrency(value) {
    const num = parseFloat(value || 0);
    return Math.abs(num).toLocaleString('en-US', {
        style: 'currency',
        currency: 'USD'
    });
}

// Format dates
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US');
    } catch {
        return dateString;
    }
}