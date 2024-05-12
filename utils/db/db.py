import psycopg2
import logging
import os

class Database:
    def __init__(self):
        self.dsn = os.getenv('DATABASE_URL')
        self.conn = None

    def connect(self):
        try:
            self.conn = psycopg2.connect(self.dsn)
            logging.debug("データベースに接続しました。")
            return self.conn
        except Exception as e:
            logging.error(f"データベース接続に失敗しました: {e}")
            return None

    def close(self):
        if self.conn:
            self.conn.close()
            logging.debug("データベース接続を閉じました。")
        
    def commit(self):
        self.conn.commit()
        logging.debug("データベースに変更をコミットしました。")

    def execute(self, query, params=None, commit=False, cursor_factory=None):
        with self.conn.cursor(cursor_factory=cursor_factory) as cursor:
            cursor.execute(query, params)
            if commit:
                self.conn.commit()
            if cursor.description:
                return cursor.fetchall()
            return None

