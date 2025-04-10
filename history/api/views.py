from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.apps import apps
from simple_history.models import HistoricalRecords
from django.db.models import Q
from itertools import chain
from django.utils import timezone
import datetime
from .serializers import GenericHistorySerializer
from rest_framework.permissions import IsAuthenticated


class RecentHistoryChangesAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """
        Get recent history changes across ALL registered models with simple_history.
        
        Query params:
        - days: Number of days to look back (default: 7)
        - limit: Maximum number of records to return (default: 100)
        - user_id: Filter by specific user (optional)
        """
        # Get query parameters
        days = int(request.query_params.get('days', 7))
        limit = int(request.query_params.get('limit', 100))
        user_id = request.query_params.get('user_id', None)
        
        # Calculate the date range
        end_date = timezone.now()
        start_date = end_date - datetime.timedelta(days=days)
        
        # Get all models with history - automatically scans the entire project
        models_with_history = []
        for model in apps.get_models():
            if hasattr(model, 'history'):
                models_with_history.append(model)
        
        # Query history for each model
        all_history = []
        for model in models_with_history:
            history_model = model.history.model
            
            # Build query
            query = Q(history_date__gte=start_date) & Q(history_date__lte=end_date)
            
            if user_id:
                query &= Q(history_user_id=user_id)
                
            # Get history records for the model
            history_records = history_model.objects.filter(query).order_by('-history_date')
            all_history.extend(history_records)
        
        # Sort all history by history_date (descending) to get latest changes first
        all_history.sort(key=lambda x: x.history_date, reverse=True)
        
        # Apply the limit
        all_history = all_history[:limit]
        
        # Serialize the data
        serializer = GenericHistorySerializer(all_history, many=True)
        
        return Response({
            "count": len(all_history),
            "results": serializer.data
        })