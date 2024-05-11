import logging
import traceback
import discord

async def send_error_message(ctx, exc):
    error_message = f"エラーが発生しました: {str(exc)}"
    logging.error(error_message)
    traceback_details = traceback.format_exc()
    logging.error(f"スタックトレース:\n{traceback_details}")
    await ctx.send(f"{error_message}: {exc}")

