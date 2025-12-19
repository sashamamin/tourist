import json
import os
import sqlite3
import hashlib
from threading import Lock


DB_NAME = "cityguide.db"
PLACES_JSON = os.path.join(os.path.dirname(__file__), "places.json")
TOURS_JSON = os.path.join(os.path.dirname(__file__), "tours.json")


class DataManager:
    _instance = None
    _lock = Lock()

    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), DB_NAME)
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._create_tables()
        self._ensure_tour_points_images_column()
        self._ensure_city_schema()
        self._ensure_cities_loaded()
        self._ensure_places_loaded()
        self._ensure_tours_loaded()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = DataManager()
        return cls._instance

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.execute(
            """CREATE TABLE IF NOT EXISTS places (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            name_ru TEXT,
            name_en TEXT,
            category TEXT,
            description TEXT,
            description_ru TEXT,
            description_en TEXT,
            short_desc TEXT,
            short_desc_ru TEXT,
            short_desc_en TEXT,
            lat REAL,
            lon REAL,
            address TEXT,
            phone TEXT,
            website TEXT,
            price TEXT,
            hours TEXT,
            rating REAL,
            image_urls TEXT
        );"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS favorites (
            user_id INTEGER,
            place_id INTEGER,
            FOREIGN KEY(place_id) REFERENCES places(id)
        );"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS tours (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            theme TEXT,
            duration INTEGER,
            distance REAL,
            cover_image TEXT,
            audio_intro TEXT,
            is_linear INTEGER,
            rating REAL,
            price REAL,
            author_id INTEGER
        );"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS tour_points (
            tour_id INTEGER,
            place_id INTEGER,
            order_index INTEGER,
            audio_story TEXT,
            quiz_question TEXT,
            FOREIGN KEY(tour_id) REFERENCES tours(id),
            FOREIGN KEY(place_id) REFERENCES places(id)
        );"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS user_tours (
            user_id INTEGER,
            tour_id INTEGER,
            progress INTEGER,
            current_point INTEGER,
            started_at TEXT,
            completed_at TEXT,
            rating_user INTEGER,
            PRIMARY KEY(user_id, tour_id),
            FOREIGN KEY(tour_id) REFERENCES tours(id)
        );"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            place_id INTEGER NOT NULL,
            user_id INTEGER,
            rating INTEGER,
            comment TEXT,
            created_at TEXT,
            FOREIGN KEY(place_id) REFERENCES places(id)
        );"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS cities (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            country TEXT,
            center_lat REAL,
            center_lon REAL,
            is_downloaded INTEGER DEFAULT 0,
            download_size INTEGER,
            last_update TEXT,
            is_active INTEGER DEFAULT 0
        );"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS user_cities (
            user_id INTEGER,
            city_id INTEGER,
            downloaded_at TEXT,
            is_current INTEGER,
            points_visited INTEGER DEFAULT 0,
            tours_completed INTEGER DEFAULT 0
        );"""
        )
        # Таблица пользователей приложения (MVP-многопользовательская система)
        cur.execute(
            """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL
        );"""
        )
        # Таблица сообщений в техподдержку между пользователем и админом
        cur.execute(
            """CREATE TABLE IF NOT EXISTS support_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            is_admin_sender INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT
        );"""
        )
        # Гарантируем наличие дополнительных полей профиля пользователя
        try:
            cur.execute("PRAGMA table_info(users)")
            cols = [row[1] for row in cur.fetchall()]
            extra_cols = [
                ("first_name", "TEXT"),
                ("last_name", "TEXT"),
                ("email", "TEXT"),
                ("secret_word", "TEXT"),
            ]
            for col_name, col_type in extra_cols:
                if col_name not in cols:
                    cur.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
        except Exception:
            pass
        self.conn.commit()

        # Если таблица пользователей пуста, создаём встроенного администратора
        cur.execute("SELECT COUNT(*) FROM users")
        count = cur.fetchone()[0]
        if count == 0:
            # admin / 1234
            password_hash = hashlib.sha256("1234".encode("utf-8")).hexdigest()
            cur.execute(
                "INSERT INTO users (username, password_hash, role, first_name, last_name, email, secret_word) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("admin", password_hash, "admin", "Админ", "", "", ""),
            )
            self.conn.commit()

    def _ensure_tour_points_images_column(self):
        """Гарантирует наличие колонки image_urls в таблице tour_points.

        Используется для хранения списка картинок точки маршрута (JSON-строка).
        """
        try:
            cur = self.conn.cursor()
            cur.execute("PRAGMA table_info(tour_points)")
            columns = [row[1] for row in cur.fetchall()]
            if "image_urls" not in columns:
                cur.execute("ALTER TABLE tour_points ADD COLUMN image_urls TEXT")
                self.conn.commit()
        except Exception:
            # Если по какой-то причине миграция не удалась, просто продолжаем без падения
            pass

    # ===== Админ: базовое редактирование туров =====

    def insert_tour_quick(self, city_id=1):
        """Создаёт простой черновик тура для админки и возвращает его id."""
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO tours (city_id, title, description, theme, price, duration, distance, rating) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                city_id,
                "Новая экскурсия",
                "Описание экскурсии",
                "history",
                0.0,
                60.0,
                2.0,
                None,
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_tour_basic(
        self,
        tour_id,
        title=None,
        description=None,
        theme=None,
        price=None,
        duration=None,
        distance=None,
        rating=None,
        cover_image=None,
    ):
        """Обновляет основные поля тура для админ-редактора."""
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE tours SET title = ?, description = ?, theme = ?, price = ?, duration = ?, distance = ?, rating = ?, cover_image = ? "
            "WHERE id = ?",
            (
                title,
                description,
                theme,
                price,
                duration,
                distance,
                rating,
                cover_image,
                tour_id,
            ),
        )
        self.conn.commit()

    def download_city_data(self, city_id):
        """Загружает/обновляет данные для указанного города из JSON-файлов.

        Ожидается, что в папке data будут файлы вида:
        - places_<city_id>.json
        - tours_<city_id>.json
        Каждый элемент в этих файлах имеет ту же структуру, что и базовые
        places.json/tours.json, city_id подставляется автоматически.
        """
        base_dir = os.path.dirname(__file__)
        places_path = os.path.join(base_dir, f"places_{city_id}.json")
        tours_path = os.path.join(base_dir, f"tours_{city_id}.json")

        # Загрузка мест города, если есть файл
        if os.path.exists(places_path):
            with open(places_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for place in data:
                place_with_city = dict(place)
                place_with_city["city_id"] = city_id
                self.insert_place(place_with_city)

        # Загрузка туров города, если есть файл
        if os.path.exists(tours_path):
            with open(tours_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for tour in data:
                tour_with_city = dict(tour)
                tour_with_city["city_id"] = city_id
                self.insert_tour_with_points(tour_with_city)

        # Помечаем город как скачанный
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE cities SET is_downloaded = 1 WHERE id = ?",
            (city_id,),
        )
        self.conn.commit()

    def _ensure_city_schema(self):
        cur = self.conn.cursor()
        try:
            cur.execute("ALTER TABLE places ADD COLUMN city_id INTEGER")
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("ALTER TABLE tours ADD COLUMN city_id INTEGER")
        except sqlite3.OperationalError:
            pass
        cur.execute("UPDATE places SET city_id = 1 WHERE city_id IS NULL")
        cur.execute("UPDATE tours SET city_id = 1 WHERE city_id IS NULL")
        self.conn.commit()

        # Дополнительные колонки для локализованных полей мест.
        # Выполняем ALTER TABLE в try/except, чтобы не падать, если колонка уже есть.
        try:
            cur.execute("ALTER TABLE places ADD COLUMN name_ru TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("ALTER TABLE places ADD COLUMN name_en TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("ALTER TABLE places ADD COLUMN description_ru TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("ALTER TABLE places ADD COLUMN description_en TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("ALTER TABLE places ADD COLUMN short_desc_ru TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cur.execute("ALTER TABLE places ADD COLUMN short_desc_en TEXT")
        except sqlite3.OperationalError:
            pass
        # Для уже существующих записей заполняем ru-колонки из старых полей
        cur.execute(
            "UPDATE places SET name_ru = COALESCE(name_ru, name), "
            "description_ru = COALESCE(description_ru, description), "
            "short_desc_ru = COALESCE(short_desc_ru, short_desc)"
        )
        self.conn.commit()

    def _ensure_cities_loaded(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM cities")
        count = cur.fetchone()[0]
        if count == 0:
            cities_seed = [
                (1, "Москва", "Россия", 55.751244, 37.618423, 1, 0, "", 1),
                (2, "Санкт-Петербург", "Россия", 59.9342802, 30.3350986, 0, 245, "", 0),
                (3, "Казань", "Россия", 55.796127, 49.106405, 0, 320, "", 0),
                (4, "Екатеринбург", "Россия", 56.838926, 60.605703, 0, 280, "", 0),
                (5, "Сочи", "Россия", 43.585525, 39.723062, 0, 260, "", 0),
                (6, "Калининград", "Россия", 54.710426, 20.452214, 0, 230, "", 0),
            ]
            cur.executemany(
                """INSERT INTO cities (id, name, country, center_lat, center_lon, is_downloaded, download_size, last_update, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                cities_seed,
            )
            self.conn.commit()

    def get_active_city(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM cities WHERE is_active = 1 LIMIT 1")
        row = cur.fetchone()
        if not row:
            return None
        columns = [c[0] for c in cur.description]
        return dict(zip(columns, row))

    def set_active_city(self, city_id, user_id=1):
        cur = self.conn.cursor()
        cur.execute("UPDATE cities SET is_active = 0")
        cur.execute("UPDATE cities SET is_active = 1 WHERE id = ?", (city_id,))
        cur.execute(
            "UPDATE user_cities SET is_current = 0 WHERE user_id = ?",
            (user_id,),
        )
        cur.execute(
            "UPDATE user_cities SET is_current = 1 WHERE user_id = ? AND city_id = ?",
            (user_id, city_id),
        )
        if cur.rowcount == 0:
            cur.execute(
                "INSERT INTO user_cities (user_id, city_id, downloaded_at, is_current) VALUES (?, ?, ?, 1)",
                (user_id, city_id, ""),
            )
        self.conn.commit()

    def add_city(
        self,
        name: str,
        country: str = "Россия",
        center_lat: float = 0.0,
        center_lon: float = 0.0,
        is_downloaded: int = 0,
        download_size: int = 0,
        is_active: int = 0,
    ) -> int:
        """Создаёт новый город в таблице cities и возвращает его id.

        last_update для простоты оставляем пустой строкой.
        """
        name = (name or "").strip()
        country = (country or "").strip() or "Россия"
        if not name:
            raise ValueError("city name is required")

        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO cities
            (name, country, center_lat, center_lon, is_downloaded, download_size, last_update, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, country, center_lat, center_lon, int(is_downloaded), int(download_size), "", int(is_active)),
        )
        self.conn.commit()
        return cur.lastrowid

    def delete_city(self, city_id: int):
        """Удаляет город и связанные записи из user_cities.

        Данные places/tours с этим city_id остаются, чтобы не ломать ссылки,
        но больше не будут показываться как часть списка городов.
        """
        cur = self.conn.cursor()
        try:
            cur.execute("DELETE FROM user_cities WHERE city_id = ?", (city_id,))
        except Exception:
            pass
        cur.execute("DELETE FROM cities WHERE id = ?", (city_id,))
        self.conn.commit()

    def _ensure_places_loaded(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM places")
        count = cur.fetchone()[0]
        if count == 0 and os.path.exists(PLACES_JSON):
            with open(PLACES_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            for place in data:
                place_with_city = dict(place)
                place_with_city.setdefault("city_id", 1)
                self.insert_place(place_with_city)

    def _ensure_tours_loaded(self):
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tours")
        count = cur.fetchone()[0]
        if count == 0 and os.path.exists(TOURS_JSON):
            with open(TOURS_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            for tour in data:
                tour_with_city = dict(tour)
                tour_with_city.setdefault("city_id", 1)
                self.insert_tour_with_points(tour_with_city)

    def reload_places_from_json(self):
        """Полностью перезагружает таблицу places из базового файла places.json.

        Полезно после изменения структуры JSON (добавление name_ru/name_en и т.п.).
        """
        cur = self.conn.cursor()
        cur.execute("DELETE FROM places")
        self.conn.commit()

        if os.path.exists(PLACES_JSON):
            with open(PLACES_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
            for place in data:
                place_with_city = dict(place)
                place_with_city.setdefault("city_id", 1)
                self.insert_place(place_with_city)

    def insert_place(self, place):
        cur = self.conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO places
            (id, name, name_ru, name_en, category,
             description, description_ru, description_en,
             short_desc, short_desc_ru, short_desc_en,
             lat, lon, address, phone,
             website, price, hours, rating, image_urls, city_id)
            VALUES (:id, :name, :name_ru, :name_en, :category,
                    :description, :description_ru, :description_en,
                    :short_desc, :short_desc_ru, :short_desc_en,
                    :lat, :lon, :address, :phone,
                    :website, :price, :hours, :rating, :image_urls, :city_id)
            """,
            {
                "id": place.get("id"),
                # Базовое имя для совместимости и ru/en-колонки для локализации
                "name": place.get("name")
                or place.get("name_ru")
                or place.get("name_en"),
                "name_ru": place.get("name_ru") or place.get("name"),
                "name_en": place.get("name_en"),
                "category": place.get("category"),
                "description": place.get("description")
                or place.get("description_ru"),
                "description_ru": place.get("description_ru")
                or place.get("description"),
                "description_en": place.get("description_en"),
                "short_desc": place.get("short_desc")
                or place.get("short_desc_ru"),
                "short_desc_ru": place.get("short_desc_ru")
                or place.get("short_desc"),
                "short_desc_en": place.get("short_desc_en"),
                "lat": place.get("lat"),
                "lon": place.get("lon"),
                "address": place.get("address"),
                "phone": place.get("phone"),
                "website": place.get("website"),
                "price": place.get("price"),
                "hours": place.get("hours"),
                "rating": place.get("rating"),
                "image_urls": json.dumps(place.get("image_urls", []), ensure_ascii=False),
                "city_id": place.get("city_id", 1),
            },
        )
        self.conn.commit()

    def get_all_places(self):
        city = self.get_active_city()
        cur = self.conn.cursor()
        if city:
            cur.execute("SELECT * FROM places WHERE city_id = ?", (city["id"],))
        else:
            cur.execute("SELECT * FROM places")
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    # --- Reviews ---

    def add_review(self, place_id, rating, comment, user_id=1, created_at=""):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO reviews (place_id, user_id, rating, comment, created_at) VALUES (?, ?, ?, ?, ?)",
            (place_id, user_id, rating, comment, created_at),
        )
        self.conn.commit()

    def get_reviews_for_place(self, place_id):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, place_id, user_id, rating, comment, created_at FROM reviews WHERE place_id = ? ORDER BY id DESC",
            (place_id,),
        )
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def delete_tour(self, tour_id):
        """Удаляет экскурсию и связанные с ней точки и прогресс пользователя."""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM tour_points WHERE tour_id = ?", (tour_id,))
        cur.execute("DELETE FROM user_tours WHERE tour_id = ?", (tour_id,))
        cur.execute("DELETE FROM tours WHERE id = ?", (tour_id,))
        self.conn.commit()

    # --- User tour progress ---

    def get_user_tour_progress(self, tour_id, user_id=1):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT user_id, tour_id, progress, current_point, started_at, completed_at, rating_user FROM user_tours WHERE user_id = ? AND tour_id = ?",
            (user_id, tour_id),
        )
        row = cur.fetchone()
        if not row:
            return None
        columns = [c[0] for c in cur.description]
        return dict(zip(columns, row))

    def upsert_user_tour_progress(
        self,
        tour_id,
        progress,
        current_point,
        started_at=None,
        completed_at=None,
        rating_user=None,
        user_id=1,
    ):
        cur = self.conn.cursor()
        cur.execute(
            """INSERT INTO user_tours
            (user_id, tour_id, progress, current_point, started_at, completed_at, rating_user)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, tour_id) DO UPDATE SET
                progress=excluded.progress,
                current_point=excluded.current_point,
                started_at=COALESCE(excluded.started_at, user_tours.started_at),
                completed_at=excluded.completed_at,
                rating_user=COALESCE(excluded.rating_user, user_tours.rating_user)
            """,
            (user_id, tour_id, progress, current_point, started_at, completed_at, rating_user),
        )
        self.conn.commit()

    # --- Tours ---

    def insert_tour_with_points(self, tour):
        cur = self.conn.cursor()
        cur.execute(
            """INSERT OR REPLACE INTO tours
            (id, title, description, theme, duration, distance, cover_image,
             audio_intro, is_linear, rating, price, author_id, city_id)
            VALUES (:id, :title, :description, :theme, :duration, :distance,
                    :cover_image, :audio_intro, :is_linear, :rating, :price,
                    :author_id, :city_id)
            """,
            {
                "id": tour.get("id"),
                "title": tour.get("title"),
                "description": tour.get("description"),
                "theme": tour.get("theme"),
                "duration": tour.get("duration"),
                "distance": tour.get("distance"),
                "cover_image": tour.get("cover_image"),
                "audio_intro": tour.get("audio_intro"),
                "is_linear": tour.get("is_linear", 1),
                "rating": tour.get("rating"),
                "price": tour.get("price"),
                "author_id": tour.get("author_id"),
                "city_id": tour.get("city_id", 1),
            },
        )
        # точки тура
        points = tour.get("points", [])
        for point in points:
            cur.execute(
                """INSERT INTO tour_points
                (tour_id, place_id, order_index, audio_story, quiz_question)
                VALUES (?, ?, ?, ?, ?)""",
                (
                    tour.get("id"),
                    point.get("place_id"),
                    point.get("order_index"),
                    point.get("audio_story", ""),
                    point.get("quiz_question", ""),
                ),
            )
        self.conn.commit()

    def get_all_tours(self):
        city = self.get_active_city()
        cur = self.conn.cursor()
        if city:
            cur.execute("SELECT * FROM tours WHERE city_id = ?", (city["id"],))
        else:
            cur.execute("SELECT * FROM tours")
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def get_all_tours_with_progress(self, user_id=1):
        """Возвращает список туров и прогресс пользователя по каждому из них."""
        city = self.get_active_city()
        cur = self.conn.cursor()
        if city:
            cur.execute(
                """SELECT t.*, ut.progress, ut.current_point, ut.completed_at
                FROM tours t
                LEFT JOIN user_tours ut
                    ON t.id = ut.tour_id AND ut.user_id = ?
                WHERE t.city_id = ?""",
                (user_id, city["id"]),
            )
        else:
            cur.execute(
                """SELECT t.*, ut.progress, ut.current_point, ut.completed_at
                FROM tours t
                LEFT JOIN user_tours ut
                    ON t.id = ut.tour_id AND ut.user_id = ?""",
                (user_id,),
            )
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def get_tour(self, tour_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM tours WHERE id = ?", (tour_id,))
        row = cur.fetchone()
        if not row:
            return None
        columns = [c[0] for c in cur.description]
        return dict(zip(columns, row))

    def get_points_for_tour(self, tour_id):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT tour_id, place_id, order_index, audio_story, quiz_question, image_urls FROM tour_points WHERE tour_id = ? ORDER BY order_index",
            (tour_id,),
        )
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def set_tour_points(self, tour_id, points):
        """Перезаписывает список точек для указанной экскурсии.

        points — список словарей с ключами:
            - place_id: ID места
            - order_index: порядковый номер точки в маршруте (1..N)
        Дополнительные поля (audio_story, quiz_question) на данном этапе не используются
        и сохраняются как пустые строки.
        """
        cur = self.conn.cursor()
        # Удаляем старые точки тура
        cur.execute("DELETE FROM tour_points WHERE tour_id = ?", (tour_id,))

        if points:
            for point in points:
                cur.execute(
                    """INSERT INTO tour_points
                    (tour_id, place_id, order_index, audio_story, quiz_question, image_urls)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        tour_id,
                        point.get("place_id"),
                        point.get("order_index"),
                        point.get("audio_story", "") or "",
                        point.get("quiz_question", "") or "",
                        json.dumps(point.get("image_urls", []) or [], ensure_ascii=False),
                    ),
                )

        self.conn.commit()

    def get_place(self, place_id):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM places WHERE id = ?", (place_id,))
        row = cur.fetchone()
        if not row:
            return None
        columns = [c[0] for c in cur.description]
        return dict(zip(columns, row))

    # --- Admin helpers ---

    def delete_place(self, place_id):
        """Удаляет место и связанные с ним данные (избранное, отзывы, точки туров)."""
        cur = self.conn.cursor()
        # Удаляем ссылки из туров и избранного, затем само место
        cur.execute("DELETE FROM tour_points WHERE place_id = ?", (place_id,))
        cur.execute("DELETE FROM favorites WHERE place_id = ?", (place_id,))
        cur.execute("DELETE FROM reviews WHERE place_id = ?", (place_id,))
        cur.execute("DELETE FROM places WHERE id = ?", (place_id,))
        self.conn.commit()

    def update_place_basic(self, place_id, name, short_desc, description, address):
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE places SET name = ?, name_ru = ?, short_desc = ?, short_desc_ru = ?, description = ?, description_ru = ?, address = ? WHERE id = ?",
            (
                name,
                name,
                short_desc,
                short_desc,
                description,
                description,
                address,
                place_id,
            ),
        )
        self.conn.commit()

    def update_place_images(self, place_id, image_urls):
        """Обновляет список фотографий места (image_urls) для админ-редактора.

        image_urls ожидается как список строк-URL. В БД сохраняем JSON-строку,
        как и при insert_place.
        """
        try:
            import json

            data = json.dumps(image_urls or [], ensure_ascii=False)
        except Exception:
            data = "[]"

        cur = self.conn.cursor()
        cur.execute(
            "UPDATE places SET image_urls = ? WHERE id = ?",
            (data, place_id),
        )
        self.conn.commit()

    def update_place_coords(self, place_id, lat, lon):
        """Обновляет координаты места (lat/lon)."""
        cur = self.conn.cursor()
        cur.execute("UPDATE places SET lat = ?, lon = ? WHERE id = ?", (lat, lon, place_id))
        self.conn.commit()

    def add_favorite(self, place_id, user_id=1):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO favorites (user_id, place_id) VALUES (?, ?)",
            (user_id, place_id),
        )
        self.conn.commit()

    def remove_favorite(self, place_id, user_id=1):
        cur = self.conn.cursor()
        cur.execute(
            "DELETE FROM favorites WHERE user_id = ? AND place_id = ?",
            (user_id, place_id),
        )
        self.conn.commit()

    def is_favorite(self, place_id, user_id=1):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND place_id = ?",
            (user_id, place_id),
        )
        return cur.fetchone() is not None

    def get_favorite_places(self, user_id=1):
        cur = self.conn.cursor()
        cur.execute(
            """SELECT p.* FROM places p
            JOIN favorites f ON p.id = f.place_id
            WHERE f.user_id = ?""",
            (user_id,),
        )
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    # --- Users (многопользовательская модель) ---

    def get_all_users(self):
        """Возвращает список всех пользователей как dict с полями id, username, role.

        Пароли не возвращаем по соображениям безопасности.
        """
        cur = self.conn.cursor()
        cur.execute("SELECT id, username, role FROM users ORDER BY id")
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def get_user_by_username(self, username: str):
        """Возвращает пользователя по логину или None."""
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        if not row:
            return None
        columns = [c[0] for c in cur.description]
        return dict(zip(columns, row))

    def create_user(
        self,
        username: str,
        password_plain: str,
        role: str = "user",
        first_name: str = "",
        last_name: str = "",
        email: str = "",
        secret_word: str = "",
    ):
        """Создаёт нового пользователя с хэшированным паролем и доп. полями.

        Возвращает id созданного пользователя.
        """
        username = (username or "").strip()
        password_plain = (password_plain or "").strip()
        if not username or not password_plain:
            raise ValueError("username and password are required")
        if role not in ("admin", "user"):
            role = "user"

        first_name = (first_name or "").strip()
        last_name = (last_name or "").strip()
        email = (email or "").strip()
        secret_word = (secret_word or "").strip()

        password_hash = hashlib.sha256(password_plain.encode("utf-8")).hexdigest()
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO users (username, password_hash, role, first_name, last_name, email, secret_word) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (username, password_hash, role, first_name, last_name, email, secret_word),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_user(self, user_id: int, username: str, password_plain: str = None, role: str = None):
        """Обновляет данные пользователя.

        Если password_plain пустой, пароль не меняется.
        Если role не указана, роль не меняем.
        """
        username = (username or "").strip()
        if not username:
            raise ValueError("username is required")

        cur = self.conn.cursor()
        if password_plain:
            password_hash = hashlib.sha256(password_plain.encode("utf-8")).hexdigest()
            if role in ("admin", "user"):
                cur.execute(
                    "UPDATE users SET username = ?, password_hash = ?, role = ? WHERE id = ?",
                    (username, password_hash, role, user_id),
                )
            else:
                cur.execute(
                    "UPDATE users SET username = ?, password_hash = ? WHERE id = ?",
                    (username, password_hash, user_id),
                )
        else:
            if role in ("admin", "user"):
                cur.execute(
                    "UPDATE users SET username = ?, role = ? WHERE id = ?",
                    (username, role, user_id),
                )
            else:
                cur.execute(
                    "UPDATE users SET username = ? WHERE id = ?",
                    (username, user_id),
                )
        self.conn.commit()

    def delete_user(self, user_id: int):
        """Удаляет пользователя по id. Встроенного admin (id=1) лучше не трогать."""
        cur = self.conn.cursor()
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        self.conn.commit()

    # --- Сообщения техподдержки ---

    def add_support_message(self, user_id: int, is_admin_sender: bool, message: str, created_at: str = ""):
        """Добавляет сообщение в переписку техподдержки.

        user_id — id пользователя, к которому относится переписка.
        is_admin_sender — True, если пишет админ, False — если пользователь.
        """
        message = (message or "").strip()
        if not user_id or not message:
            return
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO support_messages (user_id, is_admin_sender, message, created_at) VALUES (?, ?, ?, ?)",
            (int(user_id), 1 if is_admin_sender else 0, message, created_at or ""),
        )
        self.conn.commit()

    def get_support_messages_for_user(self, user_id: int):
        """Возвращает все сообщения переписки для указанного пользователя."""
        cur = self.conn.cursor()
        cur.execute(
            "SELECT id, user_id, is_admin_sender, message, created_at FROM support_messages WHERE user_id = ? ORDER BY id",
            (int(user_id),),
        )
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]

    def get_support_users_with_last_message(self):
        """Список пользователей, у которых есть переписка, с последним сообщением.

        Используется в админке для выбора диалога.
        """
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT u.id AS user_id,
                   u.username AS username,
                   (SELECT message FROM support_messages sm2 WHERE sm2.user_id = u.id ORDER BY sm2.id DESC LIMIT 1) AS last_message
            FROM users u
            WHERE EXISTS (SELECT 1 FROM support_messages sm WHERE sm.user_id = u.id)
            ORDER BY u.username
            """
        )
        columns = [c[0] for c in cur.description]
        return [dict(zip(columns, row)) for row in cur.fetchall()]
