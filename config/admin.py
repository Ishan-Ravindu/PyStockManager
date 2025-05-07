from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import User, Group

from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.admin import ModelAdmin


admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'user_permissions' in form.base_fields:
            field = form.base_fields['user_permissions']
            field.queryset = field.queryset.exclude(
                content_type__model__startswith='historical'
            )
        return form


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if 'permissions' in form.base_fields:
            field = form.base_fields['permissions']
            field.queryset = field.queryset.exclude(
                content_type__model__startswith='historical'
            )
        return form
