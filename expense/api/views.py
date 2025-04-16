from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from django.db.models import Sum, F

from expense.models import Expense
from .serializers import ExpenseSerializer

class ExpenseListAPIView(APIView):
    def get(self, request):
        expense = Expense.objects.all()
        serializer = ExpenseSerializer(expense, many=True)
        return Response(serializer.data)
