from django import forms
from django.contrib import admin
from django.utils.safestring import mark_safe
from simple_history.admin import SimpleHistoryAdmin
from unfold.admin import ModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm
from import_export.admin import ImportExportModelAdmin

from product.models import Category, Product

@admin.register(Category)
class CategoryAdmin(SimpleHistoryAdmin, ModelAdmin, ImportExportModelAdmin):
    list_display = ('name', 'description', 'profit_margin')
    search_fields = ('name', 'description')
    list_filter = ('profit_margin',)
    list_per_page = 20  
    import_form_class = ImportForm
    export_form_class = ExportForm

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
class ProductAdmin(SimpleHistoryAdmin, ModelAdmin, ImportExportModelAdmin):
    form = ProductAdminForm
    list_display = ('name', 'category', 'description', 'profit_margin')
    search_fields = ('name', 'description', 'category__name')
    list_filter = ('category', 'profit_margin',)
    fields = ('name', 'description', 'category', 'profit_margin')
    list_per_page = 20
    import_form_class = ImportForm
    export_form_class = ExportForm