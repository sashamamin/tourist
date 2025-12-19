from kivymd.uix.screen import MDScreen
from kivy.properties import BooleanProperty, NumericProperty

from kivy_garden.mapview import MapView, MapMarker

from data.data_manager import DataManager


class MapScreen(MDScreen):
    # Режим выбора точки для конкретного места
    pick_mode = BooleanProperty(False)
    pick_place_id = NumericProperty(0)
    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.data_manager = DataManager.get_instance()
        # все маркеры мест по id места
        self.all_place_markers = {}
        self._center_on_active_city()
        self._populate_markers()

    def _center_on_active_city(self):
        city = self.data_manager.get_active_city()
        if not city:
            return
        map_view = self.ids.get("map_view")
        if not map_view:
            return
        lat = city.get("center_lat")
        lon = city.get("center_lon")
        if lat is None or lon is None:
            return
        try:
            map_view.center_on(lat, lon)
        except Exception:
            map_view.lat = lat
            map_view.lon = lon

    def _populate_markers(self):
        map_view = self.ids.get("map_view")
        if not map_view:
            return
        # удаляем старые маркеры мест
        for marker in self.all_place_markers.values():
            try:
                map_view.remove_widget(marker)
            except Exception:
                pass
        self.all_place_markers = {}

        places = self.data_manager.get_all_places()

        for place in places:
            lat = place.get("lat")
            lon = place.get("lon")
            if lat is None or lon is None:
                continue
            marker = MapMarker(lat=lat, lon=lon)
            # добавляем как обычный виджет, без внутреннего регистра MapView
            map_view.add_widget(marker)
            pid = place.get("id")
            if pid is not None:
                self.all_place_markers[pid] = marker

    def focus_on_place_by_id(self, place_id):
        place = self.data_manager.get_place(place_id)
        if not place:
            return
        lat = place.get("lat")
        lon = place.get("lon")
        if lat is None or lon is None:
            return
        map_view = self.ids.get("map_view")
        if not map_view:
            return
        try:
            map_view.center_on(lat, lon)
        except Exception:
            map_view.lat = lat
            map_view.lon = lon
        try:
            map_view.center_on(lat, lon)
            map_view.zoom = 15
        except Exception:
            map_view.lat = lat
            map_view.lon = lon

    def show_route(self, place_ids):
        map_view = self.ids.get("map_view")
        if not map_view:
            return
        # скрываем все маркеры мест
        for pid, marker in self.all_place_markers.items():
            try:
                map_view.remove_widget(marker)
            except Exception:
                pass

        # показываем только выбранные маркеры
        route_places = []
        for pid in place_ids:
            marker = self.all_place_markers.get(pid)
            if not marker:
                continue
            try:
                map_view.add_widget(marker)
            except Exception:
                continue
            route_places.append((marker.lat, marker.lon))

        if route_places:
            lat0, lon0 = route_places[0]
            try:
                map_view.center_on(lat0, lon0)
                map_view.zoom = 15
            except Exception:
                map_view.lat = lat0
                map_view.lon = lon0

    # --- Панель действий над картой ---

    def on_search_text(self, text):
        """Простой поиск по местам (название и описание) с фокусом на первое совпадение."""
        query = (text or "").strip().lower()
        if not query:
            return
        places = self.data_manager.get_all_places()
        for place in places:
            name = (place.get("name") or "").lower()
            desc = (place.get("description") or "").lower()
            if query in name or query in desc:
                self.focus_on_place_by_id(place.get("id"))
                break

    def focus_on_user_location(self):
        """Заглушка под фокус на текущем местоположении пользователя.

        В текущем прототипе просто возвращаемся к центру активного города.
        """
        self._center_on_active_city()

    def reset_view(self):
        """Вернуть карту к виду по умолчанию: центр города и все маркеры."""
        self._center_on_active_city()
        self._populate_markers()

    # --- Режим выбора координат для места ---

    def enter_pick_mode(self, place_id):
        """Включает режим выбора координат для указанного места.

        После этого первый тап по карте сохранит lat/lon места в БД.
        """
        self.pick_mode = True
        self.pick_place_id = int(place_id) if place_id else 0

    def _apply_picked_coords(self, lat, lon):
        if not self.pick_place_id:
            return
        dm = self.data_manager
        try:
            dm.update_place_coords(self.pick_place_id, lat, lon)
        except Exception:
            return

        # Обновляем маркеры и центрируемся на новой точке
        map_view = self.ids.get("map_view")
        self._populate_markers()
        if map_view:
            try:
                map_view.center_on(lat, lon)
                map_view.zoom = 15
            except Exception:
                map_view.lat = lat
                map_view.lon = lon

        # Выходим из режима выбора
        self.pick_mode = False
        self.pick_place_id = 0

    def on_touch_down(self, touch):
        """Обработка нажатий мыши/пальца.

        В режиме pick_mode перехватываем первый тап по карте и сохраняем
        координаты места, затем выходим из режима. После этого событие
        не передаём дальше, чтобы карта не сдвигалась лишний раз.
        """

        if self.pick_mode:
            map_view = self.ids.get("map_view")
            if map_view and map_view.collide_point(*touch.pos):
                try:
                    # У MapView есть метод get_latlon_at для конвертации
                    lat, lon = map_view.get_latlon_at(*touch.pos)
                except Exception:
                    return False
                self._apply_picked_coords(lat, lon)
                return True

        # Обычное поведение, если не в режиме выбора точки
        return super().on_touch_down(touch)

    def open_filters(self):
        """Заглушка для будущей панели фильтров карты."""
        # В дальнейшем здесь можно открыть отдельный экран/диалог фильтров.
        pass
