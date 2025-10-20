// Delta CFO Agent - Advanced Dashboard JavaScript

let currentTransactions = [];
let currentPage = 1;
let itemsPerPage = 50;
let perPageSize = 50;
let totalPages = 1;
let isLoading = false;

// Cache for dynamically loaded dropdown options
let cachedAccountingCategories = [];
let cachedSubcategories = [];

// Drag-down fill state
let dragFillState = {
    isDragging: false,
    startRow: null,
    startCell: null,
    fieldName: null,
    value: null,
    affectedRows: []
};

document.addEventListener('DOMContentLoaded', function() {
    console.log('🟢 DOM Content Loaded - starting initialization');

    // Initialize per-page size from URL or localStorage
    initializePerPageSize();

    // Initialize filter fields from URL parameters
    initializeFiltersFromURL();

    // Load dropdown options from API
    loadDropdownOptions();

    // Load initial data
    loadTransactions();

    // Set up event listeners
    setupEventListeners();

    console.log('🟢 Initialization complete');
});

function initializePerPageSize() {
    // Check URL parameters first
    const urlParams = new URLSearchParams(window.location.search);
    const urlPerPage = urlParams.get('per_page');

    if (urlPerPage) {
        perPageSize = parseInt(urlPerPage);
    } else {
        // Check localStorage as fallback
        const savedPerPage = localStorage.getItem('perPageSize');
        if (savedPerPage) {
            perPageSize = parseInt(savedPerPage);
        }
    }

    // Update active button state
    document.querySelectorAll('.btn-per-page').forEach(btn => {
        const btnPerPage = parseInt(btn.dataset.perPage);
        if (btnPerPage === perPageSize) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

function initializeFiltersFromURL() {
    // Read URL parameters and populate filter fields
    const urlParams = new URLSearchParams(window.location.search);

    const sourceFile = urlParams.get('source_file');
    if (sourceFile) {
        const sourceFileField = document.getElementById('sourceFile');
        if (sourceFileField) {
            sourceFileField.value = sourceFile;
            console.log(`📋 Initialized source_file filter from URL: ${sourceFile}`);
        }
    }

    const entity = urlParams.get('entity');
    if (entity) {
        const entityField = document.getElementById('entityFilter');
        if (entityField) {
            entityField.value = entity;
            console.log(`📋 Initialized entity filter from URL: ${entity}`);
        }
    }

    const transactionType = urlParams.get('transaction_type');
    if (transactionType) {
        const typeField = document.getElementById('transactionType');
        if (typeField) {
            typeField.value = transactionType;
            console.log(`📋 Initialized transaction_type filter from URL: ${transactionType}`);
        }
    }

    const needsReview = urlParams.get('needs_review');
    if (needsReview) {
        const reviewField = document.getElementById('needsReview');
        if (reviewField) {
            reviewField.value = needsReview;
            console.log(`📋 Initialized needs_review filter from URL: ${needsReview}`);
        }
    }
}

async function loadDropdownOptions() {
    // Load accounting categories from API
    try {
        const categoriesResponse = await fetch('/api/accounting_categories');
        const categoriesData = await categoriesResponse.json();
        cachedAccountingCategories = categoriesData.categories || [];
        console.log(`✅ Loaded ${cachedAccountingCategories.length} accounting categories from API`);
    } catch (error) {
        console.error('Failed to load accounting categories:', error);
        // Use fallback if API fails
        cachedAccountingCategories = [
            'REVENUE', 'OPERATING_EXPENSE', 'COGS', 'INTEREST_EXPENSE',
            'OTHER_INCOME', 'OTHER_EXPENSE', 'INCOME_TAX_EXPENSE',
            'ASSET', 'LIABILITY', 'EQUITY', 'INTERCOMPANY_ELIMINATION'
        ];
    }

    // Load subcategories from API
    try {
        const subcategoriesResponse = await fetch('/api/subcategories');
        const subcategoriesData = await subcategoriesResponse.json();
        cachedSubcategories = subcategoriesData.subcategories || [];
        console.log(`✅ Loaded ${cachedSubcategories.length} subcategories from API`);
    } catch (error) {
        console.error('Failed to load subcategories:', error);
        // Use fallback if API fails
        cachedSubcategories = [
            'Bank Fees', 'Direct Costs', 'Fuel', 'General Administrative',
            'Hosting Revenue', 'Interest on Operations', 'Internal Transfer',
            'Materials', 'Meals', 'Personal Expenses', 'Return of Funds',
            'Technology Expense', 'Trading Revenue', 'Travel'
        ];
    }
}

function setupEventListeners() {
    // Column sorting
    document.querySelectorAll('.sortable').forEach(th => {
        th.style.cursor = 'pointer';
        th.addEventListener('click', () => {
            const sortField = th.dataset.sort;
            sortTransactions(sortField);
        });
    });

    // Filter button
    document.getElementById('applyFilters').addEventListener('click', () => {
        currentPage = 1;
        loadTransactions();
    });

    // Clear filters button
    document.getElementById('clearFilters').addEventListener('click', clearFilters);

    // Refresh button
    document.getElementById('refreshData').addEventListener('click', () => {
        currentPage = 1;
        loadTransactions();
    });

    // Export CSV button
    document.getElementById('exportCSV').addEventListener('click', exportToCSV);

    // Note: Select All checkbox listener is set up in renderTransactionTable()
    // because the checkbox is inside the table <thead> which must be rendered first

    // Archive Selected button
    const archiveBtn = document.getElementById('archiveSelected');
    console.log('🔵 Setting up Archive Selected button:', archiveBtn);
    if (archiveBtn) {
        archiveBtn.addEventListener('click', archiveSelectedTransactions);
        console.log('✅ Archive Selected event listener attached');
    } else {
        console.error('❌ Archive Selected button not found in DOM!');
    }

    // Show Archived toggle button
    document.getElementById('showArchived').addEventListener('click', toggleArchivedView);

    // Quick filter buttons
    document.getElementById('filterTodos').addEventListener('click', () => {
        document.getElementById('needsReview').value = 'true';
        currentPage = 1;
        loadTransactions();
    });

    document.getElementById('filter2025').addEventListener('click', () => {
        document.getElementById('startDate').value = '2025-01-01';
        document.getElementById('endDate').value = '2025-12-31';
        currentPage = 1;
        loadTransactions();
    });

    document.getElementById('filter2024').addEventListener('click', () => {
        document.getElementById('startDate').value = '2024-01-01';
        document.getElementById('endDate').value = '2024-12-31';
        currentPage = 1;
        loadTransactions();
    });

    document.getElementById('filterYTD').addEventListener('click', () => {
        const now = new Date();
        document.getElementById('startDate').value = '2025-01-01';
        document.getElementById('endDate').value = now.toISOString().split('T')[0];
        currentPage = 1;
        loadTransactions();
    });

    // Pagination buttons
    document.getElementById('prevPage').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            loadTransactions();
        }
    });

    document.getElementById('nextPage').addEventListener('click', () => {
        if (currentPage < totalPages) {
            currentPage++;
            loadTransactions();
        }
    });

    // Per-page size selector buttons
    document.querySelectorAll('.btn-per-page').forEach(button => {
        button.addEventListener('click', () => {
            const newPerPage = parseInt(button.dataset.perPage);
            if (newPerPage !== perPageSize) {
                perPageSize = newPerPage;
                currentPage = 1;

                // Save to localStorage
                localStorage.setItem('perPageSize', perPageSize);

                // Update URL parameters
                updateURLParameters();

                // Update active state
                document.querySelectorAll('.btn-per-page').forEach(btn => {
                    btn.classList.remove('active');
                });
                button.classList.add('active');

                loadTransactions();
            }
        });
    });

    // Modal close handlers
    document.querySelector('.close').addEventListener('click', closeModal);
    document.getElementById('suggestionsModal').addEventListener('click', (e) => {
        if (e.target.id === 'suggestionsModal') {
            closeModal();
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
        }
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

    // Reset to first page and reload
    currentPage = 1;
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

    // Add archived filter
    if (showingArchived) {
        params.append('show_archived', 'true');
    }

    // Add pagination
    params.append('page', currentPage);
    params.append('per_page', perPageSize);

    return params.toString();
}

function updateURLParameters() {
    const query = buildFilterQuery();
    const newUrl = `${window.location.pathname}?${query}`;
    window.history.pushState({}, '', newUrl);
}

async function loadTransactions() {
    if (isLoading) return;

    try {
        isLoading = true;
        showLoadingState();

        const query = buildFilterQuery();
        const url = `/api/transactions?${query}`;

        const response = await fetch(url);
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        currentTransactions = data.transactions || [];

        // Update pagination info
        if (data.pagination) {
            currentPage = data.pagination.page;
            totalPages = data.pagination.pages;
            updatePaginationControls();
        }

        renderTransactionTable(currentTransactions);
        updateTableInfo(data.pagination);
        loadDashboardStats();

        // Update URL parameters to reflect current state
        updateURLParameters();

    } catch (error) {
        console.error('Error loading transactions:', error);
        showToast('Error loading transactions: ' + error.message, 'error');
        document.getElementById('transactionTableBody').innerHTML =
            '<tr><td colspan="13" class="loading">Error loading transactions</td></tr>';
    } finally {
        isLoading = false;
    }
}

function showLoadingState() {
    document.getElementById('transactionTableBody').innerHTML =
        '<tr><td colspan="13" class="loading">Loading transactions...</td></tr>';
    document.getElementById('tableInfo').textContent = 'Loading...';
}

// Helper function to determine category class based on amount
function getCategoryClass(amount) {
    const val = parseFloat(amount || 0);
    if (val > 0) return 'revenue';
    if (val < 0) return 'expense';
    return 'unclassified';
}

// Helper function to format currency with icon
function formatCurrency(amount, currency) {
    if (!amount || amount === 0) return '';
    const isCrypto = ['BTC', 'ETH', 'TAO', 'SOL', 'USDC', 'USDT'].includes(currency);
    const currencyClass = isCrypto ? 'crypto' : 'fiat';
    const formattedAmount = parseFloat(amount).toFixed(isCrypto ? 4 : 2);
    return `<span class="currency-icon ${currencyClass}">${formattedAmount} ${currency || 'USD'}</span>`;
}

// Format crypto token amounts (without dollar signs, show token quantity)
function formatCryptoAmount(amount, currency) {
    console.log(`formatCryptoAmount called with amount: ${amount}, currency: ${currency}`);
    if (!amount || amount === 0) return '';
    const isCrypto = ['BTC', 'ETH', 'TAO', 'SOL', 'USDC', 'USDT'].includes(currency);
    if (isCrypto) {
        // Use different precision based on token type
        let precision = 4; // default precision
        if (currency === 'BTC') precision = 8;  // BTC needs more precision
        if (currency === 'TAO') precision = 4;  // TAO uses 4 decimal places
        if (currency === 'USDC' || currency === 'USDT') precision = 2; // stablecoins use 2

        const tokenAmount = parseFloat(amount).toFixed(precision);
        const result = `<span class="crypto">${tokenAmount} ${currency}</span>`;
        console.log(`formatCryptoAmount returning: ${result}`);
        return result;
    }
    return '';
}

/**
 * Format accounting category as "PRIMARY: Subcategory"
 * e.g., "OPERATING_EXPENSE: Bank Fees" or "REVENUE: Mining Revenue"
 */
function formatAccountingCategory(primaryCategory, subcategory) {
    // If neither exists, return N/A
    if (!primaryCategory && !subcategory) {
        return 'N/A';
    }

    // If only primary exists
    if (primaryCategory && !subcategory) {
        return primaryCategory;
    }

    // If only subcategory exists (shouldn't happen, but handle gracefully)
    if (!primaryCategory && subcategory) {
        return subcategory;
    }

    // Both exist - combine as "PRIMARY: Subcategory"
    return `${primaryCategory}: ${subcategory}`;
}

// Helper function to truncate text with tooltip
function truncateText(text, maxLength = 30) {
    if (!text || text.length <= maxLength) return text;
    return `<span title="${text}">${text.substring(0, maxLength)}...</span>`;
}

// Function to load correct dashboard statistics from backend
async function loadDashboardStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        updateSummaryStatsDisplay(data);
    } catch (error) {
        console.error('Error loading dashboard stats:', error);
        showToast('Error loading dashboard statistics: ' + error.message, 'error');
    }
}

