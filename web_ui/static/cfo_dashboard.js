/**
 * CFO Dashboard JavaScript - Simplified Version
 * Aligned with existing system design
 */

// Global variables
let currentFilters = {
    period: 'all_time',
    entity: '',
    startDate: null,
    endDate: null
};

let dashboardData = {};
let charts = {};

// Chart.js configuration
Chart.defaults.font.family = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
Chart.defaults.responsive = true;
Chart.defaults.maintainAspectRatio = false;

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeDashboard();
    setupEventListeners();
    setupQuickFilters();
});

/**
 * Initialize the CFO dashboard
 */
async function initializeDashboard() {
    showLoading(true);

    try {
        // Load initial data
        await loadDashboardData();

        // Populate entity dropdown
        await populateEntityDropdown();

        // Update KPIs
        updateKPICards();

        // Initialize charts
        initializeCharts();

    } catch (error) {
        console.error('Error initializing dashboard:', error);
        showError('Failed to load dashboard data. Please refresh the page.');
    } finally {
        showLoading(false);
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Period selector
    document.getElementById('periodSelector').addEventListener('change', function() {
        currentFilters.period = this.value;

        // Show/hide custom date range
        if (this.value === 'custom') {
            showCustomDateRange();
        } else {
            hideCustomDateRange();
            currentFilters.startDate = null;
            currentFilters.endDate = null;
        }

        refreshDashboard();
    });

    // Entity filter
    document.getElementById('entityFilter').addEventListener('change', function() {
        currentFilters.entity = this.value;
        refreshDashboard();
    });

    // Refresh button
    document.getElementById('refreshDashboard').addEventListener('click', refreshDashboard);

    // Reset button
    document.getElementById('resetFilters').addEventListener('click', resetFilters);

    // Custom date inputs
    document.addEventListener('change', function(e) {
        if (e.target.id === 'startDateInput') {
            currentFilters.startDate = e.target.value;
            refreshDashboard();
        } else if (e.target.id === 'endDateInput') {
            currentFilters.endDate = e.target.value;
            refreshDashboard();
        }
    });

    // Error modal close
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('close')) {
            hideError();
        }
    });
}

/**
 * Setup quick filters
 */
function setupQuickFilters() {
    // YTD Filter
    document.getElementById('filterYTD').addEventListener('click', function() {
        const now = new Date();
        currentFilters.startDate = now.getFullYear() + '-01-01';
        currentFilters.endDate = now.toISOString().split('T')[0];
        currentFilters.period = 'custom';
        updateFilterDisplay();
        refreshDashboard();
    });

    // 2024 Filter
    document.getElementById('filter2024').addEventListener('click', function() {
        currentFilters.startDate = '2024-01-01';
        currentFilters.endDate = '2024-12-31';
        currentFilters.period = 'custom';
        updateFilterDisplay();
        refreshDashboard();
    });

    // Q4 Filter
    document.getElementById('filterQ4').addEventListener('click', function() {
        currentFilters.startDate = '2024-10-01';
        currentFilters.endDate = '2024-12-31';
        currentFilters.period = 'custom';
        updateFilterDisplay();
        refreshDashboard();
    });

    // Last Month Filter
    document.getElementById('filterLastMonth').addEventListener('click', function() {
        const now = new Date();
        const lastMonth = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0);

        currentFilters.startDate = lastMonth.toISOString().split('T')[0];
        currentFilters.endDate = lastMonthEnd.toISOString().split('T')[0];
        currentFilters.period = 'custom';
        updateFilterDisplay();
        refreshDashboard();
    });
}

/**
 * Load dashboard data from APIs
 */
async function loadDashboardData() {
    const promises = [];

    // Load cash dashboard data
    promises.push(
        fetch('/api/reports/cash-dashboard?' + new URLSearchParams(getAPIParams()))
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    dashboardData.cashDashboard = data.data;
                }
            })
            .catch(error => console.warn('Cash dashboard API error:', error))
    );

    // Load monthly P&L data
    promises.push(
        fetch('/api/reports/monthly-pl?' + new URLSearchParams({
            ...getAPIParams(),
            months_back: currentFilters.period === 'all_time' ? 'all' : 12
        }))
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    dashboardData.monthlyPL = data.data;
                }
            })
            .catch(error => console.warn('Monthly P&L API error:', error))
    );

    // Load entity summary
    promises.push(
        fetch('/api/reports/entity-summary?' + new URLSearchParams(getAPIParams()))
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    dashboardData.entitySummary = data.data;
                }
            })
            .catch(error => console.warn('Entity summary API error:', error))
    );

    // Load charts data
    promises.push(
        fetch('/api/reports/charts-data')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    dashboardData.chartsData = data.data;
                }
            })
            .catch(error => console.warn('Charts data API error:', error))
    );

    await Promise.allSettled(promises);
}

/**
 * Populate entity dropdown
 */
async function populateEntityDropdown() {
    try {
        const response = await fetch('/api/reports/entities');
        const data = await response.json();

        if (data.success) {
            const entitySelect = document.getElementById('entityFilter');
            entitySelect.innerHTML = '<option value="">All Entities</option>';

            data.data.entities.forEach(entity => {
                const option = document.createElement('option');
                option.value = entity.name;
                option.textContent = entity.display_name || entity.name;
                entitySelect.appendChild(option);
            });
        }
    } catch (error) {
        console.warn('Error populating entity dropdown:', error);
    }
}

/**
 * Get API parameters based on current filters
 */
function getAPIParams() {
    const params = {};

    if (currentFilters.period !== 'all_time') {
        params.period = currentFilters.period;
    }

    if (currentFilters.entity) {
        params.entity = currentFilters.entity;
    }

    if (currentFilters.startDate) {
        params.start_date = currentFilters.startDate;
    }

    if (currentFilters.endDate) {
        params.end_date = currentFilters.endDate;
    }

    return params;
}

/**
 * Update KPI cards with current data
 */
function updateKPICards() {
    const cashData = dashboardData.cashDashboard?.cash_position;
    const plData = dashboardData.monthlyPL?.summary?.period_totals;

    // Safe update function
    function safeUpdate(elementId, value) {
        console.log(`safeUpdate called: ${elementId} = ${value}`);
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = formatCurrency(value || 0);
            console.log(`Element ${elementId} updated with: ${element.textContent}`);
        } else {
            console.error(`Element with ID '${elementId}' not found!`);
        }
    }

    // Update cash position
    console.log('Cash Data:', cashData);
    if (cashData) {
        console.log('Updating cashPosition with:', cashData.total_cash_usd);
        safeUpdate('cashPosition', cashData.total_cash_usd);
    } else {
        console.warn('Cash data not available');
    }

    // Update P&L data
    if (plData) {
        safeUpdate('totalRevenue', plData.total_revenue);
        safeUpdate('totalExpenses', plData.total_expenses);
        safeUpdate('netProfit', plData.total_profit);

        // Update profit color
        const profitElement = document.getElementById('netProfit');
        if (profitElement) {
            profitElement.className = `stat-number ${(plData.total_profit || 0) >= 0 ? 'positive' : 'negative'}`;
        }
    }
}

/**
 * Initialize all charts
 */
function initializeCharts() {
    // Revenue vs Expenses Chart
    createRevenueExpensesChart();

    // Monthly P&L Chart
    createMonthlyPLChart();

    // Entity Performance Chart
    createEntityChart();

    // Cash Flow Chart
    createCashFlowChart();

    // Sankey Financial Flow Diagram
    createSankeyDiagram();
}

/**
 * Create Revenue vs Expenses Chart
 */
function createRevenueExpensesChart() {
    const ctx = document.getElementById('revenueExpensesChart');
    if (!ctx) return;

    const plData = dashboardData.monthlyPL?.summary?.period_totals;
    if (!plData) return;

    charts.revenueExpenses = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Revenue', 'Expenses'],
            datasets: [{
                label: 'Amount',
                data: [plData.total_revenue || 0, plData.total_expenses || 0],
                backgroundColor: ['#667eea', '#f56565'],
                borderColor: ['#5a67d8', '#e53e3e'],
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create Monthly P&L Chart
 */
function createMonthlyPLChart() {
    const ctx = document.getElementById('monthlyPLChart');
    if (!ctx) return;

    const monthlyData = dashboardData.monthlyPL?.monthly_pl;
    if (!monthlyData || monthlyData.length === 0) return;

    const labels = monthlyData.map(m => m.month);
    const revenue = monthlyData.map(m => m.revenue || 0);
    const expenses = monthlyData.map(m => m.expenses || 0);
    const profit = monthlyData.map(m => m.profit || 0);

    charts.monthlyPL = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Revenue',
                    data: revenue,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Expenses',
                    data: expenses,
                    borderColor: '#f56565',
                    backgroundColor: 'rgba(245, 101, 101, 0.1)',
                    tension: 0.4
                },
                {
                    label: 'Profit',
                    data: profit,
                    borderColor: '#48bb78',
                    backgroundColor: 'rgba(72, 187, 120, 0.1)',
                    tension: 0.4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                }
            }
        }
    });
}

/**
 * Create Entity Performance Chart
 */
