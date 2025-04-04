from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventory"

    def ready(self):
        import inventory.signals.receipt_signals
        import inventory.signals.stock_transfer_signals
        import inventory.signals.purchase_signals
        import inventory.signals.sale_signals