// Helper function to update summary statistics display with backend data
function updateSummaryStatsDisplay(stats) {
    const statsElements = document.querySelectorAll('.stat-card');
    if (statsElements.length >= 4) {
        // Update total transactions with correct count from backend
        const totalElement = statsElements[0].querySelector('.stat-number');
        if (totalElement) totalElement.textContent = stats.total_transactions || 0;

        // Update total revenue with correct sum from backend
        const revenueElement = statsElements[1].querySelector('.stat-number');
        if (revenueElement) {
            revenueElement.textContent = '$' + (stats.total_revenue || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            revenueElement.className = 'stat-number positive';
        }

        // Update total expenses with correct sum from backend
        const expenseElement = statsElements[2].querySelector('.stat-number');
        if (expenseElement) {
            expenseElement.textContent = '$' + (stats.total_expenses || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            expenseElement.className = 'stat-number negative';
        }

        // Update needs review with correct count from backend
        const reviewElement = statsElements[3].querySelector('.stat-number');
        if (reviewElement) {
            const needsReview = stats.needs_review || 0;
            reviewElement.textContent = needsReview;
            reviewElement.className = needsReview > 0 ? 'stat-number warning' : 'stat-number';
        }
    }
}

function renderTransactionTable(transactions) {
    const tbody = document.getElementById('transactionTableBody');

    if (transactions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="13" class="loading">No transactions found</td></tr>';
        return;
    }

    tbody.innerHTML = transactions.map(transaction => {
        const amount = parseFloat(transaction.amount || 0);
        const amountClass = amount > 0 ? 'amount-positive' : amount < 0 ? 'amount-negative' : '';
        const formattedAmount = Math.abs(amount).toLocaleString('en-US', {
            style: 'currency',
            currency: 'USD'
        });

        const confidence = transaction.confidence ?
            (parseFloat(transaction.confidence) * 100).toFixed(0) + '%' : 'N/A';

        let confidenceClass = 'confidence-high';
        if (transaction.confidence) {
            const conf = parseFloat(transaction.confidence);
            if (conf < 0.6) confidenceClass = 'confidence-low';
            else if (conf < 0.8) confidenceClass = 'confidence-medium';
        } else {
            confidenceClass = 'confidence-low';
        }

        return `
            <tr data-transaction-id="${transaction.transaction_id || ''}">
                <td><input type="checkbox" class="transaction-select-cb" data-transaction-id="${transaction.transaction_id || ''}"></td>
                <td>${formatDate(transaction.date) || 'N/A'}</td>
                <td class="editable-field" data-field="origin" data-transaction-id="${transaction.transaction_id}">
                    ${transaction.origin || 'Unknown'}
                </td>
                <td class="editable-field" data-field="destination" data-transaction-id="${transaction.transaction_id}">
                    ${transaction.destination || 'Unknown'}
                </td>
                <td class="editable-field description-cell" data-field="description" data-transaction-id="${transaction.transaction_id}">
                    ${truncateText(transaction.description, 40) || 'N/A'}
                </td>
                <td class="${amountClass}">${formattedAmount}</td>
                <td class="crypto-cell">${formatCryptoAmount(transaction.crypto_amount, transaction.currency)}</td>
                <td class="editable-field smart-dropdown" data-field="classified_entity" data-transaction-id="${transaction.transaction_id}">
                    <span class="entity-category ${getCategoryClass(transaction.amount)}">${transaction.classified_entity?.replace(' N/A', '') || 'Unclassified'}</span>
                </td>
                <td class="editable-field smart-dropdown primary-category-cell" data-field="accounting_category" data-transaction-id="${transaction.transaction_id}">
                    ${transaction.accounting_category || 'N/A'}
                </td>
                <td class="editable-field smart-dropdown subcategory-cell" data-field="subcategory" data-transaction-id="${transaction.transaction_id}">
                    ${transaction.subcategory || 'N/A'}
                </td>
                <td class="editable-field" data-field="justification" data-transaction-id="${transaction.transaction_id}">
                    ${truncateText(transaction.justification, 35) || 'Unknown'}
                </td>
                <td>
                    <span class="confidence-score ${confidenceClass}">${confidence}</span>
                </td>
                <td class="source-cell">${truncateText(transaction.source_file, 25) || 'N/A'}</td>
                <td>
                    <button class="btn-secondary btn-sm" onclick="getAISmartSuggestions('${transaction.transaction_id || ''}', ${JSON.stringify(transaction).replace(/'/g, "\\'").replace(/"/g, '&quot;')})" title="Get AI-powered suggestions for this transaction">
                        🤖 AI
                    </button>
                    <button class="btn-secondary btn-sm" onclick="viewTransactionDetails('${transaction.transaction_id || ''}')" style="margin-left: 5px;">
                        View
                    </button>
                    <button class="btn-secondary btn-sm" onclick="archiveTransaction('${transaction.transaction_id || ''}')" style="margin-left: 5px;">
                        🗄️ Archive
                    </button>
                </td>
            </tr>
        `;
    }).join('');

    // Set up inline editing
    setupInlineEditing();

    // Set up checkbox change listeners for archive button visibility
    document.querySelectorAll('.transaction-select-cb').forEach(cb => {
        cb.addEventListener('change', updateArchiveButtonVisibility);
    });

    // Set up Select All checkbox listener (must be done after table is rendered)
    const selectAllCheckbox = document.getElementById('selectAll');
    if (selectAllCheckbox) {
        // Remove any existing listeners to prevent duplicates
        selectAllCheckbox.replaceWith(selectAllCheckbox.cloneNode(true));
        const newSelectAll = document.getElementById('selectAll');

        newSelectAll.addEventListener('change', function() {
            console.log('🔵 Select All checkbox changed! Checked:', this.checked);
            const checkboxes = document.querySelectorAll('.transaction-select-cb');
            console.log('🔵 Found transaction checkboxes:', checkboxes.length);
            checkboxes.forEach((cb, index) => {
                cb.checked = this.checked;
                console.log(`🔵 Set checkbox ${index} to:`, cb.checked);
            });
            updateArchiveButtonVisibility();
        });
        console.log('✅ Select All checkbox event listener attached (from renderTransactionTable)');
    }

    // Set up drag-down handles for Excel-like fill
    setTimeout(() => {
        setupDragDownHandles();
    }, 100);
}

// Track if we've already set up the delegated event listener
let inlineEditingSetup = false;

function setupInlineEditing() {
    // Use event delegation instead of attaching to each field
    // This prevents duplicate listeners and works even after DOM updates
    if (inlineEditingSetup) {
        return; // Already set up, don't duplicate
    }

    const tbody = document.getElementById('transactionTableBody');
    if (!tbody) return;

    tbody.addEventListener('click', (e) => {
        // CRITICAL: Don't start editing if clicking on drag handle or sort dot
        if (e.target.classList.contains('drag-handle') ||
            e.target.classList.contains('sort-dot')) {
            console.log('🚫 Click on drag-handle/sort-dot - skipping inline edit');
            return;
        }

        // Find the closest editable field
        const field = e.target.closest('.editable-field');
        if (!field) return;

        console.log('🔷 Table body click detected');
        console.log('🔷 Clicked element:', e.target.tagName, e.target.className);
        console.log('🔷 Field already editing?', field.classList.contains('editing'));
        console.log('🔷 Field transaction ID:', field.dataset.transactionId);

        // CRITICAL: Don't start editing if clicking on an input/select that's already in edit mode
        const clickedElement = e.target;
        if (clickedElement.classList.contains('inline-input') ||
            clickedElement.classList.contains('smart-select') ||
            clickedElement.tagName === 'OPTION') {
            console.log('⚪ Click on input/select/option detected - ignoring to prevent re-initialization');
            return; // Don't restart editing
        }

        if (!field.classList.contains('editing')) {
            console.log('🔷 Starting edit for transaction:', field.dataset.transactionId);
            startEditing(field);
        } else {
            console.log('🔷 Field already in editing mode - not restarting');
        }
    });

    inlineEditingSetup = true;
}

function startEditing(field) {
    const currentValue = field.textContent.trim();
    const fieldName = field.dataset.field;
    const transactionId = field.dataset.transactionId;

    field.classList.add('editing');
    // Store original value for cancel/custom operations
    field.dataset.originalValue = currentValue;

    // Check if this is a smart dropdown field
    if (field.classList.contains('smart-dropdown')) {
        createSmartDropdown(field, currentValue, fieldName);
    } else {
        field.innerHTML = `<input type="text" class="inline-input" value="${currentValue === 'N/A' ? '' : currentValue}" />`;
    }

    const input = field.querySelector('.inline-input, .smart-select');
    if (!input) return; // Exit if no input element found

    input.focus();
    if (input.select) input.select();

    // For text inputs: Save on Enter or blur
    // For select dropdowns: Only handle keyboard events (change event handles selection)
    const isSelect = input.classList.contains('smart-select');

    if (!isSelect) {
        // Text input: save on blur
        const saveEdit = async () => {
            const newValue = input.value.trim();
            console.log('🟢 Blur event fired - saveEdit called with value:', newValue);
            await updateTransactionField(transactionId, fieldName, newValue, field);
        };

        input.addEventListener('blur', saveEdit);
    }

    // Cancel on Escape for both text inputs and selects
    const cancelEdit = () => {
        field.classList.remove('editing');
        field.innerHTML = currentValue;
        setupInlineEditing(); // Re-setup event listeners
    };

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !isSelect) {
            e.preventDefault();
            const newValue = input.value.trim();
            updateTransactionField(transactionId, fieldName, newValue, field);
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cancelEdit();
        }
    });
}

async function createSmartDropdown(field, currentValue, fieldName) {
    // Define options for different field types
    // Use cached API data for accounting_category and subcategory
    const fieldOptions = {
        'classified_entity': [
            'Delta LLC',
            'Delta Prop Shop LLC',
            'Infinity Validator',
            'Delta Mining Paraguay S.A.',
            'Delta Brazil Operations',
            'Internal Transfer',
            'Personal'
        ],
        'accounting_category': cachedAccountingCategories.length > 0 ? cachedAccountingCategories : [
            'REVENUE',
            'COGS',
            'OPERATING_EXPENSE',
            'INTEREST_EXPENSE',
            'OTHER_INCOME',
            'OTHER_EXPENSE',
            'INCOME_TAX_EXPENSE',
            'ASSET',
            'LIABILITY',
            'EQUITY',
            'INTERCOMPANY_ELIMINATION'
        ],
        'subcategory': cachedSubcategories.length > 0 ? cachedSubcategories : [
            'Bank Fees',
            'Direct Costs',
            'Fuel',
            'General Administrative',
            'Hosting Revenue',
            'Interest on Operations',
            'Internal Transfer',
            'Materials',
            'Meals',
            'Personal Expenses',
            'Return of Funds',
            'Technology Expense',
            'Trading Revenue',
            'Travel'
        ]
    };

    let options = fieldOptions[fieldName] || [];

    // Create smart dropdown with existing options + custom input
    let selectHTML = `<select class="smart-select inline-input">`;

    // CRITICAL FIX: If current value is N/A, add it as the first selected option
    // Without this, browser auto-selects the first option (alphabetically first, like "Bank Fees")
    // causing lastValue to be set incorrectly
    if (currentValue === 'N/A') {
        selectHTML += `<option value="N/A" selected>-- Select Category --</option>`;
        console.log(`🟠 Added N/A as selected option to prevent auto-selection of first category`);
    }

    // Add current value as first option if not in list and not N/A
    if (currentValue !== 'N/A' && !options.includes(currentValue)) {
        selectHTML += `<option value="${currentValue}" selected>${currentValue}</option>`;
    }

    // Add predefined options
    options.forEach(option => {
        const selected = option === currentValue ? 'selected' : '';
        selectHTML += `<option value="${option}" ${selected}>${option}</option>`;
        if (selected) {
            console.log(`🟠 Option "${option}" is marked as SELECTED (matches currentValue: "${currentValue}")`);
        }
    });

    // Add AI assistant option (above custom)
    selectHTML += `<option value="__ai_assistant__">🤖 Ask AI Assistant...</option>`;
    // Add custom option
    selectHTML += `<option value="__custom__">+ Add Custom...</option>`;
    selectHTML += `</select>`;

    field.innerHTML = selectHTML;

    // Handle custom option selection and regular selections
    const select = field.querySelector('.smart-select');

    console.log('🟣 Setting up change listener for dropdown');
    console.log('🟣 Transaction ID:', field.dataset.transactionId);
    console.log('🟣 Field name:', field.dataset.field);
    console.log('🟣 Current value:', currentValue);
    console.log('🟣 Dropdown element:', select);

    // CRITICAL: Stop click events from bubbling to parent field
    // Without this, clicking the dropdown triggers the field's click handler
    // which recreates the dropdown and prevents the change event from firing
    select.addEventListener('click', function(e) {
        console.log('🟡 Click event on dropdown - stopping propagation');
        e.stopPropagation(); // Prevent parent field from receiving click and recreating dropdown
    });

    select.addEventListener('mousedown', function(e) {
        console.log('🟤 Mousedown event on dropdown - stopping propagation');
        e.stopPropagation(); // Also stop mousedown to prevent any parent interactions
    });

    console.log('🟢 Attaching change event listener to select element');

    // Store the initial value to detect changes
    let lastValue = select.value;
    console.log('🟢 Initial lastValue set to:', lastValue);
    console.log('🟢 currentValue from field:', currentValue);

    // Try multiple event approaches since change isn't firing reliably
    const handleSelection = async function(e) {
        // CRITICAL: Skip if drag operation is in progress
        if (dragFillState.isDragging) {
            console.log('🚫 Skipping inline edit - drag operation in progress');
            return;
        }

        console.log('🔵 Selection handler called! Event:', e.type);
        console.log('🔵 Current value:', this.value);
        console.log('🔵 Last value:', lastValue);
        console.log('🔵 Previous field value was:', currentValue);

        // Skip if user selected the N/A placeholder
        if (this.value === 'N/A' && currentValue === 'N/A') {
            console.log('🔵 N/A selected but field is already N/A, skipping');
            return;
        }

        // Only proceed if value actually changed
        if (this.value === lastValue && e.type !== 'change') {
            console.log('🔵 Value unchanged, skipping');
            return;
        }

        lastValue = this.value;

        if (this.value === '__ai_assistant__') {
            console.log('🔵 AI Assistant option selected');
            e.stopPropagation();

            // Get transaction details
            const transactionId = field.dataset.transactionId;
            const row = field.closest('tr');
            const description = row.querySelector('[data-field="description"]')?.textContent?.trim() || '';
            const amount = row.querySelector('[data-field="amount"]')?.textContent?.trim() || '';
            const entity = row.querySelector('[data-field="classified_entity"]')?.textContent?.trim() || '';

            // Open AI assistant modal
            showAIAccountingAssistant(transactionId, { description, amount, entity }, field);

            // Reset dropdown to previous value
            setTimeout(() => {
                select.value = currentValue;
            }, 100);

        } else if (this.value === '__custom__') {
            console.log('🔵 Custom option selected');
            e.stopPropagation(); // Prevent other handlers from firing

            // Get the transaction ID and field name from the parent field
            const transactionId = field.dataset.transactionId;
            const fieldName = field.dataset.field;
            const currentValue = field.dataset.originalValue || field.textContent.trim();

            // Replace with text input for custom entry
            field.innerHTML = `<input type="text" class="inline-input" value="" placeholder="Enter custom value..." />`;
            const input = field.querySelector('.inline-input');
            input.focus();

            // Set up event handlers for the new input
            const saveCustomEdit = async () => {
                const newValue = input.value.trim();
                if (newValue) { // Only save if there's a value
                    await updateTransactionField(transactionId, fieldName, newValue, field);
                } else {
                    // Cancel if empty
                    field.classList.remove('editing');
                    field.innerHTML = currentValue || 'N/A';
                    setupInlineEditing();
                }
            };

            const cancelCustomEdit = () => {
                field.classList.remove('editing');
                field.innerHTML = currentValue || 'N/A';
                setupInlineEditing();
            };

            input.addEventListener('blur', saveCustomEdit);
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    saveCustomEdit();
                } else if (e.key === 'Escape') {
                    e.preventDefault();
                    cancelCustomEdit();
                }
            });
        } else {
            // Handle regular dropdown selection - immediately save
            console.log('🔵 Regular option selected, calling updateTransactionField');
            const transactionId = field.dataset.transactionId;
            const fieldName = field.dataset.field;
            const newValue = this.value;

            console.log('🔵 Transaction ID:', transactionId, 'Field:', fieldName, 'Value:', newValue);

            // Immediately update the transaction field
            await updateTransactionField(transactionId, fieldName, newValue, field);
        }
    };

    // Attach to multiple events to ensure we catch the selection
    select.addEventListener('change', handleSelection);
    select.addEventListener('blur', handleSelection);

    console.log('🟢 Event listeners attached: change, blur');
}

async function updateTransactionField(transactionId, field, value, fieldElement) {
    try {
        const response = await fetch('/api/update_transaction', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                transaction_id: transactionId,
                field: field,
                value: value
            })
        });

        const result = await response.json();

        if (result.success) {
            fieldElement.classList.remove('editing');
            fieldElement.innerHTML = value || 'N/A';
            showToast('Transaction updated successfully', 'success');
            setupInlineEditing(); // Re-setup event listeners

            // Re-add drag handles after cell content changes
            setTimeout(() => {
                setupDragDownHandles();
            }, 50);

            // SMART CONFIDENCE UPDATE: Use the updated confidence value from backend
            console.log('🔍 DEBUG: API response:', result);
            console.log('🔍 DEBUG: Updated confidence value:', result.updated_confidence);

            if (result.updated_confidence !== undefined && result.updated_confidence !== null) {
                const row = fieldElement.closest('tr');
                console.log('🔍 DEBUG: Found row:', row);

                if (row) {
                    // Find the confidence span by its class name (not data-field)
                    const confidenceCell = row.querySelector('.confidence-score');
                    console.log('🔍 DEBUG: Found confidence cell:', confidenceCell);

                    if (confidenceCell) {
                        const confidencePercent = Math.round(result.updated_confidence * 100);
                        const oldText = confidenceCell.textContent;
                        confidenceCell.textContent = confidencePercent + '%';

                        // Update CSS class based on confidence level
                        if (confidencePercent >= 90) {
                            confidenceCell.className = 'confidence-score confidence-high';
                        } else if (confidencePercent >= 70) {
                            confidenceCell.className = 'confidence-score confidence-medium';
                        } else {
                            confidenceCell.className = 'confidence-score confidence-low';
                        }

                        console.log(`✅ CONFIDENCE UPDATE: Changed from ${oldText} to ${confidencePercent}% for transaction ${transactionId}`);
                    } else {
                        console.warn('⚠️  Could not find confidence cell in row');
                    }
                } else {
                    console.warn('⚠️  Could not find parent row');
                }
            } else {
                console.warn('⚠️  No updated_confidence in API response');
            }

            // For description changes, check if we should update similar transactions
            if (field === 'description') {
                checkForSimilarTransactions(transactionId, value);
            }

            // For entity changes, check if we should update similar transactions from same source
            if (field === 'classified_entity') {
                checkForSimilarEntities(transactionId, value);
            }

            // For accounting category changes, check if we should update similar transactions
            if (field === 'accounting_category') {
                console.log('💚 Accounting category updated, checking for similar transactions...');
                console.log('💚 Transaction ID:', transactionId, 'New Category:', value);
                checkForSimilarAccountingCategories(transactionId, value);
            }
        } else {
            throw new Error(result.error || 'Failed to update');
        }

    } catch (error) {
        console.error('Error updating transaction:', error);
        showToast('Error updating transaction: ' + error.message, 'error');

        // Restore original value
        fieldElement.classList.remove('editing');
        const originalValue = fieldElement.dataset.originalValue || 'N/A';
        fieldElement.innerHTML = originalValue;
        setupInlineEditing();
    }
}

