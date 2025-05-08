from rest_framework import serializers
from payment.models import Payment
from account.models import Account
from purchase_invoice.models import PurchaseInvoice
from expense.models import Expense

class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ['id', 'name']

class PurchaseInvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurchaseInvoice
        fields = ['id', 'shop']

class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ['id', 'name', 'description']

class PaymentSerializer(serializers.ModelSerializer):
    account = AccountSerializer()
    payable_object = serializers.SerializerMethodField()
    payment_type = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id',
            'amount',
            'account',
            'payment_date',
            'payment_type',
            'object_id',
            'payable_object'
        ]

    def get_payment_type(self, obj):
        return obj.content_type.model if obj.content_type else None

    def get_payable_object(self, obj):
        if obj.content_type and obj.object_id:
            model_name = obj.content_type.model
            if model_name == 'purchaseinvoice':
                try:
                    invoice = PurchaseInvoice.objects.get(id=obj.object_id)
                    return PurchaseInvoiceSerializer(invoice).data
                except PurchaseInvoice.DoesNotExist:
                    return None
            elif model_name == 'expense':
                try:
                    expense = Expense.objects.get(id=obj.object_id)
                    return ExpenseSerializer(expense).data
                except Expense.DoesNotExist:
                    return None
        return None
