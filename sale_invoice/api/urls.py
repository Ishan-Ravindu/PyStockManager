from django.urls import path
from .views import TotalReceivablesView

urlpatterns = [
    path('total-receivables/', TotalReceivablesView.as_view(), name='total-receivables'),
]