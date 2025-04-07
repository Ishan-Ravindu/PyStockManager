from django.apps import AppConfig


class PurchaseInvoiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "purchase_invoice"

    def ready(self):
        import purchase_invoice.signals