async function showAISuggestions(field) {
    const fieldType = field.dataset.field;
    const transactionId = field.dataset.transactionId;
    const currentValue = field.textContent.trim();

    try {
        // CRITICAL FIX: Clear modal content BEFORE showing it to prevent stale data from appearing
        document.getElementById('suggestionsList').innerHTML = '<div class="loading">Loading AI suggestions...</div>';

        // Now show the modal with fresh loading state
        showModal();

        const url = `/api/suggestions?field_type=${fieldType}&transaction_id=${transactionId}&current_value=${encodeURIComponent(currentValue)}`;
        const response = await fetch(url);
        const data = await response.json();

        if (data.error) {
            // Create a more descriptive error message
            const errorMsg = data.error.includes('ANTHROPIC_API_KEY')
                ? 'Claude AI not configured - contact administrator'
                : data.error.includes('failed to generate')
                ? 'AI service temporarily unavailable'
                : data.error;
            throw new Error(errorMsg);
        }

        if (data.suggestions && data.suggestions.length > 0) {
            document.getElementById('suggestionsList').innerHTML = data.suggestions.map(suggestion =>
                `<div class="suggestion-item" onclick="applySuggestion('${transactionId}', '${fieldType}', '${suggestion.replace(/'/g, "\\'")}', this)">${suggestion}</div>`
            ).join('') + `
                <div class="custom-input-section">
                    <input type="text" id="customInput" placeholder="Or type your own..." class="custom-input"
                           onkeypress="if(event.key==='Enter') applyCustomInput('${transactionId}', '${fieldType}')" />
                    <button onclick="applyCustomInput('${transactionId}', '${fieldType}')" class="apply-custom-btn">Apply</button>
                </div>
            `;
        } else {
            document.getElementById('suggestionsList').innerHTML = `
                <div class="loading">No AI suggestions available</div>
                <div class="custom-input-section">
                    <input type="text" id="customInput" placeholder="Type your custom value..." class="custom-input"
                           onkeypress="if(event.key==='Enter') applyCustomInput('${transactionId}', '${fieldType}')" />
                    <button onclick="applyCustomInput('${transactionId}', '${fieldType}')" class="apply-custom-btn">Apply</button>
                </div>
            `;
        }

    } catch (error) {
        console.error('Error getting AI suggestions:', error);
        let errorMessage = 'Error loading AI suggestions';

        // Check if the error response has more specific information
        if (error.message && error.message.includes('API')) {
            errorMessage = error.message;
        } else if (error instanceof TypeError) {
            errorMessage = 'Network error - check your connection';
        }

        document.getElementById('suggestionsList').innerHTML = `
            <div class="loading">${errorMessage}</div>
            <div class="custom-input-section">
                <input type="text" id="customInput" placeholder="Type your custom value..." class="custom-input"
                       onkeypress="if(event.key==='Enter') applyCustomInput('${transactionId}', '${fieldType}')" />
                <button onclick="applyCustomInput('${transactionId}', '${fieldType}')" class="apply-custom-btn">Apply</button>
            </div>
        `;
    }
}

async function applySuggestion(transactionId, field, value, element) {
    try {
        // Find the field element
        const fieldElement = document.querySelector(`[data-transaction-id="${transactionId}"][data-field="${field}"]`);

        if (fieldElement) {
            await updateTransactionField(transactionId, field, value, fieldElement);

            // Log user interaction for learning system
            await logUserInteraction(transactionId, field, fieldElement.textContent.trim(), value, 'accepted_ai_suggestion');

            // Remove the AI suggestion button after applying suggestion
            const aiBtn = fieldElement.querySelector('.ai-suggestions-btn');
            if (aiBtn) {
                aiBtn.remove();
            }

            // For description field, automatically check for similar transactions
            if (field === 'description') {
                checkForSimilarTransactions(transactionId, value);
            }

            closeModal();
        }
    } catch (error) {
        console.error('Error applying suggestion:', error);
        showToast('Error applying suggestion: ' + error.message, 'error');
    }
}

async function applyCustomInput(transactionId, fieldType) {
    try {
        const customInput = document.getElementById('customInput');
        const value = customInput.value.trim();

        if (!value) {
            showToast('Please enter a value', 'error');
            return;
        }

        // Find the field element
        const fieldElement = document.querySelector(`[data-transaction-id="${transactionId}"][data-field="${fieldType}"]`);

        if (fieldElement) {
            await updateTransactionField(transactionId, fieldType, value, fieldElement);

            // Log user interaction for learning system
            await logUserInteraction(transactionId, fieldType, fieldElement.textContent.trim(), value, 'custom_input');

            // Remove the AI suggestion button after applying custom input
            const aiBtn = fieldElement.querySelector('.ai-suggestions-btn');
            if (aiBtn) {
                aiBtn.remove();
            }

            // For description field, automatically check for similar transactions
            if (fieldType === 'description') {
                checkForSimilarTransactions(transactionId, value);
            }

            closeModal();
        }
    } catch (error) {
        console.error('Error applying custom input:', error);
        showToast('Error applying custom input: ' + error.message, 'error');
    }
}

async function checkForSimilarEntities(transactionId, newEntity) {
    try {
        // Find current transaction
        const currentTx = currentTransactions.find(t => t.transaction_id === transactionId);
        if (!currentTx) return;

        // Use Claude AI to find similar transactions for entity classification
        // Call the API endpoint that uses Claude to intelligently find similar transactions
        const response = await fetch(`/api/suggestions?transaction_id=${transactionId}&field_type=similar_entities&value=${encodeURIComponent(newEntity)}`);

        if (!response.ok) {
            console.error('Failed to get AI suggestions for similar entities');
            return;
        }

        const data = await response.json();
        const similarTxs = data.suggestions || [];

        if (similarTxs.length > 0) {
            const modal = document.getElementById('suggestionsModal');
            const content = document.getElementById('suggestionsContent');

            // Add similar-transactions-modal class to modal-content
            modal.querySelector('.modal-content').classList.add('similar-transactions-modal');

            // Format transaction date helper
            const formatDate = (dateStr) => {
                if (!dateStr) return '';
                const date = new Date(dateStr);
                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            };

            // Format amount helper
            const formatAmount = (amount) => {
                const val = parseFloat(amount || 0);
                return `<span class="transaction-amount ${val >= 0 ? 'positive' : 'negative'}">
                    ${val >= 0 ? '+' : ''}$${Math.abs(val).toFixed(2)}
                </span>`;
            };

            content.innerHTML = `
                <div class="modal-header">
                    <h3>🔄 Update Similar Transactions</h3>
                    <span class="close" onclick="closeModal()">&times;</span>
                </div>

                <div class="similar-selection-header">
                    <div class="selection-controls">
                        <button onclick="selectAllSimilar(true)">☑ Select All</button>
                        <button onclick="selectAllSimilar(false)">☐ Deselect All</button>
                    </div>
                    <div class="selection-counter">
                        <span id="selectedCount">0</span> of ${similarTxs.length} selected
                    </div>
                </div>

                <div class="modal-body">
                    <div class="update-preview">
                        <h4>📋 Entity Update Preview</h4>
                        <p><strong>Change:</strong> Entity → "${newEntity}"</p>
                        <p><strong>Matching Criteria:</strong> 🤖 Claude AI analyzed unclassified transactions and found similar patterns</p>
                        <p><strong>Impact:</strong> <span id="impactSummary">Select transactions below</span></p>
                        <div class="matching-info">
                            <small>✨ AI-powered: Claude analyzed description patterns to find transactions from the same business/entity</small>
                            ${data.has_learned_patterns === false ? '<small style="color: #888; display: block; margin-top: 4px;">(not AI based - intelligent matching used as fallback. Pattern learning will improve accuracy over time)</small>' : ''}
                        </div>
                    </div>

                    <div class="transactions-list">
                        ${similarTxs.map((t, index) => `
                            <div class="transaction-item" data-tx-id="${t.transaction_id}">
                                <input type="checkbox"
                                       class="transaction-checkbox similar-tx-cb"
                                       id="cb-${index}"
                                       data-amount="${t.amount || 0}"
                                       onchange="updateSelectionSummary()">
                                <div class="transaction-details">
                                    <div class="transaction-info">
                                        <div class="transaction-date">${formatDate(t.date)}</div>
                                        <div class="transaction-description" title="${t.description}">
                                            ${t.description}
                                        </div>
                                        <div class="transaction-meta">
                                            <span>Current: ${t.classified_entity || 'Unknown'}</span>
                                            <span>•</span>
                                            <span>Confidence: ${Math.round((t.confidence || 0) * 100)}%</span>
                                        </div>
                                    </div>
                                    ${formatAmount(t.amount)}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <div class="modal-actions">
                    <button class="btn-secondary" onclick="closeModal()">Cancel</button>
                    <button class="btn-secondary" onclick="closeModal()">Skip These</button>
                    <button class="btn-primary" id="updateSelectedBtn" onclick="applyEntityToSelected('${newEntity}')" disabled>
                        Update Selected Transactions
                    </button>
                </div>
            `;

            // Initialize selection
            updateSelectionSummary();
            showModal();
        }
    } catch (error) {
        console.error('Error checking similar entities:', error);
    }
}

// Helper function to handle select all/deselect all for similar entities modal
function selectAllSimilar(selectAll) {
    const checkboxes = document.querySelectorAll('.similar-transactions-modal .transaction-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAll;
    });
    updateSelectionSummary();
}

// Helper function to update selection summary for similar entities modal
function updateSelectionSummary() {
    const modal = document.querySelector('.similar-transactions-modal');
    if (!modal) return;

    const checkboxes = modal.querySelectorAll('.transaction-checkbox');
    const checkedBoxes = modal.querySelectorAll('.transaction-checkbox:checked');
    const updateBtn = modal.querySelector('#updateSelectedBtn');
    const selectionCounter = modal.querySelector('.selection-counter');
    const impactSummary = modal.querySelector('#impactSummary');

    // Update selection counter
    if (selectionCounter) {
        selectionCounter.textContent = `${checkedBoxes.length} of ${checkboxes.length} selected`;
    }

    // Update impact summary
    if (impactSummary) {
        if (checkedBoxes.length === 0) {
            impactSummary.textContent = 'Select transactions below';
        } else {
            let totalAmount = 0;
            checkedBoxes.forEach(cb => {
                const amount = parseFloat(cb.getAttribute('data-amount') || 0);
                totalAmount += amount;
            });
            impactSummary.innerHTML = `${checkedBoxes.length} transaction(s), Total: <strong>$${Math.abs(totalAmount).toFixed(2)}</strong>`;
        }
    }

    // Enable/disable update button
    if (updateBtn) {
        updateBtn.disabled = checkedBoxes.length === 0;
        updateBtn.style.opacity = checkedBoxes.length === 0 ? '0.6' : '1';
        updateBtn.style.cursor = checkedBoxes.length === 0 ? 'not-allowed' : 'pointer';
    }
}

// Helper function to apply entity to selected transactions
function applyEntityToSelected(newEntity) {
    const modal = document.querySelector('.similar-transactions-modal');
    if (!modal) return;

    const checkedBoxes = modal.querySelectorAll('.transaction-checkbox:checked');
    const transactionIds = [];

    checkedBoxes.forEach(checkbox => {
        const transactionItem = checkbox.closest('.transaction-item');
        if (transactionItem) {
            const transactionId = transactionItem.getAttribute('data-tx-id');
            if (transactionId) {
                transactionIds.push(transactionId);
            }
        }
    });

    if (transactionIds.length === 0) {
        alert('Please select at least one transaction to update.');
        return;
    }

    // Show confirmation dialog
    const confirmMsg = `Are you sure you want to update ${transactionIds.length} transaction(s) to entity "${newEntity}"?`;
    if (!confirm(confirmMsg)) return;

    // Make API call to update selected transactions
    fetch('/api/update_entity_bulk', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            transaction_ids: transactionIds,
            new_entity: newEntity
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
            showToast(`Successfully updated ${transactionIds.length} transaction(s).`, 'success');

            // Close modal and refresh the page to show updates
            closeModal();
            loadTransactions();
        } else {
            showToast('Error updating transactions: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error updating transactions. Please try again.', 'error');
    });
}

async function checkForSimilarAccountingCategories(transactionId, newCategory) {
    try {
        // Find current transaction to get context
        const currentTx = currentTransactions.find(t => t.transaction_id === transactionId);
        if (!currentTx) return;

        // Use Claude AI to find similar transactions for accounting category classification
        const response = await fetch(`/api/suggestions?transaction_id=${transactionId}&field_type=similar_accounting&value=${encodeURIComponent(newCategory)}`);

        if (!response.ok) {
            console.error('Failed to get AI suggestions for similar accounting categories');
            return;
        }

        const data = await response.json();
        const similarTxs = data.suggestions || [];

        if (similarTxs.length > 0) {
            const modal = document.getElementById('suggestionsModal');
            const content = document.getElementById('suggestionsContent');

            // Clear any previous loading states
            document.getElementById('suggestionsList').innerHTML = '';

            // Add similar-transactions-modal class to modal-content
            modal.querySelector('.modal-content').classList.add('similar-transactions-modal');

            // Format transaction date helper
            const formatDate = (dateStr) => {
                if (!dateStr) return '';
                const date = new Date(dateStr);
                return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            };

            // Format amount helper
            const formatAmount = (amount) => {
                const val = parseFloat(amount || 0);
                return `<span class="transaction-amount ${val >= 0 ? 'positive' : 'negative'}">
                    ${val >= 0 ? '+' : ''}$${Math.abs(val).toFixed(2)}
                </span>`;
            };

            content.innerHTML = `
                <div class="modal-header">
                    <h3>🔄 Update Similar Accounting Categories</h3>
                    <span class="close" onclick="closeModal()">&times;</span>
                </div>

                <div class="similar-selection-header">
                    <div class="selection-controls">
                        <button onclick="selectAllSimilarCategories(true)">☑ Select All</button>
                        <button onclick="selectAllSimilarCategories(false)">☐ Deselect All</button>
                    </div>
                    <div class="selection-counter">
                        <span id="selectedCategoryCount">0</span> of ${similarTxs.length} selected
                    </div>
                </div>

                <div class="modal-body">
                    <div class="update-preview">
                        <h4>📋 Category Update Preview</h4>
                        <p><strong>Change:</strong> Accounting Category → "${newCategory}"</p>
                        <p><strong>Matching Criteria:</strong> 🤖 Claude AI analyzed transaction types and purposes</p>
                        <p><strong>Impact:</strong> <span id="categoryImpactSummary">Select transactions below</span></p>
                        <div class="matching-info">
                            <small>✨ AI-powered: Claude analyzed descriptions to find similar transaction types, not based on amount</small>
                        </div>
                    </div>

                    <div class="transactions-list">
                        ${similarTxs.map((t, index) => `
                            <div class="transaction-item" data-tx-id="${t.transaction_id}">
                                <input type="checkbox"
                                       class="transaction-checkbox category-tx-cb"
                                       id="category-cb-${index}"
                                       data-amount="${t.amount || 0}"
                                       onchange="updateCategorySelectionSummary()">
                                <div class="transaction-details">
                                    <div class="transaction-info">
                                        <div class="transaction-date">${formatDate(t.date)}</div>
                                        <div class="transaction-description" title="${t.description}">
                                            ${t.description}
                                        </div>
                                        <div class="transaction-meta">
                                            <span>Entity: ${t.classified_entity || 'Unknown'}</span>
                                            <span>•</span>
                                            <span>Current: ${t.accounting_category || 'N/A'}</span>
                                            <span>•</span>
                                            <span>Confidence: ${Math.round((t.confidence || 0) * 100)}%</span>
                                        </div>
                                    </div>
                                    ${formatAmount(t.amount)}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <div class="modal-actions">
                    <button class="btn-secondary" onclick="closeModal()">Cancel</button>
                    <button class="btn-secondary" onclick="closeModal()">Skip These</button>
                    <button class="btn-primary" id="updateCategoryBtn" onclick="applyCategoryToSelected('${newCategory}')" disabled>
                        Update Selected Categories
                    </button>
                </div>
            `;

            // Initialize selection
            updateCategorySelectionSummary();
            showModal();
        }
    } catch (error) {
        console.error('Error checking similar accounting categories:', error);
    }
}

// Helper function to handle select all/deselect all for accounting category modal
function selectAllSimilarCategories(selectAll) {
    const checkboxes = document.querySelectorAll('.similar-transactions-modal .category-tx-cb');
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAll;
    });
    updateCategorySelectionSummary();
}

