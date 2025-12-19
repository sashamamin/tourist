from kivy.properties import DictProperty, ListProperty

from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.list import OneLineListItem
from kivymd.uix.filemanager import MDFileManager
from kivy.core.window import Window

from data.data_manager import DataManager
import os
import json
import shutil


class TourRouteEditScreen(MDScreen):
    tour = DictProperty()
    points = ListProperty()
    file_manager = None
    _current_image_point_index = -1

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.data_manager = DataManager.get_instance()

    def set_tour(self, tour):
        """Устанавливает текущую экскурсию и загружает её точки."""
        self.tour = tour or {}
        self._load_points()

    def _load_points(self):
        self.points = []
        if not self.tour:
            return
        dm = getattr(self, "data_manager", None) or DataManager.get_instance()
        tour_id = self.tour.get("id")
        if not tour_id:
            return
        raw_points = dm.get_points_for_tour(tour_id)
        points = []
        for p in raw_points:
            place = dm.get_place(p.get("place_id"))
            full_story = p.get("audio_story") or ""
            title = ""
            body = full_story
            if "\n" in full_story:
                title, body = full_story.split("\n", 1)
            place_name = place.get("name") if place else f"#{p.get('place_id')}"
            # image_urls может быть JSON-строкой или уже списком (на будущее)
            raw_images = p.get("image_urls")
            image_urls = []
            if isinstance(raw_images, str) and raw_images:
                try:
                    image_urls = json.loads(raw_images)
                except Exception:
                    image_urls = []
            elif isinstance(raw_images, (list, tuple)):
                image_urls = list(raw_images)
            points.append(
                {
                    "place_id": p.get("place_id"),
                    "order_index": p.get("order_index"),
                    "place_name": place_name,
                    "title": title or "",
                    "audio_story": body or "",
                    "quiz_question": p.get("quiz_question") or "",
                    "image_urls": image_urls,
                }
            )
        # Сортируем по order_index на всякий случай
        points.sort(key=lambda x: x.get("order_index") or 0)
        self.points = points
        self._refresh_points_list()

    def _refresh_points_list(self):
        """Обновляет список точек на экране из self.points."""
        ids = getattr(self, "ids", {})
        container = ids.get("route_points_list")
        if not container:
            return
        container.clear_widgets()

        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.button import MDIconButton
        from kivy.metrics import dp

        for idx, point in enumerate(self.points, start=1):
            display_name = point.get("title") or point.get("place_name", "")
            text = f"{idx}. {display_name}"
            extra = []
            if point.get("audio_story"):
                extra.append("текст есть")
            if point.get("quiz_question"):
                extra.append("вопрос есть")
            if point.get("image_urls"):
                extra.append(f"фото: {len(point.get('image_urls'))}")
            suffix = " | ".join(extra) if extra else "нет текста"
            secondary = f"ID места: {point.get('place_id')} — {suffix}"

            row = MDBoxLayout(
                orientation="horizontal",
                padding=(dp(16), dp(8)),
                spacing=dp(8),
                size_hint_y=None,
                height=dp(56),
            )

            text_box = MDBoxLayout(orientation="vertical")
            title_label = MDLabel(text=text, halign="left")
            subtitle_label = MDLabel(text=secondary, halign="left", theme_text_color="Secondary")
            text_box.add_widget(title_label)
            text_box.add_widget(subtitle_label)

            buttons_box = MDBoxLayout(
                orientation="horizontal",
                size_hint_x=None,
                width=dp(160),
                spacing=dp(4),
            )

            btn_up = MDIconButton(icon="chevron-up", on_release=lambda inst, i=idx - 1: self.move_point_up(i))
            btn_down = MDIconButton(icon="chevron-down", on_release=lambda inst, i=idx - 1: self.move_point_down(i))
            btn_del = MDIconButton(icon="delete", on_release=lambda inst, i=idx - 1: self.remove_point(i))
            btn_edit = MDIconButton(icon="pencil", on_release=lambda inst, i=idx - 1: self.open_edit_point_dialog(i))
            btn_images = MDIconButton(icon="image-multiple", on_release=lambda inst, i=idx - 1: self.open_point_images_dialog(i))

            buttons_box.add_widget(btn_up)
            buttons_box.add_widget(btn_down)
            buttons_box.add_widget(btn_del)
            buttons_box.add_widget(btn_edit)
            buttons_box.add_widget(btn_images)

            row.add_widget(text_box)
            row.add_widget(buttons_box)

            container.add_widget(row)

    def move_point_up(self, index):
        if index <= 0 or index >= len(self.points):
            return
        pts = list(self.points)
        pts[index - 1], pts[index] = pts[index], pts[index - 1]
        # Пересчитываем order_index
        for i, p in enumerate(pts, start=1):
            p["order_index"] = i
        self.points = pts
        self._refresh_points_list()

    def move_point_down(self, index):
        if index < 0 or index >= len(self.points) - 1:
            return
        pts = list(self.points)
        pts[index], pts[index + 1] = pts[index + 1], pts[index]
        for i, p in enumerate(pts, start=1):
            p["order_index"] = i
        self.points = pts
        self._refresh_points_list()

    def remove_point(self, index):
        if index < 0 or index >= len(self.points):
            return
        pts = list(self.points)
        pts.pop(index)
        for i, p in enumerate(pts, start=1):
            p["order_index"] = i
        self.points = pts
        self._refresh_points_list()

    def open_add_point_dialog(self):
        """Открывает диалог выбора места для добавления в маршрут."""
        dm = getattr(self, "data_manager", None) or DataManager.get_instance()
        places = dm.get_all_places()

        from kivymd.uix.list import MDList
        from kivy.uix.scrollview import ScrollView
        from kivy.metrics import dp

        md_list = MDList()

        # Первая строка — возможность создать свою точку без привязки к месту
        custom_item = OneLineListItem(text="Своя точка (без привязки к месту)")
        custom_item.bind(on_release=self._on_add_custom_point)
        md_list.add_widget(custom_item)

        # Далее — реальные места из базы
        for place in places:
            item = OneLineListItem(text=place["name"])  # dict c колонками из get_all_places
            item.place_id = place["id"]
            item.bind(on_release=self._on_select_place_for_point)
            md_list.add_widget(item)

        scroll = ScrollView(size_hint=(1, None), height=dp(320))
        scroll.add_widget(md_list)

        self._add_point_dialog = MDDialog(
            title="Выберите место или создайте свою точку",
            type="custom",
            content_cls=scroll,
        )
        self._add_point_dialog.open()

    def _on_select_place_for_point(self, list_item):
        """Обработчик выбора места в диалоге добавления точки."""
        if hasattr(self, "_add_point_dialog") and self._add_point_dialog:
            self._add_point_dialog.dismiss()
        place_id = getattr(list_item, "place_id", None)
        if not place_id:
            return
        dm = getattr(self, "data_manager", None) or DataManager.get_instance()
        place = dm.get_place(place_id)
        pts = list(self.points or [])
        next_index = len(pts) + 1
        pts.append(
            {
                "place_id": place_id,
                "order_index": next_index,
                "place_name": place.get("name") if place else f"#{place_id}",
                "title": place.get("name") if place else f"#{place_id}",
                "audio_story": "",
                "quiz_question": "",
                "image_urls": [],
            }
        )
        self.points = pts
        self._refresh_points_list()
        # Сразу открываем диалог редактирования для только что добавленной точки,
        # чтобы админ мог задать своё название и текст
        self.open_edit_point_dialog(next_index - 1)

    def _on_add_custom_point(self, _list_item):
        """Создание собственной точки маршрута без привязки к месту."""
        if hasattr(self, "_add_point_dialog") and self._add_point_dialog:
            self._add_point_dialog.dismiss()

        pts = list(self.points or [])
        next_index = len(pts) + 1
        pts.append(
            {
                "place_id": None,
                "order_index": next_index,
                "place_name": "Своя точка",
                "title": "Своя точка",
                "audio_story": "",
                "quiz_question": "",
                "image_urls": [],
            }
        )
        self.points = pts
        self._refresh_points_list()
        self.open_edit_point_dialog(next_index - 1)

    def open_edit_point_dialog(self, index):
        """Открывает диалог редактирования текстов для выбранной точки маршрута."""
        if index < 0 or index >= len(self.points):
            return
        point = self.points[index]

        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.button import MDFlatButton
        from kivy.metrics import dp

        box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=dp(8),
            size_hint_y=None,
            height=dp(260),
        )

        title_field = MDTextField(
            text=point.get("title", "") or point.get("place_name", ""),
            hint_text="Название точки в маршруте",
            multiline=False,
            mode="rectangle",
            size_hint_y=None,
            height=dp(48),
        )
        audio_field = MDTextField(
            text=point.get("audio_story", ""),
            hint_text="Текст для точки",
            multiline=True,
            mode="rectangle",
            size_hint_y=None,
            height=dp(96),
        )
        question_field = MDTextField(
            text=point.get("quiz_question", ""),
            hint_text="Вопрос для пользователя (quiz_question)",
            multiline=True,
            mode="rectangle",
            size_hint_y=None,
            height=dp(96),
        )

        box.add_widget(title_field)
        box.add_widget(audio_field)
        box.add_widget(question_field)

        def _save_point_texts(_btn):
            pts = list(self.points)
            p = dict(pts[index])
            p["title"] = title_field.text or ""
            p["audio_story"] = audio_field.text or ""
            p["quiz_question"] = question_field.text or ""
            pts[index] = p
            self.points = pts
            self._refresh_points_list()
            if hasattr(self, "_edit_point_dialog") and self._edit_point_dialog:
                self._edit_point_dialog.dismiss()

        def _open_images_from_buttons(_btn):
            self.open_point_images_dialog(index)

        self._edit_point_dialog = MDDialog(
            title=f"Точка #{index + 1}: {point.get('place_name', '')}",
            type="custom",
            content_cls=box,
            buttons=[
                MDFlatButton(text="Фотографии", on_release=_open_images_from_buttons),
                MDFlatButton(text="Отмена", on_release=lambda _b: self._edit_point_dialog.dismiss()),
                MDFlatButton(text="Сохранить", on_release=_save_point_texts),
            ],
        )
        self._edit_point_dialog.open()

    def save_route(self):
        """Сохраняет текущий список точек маршрута в БД."""
        if not self.tour:
            return
        tour_id = self.tour.get("id")
        if not tour_id:
            return
        dm = getattr(self, "data_manager", None) or DataManager.get_instance()
        pts = list(self.points or [])
        # На всякий случай пересчитываем order_index перед сохранением
        db_points = []
        for i, p in enumerate(pts, start=1):
            title = (p.get("title") or "").strip()
            body = (p.get("audio_story") or "").strip()
            if title and body:
                full_story = f"{title}\n{body}"
            else:
                full_story = title or body
            db_points.append(
                {
                    "place_id": p.get("place_id"),
                    "order_index": i,
                    "audio_story": full_story,
                    "quiz_question": p.get("quiz_question", ""),
                    "image_urls": p.get("image_urls", []) or [],
                }
            )
        dm.set_tour_points(tour_id, db_points)

        # После сохранения возвращаемся в админку
        from kivy.app import App

        app = App.get_running_app()
        app.sm.current = "root"

    # --- Работа с фотографиями точки маршрута ---

    def open_point_images_dialog(self, index):
        """Открывает диалог со списком фотографий для выбранной точки."""
        if index < 0 or index >= len(self.points):
            return
        self._current_image_point_index = index
        point = self.points[index]
        images = point.get("image_urls") or []

        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.button import MDFlatButton
        from kivy.metrics import dp

        box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=dp(8),
            size_hint_y=None,
            height=dp(260),
        )

        images_field = MDTextField(
            text="\n".join(images),
            hint_text="Список фото (по одному пути/URL в строке)",
            multiline=True,
            mode="rectangle",
        )

        def _add_image_from_fs(_btn):
            # запоминаем поле, чтобы дописать путь после выбора файла
            self._images_field_ref = images_field
            self.open_image_file_manager()

        add_btn = MDFlatButton(text="Добавить фото с устройства", on_release=_add_image_from_fs)

        box.add_widget(images_field)
        box.add_widget(add_btn)

        def _save_images(_btn):
            raw = images_field.text or ""
            urls = [ln.strip() for ln in raw.replace(",", "\n").splitlines() if ln.strip()]
            pts = list(self.points)
            p = dict(pts[index])
            p["image_urls"] = urls
            pts[index] = p
            self.points = pts
            self._refresh_points_list()
            if hasattr(self, "_images_dialog") and self._images_dialog:
                self._images_dialog.dismiss()

        self._images_dialog = MDDialog(
            title=f"Фотографии точки #{index + 1}",
            type="custom",
            content_cls=box,
            buttons=[
                MDFlatButton(text="Отмена", on_release=lambda _b: self._images_dialog.dismiss()),
                MDFlatButton(text="Сохранить", on_release=_save_images),
            ],
        )
        self._images_dialog.open()

    def open_image_file_manager(self):
        """Открывает файловый менеджер для добавления картинки к текущей точке."""
        if not self.file_manager:
            self.file_manager = MDFileManager(
                exit_manager=self.close_file_manager,
                select_path=self.select_image_path_for_point,
            )

        start_path = os.path.expanduser("~")
        self.file_manager.show(start_path)
        Window.keyboard_anim_args = {"d": 0.2, "t": "linear"}
        Window.softinput_mode = "below_target"

    def select_image_path_for_point(self, path: str):
        """Коллбек выбора файла: копирует фото в кэш и добавляет путь в поле изображений."""
        if not path:
            self.close_file_manager()
            return

        full_path = os.path.abspath(path)
        try:
            project_root = os.path.dirname(os.path.dirname(__file__))
            images_dir = os.path.join(project_root, "cache", "tour_points")
            os.makedirs(images_dir, exist_ok=True)

            original_name = os.path.basename(full_path)
            tour_id = self.tour.get("id") if isinstance(self.tour, dict) else None
            if tour_id and self._current_image_point_index >= 0:
                base, ext = os.path.splitext(original_name)
                filename = f"tour_{tour_id}_pt{self._current_image_point_index + 1}_{base}{ext}"
            else:
                filename = original_name

            target_path = os.path.join(images_dir, filename)
            if not os.path.exists(target_path):
                shutil.copy2(full_path, target_path)

            rel_path = os.path.relpath(target_path, project_root).replace("\\", "/")
        except Exception:
            rel_path = full_path.replace("\\", "/")

        field = getattr(self, "_images_field_ref", None)
        if field is not None:
            text = (field.text or "").strip()
            if text:
                text = text + "\n" + rel_path
            else:
                text = rel_path
            field.text = text

        self.close_file_manager()

    def close_file_manager(self, *args):
        if self.file_manager:
            self.file_manager.close()
