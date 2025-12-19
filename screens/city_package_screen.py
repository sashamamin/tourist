from kivy.properties import DictProperty

from kivymd.uix.screen import MDScreen

from data.data_manager import DataManager


class CityPackageScreen(MDScreen):
    city = DictProperty()

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.data_manager = DataManager.get_instance()

    def set_city(self, city_id: int):
        cur = self.data_manager.conn.cursor()
        cur.execute(
            "SELECT id, name, country, center_lat, center_lon, is_downloaded, download_size FROM cities WHERE id = ?",
            (city_id,),
        )
        row = cur.fetchone()
        if not row:
            self.city = {}
            return
        self.city = {
            "id": row[0],
            "name": row[1],
            "country": row[2],
            "center_lat": row[3],
            "center_lon": row[4],
            "is_downloaded": bool(row[5]),
            "download_size": row[6] or 0,
        }

    def action_skip(self):
        # Просто сделать город активным без скачивания (он будет работать как "онлайн")
        city_id = self.city.get("id")
        if not city_id:
            return
        self.data_manager.set_active_city(city_id)
        from kivy.app import App

        app = App.get_running_app()
        app.sm.current = "root"

    def action_download_all(self):
        # Загружаем данные города из JSON-файлов и делаем его активным
        city_id = self.city.get("id")
        if not city_id:
            return
        self.data_manager.download_city_data(city_id)
        self.data_manager.set_active_city(city_id)
        from kivy.app import App

        app = App.get_running_app()
        app.sm.current = "root"

    def action_online_only(self):
        # Пока просто как skip, но в будущем можно добавить флаг "online only"
        self.action_skip()