// Helper function to update selection summary for accounting category modal
function updateCategorySelectionSummary() {
    const modal = document.querySelector('.similar-transactions-modal');
    if (!modal) return;

    const checkboxes = modal.querySelectorAll('.category-tx-cb');
    const checkedBoxes = modal.querySelectorAll('.category-tx-cb:checked');
    const updateBtn = modal.querySelector('#updateCategoryBtn');
    const selectionCounter = modal.querySelector('#selectedCategoryCount');
    const impactSummary = modal.querySelector('#categoryImpactSummary');

    // Update selection counter
    if (selectionCounter) {
        selectionCounter.textContent = checkedBoxes.length;
    }

    // Update impact summary
    if (impactSummary) {
        if (checkedBoxes.length === 0) {
            impactSummary.textContent = 'Select transactions below';
        } else {
            let totalAmount = 0;
            checkedBoxes.forEach(cb => {
                const amount = parseFloat(cb.getAttribute('data-amount') || 0);
                totalAmount += amount;
            });
            impactSummary.innerHTML = `${checkedBoxes.length} transaction(s), Total: <strong>$${Math.abs(totalAmount).toFixed(2)}</strong>`;
        }
    }

    // Enable/disable update button
    if (updateBtn) {
        updateBtn.disabled = checkedBoxes.length === 0;
        updateBtn.style.opacity = checkedBoxes.length === 0 ? '0.6' : '1';
        updateBtn.style.cursor = checkedBoxes.length === 0 ? 'not-allowed' : 'pointer';
    }
}

// Helper function to apply category to selected transactions
function applyCategoryToSelected(newCategory) {
    const modal = document.querySelector('.similar-transactions-modal');
    if (!modal) return;

    const checkedBoxes = modal.querySelectorAll('.category-tx-cb:checked');
    const transactionIds = [];

    checkedBoxes.forEach(checkbox => {
        const transactionItem = checkbox.closest('.transaction-item');
        if (transactionItem) {
            const transactionId = transactionItem.getAttribute('data-tx-id');
            if (transactionId) {
                transactionIds.push(transactionId);
            }
        }
    });

    if (transactionIds.length === 0) {
        alert('Please select at least one transaction to update.');
        return;
    }

    // Show confirmation dialog
    const confirmMsg = `Are you sure you want to update ${transactionIds.length} transaction(s) to accounting category "${newCategory}"?`;
    if (!confirm(confirmMsg)) return;

    // Make API call to update selected transactions
    fetch('/api/update_category_bulk', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            transaction_ids: transactionIds,
            new_category: newCategory
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
            showToast(`Successfully updated ${transactionIds.length} transaction(s) to "${newCategory}".`, 'success');

            // Close modal and refresh the page to show updates
            closeModal();
            loadTransactions();
        } else {
            showToast('Error updating transactions: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Error updating transactions. Please try again.', 'error');
    });
}

async function applyCategoryToSimilar(transactionId, newCategory) {
    try {
        const response = await fetch('/api/update_similar_categories', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                transaction_id: transactionId,
                accounting_category: newCategory
            })
        });

        const data = await response.json();

        if (data.success) {
            // Reload the table to show updated transactions
            loadTransactions();
            closeModal();
            showNotification(`Updated ${data.updated_count} similar transactions with category: ${newCategory}`);
        } else {
            showNotification('Error updating similar transactions', 'error');
        }
    } catch (error) {
        console.error('Error applying category to similar transactions:', error);
        showNotification('Error updating similar transactions', 'error');
    }
}

async function applyToSimilar(transactionId, newDescription) {
    try {
        const response = await fetch('/api/update_similar_descriptions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                transaction_id: transactionId,
                description: newDescription
            })
        });

        const data = await response.json();

        if (data.success) {
            // Reload the table to show updated transactions
            loadTransactions();
            closeModal();
            showNotification(`Updated ${data.updated_count} similar transactions with description: ${newDescription}`);
        } else {
            showNotification('Error updating similar transactions', 'error');
        }
    } catch (error) {
        console.error('Error applying description to similar transactions:', error);
        showNotification('Error updating similar transactions', 'error');
    }
}

async function checkForSimilarTransactions(transactionId, newDescription) {
    try {
        // Show loading modal first
        const modal = document.getElementById('suggestionsModal');
        const content = document.getElementById('suggestionsContent');

        // Clear suggestionsList to use suggestionsContent
        document.getElementById('suggestionsList').innerHTML = '';

        // Show loading state
        content.innerHTML = `
            <div class="ai-suggestion-header">
                <h3>🤖 AI Suggestion</h3>
            </div>
            <div class="loading-state" style="text-align: center; padding: 40px;">
                <div style="font-size: 24px; margin-bottom: 15px;">🔍</div>
                <p>Claude is analyzing this transaction...</p>
                <div style="margin-top: 10px; color: #666; font-size: 14px;">Generating clean description suggestions</div>
            </div>
        `;

        // Show modal with loading state
        modal.style.display = 'block';

        // Get AI suggestions for clean description
        const response = await fetch(`/api/suggestions?transaction_id=${transactionId}&field_type=description&current_value=${encodeURIComponent(newDescription)}`);
        const data = await response.json();

        if (data.suggestions && data.suggestions.length > 0) {
            // Show simple list of AI-suggested descriptions with edit capability
            const modal = document.getElementById('suggestionsModal');
            const content = document.getElementById('suggestionsContent');

            // Clear suggestionsList to use suggestionsContent
            document.getElementById('suggestionsList').innerHTML = '';

            content.innerHTML = `
                <div class="ai-suggestion-header">
                    <h3>🤖 AI Suggested Descriptions</h3>
                </div>

                <div style="margin: 15px 0; padding: 10px; background: #f9f9f9; border-left: 3px solid #666; border-radius: 4px;">
                    <strong style="color: #666;">Original Description:</strong>
                    <div style="margin-top: 5px; font-size: 13px; color: #333;">${newDescription}</div>
                </div>

                <p style="margin: 15px 0;">Claude suggests these clean descriptions. Click one to select it, or edit it below:</p>

                <div class="suggestions-list" style="margin: 15px 0;">
                    ${data.suggestions.map((suggestion, index) => `
                        <div class="suggestion-item" style="padding: 12px; margin: 8px 0; background: #f5f5f5; border-radius: 6px; cursor: pointer; transition: background 0.2s; border: 2px solid transparent;"
                             onmouseover="this.style.background='#e8f4f8'"
                             onmouseout="this.style.background='#f5f5f5'"
                             onclick="selectSuggestionForEdit('${suggestion.replace(/'/g, "\\'")}')">
                            <div style="font-weight: 500;">${suggestion}</div>
                        </div>
                    `).join('')}
                </div>

                <div style="margin: 20px 0;">
                    <label style="display: block; margin-bottom: 8px; font-weight: 500;">Edit Selected Description:</label>
                    <input type="text" id="editedDescription" value="${data.suggestions[0]}"
                           style="width: 100%; padding: 10px; border: 2px solid #ddd; border-radius: 6px; font-size: 14px;"
                           placeholder="Edit the description here">
                </div>

                <div class="action-buttons">
                    <button class="btn-primary" onclick="applyDescriptionAndFindSimilar('${transactionId}')">Apply & Find Similar</button>
                    <button class="btn-secondary" onclick="closeModal()">Cancel</button>
                </div>
            `;
            showModal();
        } else {
            // No similar transactions found - just close the modal
            modal.style.display = 'none';
        }
    } catch (error) {
        console.error('Error checking similar transactions:', error);
        // Close modal on error
        const modal = document.getElementById('suggestionsModal');
        if (modal) modal.style.display = 'none';
    }
}

function selectSuggestionForEdit(suggestion) {
    // Update the input field with the selected suggestion
    const input = document.getElementById('editedDescription');
    if (input) {
        input.value = suggestion;
        input.focus();
    }

    // Visual feedback - highlight the selected item
    document.querySelectorAll('.suggestion-item').forEach(item => {
        item.style.border = '2px solid transparent';
        item.style.background = '#f5f5f5';
    });
    event.currentTarget.style.border = '2px solid #007bff';
    event.currentTarget.style.background = '#e8f4f8';
}

async function applyDescriptionAndFindSimilar(transactionId) {
    try {
        // Get the edited description
        const editedDescription = document.getElementById('editedDescription').value.trim();

        if (!editedDescription) {
            showNotification('Please enter a description', 'error');
            return;
        }

        // First, apply the description to the current transaction
        const updateResponse = await fetch('/api/update_transaction', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                transaction_id: transactionId,
                field: 'description',
                value: editedDescription
            })
        });

        if (!updateResponse.ok) {
            throw new Error('Failed to update transaction');
        }

        // Update the UI
        const cell = document.querySelector(`[data-transaction-id="${transactionId}"][data-field="description"]`);
        if (cell) {
            cell.textContent = editedDescription;
        }

        showNotification('Description updated successfully');

        // Now find and show similar transactions
        const modal = document.getElementById('suggestionsModal');
        const content = document.getElementById('suggestionsContent');

        content.innerHTML = `
            <div class="ai-suggestion-header">
                <h3>🤖 Finding Similar Transactions</h3>
            </div>
            <div class="loading-state" style="text-align: center; padding: 40px;">
                <div style="font-size: 24px; margin-bottom: 15px;">🔍</div>
                <p>Searching for similar transactions...</p>
            </div>
        `;

        // Get similar transactions
        const similarResponse = await fetch(`/api/suggestions?transaction_id=${transactionId}&field_type=similar_descriptions&value=${encodeURIComponent(editedDescription)}`);
        const similarData = await similarResponse.json();

        if (similarData.suggestions && similarData.suggestions.length > 0) {
            // Show similar transactions with checkbox selection
            content.innerHTML = `
                <div class="ai-suggestion-header">
                    <h3>🤖 Apply to Similar Transactions</h3>
                </div>

                <p>Found ${similarData.suggestions.length} similar transactions. Select which ones to update:</p>

                <div class="ai-recommendation-section">
                    <h4>🤖 Will apply this description:</h4>
                    <div class="standardized-recommendation">
                        <strong>${editedDescription}</strong>
                    </div>
                </div>

                <div class="transaction-selection">
                    <div class="select-all-container">
                        <label class="checkbox-container">
                            <input type="checkbox" id="selectAllSimilar" onchange="toggleAllSimilarTransactions()" checked>
                            <span class="checkmark"></span>
                            Select All (${similarData.suggestions.length} transactions)
                        </label>
                    </div>

                    <div class="similar-transactions-list">
                        ${similarData.suggestions.map((tx, index) => `
                            <label class="checkbox-container transaction-item">
                                <input type="checkbox" class="similar-transaction-cb" data-transaction-id="${tx.transaction_id || ''}" checked>
                                <span class="checkmark"></span>
                                <div class="transaction-details">
                                    <div class="transaction-date">${tx.date || 'N/A'}</div>
                                    <div class="transaction-description">${tx.description}</div>
                                    <div class="transaction-confidence">Confidence: ${tx.confidence || 'N/A'}</div>
                                </div>
                            </label>
                        `).join('')}
                    </div>

                    <div class="selection-counter">
                        <span id="similarSelectionCounter">Selected: ${similarData.suggestions.length} of ${similarData.suggestions.length} transactions</span>
                    </div>
                </div>

                <div class="action-buttons">
                    <button class="btn-primary" onclick="applyToSelectedSimilar('${transactionId}', '${editedDescription.replace(/'/g, "\\'")}')">Apply to Selected</button>
                    <button class="btn-secondary" onclick="closeModal()">Skip</button>
                </div>
            `;
        } else {
            // No similar transactions found
            showNotification('No similar transactions found');
            closeModal();
        }

    } catch (error) {
        console.error('Error applying description:', error);
        showNotification('Error applying description', 'error');
    }
}

function toggleAllSimilarTransactions() {
    const selectAllCheckbox = document.getElementById('selectAllSimilar');
    const transactionCheckboxes = document.querySelectorAll('.similar-transaction-cb');

    transactionCheckboxes.forEach(cb => {
        cb.checked = selectAllCheckbox.checked;
    });

    updateSimilarSelectionCounter();
}

function updateSimilarSelectionCounter() {
    const checkboxes = document.querySelectorAll('.similar-transaction-cb');
    const selectedCount = document.querySelectorAll('.similar-transaction-cb:checked').length;
    const totalCount = checkboxes.length;

    const counter = document.getElementById('similarSelectionCounter');
    if (counter) {
        counter.textContent = `Selected: ${selectedCount} of ${totalCount} transactions`;
    }

    // Update "Select All" checkbox state
    const selectAllCheckbox = document.getElementById('selectAllSimilar');
    if (selectAllCheckbox) {
        selectAllCheckbox.checked = selectedCount === totalCount;
        selectAllCheckbox.indeterminate = selectedCount > 0 && selectedCount < totalCount;
    }
}

async function updateTransactionOnly(transactionId, field, value) {
    /**
     * Simple transaction update function without UI updates
     */
    const response = await fetch('/api/update_transaction', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            transaction_id: transactionId,
            field: field,
            value: value
        })
    });

    const result = await response.json();
    if (!result.success) {
        throw new Error(result.error || 'Failed to update transaction');
    }
    return result;
}

async function applyToSelectedSimilar(originalTransactionId, newDescription) {
    try {
        const selectedCheckboxes = document.querySelectorAll('.similar-transaction-cb:checked');
        const selectedTransactionIds = Array.from(selectedCheckboxes).map(cb => cb.dataset.transactionId);

        if (selectedTransactionIds.length === 0) {
            showToast('Please select at least one transaction to update', 'warning');
            return;
        }

        // Update each selected transaction
        const updatePromises = selectedTransactionIds.map(transactionId =>
            updateTransactionOnly(transactionId, 'description', newDescription)
        );

        await Promise.all(updatePromises);

        showNotification(`Updated ${selectedTransactionIds.length} similar transactions`);
        closeModal();

        // Refresh the transaction list to show updates
        setTimeout(() => {
            loadTransactions(currentPage, itemsPerPage);
        }, 500);

    } catch (error) {
        console.error('Error applying to selected similar transactions:', error);
        showToast('Error updating selected transactions: ' + error.message, 'error');
    }
}

function showModal() {
    document.getElementById('suggestionsModal').style.display = 'block';
}

// Add event listener to update counter when individual checkboxes change
document.addEventListener('change', function(e) {
    if (e.target.classList.contains('similar-transaction-cb')) {
        updateSimilarSelectionCounter();
    }
});

function closeModal() {
    const modal = document.getElementById('suggestionsModal');
    modal.style.display = 'none';

    // CRITICAL FIX: Clean up modal state to prevent stale data from appearing on next open
    // Remove any modal-specific CSS classes
    const modalContent = modal.querySelector('.modal-content');
    if (modalContent) {
        modalContent.classList.remove('similar-transactions-modal');
    }

    // Clear modal content to prevent stale data
    const suggestionsContent = document.getElementById('suggestionsContent');
    const suggestionsList = document.getElementById('suggestionsList');
    if (suggestionsContent) {
        suggestionsContent.innerHTML = '';
    }
    if (suggestionsList) {
        suggestionsList.innerHTML = '';
    }
}

function showNotification(message, type = 'success') {
    // Simple notification using alert for now
    // Can be upgraded to a more sophisticated notification system later
    if (type === 'error') {
        alert(`Error: ${message}`);
    } else {
        alert(message);
    }
}