function createEntityChart() {
    const ctx = document.getElementById('entityChart');
    if (!ctx) return;

    const entityData = dashboardData.entitySummary?.entities;
    if (!entityData || entityData.length === 0) return;

    // Get top 5 entities by revenue
    const topEntities = entityData
        .sort((a, b) => (b.financial_metrics?.total_revenue || 0) - (a.financial_metrics?.total_revenue || 0))
        .slice(0, 5);

    const labels = topEntities.map(e => e.entity);
    const data = topEntities.map(e => e.financial_metrics?.total_revenue || 0);

    charts.entity = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Revenue',
                data: data,
                backgroundColor: '#667eea',
                borderColor: '#5a67d8',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                },
                x: {
                    ticks: {
                        maxRotation: 45
                    }
                }
            }
        }
    });
}

/**
 * Create Cash Flow Chart
 */
function createCashFlowChart() {
    const ctx = document.getElementById('cashFlowChart');
    if (!ctx) return;

    const cashData = dashboardData.cashDashboard?.trends?.['30_days'];
    if (!cashData || !cashData.daily_positions) return;

    const labels = cashData.daily_positions.map(point => point.date);
    const netFlowData = cashData.daily_positions.map(point => point.daily_change || 0);

    charts.cashFlow = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Daily Cash Change',
                data: netFlowData,
                borderColor: '#48bb78',
                backgroundColor: 'rgba(72, 187, 120, 0.1)',
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    ticks: {
                        callback: function(value) {
                            return formatCurrency(value);
                        }
                    }
                },
                x: {
                    ticks: {
                        maxTicksLimit: 10
                    }
                }
            }
        }
    });
}

/**
 * Show/hide custom date range
 */
function showCustomDateRange() {
    const startDateGroup = document.getElementById('customDateRange');
    const endDateGroup = document.getElementById('customDateRangeEnd');

    if (startDateGroup) startDateGroup.style.display = 'block';
    if (endDateGroup) endDateGroup.style.display = 'block';
}

function hideCustomDateRange() {
    const startDateGroup = document.getElementById('customDateRange');
    const endDateGroup = document.getElementById('customDateRangeEnd');

    if (startDateGroup) startDateGroup.style.display = 'none';
    if (endDateGroup) endDateGroup.style.display = 'none';
}

/**
 * Update filter display
 */
function updateFilterDisplay() {
    // Update period selector
    document.getElementById('periodSelector').value = currentFilters.period;

    // Update entity selector
    document.getElementById('entityFilter').value = currentFilters.entity;

    // Set date inputs
    if (currentFilters.startDate) {
        const startInput = document.getElementById('startDateInput');
        if (startInput) startInput.value = currentFilters.startDate;
    }

    if (currentFilters.endDate) {
        const endInput = document.getElementById('endDateInput');
        if (endInput) endInput.value = currentFilters.endDate;
    }

    // Show/hide custom date range
    if (currentFilters.period === 'custom') {
        showCustomDateRange();
    } else {
        hideCustomDateRange();
    }
}

/**
 * Reset all filters
 */
function resetFilters() {
    currentFilters = {
        period: 'all_time',
        entity: '',
        startDate: null,
        endDate: null
    };

    updateFilterDisplay();
    refreshDashboard();
}

/**
 * Refresh dashboard data
 */
