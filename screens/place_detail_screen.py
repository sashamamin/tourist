from kivy.properties import DictProperty, NumericProperty, StringProperty

from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton

from data.data_manager import DataManager
from kivy.uix.image import AsyncImage
from kivy.metrics import dp
import json


class PlaceDetailScreen(MDScreen):
    place = DictProperty()
    review_text = StringProperty("")
    review_rating = NumericProperty(5)
    image_url = StringProperty("")
    _image_dialog = None
    _image_urls_list = []

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        # place should already be set from navigation logic
        self.refresh_view()

    def refresh_view(self):
        if not self.place:
            return
        ids = self.ids
        if "name_label" in ids:
            ids["name_label"].text = self.place.get("name", "")
        if "category_label" in ids:
            ids["category_label"].text = self.place.get("category", "")
        if "description_label" in ids:
            ids["description_label"].text = self.place.get("description", "")

        # Фото места — берём все ссылки из image_urls, первая будет главной
        raw = self.place.get("image_urls")
        urls = []
        if isinstance(raw, str):
            try:
                urls = json.loads(raw)
            except Exception:
                urls = []
        elif isinstance(raw, (list, tuple)):
            urls = list(raw)
        self.image_url = urls[0] if urls else ""
        self._image_urls_list = urls

        # Заполняем карусель изображений, если она есть в разметке
        carousel = ids.get("images_carousel")
        if carousel is not None:
            carousel.clear_widgets()
            for url in urls:
                if not url:
                    continue
                img = AsyncImage(
                    source=url,
                    allow_stretch=True,
                    keep_ratio=True,
                )
                img.bind(on_touch_down=self._on_image_touch)
                carousel.add_widget(img)

        # Загрузка и отображение отзывов
        dm = DataManager.get_instance()
        place_id = self.place.get("id")
        reviews = dm.get_reviews_for_place(place_id) if place_id else []
        container = ids.get("reviews_list")
        if container is not None:
            container.clear_widgets()
            from kivymd.uix.list import OneLineIconListItem, IconLeftWidget

            from kivy.app import App
            app = App.get_running_app()
            
            if not reviews:
                item = OneLineIconListItem(text=app.get_text("no_reviews"))
                icon = IconLeftWidget(icon="comment-outline")
                item.add_widget(icon)
                container.add_widget(item)
            else:
                for review in reviews:
                    text = review.get("comment") or app.get_text("review_no_text")
                    rating = review.get("rating")
                    if rating is not None:
                        text = f"[{rating}★] " + text
                    item = OneLineIconListItem(text=text)
                    icon = IconLeftWidget(icon="comment")
                    item.add_widget(icon)
                    container.add_widget(item)

    def toggle_favorite(self):
        dm = DataManager.get_instance()
        if not self.place:
            return
        place_id = self.place.get("id")
        if not place_id:
            return
        if dm.is_favorite(place_id):
            dm.remove_favorite(place_id)
        else:
            dm.add_favorite(place_id)

        # Обновляем экран избранного, чтобы изменения были видны сразу
        try:
            from kivy.app import App

            app = App.get_running_app()
            root = app.sm.get_screen("root")
            fav_screen = root.ids.get("favorites_screen")
            if fav_screen:
                fav_screen.load_favorites()
        except Exception:
            pass

    def set_review_rating(self, rating):
        self.review_rating = rating

    def submit_review(self):
        if not self.place:
            return
        place_id = self.place.get("id")
        if not place_id:
            return
        text = (self.review_text or "").strip()
        if not text:
            return
        dm = DataManager.get_instance()
        dm.add_review(
            place_id=place_id,
            rating=int(self.review_rating or 0) or 0,
            comment=text,
            user_id=1,
            created_at="",
        )
        # очистка формы и обновление списка
        self.review_text = ""
        self.refresh_view()

    # --- Полноэкранное фото места ---

    def _on_image_touch(self, instance, touch):
        """Открывает картинку из карусели во весь экран при нажатии."""
        if instance.collide_point(*touch.pos) and not touch.is_double_tap:
            self.open_image_fullscreen(instance.source)
        return False

    def open_image_fullscreen(self, source):
        if not source:
            return

        from kivy.uix.carousel import Carousel

        urls = self._image_urls_list or [source]
        carousel = Carousel(direction="right", loop=True)
        for url in urls:
            if not url:
                continue
            img = AsyncImage(
                source=url,
                allow_stretch=True,
                keep_ratio=True,
                size_hint=(1, 1),
            )
            carousel.add_widget(img)

        try:
            idx = urls.index(source)
            carousel.index = idx
        except ValueError:
            pass

        content = MDBoxLayout(
            orientation="vertical",
            size_hint_x=1,
            size_hint_y=None,
            height=dp(400),
            padding=dp(8),
        )
        content.add_widget(carousel)

        if self._image_dialog:
            self._image_dialog.dismiss(force=True)

        self._image_dialog = MDDialog(
            type="custom",
            content_cls=content,
            size_hint=(0.95, 0.95),
            buttons=[
                MDFlatButton(text="Закрыть", on_release=lambda _b: self._image_dialog.dismiss()),
            ],
        )
        self._image_dialog.open()
