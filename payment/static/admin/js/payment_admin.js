document.addEventListener('DOMContentLoaded', function() {
    function toggleRelatedFields() {
        const contentTypeSelect = document.getElementById('id_content_type');
        if (!contentTypeSelect) return;
        const purchaseInvoiceContainer = document.querySelector('.field-purchase_invoice');
        const expenseContainer = document.querySelector('.field-expense');
        if (purchaseInvoiceContainer) purchaseInvoiceContainer.classList.remove('active');
        if (expenseContainer) expenseContainer.classList.remove('active');
        const selectedOption = contentTypeSelect.options[contentTypeSelect.selectedIndex];
        if (selectedOption) {
            const selectedModel = selectedOption.text.toLowerCase();
            
            if (selectedModel.includes('purchase') && purchaseInvoiceContainer) {
                purchaseInvoiceContainer.classList.add('active');
            } else if (selectedModel.includes('expense') && expenseContainer) {
                expenseContainer.classList.add('active');
            }
        }
    }
    toggleRelatedFields();
    const contentTypeSelect = document.getElementById('id_content_type');
    if (contentTypeSelect) {
        contentTypeSelect.addEventListener('change', toggleRelatedFields);
    }
});