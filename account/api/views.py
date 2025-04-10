from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum

from account.models import Account
from .serializers import TotalBalanceSerializer

class TotalAccountBalanceView(APIView):
    def get(self, request):
        total = Account.objects.aggregate(total_balance=Sum('balance'))
        result = {'total_balance': total['total_balance'] or 0}
        
        serializer = TotalBalanceSerializer(result)
        return Response(serializer.data)