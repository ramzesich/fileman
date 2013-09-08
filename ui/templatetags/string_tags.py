from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@stringfilter
@register.filter
def lstrip(value, arg):
    args = arg.split()
    if len(args) != 1:
        return value
    return value.lstrip(args[0])
