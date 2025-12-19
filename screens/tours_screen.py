from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.metrics import dp
from kivy.uix.image import AsyncImage

from kivymd.uix.screen import MDScreen
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton

from data.data_manager import DataManager
import json


class TourCard(MDCard):
    tour_id = None

    def __init__(self, tour_data, start_callback, get_text_func=None, **kwargs):
        super().__init__(**kwargs)
        from kivy.app import App
        
        app = App.get_running_app()
        get_text = get_text_func or (lambda key: app.get_text(key))
        
        self.tour_id = tour_data["id"]
        self.orientation = "horizontal"
        self.padding = dp(8)
        self.size_hint = (1, None)
        self.height = dp(160)  # чуть выше, чтобы текст не налезал на маленьких экранах
        self.radius = [dp(15), dp(15), dp(15), dp(15)]
        self.elevation = 2

        # Обложка экскурсии: сначала берём cover_image, если задано админом,
        # иначе пробуем найти фото по первой точке тура
        image_source = tour_data.get("cover_image") or ""
        if not image_source:
            try:
                dm = DataManager.get_instance()
                points = dm.get_points_for_tour(self.tour_id) or []
                if points:
                    first_point = points[0]
                    place_id = first_point.get("place_id")
                    if place_id:
                        place = dm.get_place(place_id)
                        if place:
                            raw = place.get("image_urls")
                            urls = []
                            if isinstance(raw, str):
                                try:
                                    urls = json.loads(raw)
                                except Exception:
                                    urls = []
                            elif isinstance(raw, (list, tuple)):
                                urls = list(raw)
                            if urls:
                                image_source = urls[0]
            except Exception:
                image_source = ""

        # Нормализуем локальные пути, чтобы AsyncImage понимал их на Android
        try:
            from kivy.utils import platform as _platform
        except Exception:
            _platform = None

        if image_source and isinstance(image_source, str):
            if "://" not in image_source and image_source.startswith("/"):
                if _platform == "android":
                    image_source = "file://" + image_source

        # Левая часть: текст
        info_layout = MDBoxLayout(
            orientation="vertical",
            padding=(dp(8), dp(8), dp(8), dp(4)),
            spacing=dp(4),
            size_hint_x=0.7,
        )

        title = tour_data.get("title") or tour_data.get("name", get_text("tour_default"))
        title_label = MDLabel(
            text=title,
            font_style="Subtitle1",
            adaptive_height=True,
            shorten=True,
            max_lines=2,
        )
        info_layout.add_widget(title_label)

        # Рейтинг и цена
        rating_price = MDBoxLayout(adaptive_height=True)
        rating = tour_data.get("rating")
        reviews = tour_data.get("reviews", 0)
        if rating is not None:
            rating_text = f"⭐ {rating:.1f} ({reviews})" if reviews else f"⭐ {rating:.1f}"
        else:
            rating_text = get_text("new_tour")
        rating_price.add_widget(
            MDLabel(text=rating_text, theme_text_color="Secondary", adaptive_height=True)
        )

        price = tour_data.get("price", 0)
        free_flag = tour_data.get("free", price in (0, None))
        if free_flag:
            price_text = get_text("free")
        else:
            price_text = f"💰 {price} ₽"
        rating_price.add_widget(
            MDLabel(text=price_text, theme_text_color="Secondary", adaptive_height=True)
        )
        info_layout.add_widget(rating_price)

        # Дистанция и время
        distance = tour_data.get("distance") or 0
        duration = tour_data.get("duration") or 0
        info_layout.add_widget(
            MDLabel(
                text=f"🚶 {distance} км   •   ⏱ {duration} мин",
                theme_text_color="Secondary",
                adaptive_height=True,
            )
        )

        # Количество остановок
        stops = tour_data.get("points") or []
        info_layout.add_widget(
            MDLabel(
                text=get_text("stops_count").format(len(stops)),
                theme_text_color="Secondary",
                adaptive_height=True,
            )
        )

        self.add_widget(info_layout)

        # Правая колонка: сверху фото, снизу кнопка
        right_box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(4),
            padding=(dp(4), dp(4), dp(4), dp(4)),
            size_hint_x=0.3,
        )

        # Фото экскурсии (если есть)
        if image_source:
            image_widget = AsyncImage(
                source=image_source,
                size_hint=(1, 0.7),
                allow_stretch=True,
                keep_ratio=True,
            )
            right_box.add_widget(image_widget)

        # Кнопка запуска/покупки
        btn_text = get_text("btn_start") if free_flag else get_text("btn_buy")
        btn = MDRaisedButton(
            text=btn_text,
            size_hint=(1, None),
            height=dp(36),
        )

        def _on_press(_btn):
            start_callback(self.tour_id)

        btn.bind(on_release=_on_press)
        right_box.add_widget(btn)

        self.add_widget(right_box)


