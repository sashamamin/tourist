from kivy.properties import ListProperty

from kivymd.uix.screen import MDScreen
from kivymd.uix.list import OneLineAvatarIconListItem, IconLeftWidget, IconRightWidget
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel

from data.data_manager import DataManager


class FavoriteListItem(OneLineAvatarIconListItem):
    place_id = None


class FavoritesScreen(MDScreen):
    favorites = ListProperty()

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.data_manager = DataManager.get_instance()
        self.load_favorites()

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self.load_favorites()

    def load_favorites(self):
        self.favorites = self.data_manager.get_favorite_places()

        # --- Блок коллекций ---
        collections_box = self.ids.get("collections_box")
        if collections_box:
            collections_box.clear_widgets()
            # Считаем избранные по категориям
            counts = {"food": 0, "museum": 0, "sight": 0, "other": 0}
            for place in self.favorites:
                cat = place.get("category") or "other"
                if cat not in counts:
                    cat = "other"
                counts[cat] += 1

            def add_collection_card(title, icon_emoji, count):
                if count <= 0:
                    return
                card = MDCard(
                    orientation="vertical",
                    padding=(8, 8),
                    radius=[12, 12, 12, 12],
                    size_hint=(None, None),
                    size=(140, 70),
                )
                title_label = MDLabel(
                    text=f"{icon_emoji} {title}",
                    theme_text_color="Primary",
                )
                count_label = MDLabel(
                    text=f"({count})",
                    theme_text_color="Secondary",
                )
                box = MDBoxLayout(orientation="vertical")
                box.add_widget(title_label)
                box.add_widget(count_label)
                card.add_widget(box)
                collections_box.add_widget(card)

            add_collection_card("Рестораны", "🍽️", counts["food"])
            add_collection_card("Музеи", "🎨", counts["museum"])
            add_collection_card("Места", "📍", counts["sight"] + counts["other"])

        # --- Список избранных ---
        container = self.ids.get("favorites_list")
        if not container:
            return
        container.clear_widgets()
        for place in self.favorites:
            item = FavoriteListItem(text=place["name"])
            item.place_id = place["id"]
            icon = IconLeftWidget(icon="heart")
            icon.bind(on_release=lambda x, pid=place["id"]: self.remove_from_favorites(pid))
            item.add_widget(icon)
            map_icon = IconRightWidget(icon="map-marker")
            map_icon.bind(on_release=lambda x, pid=place["id"]: self.show_on_map(pid))
            item.add_widget(map_icon)
            # Нажатие по строке тоже показывает место на карте
            item.bind(on_release=lambda x, pid=place["id"]: self.show_on_map(pid))
            container.add_widget(item)

    def remove_from_favorites(self, place_id):
        self.data_manager.remove_favorite(place_id)
        self.load_favorites()

        # Обновляем экран мест, чтобы сердечки там тоже обновились
        try:
            from kivy.app import App

            app = App.get_running_app()
            root = app.sm.get_screen("root")
            places_screen = root.ids.get("places_screen")
            if places_screen:
                places_screen.load_places()
        except Exception:
            pass

    def show_on_map(self, place_id):
        """Переключает вкладку на карту и показывает только выбранное место."""
        from kivy.app import App

        app = App.get_running_app()
        sm = app.root
        root = sm.get_screen("root")
        bottom_nav = root.ids.get("bottom_nav")
        if bottom_nav:
            # Пытаемся использовать switch_tab, если есть, иначе current
            if hasattr(bottom_nav, "switch_tab"):
                bottom_nav.switch_tab("map")
            else:
                bottom_nav.current = "map"
        map_screen = root.ids.get("map_screen")
        if map_screen:
            # Показываем только выбранное место на карте
            try:
                map_screen.show_route([place_id])
            except Exception:
                # На случай, если метод недоступен, хотя бы сфокусируемся на месте
                map_screen.focus_on_place_by_id(place_id)
