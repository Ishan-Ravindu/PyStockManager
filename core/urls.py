from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', include('home.urls')),    
    path('receipt/', include('receipt.urls')),
    path('sale_invoice/', include('sale_invoice.urls')),
    path('admin/payment/', include('payment.urls')),
    # api paths
    path('api/purchase_invoice/', include('purchase_invoice.api.urls')),
    path('api/account/', include('account.api.urls')),
    path('api/sale_invoice/', include('sale_invoice.api.urls')),
    path('api/inventory/', include('inventory.api.urls')),
    path('api/history/', include('history.api.urls')),
]