class ToursScreen(MDScreen):
    tours = ListProperty()
    selected_category = StringProperty("")  # '', 'history', 'architecture', 'art', 'food', ...
    sort_mode = StringProperty("popularity")  # 'popularity' or 'price'
    tours_count = NumericProperty(0)

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.data_manager = DataManager.get_instance()
        self.load_tours()

    def get_title(self):
        from kivy.app import App
        app = App.get_running_app()
        
        city = None
        try:
            city = self.data_manager.get_active_city()
        except Exception:
            city = None
        if city and city.get("name"):
            return app.get_text("tours_title_city").format(city['name'])
        return app.get_text("tours_title")
    
    def _update_static_texts(self):
        """Обновляет статические тексты при смене языка."""
        from kivy.app import App
        app = App.get_running_app()
        
        try:
            # Обновляем TopAppBar
            if hasattr(self, 'ids') and 'tours_topbar' in self.ids:
                self.ids.tours_topbar.title = self.get_title()
            
            # Обновляем кнопки фильтров
            if hasattr(self, 'ids'):
                if 'tours_filter_all_btn' in self.ids:
                    self.ids.tours_filter_all_btn.text = app.get_text("tours_filter_all")
                if 'tours_filter_history_btn' in self.ids:
                    self.ids.tours_filter_history_btn.text = app.get_text("tours_filter_history")
                if 'tours_filter_architecture_btn' in self.ids:
                    self.ids.tours_filter_architecture_btn.text = app.get_text("tours_filter_architecture")
                if 'tours_filter_art_btn' in self.ids:
                    self.ids.tours_filter_art_btn.text = app.get_text("tours_filter_art")
                
                # Обновляем метку и кнопки сортировки
                if 'tours_sort_label' in self.ids:
                    self.ids.tours_sort_label.text = app.get_text("tours_sort_label")
                if 'tours_sort_popularity_btn' in self.ids:
                    self.ids.tours_sort_popularity_btn.text = app.get_text("tours_sort_popularity")
                if 'tours_sort_price_btn' in self.ids:
                    self.ids.tours_sort_price_btn.text = app.get_text("tours_sort_price")
            
            # Перезагружаем туры, чтобы обновить карточки с новым языком
            self.load_tours()
        except Exception:
            pass

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self.load_tours()

    def set_category_filter(self, category):
        # повторное нажатие снимает фильтр
        if self.selected_category == category:
            self.selected_category = ""
        else:
            self.selected_category = category
        self.load_tours()

    def set_sort_mode(self, mode):
        if mode not in ("popularity", "price"):
            return
        self.sort_mode = mode
        self.load_tours()

    def load_tours(self):
        tours = self.data_manager.get_all_tours_with_progress()

        # фильтр по категории (theme)
        if self.selected_category:
            tours = [t for t in tours if t.get("theme") == self.selected_category]

        # сортировка
        if self.sort_mode == "price":
            tours = sorted(
                tours,
                key=lambda t: (t.get("price") is None, t.get("price") or 0),
            )
        else:  # popularity
            tours = sorted(
                tours,
                key=lambda t: (t.get("rating") is None, -(t.get("rating") or 0)),
            )

        self.tours = tours
        self.tours_count = len(self.tours)
        container = self.ids.get("tours_list")
        if not container:
            return
        container.clear_widgets()

        def _start_tour(tour_id):
            class DummyItem:
                pass

            item = DummyItem()
            item.tour_id = tour_id
            self.open_tour_details(item)

        from kivy.app import App
        app = App.get_running_app()
        
        for tour in self.tours:
            card = TourCard(tour, start_callback=_start_tour, get_text_func=app.get_text)
            container.add_widget(card)

    def open_tour_details(self, item):
        from kivy.app import App

        app = App.get_running_app()
        sm = app.sm
        tour = self.data_manager.get_tour(item.tour_id)
        if not tour:
            return
        detail_screen = sm.get_screen("tour_detail")
        detail_screen.set_tour(tour)
        sm.current = "tour_detail"
