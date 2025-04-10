from django import forms
from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.shortcuts import redirect
from django.forms import ValidationError
from django.utils import timezone
from django.forms.models import BaseInlineFormSet
from simple_history.admin import SimpleHistoryAdmin

from sale_invoice.models import SalesInvoice, SalesInvoiceItem

# ========== Validators ==========

class CustomerValidator:
    """Validator class for customer-related validations"""
    
    @staticmethod
    def validate_blacklist(customer):
        """Validate that customer is not blacklisted"""
        if customer and customer.black_list:
            raise ValidationError("Cannot create an invoice for a blacklisted customer.")
            
    @staticmethod
    def validate_due_date(due_date, customer, today=None):
        """Validate due date based on customer credit period"""
        if not due_date or not customer:
            return
            
        if today is None:
            today = timezone.now().date()
            
        if due_date < today:
            raise ValidationError("Due date cannot be earlier than today.")
        
        max_credit_date = today + timezone.timedelta(days=customer.credit_period)
        if due_date > max_credit_date:
            raise ValidationError(
                f"Due date cannot exceed customer credit period ({customer.credit_period} days)."
            )


class InventoryValidator:
    """Validator class for inventory-related validations"""
    
    @staticmethod
    def validate_stock_quantity(product, quantity, shop):
        """Validate that quantity doesn't exceed available stock"""
        if not all([product, quantity, shop]):
            return
            
        try:
            stock = product.stock_set.get(shop=shop)
            if quantity > stock.quantity:
                raise ValidationError(
                    f"Quantity cannot exceed available stock ({stock.quantity})."
                )
        except product.stock_set.model.DoesNotExist:
            raise ValidationError(f"No stock available for this product in {shop.name}.")


class InvoiceValidator:
    """Validator class for invoice-related validations"""
    
    @staticmethod
    def validate_has_items(items_count):
        """Validate that invoice has at least one item"""
        if items_count == 0:
            raise ValidationError("Invoice must have at least one valid item.")
            
    @staticmethod
    def validate_can_edit(invoice):
        """Validate that invoice can be edited (no receipts)"""
        if invoice and invoice.receipts.exists():
            receipt_list = ", ".join([str(receipt.id) for receipt in invoice.receipts.all()[:5]])
            if invoice.receipts.count() > 5:
                receipt_list += f" (and {invoice.receipts.count() - 5} more)"
                
            raise ValidationError(
                f"Cannot edit Invoice #{invoice.id} ({invoice.shop.code}) because it has "
                f"linked receipts: {receipt_list}"
            )

# ========== Service Layer ==========

class InvoiceService:
    """Service class for invoice-related business logic"""
    
    @staticmethod
    def get_remaining_amount(invoice, current_receipt=None):
        """Calculate remaining unpaid amount for an invoice"""
        if not invoice:
            return 0
            
        remaining = invoice.total_amount - invoice.paid_amount
        
        # If editing an existing receipt, add back its amount
        if current_receipt and current_receipt.pk:
            remaining += current_receipt.amount
            
        return remaining
    
    @staticmethod
    def can_edit_invoice(invoice):
        """Check if an invoice can be edited"""
        return not (invoice and invoice.receipts.exists())
        
    @staticmethod
    def can_delete_invoice(invoice):
        """Check if an invoice can be deleted"""
        return not (invoice and invoice.receipts.exists())
        
    @staticmethod
    def get_receipt_list_display(invoice):
        """Generate receipt list for display in messages"""
        if not invoice or not invoice.receipts.exists():
            return "No receipts"
            
        receipts = invoice.receipts.all()
        receipt_list = ", ".join([str(receipt.id) for receipt in receipts[:5]])
        
        if receipts.count() > 5:
            receipt_list += f" (and {receipts.count() - 5} more)"
            
        return receipt_list


# ========== Form Classes ==========

