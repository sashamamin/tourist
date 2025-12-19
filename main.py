import os

from kivy.core.window import Window
from kivy.lang import Builder
from kivy.logger import Logger
from kivy.properties import StringProperty, BooleanProperty
from kivy.storage.jsonstore import JsonStore
from kivy.utils import platform
from kivy.uix.screenmanager import CardTransition

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager

from screens.city_package_screen import CityPackageScreen
from screens.city_select_screen import CitySelectScreen
from screens.home_screen import HomeScreen
from screens.place_detail_screen import PlaceDetailScreen
from screens.place_edit_screen import PlaceEditScreen
from screens.tours_screen import ToursScreen  # нужен для правила <ToursScreen> в KV
from screens.tour_edit_screen import TourEditScreen
from screens.tour_route_edit_screen import TourRouteEditScreen
from screens.tour_constructor_screen import TourConstructorScreen
from screens.tour_detail_screen import TourDetailScreen
from screens.tour_run_screen import TourRunScreen
from screens.auth_screen import AuthScreen
from screens.users_admin_screen import UsersAdminScreen
from data.data_manager import DataManager
import hashlib


TEXTS = {
    "ru": {
        "tab_home": "🏠 Домой",
        "tab_map": "🗺️ Карта",
        "tab_places": "📍 Места",
        "tab_tours": "🎭 Экскурсии",
        "tab_favorites": "❤️ Избранное",
        "tab_routes": "🚶 Маршруты",
        "tab_profile": "👤 Профиль",
        "title_routes": "Маршруты",
        "title_favorites": "Избранное",
        "map_search_hint": "Поиск по карте (места и экскурсии)",
        "map_btn_here": "📍 Я здесь",
        "map_btn_all": "Показать все",
        "map_btn_filters": "Фильтры",
        "places_search_hint": "Поиск по названию или описанию",
        "places_filter_all": "Все",
        "places_filter_sight": "Достопримеч.",
        "places_filter_food": "Еда",
        "places_filter_museum": "Музеи",
        "places_sort_label": "Сортировка:",
        "places_sort_rating": "По рейтингу",
        "places_sort_name": "По имени",
        "category_sight": "Достопримеч.",
        "category_food": "Еда",
        "category_museum": "Музей",
        "title_tours": "Экскурсии",
        "tours_filter_all": "Все",
        "tours_filter_history": "История",
        "tours_filter_architecture": "Архитектура",
        "tours_filter_art": "Искусство",
        "tours_sort_label": "Сортировка:",
        "tours_sort_popularity": "По популярности",
        "tours_sort_price": "По цене",
        "tours_count_prefix": "Экскурсии",
        # CitySelectScreen
        "welcome_title": "CityVoice",
        "welcome_subtitle": "ДОБРО ПОЖАЛОВАТЬ!",
        "welcome_question": "В каком городе вы находитесь?",
        "popular_cities": "Популярные города:",
        # CityPackageScreen
        "city_label": "ГОРОД:",
        "loading_content": "Загрузка контента:",
        "points_of_interest": "• Точки интереса",
        "tours_label": "• Экскурсии",
        "offline_package": "• Пакет офлайн-данных: {} МБ",
        "btn_skip": "Пропустить",
        "btn_download_all": "Загрузить всё",
        "btn_online_only": "Только онлайн",
        # HomeScreen
        "city_not_selected": "Город не выбран",
        "city_prefix": "ГОРОД:",
        "place_of_day_prefix": "📍 Место дня:",
        "place_of_day_no_places": "📍 Место дня: пока нет загруженных мест",
        "what_interests_today": "✨ Что вас интересует сегодня?",
        "btn_audio_guide": "🎧 Аудиогид",
        "btn_tours": "🚶 Экскурсии",
        "btn_map": "🗺 Карта",
        "btn_favorites": "⭐ Избранное",
        "recommendations_title": "Рекомендации для вас:",
        "today_in_city": "Сегодня в городе:",
        # Quick actions
        "quick_search": "🔍 Поиск",
        "quick_new_place": "📍 Новое место",
        "quick_new_route": "🚶 Новый маршрут",
        "quick_new_tour": "🎭 Новая экскурсия",
        "quick_search_hint": "🔍 Откройте поиск в разделе 'Места'",
        "quick_new_place_hint": "📍 Откройте карту для добавления нового места",
        "quick_new_route_hint": "🚶 Откройте раздел 'Маршруты' для создания нового маршрута",
        "quick_new_tour_hint": "🎭 Откройте конструктор экскурсий",
        # FavoritesScreen
        "my_collections": "Мои коллекции:",
        "favorites_label": "Избранные:",
        # RoutesScreen
        "btn_build_route": "Построить маршрут",
        # ProfileScreen
        "profile_title": "Профиль и настройки",
        "theme_label": "Тема:",
        "btn_refresh_data": "Обновить данные",
        "btn_about": "О приложении",
        "stats_title": "Моя статистика:",
        "language_label": "Язык интерфейса:",
        "achievements_title": "Достижения:",
        "cities_title": "Мои города:",
        "progress_label": "Исследовано: {}% точек города",
        # PlaceDetailScreen
        "place_default": "Место",
        "btn_toggle_favorite": "В избранное / из избранного",
        "reviews_title": "Отзывы:",
        "review_hint": "Ваш отзыв",
        "btn_submit_review": "Отправить отзыв",
        "no_reviews": "Пока нет отзывов",
        "review_no_text": "Отзыв без текста",
        # TourDetailScreen
        "tour_default": "Экскурсия",
        "tour_progress": "Пройдено: {}/{} точек",
        "tour_progress_empty": "Пройдено: 0/0 точек",
        "btn_start_tour": "Начать экскурсию (MVP)",
        "tour_stops_title": "Остановки экскурсии:",
        "stop_label": "Остановка {}:",
        # TourRunScreen
        "tour_no_points": "Нет точек в этой экскурсии",
        "stop_progress": "Остановка {}/{}",
        "next_stop": "Далее: {}",
        "next_stop_default": "Далее: следующая точка",
        "last_stop": "Это последняя остановка",
        "btn_back": "Назад",
        "btn_next": "Далее",
        "btn_finish": "Завершить",
        # TourConstructorScreen
        "constructor_title": "Конструктор маршрутов",
        "my_tour": "МОЙ ТУР:",
        "what_interests": "Что вас интересует?",
        "theme_history": "История",
        "theme_food": "Еда",
        "theme_art": "Искусство",
        "how_much_time": "Сколько времени есть?",
        "duration_1h": "1 час",
        "duration_2_3h": "2-3 часа",
        "duration_full_day": "Целый день",
        "btn_generate_route": "Сгенерировать маршрут (MVP)",
        "suggested_route": "Предложенный маршрут:",
        "route_summary": "Итого: {} точек, {}",
        "route_no_places": "Нет подходящих мест для выбранных настроек",
        "btn_start_tour_mvp": "Начать тур (MVP)",
        # ToursScreen
        "tours_title_city": "Экскурсии — {}",
        "tours_title": "Экскурсии",
        "new_tour": "⭐ Новая экскурсия",
        "free": "🆓 Бесплатно",
        "stops_count": "📍 {} остановок",
        "btn_start": "НАЧАТЬ",
        "btn_buy": "КУПИТЬ",
        # Common
        "loading": "Загрузка...",
        "error": "Ошибка",
        "success": "Успешно",
        "btn_view_details": "Подробнее",
        # HomeScreen dynamic texts
        "morning": "утро",
        "day": "день",
        "evening": "вечер",
        "late_night": "поздний час",
        "rec1_continue": "Отличный {}: продолжите маршрут \"{}\"",
        "rec1_no_tours": "В {} пока нет экскурсий — они появятся позже",
        "rec2_visit": "Загляните в место: {}",
        "rec2_no_places": "Места в этом городе ещё не загружены",
        "rec3_walk": "Самое время прогуляться по {} и открыть новые точки на карте",
        "rec3_evening": "Вечером в {} особенно красивы подсветка и ночные маршруты по центру",
        "rec3_plan": "Спланируйте завтрашний маршрут по {} в разделе 'Маршруты'",
        "today_route": "Сегодня можно пройти маршрут \"{}\" (~{} ч)",
        "today_no_tours": "В {} пока нет активных экскурсий",
        "today_visit": "Зайдите к: {} и {}",
        "today_walk": "Хорошее место для прогулки: {}",
        "today_map": "Откройте карту и посмотрите, что рядом с вами в {}",
        # Auth
        "auth_login_title": "Вход",
        "auth_register_title": "Регистрация",
        "auth_username": "Логин",
        "auth_password": "Пароль",
        "auth_have_account": "Уже есть аккаунт? Войти",
        "auth_no_account": "Нет аккаунта? Зарегистрироваться",
        "auth_fill_all": "Заполните логин и пароль",
        "auth_user_exists": "Такой пользователь уже есть",
        "auth_wrong_credentials": "Неверный логин или пароль",
    },
    "en": {
        "tab_home": "🏠 Home",
        "tab_map": "🗺️ Map",
        "tab_places": "📍 Places",
        "tab_tours": "🎭 Tours",
        "tab_favorites": "❤️ Favorites",
        "tab_routes": "🚶 Routes",
        "tab_profile": "👤 Profile",
        "title_routes": "Routes",
        "title_favorites": "Favorites",
        "map_search_hint": "Search on map (places & tours)",
        "map_btn_here": "📍 I'm here",
        "map_btn_all": "Show all",
        "map_btn_filters": "Filters",
        "places_search_hint": "Search by name or description",
        "places_filter_all": "All",
        "places_filter_sight": "Sights",
        "places_filter_food": "Food",
        "places_filter_museum": "Museums",
        "places_sort_label": "Sort:",
        "places_sort_rating": "By rating",
        "places_sort_name": "By name",
        "category_sight": "Sight",
        "category_food": "Food",
        "category_museum": "Museum",
        "title_tours": "Tours",
        "tours_filter_all": "All",
        "tours_filter_history": "History",
        "tours_filter_architecture": "Architecture",
        "tours_filter_art": "Art",
        "tours_sort_label": "Sort:",
        "tours_sort_popularity": "By popularity",
        "tours_sort_price": "By price",
        "tours_count_prefix": "Tours",
        # CitySelectScreen
        "welcome_title": "CityVoice",
        "welcome_subtitle": "WELCOME!",
        "welcome_question": "What city are you in?",
        "popular_cities": "Popular cities:",
        # CityPackageScreen
        "city_label": "CITY:",
        "loading_content": "Loading content:",
        "points_of_interest": "• Points of interest",
        "tours_label": "• Tours",
        "offline_package": "• Offline data package: {} MB",
        "btn_skip": "Skip",
        "btn_download_all": "Download all",
        "btn_online_only": "Online only",
        # HomeScreen
        "city_not_selected": "City not selected",
        "city_prefix": "CITY:",
        "place_of_day_prefix": "📍 Place of the day:",
        "place_of_day_no_places": "📍 Place of the day: no places loaded yet",
        "what_interests_today": "✨ What interests you today?",
        "btn_audio_guide": "🎧 Audio guide",
        "btn_tours": "🚶 Tours",
        "btn_map": "🗺 Map",
        "btn_favorites": "⭐ Favorites",
        "recommendations_title": "Recommendations for you:",
        "today_in_city": "Today in the city:",
        # Quick actions
        "quick_search": "🔍 Search",
        "quick_new_place": "📍 New place",
        "quick_new_route": "🚶 New route",
        "quick_new_tour": "🎭 New tour",
        "quick_search_hint": "🔍 Open search in 'Places' section",
        "quick_new_place_hint": "📍 Open map to add a new place",
        "quick_new_route_hint": "🚶 Open 'Routes' section to create a new route",
        "quick_new_tour_hint": "🎭 Open tour constructor",
        # FavoritesScreen
        "my_collections": "My collections:",
        "favorites_label": "Favorites:",
        # RoutesScreen
        "btn_build_route": "Build route",
        # ProfileScreen
        "profile_title": "Profile & Settings",
        "theme_label": "Theme:",
        "btn_refresh_data": "Refresh data",
        "btn_about": "About",
        "stats_title": "My statistics:",
        "language_label": "Interface language:",
        "achievements_title": "Achievements:",
        "cities_title": "My cities:",
        "progress_label": "City explored: {}% of places",
        # PlaceDetailScreen
        "place_default": "Place",
        "btn_toggle_favorite": "Add to favorites / Remove from favorites",
        "reviews_title": "Reviews:",
        "review_hint": "Your review",
        "btn_submit_review": "Submit review",
        "no_reviews": "No reviews yet",
        "review_no_text": "Review without text",
        # TourDetailScreen
        "tour_default": "Tour",
        "tour_progress": "Completed: {}/{} points",
        "tour_progress_empty": "Completed: 0/0 points",
        "btn_start_tour": "Start tour (MVP)",
        "tour_stops_title": "Tour stops:",
        "stop_label": "Stop {}:",
        # TourRunScreen
        "tour_no_points": "No points in this tour",
        "stop_progress": "Stop {}/{}",
        "next_stop": "Next: {}",
        "next_stop_default": "Next: next point",
        "last_stop": "This is the last stop",
        "btn_back": "Back",
        "btn_next": "Next",
        "btn_finish": "Finish",
        # TourConstructorScreen
        "constructor_title": "Route constructor",
        "my_tour": "MY TOUR:",
        "what_interests": "What interests you?",
        "theme_history": "History",
        "theme_food": "Food",
        "theme_art": "Art",
        "how_much_time": "How much time do you have?",
        "duration_1h": "1 hour",
        "duration_2_3h": "2-3 hours",
        "duration_full_day": "Full day",
        "btn_generate_route": "Generate route (MVP)",
        "suggested_route": "Suggested route:",
        "route_summary": "Total: {} points, {}",
        "route_no_places": "No suitable places for selected settings",
        "btn_start_tour_mvp": "Start tour (MVP)",
        # ToursScreen
        "tours_title_city": "Tours — {}",
        "tours_title": "Tours",
        "new_tour": "⭐ New tour",
        "free": "🆓 Free",
        "stops_count": "📍 {} stops",
        "btn_start": "START",
        "btn_buy": "BUY",
        # Common
        "loading": "Loading...",
        "error": "Error",
        "success": "Success",
        "btn_view_details": "Details",
        # HomeScreen dynamic texts
        "morning": "morning",
        "day": "day",
        "evening": "evening",
        "late_night": "late night",
        "rec1_continue": "Great {}: continue the route \"{}\"",
        "rec1_no_tours": "No tours in {} yet — they will appear later",
        "rec2_visit": "Visit the place: {}",
        "rec2_no_places": "Places in this city are not loaded yet",
        "rec3_walk": "It's time to walk around {} and discover new points on the map",
        "rec3_evening": "In the evening, {} is especially beautiful with lighting and night routes in the center",
        "rec3_plan": "Plan tomorrow's route around {} in the 'Routes' section",
        "today_route": "Today you can take the route \"{}\" (~{} h)",
        "today_no_tours": "No active tours in {} yet",
        "today_visit": "Visit: {} and {}",
        "today_walk": "Good place for a walk: {}",
        "today_map": "Open the map and see what's near you in {}",
        # Auth
        "auth_login_title": "Login",
        "auth_register_title": "Sign up",
        "auth_username": "Username",
        "auth_password": "Password",
        "auth_have_account": "Already have an account? Login",
        "auth_no_account": "No account yet? Sign up",
        "auth_fill_all": "Please fill username and password",
        "auth_user_exists": "User already exists",
        "auth_wrong_credentials": "Wrong username or password",
    },
}


