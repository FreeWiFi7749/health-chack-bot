import discord
from discord.ext import tasks
from discord import app_commands
from discord.app_commands import command
from discord.ext.commands import GroupCog

import json
import logging
import os
from datetime import datetime, timedelta


class HealthCheckGroup(GroupCog, group_name='hc', group_description='Health check commands for bots'):
    def __init__(self, bot):
        self.bot = bot
        self.last_notification_time = {}
        self.check_bots.start()
        self.log_setup()
        logging.debug('HealthCheckGroup initialized')

    def log_setup(self):
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def cog_unload(self):
        self.check_bots.cancel()

    async def bot_list_autocomplete(self, interaction: discord.Interaction, current: str):
        your_bots = self.load_data(f'data/hc/{interaction.user.id}/list.json', interaction.user.id)
        choices = []
        for bot in your_bots:
            if current in bot['name']:
                choices.append(app_commands.Choice(name=bot['name'], value=bot['id']))
                logging.debug(f"{bot['name']}: {bot['id']}")
        logging.debug(choices)
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
        logging.debug(f"選択肢: {choices}")
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
        directory = f'data/hc/{interaction.user.id}'
        if not os.path.exists('data/hc'):
            os.makedirs('data/hc', exist_ok=True)
        os.makedirs(directory, exist_ok=True)
        file_path = f'{directory}/list.json'
        data = self.load_data(file_path, interaction.user.id)
        data['bots'].append({
            'name': bot_member.name, 
            'id': bot_member.id, 
            'last_online': datetime.utcnow().isoformat(),
            'last_notification_time': None,
            'last_channel_online_notification_time': None,
            'last_dm_online_notification_time': None,
        })
        self.save_data(file_path, data, interaction.user.id)
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

        directory = f'data/hc/{channel.guild.id}'
        if not os.path.exists('data/hc'):
            os.makedirs('data/hc', exist_ok=True)
        os.makedirs(directory, exist_ok=True)
        ch = channel.guild.get_channel(channel.id)
        logging.debug(f"チャンネル: {ch.name}")
        logging.debug(f"チャンネルID: {ch.id}")
        logging.debug(f"チャンネル名: {ch.name}")
        file_path = f'{directory}/channel.json'
        data = self.load_channel_data(file_path)
        data['bots'].append({
            'name': bot_member.name,
            'id': bot_member.id,
            'channel_id': ch.id,
            'last_online': datetime.utcnow().isoformat(),
            'last_notification_time': None,
            'last_channel_online_notification_time': None,
            'last_dm_online_notification_time': None
        })
        self.save_channel_data(file_path, data)
        await interaction.response.send_message(f"{channel.mention}に{bot_member.mention}の通知を追加しました。")
        

    @command(name='list', description='あなたが登録しているBOTのリストを表示します。')
    async def list_bots(self, interaction):
        directory = 'data/hc'
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        user_directory = f'{directory}/{interaction.user.id}'
        if not os.path.exists(user_directory):
            await interaction.response.send_message("あなたはまだBOTを登録していません。")
            return
        file_path = f'{user_directory}/list.json'
        data = self.load_data(file_path, interaction.user.id)
        bots = [self.bot.get_user(bot['id']) for bot in data['bots']]
        bot_names = ', '.join(bot.name for bot in bots if bot)
        e = discord.Embed(title='登録されているBOT', description=bot_names)
        e.set_footer(text=f"{len(bots)}個のBOTが登録されています。")
        await interaction.response.send_message(embed=e)

    @command(name='rm', description='あなたが登録しているBOTをリストから削除します。')
    @app_commands.autocomplete(bot=bot_list_autocomplete)
    @app_commands.describe(bot='BOTを選択してください。')
    async def remove_bot(self, interaction, bot: str):
        if not bot.bot:
            await interaction.response.send_message("指定されたユーザーはBOTではありません。")
            return
        file_path = f'data/hc/{interaction.user.id}/list.json'
        data = self.load_data(file_path, interaction.user.id)
        data['bots'] = [bot for bot in data['bots'] if bot['id'] != bot]
        self.save_data(file_path, data, interaction.user.id)
        await interaction.response.send_message("指定されたBOTをリストから削除しました。")

    def save_data(self, file_path, data, user_id):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
            logging.debug(f"Data for {user_id} saved at {file_path}")

    def load_data(self, file_path, user_id):
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                content = json.load(file)
                return content
        return {'bots': []}
    
    def save_channel_data(self, file_path, data):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as file:
            json.dump(data, file, indent=4)
            logging.debug(f"Channel data saved at {file_path}")


    def load_channel_data(self, file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                content = json.load(file)
                return content
        return {'bots': []}

    def get_bots(self, guild):
        return [member for member in guild.members if member.bot]

    def find_user_by_bot_id(self, bot_id):
        base_path = 'data/hc'
        for user_id in os.listdir(base_path):
            user_path = os.path.join(base_path, user_id, 'list.json')
            if os.path.exists(user_path):
                with open(user_path, 'r') as file:
                    data = json.load(file)
                    for bot in data['bots']:
                        if bot['id'] == bot_id:
                            return user_id
        return None

    @tasks.loop(minutes=1)
    async def check_bots(self):
        logging.debug('Checking bots...')
        if 'data/hc' not in os.listdir():
            os.makedirs('data/hc', exist_ok=True)
        try:
            for guild in self.bot.guilds:
                bots = self.get_bots(guild)
                channel_file_path = f'data/hc/{guild.id}/channel.json'
                channel_data = self.load_channel_data(channel_file_path)
                if channel_data['bots']:
                    notification_channel_id = channel_data['bots'][0]['channel_id']
                    notification_channel = guild.get_channel(notification_channel_id)
                    if notification_channel:
                        logging.debug(f"通知チャンネル: {notification_channel.name}")
                    else:
                        logging.error(f"チャンネルID {notification_channel_id} でチャンネルが見つかりません。")
                else:
                    logging.error("チャンネルデータにBOTが登録されていません。")

                for bot in bots:
                    user_id = self.find_user_by_bot_id(bot.id)
                    if user_id is not None:
                        file_path = f'data/hc/{user_id}/list.json'
                        data_dict = self.load_data(file_path, user_id)
                        data = data_dict.get('bots', [])
                        for bot_data in data:
                            bot_member = guild.get_member(bot_data['id'])
                            if bot_member:
                                last_online = datetime.fromisoformat(bot_data['last_online'])
                                if bot_member.status != discord.Status.online:
                                    logging.debug(f"BOT: {bot_member.name}")
                                    logging.debug(f"BOT: {bot_member.status}")
                                    logging.debug(f"最終オンライン: {last_online}")
                                    if datetime.utcnow() - last_online > timedelta(minutes=10):
                                        last_notified_str = bot_data.get('last_notification_time')
                                        if last_notified_str is None:
                                            last_notified = datetime.utcnow() - timedelta(minutes=11)
                                            logging.debug(f"最終通知: {last_notified}")
                                        else:
                                            last_notified = datetime.fromisoformat(last_notified_str)
                                            logging.debug(f"最終通知: {last_notified}")

                                        if datetime.utcnow() - last_notified > timedelta(minutes=10):
                                            logging.debug(f"{bot_member.name}がオフラインになって10分が経過しました。")
                                            logging.debug(f"通知チャンネル: {notification_channel}")
                                            if notification_channel is None:
                                                logging.debug("通知チャンネルが見つかりません。")
                                            if notification_channel is not None:
                                                last_channel_notified = datetime.fromisoformat(bot_data.get('last_channel_notification_time', '1970-01-01T00:00:00'))
                                                if datetime.utcnow() - last_channel_notified > timedelta(minutes=10):
                                                    logging.debug(f"通知チャンネル: {notification_channel.name}")
                                                    e = discord.Embed(title='BOTがオフラインになりました。', description=f"{bot_member.name}がオフラインになって10分が経過しました。", color=discord.Color.red())
                                                    last_online_time = datetime.fromisoformat(bot_data['last_online'])
                                                    last_online_timestamp = last_online_time.timestamp()
                                                    e.add_field(name='BOT情報', value=f"ID: {bot_member.id}\n名前: {bot_member.name}\nオフライン時間: <t:{int(last_online_timestamp)}:F> | <t:{int(last_online_timestamp)}:R>")
                                                    await notification_channel.send(embed=e)
                                                    bot_data['last_channel_notification_time'] = datetime.utcnow().isoformat()
                                                    self.save_channel_data(channel_file_path, channel_data)
                                                    logging.debug(f"{bot_member.name}にチャンネル通知を送信しました。")
                                            if user_id is not None:
                                                user = self.bot.get_user(int(user_id))
                                                if user:
                                                    logging.debug(f"ユーザー: {user.name}")
                                                    dm_channel = user.dm_channel or await user.create_dm()
                                                    last_dm_notified = datetime.fromisoformat(bot_data.get('last_dm_notification_time', '1970-01-01T00:00:00'))
                                                    if datetime.utcnow() - last_dm_notified > timedelta(minutes=10):
                                                        e = discord.Embed(title='BOTがオフラインになりました。', description=f"{bot_member.name}がオフラインになって10分が経過しました。", color=discord.Color.red())
                                                        last_online_time = datetime.fromisoformat(bot_data['last_online'])
                                                        last_online_timestamp = last_online_time.timestamp()
                                                        e.add_field(name='BOT情報', value=f"ID: {bot_member.id}\n名前: {bot_member.name}\nオフライン時間: <t:{int(last_online_timestamp)}:F> | <t:{int(last_online_timestamp)}:R>")
                                                        await dm_channel.send(embed=e)
                                                        bot_data['last_dm_notification_time'] = datetime.utcnow().isoformat()
                                                        self.save_data(file_path, data_dict, user_id)
                                                        logging.debug(f"{bot_member.name}にDMを送信しました。")
                                                else:
                                                    logging.error("ユーザーが見つかりません。")
                                            bot_data['last_notification_time'] = datetime.utcnow().isoformat()
                                            bot_data['last_channel_online_notification_time'] == None
                                            bot_data['last_dm_online_notification_time'] == None
                                            bot_data['bots'][0]['last_notification_time'] = datetime.utcnow().isoformat()
                                            bot_data['bots'][0]['last_channel_online_notification_time'] == None
                                            bot_data['bots'][0]['last_dm_online_notification_time'] == None
                                            self.save_data(file_path, data_dict, user_id)
                                            self.save_channel_data(channel_file_path, channel_data)
                                            logging.debug(f"{bot_member.name}に通知を送信済みです。")
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
                                        bot_data['last_channel_online_notification_time'] = datetime.utcnow().isoformat()
                                        if datetime.utcnow() - datetime.fromisoformat(bot_data['last_channel_online_notification_time']) == None:
                                            e = discord.Embed(title='BOTがオンラインになりました。', description=f"{bot_member.name}がオンラインになりました。", color=discord.Color.green())
                                            last_online_time = datetime.fromisoformat(bot_data['last_online'])
                                            last_online_timestamp = last_online_time.timestamp()
                                            e.add_field(name='BOT情報', value=f"ID: {bot_member.id}\n名前: {bot_member.name}\nオンライン時間: <t:{int(last_online_timestamp)}:F> | <t:{int(last_online_timestamp)}:R>")
                                            await notification_channel.send(embed=e)
                                            bot_data['last_channel_online_notification_time'] = datetime.utcnow().isoformat()
                                            self.save_channel_data(channel_file_path, channel_data)
                                    else:
                                        logging.debug("通知チャンネルが見つかりません。")
                                    if user_id is not None:
                                        user = self.bot.get_user(int(user_id))
                                        if user:
                                            bot_data['last_dm_online_notification_time'] = datetime.utcnow().isoformat()
                                            if datetime.utcnow() - datetime.fromisoformat(bot_data['last_dm_online_notification_time']) == None:

                                                dm_channel = user.dm_channel or await user.create_dm()
                                                e = discord.Embed(title='BOTがオンラインになりました。', description=f"{bot_member.name}がオンラインになりました。", color=discord.Color.green())
                                                last_online_time = datetime.fromisoformat(bot_data['last_online'])
                                                last_online_timestamp = last_online_time.timestamp()
                                                e.add_field(name='BOT情報', value=f"ID: {bot_member.id}\n名前: {bot_member.name}\nオンライン時間: <t:{int(last_online_timestamp)}:F> | <t:{int(last_online_timestamp)}:R>")
                                                await dm_channel.send(embed=e)
                                                bot_data['last_dm_online_notification_time'] = datetime.utcnow().isoformat()
                                                self.save_data(file_path, data_dict, user_id)
                                    bot_data['last_online'] = datetime.utcnow().isoformat()
                                    channel_data['bots'][0]['last_online'] = datetime.utcnow().isoformat()
                                    self.save_channel_data(channel_file_path, channel_data)
                                    self.save_data(file_path, data_dict, user_id)
                                    last_notified = bot_data.get('last_notification_time', None)
                                    if last_notified is not None:
                                        bot_data['last_notification_time'] = None
                                        self.save_data(file_path, data_dict, user_id)
                                        self.save_channel_data(channel_file_path, channel_data)
                                        logging.debug(f"{bot_member.name}のオンライン時間と通知時間を更新しました。")
                                    else:
                                        logging.debug(f"{bot_member.name}のオンライン時間を更新しました。")
                            else:
                                logging.debug(f"BOT: {bot_data['name']} が見つかりません。")
                    else:
                        pass
        except Exception as e:
            logging.error(f"BOTのヘルスチェック中にエラーが発生しました: {e}")
            pass

async def setup(bot):
    await bot.add_cog(HealthCheckGroup(bot))
