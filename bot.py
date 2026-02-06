import os
import subprocess
import asyncio
import logging
import uuid # Для генерации коротких ID
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import web

logging.basicConfig(level=logging.INFO)
API_TOKEN = '8275951235:AAEsmowSWbpdYnUgnlE3I7Aj0_CZzjhqan8'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Временное хранилище для file_id (чтобы не превышать лимит 64 байта в кнопках)
file_cache = {}

async def convert_video(input_path, output_path, start_time="00:00:00"):
    command = [
        'ffmpeg', '-ss', start_time, '-i', input_path,
        '-vcodec', 'libvpx-vp9',
        '-vf', 'scale=512:512:force_original_aspect_ratio=decrease,pad=512:512:(ow-iw)/2:(oh-ih)/2:color=black@0',
        '-r', '30', '-t', '3', '-an', '-b:v', '256k', '-y', output_path
    ]
    process = await asyncio.create_subprocess_exec(*command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    await process.communicate()
    return os.path.exists(output_path)

@dp.message(Command("start"))
async def cmd_start(msg: types.Message):
    await msg.answer("🎥 Привет! Пришли мне видео, и я сделаю из него стикер!")

@dp.message(F.video | F.animation | F.document)
async def handle_media(msg: types.Message):
    # Получаем file_id
    if msg.video: file_id = msg.video.file_id
    elif msg.animation: file_id = msg.animation.file_id
    elif msg.document: file_id = msg.document.file_id
    else: return

    # Создаем уникальный короткий ключ
    short_id = str(uuid.uuid4())[:8]
    file_cache[short_id] = file_id
    
    # Кнопки теперь содержат короткий short_id вместо длинного file_id
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Начало (0-3 сек)", callback_data=f"cut_0_{short_id}")],
        [InlineKeyboardButton(text="Середина (5-8 сек)", callback_data=f"cut_5_{short_id}")],
        [InlineKeyboardButton(text="Конец (10-13 сек)", callback_data=f"cut_10_{short_id}")]
    ])
    
    await msg.answer("Видео получено! Какую часть превратить в стикер?", reply_markup=kb)

@dp.callback_query(F.data.startswith("cut_"))
async def process_cut(callback: types.CallbackQuery):
    _, start_sec, short_id = callback.data.split("_")
    
    # Достаем реальный file_id из кэша
    file_id = file_cache.get(short_id)
    if not file_id:
        await callback.answer("❌ Ошибка: Данные устарели. Пришлите видео снова.", show_alert=True)
        return

    start_time = f"00:00:{start_sec.zfill(2)}"
    await callback.message.edit_text(f"⏳ Начинаю нарезку с {start_sec}-й секунды...")
    
    file = await bot.get_file(file_id)
    in_file, out_file = f"in_{short_id}.mp4", f"out_{short_id}.webm"
    
    try:
        await bot.download_file(file.file_path, in_file)
        if await convert_video(in_file, out_file, start_time):
            await callback.message.answer_document(FSInputFile(out_file), caption="✅ Готово для @Stickers!")
        else:
            await callback.message.answer("❌ Ошибка при конвертации.")
    except Exception as e:
        await callback.message.answer(f"❌ Произошла ошибка: {e}")
    finally:
        if os.path.exists(in_file): os.remove(in_file)
        if os.path.exists(out_file): os.remove(out_file)
        # Очищаем кэш после использования (опционально)
        file_cache.pop(short_id, None)

# --- ВЕБ-ЗАГЛУШКА ДЛЯ BACK4APP ---
async def handle_health(request):
    return web.Response(text="Bot is running!")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

async def main():
    asyncio.create_task(start_webserver())
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
