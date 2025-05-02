document.addEventListener('DOMContentLoaded', function() {

    const $ = window.django?.jQuery || window.jQuery;
    if (!$) {
        console.error('jQuery not found for invoice total calculator');
        return;
    }
    
    console.log('jQuery found:', $);

    const totalAmountDisplay = $('.readonly').filter(function() {
        return $(this).closest('.field-line').find('label:contains("Total amount:")').length > 0;
    });
    
    if (totalAmountDisplay.length === 0) {
        console.error('Could not find total amount display');
        return;
    }
    const itemsContainer = $('#items-group');
    const attachedListeners = new Set();

    initCalculator();

    function initCalculator() {
        $(document).on('formset:added', function(event, $row, formsetName) {
            console.log('Formset added:', formsetName);
            if (formsetName === 'items') {
                console.log('New item row added');
                setupRow($row);
                calculateTotal();
            }
        });
        
        $(document).on('formset:removed', function(event, $row, formsetName) {
            console.log('Formset removed:', formsetName);
            if (formsetName === 'items') {
                console.log('Item row removed');
                calculateTotal();
            }
        });
        itemsContainer.on('change input', 'input, select', function() {
            calculateTotal();
        });
        setupInitialRows();
        calculateTotal();
    }
    
    function setupInitialRows() {
        const rows = itemsContainer.find('tr.form-row').not('.empty-form');
        rows.each(function() {
            setupRow($(this));
        });
    }
    
    function setupRow($row) {
        const inputs = $row.find('input, select');
        inputs.each(function() {
            const inputName = this.name;
            if (!attachedListeners.has(inputName)) {
                $(this).on('change input', function() {
                    calculateTotal();
                });
                attachedListeners.add(inputName);
            }
        });
    }
    
    function calculateTotal() {
        let total = 0;
        
        const rows = itemsContainer.find('tr.form-row').not('.empty-form');
       
        rows.each(function() {
            const $row = $(this);
            const quantityInput = $row.find('input[name$="-quantity"]');
            const priceInput = $row.find('input[name$="-price"]');
            const discountMethodSelect = $row.find('select[name$="-discount_method"]');
            const discountAmountInput = $row.find('input[name$="-discount_amount"]');
            const quantity = parseFloat(quantityInput.val()) || 0;
            const price = parseFloat(priceInput.val()) || 0;
            const discountMethod = discountMethodSelect.val() || 'amount';
            const discountAmount = parseFloat(discountAmountInput.val()) || 0;

            let unitPrice = price;
            let discountedUnitPrice = unitPrice;
            
            if (discountMethod === 'amount') {
                discountedUnitPrice = Math.max(unitPrice - discountAmount, 0);
            } else if (discountMethod === 'percentage') {
                const discountValue = unitPrice * (discountAmount / 100);
                discountedUnitPrice = Math.max(unitPrice - discountValue, 0);
            }
            
            const lineTotal = discountedUnitPrice * quantity;
           
            total += lineTotal;
        });

        const formattedTotal = total.toFixed(2);
        totalAmountDisplay.text(formattedTotal);
    }

    window.testInvoiceCalculation = function() {
        const testRow = itemsContainer.find('tr.form-row').not('.empty-form').first();
        if (testRow.length) {
            const quantityInput = testRow.find('input[name$="-quantity"]');
            const priceInput = testRow.find('input[name$="-price"]');
            quantityInput.val(2);
            priceInput.val(100);
            calculateTotal();
        } else {
            console.log('No rows available for test');
        }
    };
    const pollForNewItems = setInterval(function() {
        const currentRows = itemsContainer.find('tr.form-row').not('.empty-form');
        if (currentRows.length > 0) {
            clearInterval(pollForNewItems);
            setupInitialRows();
            calculateTotal();
        }
    }, 1000);

    setTimeout(function() {
        clearInterval(pollForNewItems);
    }, 10000);
});