async function logUserInteraction(transactionId, fieldType, originalValue, userChoice, actionType) {
    try {
        // Get transaction context
        const transaction = currentTransactions.find(t => t.transaction_id === transactionId);
        if (!transaction) return;

        const context = {
            amount: transaction.amount,
            classified_entity: transaction.classified_entity,
            description: transaction.description,
            original_value: originalValue
        };

        const response = await fetch('/api/log_interaction', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                transaction_id: transactionId,
                field_type: fieldType,
                original_value: originalValue,
                user_choice: userChoice,
                action_type: actionType,
                transaction_context: context,
                session_id: `session_${Date.now()}`
            })
        });

        if (!response.ok) {
            console.error('Failed to log user interaction');
        }
    } catch (error) {
        console.error('Error logging user interaction:', error);
    }
}

function updateTableInfo(pagination) {
    const info = document.getElementById('tableInfo');

    if (pagination) {
        const start = ((pagination.page - 1) * pagination.per_page) + 1;
        const end = Math.min(pagination.page * pagination.per_page, pagination.total);
        info.textContent = `Showing ${start}-${end} of ${pagination.total} transactions`;
    } else {
        info.textContent = `Showing ${currentTransactions.length} transactions`;
    }
}

function updatePaginationControls() {
    const prevBtn = document.getElementById('prevPage');
    const nextBtn = document.getElementById('nextPage');
    const pageInfo = document.getElementById('pageInfo');

    prevBtn.disabled = currentPage <= 1;
    nextBtn.disabled = currentPage >= totalPages;
    pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
}

function viewTransactionDetails(id) {
    // Find the transaction
    const transaction = currentTransactions.find(t => t.transaction_id === id);
    if (transaction) {
        // Create a detailed view (could be a modal or new page)
        const details = Object.entries(transaction)
            .filter(([key, value]) => value != null && value !== '')
            .map(([key, value]) => `${key}: ${value}`)
            .join('\n');

        alert(`Transaction Details:\n\n${details}`);
    }
}

function quickSuggest(transactionId, fieldType) {
    // Quick AI suggestion for empty fields
    const fieldElement = document.querySelector(`[data-transaction-id="${transactionId}"][data-field="${fieldType}"]`);
    if (fieldElement) {
        showAISuggestions(fieldElement);
    }
}

function exportToCSV() {
    // Convert transactions to CSV
    const headers = [
        'Date', 'Description', 'Amount', 'Currency', 'Crypto Amount',
        'Origin', 'Destination', 'Entity', 'Accounting Category',
        'Justification', 'Confidence', 'Source File'
    ];

    const csvContent = [
        headers.join(','),
        ...currentTransactions.map(t => [
            t.date || '',
            `"${(t.description || '').replace(/"/g, '""')}"`,
            t.amount || 0,
            t.currency || 'USD',
            t.crypto_amount || '',
            `"${(t.origin || '').replace(/"/g, '""')}"`,
            `"${(t.destination || '').replace(/"/g, '""')}"`,
            `"${(t.classified_entity || '').replace(/"/g, '""')}"`,
            `"${(t.accounting_category || '').replace(/"/g, '""')}"`,
            `"${(t.justification || '').replace(/"/g, '""')}"`,
            t.confidence || 0,
            t.source_file || ''
        ].join(','))
    ].join('\n');

    // Download file
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transactions_export_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);

    showToast('Transactions exported successfully', 'success');
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;

    container.appendChild(toast);

    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 100);

    // Remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => container.removeChild(toast), 300);
    }, 3000);
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
let currentSortField = 'date';
let currentSortDirection = 'desc';

function sortTransactions(field) {
    if (field === currentSortField) {
        currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
    } else {
        currentSortField = field;
        currentSortDirection = 'asc';
    }

    currentTransactions.sort((a, b) => {
        let aVal = a[field];
        let bVal = b[field];

        // Handle nulls
        if (aVal === null || aVal === undefined) return 1;
        if (bVal === null || bVal === undefined) return -1;

        // Compare
        if (typeof aVal === 'number') {
            return currentSortDirection === 'asc' ? aVal - bVal : bVal - aVal;
        } else {
            const comparison = String(aVal).localeCompare(String(bVal));
            return currentSortDirection === 'asc' ? comparison : -comparison;
        }
    });

    renderTransactionTable(currentTransactions);
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US');
    } catch {
        return dateString;
    }
}

// Archive functionality
let showingArchived = false;

function updateArchiveButtonVisibility() {
    const selectedCount = document.querySelectorAll('.transaction-select-cb:checked').length;
    const archiveBtn = document.getElementById('archiveSelected');
    if (archiveBtn) {
        archiveBtn.style.display = selectedCount > 0 ? 'inline-block' : 'none';
    }
}

