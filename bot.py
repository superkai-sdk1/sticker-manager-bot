import os
import subprocess
import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import web

# Логи
logging.basicConfig(level=logging.INFO)
API_TOKEN = '8275951235:AAEsmowSWbpdYnUgnlE3I7Aj0_CZzjhqan8'

# Инициализация
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# --- ФУНКЦИЯ КОНВЕРТАЦИИ ---
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

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def cmd_start(msg: types.Message):
    await msg.answer("🎥 Привет! Я анимированный стикер-менеджер.\nПришли мне видео, и я сделаю из него стикер!")

@dp.message(F.video | F.animation | F.document)
async def handle_media(msg: types.Message):
    file_id = msg.video.file_id if msg.video else (msg.animation.file_id if msg.animation else msg.document.file_id)
    
    # Кнопки выбора фрагмента
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Начало (0-3 сек)", callback_data=f"cut_0_{file_id}")],
        [InlineKeyboardButton(text="Середина (от 5 сек)", callback_data=f"cut_5_{file_id}")],
        [InlineKeyboardButton(text="Конец (от 10 сек)", callback_data=f"cut_10_{file_id}")]
    ])
    
    await msg.answer("Видео получено! Какую часть превратить в стикер?", reply_markup=kb)

@dp.callback_query(F.data.startswith("cut_"))
async def process_cut(callback: types.CallbackQuery):
    _, start_sec, file_id = callback.data.split("_")
    start_time = f"00:00:{start_sec.zfill(2)}"
    
    await callback.message.edit_text("⏳ Обработка началась... Пожалуйста, подождите.")
    
    file = await bot.get_file(file_id)
    in_file, out_file = f"in_{file_id}.mp4", f"out_{file_id}.webm"
    
    await bot.download_file(file.file_path, in_file)
    
    if await convert_video(in_file, out_file, start_time):
        await callback.message.answer_document(FSInputFile(out_file), caption="✅ Готово для @Stickers!")
    else:
        await callback.message.answer("❌ Ошибка при нарезке видео.")
    
    if os.path.exists(in_file): os.remove(in_file)
    if os.path.exists(out_file): os.remove(out_file)
    await callback.answer()

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

# --- ЗАПУСК ---
async def main():
    # Запускаем веб-сервер в фоне
    asyncio.create_task(start_webserver())
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
