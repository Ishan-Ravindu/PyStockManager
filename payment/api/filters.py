import django_filters

from payment.models import Payment

class PaymentFilter(django_filters.FilterSet):
    payment_date = django_filters.DateFromToRangeFilter()
    payment_type = django_filters.CharFilter(field_name='content_type__model', lookup_expr='iexact')

    class Meta:
        model = Payment
        fields = ['account', 'payment_date', 'payment_type']
