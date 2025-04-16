from django.urls import path
from .views import PurchaseInvoiceListAPIView, TotalPayableAmountView

urlpatterns = [
    path('total-payable/', TotalPayableAmountView.as_view(), name='total-payable-amount'),
    path('', PurchaseInvoiceListAPIView.as_view(), name='purchase-invoice'),
]