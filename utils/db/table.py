from .db import Database

class BotTable:
    def __init__(self, db: Database):
        self.db = db

    def create_dm_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS bots (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            bot_id BIGINT NOT NULL,
            name TEXT NOT NULL,
            last_online TIMESTAMP,
            last_notification_time TIMESTAMP,
            last_channel_notification_time TIMESTAMP,
            last_dm_notification_time TIMESTAMP,
            last_channel_online_notification_time TIMESTAMP,
            last_dm_online_notification_time TIMESTAMP,
            guild_id BIGINT NOT NULL
        );
        """
        self.db.execute(query, commit=True)

    def create_channel_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS channels (
            id SERIAL PRIMARY KEY,
            channel_id BIGINT NOT NULL,
            bot_id BIGINT NOT NULL,
            name TEXT NOT NULL,
            last_online TIMESTAMP,
            last_notification_time TIMESTAMP,
            last_channel_notification_time TIMESTAMP,
            last_dm_notification_time TIMESTAMP,
            last_channel_online_notification_time TIMESTAMP,
            last_dm_online_notification_time TIMESTAMP
        );
        """
        self.db.execute(query, commit=True)

    def add_bot(self, user_id, bot_id, name, last_online, guild_id):
        query = """
        INSERT INTO bots (user_id, bot_id, name, last_online, guild_id)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id;
        """
        return self.db.execute(query, (user_id, bot_id, name, last_online, guild_id), commit=True)

    def add_channel(self, bot_id, channel_id, channel_name):
        query = """
        INSERT INTO channels (bot_id, channel_id, name)
        VALUES (%s, %s, %s)
        RETURNING id;
        """
        return self.db.execute(query, (bot_id, channel_id, channel_name), commit=True)

    def remove_bot(self, bot_id):
        query = """
        DELETE FROM bots WHERE bot_id = %s;
        """
        self.db.execute(query, (bot_id,), commit=True)

    def update_bot(self, bot_id, **kwargs):
        set_clause = ', '.join([f"{key} = %s" for key in kwargs])
        values = list(kwargs.values())
        query = f"UPDATE bots SET {set_clause} WHERE bot_id = %s;"
        values.append(bot_id)
        self.db.execute(query, values, commit=True)

    def get_bots(self, guild_id):
        query = "SELECT * FROM bots WHERE guild_id = %s"
        return self.db.execute(query, (guild_id,))
    
    def reset_table(self):
        query = "TRUNCATE TABLE bots;"
        self.db.execute(query, commit=True)
        query = "TRUNCATE TABLE channels;"
        self.db.execute(query, commit=True)

    def find_user_by_bot_id(self, bot_id):
        query = "SELECT user_id FROM bots WHERE bot_id = %s;"
        result = self.db.execute(query, (bot_id,))
        if result:
            return result[0]['user_id']
        return None

    def get_bot_data(self, bot_id):
        query = "SELECT * FROM bots WHERE bot_id = %s;"
        result = self.db.execute(query, (bot_id,))
        if result:
            return result[0]  # 最初の結果を返す
        return None

    def update_last_notification_time(self, bot_id, new_time, column_name):
        query = f"UPDATE bots SET {column_name} = %s WHERE bot_id = %s;"
        self.db.execute(query, (new_time, bot_id), commit=True)

    def get_notification_channel(self, guild_id):
        query = "SELECT notification_channel_id FROM guild_settings WHERE guild_id = %s;"  # 仮のテーブル名とカラム名
        result = self.db.execute(query, (guild_id,))
        if result:
            return result[0]['notification_channel_id']  # 通知チャンネルIDを返す
        return None

    def reset_last_notification_time(self, bot_id):
        query = "UPDATE bots SET last_notification_time = NULL WHERE bot_id = %s;"
        self.db.execute(query, (bot_id,), commit=True)
