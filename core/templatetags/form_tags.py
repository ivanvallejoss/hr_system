from django import template

register = template.Library()

@register.filter
def add_class(field, css_class):
    """
    agrega una clase CSS a un campo de formulario 
    Uso: {{ form.username|add_class:"form-control" }}
    """
    if hasattr(field, 'as_widget'):
        return field.as_widget(attrs={'class': css_class})
    return field
    