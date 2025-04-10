from django.urls import path
from .views import TotalAccountBalanceView

urlpatterns = [
    path('total-balance/', TotalAccountBalanceView.as_view(), name='total-account-balance'),
]