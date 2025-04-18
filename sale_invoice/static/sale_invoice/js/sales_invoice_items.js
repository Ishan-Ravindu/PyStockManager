document.addEventListener('DOMContentLoaded', function() {
    if (typeof django !== 'undefined' && typeof django.jQuery === 'function') {
        initInvoiceItemHandler(django.jQuery);
    } else {
        const checkDjangoJQuery = setInterval(function() {
            if (typeof django !== 'undefined' && typeof django.jQuery === 'function') {
                clearInterval(checkDjangoJQuery);
                initInvoiceItemHandler(django.jQuery);
            }
        }, 100);
    }
});

function initInvoiceItemHandler($) {
    const shopField = $('#id_shop');
    let currentShopId = shopField.val();
    let stockData = {};
    
    if (currentShopId) {
        fetchStockData(currentShopId);
    }
    
    shopField.on('change', function() {
        currentShopId = $(this).val();
        if (currentShopId) {
            stockData = {};
            fetchStockData(currentShopId);
            updateAllProductFields();
        }
    });
    
    function fetchStockData(shopId) {
       
        fetch(`/api/inventory/stock/?shop_id=${shopId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`API request failed with status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                stockData = data;
                updateAllProductFields();
            })
            .catch(error => {
                console.error('Error fetching stock data:', error);
            });
    }
    
    function updateAllProductFields() {
        $('select[id$="-product"]').each(function() {
            const productField = $(this);
            const productId = productField.val();
            
            if (productId) {
                const row = productField.closest('tr');
                updateProductInfoHelper(row, productId);
            }
        });
    }
    
    initializeRows();
    
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes && mutation.addedNodes.length > 0) {
                const addedNodes = $(mutation.addedNodes);
                const addedRows = addedNodes.filter('tr:not(.empty-form)').add(addedNodes.find('tr:not(.empty-form)'));
                
                if (addedRows.length > 0) {
                    setTimeout(function() {
                        initializeRows(addedRows);
                    }, 100);
                }
            }
        });
    });
    
    const formsetContainer = $('.module.aligned-formset, #salesinvoiceitem_set-group, .tabular');
    if (formsetContainer.length > 0) {
        observer.observe(formsetContainer[0], { childList: true, subtree: true });
    } else {
        console.warn('Formset container not found for mutation observer');
    }
    
    function initializeRows(rows) {
        const rowsToInit = rows || $('.module.aligned-formset tr:not(.empty-form), #salesinvoiceitem_set-group tr:not(.empty-form)');
        
        rowsToInit.each(function() {
            const row = $(this);
            
            if (row.data('initialized')) {
                return;
            }
            
            row.data('initialized', true);
            
            const productField = row.find('select[id$="-product"]');
           
            if (productField.length === 0) {
                return;
            }
            
            const productFieldCell = productField.closest('td');
            let helperDiv = productFieldCell.find('.product-info-helper');
            if (helperDiv.length === 0) {
                productFieldCell.append('<div class="product-info-helper" style="color: #666; font-size: 12px; margin-top: 5px; display: block; clear: both;"></div>');
                helperDiv = productFieldCell.find('.product-info-helper');
            }
            
            productField.on('change', function() {
                const productId = $(this).val();
                if (productId) {
                    updateProductInfoHelper(row, productId);
                } else {
                    clearProductInfoHelper(row);
                }
            });
            
            const productId = productField.val();
            if (productId) {
                updateProductInfoHelper(row, productId);
            }
        });
    }
    
    function updateProductInfoHelper(row, productId) {
        const productField = row.find('select[id$="-product"]');
        const productFieldCell = productField.closest('td');
        let helperDiv = productFieldCell.find('.product-info-helper');
        
        if (helperDiv.length === 0) {
            productFieldCell.append('<div class="product-info-helper" style="color: #666; font-size: 12px; margin-top: 5px; display: block; clear: both;"></div>');
            helperDiv = productFieldCell.find('.product-info-helper');
        }
       
        if (stockData[productId]) {
            const stock = stockData[productId];
            helperDiv.html(
                `<strong>Available Quantity:</strong> ${stock.quantity}`
            );
        } else {
            helperDiv.html('Loading product information...');
            if (currentShopId) {
                fetchStockData(currentShopId);
            }
        }
    }
    
    function clearProductInfoHelper(row) {
        const productFieldCell = row.find('select[id$="-product"]').closest('td');
        productFieldCell.find('.product-info-helper').html('');
    }
}