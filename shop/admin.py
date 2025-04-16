from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from django.core.exceptions import ValidationError
from django import forms

from shop.models import Shop

class ShopAdminForm(forms.ModelForm):
    class Meta:
        model = Shop
        fields = '__all__'
    
    def clean_code(self):
        code = self.cleaned_data.get('code')
        if code and (len(code) != 3 or not code.isalpha()):
            raise ValidationError('Code must be exactly 3 letters (A-Z or a-z).')
        return code

@admin.register(Shop)
class ShopAdmin(SimpleHistoryAdmin, ModelAdmin):
    form = ShopAdminForm
    list_display = ('name', 'code', 'location', 'is_warehouse')
    list_filter = ('is_warehouse',)
    search_fields = ('name', 'location')
    list_per_page = 20