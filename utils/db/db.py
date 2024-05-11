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

    def execute(self, query, params=None, commit=False):
        # connection オブジェクトから cursor を生成
        cursor = self.conn.cursor()

        # cursor を使用してクエリを実行
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        # 必要に応じて結果を取得
        if query.strip().lower().startswith("select"):
            results = cursor.fetchall()
        else:
            results = None

        # cursor を閉じる
        cursor.close()

        if commit:
            self.conn.commit()

        return results

