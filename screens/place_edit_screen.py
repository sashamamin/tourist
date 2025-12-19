from kivy.properties import DictProperty

from kivymd.uix.screen import MDScreen
from kivymd.uix.filemanager import MDFileManager
from kivy.core.window import Window
from kivy.utils import platform

from data.data_manager import DataManager
import json
import os
import shutil


class PlaceEditScreen(MDScreen):
    place = DictProperty()
    file_manager = None

    def set_place(self, place):
        self.place = place or {}
        self._refresh_fields()

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self._refresh_fields()

    def _refresh_fields(self):
        if not self.place or not hasattr(self, "ids"):
            return
        ids = self.ids
        ids.get("name_field").text = self.place.get("name", "") if ids.get("name_field") else ""
        ids.get("short_field").text = self.place.get("short_desc", "") if ids.get("short_field") else ""
        ids.get("desc_field").text = self.place.get("description", "") if ids.get("desc_field") else ""
        ids.get("addr_field").text = self.place.get("address", "") if ids.get("addr_field") else ""

        # image_urls могут храниться как JSON-строка или список
        raw = self.place.get("image_urls")
        urls = []
        if isinstance(raw, str):
            try:
                urls = json.loads(raw)
            except Exception:
                urls = []
        elif isinstance(raw, (list, tuple)):
            urls = list(raw)
        images_text = "\n".join([u for u in urls if u])
        if ids.get("images_field") is not None:
            ids.get("images_field").text = images_text

    def open_image_chooser(self):
        """Открывает выбор файла.

        Используем встроенный MDFileManager и на телефоне, и на ПК.
        """

        # Встроенный файловый менеджер KivyMD
        if not self.file_manager:
            # Создаём файловый менеджер один раз
            self.file_manager = MDFileManager(
                exit_manager=self.close_file_manager,
                select_path=self.select_path,
            )

        # На Android сразу открываем внешнее хранилище, на ПК — домашнюю папку
        if platform == "android":
            start_path = "/storage/emulated/0"
        else:
            start_path = os.path.expanduser("~")
        self.file_manager.show(start_path)
        Window.keyboard_anim_args = {"d": 0.2, "t": "linear"}
        Window.softinput_mode = "below_target"

    def select_path(self, path: str):
        """Коллбек при выборе файла в MDFileManager."""
        if not path:
            self.close_file_manager()
            return

        full_path = os.path.abspath(path)

        # Копируем файл в папку проекта (cache/places) и используем относительный путь
        try:
            project_root = os.path.dirname(os.path.dirname(__file__))
            images_dir = os.path.join(project_root, "cache", "places")
            os.makedirs(images_dir, exist_ok=True)

            original_name = os.path.basename(full_path)
            # Добавим id места в имя, чтобы легче было различать
            place_id = self.place.get("id") if isinstance(self.place, dict) else None
            if place_id:
                base, ext = os.path.splitext(original_name)
                filename = f"place_{place_id}_{base}{ext}"
            else:
                filename = original_name

            target_path = os.path.join(images_dir, filename)
            # Если файл ещё не скопирован, копируем
            if not os.path.exists(target_path):
                shutil.copy2(full_path, target_path)

            # На Android надёжнее использовать абсолютный путь,
            # на десктопе можно относительный относительно project_root.
            if platform == "android":
                rel_path = target_path.replace("\\", "/")
            else:
                rel_path = os.path.relpath(target_path, project_root).replace("\\", "/")
        except Exception:
            # В случае ошибки просто используем исходный путь
            rel_path = full_path.replace("\\", "/")

        ids = self.ids
        field = ids.get("images_field")
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

    def save_place(self):
        if not self.place:
            return
        dm = DataManager.get_instance()
        place_id = self.place.get("id")
        if not place_id:
            return

        ids = self.ids
        name = ids.get("name_field").text.strip() if ids.get("name_field") else ""
        short = ids.get("short_field").text.strip() if ids.get("short_field") else ""
        desc = ids.get("desc_field").text.strip() if ids.get("desc_field") else ""
        addr = ids.get("addr_field").text.strip() if ids.get("addr_field") else ""
        raw_images = ids.get("images_field").text if ids.get("images_field") else ""

        # Разбираем изображения: одна ссылка на строку, запятые тоже считаем разделителями
        parts = raw_images.replace(",", "\n").splitlines()
        image_urls = [p.strip() for p in parts if p.strip()]

        dm.update_place_basic(place_id, name, short, desc, addr)
        dm.update_place_images(place_id, image_urls)

        # Обновляем список мест на главном экране и в админке
        try:
            from kivy.app import App

            app = App.get_running_app()
            root = app.sm.get_screen("root")
            places_screen = root.ids.get("places_screen")
            if places_screen:
                places_screen.load_places()
            admin_screen = root.ids.get("admin_screen")
            if admin_screen:
                admin_screen.load_places()
        except Exception:
            pass

        # Возвращаемся назад на RootScreen и включаем вкладку Админ
        from kivy.app import App

        app = App.get_running_app()
        app.sm.current = "root"
        try:
            bottom_nav = root.ids.get("bottom_nav")
            if bottom_nav:
                bottom_nav.switch_tab("admin")
        except Exception:
            pass

    def pick_location_on_map(self):
        """Переходит на вкладку Карта и включает режим выбора точки для этого места."""
        if not self.place:
            return
        place_id = self.place.get("id")
        if not place_id:
            return

        from kivy.app import App

        app = App.get_running_app()
        root = app.sm.get_screen("root")
        map_screen = root.ids.get("map_screen") if root and hasattr(root, "ids") else None
        if not map_screen:
            return

        # Включаем режим выбора координат на карте
        if hasattr(map_screen, "enter_pick_mode"):
            map_screen.enter_pick_mode(place_id)

        # Переключаемся на RootScreen и вкладку Карта
        app.sm.current = "root"
        try:
            bottom_nav = root.ids.get("bottom_nav")
            if bottom_nav:
                if hasattr(bottom_nav, "switch_tab"):
                    bottom_nav.switch_tab("map")
                else:
                    bottom_nav.current = "map"
        except Exception:
            pass
