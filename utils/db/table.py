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

    def add_bot(self, user_id, bot_id, name, last_online):
        query = """
        INSERT INTO bots (user_id, bot_id, name, last_online)
        VALUES (%s, %s, %s, %s)
        RETURNING id;
        """
        return self.db.execute(query, (user_id, bot_id, name, last_online), commit=True)

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
