import aiohttp
import asyncio
import configparser
import logging
import json
from shared import TARGETED_USER_ADDRESSES, user_addresses_lock

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Membaca konfigurasi
config = configparser.ConfigParser()
if not config.read('config.ini'):
    logging.error("File config.ini tidak ditemukan.")
    raise FileNotFoundError("File config.ini tidak ditemukan.")

try:
    telegram_bot_token = config['telegram']['bottoken']
    telegram_chat_id = config['telegram']['chatid']
    admins = [int(admin.strip()) for admin in config['telegram']['admins'].split(',')]
except KeyError as e:
    logging.error(f"Konfigurasi tidak lengkap di config.ini: {e}")
    raise Exception(f"Pastikan file config.ini memiliki bagian [telegram] dengan 'bottoken', 'chatid', dan 'admins'.")
except ValueError as e:
    logging.error(f"Format 'admins' di config.ini tidak valid: {e}")
    raise Exception("Daftar 'admins' harus berupa angka yang dipisahkan koma (contoh: -123456789,123456).")

if not telegram_chat_id or not telegram_chat_id.lstrip('-').isdigit():
    logging.error(f"telegram_chat_id tidak valid: {telegram_chat_id}")
    raise ValueError("chatid di config.ini harus berupa angka (bisa negatif) dan tidak boleh kosong.")
telegram_chat_id = str(telegram_chat_id)

async def telegram_send_message(session: aiohttp.ClientSession, message: str, chat_id: str = telegram_chat_id) -> bool:
    """
    Mengirim pesan ke Telegram secara asinkronus.
    
    :param session: aiohttp ClientSession untuk request.
    :param message: Pesan yang akan dikirim.
    :param chat_id: ID chat tujuan (default dari config).
    :return: True jika berhasil, False jika gagal.
    """
    if not chat_id or not chat_id.lstrip('-').isdigit():
        logging.error(f"chat_id tidak valid: {chat_id}")
        return False

    api_url = f"https://api.telegram.org/bot{telegram_bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'html',
        'disable_web_page_preview': True
    }
    
    try:
        logging.debug(f"Mengirim pesan ke chat {chat_id}: {message[:50]}...")
        async with session.post(api_url, json=payload) as response:
            response.raise_for_status()
            logging.info(f"Pesan berhasil dikirim ke chat {chat_id}.")
            return True
    except aiohttp.ClientError as e:
        logging.error(f"Gagal mengirim pesan ke chat {chat_id}: {e}")
        return False

