from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from expence.models import Expense


@admin.register(Expense)
class ExpenseAdmin(SimpleHistoryAdmin):
    list_display = ('id', 'name')
    search_fields = ('name', 'description')
