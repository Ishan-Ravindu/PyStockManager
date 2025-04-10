from django.urls import path
from .views import RecentHistoryChangesAPIView

urlpatterns = [
    path('recent-history/', RecentHistoryChangesAPIView.as_view(), name='recent-history'),
]