def load_user_addresses() -> list:
    """
    Memuat daftar user_addresses dari file JSON (synchronous).
    
    :return: List alamat pengguna.
    """
    try:
        with open('user_addresses.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

async def update_user_addresses(user_address: str) -> bool:
    """
    Menambahkan user_address ke user_addresses.json dan memori.
    
    :param user_address: Alamat pengguna untuk ditambahkan.
    :return: True jika berhasil, False jika gagal atau sudah ada.
    """
    with user_addresses_lock:
        user_addresses = TARGETED_USER_ADDRESSES.copy()

        if user_address in user_addresses:
            return False

        if not (isinstance(user_address, str) and user_address.startswith("0x") and len(user_address) == 42):
            logging.warning(f"Alamat tidak valid: {user_address}")
            return False

        user_addresses.append(user_address)
        try:
            with open('user_addresses.json', 'w') as f:
                json.dump(user_addresses, f, indent=2)
            TARGETED_USER_ADDRESSES[:] = user_addresses
            logging.info(f"Berhasil menambahkan {user_address} ke user_addresses.json")
            return True
        except IOError as e:
            logging.error(f"Gagal memperbarui user_addresses.json: {e}")
            return False

async def remove_user_address(index: int) -> bool:
    """
    Menghapus user_address berdasarkan nomor urutan dari file dan memori.
    
    :param index: Nomor urutan alamat (0-based).
    :return: True jika berhasil, False jika gagal atau indeks tidak valid.
    """
    with user_addresses_lock:
        user_addresses = TARGETED_USER_ADDRESSES.copy()

        if not isinstance(index, int) or index < 0 or index >= len(user_addresses):
            logging.warning(f"Indeks tidak valid: {index}")
            return False

        removed_address = user_addresses.pop(index)
        try:
            with open('user_addresses.json', 'w') as f:
                json.dump(user_addresses, f, indent=2)
            TARGETED_USER_ADDRESSES[:] = user_addresses
            logging.info(f"Berhasil menghapus {removed_address} dari user_addresses.json")
            return True
        except IOError as e:
            logging.error(f"Gagal memperbarui user_addresses.json: {e}")
            return False

async def process_telegram_updates(session: aiohttp.ClientSession, offset: int = None):
    """
    Memproses pesan masuk dari Telegram secara asinkronus.
    
    :param session: aiohttp ClientSession untuk request.
    :param offset: Offset untuk getUpdates (opsional).
    :return: Offset baru untuk update berikutnya.
    """
    api_url = f"https://api.telegram.org/bot{telegram_bot_token}/getUpdates"
    params = {'timeout': 60, 'offset': offset} if offset else {'timeout': 60}
    
    try:
        async with session.get(api_url, params=params) as response:
            response.raise_for_status()
            data = await response.json()

            if not data.get('ok') or not data.get('result'):
                return offset

            for update in data['result']:
                update_id = update['update_id']
                message = update.get('message', {})
                chat_id = message.get('chat', {}).get('id')
                text = message.get('text', '')

                if chat_id not in admins:
                    await telegram_send_message(session, "Anda tidak memiliki izin untuk menggunakan perintah ini.", str(chat_id))
                    continue

                if text.startswith('/add'):
                    parts = text.split(maxsplit=1)
                    if len(parts) < 2:
                        await telegram_send_message(session, "Format salah. Gunakan: /add <user_address>", str(chat_id))
                        continue
                    user_address = parts[1].strip()
                    if await update_user_addresses(user_address):
                        await telegram_send_message(session, f"Berhasil menambahkan {user_address}", str(chat_id))
                    else:
                        await telegram_send_message(session, f"Gagal menambahkan {user_address}. Alamat tidak valid atau sudah ada.", str(chat_id))

                elif text == '/list':
                    with user_addresses_lock:
                        user_addresses = TARGETED_USER_ADDRESSES.copy()
                    if not user_addresses:
                        await telegram_send_message(session, "Daftar user_address kosong.", str(chat_id))
                    else:
                        message = "Daftar user_address:\n"
                        for i, addr in enumerate(user_addresses):
                            message += f"{i}. {addr}\n"
                        await telegram_send_message(session, message, str(chat_id))

                elif text.startswith('/remove'):
                    parts = text.split(maxsplit=1)
                    if len(parts) < 2 or not parts[1].isdigit():
                        await telegram_send_message(session, "Format salah. Gunakan: /remove <nomor>", str(chat_id))
                        continue
                    index = int(parts[1])
                    if await remove_user_address(index):
                        await telegram_send_message(session, f"Berhasil menghapus alamat pada nomor {index}", str(chat_id))
                    else:
                        await telegram_send_message(session, f"Gagal menghapus. Nomor {index} tidak valid.", str(chat_id))

            return update_id + 1

    except aiohttp.ClientError as e:
        logging.error(f"Gagal memproses update Telegram: {e}")
        return offset

async def telegram_polling():
    """
    Tugas asinkronus untuk polling Telegram.
    """
    async with aiohttp.ClientSession() as session:
        offset = None
        while True:
            try:
                offset = await process_telegram_updates(session, offset)
                await asyncio.sleep(1)  # Polling setiap detik
            except Exception as e:
                logging.error(f"Error di Telegram polling: {e}")
                await asyncio.sleep(10)  # Retry setelah jeda jika error