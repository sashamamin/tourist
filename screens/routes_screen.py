from kivy.properties import ListProperty

from kivymd.uix.screen import MDScreen
from kivymd.uix.list import OneLineRightIconListItem, IconRightWidget
from kivymd.uix.selectioncontrol import MDCheckbox

from data.data_manager import DataManager


class RouteListItem(OneLineRightIconListItem):
    place_id = None


class RoutesScreen(MDScreen):
    places = ListProperty()
    selected_place_ids = ListProperty()

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.data_manager = DataManager.get_instance()
        self.load_places()

    def load_places(self):
        self.places = self.data_manager.get_all_places()
        container = self.ids.get("routes_list")
        if not container:
            return
        container.clear_widgets()
        for place in self.places:
            item = RouteListItem(text=place["name"])
            item.place_id = place["id"]
            checkbox = MDCheckbox()

            def on_checkbox_active(cb, value, pid=place["id"]):
                self.toggle_place(pid, value)

            checkbox.bind(active=on_checkbox_active)
            right = IconRightWidget()
            right.add_widget(checkbox)
            item.add_widget(right)
            container.add_widget(item)

    def toggle_place(self, place_id, selected):
        ids_list = list(self.selected_place_ids or [])
        if selected:
            if place_id not in ids_list:
                ids_list.append(place_id)
        else:
            if place_id in ids_list:
                ids_list.remove(place_id)
        self.selected_place_ids = ids_list

    def build_route(self):
        if not self.selected_place_ids:
            return
        from kivy.app import App

        app = App.get_running_app()
        root = app.sm.get_screen("root")
        bottom_nav = root.ids.get("bottom_nav")
        if bottom_nav:
            if hasattr(bottom_nav, "switch_tab"):
                bottom_nav.switch_tab("map")
            else:
                bottom_nav.current = "map"
        map_screen = root.ids.get("map_screen")
        if map_screen:
            map_screen.show_route(self.selected_place_ids)

    def open_on_map(self, item):
        # Поведение по клику на строку отключено в текущем MVP маршрутов
        pass
