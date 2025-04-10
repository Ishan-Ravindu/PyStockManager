from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Gets an item from a dictionary using a key.
    Usage: {{ mydict|get_item:key }}
    """
    return dictionary.get(key, '')