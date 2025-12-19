from kivy.properties import ListProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout

from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivy.metrics import dp

from data.data_manager import DataManager


class AdminScreen(MDScreen):
    places = ListProperty()
    tours = ListProperty()
    status_text = StringProperty("")

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.data_manager = DataManager.get_instance()
        self._edit_place_dialog = None
        # Первоначальная инициализация: конкретные данные подгружаем в on_pre_enter
        self.status_text = ""

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        from kivy.app import App

        app = App.get_running_app()
        if not getattr(app, "is_admin", False):
            # Если пользователь не админ — показываем сообщение и пустые списки.
            self.status_text = "Доступ только для администратора"
            self.places = []
            self.tours = []
            container_places = self.ids.get("admin_places_list")
            container_tours = self.ids.get("admin_tours_list")
            if container_places:
                container_places.clear_widgets()
            if container_tours:
                container_tours.clear_widgets()
            return

        # Админ: подгружаем списки городов, мест и экскурсий.
        self.status_text = "Режим администратора"
        self.load_cities_admin()
        self.load_places()
        self.load_tours()

    def add_place_quick(self):
        """Быстрое добавление места с минимальным набором полей (MVP)."""
        from kivy.app import App

        app = App.get_running_app()
        if not getattr(app, "is_admin", False):
            return

        dm = self.data_manager
        # Координаты по умолчанию — центр активного города, чтобы маркер
        # сразу появился на карте.
        active_city = dm.get_active_city() or {}
        default_lat = active_city.get("center_lat")
        default_lon = active_city.get("center_lon")
        city_id = active_city.get("id") if active_city else 1
        cur = dm.conn.cursor()
        cur.execute("SELECT MAX(id) FROM places")
        row = cur.fetchone()
        next_id = (row[0] or 0) + 1

        place = {
            "id": next_id,
            "name": f"Новое место #{next_id}",
            "name_ru": f"Новое место #{next_id}",
            "name_en": f"New place #{next_id}",
            "category": "sight",
            "description": "",
            "description_ru": "",
            "description_en": "",
            "short_desc": "",
            "short_desc_ru": "",
            "short_desc_en": "",
            "lat": default_lat,
            "lon": default_lon,
            "address": "",
            "phone": "",
            "website": "",
            "price": "",
            "hours": "",
            "rating": None,
            "image_urls": [],
            # Привязываем место к активному городу, чтобы оно фигурировало
            # только в его списке и на его карте.
            "city_id": city_id,
        }

        dm.insert_place(place)
        self.load_places()

        # Обновляем экран "Места", чтобы новое место сразу появилось в основном списке
        try:
            root = app.sm.get_screen("root")
            places_screen = root.ids.get("places_screen")
            map_screen = root.ids.get("map_screen")
            if places_screen:
                places_screen.load_places()
            # Обновляем карту, чтобы маркер нового места появился сразу
            if map_screen and hasattr(map_screen, "reset_view"):
                map_screen.reset_view()
        except Exception:
            pass

        self.status_text = f"Добавлено новое место #{next_id}"

    def load_demo_data_all_cities(self):
        """Загружает демо-данные мест и экскурсий для всех предопределённых городов.

        Использует JSON-файлы вида places_<city_id>.json и tours_<city_id>.json
        через DataManager.download_city_data.
        """
        from kivy.app import App

        app = App.get_running_app()
        if not getattr(app, "is_admin", False):
            return

        dm = self.data_manager
        # id городов из _ensure_cities_loaded: 2..6 (1 уже имеет базовые данные)
        for city_id in [2, 3, 4, 5, 6]:
            try:
                dm.download_city_data(city_id)
            except Exception:
                continue

        # Обновляем списки в админке и на основных экранах
        try:
            self.load_places()
            self.load_tours()
            root = app.sm.get_screen("root")
            places_screen = root.ids.get("places_screen")
            map_screen = root.ids.get("map_screen")
            tours_screen = root.ids.get("tours_screen")
            if places_screen and hasattr(places_screen, "load_places"):
                places_screen.load_places()
            if map_screen and hasattr(map_screen, "reset_view"):
                map_screen.reset_view()
            if tours_screen and hasattr(tours_screen, "load_tours"):
                tours_screen.load_tours()
        except Exception:
            pass

        self.status_text = "Демо-данные загружены для всех городов (2–6)"

    def load_cities_admin(self):
        """Загружает список городов для админского экрана."""
        dm = self.data_manager
        cur = dm.conn.cursor()
        try:
            # Новая схема: есть колонка is_active
            cur.execute("SELECT id, name, is_active FROM cities ORDER BY id")
            rows = cur.fetchall()
        except Exception:
            # Старая схема: колонки is_active может не быть, берём только id и name
            try:
                cur.execute("SELECT id, name FROM cities ORDER BY id")
                rows = [(row[0], row[1], 0) for row in cur.fetchall()]
            except Exception:
                return
        container = self.ids.get("admin_cities_list")
        if not container:
            return
        container.clear_widgets()

        from kivymd.uix.list import OneLineAvatarIconListItem, IconRightWidget

        for city_id, name, is_active in rows:
            active_mark = " (активный)" if is_active else ""
            item = OneLineAvatarIconListItem(text=f"#{city_id} — {name}{active_mark}")

            def _on_select(inst, cid=city_id):
                # При клике делаем город активным через ProfileScreen,
                # чтобы карта и остальные экраны сразу обновились.
                from kivy.app import App

                app = App.get_running_app()
                try:
                    root = app.sm.get_screen("root")
                    profile_screen = root.ids.get("profile_screen")
                    if profile_screen and hasattr(profile_screen, "set_active_city"):
                        profile_screen.set_active_city(cid)
                    # после смены города обновляем надпись статуса и список городов
                    self.status_text = f"Активный город: {name}"
                    self.load_cities_admin()
                except Exception:
                    pass

            item.bind(on_release=_on_select)

            def _on_delete_icon(inst, cid=city_id, cname=name):
                self.delete_city(cid, cname)

            icon = IconRightWidget(icon="delete")
            icon.bind(on_release=_on_delete_icon)
            item.add_widget(icon)
            container.add_widget(item)

    def open_add_city_dialog(self):
        """Диалог добавления нового города (только для администратора)."""
        from kivy.app import App
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.dialog import MDDialog

        app = App.get_running_app()
        if not getattr(app, "is_admin", False):
            return

        dm = self.data_manager
        active = dm.get_active_city() or {}

        box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=dp(16),
            size_hint_y=None,
            height=dp(260),
        )

        name_field = MDTextField(
            text="",
            hint_text="Название города",
            mode="rectangle",
        )
        country_field = MDTextField(
            text=active.get("country", "Россия"),
            hint_text="Страна",
            mode="rectangle",
        )
        lat_field = MDTextField(
            text=str(active.get("center_lat", "")),
            hint_text="Широта центра (опционально)",
            mode="rectangle",
        )
        lon_field = MDTextField(
            text=str(active.get("center_lon", "")),
            hint_text="Долгота центра (опционально)",
            mode="rectangle",
        )

        box.add_widget(name_field)
        box.add_widget(country_field)
        box.add_widget(lat_field)
        box.add_widget(lon_field)

        def _save(_btn):
            name = (name_field.text or "").strip()
            country = (country_field.text or "").strip()
            lat_txt = (lat_field.text or "").strip()
            lon_txt = (lon_field.text or "").strip()

            if not name:
                return

            try:
                center_lat = float(lat_txt) if lat_txt else 0.0
                center_lon = float(lon_txt) if lon_txt else 0.0
            except ValueError:
                center_lat = 0.0
                center_lon = 0.0

            new_id = dm.add_city(
                name=name,
                country=country or "Россия",
                center_lat=center_lat,
                center_lon=center_lon,
                is_downloaded=0,
                download_size=0,
                is_active=0,
            )

            self.status_text = f"Добавлен город #{new_id}: {name}"

            # Делаем новый город активным и обновляем все связанные экраны
            try:
                root = app.sm.get_screen("root")
                profile_screen = root.ids.get("profile_screen")
                if profile_screen and hasattr(profile_screen, "set_active_city"):
                    profile_screen.set_active_city(new_id)
            except Exception:
                pass

            if hasattr(self, "_add_city_dialog") and self._add_city_dialog:
                self._add_city_dialog.dismiss()

        def _cancel(_btn):
            if hasattr(self, "_add_city_dialog") and self._add_city_dialog:
                self._add_city_dialog.dismiss()

        self._add_city_dialog = MDDialog(
            title="Добавить город",
            type="custom",
            content_cls=box,
            buttons=[
                MDFlatButton(text="Отмена", on_release=_cancel),
                MDFlatButton(text="Сохранить", on_release=_save),
            ],
        )
        self._add_city_dialog.open()

    # --- Управление пользователем (MVP: один пользователь из настроек приложения) ---

    def open_user_admin_dialog(self):
        """Переходит на отдельный экран управления пользователем."""
        from kivy.app import App

        app = App.get_running_app()
        app.sm.current = "users_admin"

    def open_stats_dialog(self):
        """Показывает общую статистику по данным приложения.

        Включает количество городов, мест, экскурсий, отзывов и средний рейтинг.
        """
        from kivymd.uix.dialog import MDDialog

        dm = self.data_manager
        cur = dm.conn.cursor()

        # Количество городов
        try:
            cur.execute("SELECT COUNT(*) FROM cities")
            cities_count = cur.fetchone()[0] or 0
        except Exception:
            cities_count = 0

        # Количество мест
        try:
            cur.execute("SELECT COUNT(*) FROM places")
            places_count = cur.fetchone()[0] or 0
        except Exception:
            places_count = 0

        # Количество экскурсий
        try:
            cur.execute("SELECT COUNT(*) FROM tours")
            tours_count = cur.fetchone()[0] or 0
        except Exception:
            tours_count = 0

        # Количество отзывов
        try:
            cur.execute("SELECT COUNT(*) FROM reviews")
            reviews_count = cur.fetchone()[0] or 0
        except Exception:
            reviews_count = 0

        # Средний рейтинг по местам
        avg_rating_places = None
        try:
            cur.execute("SELECT AVG(rating) FROM places WHERE rating IS NOT NULL")
            row = cur.fetchone()
            if row and row[0] is not None:
                avg_rating_places = float(row[0])
        except Exception:
            avg_rating_places = None

        # При желании можно добавить средний рейтинг по отзывам, если есть поле rating
        avg_rating_text = "Нет данных по рейтингу"
        if avg_rating_places is not None:
            avg_rating_text = f"Средний рейтинг мест: {avg_rating_places:.1f}"

        text_lines = [
            f"Городов: {cities_count}",
            f"Мест: {places_count}",
            f"Экскурсий: {tours_count}",
            f"Отзывов: {reviews_count}",
            avg_rating_text,
        ]
        text = "\n".join(text_lines)

        self._stats_dialog = MDDialog(
            title="Статистика",
            text=text,
        )
        self._stats_dialog.open()

    # --- Техподдержка ---

    def open_support_admin_dialog(self):
        """Список пользователей, написавших в поддержку, для выбора диалога."""
        from kivy.app import App
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.list import MDList, TwoLineListItem
        from kivymd.uix.dialog import MDDialog
        from kivy.metrics import dp

        app = App.get_running_app()
        if not getattr(app, "is_admin", False):
            return

        dm = self.data_manager
        users = dm.get_support_users_with_last_message() or []
        if not users:
            self.status_text = "Нет сообщений поддержки"
            return

        box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(4),
            padding=dp(8),
            size_hint_y=None,
            height=dp(300),
        )

        lst = MDList()

        def make_open(user_id, username):
            def _open(_inst):
                if hasattr(self, "_support_users_dialog") and self._support_users_dialog:
                    self._support_users_dialog.dismiss()
                self.open_support_conversation(user_id, username)

            return _open

        for u in users:
            username = u.get("username", "")
            last_msg = (u.get("last_message") or "").strip()
            item = TwoLineListItem(
                text=username,
                secondary_text=last_msg if last_msg else "(нет текста)",
            )
            item.bind(on_release=make_open(u.get("user_id"), username))
            lst.add_widget(item)

        box.add_widget(lst)

        self._support_users_dialog = MDDialog(
            title="Сообщения пользователей",
            type="custom",
            content_cls=box,
            size_hint=(0.9, None),
        )
        self._support_users_dialog.open()

    def open_support_conversation(self, user_id: int, username: str):
        """Показывает переписку с конкретным пользователем и даёт отправить ответ."""
        from kivy.app import App
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.dialog import MDDialog
        from kivy.metrics import dp

        app = App.get_running_app()
        if not getattr(app, "is_admin", False):
            return

        dm = self.data_manager
        messages = dm.get_support_messages_for_user(user_id) or []

        lines = []
        for msg in messages[-20:]:  # показываем последние 20 сообщений
            prefix = "Админ: " if msg.get("is_admin_sender") else "Пользователь: "
            lines.append(prefix + (msg.get("message") or ""))
        history_text = "\n\n".join(lines) if lines else "Сообщений пока нет"

        box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=dp(16),
            size_hint_y=None,
            height=dp(360),
        )

        history_label = MDLabel(
            text=history_text,
            halign="left",
        )

        reply_field = MDTextField(
            text="",
            hint_text="Ответ пользователю",
            mode="rectangle",
            multiline=True,
        )

        box.add_widget(history_label)
        box.add_widget(reply_field)

        def _send(_btn):
            text = (reply_field.text or "").strip()
            if not text:
                return
            dm.add_support_message(user_id=user_id, is_admin_sender=True, message=text)
            self.status_text = f"Ответ пользователю {username} отправлен"
            if hasattr(self, "_support_conversation_dialog") and self._support_conversation_dialog:
                self._support_conversation_dialog.dismiss()

        self._support_conversation_dialog = MDDialog(
            title=f"Поддержка: {username}",
            type="custom",
            content_cls=box,
            size_hint=(0.9, None),
            buttons=[
                MDFlatButton(text="Закрыть", on_release=lambda _b: self._support_conversation_dialog.dismiss()),
                MDFlatButton(text="Отправить", on_release=_send),
            ],
        )
        self._support_conversation_dialog.open()

    def load_places(self):
        """Загружает список мест в админке.

        Использует тот же DataManager.get_all_places, что и пользовательский экран
        "Места", чтобы гарантировать одинаковое поведение.
        """
        dm = self.data_manager
        try:
            all_places = dm.get_all_places() or []
        except Exception:
            all_places = []
        # self.places храним как список (id, name) для простоты
        self.places = [(p.get("id"), p.get("name")) for p in all_places]

        container = self.ids.get("admin_places_list")
        if not container:
            return
        container.clear_widgets()

        from kivymd.uix.list import OneLineAvatarIconListItem, IconRightWidget

        for place_id, name in self.places:
            if place_id is None:
                continue
            item = OneLineAvatarIconListItem(text=f"#{place_id} — {name}")

            def _make_delete(inst, pid=place_id):
                self.delete_place(pid)

            right = IconRightWidget(icon="delete")
            right.bind(on_release=_make_delete)
            item.add_widget(right)

            def _open_dialog(inst, pid=place_id):
                self.open_place_dialog(pid)

            item.bind(on_release=_open_dialog)
            container.add_widget(item)

    def open_place_dialog(self, place_id):
        """Отдельное окно (диалог) с информацией о месте и кнопкой редактирования."""
        from kivy.app import App
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton

        app = App.get_running_app()
        if not getattr(app, "is_admin", False):
            return

        dm = self.data_manager
        place = dm.get_place(place_id)
        if not place:
            self.status_text = f"Место #{place_id} не найдено"
            return

        name = place.get("name", "")
        address = place.get("address", "") or "Адрес не указан"
        desc = place.get("description", "") or "Описание не указано"

        text_lines = [
            f"Название: {name}",
            f"Адрес: {address}",
            "",  # пустая строка для разделения
            desc,
        ]
        dialog_text = "\n".join(text_lines)

        def _open_editor(_btn):
            # Переходим в существующий экран редактирования места
            try:
                edit_screen = app.sm.get_screen("place_edit")
                edit_screen.set_place(place)
                app.sm.current = "place_edit"
            except Exception:
                self.status_text = f"Не удалось открыть редактор для места #{place_id}"
            if hasattr(self, "_place_dialog") and self._place_dialog:
                self._place_dialog.dismiss()

        def _close(_btn):
            if hasattr(self, "_place_dialog") and self._place_dialog:
                self._place_dialog.dismiss()

        self._place_dialog = MDDialog(
            title=f"Место #{place_id}",
            text=dialog_text,
            buttons=[
                MDFlatButton(text="Закрыть", on_release=_close),
                MDFlatButton(text="Редактировать", on_release=_open_editor),
            ],
        )
        self._place_dialog.open()

    def load_tours(self):
        """Загружает список экскурсий в админке.

        Использует DataManager.get_all_tours, как пользовательский экран
        "Экскурсии", чтобы списки совпадали.
        """
        dm = self.data_manager
        try:
            all_tours = dm.get_all_tours() or []
        except Exception:
            all_tours = []
        self.tours = [(t.get("id"), t.get("title")) for t in all_tours]

        container = self.ids.get("admin_tours_list")
        if not container:
            return
        container.clear_widgets()

        from kivymd.uix.list import OneLineAvatarIconListItem, IconRightWidget

        for tour_id, title in self.tours:
            if tour_id is None:
                continue
            item = OneLineAvatarIconListItem(text=f"#{tour_id} — {title}")

            def _make_delete(inst, tid=tour_id):
                self.delete_tour(tid)

            icon = IconRightWidget(icon="delete")
            icon.bind(on_release=_make_delete)
            item.add_widget(icon)

            def _on_item_tap(inst, tid=tour_id):
                self.open_tour_actions_dialog(tid)

            item.bind(on_release=_on_item_tap)
            container.add_widget(item)

    def add_tour_quick(self):
        from kivy.app import App

        app = App.get_running_app()
        if not getattr(app, "is_admin", False):
            return
        dm = self.data_manager
        new_id = dm.insert_tour_quick()
        # Загружаем только что созданный тур и открываем его в редакторе
        tour = dm.get_tour(new_id)
        if not tour:
            self.load_tours()
            return
        self.load_tours()

        edit_screen = app.sm.get_screen("tour_edit")
        edit_screen.set_tour(tour)
        app.sm.current = "tour_edit"

    def open_tour_actions_dialog(self, tour_id):
        """Диалог выбора действия над экскурсией: карточка или маршрут."""
        from kivymd.uix.button import MDFlatButton

        def _open_card(_btn):
            if hasattr(self, "_tour_actions_dialog") and self._tour_actions_dialog:
                self._tour_actions_dialog.dismiss()
            self.open_edit_tour(tour_id)

        def _open_route(_btn):
            if hasattr(self, "_tour_actions_dialog") and self._tour_actions_dialog:
                self._tour_actions_dialog.dismiss()
            from kivy.app import App

            app = App.get_running_app()
            dm = self.data_manager
            tour = dm.get_tour(tour_id)
            if not tour:
                self.status_text = f"Экскурсия #{tour_id} не найдена"
                return

            try:
                edit_screen = app.sm.get_screen("tour_route_edit")
                edit_screen.set_tour(tour)
                app.sm.current = "tour_route_edit"
            except Exception:
                # На случай, если экран не зарегистрирован
                self.status_text = f"Не удалось открыть редактор маршрута для экскурсии #{tour_id}"

        self._tour_actions_dialog = MDDialog(
            title=f"Экскурсия #{tour_id}",
            text="Что вы хотите изменить?",
            buttons=[
                MDFlatButton(text="Карточка", on_release=_open_card),
                MDFlatButton(text="Маршрут", on_release=_open_route),
            ],
        )
        self._tour_actions_dialog.open()

    def delete_place(self, place_id):
        """Показывает диалог подтверждения перед удалением места."""
        from kivy.app import App
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton

        app = App.get_running_app()
        if not getattr(app, "is_admin", False):
            return

        def _confirm(_btn):
            dm = self.data_manager
            dm.delete_place(place_id)
            self.load_places()

            # Обновляем экран "Места"
            try:
                root = app.sm.get_screen("root")
                places_screen = root.ids.get("places_screen")
                if places_screen:
                    places_screen.load_places()
            except Exception:
                pass

            self.status_text = f"Место #{place_id} удалено"
            if hasattr(self, "_delete_place_dialog") and self._delete_place_dialog:
                self._delete_place_dialog.dismiss()

        def _cancel(_btn):
            if hasattr(self, "_delete_place_dialog") and self._delete_place_dialog:
                self._delete_place_dialog.dismiss()

        self._delete_place_dialog = MDDialog(
            title="Удалить место",
            text=f"Вы уверены, что хотите удалить место #{place_id}?",
            buttons=[
                MDFlatButton(text="Отмена", on_release=_cancel),
                MDFlatButton(text="Да", on_release=_confirm),
            ],
        )
        self._delete_place_dialog.open()

    def delete_city(self, city_id, name):
        """Диалог подтверждения удаления города."""
        from kivy.app import App
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton

        app = App.get_running_app()
        if not getattr(app, "is_admin", False):
            return

        # Не даём удалить текущий активный город, чтобы приложение не осталось без города
        dm = self.data_manager
        active = dm.get_active_city() or {}
        if active.get("id") == city_id:
            self.status_text = "Нельзя удалить активный город"
            return

        def _confirm(_btn):
            dm.delete_city(city_id)
            self.load_cities_admin()
            self.status_text = f"Город #{city_id} ({name}) удалён"
            if hasattr(self, "_delete_city_dialog") and self._delete_city_dialog:
                self._delete_city_dialog.dismiss()

        def _cancel(_btn):
            if hasattr(self, "_delete_city_dialog") and self._delete_city_dialog:
                self._delete_city_dialog.dismiss()

        self._delete_city_dialog = MDDialog(
            title="Удалить город",
            text=f"Вы уверены, что хотите удалить город '{name}' (#{city_id})?",
            buttons=[
                MDFlatButton(text="Отмена", on_release=_cancel),
                MDFlatButton(text="Да", on_release=_confirm),
            ],
        )
        self._delete_city_dialog.open()

    def delete_tour(self, tour_id):
        """Показывает диалог подтверждения перед удалением экскурсии."""
        from kivy.app import App
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton

        app = App.get_running_app()
        if not getattr(app, "is_admin", False):
            return

        def _confirm(_btn):
            dm = self.data_manager
            dm.delete_tour(tour_id)
            self.load_tours()

            # Обновляем связанные экраны при необходимости (например, рекомендации по турам)
            try:
                root = app.sm.get_screen("root")
                tours_screen = root.ids.get("tours_screen")
                if tours_screen:
                    tours_screen.load_tours()
            except Exception:
                pass

            self.status_text = f"Экскурсия #{tour_id} удалена"
            if hasattr(self, "_delete_tour_dialog") and self._delete_tour_dialog:
                self._delete_tour_dialog.dismiss()

        def _cancel(_btn):
            if hasattr(self, "_delete_tour_dialog") and self._delete_tour_dialog:
                self._delete_tour_dialog.dismiss()

        self._delete_tour_dialog = MDDialog(
            title="Удалить экскурсию",
            text=f"Вы уверены, что хотите удалить экскурсию #{tour_id}?",
            buttons=[
                MDFlatButton(text="Отмена", on_release=_cancel),
                MDFlatButton(text="Да", on_release=_confirm),
            ],
        )
        self._delete_tour_dialog.open()

    def open_edit_place(self, place_id):
        from kivy.app import App

        app = App.get_running_app()
        if not getattr(app, "is_admin", False):
            return
        dm = self.data_manager
        place = dm.get_place(place_id)
        if not place:
            return

        # Переходим на отдельный экран редактирования места
        edit_screen = app.sm.get_screen("place_edit")
        edit_screen.set_place(place)
        app.sm.current = "place_edit"

    def open_edit_tour(self, tour_id):
        from kivy.app import App

        app = App.get_running_app()
        if not getattr(app, "is_admin", False):
            return
        dm = self.data_manager
        tour = dm.get_tour(tour_id)
        if not tour:
            return

        edit_screen = app.sm.get_screen("tour_edit")
        edit_screen.set_tour(tour)
        app.sm.current = "tour_edit"
