from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum, F

from sale_invoice.models import SalesInvoice
from .serializers import TotalReceivablesSerializer

class TotalReceivablesView(APIView):
    def get(self, request):
        total = SalesInvoice.objects.aggregate(
            total_receivables=Sum(F('total_amount') - F('paid_amount'))
        )

        result = {'total_receivables': total['total_receivables'] or 0}
        
        serializer = TotalReceivablesSerializer(result)
        return Response(serializer.data)