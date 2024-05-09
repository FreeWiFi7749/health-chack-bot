import discord
from discord.ext import tasks
from discord import app_commands
from discord.app_commands import Group, command
from discord.ext.commands import GroupCog

import json
import logging
import os
from datetime import datetime, timedelta

class HealthCheckGroup(GroupCog, group_name='hc', group_description='Health check commands for bots'):
    def __init__(self, bot):
        self.bot = bot
        self.check_bots.start()

    def cog_unload(self):
        self.check_bots.cancel()

    async def bot_list_autocomplete(self, interaction: discord.Interaction, current: str):
        your_bots = self.load_data(f'data/hc/{interaction.user.id}/list.json')
        choices = []
        for bot in your_bots:
            if current in bot['name']:
                choices.append(app_commands.OptionChoice(name=bot['name'], value=bot['id']))
                logging.debug(f"{bot['name']}: {bot['id']}")
        logging.debug(choices)
        return choices
    
    async def bot_list_autocomplete(self, interaction: discord.Interaction, current: str):
        server_bots = [member for member in interaction.guild.members if member.bot]
        choices = []
        for bot in server_bots:
            if current in bot.name:
                choices.append(app_commands.OptionChoice(name=bot.name, value=bot.id))
                logging.debug(f"{bot.name}: {bot.id}")
        logging.debug(choices)
        return choices

    @command(name='add', description='BOTを監視リストに追加します。')
    @app_commands.option(name='bot', description='BOTを選択してください。', type=app_commands.OptionType.USER, required=True, autocomplete=bot_list_autocomplete)
    async def add_bot(self, interaction, bot: discord.User):
        if not bot.bot:
            await interaction.response.send_message("指定されたユーザーはBOTではありません。")
            return
        directory = f'data/hc/{interaction.user.id}'
        os.makedirs(directory, exist_ok=True)
        file_path = f'{directory}/list.json'
        data = self.load_data(file_path)
        data.append({'name': bot.name, 'id': bot.id, 'last_online': datetime.utcnow().isoformat()})
        self.save_data(file_path, data)
        await interaction.response.send_message(f"{bot.name}を監視リストに追加しました。")

    @command(name='list', description='あなたが登録しているBOTのリストを表示します。')
    async def list_bots(self, interaction):
        file_path = f'data/hc/{interaction.user.id}/list.json'
        data = self.load_data(file_path)
        bots = [self.bot.get_user(bot['id']) for bot in data]
        e = discord.Embed(title='登録されているBOT', description=f'{bots.status.value}, '.join(bots))
        e.set_footer(text=f"{len(bots)}個のBOTが登録されています。")
        await interaction.response.send_message(embed=e)

    @command(name='rm', description='あなたが登録しているBOTをリストから削除します。')
    @app_commands.option(name='bot', description='Bot to remove', type=app_commands.OptionType.INTEGER, required=True, autocomplete=bot_list_autocomplete)
    async def remove_bot(self, interaction, bot: int):
        file_path = f'data/hc/{interaction.user.id}/list.json'
        data = self.load_data(file_path)
        data = [bot for bot in data if bot['id'] != bot]
        self.save_data(file_path, data)
        await interaction.response.send_message("指定されたBOTをリストから削除しました。")

    def save_data(self, file_path, data):
        with open(file_path, 'w') as file:
            if file_path is not None:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
            json.dump(data, file)

    def load_data(self, file_path):
        if os.path.exists(file_path):
            with open(file_path, 'r') as file:
                return json.load(file)
        return []

    @tasks.loop(minutes=1)
    async def check_bots(self):
        for guild in self.bot.guilds:
            for member in guild.members:
                if member.bot:
                    file_path = f'data/hc/{member.id}/list.json'
                    data = self.load_data(file_path)
                    for bot in data:
                        bot_user = self.bot.get_user(bot['id'])
                        if bot_user.status != discord.Status.online:
                            last_online = datetime.fromisoformat(bot['last_online'])
                            if datetime.utcnow() - last_online > timedelta(minutes=10):
                                author = self.bot.get_user(member.id)
                                e = discord.Embed(title='BOTがオフラインになりました。', description=f"{bot_user.name}がオフラインになって10分が経過しました。", color=discord.Color.red())
                                e.add_field(name='BOT情報', value=f"ID: {bot_user.id}\n名前: {bot_user.name}\nオフライン時間: {last_online.strftime('%Y-%m-%d %H:%M:%S')}")
                                await author.send(embed=e)
                            else:
                                bot['last_online'] = datetime.utcnow().isoformat()
                    self.save_data(file_path, data)

async def setup(bot):
    await bot.add_cog(HealthCheckGroup(bot))

