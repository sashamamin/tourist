from kivy.properties import DictProperty, ListProperty

from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivy.uix.image import AsyncImage
from kivy.metrics import dp
from kivymd.uix.button import MDFlatButton

from data.data_manager import DataManager


class TourDetailScreen(MDScreen):
    tour = DictProperty()
    points = ListProperty()
    image_urls = ListProperty()
    _image_dialog = None

    def set_tour(self, tour):
        self.tour = tour
        self._load_points()
        self.refresh_view()

    def _load_points(self):
        if not self.tour:
            self.points = []
            self.image_urls = []
            return
        dm = DataManager.get_instance()
        self.points = dm.get_points_for_tour(self.tour["id"])

        # Обложка тура: как в TourCard — сначала cover_image,
        # иначе первое фото первого места маршрута
        image_source = self.tour.get("cover_image") or ""
        if not image_source:
            try:
                import json

                points = self.points or []
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

        self.image_urls = [image_source] if image_source else []

    def open_image_fullscreen(self, source):
        """Открывает обложку тура в увеличенном виде."""
        if not source:
            return

        content = MDBoxLayout(
            orientation="vertical",
            size_hint_x=1,
            size_hint_y=None,
            height=dp(400),
            padding=dp(8),
        )
        content.add_widget(
            AsyncImage(
                source=source,
                allow_stretch=True,
                keep_ratio=True,
                size_hint=(1, 1),
            )
        )

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

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self.refresh_view()

    def refresh_view(self):
        ids = self.ids
        if not self.tour:
            return
        if "tour_title" in ids:
            ids["tour_title"].text = self.tour.get("title", "")
        if "tour_description" in ids:
            ids["tour_description"].text = self.tour.get("description", "")
        if "tour_meta" in ids:
            duration = self.tour.get("duration")
            distance = self.tour.get("distance")
            rating = self.tour.get("rating")
            parts = []
            if duration:
                parts.append(f"⏱ {duration} мин")
            if distance:
                parts.append(f"🚶 {distance} км")
            if rating is not None:
                parts.append(f"⭐ {rating:.1f}")
            ids["tour_meta"].text = "  ·  ".join(parts)

        # Прогресс по туру (кол-во точек)
        total_points = len(self.points)
        progress_value = 0
        if total_points:
            dm = DataManager.get_instance()
            user_progress = dm.get_user_tour_progress(self.tour["id"], user_id=1)
            if user_progress and user_progress.get("progress") is not None:
                progress_value = int(user_progress["progress"])
        from kivy.app import App
        app = App.get_running_app()
        
        if "tour_progress_label" in ids:
            if total_points:
                ids["tour_progress_label"].text = app.get_text("tour_progress").format(progress_value, total_points)
            else:
                ids["tour_progress_label"].text = app.get_text("tour_progress_empty")
        if "tour_progress_bar" in ids:
            if total_points:
                ids["tour_progress_bar"].value = 100 * min(progress_value, total_points) / total_points
            else:
                ids["tour_progress_bar"].value = 0

        # Список точек
        container = ids.get("tour_points_list")
        if container is None:
            return
        container.clear_widgets()
        dm = DataManager.get_instance()
        from kivymd.uix.list import TwoLineListItem
        from kivy.app import App
        app = App.get_running_app()

        for idx, point in enumerate(self.points, start=1):
            place = None
            place_name = ""
            place_subtitle = ""
            place_id = point.get("place_id")
            if place_id:
                place = dm.get_place(place_id)
                if place:
                    place_name = place.get("name", "")
                    place_subtitle = place.get("short_desc") or place.get("address") or ""

            # Для точек без места или если место не найдено используем текст из audio_story
            if not place:
                full_story = point.get("audio_story") or ""
                custom_title = ""
                custom_body = ""
                if "\n" in full_story:
                    custom_title, custom_body = full_story.split("\n", 1)
                else:
                    custom_body = full_story
                place_name = custom_title.strip() or custom_body.strip() or "Точка без места"
                place_subtitle = custom_body.strip()

            title = app.get_text("stop_label").format(idx) + f" {place_name}"
            subtitle = place_subtitle
            item = TwoLineListItem(text=title, secondary_text=subtitle)
            container.add_widget(item)

    def start_tour(self):
        from kivy.app import App

        if not self.tour:
            return
        app = App.get_running_app()
        run_screen = app.sm.get_screen("tour_run")
        run_screen.start_tour(self.tour)
        app.sm.current = "tour_run"
