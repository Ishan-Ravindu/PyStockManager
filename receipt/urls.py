from django.urls import path
from . import views

urlpatterns = [
    path('receipt/<int:receipt_id>/pdf/', views.generate_receipt_pdf, name='generate_receipt_pdf'),
]