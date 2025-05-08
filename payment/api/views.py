from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework.response import Response
from rest_framework import status
from django.db import models

from payment.models import Payment
from .serializers import PaymentSerializer
from .filters import PaymentFilter

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all().select_related('content_type', 'account')
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_class = PaymentFilter
    ordering_fields = ['payment_date', 'amount']
    search_fields = ['id', 'amount']

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        # Pagination (if any)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page or queryset, many=True)

        # Total payment amount of filtered results
        total_amount = queryset.aggregate(total=models.Sum('amount'))['total'] or 0

        response_data = {
            'total_amount': total_amount,
            'count': queryset.count(),
            'results': serializer.data if page is None else serializer.data
        }

        if page is not None:
            return self.get_paginated_response(response_data)

        return Response(response_data, status=status.HTTP_200_OK)

