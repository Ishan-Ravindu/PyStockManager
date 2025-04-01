from django.urls import path
from . import views

urlpatterns = [
    path('invoice/<int:invoice_id>/pdf/', views.generate_invoice_pdf, name='generate_invoice_pdf'),
    path('receipt/<int:receipt_id>/pdf/', views.generate_receipt_pdf, name='generate_receipt_pdf'),
]