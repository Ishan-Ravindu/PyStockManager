from django.urls import path

from inventory.api.views import InventoryValueAPI, StockAPI

urlpatterns = [
    path('stock/', StockAPI.as_view(), name='stock-api'),
    path('inventory-value/', InventoryValueAPI.as_view(), name='inventory-value-api'),
]