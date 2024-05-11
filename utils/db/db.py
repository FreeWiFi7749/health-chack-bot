import psycopg2
from psycopg2.extras import RealDictCursor
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
        except Exception as e:
            logging.error(f"データベース接続に失敗しました: {e}")

    def close(self):
        if self.conn:
            self.conn.close()
            logging.debug("データベース接続を閉じました。")

    def execute(self, query, params=None, commit=False):
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            if commit:
                self.conn.commit()
            return cursor.fetchall()

    def commit(self):
        self.conn.commit()
        logging.debug("データベースに変更をコミットしました。")
        logging.debug("データベースに変更をコミットしました。")