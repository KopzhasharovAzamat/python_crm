# inventory/templatetags/pagination_tags.py

from django import template

register = template.Library()


@register.simple_tag
def querystring(get_params, **kwargs):
    """
    Формирует строку GET-параметров, заменяя или добавляя новые параметры из kwargs.
    """
    # Создаем копию GET-параметров
    params = get_params.copy()

    # Удаляем старый параметр 'page', если он есть
    if 'page' in params:
        params.pop('page')

    # Добавляем новый параметр 'page' из kwargs
    for key, value in kwargs.items():
        params[key] = value

    # Формируем строку запроса
    return params.urlencode()