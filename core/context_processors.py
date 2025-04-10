def jazzmin_settings(request):
    """
    Add hidden_app_names and app_custom_names to the context for Jazzmin templates.
    """

    hidden_app_names = ['Product', 'Payment', 'Receipt', 'Supplier', 'Customer']

    app_custom_names = {       
        'Product': 'Inventory',
        'Purchase_Invoice': 'Purchase Invoice',
        'Sale_Invoice': 'Sale Invoice',
        'Shop': 'Entity'
    }
    
    return {
        'hidden_app_names': hidden_app_names,
        'app_custom_names': app_custom_names,
    }