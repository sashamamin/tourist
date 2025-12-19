from kivy.properties import StringProperty

from kivymd.uix.screen import MDScreen

from data.data_manager import DataManager

from datetime import datetime, date
import random


class HomeScreen(MDScreen):
    greeting = StringProperty("")
    rec1 = StringProperty("")
    rec2 = StringProperty("")
    rec3 = StringProperty("")
    today1 = StringProperty("")
    today2 = StringProperty("")
    today3 = StringProperty("")
    place_of_day = StringProperty("")

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.data_manager = DataManager.get_instance()
        self.update_greeting()
        self.update_recommendations()
        self.update_today()
        self.update_place_of_day()

    def on_pre_enter(self, *args):
        super().on_pre_enter(*args)
        self.update_greeting()
        self.update_recommendations()
        self.update_today()
        self.update_place_of_day()
        self._update_static_texts()
    
    def _update_static_texts(self):
        """Обновляет статические тексты в KV файле при смене языка."""
        from kivy.app import App
        app = App.get_running_app()
        
        try:
            # Обновляем тексты кнопок и заголовков
            if hasattr(self, 'ids'):
                if 'what_interests_label' in self.ids:
                    self.ids.what_interests_label.text = app.get_text("what_interests_today")
                if 'btn_audio' in self.ids:
                    self.ids.btn_audio.text = app.get_text("btn_audio_guide")
                if 'btn_tours_home' in self.ids:
                    self.ids.btn_tours_home.text = app.get_text("btn_tours")
                if 'btn_map_home' in self.ids:
                    self.ids.btn_map_home.text = app.get_text("btn_map")
                if 'btn_favorites_home' in self.ids:
                    self.ids.btn_favorites_home.text = app.get_text("btn_favorites")
                if 'recommendations_title_label' in self.ids:
                    self.ids.recommendations_title_label.text = app.get_text("recommendations_title")
                if 'today_in_city_label' in self.ids:
                    self.ids.today_in_city_label.text = app.get_text("today_in_city")
        except Exception:
            pass

    def update_greeting(self):
        from kivy.app import App
        app = App.get_running_app()
        
        city = None
        try:
            city = self.data_manager.get_active_city()
        except Exception:
            city = None
        city_name = city.get("name") if city else app.get_text("city_not_selected")
        self.greeting = f"{app.get_text('city_prefix')} {city_name}"

    def update_recommendations(self):
        from kivy.app import App
        app = App.get_running_app()
        
        dm = self.data_manager
        city = None
        try:
            city = dm.get_active_city()
        except Exception:
            city = None
        city_name = city.get("name") if city else "городе"

        # Время суток для более живых текстов
        hour = datetime.now().hour
        if 6 <= hour < 11:
            day_part = app.get_text("morning")
        elif 11 <= hour < 17:
            day_part = app.get_text("day")
        elif 17 <= hour < 23:
            day_part = app.get_text("evening")
        else:
            day_part = app.get_text("late_night")

        # Рекомендация 1: незавершённый тур или самый популярный
        tours = []
        try:
            tours = dm.get_all_tours_with_progress()
        except Exception:
            tours = []
        rec_tour = None
        for t in tours:
            # ищем туры без completed_at
            if not t.get("completed_at"):
                rec_tour = t
                break
        if not rec_tour and tours:
            # если всё завершено, возьмём первый по популярности/списку
            rec_tour = tours[0]
        if rec_tour:
            title = rec_tour.get("title", "экскурсия")
            self.rec1 = f"1. {app.get_text('rec1_continue').format(day_part, title)}"
        else:
            self.rec1 = f"1. {app.get_text('rec1_no_tours').format(city_name)}"

        # Рекомендация 2: место, которое ещё не было в точках туров
        places = []
        try:
            places = dm.get_all_places()
        except Exception:
            places = []
        used_place_ids = set()
        try:
            from data.data_manager import DataManager as _DM

            # используем те же данные dm, просто обходим точки туров
            for t in tours:
                pts = dm.get_points_for_tour(t["id"])
                for pt in pts:
                    used_place_ids.add(pt.get("place_id"))
        except Exception:
            pass
        candidate_place = None
        for p in places:
            if p.get("id") not in used_place_ids:
                candidate_place = p
                break
        if not candidate_place and places:
            candidate_place = places[0]
        if candidate_place:
            name = candidate_place.get("name", "интересное место")
            self.rec2 = f"2. {app.get_text('rec2_visit').format(name)}"
        else:
            self.rec2 = f"2. {app.get_text('rec2_no_places')}"

        # Рекомендация 3: общее сообщение с учётом времени суток
        if day_part in (app.get_text("morning"), app.get_text("day")):
            self.rec3 = f"3. {app.get_text('rec3_walk').format(city_name)}"
        elif day_part == app.get_text("evening"):
            self.rec3 = f"3. {app.get_text('rec3_evening').format(city_name)}"
        else:
            self.rec3 = f"3. {app.get_text('rec3_plan').format(city_name)}"

    def update_today(self):
        """MVP-блок "Сегодня в городе" на основе туров и мест."""
        from kivy.app import App
        app = App.get_running_app()
        
        dm = self.data_manager
        city = None
        try:
            city = dm.get_active_city()
        except Exception:
            city = None
        city_name = city.get("name") if city else "городе"

        tours = []
        try:
            tours = dm.get_all_tours_with_progress()
        except Exception:
            tours = []

        if tours:
            t = tours[0]
            title = t.get("title", "экскурсия")
            duration = t.get("duration") or 0
            self.today1 = f"• {app.get_text('today_route').format(title, int(duration/60) or 1)}"
        else:
            self.today1 = f"• {app.get_text('today_no_tours').format(city_name)}"

        places = []
        try:
            places = dm.get_all_places()
        except Exception:
            places = []
        if len(places) >= 2:
            p1 = places[0]
            p2 = places[1]
            self.today2 = f"• {app.get_text('today_visit').format(p1.get('name', ''), p2.get('name', ''))}"
        elif places:
            p1 = places[0]
            self.today2 = f"• {app.get_text('today_walk').format(p1.get('name', ''))}"
        else:
            self.today2 = f"• {app.get_text('rec2_no_places')}"

        self.today3 = f"• {app.get_text('today_map').format(city_name)}"

    def update_place_of_day(self):
        """Простая логика "Место дня": одно случайное место в день."""
        from kivy.app import App
        app = App.get_running_app()
        
        dm = self.data_manager
        try:
            places = dm.get_all_places()
        except Exception:
            places = []

        if not places:
            self.place_of_day = app.get_text("place_of_day_no_places")
            return

        # Делаем выбор стабильным в пределах одного календарного дня
        seed = date.today().toordinal()
        rnd = random.Random(seed)
        place = rnd.choice(places)
        name = place.get("name", "интересное место")
        short = place.get("short_desc") or place.get("description", "")
        if short:
            self.place_of_day = f"{app.get_text('place_of_day_prefix')} {name} — {short}"
        else:
            self.place_of_day = f"{app.get_text('place_of_day_prefix')} {name}"

    def _switch_tab(self, tab_name: str):
        from kivy.app import App

        app = App.get_running_app()
        root = app.sm.get_screen("root")
        bottom_nav = root.ids.get("bottom_nav")
        if not bottom_nav:
            return
        if hasattr(bottom_nav, "switch_tab"):
            bottom_nav.switch_tab(tab_name)
        else:
            bottom_nav.current = tab_name

    def open_map(self):
        self._switch_tab("map")

    def open_tours(self):
        self._switch_tab("tours")

    def open_favorites(self):
        self._switch_tab("favorites")

    def open_audio(self):
        # Пока используем экран экскурсии как точку входа в аудиогиды
        self._switch_tab("tours")

    def open_quick_actions(self):
        """Открывает меню быстрых действий при нажатии на FAB."""
        from kivymd.uix.menu import MDDropdownMenu
        from kivy.app import App
        from kivy.metrics import dp
        
        app = App.get_running_app()
        fab = self.ids.get("fab")
        if not fab:
            return
        
        menu_items = [
            {
                "text": app.get_text("quick_search"),
                "viewclass": "OneLineListItem",
                "on_release": lambda x="search": self._handle_quick_action(x),
            },
            {
                "text": app.get_text("quick_new_place"),
                "viewclass": "OneLineListItem",
                "on_release": lambda x="new_place": self._handle_quick_action(x),
            },
            {
                "text": app.get_text("quick_new_route"),
                "viewclass": "OneLineListItem",
                "on_release": lambda x="new_route": self._handle_quick_action(x),
            },
            {
                "text": app.get_text("quick_new_tour"),
                "viewclass": "OneLineListItem",
                "on_release": lambda x="new_tour": self._handle_quick_action(x),
            },
        ]
        
        menu = MDDropdownMenu(
            caller=fab,
            items=menu_items,
            width_mult=4,
        )
        menu.open()

    def _handle_quick_action(self, action):
        """Обрабатывает выбранное быстрое действие."""
        from kivy.app import App
        app = App.get_running_app()
        
        if action == "search":
            self._switch_tab("places")
            self._show_snackbar(app.get_text("quick_search_hint"))
        elif action == "new_place":
            self._switch_tab("map")
            self._show_snackbar(app.get_text("quick_new_place_hint"))
        elif action == "new_route":
            self._switch_tab("routes")
            self._show_snackbar(app.get_text("quick_new_route_hint"))
        elif action == "new_tour":
            app.sm.current = "tour_constructor"
            self._show_snackbar(app.get_text("quick_new_tour_hint"))

    def _show_snackbar(self, message):
        """Показывает уведомление Snackbar."""
        from kivymd.uix.snackbar import Snackbar
        from kivy.metrics import dp
        
        Snackbar(
            text=message,
            snackbar_x="10dp",
            snackbar_y="10dp",
            size_hint_x=0.9,
            bg_color=(0.2, 0.6, 0.8, 1),  # Синий цвет
            duration=2
        ).open()