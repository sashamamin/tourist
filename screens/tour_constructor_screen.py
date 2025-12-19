from kivy.properties import StringProperty

from kivymd.uix.screen import MDScreen

from data.data_manager import DataManager


class TourConstructorScreen(MDScreen):
    """Базовый конструктор маршрутов: выбор темы и длительности, генерация простого тура.

    MVP: просто фильтрует места по категории и создаёт короткий список.
    """

    selected_theme = StringProperty("history")
    selected_duration = StringProperty("short")  # short / medium / long
    route_title = StringProperty("Мой маршрут")
    summary_text = StringProperty("")

    def set_theme(self, theme):
        self.selected_theme = theme

    def set_duration(self, duration):
        self.selected_duration = duration

    def generate_route(self):
        """Пример генерации маршрута: выбираем N мест и показываем их в списке.

        В полноценной версии можно сохранять как пользовательский тур.
        """
        ids = self.ids
        container = ids.get("constructor_result_list")
        if not container:
            return
        container.clear_widgets()

        dm = DataManager.get_instance()
        places = dm.get_all_places()

        # Простая фильтрация по теме -> категориям мест
        theme_map = {
            "history": ["sight", "museum"],
            "food": ["food"],
            "art": ["museum"],
            "fun": ["entertainment"],
            "nature": ["park"],
        }
        categories = theme_map.get(self.selected_theme, [])
        if categories:
            places = [p for p in places if (p.get("category") in categories)]

        # Кол-во точек по длительности
        if self.selected_duration == "short":
            limit = 3
        elif self.selected_duration == "medium":
            limit = 6
        else:
            limit = 10

        places = places[:limit]

        from kivy.app import App
        app = App.get_running_app()
        
        theme_titles = {
            "history": app.get_text("theme_history"),
            "food": app.get_text("theme_food"),
            "art": app.get_text("theme_art"),
            "fun": "Развлечения",
            "nature": "Прогулка на природе",
        }
        duration_titles = {
            "short": app.get_text("duration_1h"),
            "medium": app.get_text("duration_2_3h"),
            "long": app.get_text("duration_full_day"),
        }
        self.route_title = theme_titles.get(self.selected_theme, "Мой маршрут")

        from kivymd.uix.list import TwoLineListItem

        for idx, place in enumerate(places, start=1):
            title = f"{idx}. {place['name']}"
            subtitle = place.get("short_desc") or place.get("address") or ""
            item = TwoLineListItem(text=title, secondary_text=subtitle)
            container.add_widget(item)

        count = len(places)
        duration_label = duration_titles.get(self.selected_duration, "")
        if count:
            self.summary_text = app.get_text("route_summary").format(count, duration_label)
        else:
            self.summary_text = app.get_text("route_no_places")
