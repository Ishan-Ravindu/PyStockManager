from django.urls import path
from .views import ShopListCreateView, ShopDetailView, WarehouseListView, StoreListView

urlpatterns = [
    path('', ShopListCreateView.as_view(), name='shop-list'),
    path('<int:pk>/', ShopDetailView.as_view(), name='shop-detail'),
    path('warehouses/', WarehouseListView.as_view(), name='warehouse-list'),
    path('stores/', StoreListView.as_view(), name='store-list'),
]