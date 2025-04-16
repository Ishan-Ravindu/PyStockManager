from django.urls import path
from .views import get_object_options

urlpatterns = [
    path('get-object-options/', get_object_options, name='get_object_options'),
]
