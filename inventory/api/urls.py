from django.urls import path

from inventory.api.views import StockAPI

urlpatterns = [
    path('stock/', StockAPI.as_view(), name='stock-api'),
]