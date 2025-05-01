# views.py
from rest_framework import generics, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from shop.models import Shop
from .serializers import ShopSerializer

class ShopListCreateView(generics.ListCreateAPIView):
    """
    API endpoint that allows shops to be viewed or created.
    """
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['name', 'code', 'is_warehouse']
    search_fields = ['name', 'code', 'location']
    ordering_fields = ['name', 'code']

class ShopDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API endpoint that allows a specific shop to be viewed, updated, or deleted.
    """
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    permission_classes = [IsAuthenticated]

class WarehouseListView(generics.ListAPIView):
    """
    API endpoint that allows all warehouses to be viewed.
    """
    queryset = Shop.objects.filter(is_warehouse=True)
    serializer_class = ShopSerializer
    permission_classes = [IsAuthenticated]

class StoreListView(generics.ListAPIView):
    """
    API endpoint that allows all stores (non-warehouses) to be viewed.
    """
    queryset = Shop.objects.filter(is_warehouse=False)
    serializer_class = ShopSerializer
    permission_classes = [IsAuthenticated]