import psycopg2
from psycopg2.extras import RealDictCursor

class Database:
    def __init__(self):
        try:
            self.conn = psycopg2.connect(
                dbname="dating_site",
                user="postgres",
                password="postgres",
                host="localhost",
                port="5432"
            )
            print("Successfully connected to the database")
            self.create_tables()
        except Exception as e:
            print(f"Error connecting to the database: {e}")

    def create_tables(self):
        try:
            with self.conn.cursor() as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        name TEXT NOT NULL,
                        email TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        age INTEGER,
                        bio TEXT,
                        photo TEXT
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS posts (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        content TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS comments (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        post_id INTEGER REFERENCES posts(id),
                        content TEXT NOT NULL,
                        created_at TIMESTAMP NOT NULL
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS likes (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        post_id INTEGER REFERENCES posts(id),
                        UNIQUE(user_id, post_id)
                    )
                ''')
                
                # Проверяем, существует ли столбец post_id в таблице likes
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='likes' AND column_name='post_id'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE likes ADD COLUMN post_id INTEGER REFERENCES posts(id)")
                
                # Проверяем, существует ли столбец age в таблице users
                cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='age'")
                if not cursor.fetchone():
                    cursor.execute("ALTER TABLE users ADD COLUMN age INTEGER")
            
            print("Tables created successfully")
            self.conn.commit()
        except Exception as e:
            print(f"Error creating tables: {e}")

    def get_random_profiles(self, limit, exclude_id=None, offset=0):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            try:
                if exclude_id:
                    cursor.execute("""
                        SELECT * FROM users 
                        WHERE id != %s 
                        ORDER BY RANDOM() 
                        LIMIT %s OFFSET %s
                    """, (exclude_id, limit, offset))
                else:
                    cursor.execute("SELECT * FROM users ORDER BY RANDOM() LIMIT %s OFFSET %s", (limit, offset))
                
                profiles = cursor.fetchall()
                return profiles if profiles else []  # Возвращаем пустой список, если нет результатов
            except Exception as e:
                print(f"Error in get_random_profiles: {e}")
                return []  # Возвращаем пустой список в случае ошибки

    def get_profile(self, user_id):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cursor.fetchone()

    def get_matches(self, user_id):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute('''
                SELECT DISTINCT u.* 
                FROM users u
                JOIN likes l1 ON u.id = l1.liked_user_id
                JOIN likes l2 ON u.id = l2.user_id
                WHERE l1.user_id = %s AND l2.liked_user_id = %s
                AND l1.liked_user_id = l2.user_id
                AND u.id != %s
            ''', (user_id, user_id, user_id))
            return cursor.fetchall()

    def add_like(self, user_id, liked_user_id):
        if user_id == liked_user_id:
            return False  # Нельзя лайкнуть самого себя
        with self.conn.cursor() as cursor:
            cursor.execute("INSERT INTO likes (user_id, liked_user_id) VALUES (%s, %s)", (user_id, liked_user_id))
            self.conn.commit()
            
            cursor.execute("SELECT * FROM likes WHERE user_id = %s AND liked_user_id = %s", (liked_user_id, user_id))
            return cursor.fetchone() is not None

    def get_user_by_email(self, email):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            return cursor.fetchone()

    def create_user(self, name, email, password):
        with self.conn.cursor() as cursor:
            try:
                cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
                self.conn.commit()
                return True
            except psycopg2.IntegrityError:
                self.conn.rollback()
                return False

    def update_profile(self, user_id, name, age, bio, photo_url):
        with self.conn.cursor() as cursor:
            try:
                if photo_url:
                    print(f"Updating profile with photo: user_id={user_id}, name={name}, age={age}, bio={bio}, photo_url={photo_url}")
                    cursor.execute("""
                        UPDATE users 
                        SET name = %s, age = %s, bio = %s, photo = %s
                        WHERE id = %s
                    """, (name, age, bio, photo_url, user_id))
                else:
                    print(f"Updating profile without photo: user_id={user_id}, name={name}, age={age}, bio={bio}")
                    cursor.execute("""
                        UPDATE users 
                        SET name = %s, age = %s, bio = %s
                        WHERE id = %s
                    """, (name, age, bio, user_id))
                self.conn.commit()
                print("Profile updated successfully")
                return True
            except psycopg2.Error as e:
                print(f"An error occurred while updating profile: {e}")
                self.conn.rollback()
                return False

    def __del__(self):
        self.conn.close()

    def create_post(self, user_id, content):
        with self.conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO posts (user_id, content, created_at)
                VALUES (%s, %s, NOW())
                RETURNING id
            """, (user_id, content))
            post_id = cursor.fetchone()[0]
            self.conn.commit()
            return post_id

    def get_posts(self, user_id):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT p.*, u.name as author_name, 
                       (SELECT COUNT(*) FROM likes WHERE post_id = p.id) as likes_count
                FROM posts p
                JOIN users u ON p.user_id = u.id
                WHERE p.user_id = %s
                ORDER BY p.created_at DESC
            """, (user_id,))
            return cursor.fetchall()

    def add_comment(self, user_id, post_id, content):
        with self.conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO comments (user_id, post_id, content, created_at)
                VALUES (%s, %s, %s, NOW())
                RETURNING id
            """, (user_id, post_id, content))
            comment_id = cursor.fetchone()[0]
            self.conn.commit()
            return comment_id

    def get_comments(self, post_id):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT c.*, u.name as author_name
                FROM comments c
                JOIN users u ON c.user_id = u.id
                WHERE c.post_id = %s
                ORDER BY c.created_at ASC
            """, (post_id,))
            return cursor.fetchall()

    def add_like(self, user_id, post_id):
        with self.conn.cursor() as cursor:
            try:
                cursor.execute("""
                    INSERT INTO likes (user_id, post_id)
                    VALUES (%s, %s)
                """, (user_id, post_id))
                self.conn.commit()
                return True
            except psycopg2.IntegrityError:
                self.conn.rollback()
                return False

    def remove_like(self, user_id, post_id):
        with self.conn.cursor() as cursor:
            cursor.execute("""
                DELETE FROM likes
                WHERE user_id = %s AND post_id = %s
            """, (user_id, post_id))
            self.conn.commit()
            return cursor.rowcount > 0
