from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path('', include('home.urls')),
    path('inventory/', include('inventory.urls')),
    path('api/inventory/', include('inventory.api.urls')),
]
