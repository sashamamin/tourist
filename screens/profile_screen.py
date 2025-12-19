from kivy.properties import ListProperty, StringProperty, NumericProperty

from kivymd.uix.screen import MDScreen
from kivymd.uix.list import TwoLineRightIconListItem, IconRightWidget
from kivymd.uix.dialog import MDDialog

from data.data_manager import DataManager


class ProfileScreen(MDScreen):
    theme_style = StringProperty("Light")
    cities = ListProperty()
    level_text = StringProperty("")
    stats_cities = StringProperty("")
    stats_places = StringProperty("")
    stats_tours = StringProperty("")
    stats_routes = StringProperty("")
    stats_reviews = StringProperty("")
    achievements_text = StringProperty("")
    stats_summary = StringProperty("")
    progress_label = StringProperty("")
    progress_percent = NumericProperty(0)
    language = StringProperty("Русский")
    profile_title = StringProperty("Профиль и настройки")
    stats_title = StringProperty("Моя статистика:")
    achievements_title = StringProperty("Достижения:")
    cities_title = StringProperty("Мои города:")

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.data_manager = DataManager.get_instance()
        # Загружаем язык из настроек приложения, если доступно
        load_lang = getattr(self.app, "_load_language", None)
        if callable(load_lang):
            try:
                self.language = load_lang()
            except Exception:
                pass
        self.load_cities()
        self.update_stats()

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self.load_cities()
        self.update_stats()

    def show_about(self):
        if hasattr(self, "_about_dialog") and self._about_dialog:
            self._about_dialog.open()
            return

        app = self.app
        title = "City Guide"
        text = """Городской гид по Москве.

Исследуйте интересные места, проходите экскурсии,
собирайте достижения и отслеживайте прогресс исследования города.
Приложение работает офлайн и использует карту OpenStreetMap."""
        try:
            lang = getattr(app, "get_language_code", lambda: "ru")()
        except Exception:
            lang = "ru"
        if str(lang).startswith("en"):
            title = "City Guide"
            text = (
                "City guide for Moscow. Explore points of interest, take tours, "
                "collect achievements and track how much of the city you have explored. "
                "Works offline and uses OpenStreetMap."
            )

        self._about_dialog = MDDialog(title=title, text=text)
        self._about_dialog.open()

    def toggle_theme(self):
        app = self.app
        if app.theme_cls.theme_style == "Light":
            app.theme_cls.theme_style = "Dark"
            self.theme_style = "Dark"
        else:
            app.theme_cls.theme_style = "Light"
            self.theme_style = "Light"
        # Сохраняем выбранную тему в настройках приложения, если есть соответствующий метод
        save_method = getattr(app, "save_theme_style", None)
        if callable(save_method):
            save_method(self.theme_style)

    def toggle_language(self):
        """Простой переключатель языка по кругу (UI-заглушка)."""
        langs = ["Русский", "English", "中文", "Español"]
        try:
            idx = langs.index(self.language)
        except ValueError:
            idx = 0
        self.language = langs[(idx + 1) % len(langs)]

        # Сохраняем выбор в настройки приложения, если есть метод
        save_lang = getattr(self.app, "save_language", None)
        if callable(save_lang):
            try:
                save_lang(self.language)
            except Exception:
                pass

        # Обновляем текстовую статистику и заголовки под новый язык
        self.update_stats()

        # Обновляем код языка в приложении, чтобы KV-подписи (вкладки и заголовки)
        # могли сразу перестроиться
        app = self.app
        try:
            app.ui_language = app.get_language_code()
        except Exception:
            pass

        # Обновляем все экраны для нового языка
        self._refresh_all_screens()

    def load_cities(self):
        dm = self.data_manager
        cur = dm.conn.cursor()
        # базовая информация о городах
        cur.execute(
            "SELECT id, name, country, is_downloaded, is_active FROM cities ORDER BY id"
        )
        rows = cur.fetchall()
        cities = []
        for row in rows:
            city_id, name, country, is_downloaded, is_active = row
            # считаем количество мест и экскурсий в этом городе
            cur.execute("SELECT COUNT(*) FROM places WHERE city_id = ?", (city_id,))
            places_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM tours WHERE city_id = ?", (city_id,))
            tours_count = cur.fetchone()[0]
            cities.append(
                {
                    "id": city_id,
                    "name": name,
                    "country": country,
                    "is_downloaded": bool(is_downloaded),
                    "is_active": bool(is_active),
                    "places_count": places_count,
                    "tours_count": tours_count,
                }
            )
        self.cities = cities

        container = self.ids.get("cities_list")
        if not container:
            return
        container.clear_widgets()
        for city in self.cities:
            title = city["name"]
            subtitle = f"Точек: {city['places_count']}  •  Экскурсий: {city['tours_count']}"
            if city["is_active"]:
                subtitle += "  •  Активный"
            item = TwoLineRightIconListItem(text=title, secondary_text=subtitle)

            def make_active(inst, cid=city["id"]):
                self.set_active_city(cid)

            item.bind(on_release=make_active)

            # правая иконка: скачан / не скачан
            icon_name = "cloud-check" if city["is_downloaded"] else "cloud-download"
            right = IconRightWidget(icon=icon_name)

            def download_city(inst, cid=city["id"]):
                self.download_city(cid)

            right.bind(on_release=download_city)
            item.add_widget(right)
            container.add_widget(item)

    def update_stats(self):
        dm = self.data_manager
        cur = dm.conn.cursor()

        # Для профиля фиксируем русский язык (is_en всегда False),
        # чтобы все надписи были на русском.
        self.language = "Русский"
        is_en = False

        # Сколько городов пользователь когда-либо делал активными/скачивал
        cur.execute("SELECT COUNT(DISTINCT city_id) FROM user_cities")
        cities_count = cur.fetchone()[0] or 0
        if is_en:
            self.stats_cities = f"Cities visited: {cities_count}"
        else:
            self.stats_cities = f"Городов посещено: {cities_count}"

        # Сколько точек в избранном считаем как посещённые (MVP)
        cur.execute("SELECT COUNT(DISTINCT place_id) FROM favorites WHERE user_id = 1")
        places_count = cur.fetchone()[0] or 0
        if is_en:
            self.stats_places = f"Places visited: {places_count}"
        else:
            self.stats_places = f"Точек посещено: {places_count}"

        # Сколько экскурсий завершено
        cur.execute(
            "SELECT COUNT(*) FROM user_tours WHERE user_id = 1 AND completed_at IS NOT NULL AND completed_at != ''"
        )
        tours_completed = cur.fetchone()[0] or 0
        if is_en:
            self.stats_tours = f"Tours completed: {tours_completed}"
        else:
            self.stats_tours = f"Экскурсий завершено: {tours_completed}"

        # Маршруты (MVP) считаем как количество начатых или завершённых экскурсий
        cur.execute(
            "SELECT COUNT(*) FROM user_tours WHERE user_id = 1"
        )
        routes_count = cur.fetchone()[0] or 0
        self.stats_routes = (
            f"Routes: {routes_count}" if is_en else f"Маршрутов: {routes_count}"
        )

        # Количество отзывов пользователя (если таблица reviews есть)
        reviews_count = 0
        try:
            cur.execute("SELECT COUNT(*) FROM reviews WHERE user_id = 1")
            reviews_count = cur.fetchone()[0] or 0
        except Exception:
            reviews_count = 0
        self.stats_reviews = (
            f"Reviews: {reviews_count}" if is_en else f"Отзывов: {reviews_count}"
        )

        # Простейшая система уровней по числу завершённых экскурсий
        if tours_completed >= 15:
            level_name = "Master Guide" if is_en else "Мастер-гид"
        elif tours_completed >= 8:
            level_name = "City Explorer" if is_en else "Исследователь города"
        elif tours_completed >= 3:
            level_name = "Traveler" if is_en else "Путешественник"
        else:
            level_name = "Newbie" if is_en else "Новичок"
        if is_en:
            self.level_text = f"Level: {level_name} ({tours_completed})"
        else:
            self.level_text = f"Уровень: {level_name} ({tours_completed})"

        # Сводная строка статистики для красивого блока
        if is_en:
            self.stats_summary = (
                f"🏙 Cities: {cities_count}   "
                f"📍 Places: {places_count}   "
                f"🚶 Routes: {routes_count}   "
                f"⭐ Reviews: {reviews_count}"
            )
        else:
            self.stats_summary = (
                f"🏙 Городов: {cities_count}   "
                f"📍 Мест: {places_count}   "
                f"🚶 Маршрутов: {routes_count}   "
                f"⭐ Отзывов: {reviews_count}"
            )

        # Прогресс исследования города: посещённые места / все места (по MVP-логике)
        cur.execute("SELECT COUNT(*) FROM places")
        total_places = cur.fetchone()[0] or 0
        if total_places > 0:
            percent = int(100 * min(places_count, total_places) / total_places)
        else:
            percent = 0
        self.progress_percent = percent
        if is_en:
            self.progress_label = f"City explored: {percent}% of places"
        else:
            self.progress_label = f"Исследовано: {percent}% точек города"

        # Достижения по простым порогам
        achievements = []
        if places_count >= 20:
            achievements.append(
                "🥇 Explorer" if is_en else "🥇 Исследователь"
            )
        if reviews_count >= 5:
            achievements.append(
                "🥈 Active Reviewer" if is_en else "🥈 Активный критик"
            )
        if tours_completed >= 3:
            achievements.append(
                "🥉 Tour Lover" if is_en else "🥉 Любитель экскурсий"
            )
        if not achievements:
            achievements.append(
                "No achievements yet — time to explore!"
                if is_en
                else "Пока без достижений — самое время начать путешествовать!"
            )
        self.achievements_text = "\n".join(achievements)

        # Заголовки для профиля
        if is_en:
            self.profile_title = "Profile & Settings"
            self.stats_title = "My statistics:"
            self.achievements_title = "Achievements:"
            self.cities_title = "My cities:"
        else:
            self.profile_title = "Профиль и настройки"
            self.stats_title = "Моя статистика:"
            self.achievements_title = "Достижения:"
            self.cities_title = "Мои города:"

    def set_active_city(self, city_id):
        """Делает город активным и обновляет связанные экраны.

        Чтобы пользователь сразу увидел новый контент по выбранному городу,
        перезагружаем списки мест/экскурсий и связанные экраны.
        """
        from kivy.app import App

        self.data_manager.set_active_city(city_id)
        self.load_cities()

        # Обновляем основные экраны под новый активный город
        try:
            app = App.get_running_app()
            root = app.sm.get_screen("root")
            if not root:
                return

            home_screen = root.ids.get("home_screen")
            map_screen = root.ids.get("map_screen")
            places_screen = root.ids.get("places_screen")
            tours_screen = root.ids.get("tours_screen")
            favorites_screen = root.ids.get("favorites_screen")
            routes_screen = root.ids.get("routes_screen")

            if home_screen:
                # обновляем приветствие (город вверху), рекомендации и место дня
                if hasattr(home_screen, "update_greeting"):
                    home_screen.update_greeting()
                if hasattr(home_screen, "update_place_of_day"):
                    home_screen.update_place_of_day()
                if hasattr(home_screen, "update_recommendations"):
                    home_screen.update_recommendations()
                if hasattr(home_screen, "update_today"):
                    home_screen.update_today()

            # Обновляем карту: центр и маркеры по новому городу
            if map_screen and hasattr(map_screen, "reset_view"):
                map_screen.reset_view()

            if places_screen:
                places_screen.load_places()

            if tours_screen:
                tours_screen.load_tours()

            if favorites_screen:
                favorites_screen.load_favorites()

            if routes_screen and hasattr(routes_screen, "load_places"):
                routes_screen.load_places()

        except Exception:
            # Если что-то пошло не так, просто не падаем — город уже переключён
            pass

    def download_city(self, city_id):
        # Для пользователя это просто пометка, что город скачан (без реальной загрузки JSON)
        cur = self.data_manager.conn.cursor()
        cur.execute("UPDATE cities SET is_downloaded = 1 WHERE id = ?", (city_id,))
        self.data_manager.conn.commit()
        self.load_cities()

    def refresh_data(self):
        """Перезагружает данные мест из JSON и обновляет связанные экраны.

        Используется пунктом меню "Обновить данные" в профиле, чтобы
        подтянуть изменения в places.json (в том числе локализованные поля).
        """
        try:
            self.data_manager.reload_places_from_json()
        except Exception:
            return

        # Обновляем список мест, маршрутов и избранного
        try:
            from kivy.app import App

            app = App.get_running_app()
            root = app.sm.get_screen("root")
            places_screen = root.ids.get("places_screen")
            routes_screen = root.ids.get("routes_screen")
            favorites_screen = root.ids.get("favorites_screen")
            if places_screen:
                places_screen.load_places()
            if routes_screen:
                routes_screen.load_places()
            if favorites_screen:
                favorites_screen.load_favorites()
        except Exception:
            pass

    def _refresh_all_screens(self):
        """Обновляет все экраны при смене языка."""
        from kivy.app import App
        from kivy.clock import Clock
        app = App.get_running_app()
        
        # Используем Clock для обновления после того, как ui_language обновится
        def _update():
            try:
                root = app.sm.get_screen("root")
                if not root:
                    return
                
                # Сначала обновляем ui_language в приложении
                # Это важно сделать ДО пересоздания карточек
                new_lang = app.get_language_code()
                app.ui_language = new_lang
                
                # Обновляем HomeScreen
                home_screen = root.ids.get("home_screen")
                if home_screen:
                    home_screen.update_greeting()
                    home_screen.update_recommendations()
                    home_screen.update_today()
                    home_screen.update_place_of_day()
                    if hasattr(home_screen, '_update_static_texts'):
                        home_screen._update_static_texts()
                
                # Обновляем PlacesScreen - ПЕРЕЗАГРУЖАЕМ карточки с новым языком
                places_screen = root.ids.get("places_screen")
                if places_screen:
                    # Очищаем текущий список и перезагружаем
                    places_screen.load_places()
                    if hasattr(places_screen, '_update_static_texts'):
                        places_screen._update_static_texts()
                
                # Обновляем ToursScreen - ПЕРЕЗАГРУЖАЕМ карточки с новым языком
                tours_screen = root.ids.get("tours_screen")
                if tours_screen:
                    tours_screen.load_tours()
                    if hasattr(tours_screen, '_update_static_texts'):
                        tours_screen._update_static_texts()
                
                # Обновляем FavoritesScreen
                favorites_screen = root.ids.get("favorites_screen")
                if favorites_screen:
                    favorites_screen.load_favorites()
                
                # Обновляем RoutesScreen
                routes_screen = root.ids.get("routes_screen")
                if routes_screen:
                    routes_screen.load_places()
                
                # Обновляем заголовки в ProfileScreen
                self.update_stats()
                
                # Обновляем заголовки TopAppBar во всех экранах
                self._update_top_appbars(root)
                
                # Обновляем все статические тексты в KV файлах
                self._update_kv_texts(root)
                
            except Exception as e:
                import traceback
                traceback.print_exc()
        
        # Даем время на обновление ui_language
        Clock.schedule_once(lambda dt: _update(), 0.2)
    
    def _update_top_appbars(self, root):
        """Обновляет заголовки TopAppBar во всех экранах."""
        from kivy.app import App
        app = App.get_running_app()
        
        try:
            # PlacesScreen
            places_screen = root.ids.get("places_screen")
            if places_screen and hasattr(places_screen, 'ids') and 'places_topbar' in places_screen.ids:
                places_screen.ids.places_topbar.title = places_screen.get_title()
            
            # ToursScreen
            tours_screen = root.ids.get("tours_screen")
            if tours_screen and hasattr(tours_screen, 'ids') and 'tours_topbar' in tours_screen.ids:
                tours_screen.ids.tours_topbar.title = tours_screen.get_title()
            
            # FavoritesScreen - заголовок уже использует app.get_text() в KV
            # RoutesScreen - заголовок уже использует app.get_text() в KV
            
        except Exception:
            pass
    
    def _update_kv_texts(self, root):
        """Обновляет все статические тексты в KV файлах."""
        from kivy.app import App
        app = App.get_running_app()
        
        try:
            # Обновляем все тексты в HomeScreen
            home_screen = root.ids.get("home_screen")
            if home_screen and hasattr(home_screen, '_update_static_texts'):
                home_screen._update_static_texts()
            
            # Обновляем все тексты в PlacesScreen
            places_screen = root.ids.get("places_screen")
            if places_screen and hasattr(places_screen, '_update_static_texts'):
                places_screen._update_static_texts()
            
            # Обновляем все тексты в ToursScreen
            tours_screen = root.ids.get("tours_screen")
            if tours_screen and hasattr(tours_screen, '_update_static_texts'):
                tours_screen._update_static_texts()
            
            # Обновляем тексты в FavoritesScreen
            favorites_screen = root.ids.get("favorites_screen")
            if favorites_screen:
                favorites_screen.load_favorites()
            
            # Обновляем тексты в RoutesScreen
            routes_screen = root.ids.get("routes_screen")
            if routes_screen:
                routes_screen.load_places()
            
        except Exception:
            pass

    # --- Управление аккаунтом пользователя ---

    def show_account_info(self):
        """Окно просмотра и редактирования данных текущего пользователя.

        Позволяет изменить имя, фамилию, e-mail, логин, пароль и кодовое слово,
        а также удалить текущий аккаунт. Пароль можно показать/скрыть.
        """
        from kivy.app import App
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.label import MDLabel
        from kivy.metrics import dp

        app = App.get_running_app()
        base_user = app._get_user()
        if not base_user:
            return

        username = base_user.get("username", "")
        if not username:
            return

        dm = self.data_manager
        db_user = dm.get_user_by_username(username)
        if not db_user:
            return

        user_id = db_user.get("id")
        role = db_user.get("role", "user")

        first_name_val = db_user.get("first_name") or ""
        last_name_val = db_user.get("last_name") or ""
        email_val = db_user.get("email") or ""
        secret_word_val = db_user.get("secret_word") or ""

        box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(10),
            padding=dp(16),
            size_hint_y=None,
            height=dp(420),
        )

        first_name_field = MDTextField(
            text=first_name_val,
            hint_text="Имя",
            mode="rectangle",
        )
        last_name_field = MDTextField(
            text=last_name_val,
            hint_text="Фамилия",
            mode="rectangle",
        )
        email_field = MDTextField(
            text=email_val,
            hint_text="E-mail",
            mode="rectangle",
        )
        username_field = MDTextField(
            text=username,
            hint_text="Логин",
            mode="rectangle",
        )
        password_field = MDTextField(
            text="",
            hint_text="Пароль (оставьте пустым, чтобы не менять)",
            password=True,
            mode="rectangle",
        )
        secret_word_field = MDTextField(
            text=secret_word_val,
            hint_text="Кодовое слово",
            mode="rectangle",
        )

        box.add_widget(first_name_field)
        box.add_widget(last_name_field)
        box.add_widget(email_field)
        box.add_widget(username_field)
        box.add_widget(password_field)
        box.add_widget(secret_word_field)

        def _toggle_password(_btn):
            password_field.password = not password_field.password

        toggle_btn = MDFlatButton(text="Показать пароль", on_release=_toggle_password)
        box.add_widget(toggle_btn)

        def _save(_btn):
            new_first_name = (first_name_field.text or "").strip()
            new_last_name = (last_name_field.text or "").strip()
            new_email = (email_field.text or "").strip()
            new_username = (username_field.text or "").strip()
            new_password = (password_field.text or "").strip() or None
            new_secret_word = (secret_word_field.text or "").strip()

            if not new_username:
                return

            # Обновляем логин/пароль и роль через существующий метод
            dm.update_user(user_id, username=new_username, password_plain=new_password, role=role)

            # Обновляем дополнительные поля профиля
            cur = dm.conn.cursor()
            cur.execute(
                "UPDATE users SET first_name = ?, last_name = ?, email = ?, secret_word = ? WHERE id = ?",
                (new_first_name, new_last_name, new_email, new_secret_word, user_id),
            )
            dm.conn.commit()

            # Если редактируем текущего активного пользователя — обновляем настройки
            store = app._get_settings_store()
            store.put("user", username=new_username, is_admin=(role == "admin"))
            app.is_admin = role == "admin"

            self.update_stats()

            if hasattr(self, "_account_info_dialog") and self._account_info_dialog:
                self._account_info_dialog.dismiss()

        def _delete(_btn):
            # Встроенного admin по безопасности не удаляем
            if username == "admin":
                if hasattr(self, "_account_info_dialog") and self._account_info_dialog:
                    self._account_info_dialog.dismiss()
                return

            dm.delete_user(user_id)

            store = app._get_settings_store()
            if store.exists("user"):
                store.delete("user")
            app.is_admin = False
            app.sm.current = "auth"

            if hasattr(self, "_account_info_dialog") and self._account_info_dialog:
                self._account_info_dialog.dismiss()

        buttons = [
            MDFlatButton(text="Удалить", on_release=_delete),
            MDFlatButton(text="Сохранить", on_release=_save),
        ]

        self._account_info_dialog = MDDialog(
            title="Данные аккаунта",
            type="custom",
            content_cls=box,
            size_hint=(0.9, None),
            buttons=buttons,
        )
        self._account_info_dialog.open()

    def open_edit_account_dialog(self):
        """Окно изменения логина и пароля ТЕКУЩЕГО пользователя.

        Роль (admin/user) здесь не меняем, только логин и пароль.
        """
        from kivy.app import App
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.dialog import MDDialog
        from kivy.metrics import dp

        app = App.get_running_app()
        base_user = app._get_user()
        if not base_user:
            # если пользователь не залогинен, менять нечего
            return

        current_username = base_user.get("username", "")

        box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            padding=dp(16),
            size_hint_y=None,
            height=dp(260),
        )

        username_field = MDTextField(
            text=current_username,
            hint_text="Логин",
            mode="rectangle",
        )
        password_field = MDTextField(
            text="",
            hint_text="Новый пароль (оставьте пустым, чтобы не менять)",
            password=True,
            mode="rectangle",
        )

        box.add_widget(username_field)
        box.add_widget(password_field)

        def _save(_btn):
            new_username = (username_field.text or "").strip()
            new_password = (password_field.text or "").strip() or None
            if not new_username:
                return

            dm = self.data_manager
            db_user = dm.get_user_by_username(current_username)
            if not db_user:
                return

            role = db_user.get("role", "user")
            dm.update_user(db_user["id"], username=new_username, password_plain=new_password, role=role)

            # Обновляем кэш последнего пользователя в настройках
            store = app._get_settings_store()
            store.put("user", username=new_username, is_admin=(role == "admin"))
            app.is_admin = role == "admin"

            # Пересчитываем статистику и заголовки при смене логина (опционально)
            self.update_stats()

            if hasattr(self, "_account_dialog") and self._account_dialog:
                self._account_dialog.dismiss()

        self._account_dialog = MDDialog(
            title="Изменение аккаунта",
            type="custom",
            content_cls=box,
            buttons=[
                MDFlatButton(text="Отмена", on_release=lambda _b: self._account_dialog.dismiss()),
                MDFlatButton(text="Сохранить", on_release=_save),
            ],
        )
        self._account_dialog.open()

    def logout(self):
        """Запрашивает подтверждение выхода из аккаунта."""
        from kivy.app import App
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton

        app = App.get_running_app()

        def _do_logout(_btn):
            store = app._get_settings_store()
            if store.exists("user"):
                store.delete("user")
            app.is_admin = False
            app.sm.current = "auth"

        dialog = MDDialog(
            title="Выход",
            text="Вы действительно хотите выйти из аккаунта?",
            buttons=[
                MDFlatButton(text="Отмена", on_release=lambda _b: dialog.dismiss()),
                MDFlatButton(text="Выйти", on_release=_do_logout),
            ],
        )
        dialog.open()

    def open_support_dialog(self):
        """Диалог обращения в техподдержку (сообщение администратору)."""
        from kivy.app import App
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.label import MDLabel
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.dialog import MDDialog
        from kivy.metrics import dp

        app = App.get_running_app()

        base_user = app._get_user()
        if not base_user:
            return

        username = base_user.get("username")
        if not username:
            return

        dm = self.data_manager
        db_user = dm.get_user_by_username(username)
        if not db_user:
            return

        user_id = db_user.get("id")
        if not user_id:
            return

        box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=dp(16),
            size_hint_y=None,
            height=dp(320),
        )

        # История переписки: последние сообщения
        messages = dm.get_support_messages_for_user(user_id) or []
        lines = []
        for msg in messages[-20:]:  # показываем последние 20 сообщений
            is_admin = bool(msg.get("is_admin_sender"))
            prefix = "Админ: " if is_admin else "Вы: "
            lines.append(prefix + (msg.get("message") or ""))
        history_text = "\n\n".join(lines) if lines else "Сообщений пока нет. Напишите свой вопрос ниже."

        history_label = MDLabel(
            text=history_text,
            halign="left",
        )

        message_field = MDTextField(
            text="",
            hint_text="Опишите вашу проблему или вопрос",
            mode="rectangle",
            multiline=True,
        )

        box.add_widget(history_label)
        box.add_widget(message_field)

        def _send(_btn):
            text = (message_field.text or "").strip()
            if not text:
                return
            dm.add_support_message(user_id=user_id, is_admin_sender=False, message=text)
            if hasattr(self, "_support_dialog") and self._support_dialog:
                self._support_dialog.dismiss()

        self._support_dialog = MDDialog(
            title="Сообщение в поддержку",
            type="custom",
            content_cls=box,
            size_hint=(0.9, None),
            buttons=[
                MDFlatButton(text="Отмена", on_release=lambda _b: self._support_dialog.dismiss()),
                MDFlatButton(text="Отправить", on_release=_send),
            ],
        )
        self._support_dialog.open()

    @property
    def app(self):
        from kivy.app import App

        return App.get_running_app()