SCREENS = [
    ("auth", AuthScreen),
    ("city_select", CitySelectScreen),
    ("city_package", CityPackageScreen),
    ("root", None),  # RootScreen добавим отдельно, так как он описан в KV
    ("place_detail", PlaceDetailScreen),
    ("place_edit", PlaceEditScreen),
    ("tour_detail", TourDetailScreen),
    ("tour_edit", TourEditScreen),
    ("tour_route_edit", TourRouteEditScreen),
    ("tour_run", TourRunScreen),
    ("tour_constructor", TourConstructorScreen),
    ("users_admin", UsersAdminScreen),
]


class RootScreen(MDScreen):
    pass


class CityGuideApp(MDApp):
    # Текущий язык интерфейса в виде кода ('ru' / 'en') для реактивных биндингов KV
    ui_language = StringProperty("ru")
    is_admin = BooleanProperty(False)
    def build(self):
        # Перед настройкой внешнего вида и загрузкой KV узнаём язык
        self.ui_language = self.get_language_code()
        self._setup_appearance()
        self._setup_window()
        self._load_ui()
        self._create_screens()
        Logger.info("CityGuideApp: application built and screens created")
        return self.sm

    # --- Инициализация внешнего вида и окна ---

    def _setup_appearance(self):
        """Настройка темы и базового внешнего вида приложения."""
        self.title = "CityCompass"
        
        # Загружаем тему из настроек, если она уже сохранена
        style = self._load_theme_style()
        if style not in ("Light", "Dark"):
            # По умолчанию включаем тёмную тему
            style = "Dark"
        self.theme_cls.theme_style = style
        
        # Современные цвета Material Design (без сложных анимаций, чтобы избежать ошибок Animation)
        self.theme_cls.primary_palette = "Indigo"
        self.theme_cls.secondary_palette = "Teal"
        # Отключаем анимацию переключения темы, так как на некоторых конфигурациях
        # Kivy/KivyMD это может вызывать ошибки Animation (None * float)
        self.theme_cls.theme_style_switch_animation = False

        # Используем базовый стиль (без явного включения M3 и дополнительных анимаций),
        # чтобы убрать возможные проблемы с анимацией свойств виджетов
        try:
            # Если поддерживается, можно оставить материал-стиль по умолчанию
            _ = self.theme_cls.material_style
        except Exception:
            pass

    def _setup_window(self):
        """Настройка размеров окна для десктопа."""
        try:
            if platform in ("win", "linux", "macosx"):
                Window.minimum_width = 400
                Window.minimum_height = 600
        except Exception as exc:
            Logger.warning(f"CityGuideApp: unable to setup window constraints: {exc}")

    # --- Загрузка KV и создание экранов ---

    def _load_ui(self):
        """Загружаем основной KV-файл с описанием интерфейса."""
        try:
            Builder.load_file("main.kv")
        except Exception as exc:
            Logger.error(f"CityGuideApp: failed to load main.kv: {exc}")
            raise

    def _create_screens(self):
        """Создаём ScreenManager и регистрируем все экраны приложения."""
        # Добавляем анимированный переход между экранами
        self.sm = MDScreenManager(transition=CardTransition(duration=0.35))

        for name, cls in SCREENS:
            if name == "root":
                # RootScreen описан в KV и используется как контейнер нижней навигации
                screen = RootScreen(name="root")
            else:
                screen = cls(name=name)
            self.sm.add_widget(screen)

    def on_start(self):
        Logger.info("CityGuideApp: on_start called")
        # Здесь в будущем можно добавить загрузку пользовательских данных,
        # проверку обновлений и аналитики запуска приложения.

    # --- Настройки приложения (JsonStore) ---

    def _get_settings_store(self):
        if not hasattr(self, "_settings_store"):
            base_dir = os.path.dirname(__file__)
            path = os.path.join(base_dir, "settings.json")
            self._settings_store = JsonStore(path)
        return self._settings_store

    def _load_theme_style(self):
        """Читает сохранённую тему пользователя (Light/Dark)."""
        store = self._get_settings_store()
        if store.exists("theme"):
            return store.get("theme").get("style", "Light")
        return "Light"

    def save_theme_style(self, style: str):
        """Сохраняет выбранную тему пользователя."""
        if style not in ("Light", "Dark"):
            return
        store = self._get_settings_store()
        store.put("theme", style=style)

    def _load_language(self) -> str:
        """Читает сохранённый язык интерфейса пользователя."""
        store = self._get_settings_store()
        if store.exists("language"):
            return store.get("language").get("code", "Русский")
        return "Русский"

    def save_language(self, language: str):
        """Сохраняет выбранный язык интерфейса пользователя (без локализации)."""
        store = self._get_settings_store()
        store.put("language", code=language)

    # --- Простая аутентификация пользователя через JsonStore ---

    def _get_user(self):
        store = self._get_settings_store()
        if store.exists("user"):
            data = store.get("user")
            username = data.get("username")
            if not username:
                return None
            dm = DataManager.get_instance()
            db_user = dm.get_user_by_username(username)
            if not db_user:
                return None
            # админский интерфейс доступен только встроенному пользователю 'admin'
            self.is_admin = db_user.get("username") == "admin"
            return {"username": db_user.get("username"), "is_admin": self.is_admin}
        return None

    def register_user(
        self,
        username: str,
        password: str,
        first_name: str = "",
        last_name: str = "",
        email: str = "",
        secret_word: str = "",
    ):
        """Регистрирует нового пользователя в таблице users.

        Для MVP допускается несколько пользователей, но UI пока ориентирован на одного
        активного. Роль по умолчанию — user.
        """
        username = (username or "").strip()
        password = (password or "").strip()
        first_name = (first_name or "").strip()
        last_name = (last_name or "").strip()
        email = (email or "").strip()
        secret_word = (secret_word or "").strip()

        # Все поля регистрации должны быть заполнены
        if not (username and password and first_name and last_name and email and secret_word):
            return False, "auth_fill_all"

        dm = DataManager.get_instance()
        if dm.get_user_by_username(username):
            return False, "auth_user_exists"

        # создаём обычного пользователя
        dm.create_user(
            username=username,
            password_plain=password,
            role="user",
            first_name=first_name,
            last_name=last_name,
            email=email,
            secret_word=secret_word,
        )

        # сохраняем последнего активного в settings.json
        store = self._get_settings_store()
        store.put("user", username=username, is_admin=False)
        self.is_admin = False
        return True, "success"

    def login_user(self, username: str, password: str):
        """Проверяет логин/пароль по таблице users.

        admin / 1234 теперь тоже хранится в БД (создаётся при инициализации DataManager).
        """
        username = (username or "").strip()
        password = (password or "").strip()
        if not username or not password:
            return False, "auth_fill_all"

        dm = DataManager.get_instance()
        user = dm.get_user_by_username(username)
        if not user:
            return False, "auth_wrong_credentials"

        password_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        if password_hash != user.get("password_hash"):
            return False, "auth_wrong_credentials"

        # успешный вход: админский режим только для логина 'admin'
        self.is_admin = user.get("username") == "admin"

        # запоминаем последнего вошедшего пользователя в settings.json (без пароля)
        store = self._get_settings_store()
        store.put("user", username=username, is_admin=self.is_admin)
        return True, "success"

    # --- Управление пользователем для админки ---

    def get_user_info(self):
        """Возвращает данные текущего пользователя по информации из settings.json.

        Используется в админ-окне для отображения и редактирования логина/роли.
        Пароль из БД не возвращаем по соображениям безопасности.
        """
        base = self._get_user()
        return base or {}

    def update_user_info(self, username: str, password: str, is_admin: bool):
        """Создаёт или обновляет пользователя в БД и в settings.json.

        Используется экраном управления пользователями.
        """
        username = (username or "").strip()
        password = (password or "").strip()
        if not username or not password:
            return False

        dm = DataManager.get_instance()
        existing = dm.get_user_by_username(username)
        role = "admin" if is_admin else "user"
        if existing:
            dm.update_user(existing["id"], username=username, password_plain=password, role=role)
        else:
            dm.create_user(username=username, password_plain=password, role=role)

        store = self._get_settings_store()
        # флаг is_admin в настройках используется только для удобства, но
        # реальный доступ к админке определяется логином 'admin'
        self.is_admin = username == "admin"
        store.put("user", username=username, is_admin=self.is_admin)
        return True

    def delete_user_info(self):
        """Удаляет пользователя из БД и настроек (кроме встроенного admin)."""
        user = self._get_user()
        if not user:
            return
        username = user.get("username")
        if not username or username == "admin":
            return

        dm = DataManager.get_instance()
        db_user = dm.get_user_by_username(username)
        if db_user:
            dm.delete_user(db_user.get("id"))

        store = self._get_settings_store()
        if store.exists("user"):
            store.delete("user")
        self.is_admin = False

    # --- Локализация интерфейса ---

    def get_language_code(self) -> str:
        """Возвращает код языка интерфейса.

        Для текущей версии приложения фиксируем русский язык ('ru'), чтобы
        весь интерфейс и тексты из словаря TEXTS всегда были на русском,
        независимо от сохранённых настроек.
        """
        return "ru"

    def get_text(self, key: str) -> str:
        """Возвращает локализованную строку по ключу.

        Если ключ не найден, вернёт сам key, чтобы легче было отлавливать пропуски.
        """
        lang_code = self.get_language_code()
        lang_texts = TEXTS.get(lang_code, TEXTS["ru"])
        return lang_texts.get(key, key)


if __name__ == "__main__":
    CityGuideApp().run()
