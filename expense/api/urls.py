from django.urls import path
from .views import ExpenseListAPIView

urlpatterns = [
    path('', ExpenseListAPIView.as_view(), name='purchase-invoice'),
]