import discord
from discord.ext import tasks
from discord import app_commands
from discord.app_commands import command
from discord.ext.commands import GroupCog

import logging
from datetime import datetime, timedelta, timezone

from utils.db.table import BotTable
from utils.db.db import Database

class DatabaseSetup:
    def __init__(self):
        self.db = Database()
        self.db_connection = self.db.connect()
        if self.db_connection is None:
            logging.error("データベースへの接続に失敗しました。")
            return
        self.bot_table = BotTable(self.db)

    def create_tables(self):
        self.bot_table.create_dm_table()
        self.bot_table.create_channel_table()

    def close_connection(self):
        self.db.close()


class HealthCheckGroup(GroupCog, group_name='hc', group_description='Health check commands for bots'):
    def __init__(self, bot, db_connection):
        self.bot = bot
        self.db = BotTable(db_connection)
        self.check_bots.start()
        self.log_setup()
        logging.debug('HealthCheckGroup initialized')

    def log_setup(self):
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def cog_unload(self):
        self.check_bots.cancel()

    async def bot_list_autocomplete(self, interaction: discord.Interaction, current: str):
        your_bots = self.db.get_bots(interaction.user.id)
        choices = []
        for bot in your_bots:
            if current in bot['name']:
                choices.append(app_commands.Choice(name=bot['name'], value=bot['id']))
                logging.debug(f"{bot['name']}: {bot['id']}")
        return choices
    
    async def bot_autocomplete(self, interaction: discord.Interaction, current: str):
        server_bots = [member for member in interaction.guild.members if member.bot]
        logging.debug(f"サーバーのBOTリスト: {server_bots}")
        choices = []
        current_lower = current.lower()
        for bot in server_bots:
            if current_lower in bot.name.lower():
                choices.append(app_commands.Choice(name=bot.name, value=str(bot.id)))
                logging.debug(f"{bot.name}: {bot.id}")
        if not choices:
            choices.append(app_commands.Choice(name="選択肢が見つかりません", value="none"))
        return choices

    @command(name='add', description='BOTを監視リストに追加します。')
    @app_commands.autocomplete(bot=bot_autocomplete)
    @app_commands.describe(bot='BOTを選択してください。')
    async def add_bot(self, interaction, bot: str):
        bot_member = interaction.guild.get_member(int(bot))
        if bot_member is None or not bot_member.bot:
            await interaction.response.send_message("指定されたユーザーはBOTではありません。")
            return
        self.db.add_bot(interaction.user.id, bot_member.id, bot_member.name, datetime.utcnow())
        await interaction.response.send_message(f"{bot_member.name}を監視リストに追加しました。")

    @command(name='channel_add', description='チャンネルに通知を送信するBOTを追加します。')
    @app_commands.autocomplete(bot=bot_autocomplete)
    @app_commands.describe(bot='BOTを選択してください。')
    @app_commands.describe(channel='通知を送信するチャンネルを選択してください。')
    async def add_channel(self, interaction: discord.Interaction, bot: str, channel: discord.TextChannel):
        bot_member = interaction.guild.get_member(int(bot))
        if bot_member is None or not bot_member.bot:
            await interaction.response.send_message("指定されたユーザーはBOTではありません。")
            return

        self.db.add_channel(bot_member.id, channel.id)
        await interaction.response.send_message(f"{channel.mention}に{bot_member.mention}の通知を追加しました。")

    @command(name='list', description='あなたが登録しているBOTのリストを表示します。')
    async def list_bots(self, interaction):
        bots = self.db.get_bots(interaction.user.id)
        bot_names = ', '.join(bot['name'] for bot in bots)
        e = discord.Embed(title='登録されているBOT', description=bot_names)
        e.set_footer(text=f"{len(bots)}個のBOTが登録されています。")
        await interaction.response.send_message(embed=e)

    @command(name='rm', description='あなたが登録しているBOTをリストから削除します。')
    @app_commands.autocomplete(bot=bot_list_autocomplete)
    @app_commands.describe(bot='BOTを選択してください。')
    async def remove_bot(self, interaction, bot: str):
        self.db.remove_bot(bot)
        await interaction.response.send_message("指定されたBOTをリストから削除しました。")

    @tasks.loop(minutes=1)
    async def check_bots(self):
        logging.debug('Checking bots...')
        try:
            for guild in self.bot.guilds:
                bots = self.db.get_bots(guild)
                for bot in bots:
                    user_id = self.find_user_by_bot_id(bot.id)
                    if user_id is not None:
                        bot_data = self.db.get_bot_data(bot.id)
                        if bot_data:
                            bot_member = guild.get_member(bot_data['id'])
                            if bot_member:
                                last_online = datetime.fromisoformat(bot_data['last_online'])
                                if bot_member.status != discord.Status.online:
                                    logging.debug(f"BOT: {bot_member.name}")
                                    logging.debug(f"BOT: {bot_member.status}")
                                    logging.debug(f"最終オンライン: {last_online}")
                                    if datetime.utcnow() - last_online > timedelta(minutes=10):
                                        last_notified = bot_data.get('last_notification_time')
                                        if last_notified is None:
                                            last_notified = datetime.utcnow() - timedelta(minutes=11)
                                            logging.debug(f"最終通知: {last_notified}")
                                        else:
                                            last_notified = datetime.fromisoformat(last_notified)

                                        if datetime.utcnow() - last_notified > timedelta(minutes=10):
                                            logging.debug(f"{bot_member.name}がオフラインになって10分が経過しました。")
                                            notification_channel = self.db.get_notification_channel(guild.id)
                                            if notification_channel:
                                                logging.debug(f"通知チャンネル: {notification_channel.name}")
                                                now_jst = datetime.now(timezone(timedelta(hours=9)))
                                                e = discord.Embed(title='BOTがオフラインになりました。', description=f"{bot_member.name}がオフラインになって10分が経過しました。", color=discord.Color.red(), timestamp=now_jst)
                                                last_online_time = datetime.fromisoformat(bot_data['last_online'])
                                                last_online_timestamp = last_online_time.timestamp()
                                                e.add_field(name='BOT情報', value=f"ID: {bot_member.id}\n名前: {bot_member.name}\nオフライン時間: <t:{int(last_online_timestamp)}:F> | <t:{int(last_online_timestamp)}:R>")
                                                await notification_channel.send(embed=e)
                                                self.db.update_last_channel_notification_time(bot_member.id, datetime.utcnow().isoformat())
                                                logging.debug(f"{bot_member.name}にチャンネル通知を送信しました。")
                                            else:
                                                logging.debug("通知チャンネルが見つかりません。")
                                            if user_id is not None:
                                                user = self.bot.get_user(int(user_id))
                                                if user:
                                                    dm_channel = user.dm_channel or await user.create_dm()
                                                    now_jst = datetime.now(timezone(timedelta(hours=9)))
                                                    e = discord.Embed(title='BOTがオフラインになりました。', description=f"{bot_member.name}がオフラインになって10分が経過しました。", color=discord.Color.red(), timestamp=now_jst)
                                                    last_online_time = datetime.fromisoformat(bot_data['last_online'])
                                                    last_online_timestamp = last_online_time.timestamp()
                                                    e.add_field(name='BOT情報', value=f"ID: {bot_member.id}\n名前: {bot_member.name}\nオフライン時間: <t:{int(last_online_timestamp)}:F> | <t:{int(last_online_timestamp)}:R>")
                                                    await dm_channel.send(embed=e)
                                                    self.db.update_last_dm_notification_time(bot_member.id, datetime.utcnow().isoformat())
                                                    logging.debug(f"{bot_member.name}にDMを送信しました。")
                                                else:
                                                    logging.error("ユーザーが見つかりません。")
                                            self.db.update_last_notification_time(bot_member.id, datetime.utcnow().isoformat())
                                        else:
                                            logging.debug(f"{bot_member.name}に通知を送信済みです。")
                                    else:
                                        nokori = timedelta(minutes=10) - (datetime.utcnow() - last_online)
                                        if nokori.total_seconds() > 0:
                                            logging.debug(f"{bot_member.name}がオフラインになって10分未満です。:あと{nokori}")
                                        else:
                                            logging.debug(f"{bot_member.name}がオフラインになって10分未満です。")
                                else:
                                    logging.debug(f"{bot_member.name}はオンラインです。")
                                    if notification_channel is not None:
                                        self.db.update_last_channel_online_notification_time(bot_member.id, datetime.utcnow().isoformat())
                                        if datetime.utcnow() - datetime.fromisoformat(bot_data['last_channel_online_notification_time']) == None:
                                            now_jst = datetime.now(timezone(timedelta(hours=9)))
                                            e = discord.Embed(title='BOTがオンラインになりました。', description=f"{bot_member.name}がオンラインになりました。", color=discord.Color.green(), timestamp=now_jst)
                                            last_online_time = datetime.fromisoformat(bot_data['last_online'])
                                            last_online_timestamp = last_online_time.timestamp()
                                            e.add_field(name='BOT情報', value=f"ID: {bot_member.id}\n名前: {bot_member.name}\nオンライン時間: <t:{int(last_online_timestamp)}:F> | <t:{int(last_online_timestamp)}:R>")
                                            await notification_channel.send(embed=e)
                                            self.db.update_last_channel_online_notification_time(bot_member.id, datetime.utcnow().isoformat())
                                        else:
                                            logging.debug("通知チャンネルが見つかりません。")
                                        if user_id is not None:
                                            user = self.bot.get_user(int(user_id))
                                            if user:
                                                self.db.update_last_dm_online_notification_time(bot_member.id, datetime.utcnow().isoformat())
                                                if datetime.utcnow() - datetime.fromisoformat(bot_data['last_dm_online_notification_time']) == None:
                                                    dm_channel = user.dm_channel or await user.create_dm()
                                                    now_jst = datetime.now(timezone(timedelta(hours=9)))
                                                    e = discord.Embed(title='BOTがオンラインになりました。', description=f"{bot_member.name}がオンラインになりました。", color=discord.Color.green(), timestamp=now_jst)
                                                    last_online_time = datetime.fromisoformat(bot_data['last_online'])
                                                    last_online_timestamp = last_online_time.timestamp()
                                                    e.add_field(name='BOT情報', value=f"ID: {bot_member.id}\n名前: {bot_member.name}\nオンライン時間: <t:{int(last_online_timestamp)}:F> | <t:{int(last_online_timestamp)}:R>")
                                                    await dm_channel.send(embed=e)
                                                    self.db.update_last_dm_online_notification_time(bot_member.id, datetime.utcnow().isoformat())
                                            bot_data['last_online'] = datetime.utcnow().isoformat()
                                            self.db.update_bot_last_online(bot_member.id, datetime.utcnow().isoformat())
                                            last_notified = bot_data.get('last_notification_time', None)
                                            if last_notified is not None:
                                                self.db.reset_last_notification_time(bot_member.id)
                                                logging.debug(f"{bot_member.name}のオンライン時間と通知時間を更新しました。")
                                            else:

                                                logging.debug(f"{bot_member.name}のオンライン時間を更新しました。")
                            else:
                                logging.debug(f"BOT: {bot_data['name']} が見つかりません。")
                    else:
                        logging.debug(f"ユーザーが見つかりません。")
        except Exception as e:
            logging.error(f"BOTのヘルスチェック中にエラーが発生しました: {e}")
            pass 

async def setup(bot):
    db_setup = DatabaseSetup()
    if db_setup.db_connection is None:
        logging.error("データベースへの接続に失敗しました。")
        return
    db_setup.create_tables()
    await bot.add_cog(HealthCheckGroup(bot, db_setup.db_connection))
