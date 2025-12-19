"""Утилиты для обновления текстов при смене языка."""
from kivy.app import App


def update_widget_texts(widget, text_map):
    """Рекурсивно обновляет тексты виджетов по карте ключей."""
    app = App.get_running_app()
    
    # Обновляем текст самого виджета, если есть ключ
    if hasattr(widget, 'text') and hasattr(widget, 'id') and widget.id:
        if widget.id in text_map:
            widget.text = app.get_text(text_map[widget.id])
    
    # Рекурсивно обновляем дочерние виджеты
    if hasattr(widget, 'children'):
        for child in widget.children:
            update_widget_texts(child, text_map)
    
    # Для MDTopAppBar обновляем title
    if hasattr(widget, 'title') and hasattr(widget, 'id') and widget.id:
        if widget.id in text_map:
            widget.title = app.get_text(text_map[widget.id])
    
    # Для MDTextField обновляем hint_text
    if hasattr(widget, 'hint_text') and hasattr(widget, 'id') and widget.id:
        if widget.id in text_map:
            widget.hint_text = app.get_text(text_map[widget.id])

