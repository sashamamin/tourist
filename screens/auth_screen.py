from kivy.properties import StringProperty

from kivymd.uix.screen import MDScreen


class AuthScreen(MDScreen):
    mode = StringProperty("login")  # 'login' or 'register'
    username = StringProperty("")
    password = StringProperty("")
    error_text = StringProperty("")
    first_name = StringProperty("")
    last_name = StringProperty("")
    email = StringProperty("")
    secret_word = StringProperty("")

    def switch_mode(self):
        self.error_text = ""
        self.username = (self.username or "").strip()
        self.password = ""
        self.mode = "register" if self.mode == "login" else "login"

    def submit(self):
        from kivy.app import App

        app = App.get_running_app()
        username = (self.username or "").strip()
        password = (self.password or "").strip()

        if self.mode == "register":
            first_name = (self.first_name or "").strip()
            last_name = (self.last_name or "").strip()
            email = (self.email or "").strip()
            secret_word = (self.secret_word or "").strip()

            if not (username and password and first_name and last_name and email and secret_word):
                self.error_text = app.get_text("auth_fill_all")
                return

            ok, msg_key = app.register_user(
                username,
                password,
                first_name=first_name,
                last_name=last_name,
                email=email,
                secret_word=secret_word,
            )
        else:
            if not username or not password:
                self.error_text = app.get_text("auth_fill_all")
                return
            ok, msg_key = app.login_user(username, password)

        if not ok:
            self.error_text = app.get_text(msg_key)
            return

        self.error_text = ""
        # После успешного входа переходим к обычному флоу выбора города
        try:
            app.sm.current = "city_select"
        except Exception:
            app.sm.current = "root"

    def open_password_reset_dialog(self):
        """Открывает первый шаг восстановления пароля: логин + кодовое слово."""
        from kivy.app import App
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.dialog import MDDialog
        from kivy.metrics import dp

        app = App.get_running_app()

        box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            padding=dp(16),
            size_hint_y=None,
            height=dp(200),
        )

        username_field = MDTextField(
            text="",
            hint_text=app.get_text("auth_username"),
            mode="rectangle",
        )
        secret_word_field = MDTextField(
            text="",
            hint_text="Кодовое слово",
            mode="rectangle",
        )

        box.add_widget(username_field)
        box.add_widget(secret_word_field)

        dialog_ref = {"dialog": None}

        def _next_step(_btn):
            from data.data_manager import DataManager

            username = (username_field.text or "").strip()
            secret = (secret_word_field.text or "").strip()
            if not username or not secret:
                self.error_text = app.get_text("auth_fill_all")
                return

            dm = DataManager.get_instance()
            user = dm.get_user_by_username(username)
            if not user or (user.get("secret_word") or "") != secret:
                # Неверное кодовое слово или логин
                self.error_text = app.get_text("auth_wrong_credentials")
                return

            # Закрываем первый диалог и открываем второй шаг
            if dialog_ref["dialog"]:
                dialog_ref["dialog"].dismiss()
            self._open_new_password_dialog(user)

        dialog = MDDialog(
            title="Восстановление пароля",
            type="custom",
            content_cls=box,
            size_hint=(0.9, None),
            buttons=[
                MDFlatButton(text="Отмена", on_release=lambda _b: dialog.dismiss()),
                MDFlatButton(text="Далее", on_release=_next_step),
            ],
        )
        dialog_ref["dialog"] = dialog
        dialog.open()

    def _open_new_password_dialog(self, user: dict):
        """Второй шаг восстановления: ввод нового пароля и подтверждения."""
        from kivy.app import App
        from kivymd.uix.boxlayout import MDBoxLayout
        from kivymd.uix.textfield import MDTextField
        from kivymd.uix.button import MDFlatButton
        from kivymd.uix.dialog import MDDialog
        from kivy.metrics import dp
        from data.data_manager import DataManager

        app = App.get_running_app()

        box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            padding=dp(16),
            size_hint_y=None,
            height=dp(220),
        )

        password1_field = MDTextField(
            text="",
            hint_text=app.get_text("auth_password"),
            password=True,
            mode="rectangle",
        )
        password2_field = MDTextField(
            text="",
            hint_text="Повторите пароль",
            password=True,
            mode="rectangle",
        )

        box.add_widget(password1_field)
        box.add_widget(password2_field)

        def _save_password(_btn):
            pwd1 = (password1_field.text or "").strip()
            pwd2 = (password2_field.text or "").strip()
            if not pwd1 or not pwd2:
                self.error_text = app.get_text("auth_fill_all")
                return
            if pwd1 != pwd2:
                # Пароли не совпадают
                self.error_text = "Пароли не совпадают"
                return

            dm = DataManager.get_instance()
            dm.update_user(user_id=user.get("id"), username=user.get("username"), password_plain=pwd1, role=user.get("role"))

            self.error_text = "Пароль успешно изменён"
            dialog.dismiss()

        dialog = MDDialog(
            title="Новый пароль",
            type="custom",
            content_cls=box,
            size_hint=(0.9, None),
            buttons=[
                MDFlatButton(text="Отмена", on_release=lambda _b: dialog.dismiss()),
                MDFlatButton(text="Сохранить", on_release=_save_password),
            ],
        )
        dialog.open()