async function archiveSelectedTransactions() {
    console.log('🔵 archiveSelectedTransactions() called!');

    const selectedCheckboxes = document.querySelectorAll('.transaction-select-cb:checked');
    console.log('🔵 Found checkboxes:', selectedCheckboxes.length);

    const transactionIds = Array.from(selectedCheckboxes).map(cb => cb.dataset.transactionId);
    console.log('🔵 Transaction IDs:', transactionIds);

    if (transactionIds.length === 0) {
        console.log('🔴 No transactions selected, returning');
        return;
    }

    console.log('🔵 About to show confirmation dialog');
    if (!confirm(`Archive ${transactionIds.length} selected transaction(s)?`)) {
        console.log('🔴 User cancelled confirmation dialog');
        return;
    }

    console.log('🔵 User confirmed, making API call');

    try {
        const response = await fetch('/api/archive_transactions', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({transaction_ids: transactionIds})
        });

        console.log('🔵 API response status:', response.status);
        const data = await response.json();
        console.log('🔵 API response data:', data);

        if (data.success) {
            showToast(`Archived ${data.archived_count} transactions`, 'success');
            // Uncheck "Select All" checkbox (if it exists)
            const selectAllCheckbox = document.getElementById('selectAll');
            if (selectAllCheckbox) {
                selectAllCheckbox.checked = false;
            }
            loadTransactions();
        } else {
            showToast('Error archiving transactions: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('🔴 Error archiving transactions:', error);
        showToast('Error archiving transactions: ' + error.message, 'error');
    }
}

async function archiveTransaction(transactionId) {
    if (!confirm('Archive this transaction?')) return;

    try {
        const response = await fetch('/api/archive_transactions', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({transaction_ids: [transactionId]})
        });

        const data = await response.json();
        if (data.success) {
            showToast('Transaction archived successfully', 'success');
            loadTransactions();
        } else {
            showToast('Error archiving transaction: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        showToast('Error archiving transaction: ' + error.message, 'error');
    }
}

function toggleArchivedView() {
    showingArchived = !showingArchived;
    const button = document.getElementById('showArchived');
    button.textContent = showingArchived ? '📦 Hide Archived' : '📦 Show Archived';
    currentPage = 1;
    loadTransactions();
}

// =============================================================================
// AI SMART SUGGESTIONS - NEW DYNAMIC CONFIDENCE REASSESSMENT SYSTEM
// =============================================================================

/**
 * Get AI-powered suggestions for improving a transaction's classification
 * This is the main entry point called by the "🤖 AI" button
 */
async function getAISmartSuggestions(transactionId, transaction) {
    try {
        // Show modal immediately with loading state
        showModal();

        // Hide any previous error/empty states - with null checks
        const errorDiv = document.getElementById('suggestionsError');
        const emptyDiv = document.getElementById('suggestionsEmpty');
        const assessmentDiv = document.getElementById('suggestionAssessment');

        if (errorDiv) errorDiv.style.display = 'none';
        if (emptyDiv) emptyDiv.style.display = 'none';
        if (assessmentDiv) assessmentDiv.style.display = 'none';

        // Clear previous suggestions
        const suggestionsList = document.getElementById('suggestionsList');
        if (suggestionsList) {
            suggestionsList.innerHTML = '<div class="loading">🤖 AI is analyzing this transaction...</div>';
        }

        // Populate transaction info - with null checks
        const descEl = document.getElementById('suggestionDescription');
        const amountEl = document.getElementById('suggestionAmount');
        const confEl = document.getElementById('suggestionCurrentConfidence');

        if (descEl) descEl.textContent = transaction.description || 'N/A';
        if (amountEl) amountEl.textContent = formatCurrency(transaction.amount);
        if (confEl) confEl.textContent = transaction.confidence ? (transaction.confidence * 100).toFixed(0) + '%' : 'N/A';

        // Call the AI suggestions API
        const response = await fetch(`/api/ai/get-suggestions?transaction_id=${transactionId}`);
        const data = await response.json();

        if (data.error) {
            // Show error state
            if (errorDiv) errorDiv.style.display = 'block';
            const errorMsgEl = document.getElementById('suggestionsErrorMessage');
            if (errorMsgEl) errorMsgEl.textContent = data.error;
            if (suggestionsList) suggestionsList.innerHTML = '';
            return;
        }

        // Check if transaction doesn't need reassessment
        if (data.message && (!data.suggestions || data.suggestions.length === 0)) {
            // CRITICAL FIX: Only show "No improvements needed" if confidence is actually high
            // For low confidence transactions without suggestions, show a different message
            const currentConfidence = transaction.confidence || 0;

            if (currentConfidence >= 0.8) {
                // High confidence - truly no improvements needed
                if (emptyDiv) emptyDiv.style.display = 'block';
                if (suggestionsList) suggestionsList.innerHTML = '';
            } else {
                // Low confidence but no suggestions - show error instead
                if (errorDiv) errorDiv.style.display = 'block';
                const errorMsgEl = document.getElementById('suggestionsErrorMessage');
                if (errorMsgEl) {
                    errorMsgEl.textContent = `AI could not generate suggestions. Current confidence: ${(currentConfidence * 100).toFixed(0)}%. Try editing the fields manually or contact support.`;
                }
                if (suggestionsList) suggestionsList.innerHTML = '';
            }
            return;
        }

        // Show AI assessment section
        if (data.reasoning && assessmentDiv) {
            assessmentDiv.style.display = 'block';
            const reasoningEl = document.getElementById('suggestionReasoning');
            const newConfEl = document.getElementById('suggestionNewConfidence');
            const contextEl = document.getElementById('suggestionContext');

            if (reasoningEl) reasoningEl.textContent = data.reasoning;
            if (newConfEl) newConfEl.textContent = (data.new_confidence * 100).toFixed(0) + '%';

            const contextText = `Based on ${data.similar_count || 0} similar transactions and ${data.patterns_count || 0} learned patterns`;
            if (contextEl) contextEl.textContent = contextText;
        }

        // Render suggestions with checkboxes for multi-select
        if (data.suggestions && data.suggestions.length > 0) {
            // Add selection controls header
            const selectionHeader = `
                <div style="padding: 10px; margin-bottom: 15px; background: #f0f0f0; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <button onclick="selectAllAISuggestions(true)" class="btn-secondary btn-sm" style="margin-right: 8px;">
                            ☑ Select All
                        </button>
                        <button onclick="selectAllAISuggestions(false)" class="btn-secondary btn-sm">
                            ☐ Deselect All
                        </button>
                    </div>
                    <div style="color: #666; font-size: 0.9em;">
                        <span id="aiSuggestionSelectedCount">0</span> of ${data.suggestions.length} selected
                    </div>
                </div>
            `;

            const suggestionsHTML = data.suggestions.map((suggestion, index) => {
                const fieldLabel = {
                    'classified_entity': 'Business Entity',
                    'accounting_category': 'Accounting Category',
                    'justification': 'Justification'
                }[suggestion.field] || suggestion.field;

                // Determine if this field should use a dropdown or text input
                let inputHTML = '';
                if (suggestion.field === 'classified_entity') {
                    // Use dropdown for Entity
                    const entityOptions = [
                        'Delta LLC',
                        'Delta Prop Shop LLC',
                        'Infinity Validator',
                        'Delta Mining Paraguay S.A.',
                        'Delta Brazil Operations',
                        'Internal Transfer',
                        'Personal'
                    ];
                    inputHTML = `
                        <select class="ai-suggestion-value-input"
                                id="ai-suggestion-value-${index}"
                                data-index="${index}"
                                style="width: 100%; padding: 8px; border: 1px solid #0066cc; border-radius: 4px; font-weight: 500; font-size: 14px; background: white;">
                            ${entityOptions.map(entity =>
                                `<option value="${entity}" ${entity === suggestion.suggested_value ? 'selected' : ''}>${entity}</option>`
                            ).join('')}
                        </select>
                    `;
                } else if (suggestion.field === 'accounting_category') {
                    // Use dropdown for Category (will be populated dynamically)
                    inputHTML = `
                        <select class="ai-suggestion-value-input ai-suggestion-category-dropdown"
                                id="ai-suggestion-value-${index}"
                                data-index="${index}"
                                data-suggested-value="${suggestion.suggested_value}"
                                style="width: 100%; padding: 8px; border: 1px solid #0066cc; border-radius: 4px; font-weight: 500; font-size: 14px; background: white;">
                            <option value="">Loading categories...</option>
                        </select>
                    `;
                } else {
                    // Use text input for Justification
                    inputHTML = `
                        <input type="text"
                               class="ai-suggestion-value-input"
                               id="ai-suggestion-value-${index}"
                               value="${suggestion.suggested_value}"
                               data-index="${index}"
                               style="width: 100%; padding: 8px; border: 1px solid #0066cc; border-radius: 4px; font-weight: 500; font-size: 14px; background: white;"
                               placeholder="Edit AI suggestion...">
                    `;
                }

                return `
                    <div class="ai-suggestion-item" style="padding: 15px; margin: 10px 0; border: 1px solid #ddd; border-radius: 6px; background: #f9f9f9; display: flex; gap: 15px;">
                        <div style="display: flex; align-items: flex-start; padding-top: 5px;">
                            <input type="checkbox"
                                   class="ai-suggestion-checkbox"
                                   id="ai-suggestion-cb-${index}"
                                   data-index="${index}"
                                   onchange="updateAISuggestionSelectionCount()"
                                   style="width: 18px; height: 18px; cursor: pointer;">
                        </div>
                        <div style="flex: 1;">
                            <div style="margin-bottom: 8px;">
                                <strong style="color: #0066cc;">${fieldLabel}</strong>
                            </div>
                            <div style="margin: 8px 0; padding: 8px; background: #fff; border-radius: 4px;">
                                <div style="font-size: 0.85em; color: #666;">Current:</div>
                                <div style="margin: 4px 0;">${suggestion.current_value || 'N/A'}</div>
                            </div>
                            <div style="margin: 8px 0; padding: 8px; background: #e8f4f8; border-radius: 4px; border-left: 3px solid #0066cc;">
                                <div style="font-size: 0.85em; color: #0066cc; margin-bottom: 6px;">AI Suggests ${suggestion.field === 'justification' ? '(editable)' : '(select from dropdown)'}:</div>
                                ${inputHTML}
                            </div>
                            <div style="margin: 8px 0; color: #666; font-size: 0.9em; font-style: italic;">
                                "${suggestion.reasoning}"
                            </div>
                            <div style="margin-top: 12px;">
                                <span style="color: #666; font-size: 0.9em;">
                                    AI Confidence: <strong>${(suggestion.confidence * 100).toFixed(0)}%</strong>
                                </span>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

            // Add Apply Selected button at the bottom
            const applyButton = `
                <div style="margin-top: 20px; padding: 15px; background: #f0f0f0; border-radius: 6px; text-align: right;">
                    <button id="applySelectedSuggestionsBtn"
                            onclick="applySelectedAISuggestions('${transactionId}')"
                            class="btn-primary"
                            style="padding: 10px 20px;"
                            disabled>
                        Apply Selected Suggestions (<span id="applyBtnCount">0</span>)
                    </button>
                </div>
            `;

            document.getElementById('suggestionsList').innerHTML = selectionHeader + suggestionsHTML + applyButton;

            // Store suggestions in a global variable for easy access when applying
            window.currentAISuggestions = {
                transactionId: transactionId,
                suggestions: data.suggestions
            };

            // Initialize selection count
            updateAISuggestionSelectionCount();

            // Populate accounting category dropdowns
            const categoryDropdowns = document.querySelectorAll('.ai-suggestion-category-dropdown');
            if (categoryDropdowns.length > 0) {
                // Fetch categories and populate dropdowns
                fetch('/api/accounting_categories')
                    .then(response => response.json())
                    .then(data => {
                        const categories = data.categories || [];
                        categoryDropdowns.forEach(dropdown => {
                            const suggestedValue = dropdown.getAttribute('data-suggested-value');
                            dropdown.innerHTML = categories.map(cat =>
                                `<option value="${cat}" ${cat === suggestedValue ? 'selected' : ''}>${cat}</option>`
                            ).join('');
                        });
                    })
                    .catch(error => {
                        console.error('Failed to fetch accounting categories:', error);
                        // Fallback to default categories
                        const fallbackCategories = [
                            'Revenue - Trading',
                            'Revenue - Mining',
                            'Revenue - Challenge',
                            'Interest Income',
                            'Cost of Goods Sold (COGS)',
                            'Technology Expense',
                            'General and Administrative',
                            'Bank Fees',
                            'Internal Transfer'
                        ];
                        categoryDropdowns.forEach(dropdown => {
                            const suggestedValue = dropdown.getAttribute('data-suggested-value');
                            dropdown.innerHTML = fallbackCategories.map(cat =>
                                `<option value="${cat}" ${cat === suggestedValue ? 'selected' : ''}>${cat}</option>`
                            ).join('');
                        });
                    });
            }
        } else {
            document.getElementById('suggestionsList').innerHTML =
                '<div style="padding: 20px; text-align: center; color: #666;">No specific suggestions available</div>';
        }

    } catch (error) {
        console.error('Error getting AI suggestions:', error);
        const errorDiv = document.getElementById('suggestionsError');
        const errorMsgEl = document.getElementById('suggestionsErrorMessage');
        const suggestionsList = document.getElementById('suggestionsList');

        if (errorDiv) errorDiv.style.display = 'block';
        if (errorMsgEl) errorMsgEl.textContent = 'Failed to load AI suggestions: ' + error.message;
        if (suggestionsList) suggestionsList.innerHTML = '';
    }
}

/**
 * Apply a specific AI suggestion to the transaction
 */
async function applyAISuggestion(transactionId, suggestionIndex) {
    try {
        // Get the suggestion from the stored data
        if (!window.currentAISuggestions || window.currentAISuggestions.transactionId !== transactionId) {
            showToast('Error: Suggestion data not found', 'error');
            return;
        }

        const suggestion = window.currentAISuggestions.suggestions[suggestionIndex];
        if (!suggestion) {
            showToast('Error: Invalid suggestion index', 'error');
            return;
        }

        // Show loading state on the button
        const buttons = document.querySelectorAll('.ai-suggestion-item button');
        if (buttons[suggestionIndex]) {
            buttons[suggestionIndex].disabled = true;
            buttons[suggestionIndex].textContent = 'Applying...';
        }

        // Call the API to apply the suggestion
        const response = await fetch('/api/ai/apply-suggestion', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                transaction_id: transactionId,
                suggestion: suggestion
            })
        });

        const data = await response.json();

        if (data.success) {
            showToast('✅ AI suggestion applied successfully!', 'success');

            // IMPORTANT: Now look for similar transactions that could benefit from the same change
            await findSimilarTransactionsAfterAISuggestion(transactionId, suggestion);

            // Clean up stored suggestions
            delete window.currentAISuggestions;
        } else {
            showToast('Error applying suggestion: ' + (data.error || 'Unknown error'), 'error');

            // Re-enable the button
            if (buttons[suggestionIndex]) {
                buttons[suggestionIndex].disabled = false;
                buttons[suggestionIndex].textContent = 'Apply This Suggestion';
            }
        }

    } catch (error) {
        console.error('Error applying AI suggestion:', error);
        showToast('Error applying suggestion: ' + error.message, 'error');
    }
}

/**
 * Select or deselect all AI suggestions
 */
function selectAllAISuggestions(selectAll) {
    const checkboxes = document.querySelectorAll('.ai-suggestion-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAll;
    });
    updateAISuggestionSelectionCount();
}

/**
 * Update the selection count and enable/disable the Apply button
 */
function updateAISuggestionSelectionCount() {
    const checkboxes = document.querySelectorAll('.ai-suggestion-checkbox');
    const checkedBoxes = document.querySelectorAll('.ai-suggestion-checkbox:checked');
    const countElement = document.getElementById('aiSuggestionSelectedCount');
    const applyBtn = document.getElementById('applySelectedSuggestionsBtn');
    const applyBtnCount = document.getElementById('applyBtnCount');

    // Update count display
    if (countElement) {
        countElement.textContent = checkedBoxes.length;
    }

    // Update button count
    if (applyBtnCount) {
        applyBtnCount.textContent = checkedBoxes.length;
    }

    // Enable/disable the Apply button
    if (applyBtn) {
        applyBtn.disabled = checkedBoxes.length === 0;
        applyBtn.style.opacity = checkedBoxes.length === 0 ? '0.6' : '1';
        applyBtn.style.cursor = checkedBoxes.length === 0 ? 'not-allowed' : 'pointer';
    }
}

/**
 * Apply all selected AI suggestions to the transaction
 */
async function applySelectedAISuggestions(transactionId) {
    try {
        // Get all selected checkboxes
        const checkedBoxes = document.querySelectorAll('.ai-suggestion-checkbox:checked');

        if (checkedBoxes.length === 0) {
            showToast('Please select at least one suggestion to apply', 'warning');
            return;
        }

        // Get the selected suggestions with EDITED values from input fields
        const selectedSuggestions = [];
        checkedBoxes.forEach(checkbox => {
            const index = parseInt(checkbox.dataset.index);
            if (window.currentAISuggestions && window.currentAISuggestions.suggestions[index]) {
                // Clone the suggestion object
                const suggestion = {...window.currentAISuggestions.suggestions[index]};

                // Get the edited value from the input field
                const inputField = document.getElementById(`ai-suggestion-value-${index}`);
                if (inputField) {
                    suggestion.suggested_value = inputField.value.trim();
                }

                selectedSuggestions.push(suggestion);
            }
        });

        if (selectedSuggestions.length === 0) {
            showToast('Error: No valid suggestions selected', 'error');
            return;
        }

        // Show confirmation
        const fieldsList = selectedSuggestions.map(s => {
            const fieldLabel = {
                'classified_entity': 'Business Entity',
                'accounting_category': 'Accounting Category',
                'justification': 'Justification'
            }[s.field] || s.field;
            return `• ${fieldLabel}: "${s.suggested_value}"`;
        }).join('\n');

        const confirmMsg = `Apply ${selectedSuggestions.length} AI suggestion(s)?\n\n${fieldsList}`;
        if (!confirm(confirmMsg)) {
            return;
        }

        // Disable the apply button
        const applyBtn = document.getElementById('applySelectedSuggestionsBtn');
        if (applyBtn) {
            applyBtn.disabled = true;
            applyBtn.textContent = 'Applying...';
        }

        // Apply each suggestion sequentially and track ALL successful ones
        let successCount = 0;
        let appliedSuggestions = [];  // Track ALL successfully applied suggestions

        for (const suggestion of selectedSuggestions) {
            try {
                const response = await fetch('/api/ai/apply-suggestion', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        transaction_id: transactionId,
                        suggestion: suggestion
                    })
                });

                const data = await response.json();

                if (data.success) {
                    successCount++;
                    appliedSuggestions.push(suggestion);  // Add to list of applied suggestions
                } else {
                    console.error(`Failed to apply suggestion for ${suggestion.field}:`, data.error);
                }
            } catch (error) {
                console.error(`Error applying suggestion for ${suggestion.field}:`, error);
            }
        }

        if (successCount > 0) {
            showToast(`✅ Successfully applied ${successCount} of ${selectedSuggestions.length} suggestion(s)!`, 'success');

            // If at least one suggestion was applied, look for similar transactions
            // Pass ALL successfully applied suggestions for comprehensive similarity search
            if (appliedSuggestions.length > 0) {
                await findSimilarTransactionsAfterAISuggestion(transactionId, appliedSuggestions);
            } else {
                // No similar transaction search, just refresh
                closeModal();
                loadTransactions();
            }

            // Clean up stored suggestions
            delete window.currentAISuggestions;
        } else {
            showToast('Error: Failed to apply any suggestions', 'error');
            if (applyBtn) {
                applyBtn.disabled = false;
                applyBtn.textContent = `Apply Selected Suggestions (${selectedSuggestions.length})`;
            }
        }

    } catch (error) {
        console.error('Error applying selected AI suggestions:', error);
        showToast('Error applying suggestions: ' + error.message, 'error');
    }
}

/**
 * Find similar transactions after applying AI suggestions
 * Uses Claude AI to find other transactions that could benefit from the same changes
 * Supports multiple applied suggestions (e.g., entity + category + justification)
 */
async function findSimilarTransactionsAfterAISuggestion(transactionId, appliedSuggestions) {
    try {
        // Support both single suggestion (legacy) and array of suggestions
        if (!Array.isArray(appliedSuggestions)) {
            appliedSuggestions = [appliedSuggestions];
        }

        console.log(`🔍 Looking for similar transactions after applying ${appliedSuggestions.length} suggestion(s)...`);

        // Show loading modal
        const modal = document.getElementById('suggestionsModal');
        const content = document.getElementById('suggestionsContent');
        const suggestionsList = document.getElementById('suggestionsList');

        // Clear previous content
        if (suggestionsList) suggestionsList.innerHTML = '';

        // Create a friendly list of what was applied
        const appliedFieldsList = appliedSuggestions.map(s => {
            const fieldLabel = {
                'classified_entity': 'Business Entity',
                'accounting_category': 'Accounting Category',
                'justification': 'Justification'
            }[s.field] || s.field;
            return `${fieldLabel}: "${s.suggested_value}"`;
        }).join(', ');

        content.innerHTML = `
            <div class="modal-header">
                <h3>🤖 Finding Similar Transactions</h3>
            </div>
            <div class="loading-state" style="text-align: center; padding: 40px;">
                <div style="font-size: 24px; margin-bottom: 15px;">🔍</div>
                <p>Claude AI is analyzing for similar transactions...</p>
                <div style="margin-top: 10px; color: #666; font-size: 14px;">
                    Will apply: ${appliedFieldsList}
                </div>
            </div>
        `;

        showModal();

        // Call the API endpoint with ALL applied suggestions
        const response = await fetch('/api/ai/find-similar-after-suggestion', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                transaction_id: transactionId,
                applied_suggestions: appliedSuggestions  // Send all suggestions
            })
        });

        const data = await response.json();

        if (data.error) {
            console.log('❌ Error finding similar transactions:', data.error);
            closeModal();
            loadTransactions();
            return;
        }

        if (!data.similar_transactions || data.similar_transactions.length === 0) {
            console.log('ℹ️ No similar transactions found');
            closeModal();
            loadTransactions();
            return;
        }

        // Show similar transactions modal with selection UI
        const similarTxs = data.similar_transactions;
        const appliedFields = data.applied_fields || {};  // All fields that will be applied

        // Store applied fields globally for use in applyAISuggestionToSelected
        window.currentAppliedFields = appliedFields;

        // Create friendly labels for all fields being applied
        const fieldLabelMap = {
            'classified_entity': 'Business Entity',
            'accounting_category': 'Accounting Category',
            'justification': 'Justification'
        };

        // Build list of changes that will be applied
        const changesHTML = Object.keys(appliedFields).map(field => {
            const label = fieldLabelMap[field] || field;
            const value = appliedFields[field];
            return `<li><strong>${label}:</strong> "${value}"</li>`;
        }).join('');

        // Format transaction date helper
        const formatTxDate = (dateStr) => {
            if (!dateStr) return '';
            const date = new Date(dateStr);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        };

        // Format amount helper
        const formatTxAmount = (amount) => {
            const val = parseFloat(amount || 0);
            return `<span class="transaction-amount ${val >= 0 ? 'positive' : 'negative'}">
                ${val >= 0 ? '+' : ''}$${Math.abs(val).toFixed(2)}
            </span>`;
        };

        content.innerHTML = `
            <div class="modal-header">
                <h3>🤖 Apply AI Suggestions to Similar Transactions</h3>
                <span class="close" onclick="closeModalAndRefresh()">&times;</span>
            </div>

            <div class="similar-selection-header">
                <div class="selection-controls">
                    <button onclick="selectAllAISimilar(true)">☑ Select All</button>
                    <button onclick="selectAllAISimilar(false)">☐ Deselect All</button>
                </div>
                <div class="selection-counter">
                    <span id="aiSimilarSelectedCount">0</span> of ${similarTxs.length} selected
                </div>
            </div>

            <div class="modal-body">
                <div class="update-preview">
                    <h4>📋 AI Suggestions Application</h4>
                    <p><strong>Changes to Apply:</strong></p>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        ${changesHTML}
                    </ul>
                    <p><strong>AI Found:</strong> ${similarTxs.length} similar transaction(s)</p>
                    <p><strong>Impact:</strong> <span id="aiSimilarImpactSummary">Select transactions below</span></p>
                    <div class="matching-info">
                        <small>✨ AI-powered: Claude analyzed transaction patterns across ${Object.keys(appliedFields).length} field(s) to find similar cases</small>
                    </div>
                </div>

                <div class="transactions-list">
                    ${similarTxs.map((t, index) => `
                        <div class="transaction-item" data-tx-id="${t.transaction_id}">
                            <input type="checkbox"
                                   class="transaction-checkbox ai-similar-tx-cb"
                                   id="ai-similar-cb-${index}"
                                   data-amount="${t.amount || 0}"
                                   onchange="updateAISimilarSelectionSummary()">
                            <div class="transaction-details">
                                <div class="transaction-info">
                                    <div class="transaction-date">${formatTxDate(t.date)}</div>
                                    <div class="transaction-description" title="${t.description}">
                                        ${t.description}
                                    </div>
                                    <div class="transaction-meta">
                                        ${Object.keys(appliedFields).map(field => {
                                            const label = fieldLabelMap[field] || field;
                                            return `<span>Current ${label}: ${t[field] || 'N/A'}</span>`;
                                        }).join(' <span>•</span> ')}
                                        <span>•</span>
                                        <span>Confidence: ${Math.round((t.confidence || 0) * 100)}%</span>
                                    </div>
                                </div>
                                ${formatTxAmount(t.amount)}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>

            <div class="modal-actions">
                <button class="btn-secondary" onclick="closeModalAndRefresh()">Cancel</button>
                <button class="btn-secondary" onclick="closeModalAndRefresh()">Skip These</button>
                <button class="btn-primary" id="updateAISimilarBtn" onclick="applyMultipleFieldsToSelected()">
                    Apply to Selected Transactions
                </button>
            </div>
        `;

        // Initialize selection - disable button initially
        updateAISimilarSelectionSummary();

    } catch (error) {
        console.error('Error finding similar transactions after AI suggestion:', error);
        closeModal();
        loadTransactions();
    }
}

// Helper function to select all/deselect all for AI similar transactions modal
function selectAllAISimilar(selectAll) {
    const checkboxes = document.querySelectorAll('.ai-similar-tx-cb');
    checkboxes.forEach(checkbox => {
        checkbox.checked = selectAll;
    });
    updateAISimilarSelectionSummary();
}

// Helper function to update selection summary for AI similar transactions modal
function updateAISimilarSelectionSummary() {
    const checkboxes = document.querySelectorAll('.ai-similar-tx-cb');
    const checkedBoxes = document.querySelectorAll('.ai-similar-tx-cb:checked');
    const updateBtn = document.getElementById('updateAISimilarBtn');
    const selectionCounter = document.getElementById('aiSimilarSelectedCount');
    const impactSummary = document.getElementById('aiSimilarImpactSummary');

    // Update selection counter
    if (selectionCounter) {
        selectionCounter.textContent = checkedBoxes.length;
    }

    // Update impact summary
    if (impactSummary) {
        if (checkedBoxes.length === 0) {
            impactSummary.textContent = 'Select transactions below';
        } else {
            let totalAmount = 0;
            checkedBoxes.forEach(cb => {
                const amount = parseFloat(cb.getAttribute('data-amount') || 0);
                totalAmount += amount;
            });
            impactSummary.innerHTML = `${checkedBoxes.length} transaction(s), Total: <strong>$${Math.abs(totalAmount).toFixed(2)}</strong>`;
        }
    }

    // Enable/disable update button
    if (updateBtn) {
        updateBtn.disabled = checkedBoxes.length === 0;
        updateBtn.style.opacity = checkedBoxes.length === 0 ? '0.6' : '1';
        updateBtn.style.cursor = checkedBoxes.length === 0 ? 'not-allowed' : 'pointer';
    }
}

// Helper function to apply AI suggestion to selected similar transactions
async function applyAISuggestionToSelected(field, newValue) {
    const checkedBoxes = document.querySelectorAll('.ai-similar-tx-cb:checked');
    const transactionIds = [];

    checkedBoxes.forEach(checkbox => {
        const transactionItem = checkbox.closest('.transaction-item');
        if (transactionItem) {
            const transactionId = transactionItem.getAttribute('data-tx-id');
            if (transactionId) {
                transactionIds.push(transactionId);
            }
        }
    });

    if (transactionIds.length === 0) {
        alert('Please select at least one transaction to update.');
        return;
    }

    // Show confirmation dialog
    const fieldLabel = {
        'classified_entity': 'entity',
        'accounting_category': 'accounting category',
        'justification': 'justification'
    }[field] || field;

    const confirmMsg = `Apply the AI suggestion to ${transactionIds.length} transaction(s)?\n\nThis will update the ${fieldLabel} to: "${newValue}"`;
    if (!confirm(confirmMsg)) return;

    try {
        // Make API call to update selected transactions in bulk
        const endpointMap = {
            'classified_entity': '/api/update_entity_bulk',
            'accounting_category': '/api/update_category_bulk'
        };

        const endpoint = endpointMap[field];
        if (!endpoint) {
            // Fallback: update one by one
            for (const txId of transactionIds) {
                await fetch('/api/update_transaction', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        transaction_id: txId,
                        field: field,
                        value: newValue
                    })
                });
            }

            showToast(`Successfully updated ${transactionIds.length} transaction(s) with AI suggestion!`, 'success');
            closeModal();
            loadTransactions();
            return;
        }

        // Use bulk endpoint if available
        const payload = field === 'classified_entity'
            ? { transaction_ids: transactionIds, new_entity: newValue }
            : { transaction_ids: transactionIds, new_category: newValue };

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        if (data.success) {
            showToast(`Successfully applied AI suggestion to ${transactionIds.length} transaction(s)!`, 'success');
            closeModal();
            loadTransactions();
        } else {
            showToast('Error updating transactions: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Error applying AI suggestion to selected transactions. Please try again.', 'error');
    }
}

// Helper function to apply MULTIPLE AI suggestion fields to selected similar transactions
async function applyMultipleFieldsToSelected() {
    const checkedBoxes = document.querySelectorAll('.ai-similar-tx-cb:checked');
    const transactionIds = [];

    checkedBoxes.forEach(checkbox => {
        const transactionItem = checkbox.closest('.transaction-item');
        if (transactionItem) {
            const transactionId = transactionItem.getAttribute('data-tx-id');
            if (transactionId) {
                transactionIds.push(transactionId);
            }
        }
    });

    if (transactionIds.length === 0) {
        alert('Please select at least one transaction to update.');
        return;
    }

    // Get the fields to apply from window.currentAppliedFields
    const appliedFields = window.currentAppliedFields || {};
    const fieldKeys = Object.keys(appliedFields);

    if (fieldKeys.length === 0) {
        alert('No fields to apply. Please try again.');
        return;
    }

    // Build confirmation message showing ALL fields that will be applied
    const fieldLabels = {
        'classified_entity': 'Entity',
        'accounting_category': 'Accounting Category',
        'justification': 'Justification'
    };

    const fieldsList = fieldKeys.map(field => {
        const label = fieldLabels[field] || field;
        const value = appliedFields[field];
        return `  • ${label}: "${value}"`;
    }).join('\n');

    const confirmMsg = `Apply AI suggestions to ${transactionIds.length} transaction(s)?\n\nThe following fields will be updated:\n${fieldsList}`;
    if (!confirm(confirmMsg)) return;

    try {
        let successCount = 0;
        let errorMessages = [];

        // Process each field
        for (const field of fieldKeys) {
            const newValue = appliedFields[field];

            // Determine which endpoint to use
            const endpointMap = {
                'classified_entity': '/api/update_entity_bulk',
                'accounting_category': '/api/update_category_bulk'
            };

            const endpoint = endpointMap[field];

            if (endpoint) {
                // Use bulk endpoint for entity and category
                const payload = field === 'classified_entity'
                    ? { transaction_ids: transactionIds, new_entity: newValue }
                    : { transaction_ids: transactionIds, new_category: newValue };

                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });

                const data = await response.json();
                if (data.success) {
                    successCount++;
                } else {
                    errorMessages.push(`${field}: ${data.error || 'Unknown error'}`);
                }
            } else {
                // Fallback: update one by one for justification and other fields
                let fieldSuccessCount = 0;
                for (const txId of transactionIds) {
                    const response = await fetch('/api/update_transaction', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            transaction_id: txId,
                            field: field,
                            value: newValue
                        })
                    });

                    const data = await response.json();
                    if (data.success) {
                        fieldSuccessCount++;
                    }
                }

                if (fieldSuccessCount === transactionIds.length) {
                    successCount++;
                } else {
                    errorMessages.push(`${field}: Only ${fieldSuccessCount}/${transactionIds.length} updated`);
                }
            }
        }

        // Show results
        if (successCount === fieldKeys.length) {
            showToast(`Successfully applied ${fieldKeys.length} AI suggestion(s) to ${transactionIds.length} transaction(s)!`, 'success');
            closeModal();
            loadTransactions();
        } else if (successCount > 0) {
            showToast(`Partially successful: ${successCount}/${fieldKeys.length} fields updated. Errors: ${errorMessages.join(', ')}`, 'warning');
            closeModal();
            loadTransactions();
        } else {
            showToast(`Failed to update transactions. Errors: ${errorMessages.join(', ')}`, 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Error applying AI suggestions to selected transactions. Please try again.', 'error');
    }
}

// Helper function to close modal and refresh transactions
function closeModalAndRefresh() {
    closeModal();
    loadTransactions();
}

/**
 * Show AI Accounting Assistant Modal
 * Helps users categorize expenses by asking natural language questions
 */
async function showAIAccountingAssistant(transactionId, transactionContext, targetField) {
    const modal = document.getElementById('suggestionsModal');
    const modalContent = modal.querySelector('.modal-content .modal-body');

    // Build modal content
    modalContent.innerHTML = `
        <div style="padding: 20px;">
            <h3 style="margin-bottom: 15px;">🤖 AI Accounting Assistant</h3>

            <div style="background: #f5f5f5; padding: 15px; border-radius: 6px; margin-bottom: 20px;">
                <p style="margin: 5px 0;"><strong>Transaction:</strong> ${transactionContext.description || 'N/A'}</p>
                <p style="margin: 5px 0;"><strong>Amount:</strong> ${transactionContext.amount || 'N/A'}</p>
                <p style="margin: 5px 0;"><strong>Entity:</strong> ${transactionContext.entity || 'N/A'}</p>
            </div>

            <div style="margin-bottom: 20px;">
                <label style="display: block; margin-bottom: 8px; font-weight: 500;">
                    Ask a question about how to categorize this expense:
                </label>
                <textarea
                    id="aiQuestionInput"
                    placeholder="Example: What category should I use for cloud hosting fees?"
                    style="width: 100%; min-height: 80px; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px;"
                ></textarea>
                <p style="margin-top: 8px; font-size: 0.9em; color: #666;">
                    💡 Tip: Be specific about the expense type for better suggestions
                </p>
            </div>

            <div id="aiAssistantResult" style="display: none; margin-top: 20px;">
                <!-- AI response will appear here -->
            </div>

            <div style="display: flex; gap: 10px; justify-content: flex-end; margin-top: 20px;">
                <button onclick="closeModal()" class="btn-secondary">Cancel</button>
                <button onclick="askAIAccountingQuestion('${transactionId}', '${targetField?.dataset?.transactionId || ''}', '${targetField?.dataset?.field || ''}')"
                        class="btn-primary"
                        id="askAIBtn">
                    Ask AI
                </button>
            </div>
        </div>
    `;

    // Show modal
    modal.style.display = 'flex';

    // Focus on textarea
    setTimeout(() => {
        document.getElementById('aiQuestionInput').focus();
    }, 100);

    // Store target field globally for later use
    window.aiAssistantTargetField = targetField;
}

/**
 * Ask AI the accounting question and display results
 */
async function askAIAccountingQuestion(transactionId, fieldTransactionId, fieldName) {
    const questionInput = document.getElementById('aiQuestionInput');
    const question = questionInput.value.trim();
    const askBtn = document.getElementById('askAIBtn');
    const resultDiv = document.getElementById('aiAssistantResult');

    if (!question) {
        showToast('Please enter a question', 'warning');
        return;
    }

    // Disable button and show loading
    askBtn.disabled = true;
    askBtn.textContent = 'Asking AI...';
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '<div style="text-align: center; padding: 20px;"><div class="loading">🤖 AI is thinking...</div></div>';

    try {
        // Get transaction context from the row
        const targetField = window.aiAssistantTargetField;
        const row = targetField?.closest('tr');
        const description = row?.querySelector('[data-field="description"]')?.textContent?.trim() || '';
        const amount = row?.querySelector('[data-field="amount"]')?.textContent?.trim() || '';
        const entity = row?.querySelector('[data-field="classified_entity"]')?.textContent?.trim() || '';

        // Call AI endpoint
        const response = await fetch('/api/ai/ask-accounting-category', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                question: question,
                transaction_context: {
                    description: description,
                    amount: amount,
                    entity: entity
                }
            })
        });

        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Failed to get AI response');
        }

        // Display results
        const result = data.result;
        let resultHTML = '<div style="background: #e8f4f8; padding: 15px; border-radius: 6px; border-left: 4px solid #0066cc;">';
        resultHTML += '<h4 style="margin-top: 0; color: #0066cc;">AI Recommendation:</h4>';

        if (result.note) {
            resultHTML += `<p style="font-style: italic; margin-bottom: 15px; color: #666;">${result.note}</p>`;
        }

        result.categories.forEach((cat, index) => {
            resultHTML += `
                <div style="background: white; padding: 12px; margin-bottom: 10px; border-radius: 4px; border: 1px solid #ddd;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div style="flex: 1;">
                            <strong style="color: #0066cc; font-size: 1.1em;">${cat.name}</strong>
                            <p style="margin: 8px 0 0 0; color: #666; font-size: 0.95em;">${cat.explanation}</p>
                        </div>
                        <button
                            onclick="applyAIAccountingCategory('${cat.name}', '${fieldTransactionId}', '${fieldName}')"
                            class="btn-primary"
                            style="margin-left: 15px; white-space: nowrap;">
                            Apply This
                        </button>
                    </div>
                </div>
            `;
        });

        resultHTML += '</div>';

        resultDiv.innerHTML = resultHTML;

        // Re-enable button but change text
        askBtn.disabled = false;
        askBtn.textContent = 'Ask Another Question';

    } catch (error) {
        console.error('Error asking AI:', error);
        resultDiv.innerHTML = `
            <div style="background: #fee; padding: 15px; border-radius: 6px; border-left: 4px solid #c33;">
                <p style="color: #c33; margin: 0;"><strong>Error:</strong> ${error.message}</p>
            </div>
        `;
        askBtn.disabled = false;
        askBtn.textContent = 'Try Again';
    }
}

