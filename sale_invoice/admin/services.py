class InvoiceService:
    @staticmethod
    def get_remaining_amount(invoice, current_receipt=None):
        if not invoice:
            return 0
        remaining = invoice.total_amount - invoice.paid_amount
        if current_receipt and current_receipt.pk:
            remaining += current_receipt.amount
        return remaining

    @staticmethod
    def can_edit_invoice(invoice):
        return not (invoice and invoice.receipts.exists())

    @staticmethod
    def can_delete_invoice(invoice):
        return not (invoice and invoice.receipts.exists())

    @staticmethod
    def get_receipt_list_display(invoice):
        if not invoice or not invoice.receipts.exists():
            return "No receipts"
        receipts = invoice.receipts.all()
        receipt_list = ", ".join([str(r.id) for r in receipts[:5]])
        if receipts.count() > 5:
            receipt_list += f" (and {receipts.count() - 5} more)"
        return receipt_list
