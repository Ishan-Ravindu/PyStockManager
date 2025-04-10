from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from shop.models import Shop

@admin.register(Shop)
class ShopAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'code', 'location', 'is_warehouse')
    list_filter = ('is_warehouse',)
    search_fields = ('name', 'location')
    list_per_page = 20