/**
 * Apply the AI-suggested accounting category to the transaction
 */
async function applyAIAccountingCategory(categoryName, transactionId, fieldName) {
    try {
        const response = await fetch('/api/update_transaction', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                transaction_id: transactionId,
                field: fieldName,
                value: categoryName
            })
        });

        const data = await response.json();

        if (data.success) {
            showToast(`Applied category: ${categoryName}`, 'success');
            closeModal();
            loadTransactions();
        } else {
            showToast('Error applying category: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error applying category:', error);
        showToast('Error applying category. Please try again.', 'error');
    }
}

// ===========================
// Invoice Matching Functions
// ===========================

/**
 * Main function to run invoice matching and display results in modal
 */
async function runInvoiceMatching() {
    const modal = document.getElementById('invoiceMatchingModal');
    const loadingDiv = document.getElementById('matchingLoading');
    const summaryDiv = document.getElementById('matchingSummary');
    const containerDiv = document.getElementById('matchesContainer');
    const emptyDiv = document.getElementById('matchesEmpty');
    const errorDiv = document.getElementById('matchesError');

    // Show modal and loading state
    modal.style.display = 'block';
    loadingDiv.style.display = 'block';
    summaryDiv.style.display = 'none';
    containerDiv.style.display = 'none';
    emptyDiv.style.display = 'none';
    errorDiv.style.display = 'none';

    try {
        // Step 1: Run the matching algorithm
        const matchResponse = await fetch('/api/revenue/run-robust-matching', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                auto_apply: false  // Don't auto-apply, let user review
            })
        });

        const matchData = await matchResponse.json();

        if (!matchData.success) {
            throw new Error(matchData.error || 'Failed to run matching algorithm');
        }

        // Hide loading
        loadingDiv.style.display = 'none';

        // Get matches directly from the matching algorithm response
        const allMatches = matchData.matches || [];

        // Only keep the BEST match for each invoice (highest score)
        const bestMatches = {};
        allMatches.forEach(match => {
            const invoiceId = match.invoice_id;
            if (!bestMatches[invoiceId] || match.score > bestMatches[invoiceId].score) {
                bestMatches[invoiceId] = match;
            }
        });

        // Convert back to array and filter for medium/high confidence only
        const matches = Object.values(bestMatches).filter(m => m.score >= 0.4);

        if (matches.length === 0) {
            emptyDiv.style.display = 'block';
        } else {
            // Show summary
            document.getElementById('totalMatchesCount').textContent = matches.length;
            summaryDiv.style.display = 'block';

            // Fetch full details for matches and render table
            await renderMatchesTableWithDetails(matches);
            containerDiv.style.display = 'block';
        }

    } catch (error) {
        console.error('Error running invoice matching:', error);
        loadingDiv.style.display = 'none';
        errorDiv.style.display = 'block';
        document.getElementById('matchesErrorMessage').textContent = error.message;
    }
}

/**
 * Render matches table with invoice and transaction details (provided by backend)
 */
async function renderMatchesTableWithDetails(matches) {
    const tbody = document.getElementById('matchesTableBody');
    tbody.innerHTML = '';

    // The backend now provides invoice and transaction details inline
    matches.forEach((match, index) => {
        const invoice = match.invoice || {};
        const transaction = match.transaction || {};

        const row = document.createElement('tr');
        row.style.borderBottom = '1px solid #ddd';

        const matchScore = match.score || 0;
        const confidenceColor = matchScore >= 0.8 ? '#28a745' :
                               matchScore >= 0.6 ? '#ffc107' : '#dc3545';

        row.innerHTML = `
            <td style="padding: 12px; border: 1px solid #ddd;">
                <div><strong>${invoice.customer_name || 'Unknown Client'}</strong></div>
                <div style="font-size: 0.85em; color: #666;">
                    Invoice: ${invoice.invoice_number || 'N/A'}
                </div>
                <div style="font-size: 0.85em; color: #666;">
                    Amount: $${parseFloat(invoice.total_amount || 0).toFixed(2)} ${invoice.currency || 'USD'}
                </div>
                <div style="font-size: 0.85em; color: #666;">
                    Date: ${invoice.date ? new Date(invoice.date).toLocaleDateString() : 'N/A'}
                </div>
            </td>
            <td style="padding: 12px; border: 1px solid #ddd;">
                <div><strong>${transaction.description || 'Unknown'}</strong></div>
                <div style="font-size: 0.85em; color: #666;">
                    Amount: $${Math.abs(parseFloat(transaction.amount || 0)).toFixed(2)} ${transaction.currency || 'USD'}
                </div>
                <div style="font-size: 0.85em; color: #666;">
                    Date: ${transaction.date ? new Date(transaction.date).toLocaleDateString() : 'N/A'}
                </div>
                <div style="font-size: 0.85em; color: #666;">
                    Entity: ${transaction.classified_entity || 'N/A'}
                </div>
            </td>
            <td style="padding: 12px; text-align: center; border: 1px solid #ddd;">
                <div style="background: ${confidenceColor}; color: white; padding: 6px 12px; border-radius: 20px; display: inline-block; font-weight: bold;">
                    ${(matchScore * 100).toFixed(0)}%
                </div>
                <div style="font-size: 0.75em; color: #666; margin-top: 4px;">
                    ${match.match_type || ''}
                </div>
            </td>
            <td style="padding: 12px; border: 1px solid #ddd; font-size: 0.9em;">
                ${match.explanation || `Matched based on ${match.match_type || 'similarity'}`}
            </td>
            <td style="padding: 12px; text-align: center; border: 1px solid #ddd;">
                <button class="btn-primary" style="margin: 4px; padding: 8px 16px; font-size: 0.9em;"
                        onclick="acceptMatch('${match.invoice_id}', '${match.transaction_id}', '${(invoice.customer_name || '').replace(/'/g, "\\'")}', '${(invoice.invoice_number || '').replace(/'/g, "\\'")}')">
                    ✓ Accept
                </button>
                <button class="btn-secondary" style="margin: 4px; padding: 8px 16px; font-size: 0.9em;"
                        onclick="rejectMatch('${match.invoice_id}', '${match.transaction_id}')">
                    ✗ Reject
                </button>
            </td>
        `;

        tbody.appendChild(row);
    });
}

