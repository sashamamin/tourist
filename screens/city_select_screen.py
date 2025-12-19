from kivy.properties import ListProperty

from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.list import MDList

from data.data_manager import DataManager


class CitySelectScreen(MDScreen):
    cities = ListProperty()

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.data_manager = DataManager.get_instance()
        self.load_cities()

    def load_cities(self):
        cur = self.data_manager.conn.cursor()
        cur.execute("SELECT id, name, country, is_downloaded, is_active FROM cities ORDER BY id")
        rows = cur.fetchall()
        self.cities = [
            {
                "id": r[0],
                "name": r[1],
                "country": r[2],
                "is_downloaded": bool(r[3]),
                "is_active": bool(r[4]),
            }
            for r in rows
        ]

        container = self.ids.get("cities_list")
        if not container:
            return
        if isinstance(container, MDList):
            container.clear_widgets()
            for city in self.cities:
                btn = MDRaisedButton(text=city["name"], size_hint_x=1)

                def make_handler(cid):
                    return lambda x: self.select_city(cid)

                btn.bind(on_release=make_handler(city["id"]))
                container.add_widget(btn)

    def select_city(self, city_id):
        from kivy.app import App

        app = App.get_running_app()
        self.data_manager.set_active_city(city_id)
        app.sm.current = "root"
