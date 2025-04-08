from django.apps import AppConfig


class SaleInvoiceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sale_invoice"

    def ready(self):
        import sale_invoice.signals
