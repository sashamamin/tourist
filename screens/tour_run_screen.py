from kivy.properties import DictProperty, ListProperty, NumericProperty, StringProperty

from kivymd.uix.screen import MDScreen

from data.data_manager import DataManager
from kivy.uix.carousel import Carousel
from kivy.uix.image import AsyncImage
from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton
from kivy.metrics import dp
import json


class TourRunScreen(MDScreen):
    """Простой режим прохождения экскурсии (линейный, без аудио и GPS)."""

    tour = DictProperty()
    points = ListProperty()
    current_index = NumericProperty(0)
    progress_text = StringProperty("")
    quiz_text = StringProperty("")
    _full_text = StringProperty("")

    def start_tour(self, tour):
        """Инициализация экскурсии и переход к первой точке."""
        self.tour = tour
        dm = DataManager.get_instance()
        self.points = dm.get_points_for_tour(tour["id"])
        self.current_index = 0
        self._update_view(save_progress=True)

    _image_dialog = None

    def _update_view(self, save_progress=False):
        ids = self.ids
        dm = DataManager.get_instance()

        from kivy.app import App
        app = App.get_running_app()
        
        total = len(self.points)
        if total == 0:
            self.progress_text = app.get_text("tour_no_points")
            self.quiz_text = ""
            if "point_title" in ids:
                ids["point_title"].text = ""
            if "point_description" in ids:
                ids["point_description"].text = ""
            if "next_info" in ids:
                ids["next_info"].text = ""
            return

        # Текущая точка
        point = self.points[self.current_index]
        place = dm.get_place(point["place_id"])

        self.progress_text = app.get_text("stop_progress").format(self.current_index + 1, total)

        # Картинки текущей точки: сначала берём собственные image_urls точки,
        # если их нет — фото места.
        raw_point_images = point.get("image_urls")
        image_urls = []
        if isinstance(raw_point_images, str) and raw_point_images:
            try:
                image_urls = json.loads(raw_point_images)
            except Exception:
                image_urls = []
        elif isinstance(raw_point_images, (list, tuple)):
            image_urls = list(raw_point_images)
        if not image_urls and place is not None:
            try:
                raw = place.get("image_urls")
                if isinstance(raw, str) and raw:
                    try:
                        image_urls = json.loads(raw)
                    except Exception:
                        image_urls = []
                elif isinstance(raw, (list, tuple)):
                    image_urls = list(raw)
            except Exception:
                image_urls = []

        carousel = ids.get("point_image_carousel")
        if carousel is not None:
            carousel.clear_widgets()
            for url in image_urls:
                if not url:
                    continue
                img = AsyncImage(source=url, allow_stretch=True, keep_ratio=True)
                img.bind(on_touch_down=self._on_image_touch)
                carousel.add_widget(img)
        # сохраняем список текущих картинок для полноэкранного просмотра
        self._current_image_urls = image_urls

        # Заголовок и текст точки: сначала пробуем взять из audio_story,
        # где первая строка — заголовок, остальное — текст. Если пусто,
        # используем данные места.
        full_story = point.get("audio_story") or ""
        custom_title = ""
        custom_body = ""
        if "\n" in full_story:
            custom_title, custom_body = full_story.split("\n", 1)
        else:
            custom_body = full_story

        if "point_title" in ids:
            if custom_title.strip():
                ids["point_title"].text = custom_title.strip()
            else:
                ids["point_title"].text = place.get("name", "") if place else ""
        # Полный текст для диалога: заголовок + перенос строки + основной текст (если есть)
        full_for_dialog = ""
        if custom_title.strip():
            full_for_dialog = custom_title.strip()
            if custom_body.strip():
                full_for_dialog += "\n" + custom_body.strip()
        else:
            full_for_dialog = custom_body.strip() or (place.get("description", "") if place else "") or ""

        # Сохраняем полный текст отдельно, а в label показываем только первые 100 символов
        self._full_text = full_for_dialog
        if "point_description" in ids:
            short = full_for_dialog
            if len(short) > 100:
                short = short[:100] + "..."
            ids["point_description"].text = short

        # Вопрос/загадка для точки, если есть
        self.quiz_text = point.get("quiz_question") or ""
        if "quiz_label" in ids:
            ids["quiz_label"].text = self.quiz_text

        # Информация о следующей точке (только текст-заглушка)
        if "next_info" in ids:
            if self.current_index + 1 < total:
                next_place = dm.get_place(self.points[self.current_index + 1]["place_id"])
                if next_place:
                    ids["next_info"].text = app.get_text("next_stop").format(next_place['name'])
                else:
                    ids["next_info"].text = app.get_text("next_stop_default")
            else:
                ids["next_info"].text = app.get_text("last_stop")

        # Сохранение прогресса
        if save_progress and self.tour:
            dm.upsert_user_tour_progress(
                tour_id=self.tour["id"],
                progress=self.current_index + 1,
                current_point=self.current_index,
            )

    def _on_image_touch(self, instance, touch):
        # открываем картинку во весь экран, если кликнули именно по ней
        if instance.collide_point(*touch.pos) and touch.is_double_tap is False:
            self.open_image_fullscreen(instance.source)
        return False

    def open_image_fullscreen(self, source):
        if not source:
            return

        # Карусель со всеми картинками точки, чтобы можно было листать
        urls = getattr(self, "_current_image_urls", []) or [source]

        from kivy.uix.carousel import Carousel

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

        # устанавливаем текущий слайд на нажатую картинку
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

    def open_full_text_dialog(self):
        """Показывает полный текст точки в простом диалоге."""
        if not self.points:
            return

        # Пересчитываем полный текст напрямую из текущей точки
        dm = DataManager.get_instance()
        point = self.points[self.current_index]
        place = dm.get_place(point["place_id"])

        full_story = point.get("audio_story") or ""
        custom_title = ""
        custom_body = ""
        if "\n" in full_story:
            custom_title, custom_body = full_story.split("\n", 1)
        else:
            custom_body = full_story

        if custom_title.strip():
            full_for_dialog = custom_title.strip()
            if custom_body.strip():
                full_for_dialog += "\n" + custom_body.strip()
        else:
            full_for_dialog = custom_body.strip() or (place.get("description", "") if place else "") or ""

        if not full_for_dialog:
            return

        dialog = MDDialog(
            title="Текст точки",
            text=full_for_dialog,
            size_hint=(0.95, None),
            buttons=[
                MDFlatButton(text="Закрыть", on_release=lambda _b: dialog.dismiss()),
            ],
        )
        dialog.open()

    def go_next(self):
        if self.current_index + 1 < len(self.points):
            self.current_index += 1
            self._update_view(save_progress=True)

    def go_prev(self):
        if self.current_index > 0:
            self.current_index -= 1
            # назад тоже обновляем прогресс, но без увеличения счётчика
            self._update_view(save_progress=True)

    def finish_tour(self):
        """Завершение экскурсии: сохраняем как завершённую и выходим."""
        from kivy.app import App

        if self.tour and self.points:
            dm = DataManager.get_instance()
            dm.upsert_user_tour_progress(
                tour_id=self.tour["id"],
                progress=len(self.points),
                current_point=self.current_index,
                completed_at="completed",  # MVP-заглушка вместо реального времени
            )

        app = App.get_running_app()
        app.sm.current = "root"
