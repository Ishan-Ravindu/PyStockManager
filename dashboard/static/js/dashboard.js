const Dashboard = (function() {
    // Configuration
    const config = {
        itemsPerPage: 30,
        defaultSort: {
            column: 'shop_name',
            order: 'asc'
        }
    };

    // State
    const state = {
        allShops: [],
        allInventoryData: [],
        currentPage: 1,
        currentSort: {...config.defaultSort}
    };

    // DOM Elements
    const elements = {
        dashboardCards: {
            balance: document.getElementById('total-balance'),
            payable: document.getElementById('total-payable'),
            receivable: document.getElementById('total-receivables')
        },
        allShopsSummary: {
            inventoryValue: document.getElementById('all-shops-inventory-value'),
            productsCount: document.getElementById('all-shops-products-count')
        },
        tabsContainer: document.getElementById('shop-tabs')
    };

    // Utility functions
    const utils = {
        formatNumber: (value) => {
            if (typeof value === 'string' && !isNaN(parseFloat(value))) {
                return parseFloat(value).toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                });
            }
            return value;
        },
        
        createInventoryRow: (item, includeShop = true) => {
            return `
                <tr>
                    ${includeShop ? `<td>${item.shop_name || ''}</td>` : ''}
                    <td>${item.product_id}</td>
                    <td>${item.product_name}</td>
                    <td>${item.quantity}</td>
                    <td>${utils.formatNumber(item.average_cost)}</td>
                    <td>${utils.formatNumber(item.selling_price)}</td>
                    <td>${utils.formatNumber(item.inventory_value)}</td>
                </tr>
            `;
        },
        
        createShopInfo: (shop) => {
            return `
                <div class="shop-info">
                    <div class="shop-name">${shop.name}</div>
                    <div class="shop-inventory-value">Total Inventory Value: ${utils.formatNumber(shop.total_inventory_value)}</div>
                    <div class="shop-products-count">Total Products: ${shop.total_products}</div>
                </div>
            `;
        }
    };

    // API functions
    const api = {
        fetchFinancialData: async () => {
            try {
                const [balanceRes, payableRes, receivableRes] = await Promise.all([
                    fetch('/api/account/total-balance/'),
                    fetch('/api/purchase_invoice/total-payable/'),
                    fetch('/api/sale_invoice/total-receivables/')
                ]);

                const balanceData = await balanceRes.json();
                const payableData = await payableRes.json();
                const receivableData = await receivableRes.json();
                
                elements.dashboardCards.balance.textContent = utils.formatNumber(balanceData.total_balance);
                elements.dashboardCards.payable.textContent = utils.formatNumber(payableData.total_payable);
                elements.dashboardCards.receivable.textContent = utils.formatNumber(receivableData.total_receivables);
            } catch (error) {
                console.error("Error fetching financial data", error);
                elements.dashboardCards.balance.textContent = "Error";
                elements.dashboardCards.payable.textContent = "Error";
                elements.dashboardCards.receivable.textContent = "Error";
            }
        },
        
        fetchShops: async () => {
            try {
                const response = await fetch('/api/shop/');
                state.allShops = await response.json();
                
                // Remove loading tab
                document.querySelector('.tab[data-shop-id="loading"]').style.display = 'none';
                
                // Create tabs for each shop
                for (const shop of state.allShops) {
                    try {
                        const inventoryRes = await fetch(`/api/inventory/inventory-value/?shop_id=${shop.id}`);
                        const inventoryData = await inventoryRes.json();
                        
                        // Add shop inventory data
                        shop.total_inventory_value = inventoryData.total_inventory_value;
                        shop.total_products = inventoryData.products.length;
                        
                        // Add inventory data to global array
                        inventoryData.products.forEach(product => {
                            product.shop_id = shop.id.toString();
                            product.shop_name = shop.name;
                            state.allInventoryData.push(product);
                        });
                        
                        // Create tab for this shop
                        createShopTab(shop);
                        
                        // Populate the shop's inventory table
                        const shopInventory = state.allInventoryData.filter(item => item.shop_id === shop.id.toString());
                        displayShopInventory(shop.id.toString(), shopInventory);
                        
                    } catch (inventoryError) {
                        console.error(`Error fetching inventory for shop ${shop.id}`, inventoryError);
                    }
                }
                
                // Setup all inventory tab and populate it
                setupAllInventoryTab();
                displayAllInventory(state.allInventoryData);
                
            } catch (error) {
                console.error("Error fetching shops", error);
                document.querySelector('.tab[data-shop-id="loading"]').textContent = "Error loading shops";
                document.querySelector('.tab[data-shop-id="loading"]').style.display = 'block';
            }
        }
    };

    // UI functions
    const ui = {
        switchTab: (shopId) => {
            // Hide all tab contents
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Deactivate all tabs
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Activate selected tab and content
            document.querySelector(`.tab[data-shop-id="${shopId}"]`).classList.add('active');
            document.getElementById(`content-${shopId}`).classList.add('active');
            
            // Reset to first page when switching tabs
            state.currentPage = 1;
        },
        
        createPagination: (totalItems, currentPage, containerId) => {
            const totalPages = config.itemsPerPage > 0 ? Math.ceil(totalItems / config.itemsPerPage) : 1;
            const paginationContainer = document.getElementById(containerId);
            paginationContainer.innerHTML = '';
            
            // Previous button
            if (totalPages > 1) {
                const prevButton = document.createElement('button');
                prevButton.className = 'pagination-button';
                prevButton.textContent = 'Previous';
                prevButton.disabled = currentPage === 1;
                prevButton.onclick = () => ui.goToPage(currentPage - 1, containerId);
                paginationContainer.appendChild(prevButton);
                
                // Page buttons
                let startPage = Math.max(1, currentPage - 2);
                let endPage = Math.min(totalPages, startPage + 4);
                
                if (endPage - startPage < 4) {
                    startPage = Math.max(1, endPage - 4);
                }
                
                for (let i = startPage; i <= endPage; i++) {
                    const pageButton = document.createElement('button');
                    pageButton.className = `pagination-button ${i === currentPage ? 'active' : ''}`;
                    pageButton.textContent = i;
                    pageButton.onclick = () => ui.goToPage(i, containerId);
                    paginationContainer.appendChild(pageButton);
                }
                
                // Next button
                const nextButton = document.createElement('button');
                nextButton.className = 'pagination-button';
                nextButton.textContent = 'Next';
                nextButton.disabled = currentPage === totalPages;
                nextButton.onclick = () => ui.goToPage(currentPage + 1, containerId);
                paginationContainer.appendChild(nextButton);
            }
            
            // Add page size selector
            const pageSizeSelect = document.createElement('select');
            pageSizeSelect.className = 'pagination-button';
            pageSizeSelect.innerHTML = `
                <option value="20" ${config.itemsPerPage === 20 ? 'selected' : ''}>20</option>
                <option value="30" ${config.itemsPerPage === 30 ? 'selected' : ''}>30</option>
                <option value="50" ${config.itemsPerPage === 50 ? 'selected' : ''}>50</option>
                <option value="100" ${config.itemsPerPage === 100 ? 'selected' : ''}>100</option>
                <option value="0" ${config.itemsPerPage === 0 ? 'selected' : ''}>ALL</option>
            `;
            pageSizeSelect.value = config.itemsPerPage;
            pageSizeSelect.onchange = function() {
                config.itemsPerPage = parseInt(this.value) || 0;
                state.currentPage = 1;
                const shopId = containerId.replace('-pagination', '');
                
                if (shopId === 'all') {
                    displayAllInventory(filterAllInventory());
                } else {
                    const shopInventory = filterShopInventory(shopId);
                    displayShopInventory(shopId, shopInventory);
                }
            };
            paginationContainer.appendChild(pageSizeSelect);
        },
        
        goToPage: (page, paginationId) => {
            state.currentPage = page;
            const shopId = paginationId.replace('-pagination', '');
            
            if (shopId === 'all') {
                displayAllInventory(filterAllInventory());
            } else {
                const shopInventory = filterShopInventory(shopId);
                displayShopInventory(shopId, shopInventory);
            }
        },
        
        sortTable: (tableId, sortBy, order = 'asc') => {
            state.currentSort.column = sortBy;
            state.currentSort.order = order;
            
            const table = document.getElementById(tableId);
            const headerCells = table.querySelectorAll('th');
            
            // Reset all header styles
            headerCells.forEach(cell => {
                cell.classList.remove('sorted-asc', 'sorted-desc');
            });
            
            // Set the active sort header
            const activeHeader = table.querySelector(`th[data-sort="${sortBy}"]`);
            if (activeHeader) {
                activeHeader.classList.add(order === 'asc' ? 'sorted-asc' : 'sorted-desc');
            }
            
            // Determine which inventory to sort
            const shopId = tableId.replace('-inventory-table', '');
            
            if (shopId === 'all') {
                const filteredData = filterAllInventory();
                displayAllInventory(filteredData);
            } else {
                const shopInventory = filterShopInventory(shopId);
                displayShopInventory(shopId, shopInventory);
            }
        }
    };

    // Filter functions
    const filterAllInventory = () => {
        const productFilter = document.getElementById('all-filter-product').value.toLowerCase();
        const minQty = document.getElementById('all-filter-min-qty').value;
        const maxQty = document.getElementById('all-filter-max-qty').value;
        const minValue = document.getElementById('all-filter-min-value').value;
        const maxValue = document.getElementById('all-filter-max-value').value;
        
        return state.allInventoryData.filter(item => {
            const matchesProduct = !productFilter || (item.product_name && item.product_name.toLowerCase().includes(productFilter));
            const matchesMinQty = !minQty || item.quantity >= parseInt(minQty);
            const matchesMaxQty = !maxQty || item.quantity <= parseInt(maxQty);
            const matchesMinValue = !minValue || parseFloat(item.inventory_value) >= parseFloat(minValue);
            const matchesMaxValue = !maxValue || parseFloat(item.inventory_value) <= parseFloat(maxValue);
            
            return matchesProduct && matchesMinQty && matchesMaxQty && matchesMinValue && matchesMaxValue;
        });
    };
    
    const filterShopInventory = (shopId) => {
        const productFilter = document.getElementById(`${shopId}-filter-product`).value.toLowerCase();
        const minQty = document.getElementById(`${shopId}-filter-min-qty`).value;
        const maxQty = document.getElementById(`${shopId}-filter-max-qty`).value;
        const minValue = document.getElementById(`${shopId}-filter-min-value`).value;
        const maxValue = document.getElementById(`${shopId}-filter-max-value`).value;
        
        return state.allInventoryData.filter(item => {
            if (item.shop_id !== shopId) return false;
            
            const matchesProduct = !productFilter || (item.product_name && item.product_name.toLowerCase().includes(productFilter));
            const matchesMinQty = !minQty || item.quantity >= parseInt(minQty);
            const matchesMaxQty = !maxQty || item.quantity <= parseInt(maxQty);
            const matchesMinValue = !minValue || parseFloat(item.inventory_value) >= parseFloat(minValue);
            const matchesMaxValue = !maxValue || parseFloat(item.inventory_value) <= parseFloat(maxValue);
            
            return matchesProduct && matchesMinQty && matchesMaxQty && matchesMinValue && matchesMaxValue;
        });
    };

    // Display functions
    const displayAllInventory = (filteredData) => {
        // Apply current sort
        filteredData.sort((a, b) => {
            let valueA = a[state.currentSort.column];
            let valueB = b[state.currentSort.column];
            
            // Handle numeric values
            if (!isNaN(parseFloat(valueA)) && !isNaN(parseFloat(valueB))) {
                valueA = parseFloat(valueA);
                valueB = parseFloat(valueB);
            } else if (typeof valueA === 'string' && typeof valueB === 'string') {
                // Case-insensitive string comparison
                valueA = valueA.toLowerCase();
                valueB = valueB.toLowerCase();
            }
            
            if (valueA < valueB) return state.currentSort.order === 'asc' ? -1 : 1;
            if (valueA > valueB) return state.currentSort.order === 'asc' ? 1 : -1;
            return 0;
        });
        
        const totalItems = filteredData.length;
        const start = config.itemsPerPage > 0 ? (state.currentPage - 1) * config.itemsPerPage : 0;
        const end = config.itemsPerPage > 0 ? Math.min(start + config.itemsPerPage, totalItems) : totalItems;
        const paginatedData = config.itemsPerPage > 0 ? filteredData.slice(start, end) : filteredData;
        
        const tbody = document.getElementById('all-inventory-body');
        
        if (paginatedData.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" class="no-data">No inventory data found</td></tr>';
        } else {
            tbody.innerHTML = paginatedData.map(item => utils.createInventoryRow(item, true)).join('');
        }
        
        // Update all shops summary
        updateAllShopsSummary(filteredData);
        
        // Update sort indicators
        const table = document.getElementById('all-inventory-table');
        const headerCells = table.querySelectorAll('th');
        headerCells.forEach(cell => {
            cell.classList.remove('sorted-asc', 'sorted-desc');
            if (cell.dataset.sort === state.currentSort.column) {
                cell.classList.add(`sorted-${state.currentSort.order}`);
            }
        });
        
        ui.createPagination(totalItems, state.currentPage, 'all-pagination');
    };
    
    const updateAllShopsSummary = (data) => {
        let totalValue = 0;
        let uniqueProducts = new Set();
        
        data.forEach(item => {
            totalValue += parseFloat(item.inventory_value || 0);
            uniqueProducts.add(item.product_id);
        });
        
        elements.allShopsSummary.inventoryValue.textContent = utils.formatNumber(totalValue.toString());
        elements.allShopsSummary.productsCount.textContent = uniqueProducts.size;
    };
    
    const displayShopInventory = (shopId, filteredData) => {
        // Apply current sort
        filteredData.sort((a, b) => {
            let valueA = a[state.currentSort.column];
            let valueB = b[state.currentSort.column];
            
            // Handle numeric values
            if (!isNaN(parseFloat(valueA)) && !isNaN(parseFloat(valueB))) {
                valueA = parseFloat(valueA);
                valueB = parseFloat(valueB);
            } else if (typeof valueA === 'string' && typeof valueB === 'string') {
                // Case-insensitive string comparison
                valueA = valueA.toLowerCase();
                valueB = valueB.toLowerCase();
            }
            
            if (valueA < valueB) return state.currentSort.order === 'asc' ? -1 : 1;
            if (valueA > valueB) return state.currentSort.order === 'asc' ? 1 : -1;
            return 0;
        });
        
        const totalItems = filteredData.length;
        const start = config.itemsPerPage > 0 ? (state.currentPage - 1) * config.itemsPerPage : 0;
        const end = config.itemsPerPage > 0 ? Math.min(start + config.itemsPerPage, totalItems) : totalItems;
        const paginatedData = config.itemsPerPage > 0 ? filteredData.slice(start, end) : filteredData;
        
        const tbody = document.getElementById(`${shopId}-inventory-body`);
        
        if (paginatedData.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="no-data">No inventory data found</td></tr>';
        } else {
            tbody.innerHTML = paginatedData.map(item => utils.createInventoryRow(item, false)).join('');
        }
        
        // Update sort indicators
        const table = document.getElementById(`${shopId}-inventory-table`);
        const headerCells = table.querySelectorAll('th');
        headerCells.forEach(cell => {
            cell.classList.remove('sorted-asc', 'sorted-desc');
            if (cell.dataset.sort === state.currentSort.column) {
                cell.classList.add(`sorted-${state.currentSort.order}`);
            }
        });
        
        ui.createPagination(totalItems, state.currentPage, `${shopId}-pagination`);
    };

    // Setup functions
    const createShopTab = (shop) => {
        // Create tab
        const tab = document.createElement('div');
        tab.className = 'tab';
        tab.dataset.shopId = shop.id;
        tab.textContent = shop.name;
        tab.onclick = function() { ui.switchTab(shop.id); };
        elements.tabsContainer.appendChild(tab);
        
        // Create tab content
        const tabsContentContainer = document.querySelector('.tabs-container');
        const tabContent = document.createElement('div');
        tabContent.id = `content-${shop.id}`;
        tabContent.className = 'tab-content';
        
        // Create the shop information section
        tabContent.innerHTML = utils.createShopInfo(shop);
        
        // Create filters
        const filtersContainer = document.createElement('div');
        filtersContainer.className = 'filters-container';
        filtersContainer.innerHTML = `
            <input type="text" id="${shop.id}-filter-product" class="filter-input" placeholder="Filter by product name...">
            <input type="number" id="${shop.id}-filter-min-qty" class="filter-input" placeholder="Min quantity">
            <input type="number" id="${shop.id}-filter-max-qty" class="filter-input" placeholder="Max quantity">
            <input type="number" id="${shop.id}-filter-min-value" class="filter-input" placeholder="Min inventory value">
            <input type="number" id="${shop.id}-filter-max-value" class="filter-input" placeholder="Max inventory value">
        `;
        tabContent.appendChild(filtersContainer);
        
        // Create table
        const table = document.createElement('table');
        table.className = 'inventory-table';
        table.id = `${shop.id}-inventory-table`;
        table.innerHTML = `
            <thead>
                <tr>
                    <th data-sort="product_id">Product ID</th>
                    <th data-sort="product_name">Product Name</th>
                    <th data-sort="quantity">Quantity</th>
                    <th data-sort="average_cost">Average Cost</th>
                    <th data-sort="selling_price">Selling Price</th>
                    <th data-sort="inventory_value">Inventory Value</th>
                </tr>
            </thead>
            <tbody id="${shop.id}-inventory-body">
                <tr>
                    <td colspan="6" class="loading">Loading inventory data...</td>
                </tr>
            </tbody>
        `;
        tabContent.appendChild(table);
        
        // Create pagination
        const pagination = document.createElement('div');
        pagination.className = 'pagination';
        pagination.id = `${shop.id}-pagination`;
        tabContent.appendChild(pagination);
        
        tabsContentContainer.appendChild(tabContent);
        
        // Add event listeners for sorting
        const headerCells = table.querySelectorAll('th');
        headerCells.forEach(cell => {
            cell.addEventListener('click', function() {
                const sortBy = this.dataset.sort;
                const currentOrder = this.classList.contains('sorted-asc') ? 'desc' : 'asc';
                ui.sortTable(`${shop.id}-inventory-table`, sortBy, currentOrder);
            });
        });
        
        // Add event listeners for filtering
        const filterInputs = filtersContainer.querySelectorAll('input');
        filterInputs.forEach(input => {
            input.addEventListener('input', function() {
                state.currentPage = 1; // Reset to first page when filtering
                const shopInventory = filterShopInventory(shop.id);
                displayShopInventory(shop.id, shopInventory);
            });
        });
    };
    
    const setupAllInventoryTab = () => {
        // Add event listeners for sorting
        const headerCells = document.querySelectorAll('#all-inventory-table th');
        headerCells.forEach(cell => {
            cell.addEventListener('click', function() {
                const sortBy = this.dataset.sort;
                const currentOrder = this.classList.contains('sorted-asc') ? 'desc' : 'asc';
                ui.sortTable('all-inventory-table', sortBy, currentOrder);
            });
        });
        
        // Add event listeners for filtering
        const filterInputs = document.querySelectorAll('#content-all .filter-input');
        filterInputs.forEach(input => {
            input.addEventListener('input', function() {
                state.currentPage = 1; // Reset to first page when filtering
                displayAllInventory(filterAllInventory());
            });
        });
    };

    // Initialize
    const init = () => {
        api.fetchFinancialData();
        api.fetchShops();
    };

    // Public API
    return {
        init,
        switchTab: ui.switchTab,
        sortTable: ui.sortTable
    };
})();

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    Dashboard.init();
});