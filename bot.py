import os
import subprocess
import asyncio
import logging
import socket
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from aiogram.client.session.aiohttp import AiohttpSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = '8275951235:AAEsmowSWbpdYnUgnlE3I7Aj0_CZzjhqan8'

async def convert_video(input_path, output_path):
    # Стандарт Telegram: VP9, 512x512, 30fps, макс 3 сек, без звука
    command = [
        'ffmpeg', '-i', input_path,
        '-vcodec', 'libvpx-vp9',
        '-vf', 'scale=512:512:force_original_aspect_ratio=decrease,pad=512:512:(ow-iw)/2:(oh-ih)/2:color=black@0',
        '-r', '30', '-t', '3', '-an', '-b:v', '256k',
        '-y', output_path
    ]
    process = await asyncio.create_subprocess_exec(*command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    await process.communicate()
    return os.path.exists(output_path)

dp = Dispatcher()

@dp.message(Command("start"))
async def start_handler(msg: types.Message):
    await msg.answer("✅ Бот активен на Koyeb! Присылай видео.")

@dp.message(F.video | F.document | F.animation)
async def handle_video(msg: types.Message, bot: Bot):
    file_id = msg.video.file_id if msg.video else (msg.animation.file_id if msg.animation else msg.document.file_id)
    
    status_msg = await msg.answer("⏳ Конвертация...")
    input_file = f"in_{file_id}.mp4"
    output_file = f"out_{file_id}.webm"
    
    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, input_file)
        
        if await convert_video(input_file, output_file):
            await msg.reply_document(FSInputFile(output_file), caption="Готово для @Stickers")
        else:
            await msg.answer("❌ Ошибка FFmpeg")
    except Exception as e:
        await msg.answer(f"❌ Ошибка: {e}")
    finally:
        for f in [input_file, output_file]:
            if os.path.exists(f): os.remove(f)
        await status_msg.delete()

async def main():
    # На Koyeb обычно не нужен принудительный IPv4, но оставим для надежности
    session = AiohttpSession(connector=aiohttp.TCPConnector(family=socket.AF_INET))
    bot = Bot(token=API_TOKEN, session=session)
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await session.close()

if __name__ == '__main__':
    asyncio.run(main())
