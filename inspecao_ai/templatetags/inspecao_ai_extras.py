from django import template


register = template.Library()


@register.filter
def split_lines(value):
    texto = str(value or "")
    return [linha.strip() for linha in texto.splitlines() if linha.strip()]