async function refreshDashboard() {
    showLoading(true);

    try {
        await loadDashboardData();
        updateKPICards();

        // Destroy existing charts
        Object.values(charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        charts = {};

        // Recreate charts
        initializeCharts();

    } catch (error) {
        console.error('Error refreshing dashboard:', error);
        showError('Failed to refresh dashboard data.');
    } finally {
        showLoading(false);
    }
}

/**
 * Utility Functions
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount || 0);
}

function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.style.display = show ? 'flex' : 'none';
    }
}

function showError(message) {
    const modal = document.getElementById('errorModal');
    const messageEl = document.getElementById('errorMessage');

    if (modal && messageEl) {
        messageEl.textContent = message;
        modal.style.display = 'flex';
    }
}

function hideError() {
    const modal = document.getElementById('errorModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Financial Reports Functions
 */
function generateDREReport() {
    try {
        // Show loading
        showLoading(true);

        // Load DRE data and show preview modal
        loadDREPreviewData();

    } catch (error) {
        console.error('Error loading DRE preview:', error);
        showError('Failed to load DRE preview. Please try again.');
        showLoading(false);
    }
}

/**
 * Load DRE data and show preview modal
 */
async function loadDREPreviewData() {
    try {
        // Get current filters
        const params = new URLSearchParams(getAPIParams());

        // Add company name
        const companyName = document.getElementById('reportCompanyName')?.value || 'Delta Mining';
        params.set('company_name', companyName);

        // Fetch DRE data from simple JSON endpoint (same as PDF)
        const response = await fetch(`/api/reports/income-statement/simple?${params.toString()}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to load DRE data');
        }

        // Show modal first to ensure it exists
        openDREModal();

        // Then populate modal with data with small delay to ensure DOM is ready
        setTimeout(() => {
            populateDREModal(data.statement, companyName);
        }, 100);

    } catch (error) {
        console.error('Error loading DRE data:', error);
        showError('Erro ao carregar dados da DRE: ' + error.message);
    } finally {
        showLoading(false);
    }
}

/**
 * Populate DRE modal with data
 */
function populateDREModal(dreData, companyName) {
    console.log('populateDREModal called with:', dreData, companyName);

    // Check if modal exists first
    const modal = document.getElementById('drePreviewModal');
    if (!modal) {
        console.error('drePreviewModal not found in DOM');
        return;
    }

    // Update summary metrics - handle both simple and full API response formats
    let totalRevenue, grossProfit, netIncome;

    if (dreData.summary_metrics) {
        // Full API format
        const summaryMetrics = dreData.summary_metrics;
        totalRevenue = summaryMetrics.total_revenue || 0;
        grossProfit = summaryMetrics.gross_profit || 0;
        netIncome = summaryMetrics.net_income || 0;
    } else {
        // Simple API format - extract from main structure
        grossProfit = dreData.gross_profit?.amount || 0;
        netIncome = dreData.net_income?.amount || 0;
        // Calculate revenue as Gross Profit + Cost of Goods Sold
        totalRevenue = grossProfit + (dreData.cost_of_goods_sold?.total || 0);
    }

    console.log('Summary metrics:', {totalRevenue, grossProfit, netIncome});

    // Safe element updates with null checks
    const safeUpdateElement = (id, value, styleUpdates = null) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
            if (styleUpdates) {
                Object.assign(element.style, styleUpdates);
            }
            console.log(`Successfully updated element '${id}' with value: ${value}`);
        } else {
            console.warn(`Element with ID '${id}' not found in DOM`);

            // Additional debugging
            const allElements = document.querySelectorAll('[id]');
            console.log('All elements with IDs found:', Array.from(allElements).map(el => el.id));
        }
    };

    safeUpdateElement('drePreviewRevenue', formatCurrency(totalRevenue));
    safeUpdateElement('drePreviewGrossProfit', formatCurrency(grossProfit));
    safeUpdateElement('drePreviewNetIncome', formatCurrency(netIncome), {
        color: netIncome >= 0 ? '#48bb78' : '#f56565'
    });

    // Update period information
    const periodInfo = dreData.period || {};
    const periodName = periodInfo.period_name || 'Período completo';
    safeUpdateElement('drePeriodInfo', periodName);

    // Update company information
    safeUpdateElement('dreCompanyInfo', companyName);
    safeUpdateElement('dreGeneratedAt', new Date().toLocaleDateString('pt-BR'));

    // Populate detailed table with DRE structure
    populateDRETable(dreData);
}

/**
 * Populate DRE detailed table
 */
function populateDRETable(dreData) {
    const tableBody = document.getElementById('dreDetailsList');
    if (!tableBody) {
        console.error('dreDetailsList element not found');
        return;
    }
    tableBody.innerHTML = '';

    // Extract values for DRE calculation
    const grossProfitAmount = dreData.gross_profit?.amount || 0;
    const costOfGoodsSold = dreData.cost_of_goods_sold?.total || 0;
    const operatingExpenses = dreData.operating_expenses?.total || 0;
    const operatingIncome = dreData.operating_income?.amount || 0;
    const otherIncomeExpenses = dreData.other_income_expenses?.total || 0;
    const netIncomeAmount = dreData.net_income?.amount || 0;

    // Calculate revenue as Gross Profit + Cost of Goods Sold
    const revenueAmount = grossProfitAmount + costOfGoodsSold;

    // Build DRE structure following Brazilian standards
    const dreStructure = [
        {
            name: 'Receita Operacional Bruta',
            amount: revenueAmount,
            isMain: true,
            type: 'revenue'
        },
        {
            name: '(-) Custo dos Produtos Vendidos',
            amount: -costOfGoodsSold,
            isMain: false,
            type: 'expense'
        },
        {
            name: '= Lucro Bruto',
            amount: grossProfitAmount,
            isMain: true,
            type: 'calculated'
        },
        {
            name: '(-) Despesas Operacionais',
            amount: -operatingExpenses,
            isMain: false,
            type: 'expense'
        },
        {
            name: '= Lucro Operacional',
            amount: operatingIncome,
            isMain: true,
            type: 'calculated'
        },
        {
            name: '(+/-) Outras Receitas/Despesas',
            amount: otherIncomeExpenses,
            isMain: false,
            type: 'other'
        },
        {
            name: '= Lucro Líquido do Exercício',
            amount: netIncomeAmount,
            isMain: true,
            type: 'final'
        }
    ];

    dreStructure.forEach(item => {
        const row = document.createElement('tr');

        // Calculate percentage of revenue - use the calculated revenueAmount
        const percentage = revenueAmount > 0 ? ((item.amount / revenueAmount) * 100).toFixed(1) : '0.0';

        row.innerHTML = `
            <td style="padding: 0.5rem 0; padding-left: ${item.isMain ? '0px' : '20px'}; font-weight: ${item.isMain ? 'bold' : 'normal'}; border-bottom: 1px solid #f1f5f9;">
                ${item.name}
            </td>
            <td style="text-align: right; padding: 0.5rem 0; font-weight: ${item.isMain ? 'bold' : 'normal'}; color: ${getDREAmountColor(item.amount, item.type)}; border-bottom: 1px solid #f1f5f9;">
                ${formatCurrency(item.amount)}
            </td>
            <td style="text-align: right; padding: 0.5rem 0; font-weight: ${item.isMain ? 'bold' : 'normal'}; color: #666; border-bottom: 1px solid #f1f5f9;">
                ${percentage}%
            </td>
        `;

        // Add special styling for main categories
        if (item.isMain) {
            row.style.backgroundColor = '#f8f9fa';
        }

        // Special styling for final result
        if (item.type === 'final') {
            row.style.backgroundColor = '#e8f5e8';
            row.style.fontWeight = 'bold';
        }

        tableBody.appendChild(row);
    });
}

/**
 * Get color for amount based on value and context
 */
function getAmountColor(amount) {
    if (amount === 0) return '#6c757d';
    return amount > 0 ? '#28a745' : '#dc3545';
}

/**
 * Get color for DRE amounts based on type and value
 */
function getDREAmountColor(amount, type) {
    if (amount === 0) return '#6c757d';

    switch (type) {
        case 'revenue':
            return amount > 0 ? '#28a745' : '#dc3545';
        case 'expense':
            return '#dc3545'; // Always red for expenses (shown as negative)
        case 'calculated':
        case 'final':
            return amount >= 0 ? '#28a745' : '#dc3545';
        case 'other':
            return amount >= 0 ? '#28a745' : '#dc3545';
        default:
            return amount > 0 ? '#28a745' : '#dc3545';
    }
}

/**
 * Open DRE preview modal
 */
function openDREModal() {
    let modal = document.getElementById('drePreviewModal');

    // If modal doesn't exist, create it dynamically
    if (!modal) {
        console.log('Modal not found, creating dynamically...');
        modal = createDREModal();
    }

    if (modal) {
        modal.style.display = 'flex';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        modal.style.zIndex = '1000';
        modal.style.justifyContent = 'center';
        modal.style.alignItems = 'center';

        // Focus trap for accessibility
        modal.focus();

        console.log('DRE modal opened successfully');
    } else {
        console.error('Failed to create or find DRE modal');
    }
}

/**
 * Create DRE modal dynamically
 */
function createDREModal() {
    const modalHTML = `
        <div id="drePreviewModal" class="modal" style="display: none;">
            <div class="modal-content" style="max-width: 800px; width: 90%; background: white; border-radius: 12px; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2); max-height: 90vh; overflow-y: auto;">
                <div class="modal-header" style="padding: 1.5rem; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #2d3748;">📊 Demonstração do Resultado do Exercício (DRE)</h3>
                    <span class="close" onclick="closeDREModal()" style="font-size: 1.5rem; cursor: pointer; color: #718096; border: none; background: none;">&times;</span>
                </div>
                <div class="modal-body" style="padding: 1.5rem;">
                    <div id="drePreviewContent">
                        <div class="dre-summary" style="margin-bottom: 2rem;">
                            <h4 style="color: #2d3748; margin-bottom: 1rem;">📋 Resumo do Período</h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Receita Total</div>
                                    <div id="drePreviewRevenue" style="font-size: 1.2rem; font-weight: bold; color: #48bb78;">R$ 0,00</div>
                                </div>
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Lucro Bruto</div>
                                    <div id="drePreviewGrossProfit" style="font-size: 1.2rem; font-weight: bold; color: #4299e1;">R$ 0,00</div>
                                </div>
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Resultado Líquido</div>
                                    <div id="drePreviewNetIncome" style="font-size: 1.2rem; font-weight: bold;">R$ 0,00</div>
                                </div>
                            </div>
                        </div>

                        <div class="dre-details" style="margin-bottom: 2rem;">
                            <h4 style="color: #2d3748; margin-bottom: 1rem;">📈 Detalhes Financeiros</h4>
                            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem;">
                                <table style="width: 100%; border-collapse: collapse;">
                                    <thead>
                                        <tr style="border-bottom: 2px solid #e2e8f0;">
                                            <th style="text-align: left; padding: 0.75rem 0; color: #4a5568;">Item</th>
                                            <th style="text-align: right; padding: 0.75rem 0; color: #4a5568;">Valor</th>
                                            <th style="text-align: right; padding: 0.75rem 0; color: #4a5568;">% da Receita</th>
                                        </tr>
                                    </thead>
                                    <tbody id="dreDetailsList">
                                        <!-- Items will be populated by JavaScript -->
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div class="dre-period-info" style="background: #edf2f7; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                                <div><strong>Período:</strong> <span id="drePeriodInfo">-</span></div>
                                <div><strong>Empresa:</strong> <span id="dreCompanyInfo">-</span></div>
                                <div><strong>Gerado em:</strong> <span id="dreGeneratedAt">-</span></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer" style="display: flex; gap: 1rem; justify-content: flex-end; padding: 1.5rem; border-top: 1px solid #e2e8f0;">
                    <button onclick="closeDREModal()" style="background-color: #e2e8f0; color: #4a5568; border: none; border-radius: 6px; cursor: pointer; padding: 0.75rem 1.5rem;">❌ Fechar</button>
                    <button onclick="downloadDREPDF()" style="background-color: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; padding: 0.75rem 1.5rem;">📄 Baixar PDF</button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = document.getElementById('drePreviewModal');
    console.log('Modal created dynamically:', modal);
    return modal;
}

/**
 * Close DRE preview modal
 */
function closeDREModal() {
    const modal = document.getElementById('drePreviewModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Download DRE PDF (called from modal)
 */
function downloadDREPDF() {
    try {
        // Show loading
        showLoading(true);

        // Get current filters
        const params = new URLSearchParams(getAPIParams());

        // Add company name
        const companyName = document.getElementById('reportCompanyName')?.value || 'Delta Mining';
        params.set('company_name', companyName);

        // Build URL
        const url = `/api/reports/dre-pdf?${params.toString()}`;

        // Create a temporary link to download the PDF
        const link = document.createElement('a');
        link.href = url;
        link.download = ''; // Let the server set the filename
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Close modal
        closeDREModal();

        // Show success notification
        showReportGenerationStatus('📄 DRE PDF gerado com sucesso!', true);

        // Hide loading after a short delay
        setTimeout(() => {
            showLoading(false);
        }, 1000);

    } catch (error) {
        console.error('Error downloading DRE PDF:', error);
        showError('Failed to download DRE PDF. Please try again.');
        showLoading(false);
    }
}

function showReportGenerationStatus(message, isSuccess = true) {
    // Create a simple notification
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${isSuccess ? '#48bb78' : '#f56565'};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        z-index: 1001;
        font-size: 0.9rem;
        max-width: 300px;
    `;
    notification.textContent = message;

    document.body.appendChild(notification);

    // Remove after 3 seconds
    setTimeout(() => {
        if (document.body.contains(notification)) {
            document.body.removeChild(notification);
        }
    }, 3000);
}

/**
 * Generate Balance Sheet Report (show modal first)
 */
function generateBalanceSheetReport() {
    try {
        // Show loading
        showLoading(true);

        // Load Balance Sheet data and show preview modal
        loadBalanceSheetPreviewData();

    } catch (error) {
        console.error('Error loading Balance Sheet preview:', error);
        showError('Failed to load Balance Sheet preview. Please try again.');
        showLoading(false);
    }
}

/**
 * Load Balance Sheet data and show preview modal
 */
async function loadBalanceSheetPreviewData() {
    try {
        // Get current filters
        const params = new URLSearchParams(getAPIParams());

        // Add company name
        const companyName = document.getElementById('reportCompanyName')?.value || 'Delta Mining';
        params.set('company_name', companyName);

        // Fetch Balance Sheet data from simple JSON endpoint
        const response = await fetch(`/api/reports/balance-sheet/simple?${params.toString()}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to load Balance Sheet data');
        }

        // Show modal first to ensure it exists
        openBalanceSheetModal();

        // Then populate modal with data with small delay to ensure DOM is ready
        setTimeout(() => {
            populateBalanceSheetModal(data.statement, companyName);
        }, 100);

    } catch (error) {
        console.error('Error loading Balance Sheet data:', error);
        showError('Erro ao carregar dados do Balanço Patrimonial: ' + error.message);
    } finally {
        showLoading(false);
    }
}

/**
 * Generate Cash Flow Report (show modal first)
 */
function generateCashFlowReport() {
    try {
        // Show loading
        showLoading(true);

        // Load Cash Flow data and show preview modal
        loadCashFlowPreviewData();

    } catch (error) {
        console.error('Error loading Cash Flow preview:', error);
        showError('Failed to load Cash Flow preview. Please try again.');
        showLoading(false);
    }
}

/**
 * Load Cash Flow data and show preview modal
 */
async function loadCashFlowPreviewData() {
    try {
        // Get current filters
        const params = new URLSearchParams(getAPIParams());

        // Add company name
        const companyName = document.getElementById('reportCompanyName')?.value || 'Delta Mining';
        params.set('company_name', companyName);

        // Fetch Cash Flow data from simple JSON endpoint
        const response = await fetch(`/api/reports/cash-flow/simple?${params.toString()}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to load Cash Flow data');
        }

        // Show modal first to ensure it exists
        openCashFlowModal();

        // Then populate modal with data with small delay to ensure DOM is ready
        setTimeout(() => {
            populateCashFlowModal(data.statement, companyName);
        }, 100);

    } catch (error) {
        console.error('Error loading Cash Flow data:', error);
        showError('Erro ao carregar dados do Fluxo de Caixa: ' + error.message);
    } finally {
        showLoading(false);
    }
}

/**
 * Generate DMPL Report (show modal first)
 */
function generateDMPLReport() {
    try {
        // Show loading
        showLoading(true);

        // Load DMPL data and show preview modal
        loadDMPLPreviewData();

    } catch (error) {
        console.error('Error loading DMPL preview:', error);
        showError('Failed to load DMPL preview. Please try again.');
        showLoading(false);
    }
}

/**
 * Load DMPL data and show preview modal
 */
async function loadDMPLPreviewData() {
    try {
        // Get current filters
        const params = new URLSearchParams(getAPIParams());

        // Add company name
        const companyName = document.getElementById('reportCompanyName')?.value || 'Delta Mining';
        params.set('company_name', companyName);

        // Fetch DMPL data from simple JSON endpoint
        const response = await fetch(`/api/reports/dmpl/simple?${params.toString()}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to load DMPL data');
        }

        // Show modal first to ensure it exists
        openDMPLModal();

        // Then populate modal with data with small delay to ensure DOM is ready
        setTimeout(() => {
            populateDMPLModal(data.statement, companyName);
        }, 100);

    } catch (error) {
        console.error('Error loading DMPL data:', error);
        showError('Erro ao carregar dados do DMPL: ' + error.message);
    } finally {
        showLoading(false);
    }
}

/**
 * Balance Sheet Modal Functions
 */

/**
 * Populate Balance Sheet modal with data
 */
function populateBalanceSheetModal(balanceSheetData, companyName) {
    console.log('populateBalanceSheetModal called with:', balanceSheetData, companyName);

    // Check if modal exists first
    const modal = document.getElementById('balanceSheetPreviewModal');
    if (!modal) {
        console.error('balanceSheetPreviewModal not found in DOM');
        return;
    }

    // Extract metrics from API response
    let totalAssets, totalLiabilities, totalEquity;

    if (balanceSheetData.summary_metrics) {
        const summaryMetrics = balanceSheetData.summary_metrics;
        totalAssets = summaryMetrics.total_assets || 0;
        totalLiabilities = summaryMetrics.total_liabilities || 0;
        totalEquity = summaryMetrics.total_equity || 0;
    } else {
        // Fallback to assets structure if available
        totalAssets = balanceSheetData.assets?.total || 0;
        totalLiabilities = balanceSheetData.liabilities?.total || 0;
        totalEquity = balanceSheetData.equity?.total || 0;
    }

    console.log('Balance Sheet metrics:', {totalAssets, totalLiabilities, totalEquity});

    // Safe element updates with null checks
    const safeUpdateElement = (id, value, styleUpdates = null) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
            if (styleUpdates) {
                Object.assign(element.style, styleUpdates);
            }
            console.log(`Successfully updated element '${id}' with value: ${value}`);
        } else {
            console.warn(`Element with ID '${id}' not found in DOM`);
        }
    };

    safeUpdateElement('balanceSheetPreviewAssets', formatCurrency(totalAssets));
    safeUpdateElement('balanceSheetPreviewLiabilities', formatCurrency(totalLiabilities));
    safeUpdateElement('balanceSheetPreviewEquity', formatCurrency(totalEquity), {
        color: totalEquity >= 0 ? '#48bb78' : '#f56565'
    });

    // Update period information
    const periodInfo = balanceSheetData.period || {};
    const periodName = periodInfo.period_name || 'Período completo';
    safeUpdateElement('balanceSheetPeriodInfo', periodName);

    // Update company information
    safeUpdateElement('balanceSheetCompanyInfo', companyName);
    safeUpdateElement('balanceSheetGeneratedAt', new Date().toLocaleDateString('pt-BR'));

    // Populate detailed table with Balance Sheet structure
    populateBalanceSheetTable(balanceSheetData);
}

/**
 * Populate Balance Sheet detailed table
 */
function populateBalanceSheetTable(balanceSheetData) {
    const tableBody = document.getElementById('balanceSheetDetailsList');
    if (!tableBody) {
        console.error('balanceSheetDetailsList element not found');
        return;
    }
    tableBody.innerHTML = '';

    // Extract values for Balance Sheet calculation
    const totalAssets = balanceSheetData.assets?.total || balanceSheetData.summary_metrics?.total_assets || 0;
    const totalLiabilities = balanceSheetData.liabilities?.total || balanceSheetData.summary_metrics?.total_liabilities || 0;
    const totalEquity = balanceSheetData.equity?.total || balanceSheetData.summary_metrics?.total_equity || 0;

    // Build Balance Sheet structure following Brazilian standards
    const balanceSheetStructure = [
        {
            name: 'ATIVO',
            amount: null,
            isHeader: true,
            type: 'header'
        },
        {
            name: 'Total do Ativo',
            amount: totalAssets,
            isMain: true,
            type: 'asset'
        },
        {
            name: '',
            amount: null,
            isHeader: false,
            type: 'spacer'
        },
        {
            name: 'PASSIVO E PATRIMÔNIO LÍQUIDO',
            amount: null,
            isHeader: true,
            type: 'header'
        },
        {
            name: 'Total do Passivo',
            amount: totalLiabilities,
            isMain: true,
            type: 'liability'
        },
        {
            name: 'Total do Patrimônio Líquido',
            amount: totalEquity,
            isMain: true,
            type: 'equity'
        },
        {
            name: '',
            amount: null,
            isHeader: false,
            type: 'spacer'
        },
        {
            name: 'TOTAL DO PASSIVO + PATRIMÔNIO LÍQUIDO',
            amount: totalLiabilities + totalEquity,
            isMain: true,
            type: 'total'
        }
    ];

    balanceSheetStructure.forEach(item => {
        if (item.type === 'spacer' && !item.name) {
            // Add empty row for spacing
            const row = document.createElement('tr');
            row.innerHTML = `<td colspan="2" style="padding: 0.25rem;"></td>`;
            tableBody.appendChild(row);
            return;
        }

        const row = document.createElement('tr');

        if (item.isHeader) {
            row.innerHTML = `
                <td colspan="2" style="padding: 0.75rem 0; font-weight: bold; font-size: 1.1rem; color: #2d3748; background: #f7fafc; border-bottom: 2px solid #e2e8f0;">
                    ${item.name}
                </td>
            `;
        } else {
            row.innerHTML = `
                <td style="padding: 0.5rem 0; padding-left: ${item.isMain ? '20px' : '40px'}; font-weight: ${item.isMain ? 'bold' : 'normal'}; border-bottom: 1px solid #f1f5f9;">
                    ${item.name}
                </td>
                <td style="text-align: right; padding: 0.5rem 0; font-weight: ${item.isMain ? 'bold' : 'normal'}; color: ${getBalanceSheetAmountColor(item.amount, item.type)}; border-bottom: 1px solid #f1f5f9;">
                    ${formatCurrency(item.amount)}
                </td>
            `;
        }

        // Add special styling for main categories
        if (item.isMain) {
            row.style.backgroundColor = '#f8f9fa';
        }

        // Special styling for total
        if (item.type === 'total') {
            row.style.backgroundColor = '#e8f5e8';
            row.style.fontWeight = 'bold';
        }

        tableBody.appendChild(row);
    });
}

/**
 * Get color for Balance Sheet amounts based on type and value
 */
function getBalanceSheetAmountColor(amount, type) {
    if (amount === null || amount === 0) return '#6c757d';

    switch (type) {
        case 'asset':
            return amount > 0 ? '#4299e1' : '#f56565';
        case 'liability':
            return amount > 0 ? '#f56565' : '#4299e1';
        case 'equity':
        case 'total':
            return amount >= 0 ? '#48bb78' : '#f56565';
        default:
            return amount > 0 ? '#4299e1' : '#f56565';
    }
}

/**
 * Open Balance Sheet preview modal
 */
function openBalanceSheetModal() {
    let modal = document.getElementById('balanceSheetPreviewModal');

    // If modal doesn't exist, create it dynamically
    if (!modal) {
        console.log('Modal not found, creating dynamically...');
        modal = createBalanceSheetModal();
    }

    if (modal) {
        modal.style.display = 'flex';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        modal.style.zIndex = '1000';
        modal.style.justifyContent = 'center';
        modal.style.alignItems = 'center';

        // Focus trap for accessibility
        modal.focus();

        console.log('Balance Sheet modal opened successfully');
    } else {
        console.error('Failed to create or find Balance Sheet modal');
    }
}

/**
 * Create Balance Sheet modal dynamically
 */
function createBalanceSheetModal() {
    const modalHTML = `
        <div id="balanceSheetPreviewModal" class="modal" style="display: none;">
            <div class="modal-content" style="max-width: 800px; width: 90%; background: white; border-radius: 12px; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2); max-height: 90vh; overflow-y: auto;">
                <div class="modal-header" style="padding: 1.5rem; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #2d3748;">⚖️ Balanço Patrimonial (BP)</h3>
                    <span class="close" onclick="closeBalanceSheetModal()" style="font-size: 1.5rem; cursor: pointer; color: #718096; border: none; background: none;">&times;</span>
                </div>
                <div class="modal-body" style="padding: 1.5rem;">
                    <div id="balanceSheetPreviewContent">
                        <div class="balance-sheet-summary" style="margin-bottom: 2rem;">
                            <h4 style="color: #2d3748; margin-bottom: 1rem;">📋 Resumo do Período</h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Total do Ativo</div>
                                    <div id="balanceSheetPreviewAssets" style="font-size: 1.2rem; font-weight: bold; color: #4299e1;">$0</div>
                                </div>
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Total do Passivo</div>
                                    <div id="balanceSheetPreviewLiabilities" style="font-size: 1.2rem; font-weight: bold; color: #f56565;">$0</div>
                                </div>
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Patrimônio Líquido</div>
                                    <div id="balanceSheetPreviewEquity" style="font-size: 1.2rem; font-weight: bold;">$0</div>
                                </div>
                            </div>
                        </div>

                        <div class="balance-sheet-details" style="margin-bottom: 2rem;">
                            <h4 style="color: #2d3748; margin-bottom: 1rem;">📊 Estrutura Patrimonial</h4>
                            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem;">
                                <table style="width: 100%; border-collapse: collapse;">
                                    <thead>
                                        <tr style="border-bottom: 2px solid #e2e8f0;">
                                            <th style="text-align: left; padding: 0.75rem 0; color: #4a5568;">Item</th>
                                            <th style="text-align: right; padding: 0.75rem 0; color: #4a5568;">Valor</th>
                                        </tr>
                                    </thead>
                                    <tbody id="balanceSheetDetailsList">
                                        <!-- Items will be populated by JavaScript -->
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div class="balance-sheet-period-info" style="background: #edf2f7; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                                <div><strong>Período:</strong> <span id="balanceSheetPeriodInfo">-</span></div>
                                <div><strong>Empresa:</strong> <span id="balanceSheetCompanyInfo">-</span></div>
                                <div><strong>Gerado em:</strong> <span id="balanceSheetGeneratedAt">-</span></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer" style="display: flex; gap: 1rem; justify-content: flex-end; padding: 1.5rem; border-top: 1px solid #e2e8f0;">
                    <button onclick="closeBalanceSheetModal()" style="background-color: #e2e8f0; color: #4a5568; border: none; border-radius: 6px; cursor: pointer; padding: 0.75rem 1.5rem;">❌ Fechar</button>
                    <button onclick="downloadBalanceSheetPDF()" style="background-color: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; padding: 0.75rem 1.5rem;">📄 Baixar PDF</button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = document.getElementById('balanceSheetPreviewModal');
    console.log('Balance Sheet modal created dynamically:', modal);
    return modal;
}

/**
 * Close Balance Sheet preview modal
 */
function closeBalanceSheetModal() {
    const modal = document.getElementById('balanceSheetPreviewModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Download Balance Sheet PDF (called from modal)
 */
function downloadBalanceSheetPDF() {
    try {
        // Show loading
        showLoading(true);

        // Get current filters
        const params = new URLSearchParams(getAPIParams());

        // Add company name
        const companyName = document.getElementById('reportCompanyName')?.value || 'Delta Mining';
        params.set('company_name', companyName);

        // Build URL
        const url = `/api/reports/balance-sheet-pdf?${params.toString()}`;

        // Create a temporary link to download the PDF
        const link = document.createElement('a');
        link.href = url;
        link.download = ''; // Let the server set the filename
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Close modal
        closeBalanceSheetModal();

        // Show success notification
        showReportGenerationStatus('⚖️ Balanço Patrimonial PDF gerado com sucesso!', true);

        // Hide loading after a short delay
        setTimeout(() => {
            showLoading(false);
        }, 1000);

    } catch (error) {
        console.error('Error downloading Balance Sheet PDF:', error);
        showError('Failed to download Balance Sheet PDF. Please try again.');
        showLoading(false);
    }
}

/**
 * Cash Flow Modal Functions
 */

/**
 * Populate Cash Flow modal with data
 */
function populateCashFlowModal(cashFlowData, companyName) {
    console.log('populateCashFlowModal called with:', cashFlowData, companyName);

    // Check if modal exists first
    const modal = document.getElementById('cashFlowPreviewModal');
    if (!modal) {
        console.error('cashFlowPreviewModal not found in DOM');
        return;
    }

    // Extract metrics from API response
    let netCashFlow, cashReceipts, cashPayments, endingCash;

    if (cashFlowData.summary_metrics) {
        const summaryMetrics = cashFlowData.summary_metrics;
        netCashFlow = summaryMetrics.net_cash_flow || 0;
        cashReceipts = summaryMetrics.cash_receipts || 0;
        cashPayments = summaryMetrics.cash_payments || 0;
        endingCash = summaryMetrics.ending_cash || 0;
    } else if (cashFlowData.operating_activities) {
        // Fallback to operating activities structure
        const operating = cashFlowData.operating_activities;
        cashReceipts = operating.cash_receipts || 0;
        cashPayments = operating.cash_payments || 0;
        netCashFlow = operating.net_operating || 0;
        endingCash = netCashFlow; // Simplified
    } else {
        // Default values
        cashReceipts = 0;
        cashPayments = 0;
        netCashFlow = 0;
        endingCash = 0;
    }

    console.log('Cash Flow metrics:', {netCashFlow, cashReceipts, cashPayments, endingCash});

    // Safe element updates with null checks
    const safeUpdateElement = (id, value, styleUpdates = null) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
            if (styleUpdates) {
                Object.assign(element.style, styleUpdates);
            }
            console.log(`Successfully updated element '${id}' with value: ${value}`);
        } else {
            console.warn(`Element with ID '${id}' not found in DOM`);
        }
    };

    safeUpdateElement('cashFlowPreviewReceipts', formatCurrency(cashReceipts));
    safeUpdateElement('cashFlowPreviewPayments', formatCurrency(cashPayments));
    safeUpdateElement('cashFlowPreviewNetFlow', formatCurrency(netCashFlow), {
        color: netCashFlow >= 0 ? '#48bb78' : '#f56565'
    });

    // Update period information
    const periodInfo = cashFlowData.period || {};
    const periodName = periodInfo.period_name || 'Período completo';
    safeUpdateElement('cashFlowPeriodInfo', periodName);

    // Update company information
    safeUpdateElement('cashFlowCompanyInfo', companyName);
    safeUpdateElement('cashFlowGeneratedAt', new Date().toLocaleDateString('pt-BR'));

    // Populate detailed table with Cash Flow structure
    populateCashFlowTable(cashFlowData);
}

/**
 * Populate Cash Flow detailed table
 */
function populateCashFlowTable(cashFlowData) {
    const tableBody = document.getElementById('cashFlowDetailsList');
    if (!tableBody) {
        console.error('cashFlowDetailsList element not found');
        return;
    }
    tableBody.innerHTML = '';

    // Extract values for Cash Flow calculation
    const cashReceipts = cashFlowData.summary_metrics?.cash_receipts || cashFlowData.operating_activities?.cash_receipts || 0;
    const cashPayments = cashFlowData.summary_metrics?.cash_payments || cashFlowData.operating_activities?.cash_payments || 0;
    const netOperating = cashFlowData.summary_metrics?.net_cash_flow || cashFlowData.operating_activities?.net_operating || (cashReceipts - cashPayments);

    // Build Cash Flow structure following Brazilian standards
    const cashFlowStructure = [
        {
            name: 'FLUXOS DE CAIXA DAS ATIVIDADES OPERACIONAIS',
            amount: null,
            isHeader: true,
            type: 'header'
        },
        {
            name: 'Recebimentos de Clientes',
            amount: cashReceipts,
            isMain: false,
            type: 'operating_inflow'
        },
        {
            name: 'Pagamentos a Fornecedores e Funcionários',
            amount: -cashPayments,
            isMain: false,
            type: 'operating_outflow'
        },
        {
            name: 'Caixa Líquido das Atividades Operacionais',
            amount: netOperating,
            isMain: true,
            type: 'operating_total'
        },
        {
            name: '',
            amount: null,
            isHeader: false,
            type: 'spacer'
        },
        {
            name: 'FLUXOS DE CAIXA DAS ATIVIDADES DE INVESTIMENTO',
            amount: null,
            isHeader: true,
            type: 'header'
        },
        {
            name: 'Caixa Líquido das Atividades de Investimento',
            amount: 0, // Simplified
            isMain: true,
            type: 'investing_total'
        },
        {
            name: '',
            amount: null,
            isHeader: false,
            type: 'spacer'
        },
        {
            name: 'FLUXOS DE CAIXA DAS ATIVIDADES DE FINANCIAMENTO',
            amount: null,
            isHeader: true,
            type: 'header'
        },
        {
            name: 'Caixa Líquido das Atividades de Financiamento',
            amount: 0, // Simplified
            isMain: true,
            type: 'financing_total'
        },
        {
            name: '',
            amount: null,
            isHeader: false,
            type: 'spacer'
        },
        {
            name: 'AUMENTO (DIMINUIÇÃO) LÍQUIDA DE CAIXA',
            amount: netOperating,
            isMain: true,
            type: 'net_change'
        }
    ];

    cashFlowStructure.forEach(item => {
        if (item.type === 'spacer' && !item.name) {
            // Add empty row for spacing
            const row = document.createElement('tr');
            row.innerHTML = `<td colspan="2" style="padding: 0.25rem;"></td>`;
            tableBody.appendChild(row);
            return;
        }

        const row = document.createElement('tr');

        if (item.isHeader) {
            row.innerHTML = `
                <td colspan="2" style="padding: 0.75rem 0; font-weight: bold; font-size: 1.1rem; color: #2d3748; background: #f7fafc; border-bottom: 2px solid #e2e8f0;">
                    ${item.name}
                </td>
            `;
        } else {
            row.innerHTML = `
                <td style="padding: 0.5rem 0; padding-left: ${item.isMain ? '20px' : '40px'}; font-weight: ${item.isMain ? 'bold' : 'normal'}; border-bottom: 1px solid #f1f5f9;">
                    ${item.name}
                </td>
                <td style="text-align: right; padding: 0.5rem 0; font-weight: ${item.isMain ? 'bold' : 'normal'}; color: ${getCashFlowAmountColor(item.amount, item.type)}; border-bottom: 1px solid #f1f5f9;">
                    ${formatCurrency(item.amount)}
                </td>
            `;
        }

        // Add special styling for main categories
        if (item.isMain) {
            row.style.backgroundColor = '#f8f9fa';
        }

        // Special styling for net change
        if (item.type === 'net_change') {
            row.style.backgroundColor = '#e8f5e8';
            row.style.fontWeight = 'bold';
        }

        tableBody.appendChild(row);
    });
}

/**
 * Get color for Cash Flow amounts based on type and value
 */
function getCashFlowAmountColor(amount, type) {
    if (amount === null || amount === 0) return '#6c757d';

    switch (type) {
        case 'operating_inflow':
            return amount > 0 ? '#48bb78' : '#f56565';
        case 'operating_outflow':
            return '#f56565'; // Always red for outflows (shown as negative)
        case 'operating_total':
        case 'investing_total':
        case 'financing_total':
        case 'net_change':
            return amount >= 0 ? '#48bb78' : '#f56565';
        default:
            return amount > 0 ? '#48bb78' : '#f56565';
    }
}

/**
 * Open Cash Flow preview modal
 */
function openCashFlowModal() {
    let modal = document.getElementById('cashFlowPreviewModal');

    // If modal doesn't exist, create it dynamically
    if (!modal) {
        console.log('Modal not found, creating dynamically...');
        modal = createCashFlowModal();
    }

    if (modal) {
        modal.style.display = 'flex';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        modal.style.zIndex = '1000';
        modal.style.justifyContent = 'center';
        modal.style.alignItems = 'center';

        // Focus trap for accessibility
        modal.focus();

        console.log('Cash Flow modal opened successfully');
    } else {
        console.error('Failed to create or find Cash Flow modal');
    }
}

/**
 * Create Cash Flow modal dynamically
 */
function createCashFlowModal() {
    const modalHTML = `
        <div id="cashFlowPreviewModal" class="modal" style="display: none;">
            <div class="modal-content" style="max-width: 800px; width: 90%; background: white; border-radius: 12px; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2); max-height: 90vh; overflow-y: auto;">
                <div class="modal-header" style="padding: 1.5rem; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #2d3748;">💰 Demonstração de Fluxo de Caixa (DFC)</h3>
                    <span class="close" onclick="closeCashFlowModal()" style="font-size: 1.5rem; cursor: pointer; color: #718096; border: none; background: none;">&times;</span>
                </div>
                <div class="modal-body" style="padding: 1.5rem;">
                    <div id="cashFlowPreviewContent">
                        <div class="cash-flow-summary" style="margin-bottom: 2rem;">
                            <h4 style="color: #2d3748; margin-bottom: 1rem;">📋 Resumo do Período</h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Recebimentos</div>
                                    <div id="cashFlowPreviewReceipts" style="font-size: 1.2rem; font-weight: bold; color: #48bb78;">$0</div>
                                </div>
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Pagamentos</div>
                                    <div id="cashFlowPreviewPayments" style="font-size: 1.2rem; font-weight: bold; color: #f56565;">$0</div>
                                </div>
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Fluxo Líquido</div>
                                    <div id="cashFlowPreviewNetFlow" style="font-size: 1.2rem; font-weight: bold;">$0</div>
                                </div>
                            </div>
                        </div>

                        <div class="cash-flow-details" style="margin-bottom: 2rem;">
                            <h4 style="color: #2d3748; margin-bottom: 1rem;">💸 Fluxos de Caixa por Atividade</h4>
                            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem;">
                                <table style="width: 100%; border-collapse: collapse;">
                                    <thead>
                                        <tr style="border-bottom: 2px solid #e2e8f0;">
                                            <th style="text-align: left; padding: 0.75rem 0; color: #4a5568;">Item</th>
                                            <th style="text-align: right; padding: 0.75rem 0; color: #4a5568;">Valor</th>
                                        </tr>
                                    </thead>
                                    <tbody id="cashFlowDetailsList">
                                        <!-- Items will be populated by JavaScript -->
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div class="cash-flow-period-info" style="background: #edf2f7; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                                <div><strong>Período:</strong> <span id="cashFlowPeriodInfo">-</span></div>
                                <div><strong>Empresa:</strong> <span id="cashFlowCompanyInfo">-</span></div>
                                <div><strong>Gerado em:</strong> <span id="cashFlowGeneratedAt">-</span></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer" style="display: flex; gap: 1rem; justify-content: flex-end; padding: 1.5rem; border-top: 1px solid #e2e8f0;">
                    <button onclick="closeCashFlowModal()" style="background-color: #e2e8f0; color: #4a5568; border: none; border-radius: 6px; cursor: pointer; padding: 0.75rem 1.5rem;">❌ Fechar</button>
                    <button onclick="downloadCashFlowPDF()" style="background-color: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; padding: 0.75rem 1.5rem;">📄 Baixar PDF</button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = document.getElementById('cashFlowPreviewModal');
    console.log('Cash Flow modal created dynamically:', modal);
    return modal;
}

/**
 * Close Cash Flow preview modal
 */
function closeCashFlowModal() {
    const modal = document.getElementById('cashFlowPreviewModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Download Cash Flow PDF (called from modal)
 */
function downloadCashFlowPDF() {
    try {
        // Show loading
        showLoading(true);

        // Get current filters
        const params = new URLSearchParams(getAPIParams());

        // Add company name
        const companyName = document.getElementById('reportCompanyName')?.value || 'Delta Mining';
        params.set('company_name', companyName);

        // Build URL
        const url = `/api/reports/cash-flow-pdf?${params.toString()}`;

        // Create a temporary link to download the PDF
        const link = document.createElement('a');
        link.href = url;
        link.download = ''; // Let the server set the filename
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Close modal
        closeCashFlowModal();

        // Show success notification
        showReportGenerationStatus('💰 Demonstração de Fluxo de Caixa PDF gerado com sucesso!', true);

        // Hide loading after a short delay
        setTimeout(() => {
            showLoading(false);
        }, 1000);

    } catch (error) {
        console.error('Error downloading Cash Flow PDF:', error);
        showError('Failed to download Cash Flow PDF. Please try again.');
        showLoading(false);
    }
}

/**
 * DMPL Modal Functions
 */

/**
 * Populate DMPL modal with data
 */
function populateDMPLModal(dmplData, companyName) {
    console.log('populateDMPLModal called with:', dmplData, dmplData);

    // Check if modal exists first
    const modal = document.getElementById('dmplPreviewModal');
    if (!modal) {
        console.error('dmplPreviewModal not found in DOM');
        return;
    }

    // Extract metrics from API response
    let beginningEquity, netIncome, endingEquity;

    if (dmplData.summary_metrics) {
        const summaryMetrics = dmplData.summary_metrics;
        beginningEquity = summaryMetrics.beginning_equity || 0;
        netIncome = summaryMetrics.net_income || 0;
        endingEquity = summaryMetrics.ending_equity || 0;
    } else if (dmplData.equity_movements) {
        // Fallback to equity movements structure
        const equity = dmplData.equity_movements;
        beginningEquity = equity.beginning_equity || 0;
        netIncome = equity.net_income || 0;
        endingEquity = equity.ending_equity || 0;
    } else {
        // Default values
        beginningEquity = 0;
        netIncome = 0;
        endingEquity = 0;
    }

    console.log('DMPL metrics:', {beginningEquity, netIncome, endingEquity});

    // Safe element updates with null checks
    const safeUpdateElement = (id, value, styleUpdates = null) => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
            if (styleUpdates) {
                Object.assign(element.style, styleUpdates);
            }
            console.log(`Successfully updated element '${id}' with value: ${value}`);
        } else {
            console.warn(`Element with ID '${id}' not found in DOM`);
        }
    };

    safeUpdateElement('dmplPreviewBeginningEquity', formatCurrency(beginningEquity));
    safeUpdateElement('dmplPreviewNetIncome', formatCurrency(netIncome), {
        color: netIncome >= 0 ? '#48bb78' : '#f56565'
    });
    safeUpdateElement('dmplPreviewEndingEquity', formatCurrency(endingEquity), {
        color: endingEquity >= 0 ? '#48bb78' : '#f56565'
    });

    // Update period information
    const periodInfo = dmplData.period || {};
    const periodName = periodInfo.period_name || 'Período completo';
    safeUpdateElement('dmplPeriodInfo', periodName);

    // Update company information
    safeUpdateElement('dmplCompanyInfo', companyName);
    safeUpdateElement('dmplGeneratedAt', new Date().toLocaleDateString('pt-BR'));

    // Populate detailed table with DMPL structure
    populateDMPLTable(dmplData);
}

/**
 * Populate DMPL detailed table
 */
function populateDMPLTable(dmplData) {
    const tableBody = document.getElementById('dmplDetailsList');
    if (!tableBody) {
        console.error('dmplDetailsList element not found');
        return;
    }
    tableBody.innerHTML = '';

    // Extract values for DMPL calculation
    const beginningEquity = dmplData.summary_metrics?.beginning_equity || dmplData.equity_movements?.beginning_equity || 0;
    const netIncome = dmplData.summary_metrics?.net_income || dmplData.equity_movements?.net_income || 0;
    const endingEquity = dmplData.summary_metrics?.ending_equity || dmplData.equity_movements?.ending_equity || 0;

    // Build DMPL structure following Brazilian standards
    const dmplStructure = [
        {
            name: 'PATRIMÔNIO LÍQUIDO - INÍCIO DO PERÍODO',
            amount: beginningEquity,
            isMain: true,
            type: 'beginning'
        },
        {
            name: '',
            amount: null,
            isHeader: false,
            type: 'spacer'
        },
        {
            name: 'MUTAÇÕES DO PERÍODO:',
            amount: null,
            isHeader: true,
            type: 'header'
        },
        {
            name: 'Lucro/Prejuízo do Exercício',
            amount: netIncome,
            isMain: false,
            type: 'income'
        },
        {
            name: 'Aportes de Capital',
            amount: 0, // Simplified
            isMain: false,
            type: 'capital'
        },
        {
            name: 'Distribuições de Resultado',
            amount: 0, // Simplified
            isMain: false,
            type: 'distribution'
        },
        {
            name: '',
            amount: null,
            isHeader: false,
            type: 'spacer'
        },
        {
            name: 'TOTAL DAS MUTAÇÕES',
            amount: netIncome, // Simplified - just net income for now
            isMain: true,
            type: 'total_changes'
        },
        {
            name: '',
            amount: null,
            isHeader: false,
            type: 'spacer'
        },
        {
            name: 'PATRIMÔNIO LÍQUIDO - FINAL DO PERÍODO',
            amount: endingEquity,
            isMain: true,
            type: 'ending'
        }
    ];

    dmplStructure.forEach(item => {
        if (item.type === 'spacer' && !item.name) {
            // Add empty row for spacing
            const row = document.createElement('tr');
            row.innerHTML = `<td colspan="2" style="padding: 0.25rem;"></td>`;
            tableBody.appendChild(row);
            return;
        }

        const row = document.createElement('tr');

        if (item.isHeader) {
            row.innerHTML = `
                <td colspan="2" style="padding: 0.75rem 0; font-weight: bold; font-size: 1.1rem; color: #2d3748; background: #f7fafc; border-bottom: 2px solid #e2e8f0;">
                    ${item.name}
                </td>
            `;
        } else {
            row.innerHTML = `
                <td style="padding: 0.5rem 0; padding-left: ${item.isMain ? '0px' : '20px'}; font-weight: ${item.isMain ? 'bold' : 'normal'}; border-bottom: 1px solid #f1f5f9;">
                    ${item.name}
                </td>
                <td style="text-align: right; padding: 0.5rem 0; font-weight: ${item.isMain ? 'bold' : 'normal'}; color: ${getDMPLAmountColor(item.amount, item.type)}; border-bottom: 1px solid #f1f5f9;">
                    ${formatCurrency(item.amount)}
                </td>
            `;
        }

        // Add special styling for main categories
        if (item.isMain) {
            row.style.backgroundColor = '#f8f9fa';
        }

        // Special styling for ending equity
        if (item.type === 'ending') {
            row.style.backgroundColor = '#e8f5e8';
            row.style.fontWeight = 'bold';
        }

        tableBody.appendChild(row);
    });
}

/**
 * Get color for DMPL amounts based on type and value
 */
function getDMPLAmountColor(amount, type) {
    if (amount === null || amount === 0) return '#6c757d';

    switch (type) {
        case 'beginning':
        case 'ending':
            return amount >= 0 ? '#48bb78' : '#f56565';
        case 'income':
            return amount >= 0 ? '#48bb78' : '#f56565';
        case 'capital':
            return amount > 0 ? '#4299e1' : '#6c757d';
        case 'distribution':
            return amount > 0 ? '#f56565' : '#6c757d';
        case 'total_changes':
            return amount >= 0 ? '#48bb78' : '#f56565';
        default:
            return amount >= 0 ? '#48bb78' : '#f56565';
    }
}

/**
 * Open DMPL preview modal
 */
function openDMPLModal() {
    let modal = document.getElementById('dmplPreviewModal');

    // If modal doesn't exist, create it dynamically
    if (!modal) {
        console.log('Modal not found, creating dynamically...');
        modal = createDMPLModal();
    }

    if (modal) {
        modal.style.display = 'flex';
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        modal.style.zIndex = '1000';
        modal.style.justifyContent = 'center';
        modal.style.alignItems = 'center';

        // Focus trap for accessibility
        modal.focus();

        console.log('DMPL modal opened successfully');
    } else {
        console.error('Failed to create or find DMPL modal');
    }
}

/**
 * Create DMPL modal dynamically
 */
function createDMPLModal() {
    const modalHTML = `
        <div id="dmplPreviewModal" class="modal" style="display: none;">
            <div class="modal-content" style="max-width: 800px; width: 90%; background: white; border-radius: 12px; box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2); max-height: 90vh; overflow-y: auto;">
                <div class="modal-header" style="padding: 1.5rem; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #2d3748;">📈 Demonstração das Mutações do Patrimônio Líquido (DMPL)</h3>
                    <span class="close" onclick="closeDMPLModal()" style="font-size: 1.5rem; cursor: pointer; color: #718096; border: none; background: none;">&times;</span>
                </div>
                <div class="modal-body" style="padding: 1.5rem;">
                    <div id="dmplPreviewContent">
                        <div class="dmpl-summary" style="margin-bottom: 2rem;">
                            <h4 style="color: #2d3748; margin-bottom: 1rem;">📋 Resumo do Período</h4>
                            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 1.5rem;">
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">PL Inicial</div>
                                    <div id="dmplPreviewBeginningEquity" style="font-size: 1.2rem; font-weight: bold; color: #4299e1;">$0</div>
                                </div>
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">Resultado do Período</div>
                                    <div id="dmplPreviewNetIncome" style="font-size: 1.2rem; font-weight: bold;">$0</div>
                                </div>
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; text-align: center;">
                                    <div style="font-size: 0.9rem; color: #666;">PL Final</div>
                                    <div id="dmplPreviewEndingEquity" style="font-size: 1.2rem; font-weight: bold;">$0</div>
                                </div>
                            </div>
                        </div>

                        <div class="dmpl-details" style="margin-bottom: 2rem;">
                            <h4 style="color: #2d3748; margin-bottom: 1rem;">📊 Movimentação do Patrimônio Líquido</h4>
                            <div style="background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem;">
                                <table style="width: 100%; border-collapse: collapse;">
                                    <thead>
                                        <tr style="border-bottom: 2px solid #e2e8f0;">
                                            <th style="text-align: left; padding: 0.75rem 0; color: #4a5568;">Item</th>
                                            <th style="text-align: right; padding: 0.75rem 0; color: #4a5568;">Valor</th>
                                        </tr>
                                    </thead>
                                    <tbody id="dmplDetailsList">
                                        <!-- Items will be populated by JavaScript -->
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <div class="dmpl-period-info" style="background: #edf2f7; padding: 1rem; border-radius: 8px; margin-bottom: 1.5rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                                <div><strong>Período:</strong> <span id="dmplPeriodInfo">-</span></div>
                                <div><strong>Empresa:</strong> <span id="dmplCompanyInfo">-</span></div>
                                <div><strong>Gerado em:</strong> <span id="dmplGeneratedAt">-</span></div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer" style="display: flex; gap: 1rem; justify-content: flex-end; padding: 1.5rem; border-top: 1px solid #e2e8f0;">
                    <button onclick="closeDMPLModal()" style="background-color: #e2e8f0; color: #4a5568; border: none; border-radius: 6px; cursor: pointer; padding: 0.75rem 1.5rem;">❌ Fechar</button>
                    <button onclick="downloadDMPLPDF()" style="background-color: #667eea; color: white; border: none; border-radius: 6px; cursor: pointer; padding: 0.75rem 1.5rem;">📄 Baixar PDF</button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
    const modal = document.getElementById('dmplPreviewModal');
    console.log('DMPL modal created dynamically:', modal);
    return modal;
}

/**
 * Close DMPL preview modal
 */
function closeDMPLModal() {
    const modal = document.getElementById('dmplPreviewModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Download DMPL PDF (called from modal)
 */
function downloadDMPLPDF() {
    try {
        // Show loading
        showLoading(true);

        // Get current filters
        const params = new URLSearchParams(getAPIParams());

        // Add company name
        const companyName = document.getElementById('reportCompanyName')?.value || 'Delta Mining';
        params.set('company_name', companyName);

        // Build URL
        const url = `/api/reports/dmpl-pdf?${params.toString()}`;

        // Create a temporary link to download the PDF
        const link = document.createElement('a');
        link.href = url;
        link.download = ''; // Let the server set the filename
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        // Close modal
        closeDMPLModal();

        // Show success notification
        showReportGenerationStatus('📈 DMPL PDF gerado com sucesso!', true);

        // Hide loading after a short delay
        setTimeout(() => {
            showLoading(false);
        }, 1000);

    } catch (error) {
        console.error('Error downloading DMPL PDF:', error);
        showError('Failed to download DMPL PDF. Please try again.');
        showLoading(false);
    }
}

/**
 * Create Sankey Financial Flow Diagram
 */
function createSankeyDiagram() {
    const container = document.getElementById('sankeyDiagram');
    if (!container) {
        console.warn('Sankey diagram container not found');
        return;
    }

    // Clear any existing content
    container.innerHTML = '';

    // Check if D3 and d3-sankey are available
    if (typeof d3 === 'undefined' || typeof d3.sankey === 'undefined') {
        console.warn('D3.js or d3-sankey library not available for Sankey diagram');
        container.innerHTML = '<div style="text-align: center; color: #666; padding: 2rem;">Sankey diagram requires D3.js and d3-sankey libraries</div>';
        return;
    }

    // Get financial data for the diagram
    const plData = dashboardData.monthlyPL?.summary?.period_totals;
    if (!plData) {
        container.innerHTML = '<div style="text-align: center; color: #666; padding: 2rem;">No financial data available for Sankey diagram</div>';
        return;
    }

    // Set dimensions
    const margin = {top: 10, right: 10, bottom: 10, left: 10};
    const width = container.clientWidth - margin.left - margin.right;
    const height = 450 - margin.top - margin.bottom;

    // Create SVG
    const svg = d3.select(container)
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom);

    const g = svg.append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Prepare data for Sankey diagram
    const totalRevenue = Math.max(plData.total_revenue || 0, 0);
    const totalExpenses = Math.max(plData.total_expenses || 0, 0);
    const netProfit = (plData.total_profit || 0);

    // If no significant data, show placeholder
    if (totalRevenue < 1) {
        container.innerHTML = '<div style="text-align: center; color: #666; padding: 2rem;">Insufficient revenue data to generate meaningful flow visualization</div>';
        return;
    }

    // Create nodes and links for the Sankey diagram
    const nodes = [
        // Source: Revenue
        { id: 0, name: 'Total Revenue' },

        // Intermediate: Expense categories (simplified)
        { id: 1, name: 'Operating Expenses' },
        { id: 2, name: 'Other Costs' },

        // Destination: Net result
        { id: 3, name: netProfit >= 0 ? 'Net Profit' : 'Net Loss' }
    ];

    // Calculate flows
    const operatingExpenseFlow = Math.min(totalExpenses * 0.7, totalRevenue); // 70% of expenses as operating
    const otherCostFlow = Math.min(totalExpenses * 0.3, totalRevenue - operatingExpenseFlow); // 30% as other costs
    const remainingRevenue = Math.max(totalRevenue - operatingExpenseFlow - otherCostFlow, 0);

    const links = [
        // Revenue flows to expenses and profit/loss
        { source: 0, target: 1, value: operatingExpenseFlow },
        { source: 0, target: 2, value: otherCostFlow },
        { source: 0, target: 3, value: remainingRevenue }
    ].filter(link => link.value > 0); // Only include links with positive values

    // Create Sankey generator
    const sankey = d3.sankey()
        .nodeWidth(15)
        .nodePadding(20)
        .size([width, height]);

    // Generate the Sankey layout
    const sankeyData = sankey({
        nodes: nodes.map(d => Object.assign({}, d)),
        links: links.map(d => Object.assign({}, d))
    });

    // Color scale for different flow types
    const color = d3.scaleOrdinal()
        .domain(['revenue', 'expense', 'profit', 'loss'])
        .range(['#48bb78', '#f56565', '#4299e1', '#f59e0b']);

    // Function to get color for links
    const getLinkColor = (link) => {
        if (link.target.name.includes('Profit')) return color('profit');
        if (link.target.name.includes('Loss')) return color('loss');
        if (link.target.name.includes('Expenses') || link.target.name.includes('Cost')) return color('expense');
        return color('revenue');
    };

    // Draw links
    g.selectAll('.link')
        .data(sankeyData.links)
        .enter().append('path')
        .attr('class', 'link')
        .attr('d', d3.sankeyLinkHorizontal())
        .attr('stroke', d => getLinkColor(d))
        .attr('stroke-width', d => Math.max(1, d.width))
        .attr('fill', 'none')
        .attr('opacity', 0.7)
        .on('mouseover', function(event, d) {
            // Show tooltip on hover
            d3.select(this).attr('opacity', 0.9);

            // Create or update tooltip
            let tooltip = d3.select('body').select('.sankey-tooltip');
            if (tooltip.empty()) {
                tooltip = d3.select('body').append('div')
                    .attr('class', 'sankey-tooltip')
                    .style('position', 'absolute')
                    .style('background', 'rgba(0, 0, 0, 0.8)')
                    .style('color', 'white')
                    .style('padding', '8px 12px')
                    .style('border-radius', '4px')
                    .style('font-size', '12px')
                    .style('pointer-events', 'none')
                    .style('opacity', 0)
                    .style('z-index', 1000);
            }

            tooltip.html(`
                <strong>${d.source.name}</strong> → <strong>${d.target.name}</strong><br/>
                Flow: ${formatCurrency(d.value)}
            `)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 10) + 'px')
                .transition()
                .duration(200)
                .style('opacity', 1);
        })
        .on('mouseout', function(event, d) {
            d3.select(this).attr('opacity', 0.7);
            d3.select('.sankey-tooltip').transition().duration(200).style('opacity', 0);
        });

    // Draw nodes
    const nodeGroup = g.selectAll('.node')
        .data(sankeyData.nodes)
        .enter().append('g')
        .attr('class', 'node');

    nodeGroup.append('rect')
        .attr('x', d => d.x0)
        .attr('y', d => d.y0)
        .attr('height', d => d.y1 - d.y0)
        .attr('width', d => d.x1 - d.x0)
        .attr('fill', d => {
            if (d.name.includes('Revenue')) return color('revenue');
            if (d.name.includes('Profit')) return color('profit');
            if (d.name.includes('Loss')) return color('loss');
            return color('expense');
        })
        .attr('opacity', 0.8)
        .on('mouseover', function(event, d) {
            d3.select(this).attr('opacity', 1);
        })
        .on('mouseout', function(event, d) {
            d3.select(this).attr('opacity', 0.8);
        });

    // Add node labels
    nodeGroup.append('text')
        .attr('x', d => d.x0 < width / 2 ? d.x1 + 6 : d.x0 - 6)
        .attr('y', d => (d.y1 + d.y0) / 2)
        .attr('dy', '0.35em')
        .attr('text-anchor', d => d.x0 < width / 2 ? 'start' : 'end')
        .text(d => d.name)
        .style('font-family', '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif')
        .style('font-size', '12px')
        .style('fill', '#4a5568')
        .style('font-weight', 'bold');

    // Add value labels on nodes
    nodeGroup.append('text')
        .attr('x', d => d.x0 < width / 2 ? d.x1 + 6 : d.x0 - 6)
        .attr('y', d => (d.y1 + d.y0) / 2 + 14)
        .attr('text-anchor', d => d.x0 < width / 2 ? 'start' : 'end')
        .text(d => {
            // Calculate total value for the node
            let value = 0;
            if (d.name === 'Total Revenue') value = totalRevenue;
            else if (d.name.includes('Profit') || d.name.includes('Loss')) value = Math.abs(netProfit);
            else {
                // Sum up the incoming flows for expense nodes
                value = sankeyData.links.filter(link => link.target === d).reduce((sum, link) => sum + link.value, 0);
            }
            return formatCurrency(value);
        })
        .style('font-family', '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif')
        .style('font-size', '10px')
        .style('fill', '#666')
        .style('font-weight', 'normal');

    console.log('Sankey diagram created successfully with data:', {
        totalRevenue,
        totalExpenses,
        netProfit,
        nodes: sankeyData.nodes.length,
        links: sankeyData.links.length
    });
}