from django.contrib import messages
from django.urls import reverse
from django.utils.html import format_html

class PDFViewMixin:
    def get_pdf_button(self, obj, url_name, button_text="View PDF"):
        if obj and obj.id:
            url = reverse(url_name, args=[obj.id])
            return format_html(
                '<a class="button" href="{}" target="_blank"><i class="fa fa-file-pdf"></i> {}</a>',
                url, button_text
            )
        return "-"

class MessageMixin:
    def display_error(self, request, message):
        messages.error(request, message)

    def display_success(self, request, message):
        messages.success(request, message)
