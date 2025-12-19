from kivy.properties import StringProperty, BooleanProperty, ListProperty

from kivymd.uix.screen import MDScreen

from data.data_manager import DataManager


class UsersAdminScreen(MDScreen):
    """Простое окно управления единственным пользователем (MVP).

    Данные берутся из локального хранилища приложения (settings.json)
    через методы CityGuideApp.get_user_info / update_user_info.
    """

    username = StringProperty("")
    password = StringProperty("")
    is_admin = BooleanProperty(False)
    users = ListProperty()  # список словарей пользователей из БД

    def on_pre_enter(self, *args):
        from kivy.app import App

        super().on_pre_enter(*args)
        # При входе просто обновляем список пользователей
        self.refresh_users()

    def refresh_users(self):
        """Заполняет список пользователей для отображения.

        MVP: показываем встроенного admin и локального пользователя из настроек.
        """
        # Берём всех пользователей из БД
        dm = DataManager.get_instance()
        items = dm.get_all_users() or []
        self.users = items

        # обновляем виджет списка, если он есть
        ids = getattr(self, "ids", {})
        container = ids.get("users_list")
        if not container:
            return
        container.clear_widgets()

        from kivymd.uix.list import TwoLineListItem

        for item in self.users:
            text = item.get("username", "")
            role = item.get("role", "user")
            secondary = f"Роль: {role}"
            if text == "admin":
                secondary += " (встроенный)"

            def _on_select(inst, it=item):
                from kivy.app import App
                from kivymd.uix.boxlayout import MDBoxLayout
                from kivymd.uix.textfield import MDTextField
                from kivymd.uix.button import MDFlatButton
                from kivymd.uix.dialog import MDDialog
                from kivy.metrics import dp
                from kivy.uix.switch import Switch
                from kivymd.uix.label import MDLabel

                app = App.get_running_app()

                user_id = it.get("id")
                username = it.get("username", "")
                role = it.get("role", "user")

                # Встроенного admin по логину не удаляем и не меняем роль
                is_built_in_admin = username == "admin"

                start_username = username
                start_is_admin = role == "admin"

                # Загружаем дополнительные поля профиля из БД
                dm = DataManager.get_instance()
                db_user = dm.get_user_by_username(username) or {}
                start_first_name = db_user.get("first_name") or ""
                start_last_name = db_user.get("last_name") or ""
                start_email = db_user.get("email") or ""
                start_secret_word = db_user.get("secret_word") or ""

                box = MDBoxLayout(
                    orientation="vertical",
                    spacing=dp(12),
                    padding=dp(16),
                    size_hint_y=None,
                    height=dp(420),
                )

                first_name_field = MDTextField(
                    text=start_first_name,
                    hint_text="Имя",
                    mode="rectangle",
                )
                last_name_field = MDTextField(
                    text=start_last_name,
                    hint_text="Фамилия",
                    mode="rectangle",
                )
                email_field = MDTextField(
                    text=start_email,
                    hint_text="E-mail",
                    mode="rectangle",
                )
                username_field = MDTextField(
                    text=start_username,
                    hint_text="Логин пользователя",
                    mode="rectangle",
                )
                # По соображениям безопасности пароль не подставляем, поле пустое
                password_field = MDTextField(
                    text="",
                    hint_text="Новый пароль (оставьте пустым, чтобы не менять)",
                    password=True,
                    mode="rectangle",
                )

                secret_word_field = MDTextField(
                    text=start_secret_word,
                    hint_text="Кодовое слово",
                    mode="rectangle",
                )

                role_box = MDBoxLayout(orientation="horizontal", spacing=dp(8))
                role_label = MDLabel(text="Администратор")
                role_switch = Switch(active=start_is_admin, disabled=is_built_in_admin)
                role_box.add_widget(role_label)
                role_box.add_widget(role_switch)

                box.add_widget(first_name_field)
                box.add_widget(last_name_field)
                box.add_widget(email_field)
                box.add_widget(username_field)
                box.add_widget(password_field)
                box.add_widget(secret_word_field)
                box.add_widget(role_box)

                def _save(_btn):
                    new_first_name = (first_name_field.text or "").strip()
                    new_last_name = (last_name_field.text or "").strip()
                    new_email = (email_field.text or "").strip()
                    new_username = (username_field.text or "").strip()
                    new_password = (password_field.text or "").strip() or None
                    new_secret_word = (secret_word_field.text or "").strip()
                    new_role = "admin" if role_switch.active else "user"

                    dm = DataManager.get_instance()
                    # Обновляем основные поля (логин/пароль/роль)
                    dm.update_user(user_id, username=new_username, password_plain=new_password, role=new_role)
                    # Обновляем дополнительные поля профиля
                    cur = dm.conn.cursor()
                    cur.execute(
                        "UPDATE users SET first_name = ?, last_name = ?, email = ?, secret_word = ? WHERE id = ?",
                        (new_first_name, new_last_name, new_email, new_secret_word, user_id),
                    )
                    dm.conn.commit()
                    # Обновляем текущий user в настройках, если редактировали активного
                    base = app._get_user()
                    if base and base.get("username") == username:
                        store = app._get_settings_store()
                        store.put("user", username=new_username, is_admin=(new_role == "admin"))
                        app.is_admin = new_role == "admin"
                    self.refresh_users()
                    dialog.dismiss()

                def _delete(_btn):
                    # Встроенного admin не удаляем
                    if is_built_in_admin:
                        dialog.dismiss()
                        return
                    dm = DataManager.get_instance()
                    dm.delete_user(user_id)
                    # Если удаляем текущего активного пользователя – чистим настройки
                    base = app._get_user()
                    if base and base.get("username") == username:
                        store = app._get_settings_store()
                        if store.exists("user"):
                            store.delete("user")
                        app.is_admin = False
                    self.refresh_users()
                    dialog.dismiss()

                buttons = [MDFlatButton(text="Отмена", on_release=lambda _b: dialog.dismiss())]
                buttons.append(MDFlatButton(text="Удалить", on_release=_delete))
                buttons.append(MDFlatButton(text="Сохранить", on_release=_save))

                dialog = MDDialog(
                    title="Редактирование пользователя",
                    type="custom",
                    content_cls=box,
                    size_hint=(0.9, None),
                    buttons=buttons,
                )
                dialog.open()

            row = TwoLineListItem(text=text, secondary_text=secondary)
            row.bind(on_release=_on_select)
            container.add_widget(row)

    # Методы ниже оставлены для совместимости, сейчас основная логика в диалогах

    def create_user(self):
        from kivy.app import App

        app = App.get_running_app()
        app.update_user_info(self.username, self.password, self.is_admin)
        self.refresh_users()

    def update_user(self):
        self.create_user()

    def delete_user(self):
        from kivy.app import App

        app = App.get_running_app()
        app.delete_user_info()
        self.username = ""
        self.password = ""
        self.is_admin = False
        self.refresh_users()

    def open_create_user_dialog(self):
        """Отдельный диалог создания нового пользователя по кнопке."""
        from kivy.app import App
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.dialog import MDDialog
        from kivy.metrics import dp
        from kivy.uix.switch import Switch
        from kivymd.uix.label import MDLabel

        app = App.get_running_app()

        box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            padding=dp(16),
            size_hint_y=None,
            height=dp(420),
        )

        first_name_field = MDTextField(
            text="",
            hint_text="Имя",
            mode="rectangle",
        )
        last_name_field = MDTextField(
            text="",
            hint_text="Фамилия",
            mode="rectangle",
        )
        email_field = MDTextField(
            text="",
            hint_text="E-mail",
            mode="rectangle",
        )
        username_field = MDTextField(
            text="",
            hint_text="Логин пользователя",
            mode="rectangle",
        )
        password_field = MDTextField(
            text="",
            hint_text="Пароль",
            password=True,
            mode="rectangle",
        )
        secret_word_field = MDTextField(
            text="",
            hint_text="Кодовое слово",
            mode="rectangle",
        )

        role_box = MDBoxLayout(orientation="horizontal", spacing=dp(8))
        role_label = MDLabel(text="Администратор")
        role_switch = Switch(active=False)
        role_box.add_widget(role_label)
        role_box.add_widget(role_switch)

        box.add_widget(first_name_field)
        box.add_widget(last_name_field)
        box.add_widget(email_field)
        box.add_widget(username_field)
        box.add_widget(password_field)
        box.add_widget(secret_word_field)
        box.add_widget(role_box)

        def _save(_btn):
            dm = DataManager.get_instance()
            dm.create_user(
                username=(username_field.text or "").strip(),
                password_plain=(password_field.text or "").strip(),
                role="admin" if role_switch.active else "user",
                first_name=(first_name_field.text or "").strip(),
                last_name=(last_name_field.text or "").strip(),
                email=(email_field.text or "").strip(),
                secret_word=(secret_word_field.text or "").strip(),
            )
            self.refresh_users()
            dialog.dismiss()

        dialog = MDDialog(
            title="Новый пользователь",
            type="custom",
            content_cls=box,
            size_hint=(0.9, None),
            buttons=[
                MDFlatButton(text="Отмена", on_release=lambda _b: dialog.dismiss()),
                MDFlatButton(text="Сохранить", on_release=_save),
            ],
        )
        dialog.open()
