document.addEventListener('DOMContentLoaded', function() {
    const contentTypeField = document.getElementById('id_content_type');
    const objectIdField = document.getElementById('id_object_id');
    
    if (!contentTypeField || !objectIdField) {
        return;
    }
    
    const payableItemsMap = {};
    
    function initPayableItemsMap() {
        Array.from(contentTypeField.options).forEach(option => {
            if (!option.value) return;
            
            const optionText = option.text.toLowerCase();
            let items = [];
            
            if (optionText.includes('purchase') || optionText.includes('invoice')) {
                items = [
                    { id: '1', display: 'Invoice #1 - Vendor A - $100.00' },
                    { id: '2', display: 'Invoice #2 - Vendor B - $250.00' },
                    { id: '3', display: 'Invoice #3 - Vendor C - $175.50' }
                ];
            } else if (optionText.includes('expense')) {
                items = [
                    { id: '1', display: 'Expense #1 - Office Supplies - $45.99' },
                    { id: '2', display: 'Expense #2 - Travel - $320.75' },
                    { id: '3', display: 'Expense #3 - Equipment - $1,200.00' }
                ];
            }
            
            if (items.length > 0) {
                payableItemsMap[option.value] = items;
            }
        });
    }
    
    function updateObjectIdOptions() {
        const selectedContentTypeId = contentTypeField.value;
        
        while (objectIdField.options.length > 0) {
            objectIdField.remove(0);
        }
        
        const defaultOption = document.createElement('option');
        defaultOption.value = '';
        defaultOption.textContent = '---Select Item---';
        objectIdField.appendChild(defaultOption);
        
        // Disable the default option if no payment type is selected
        if (!selectedContentTypeId) {
            defaultOption.disabled = true;
            objectIdField.disabled = true;
            return;
        } else {
            defaultOption.disabled = false;
            objectIdField.disabled = false;
        }
        
        const items = payableItemsMap[selectedContentTypeId] || [];
        
        if (items.length > 0) {
            items.forEach(item => {
                const option = document.createElement('option');
                option.value = item.id;
                option.textContent = item.display;
                objectIdField.appendChild(option);
            });
        }
    }
    
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'value') {
                updateObjectIdOptions();
            }
        });
    });
    
    observer.observe(contentTypeField, { attributes: true });
    
    initPayableItemsMap();
    
    contentTypeField.addEventListener('change', function() {
        updateObjectIdOptions();
    });
    
    if (window.jQuery) {
        window.jQuery(contentTypeField).on('change', function() {
            updateObjectIdOptions();
        });
    }
    
    // Initial setup
    updateObjectIdOptions();
});