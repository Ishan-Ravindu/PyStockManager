from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', include('home.urls')),    
    path('receipt/', include('receipt.urls')),
    path('api/inventory/', include('inventory.api.urls')),
    path('sale_invoice/', include('sale_invoice.urls')),
]
