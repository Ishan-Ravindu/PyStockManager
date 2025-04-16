from io import BytesIO
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.core.validators import RegexValidator

def render_to_pdf(template_src, context_dict={}):
    """Generate PDF from HTML template"""
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

phone_regex = RegexValidator(
    regex=r'^0\d{9}$',
    message="Phone number must be in the format: '0XXXXXXXXX'. Exactly 10 digits starting with 0."
)

def invoice_number(input_string, number, padding=4):
    """
    Formats a string and number with zero padding in between for invoice numbering.
    
    Args:
        input_string (str): The string prefix for the invoice
        number (int): The invoice number to append
        padding (int, optional): Number of zeros to pad. Defaults to 4.
    
    Returns:
        str: Formatted invoice number in the pattern "string0000number"
    """
    number_str = str(number)
    zeros = '0' * (padding - len(number_str)) if len(number_str) < padding else ''
    result = f"{input_string}{zeros}{number}"    
    return result