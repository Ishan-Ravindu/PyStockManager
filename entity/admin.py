from django import forms
from django.contrib import admin
from django.utils.safestring import mark_safe

from entity.models import Category, Customer, Product, Supplier

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'mobile_number', 'payable')
    search_fields = ('name', 'mobile_number')
    readonly_fields = ('payable',)
    list_per_page = 20

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'mobile_number', 'address', 'credit', 'credit_limit', 
                   'credit_period', 'combined_status', 'black_list')
    list_filter = ('credit_period', 'black_list')
    search_fields = ('name', 'mobile_number')
    readonly_fields = ('credit',)
    list_per_page = 20
    
    fieldsets = (
        (None, {
            'fields': ('name', 'mobile_number', 'address')
        }),
        ('Credit Information', {
            'fields': ('credit', 'credit_limit', 'credit_period', 'black_list')
        }),
    )

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'profit_margin')
    search_fields = ('name', 'description')
    list_filter = ('profit_margin',)
    list_per_page = 20  

class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        categories = Category.objects.all()
        categories_profit_margins = {}
        for category in categories:
            categories_profit_margins[category.id] = str(category.profit_margin)
        js_code = """
        <script>
        var categoryProfitMargins = {};
        """
        for cat_id, margin in categories_profit_margins.items():
            js_code += f"categoryProfitMargins[{cat_id}] = '{margin}';\n"
        js_code += """
        // Function to update profit margin when category changes
        function handleCategoryChange() {
            var allSelects = document.querySelectorAll('select');
            var categorySelect = null;
            for (var i = 0; i < allSelects.length; i++) {
                if (allSelects[i].name && allSelects[i].name.includes('category')) {
                    categorySelect = allSelects[i];
                    break;
                }
            }            
            if (!categorySelect) return;
            var categoryId = categorySelect.value;
            var allInputs = document.querySelectorAll('input');
            var profitMarginInput = null;            
            for (var i = 0; i < allInputs.length; i++) {
                if (allInputs[i].name && allInputs[i].name.includes('profit_margin')) {
                    profitMarginInput = allInputs[i];
                    break;
                }
            }            
            if (!profitMarginInput) return;
            if (categoryId && categoryProfitMargins[categoryId]) {
                profitMarginInput.value = categoryProfitMargins[categoryId];
                profitMarginInput.style.backgroundColor = '#ffffcc';
                setTimeout(function() {
                    profitMarginInput.style.backgroundColor = '';
                }, 1000);
            }
        }
        window.addEventListener('load', function() {
            var allSelects = document.querySelectorAll('select');            
            for (var i = 0; i < allSelects.length; i++) {
                if (allSelects[i].name && allSelects[i].name.includes('category')) {
                    allSelects[i].addEventListener('change', handleCategoryChange);
                    allSelects[i].setAttribute('onchange', 'handleCategoryChange()');
                }
            }
        });
        </script>
        """
        self.fields['category'].help_text = mark_safe(
            "<strong></strong>" + js_code
        )
        self.fields['profit_margin'].help_text = mark_safe(
            "<strong style='color: #336699;'>Add a manual profit margin if you want to use a product-specific profit margin</strong>"
        )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductAdminForm
    list_display = ('name', 'category', 'description', 'profit_margin')
    search_fields = ('name', 'description')
    fields = ('name', 'description', 'category', 'profit_margin')
    list_per_page = 20