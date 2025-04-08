from django.contrib import admin

from shop.models import Shop

@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'location', 'is_warehouse')
    list_filter = ('is_warehouse',)
    search_fields = ('name', 'location')
    list_per_page = 20