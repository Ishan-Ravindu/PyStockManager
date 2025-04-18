document.addEventListener('DOMContentLoaded', function() {
    if (typeof window.django !== 'undefined' && typeof window.django.jQuery === 'function') {
        initializeCustomerDueDateHandler(window.django.jQuery);
    } else if (typeof window.jQuery === 'function') {
        initializeCustomerDueDateHandler(window.jQuery);
    } else {
        console.error('jQuery not found for customer-due-date handler');
    }
});

function initializeCustomerDueDateHandler($) {
    const customerField = $('#id_customer');
    const dueDateField = $('#id_due_date');
    
    if (customerField.length === 0 || dueDateField.length === 0) {
        console.log('Required fields not found for customer-due-date handler');
        return;
    }

    customerField.on('change', function() {
        const customerId = $(this).val();
        if (customerId) {
            console.log('Customer changed to ID:', customerId);
            fetchCustomerDetails(customerId);
        }
    });

    function fetchCustomerDetails(customerId) {
        fetch(`/api/customer/${customerId}/`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`API request failed with status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            updateDueDate(data.credit_period);
        })
        .catch(error => {
            console.error('Error fetching customer details:', error);
        });
    }

    function updateDueDate(creditPeriod) {
        const today = new Date();
        const creditDays = parseInt(creditPeriod || 0);
        console.log('Updating due date with credit period of', creditDays, 'days');
        const dueDate = new Date(today);
        dueDate.setDate(today.getDate() + creditDays);
        const formattedDate = formatDate(dueDate);
        console.log('Setting due date to:', formattedDate);
        dueDateField.val(formattedDate);
        dueDateField.trigger('change');
    }
    function formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        
        return `${year}-${month}-${day}`;
    }
}