/**
 * Render the matches in the table
 * Handles both formats: from run-robust-matching (matches array) and from matched-pairs (pairs array)
 */
function renderMatchesTable(matches) {
    const tbody = document.getElementById('matchesTableBody');
    tbody.innerHTML = '';

    matches.forEach((match, index) => {
        const row = document.createElement('tr');
        row.style.borderBottom = '1px solid #ddd';

        // Calculate confidence badge color based on score
        const matchScore = match.score || match.match_score || 0;
        const confidenceColor = matchScore >= 0.8 ? '#28a745' :
                               matchScore >= 0.6 ? '#ffc107' : '#dc3545';

        // Determine if this is from run-robust-matching (has invoice_id/transaction_id directly)
        // or from matched-pairs (has nested invoice/transaction objects)
        const isDirectMatch = !match.invoice && !match.transaction;

        row.innerHTML = `
            <td style="padding: 12px; border: 1px solid #ddd;">
                <div><strong>Invoice ID: ${match.invoice_id || 'N/A'}</strong></div>
                <div style="font-size: 0.85em; color: #666; margin-top: 8px;">
                    <em>View details in /invoices page</em>
                </div>
            </td>
            <td style="padding: 12px; border: 1px solid #ddd;">
                <div><strong>Transaction ID: ${match.transaction_id || 'N/A'}</strong></div>
                <div style="font-size: 0.85em; color: #666; margin-top: 8px;">
                    <em>View details in transactions table</em>
                </div>
            </td>
            <td style="padding: 12px; text-align: center; border: 1px solid #ddd;">
                <div style="background: ${confidenceColor}; color: white; padding: 6px 12px; border-radius: 20px; display: inline-block; font-weight: bold;">
                    ${(matchScore * 100).toFixed(0)}%
                </div>
                <div style="font-size: 0.75em; color: #666; margin-top: 4px;">
                    ${match.match_type || ''}
                </div>
                <div style="font-size: 0.75em; color: #666; margin-top: 2px;">
                    ${match.confidence_level || ''}
                </div>
            </td>
            <td style="padding: 12px; border: 1px solid #ddd; font-size: 0.9em;">
                ${match.explanation || match.match_explanation || `Matched based on ${match.match_type || 'amount and date proximity'}`}
            </td>
            <td style="padding: 12px; text-align: center; border: 1px solid #ddd;">
                <button class="btn-primary" style="margin: 4px; padding: 8px 16px; font-size: 0.9em;"
                        onclick="acceptMatch('${match.invoice_id}', '${match.transaction_id}')">
                    ✓ Accept
                </button>
                <button class="btn-secondary" style="margin: 4px; padding: 8px 16px; font-size: 0.9em;"
                        onclick="rejectMatch('${match.invoice_id}', '${match.transaction_id}')">
                    ✗ Reject
                </button>
            </td>
        `;

        tbody.appendChild(row);
    });
}

/**
 * Accept a match (confirm the invoice-transaction pairing)
 */
async function acceptMatch(invoiceId, transactionId, customerName, invoiceNumber) {
    try {
        const response = await fetch('/api/revenue/confirm-match', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                invoice_id: invoiceId,
                transaction_id: transactionId,
                customer_name: customerName,
                invoice_number: invoiceNumber,
                user_id: 'admin'  // TODO: Replace with actual user ID when auth is implemented
            })
        });

        const data = await response.json();

        if (data.success) {
            showToast('Match accepted! Transaction reclassified as Revenue.', 'success');
            // Re-run the matching to refresh the list
            runInvoiceMatching();
            // Refresh the transactions table
            loadTransactions();
        } else {
            showToast('Error accepting match: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error accepting match:', error);
        showToast('Error accepting match. Please try again.', 'error');
    }
}

/**
 * Reject a match (mark as incorrect pairing)
 */
async function rejectMatch(invoiceId, transactionId) {
    const reason = prompt('Please provide a reason for rejecting this match (optional):');

    try {
        const response = await fetch('/api/revenue/unmatch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                invoice_id: invoiceId,
                reason: reason || 'User rejected match',
                user_id: 'admin'  // TODO: Replace with actual user ID when auth is implemented
            })
        });

        const data = await response.json();

        if (data.success) {
            showToast('Match rejected successfully.', 'success');
            // Re-run the matching to refresh the list
            runInvoiceMatching();
        } else {
            showToast('Error rejecting match: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Error rejecting match:', error);
        showToast('Error rejecting match. Please try again.', 'error');
    }
}

/**
 * Close the invoice matching modal
 */
function closeInvoiceMatchingModal() {
    const modal = document.getElementById('invoiceMatchingModal');
    modal.style.display = 'none';
}

/**
 * Run blockchain enrichment for all pending transactions
 */
async function runBlockchainEnrichment() {
    const button = document.getElementById('runBlockchainEnrichment');
    const originalText = button.textContent;

    // Disable button and show loading state
    button.disabled = true;
    button.textContent = '⏳ Enriching...';
    button.style.opacity = '0.6';

    try {
        showToast('🔗 Starting blockchain enrichment for all pending transactions...', 'info');

        // Call the enrichment endpoint
        const response = await fetch('/api/transactions/enrich/all-pending', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                batch_size: 100  // Process 100 at a time
            })
        });

        const data = await response.json();

        if (data.success) {
            const results = data.results;
            const successRate = results.total_processed > 0
                ? ((results.successful / results.total_processed) * 100).toFixed(1)
                : 0;

            // Show detailed results
            const message = `
✅ Blockchain Enrichment Complete!

📊 Results:
• Total Pending: ${results.total_pending}
• Processed: ${results.total_processed}
• ✅ Successful: ${results.successful}
• ❌ Failed: ${results.failed}
• ⏭️ Skipped: ${results.skipped}
• Success Rate: ${successRate}%
• Batches: ${results.batches_processed}

Transactions have been enriched with:
• Blockchain wallet addresses
• Matched against known wallets
• Auto-categorized based on wallet types
            `.trim();

            showToast(message, 'success');

            // Refresh the transaction table to show updated data
            setTimeout(() => {
                if (typeof loadTransactions === 'function') {
                    loadTransactions();
                }
            }, 1500);

        } else {
            throw new Error(data.error || 'Failed to run blockchain enrichment');
        }

    } catch (error) {
        console.error('Error running blockchain enrichment:', error);
        showToast('❌ Error running blockchain enrichment: ' + error.message, 'error');
    } finally {
        // Re-enable button
        button.disabled = false;
        button.textContent = originalText;
        button.style.opacity = '1';
    }
}

// ============================================================================
// EXCEL-LIKE DRAG-DOWN FILL FUNCTIONALITY
// ============================================================================

function setupDragDownHandles() {
    // Add drag handles and sort dots to editable cells
    document.querySelectorAll('.editable-field').forEach(cell => {
        // Add drag handle (bottom-right)
        if (!cell.querySelector('.drag-handle')) {
            const handle = document.createElement('div');
            handle.className = 'drag-handle';
            handle.title = 'Drag to fill down';
            cell.style.position = 'relative';
            cell.appendChild(handle);

            // Handle mousedown on drag handle
            handle.addEventListener('mousedown', (e) => {
                e.preventDefault();
                e.stopPropagation();
                startDragFill(cell);
            });
        }

        // Add sort dot (top-right)
        if (!cell.querySelector('.sort-dot')) {
            const sortDot = document.createElement('div');
            sortDot.className = 'sort-dot';
            sortDot.title = 'Sort all by this value';
            cell.appendChild(sortDot);

            // Handle click on sort dot
            sortDot.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                sortByCell(cell);
            });
        }
    });
}

function startDragFill(cell) {
    const row = cell.closest('tr');
    const fieldName = cell.dataset.field;
    let value;

    // Get current value from cell
    if (cell.classList.contains('smart-dropdown')) {
        // For dropdown fields, get the text content
        const span = cell.querySelector('span');
        value = span ? span.textContent.trim() : cell.textContent.trim();
    } else {
        value = cell.textContent.trim();
    }

    // Initialize drag state
    dragFillState = {
        isDragging: true,
        startRow: row,
        startCell: cell,
        fieldName: fieldName,
        value: value,
        affectedRows: [row]
    };

    // Add visual feedback
    row.classList.add('drag-fill-source');
    cell.classList.add('drag-fill-active');

    // Add document-level event listeners
    document.addEventListener('mousemove', handleDragFillMove);
    document.addEventListener('mouseup', handleDragFillEnd);

    console.log(`🎯 Started drag fill: field="${fieldName}", value="${value}"`);
}

function handleDragFillMove(e) {
    if (!dragFillState.isDragging) return;

    // Find the row under the mouse
    const targetElement = document.elementFromPoint(e.clientX, e.clientY);
    if (!targetElement) return;

    const targetRow = targetElement.closest('tr');
    if (!targetRow || !targetRow.dataset.transactionId) return;

    // Get all rows in the table
    const tbody = document.getElementById('transactionTableBody');
    const allRows = Array.from(tbody.querySelectorAll('tr[data-transaction-id]'));
    const startIndex = allRows.indexOf(dragFillState.startRow);
    const targetIndex = allRows.indexOf(targetRow);

    // Determine range of affected rows
    const minIndex = Math.min(startIndex, targetIndex);
    const maxIndex = Math.max(startIndex, targetIndex);

    // Clear previous highlights
    dragFillState.affectedRows.forEach(row => {
        row.classList.remove('drag-fill-target');
    });

    // Highlight affected rows
    dragFillState.affectedRows = [];
    for (let i = minIndex; i <= maxIndex; i++) {
        const row = allRows[i];
        row.classList.add('drag-fill-target');
        dragFillState.affectedRows.push(row);
    }
}

async function handleDragFillEnd(e) {
    if (!dragFillState.isDragging) return;

    // Remove event listeners
    document.removeEventListener('mousemove', handleDragFillMove);
    document.removeEventListener('mouseup', handleDragFillEnd);

    const affectedCount = dragFillState.affectedRows.length;

    console.log(`🖱️ Drag ended. Affected rows: ${affectedCount}`);

    if (affectedCount > 1) {
        // Apply the value to all affected rows
        console.log(`📝 Applying "${dragFillState.value}" to ${affectedCount} rows for field "${dragFillState.fieldName}"`);
        console.log('Affected rows:', dragFillState.affectedRows.map(r => r.dataset.transactionId));

        const updates = [];
        for (const row of dragFillState.affectedRows) {
            const transactionId = row.dataset.transactionId;
            if (transactionId) {
                updates.push({
                    transaction_id: transactionId,
                    field: dragFillState.fieldName,
                    value: dragFillState.value
                });
                console.log(`  ✓ Queuing update for transaction: ${transactionId}`);
            } else {
                console.warn(`  ✗ Row missing transaction ID:`, row);
            }
        }

        console.log(`📦 Prepared ${updates.length} updates out of ${affectedCount} affected rows`);
        console.log('Updates:', JSON.stringify(updates, null, 2));

        // Show loading toast
        showToast(`⏳ Updating ${updates.length} transactions...`, 'info');

        // Send bulk update to backend
        try {
            const response = await fetch('/api/bulk_update_transactions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ updates })
            });

            const result = await response.json();

            if (result.success) {
                showToast(`✅ Successfully updated ${updates.length} transactions`, 'success');

                // Update the cells in place instead of reloading
                // This preserves the current sort order and avoids page reset
                dragFillState.affectedRows.forEach(row => {
                    const cell = row.querySelector(`[data-field="${dragFillState.fieldName}"]`);
                    if (cell) {
                        // Update the cell's displayed value
                        if (cell.classList.contains('smart-dropdown')) {
                            const span = cell.querySelector('span');
                            if (span) {
                                span.textContent = dragFillState.value;
                            } else {
                                cell.textContent = dragFillState.value;
                            }
                        } else {
                            cell.textContent = dragFillState.value;
                        }
                    }
                });

                // Refresh stats only (not the full table)
                await loadDashboardStats();

                // Re-add drag handles to updated cells
                setTimeout(() => {
                    setupDragDownHandles();
                }, 100);
            } else {
                throw new Error(result.error || 'Update failed');
            }
        } catch (error) {
            console.error('Bulk update error:', error);
            showToast(`❌ Error updating transactions: ${error.message}`, 'error');
        }
    }

    // Clear drag state and visual feedback
    dragFillState.affectedRows.forEach(row => {
        row.classList.remove('drag-fill-target', 'drag-fill-source');
    });
    dragFillState.startCell?.classList.remove('drag-fill-active');

    dragFillState = {
        isDragging: false,
        startRow: null,
        startCell: null,
        fieldName: null,
        value: null,
        affectedRows: []
    };
}

// ============================================================================
// SORT BY CELL VALUE FUNCTIONALITY
// ============================================================================

function sortByCell(cell) {
    const fieldName = cell.dataset.field;
    let value;

    // Get current value from cell
    if (cell.classList.contains('smart-dropdown')) {
        const span = cell.querySelector('span');
        value = span ? span.textContent.trim() : cell.textContent.trim();
    } else {
        value = cell.textContent.trim();
    }

    console.log(`🔍 Sorting by ${fieldName} = "${value}"`);

    // Get the table body
    const tbody = document.getElementById('transactionTableBody');
    if (!tbody) {
        console.error('Transaction table body not found');
        return;
    }

    // Get all rows
    const rows = Array.from(tbody.querySelectorAll('tr'));

    // Separate matching rows from non-matching rows
    const matchingRows = [];
    const nonMatchingRows = [];

    rows.forEach(row => {
        // Find the cell in this row that corresponds to the same field
        const rowCell = row.querySelector(`[data-field="${fieldName}"]`);
        if (rowCell) {
            let rowValue;
            if (rowCell.classList.contains('smart-dropdown')) {
                const span = rowCell.querySelector('span');
                rowValue = span ? span.textContent.trim() : rowCell.textContent.trim();
            } else {
                rowValue = rowCell.textContent.trim();
            }

            // Check if values match (case-insensitive for text fields)
            if (rowValue.toLowerCase() === value.toLowerCase()) {
                matchingRows.push(row);
            } else {
                nonMatchingRows.push(row);
            }
        }
    });

    // Clear the table
    tbody.innerHTML = '';

    // Add matching rows first (grouped together)
    matchingRows.forEach(row => {
        row.classList.add('sort-highlight');
        tbody.appendChild(row);
    });

    // Then add non-matching rows
    nonMatchingRows.forEach(row => {
        row.classList.remove('sort-highlight');
        tbody.appendChild(row);
    });

    // Remove highlight after 2 seconds
    setTimeout(() => {
        matchingRows.forEach(row => {
            row.classList.remove('sort-highlight');
        });
    }, 2000);

    showToast(`✅ Sorted ${matchingRows.length} transactions by ${fieldName} = "${value}"`, 'success');
}