from kivy.properties import ListProperty, StringProperty
from kivy.clock import Clock
from kivy.uix.image import AsyncImage

from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDIconButton

from data.data_manager import DataManager
from utils.notifications import show_success, haptic_feedback


class PlacesScreen(MDScreen):
    places = ListProperty()
    search_query = StringProperty("")
    selected_category = StringProperty("")  # '', 'sight', 'food', 'museum', ...
    sort_mode = StringProperty("rating")

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.data_manager = DataManager.get_instance()
        self.load_places()

    def get_title(self):
        from kivy.app import App
        app = App.get_running_app()
        
        city = None
        try:
            city = self.data_manager.get_active_city()
        except Exception:
            city = None
        if city and city.get("name"):
            return f"{app.get_text('tab_places')} — {city['name']}"
        return app.get_text("tab_places")
    
    def _update_static_texts(self):
        """Обновляет статические тексты при смене языка."""
        from kivy.app import App
        app = App.get_running_app()
        
        try:
            # Обновляем TopAppBar
            if hasattr(self, 'ids') and 'places_topbar' in self.ids:
                self.ids.places_topbar.title = self.get_title()
            
            # Обновляем hint_text в поиске
            if hasattr(self, 'ids') and 'places_search_field' in self.ids:
                self.ids.places_search_field.hint_text = app.get_text("places_search_hint")
            
            # Обновляем кнопки фильтров
            if hasattr(self, 'ids'):
                if 'filter_all_btn' in self.ids:
                    self.ids.filter_all_btn.text = app.get_text("places_filter_all")
                if 'filter_sight_btn' in self.ids:
                    self.ids.filter_sight_btn.text = app.get_text("places_filter_sight")
                if 'filter_food_btn' in self.ids:
                    self.ids.filter_food_btn.text = app.get_text("places_filter_food")
                if 'filter_museum_btn' in self.ids:
                    self.ids.filter_museum_btn.text = app.get_text("places_filter_museum")
                
                # Обновляем метку и кнопки сортировки
                if 'sort_label' in self.ids:
                    self.ids.sort_label.text = app.get_text("places_sort_label")
                if 'sort_rating_btn' in self.ids:
                    self.ids.sort_rating_btn.text = app.get_text("places_sort_rating")
                if 'sort_name_btn' in self.ids:
                    self.ids.sort_name_btn.text = app.get_text("places_sort_name")
            
            # Перезагружаем места, чтобы обновить карточки с новым языком
            self.load_places()
        except Exception:
            pass

    def on_search_text(self, text):
        self.search_query = text
        self.load_places()

    def set_category_filter(self, category):
        # Повторное нажатие снимает фильтр
        if self.selected_category == category:
            self.selected_category = ""
        else:
            self.selected_category = category
        self.load_places()

    def set_sort_mode(self, mode):
        self.sort_mode = mode
        self.load_places()

    def load_places(self, show_notification=False):
        all_places = self.data_manager.get_all_places()

        # Фильтр по категории
        if self.selected_category:
            all_places = [p for p in all_places if p.get("category") == self.selected_category]

        # Поиск по названию и описанию
        q = (self.search_query or "").strip().lower()
        if q:
            def match(p):
                return q in (p.get("name", "").lower()) or q in (p.get("description", "").lower())

            all_places = [p for p in all_places if match(p)]

        if self.sort_mode == "rating":
            all_places.sort(key=lambda p: p.get("rating") or 0, reverse=True)
        elif self.sort_mode == "name":
            all_places.sort(key=lambda p: (p.get("name") or "").lower())

        self.places = all_places
        container = self.ids.get("places_list")
        if not container:
            return
        container.clear_widgets()
        for place in self.places:
            card = self._build_place_card(place)
            container.add_widget(card)
        
        # Обновляем статические тексты кнопок
        self._update_filter_buttons()
        
        if show_notification:
            haptic_feedback()
            show_success(f"✅ Обновлено: {len(self.places)} мест")

    def refresh_places(self):
        """Метод для pull-to-refresh."""
        self.load_places(show_notification=True)
    
    def _update_filter_buttons(self):
        """Обновляет тексты кнопок фильтров и сортировки."""
        from kivy.app import App
        app = App.get_running_app()
        
        try:
            # Обновляем кнопки фильтров - они пересоздаются при load_places
            # Но нужно обновить их тексты программно
            if hasattr(self, 'ids'):
                # Находим все NeonButton в контейнерах фильтров
                for child in self.children:
                    if hasattr(child, 'children'):
                        for grandchild in child.children:
                            if hasattr(grandchild, 'children'):
                                for btn in grandchild.children:
                                    if hasattr(btn, 'text') and hasattr(btn, 'on_release'):
                                        # Это кнопка фильтра или сортировки
                                        # Обновляем текст на основе текущего языка
                                        if "places_filter_all" in str(btn.on_release) or not self.selected_category:
                                            btn.text = app.get_text("places_filter_all")
                                        elif "sight" in str(btn.on_release) or self.selected_category == "sight":
                                            btn.text = app.get_text("places_filter_sight")
                                        elif "food" in str(btn.on_release) or self.selected_category == "food":
                                            btn.text = app.get_text("places_filter_food")
                                        elif "museum" in str(btn.on_release) or self.selected_category == "museum":
                                            btn.text = app.get_text("places_filter_museum")
                                        elif "rating" in str(btn.on_release) or self.sort_mode == "rating":
                                            btn.text = app.get_text("places_sort_rating")
                                        elif "name" in str(btn.on_release) or self.sort_mode == "name":
                                            btn.text = app.get_text("places_sort_name")
        except Exception:
            pass

    def toggle_favorite_from_list(self, place_id, icon_widget):
        dm = self.data_manager
        if dm.is_favorite(place_id):
            dm.remove_favorite(place_id)
            icon_widget.icon = "heart-outline"
            icon_widget.theme_text_color = "Secondary"
        else:
            dm.add_favorite(place_id)
            icon_widget.icon = "heart"
            icon_widget.theme_text_color = "Primary"

        # Обновляем экран избранного, чтобы изменения сразу были видны
        try:
            from kivy.app import App

            app = App.get_running_app()
            root = app.sm.get_screen("root")
            fav_screen = root.ids.get("favorites_screen")
            if fav_screen:
                fav_screen.load_favorites()
        except Exception:
            pass

    def open_place_details(self, item):
        from kivy.app import App

        app = App.get_running_app()
        sm = app.sm
        place = self.data_manager.get_place(item.place_id)
        if not place:
            return
        detail_screen = sm.get_screen("place_detail")
        detail_screen.place = place
        sm.current = "place_detail"

    def _build_place_card(self, place):
        from kivy.metrics import dp
        from kivy.app import App
        import json

        app = App.get_running_app()
        
        # Горизонтальная карточка: слева текст и рейтинг, справа фото
        card = MDCard(
            orientation="horizontal",
            padding=dp(8),
            spacing=dp(8),
            radius=[dp(15), dp(15), dp(15), dp(15)],
            size_hint_y=None,
            height=dp(160),  # чуть выше, чтобы текст не налезал на маленьких экранах
            elevation=2,
            ripple_behavior=True,
            style="elevated",
        )
        card.place_id = place["id"]

        # Определяем язык и выбираем правильные поля
        # Используем get_language_code() для правильного определения языка
        # Это гарантирует, что мы используем актуальный язык из настроек
        if hasattr(app, "get_language_code"):
            lang = app.get_language_code()
        else:
            lang = "ru"

        # Используем правильные поля из базы данных с fallback
        if lang == "en":
            # Для английского: сначала name_en, потом name_ru, потом name
            name = place.get("name_en") or place.get("name_ru") or place.get("name") or ""
            short_desc = (
                place.get("short_desc_en")
                or place.get("short_desc_ru")
                or place.get("short_desc")
                or ""
            )
            description = (
                place.get("description_en")
                or place.get("description_ru")
                or place.get("description")
                or ""
            )
        else:
            # Для русского: сначала name_ru, потом name
            name = place.get("name_ru") or place.get("name") or ""
            short_desc = place.get("short_desc_ru") or place.get("short_desc") or ""
            description = place.get("description_ru") or place.get("description") or ""

        # Изображение места (первая фотка из image_urls, если есть)
        image_source = ""
        raw_images = place.get("image_urls")
        urls = []
        if isinstance(raw_images, str):
            try:
                urls = json.loads(raw_images)
            except Exception:
                urls = []
        elif isinstance(raw_images, (list, tuple)):
            urls = list(raw_images)
        if urls:
            image_source = urls[0]

        # Нормализуем локальные пути, чтобы AsyncImage понимал их на Android
        try:
            from kivy.utils import platform as _platform
        except Exception:
            _platform = None

        if image_source and isinstance(image_source, str):
            # Если это локальный путь без схемы, добавляем file://
            if "://" not in image_source and image_source.startswith("/"):
                if _platform == "android":
                    image_source = "file://" + image_source

        # Контейнер для текстовой части (слева)
        content_box = MDBoxLayout(
            orientation="vertical",
            padding=dp(8),
            spacing=dp(4),
            size_hint_x=0.7,
        )

        # Заголовок с рейтингом
        header = MDBoxLayout(orientation="horizontal", spacing=dp(4))

        rating = place.get("rating")
        if rating is not None:
            rating_text = f"★ {rating:.1f}"
        else:
            rating_text = ""
        rating_label = MDLabel(
            text=rating_text,
            theme_text_color="Secondary",
            size_hint_x=None,
            width=dp(48),
            shorten=True,
            max_lines=1,
        )

        title_label = MDLabel(
            text=name,
            font_style="Subtitle1",
            theme_text_color="Primary",
            shorten=True,
            max_lines=1,
        )

        header.add_widget(rating_label)
        header.add_widget(title_label)
        content_box.add_widget(header)

        # Краткое описание
        if short_desc:
            short_label = MDLabel(
                text=short_desc,
                theme_text_color="Secondary",
                font_style="Body2",
                shorten=True,
                max_lines=2,
            )
            content_box.add_widget(short_label)

        # Адрес и время работы
        address = place.get("address") or ""
        if address:
            address_label = MDLabel(
                text=f"📍 {address}",
                theme_text_color="Secondary",
                font_style="Caption",
            )
            content_box.add_widget(address_label)

        hours = place.get("hours") or ""
        if hours:
            hours_label = MDLabel(
                text=f"🕐 {hours}",
                theme_text_color="Secondary",
                font_style="Caption",
            )
            content_box.add_widget(hours_label)

        # Цена и категория
        price = place.get("price") or ""
        category_code = place.get("category") or ""
        get_text = getattr(app, "get_text", None)
        if callable(get_text) and category_code:
            key = f"category_{category_code}"
            category_label_text = get_text(key)
        else:
            category_label_text = category_code

        price_category_parts = []
        if price:
            price_category_parts.append(f"💰 {price}")
        if category_label_text:
            price_category_parts.append(f"🏷️ {category_label_text}")
        if price_category_parts:
            price_category_text = " | ".join(price_category_parts)
            price_category_label = MDLabel(
                text=price_category_text,
                theme_text_color="Secondary",
                font_style="Caption",
                shorten=True,
                max_lines=1,
            )
            content_box.add_widget(price_category_label)

        # Действия
        actions = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(32),
            padding=(0, dp(8), 0, 0),
        )
        is_fav = self.data_manager.is_favorite(place["id"])
        fav_icon = MDIconButton(
            icon="heart" if is_fav else "heart-outline",
            theme_icon_color="Primary" if is_fav else "Secondary",
        )

        def on_fav_press(instance):
            self.toggle_favorite_from_list(place["id"], fav_icon)

        fav_icon.bind(on_release=on_fav_press)
        actions.add_widget(fav_icon)

        def on_card_tap(instance):
            self.open_place_details(card)

        content_box.add_widget(actions)
        card.add_widget(content_box)

        # Фото справа
        if image_source:
            image_widget = AsyncImage(
                source=image_source,
                size_hint=(0.3, 1),
                allow_stretch=True,
                keep_ratio=True,
            )
            card.add_widget(image_widget)
        card.bind(on_release=on_card_tap)
        return card