class SalesInvoiceItemForm(forms.ModelForm):
    """Custom form for invoice items with stock validation"""
    
    class Meta:
        model = SalesInvoiceItem
        fields = '__all__'
    
    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get('product')
        quantity = cleaned_data.get('quantity')
        
        # Get shop from parent invoice if available
        shop = None
        if hasattr(self, 'parent_instance') and self.parent_instance and hasattr(self.parent_instance, 'shop'):
            shop = self.parent_instance.shop
        
        # Validate stock quantity
        if product and quantity and shop:
            try:
                InventoryValidator.validate_stock_quantity(product, quantity, shop)
            except ValidationError as e:
                self.add_error('quantity', e)
        
        return cleaned_data


class SalesInvoiceItemFormSet(BaseInlineFormSet):
    """Custom formset for invoice items"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = kwargs.get('instance')
        # Initialize tracking attributes that Django admin expects
        self._errors = None
        self.changed_objects = []
        self.deleted_objects = []
        self.new_objects = []
    
    def add_fields(self, form, index):
        super().add_fields(form, index)
        # Pass parent instance to form for validation
        form.parent_instance = self.instance
        
    def save_new(self, form, commit=True):
        """Save and return a new model instance for the given form."""
        obj = super().save_new(form, commit=commit)
        if commit:
            self.new_objects.append(obj)
        return obj
    
    def save_existing(self, form, instance, commit=True):
        """Save and return an existing model instance for the given form."""
        obj = super().save_existing(form, instance, commit=commit)
        if commit and instance not in self.changed_objects:
            self.changed_objects.append((instance, form.changed_data))
        return obj
    
    def save_deleted(self, obj):
        """Save the fact that obj was deleted."""
        if obj not in self.deleted_objects:
            self.deleted_objects.append(obj)
        super().save_deleted(obj)

class SalesInvoiceForm(forms.ModelForm):
    """Custom form for sales invoices with customer and due date validation"""
    
    class Meta:
        model = SalesInvoice
        fields = '__all__'
        exclude = ('created_at',)
    
    def clean(self):
        cleaned_data = super().clean()
        customer = cleaned_data.get('customer')
        due_date = cleaned_data.get('due_date')
        today = timezone.now().date()
        
        # Validate customer is not blacklisted
        try:
            CustomerValidator.validate_blacklist(customer)
        except ValidationError as e:
            self.add_error(None, e)  # Form-wide error
        
        # Validate due date
        if customer and due_date:
            try:
                CustomerValidator.validate_due_date(due_date, customer, today)
            except ValidationError as e:
                self.add_error('due_date', e)
        
        return cleaned_data


# ========== Mixins ==========

class PDFViewMixin:
    """Mixin for adding PDF view buttons to admin"""
    
    def get_pdf_button(self, obj, url_name, button_text="View PDF"):
        """Generate HTML for PDF view button"""
        if obj and obj.id:
            url = reverse(url_name, args=[obj.id])
            return format_html(
                '<a class="button" href="{}" target="_blank"><i class="fa fa-file-pdf"></i> {}</a>',
                url, button_text
            )
        return "-"


class MessageMixin:
    """Mixin for consistent message formatting"""
    
    def display_error(self, request, message):
        """Display consistent error message"""
        messages.error(request, message)
    
    def display_success(self, request, message):
        """Display consistent success message"""
        messages.success(request, message)


# ========== Inline Admin Classes ==========

class SalesInvoiceItemInline(admin.StackedInline):
    """Admin inline for invoice items"""
    model = SalesInvoiceItem
    form = SalesInvoiceItemForm
    formset = SalesInvoiceItemFormSet
    extra = 1
    
    def get_formset(self, request, obj=None, **kwargs):
        """Ensure formset is properly configured for Django admin"""
        FormSet = super().get_formset(request, obj, **kwargs)
        # Make sure our formset class has the required attributes
        if not hasattr(FormSet, 'new_objects'):
            FormSet.new_objects = []
        if not hasattr(FormSet, 'changed_objects'):
            FormSet.changed_objects = []
        if not hasattr(FormSet, 'deleted_objects'):
            FormSet.deleted_objects = []
        return FormSet

# ========== Admin Classes ==========

@admin.register(SalesInvoice)
class SalesInvoiceAdmin(SimpleHistoryAdmin, PDFViewMixin, MessageMixin):
    """Admin interface for sales invoices"""
    form = SalesInvoiceForm
    list_display = ('id', 'shop', 'customer', 'total_amount', 'paid_amount', 'created_at', 
                   'due_date', 'payment_status', 'add_receipt_button', 'view_receipts', 
                   'view_invoice_pdf')
    list_filter = ('shop', 'customer', 'created_at')
    search_fields = ('shop__name', 'customer__name')
    readonly_fields = ('total_amount', 'paid_amount', 'created_at')
    exclude = ('created_at',)
    inlines = [SalesInvoiceItemInline]
    list_per_page = 20
    actions = None
    
    def has_delete_permission(self, request, obj=None):
        """Control delete permission based on receipts"""
        if not InvoiceService.can_delete_invoice(obj):
            return False
        return super().has_delete_permission(request, obj)
   
    def save_model(self, request, obj, form, change):
        """Custom save behavior for invoices"""
        # Check if invoice has receipts before allowing edit
        if change:
            try:
                InvoiceValidator.validate_can_edit(obj)
            except ValidationError as e:
                self.display_error(request, str(e))
                return
        
        super().save_model(request, obj, form, change)
    
    def save_related(self, request, form, formsets, change):
        """Validate invoice has items before saving related objects"""
        # Count valid invoice items
        items_count = 0
        for formset in formsets:
            if formset.model == SalesInvoiceItem:
                for item_form in formset.forms:
                    if (item_form.is_valid() and 
                        not item_form.cleaned_data.get('DELETE', False) and
                        item_form.cleaned_data.get('product') and 
                        item_form.cleaned_data.get('quantity')):
                        items_count += 1
        
        # Validate invoice has at least one item
        try:
            InvoiceValidator.validate_has_items(items_count)
        except ValidationError as e:
            self.display_error(request, str(e))
            return
            
        super().save_related(request, form, formsets, change)
    
    def response_change(self, request, obj):
        """Custom response after invoice change"""
        if not InvoiceService.can_edit_invoice(obj):
            return redirect(reverse('admin:inventory_salesinvoice_changelist'))
        return super().response_change(request, obj)

    def delete_model(self, request, obj):
        """Custom delete behavior for invoices"""
        if not InvoiceService.can_delete_invoice(obj):
            receipt_list = InvoiceService.get_receipt_list_display(obj)
            self.display_error(
                request,
                f"Cannot delete Invoice #{obj.id} ({obj.shop.code}) because it has "
                f"linked receipts: {receipt_list}"
            )
            return
        
        invoice_ref = f"Invoice #{obj.id} ({obj.shop.code})"
        obj.delete()
        self.display_success(request, f"{invoice_ref} was deleted successfully")

    def response_delete(self, request, obj_display, obj_id):
        """Custom response after invoice deletion"""
        return redirect(reverse('admin:inventory_salesinvoice_changelist'))

    def add_receipt_button(self, obj):
        """Generate button for adding new receipt"""
        url = reverse('admin:receipt_receipt_add') + f'?invoice={obj.id}'
        return format_html('<a class="button" href="{}">Add Receipt</a>', url)
    add_receipt_button.short_description = 'Add Receipt'

    def view_receipts(self, obj):
        """Generate HTML for viewing receipts"""
        receipts = obj.receipts.all()
        if not receipts:
            return "No receipts"        
        
        links = []
        for receipt in receipts:
            url = reverse('admin:receipt_receipt_change', args=[receipt.id])
            links.append(f'<a href="{url}">{receipt.id}({receipt.amount})</a>')        
        
        return mark_safe(', '.join(links))
    view_receipts.short_description = 'Receipts history'

    def view_invoice_pdf(self, obj):
        """Generate PDF view button for invoice"""
        return self.get_pdf_button(obj, 'generate_invoice_pdf')
    view_invoice_pdf.short_description = 'Invoice PDF'
