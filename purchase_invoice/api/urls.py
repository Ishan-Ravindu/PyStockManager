from django.urls import path
from .views import TotalPayableAmountView

urlpatterns = [
    path('total-payable/', TotalPayableAmountView.as_view(), name='total-payable-amount'),
]