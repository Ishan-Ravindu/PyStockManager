from django.db.models.signals import pre_save
from django.dispatch import receiver

from sale_invoice.models import SalesInvoiceItem
from sale_invoice.signals.logic.average_cost_logic import update_sales_invoice_item_average_cost

@receiver(pre_save, sender=SalesInvoiceItem)
def handle_sales_invoice_item_pre_save(sender, instance, **kwargs):
    update_sales_invoice_item_average_cost(instance)