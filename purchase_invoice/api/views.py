from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from django.db.models import Sum, F
from ..models import PurchaseInvoice
from .serializers import PurchaseInvoiceSerializer, TotalPayableSerializer

class TotalPayableAmountView(APIView):
    def get(self, request):
        total_payable = PurchaseInvoice.objects.aggregate(
            payable=Sum(F('total_amount') - F('paid_amount'))
        )
        result = {'total_payable': total_payable['payable'] or 0}
        serializer = TotalPayableSerializer(result)
        return Response(serializer.data)

class PurchaseInvoiceListAPIView(APIView):
    def get(self, request):
        invoices = PurchaseInvoice.objects.all()
        serializer = PurchaseInvoiceSerializer(invoices, many=True)
        return Response(serializer.data)
