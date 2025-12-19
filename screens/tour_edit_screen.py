from kivy.properties import DictProperty

from kivymd.uix.screen import MDScreen
from kivymd.uix.filemanager import MDFileManager
from kivy.core.window import Window
from kivy.utils import platform

from data.data_manager import DataManager
import os
import shutil


class TourEditScreen(MDScreen):
    tour = DictProperty()
    file_manager = None

    def set_tour(self, tour):
        self.tour = tour or {}
        self._refresh_fields()

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self._refresh_fields()

    def _refresh_fields(self):
        if not self.tour or not hasattr(self, "ids"):
            return
        ids = self.ids
        get = self.tour.get
        if ids.get("title_field"):
            ids["title_field"].text = get("title", "")
        if ids.get("short_field"):
            ids["short_field"].text = get("short_desc", "")
        if ids.get("desc_field"):
            ids["desc_field"].text = get("description", "")
        if ids.get("theme_field"):
            ids["theme_field"].text = get("theme", "")
        if ids.get("price_field"):
            ids["price_field"].text = str(get("price", "") or "")
        if ids.get("duration_field"):
            ids["duration_field"].text = str(get("duration", "") or "")
        if ids.get("distance_field"):
            ids["distance_field"].text = str(get("distance", "") or "")
        if ids.get("rating_field"):
            ids["rating_field"].text = str(get("rating", "") or "")
        if ids.get("cover_image_field"):
            ids["cover_image_field"].text = get("cover_image", "") or ""

    def save_tour(self):
        if not self.tour:
            return
        dm = DataManager.get_instance()
        tour_id = self.tour.get("id")
        if not tour_id:
            return

        ids = self.ids
        title = ids["title_field"].text.strip() if ids.get("title_field") else ""
        short = ids["short_field"].text.strip() if ids.get("short_field") else ""
        desc = ids["desc_field"].text.strip() if ids.get("desc_field") else ""
        theme = ids["theme_field"].text.strip() if ids.get("theme_field") else ""
        cover_image = ids["cover_image_field"].text.strip() if ids.get("cover_image_field") else ""

        def _to_float(text):
            try:
                text = (text or "").replace(",", ".")
                return float(text)
            except Exception:
                return None

        price = _to_float(ids["price_field"].text) if ids.get("price_field") else None
        duration = _to_float(ids["duration_field"].text) if ids.get("duration_field") else None
        distance = _to_float(ids["distance_field"].text) if ids.get("distance_field") else None
        rating = _to_float(ids["rating_field"].text) if ids.get("rating_field") else None

        dm.update_tour_basic(
            tour_id=tour_id,
            title=title,
            description=desc or short,
            theme=theme,
            price=price,
            duration=duration,
            distance=distance,
            rating=rating,
            cover_image=cover_image or None,
        )

        # Обновляем списки экскурсий
        try:
            from kivy.app import App

            app = App.get_running_app()
            root = app.sm.get_screen("root")
            tours_screen = root.ids.get("tours_screen")
            if tours_screen:
                tours_screen.load_tours()
            admin_screen = root.ids.get("admin_screen")
            if admin_screen:
                admin_screen.load_tours()
        except Exception:
            pass

        # Возвращаемся в админку
        from kivy.app import App

        app = App.get_running_app()
        app.sm.current = "root"

    # --- Выбор обложки экскурсии из файловой системы ---

    def open_cover_image_chooser(self):
        """Открывает выбор файла для обложки тура.

        Используем встроенный MDFileManager и на телефоне, и на ПК.
        """
        if not self.file_manager:
            self.file_manager = MDFileManager(
                exit_manager=self.close_file_manager,
                select_path=self.select_cover_image_path,
            )

        if platform == "android":
            start_path = "/storage/emulated/0"
        else:
            start_path = os.path.expanduser("~")
        self.file_manager.show(start_path)
        Window.keyboard_anim_args = {"d": 0.2, "t": "linear"}
        Window.softinput_mode = "below_target"

    def select_cover_image_path(self, path: str):
        """Коллбек при выборе файла для обложки тура."""
        if not path:
            self.close_file_manager()
            return

        full_path = os.path.abspath(path)

        try:
            project_root = os.path.dirname(os.path.dirname(__file__))
            images_dir = os.path.join(project_root, "cache", "tours")
            os.makedirs(images_dir, exist_ok=True)

            original_name = os.path.basename(full_path)
            tour_id = self.tour.get("id") if isinstance(self.tour, dict) else None
            if tour_id:
                base, ext = os.path.splitext(original_name)
                filename = f"tour_{tour_id}_{base}{ext}"
            else:
                filename = original_name

            target_path = os.path.join(images_dir, filename)
            if not os.path.exists(target_path):
                shutil.copy2(full_path, target_path)

            if platform == "android":
                rel_path = target_path.replace("\\", "/")
            else:
                rel_path = os.path.relpath(target_path, project_root).replace("\\", "/")
        except Exception:
            rel_path = full_path.replace("\\", "/")

        field = self.ids.get("cover_image_field")
        if field is not None:
            field.text = rel_path

        self.close_file_manager()

    def close_file_manager(self, *args):
        if self.file_manager:
            self.file_manager.close()
