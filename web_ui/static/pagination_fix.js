
// Quick Fix for Pagination Issue
// This script forces showing all transactions instead of just 50

// Override the buildFilterQuery function
(function() {
    console.log('Applying pagination quick fix...');

    // Save original function
    const originalBuildFilterQuery = window.buildFilterQuery;

    window.buildFilterQuery = function() {
        // Call original function to get base params
        const queryString = originalBuildFilterQuery ? originalBuildFilterQuery() : '';
        const params = new URLSearchParams(queryString);

        // Override per_page to show all
        params.delete('per_page');
        params.append('per_page', 1000);

        console.log('Pagination fix applied - requesting 1000 items');
        return params.toString();
    };

    // Force reload after 2 seconds if loadTransactions exists
    setTimeout(() => {
        if (typeof loadTransactions === 'function') {
            console.log('Reloading transactions with fix...');
            loadTransactions();
        }
    }, 2000);

    console.log('Pagination quick fix loaded successfully');
})();
