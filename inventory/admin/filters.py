from django.contrib.admin import SimpleListFilter
from django.db.models import F


class QuantityRangeFilter(SimpleListFilter):
    title = 'quantity range'
    parameter_name = 'quantity_range'

    def lookups(self, request, model_admin):
        return (
            ('0', 'Empty stock (0)'),
            ('1-10', 'Low stock (1-10)'),
            ('11-50', 'Medium stock (11-50)'),
            ('51-100', 'High stock (51-100)'),
            ('101+', 'Very high stock (101+)'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == '0':
            return queryset.filter(quantity=0)
        elif value == '1-10':
            return queryset.filter(quantity__range=(1, 10))
        elif value == '11-50':
            return queryset.filter(quantity__range=(11, 50))
        elif value == '51-100':
            return queryset.filter(quantity__range=(51, 100))
        elif value == '101+':
            return queryset.filter(quantity__gte=101)
        return queryset


class PriceComparisonFilter(SimpleListFilter):
    title = 'price comparison'
    parameter_name = 'price_comparison'

    def lookups(self, request, model_admin):
        return (
            ('profit_positive', 'Profitable (Selling > Cost)'),
            ('profit_negative', 'Loss (Selling < Cost)'),
            ('profit_neutral', 'Break-even (Selling = Cost)'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        if value == 'profit_positive':
            return queryset.filter(selling_price__gt=F('average_cost'))
        elif value == 'profit_negative':
            return queryset.filter(selling_price__lt=F('average_cost'))
        elif value == 'profit_neutral':
            return queryset.filter(selling_price=F('average_cost'))
        return queryset
