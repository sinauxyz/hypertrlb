import pandas as pd
import asyncio
import datetime
import logging
import time
import aiohttp
from misc import get_header, get_json
from message import telegram_send_message, telegram_polling, load_user_addresses, telegram_chat_id
from hyperliquid import get_position, get_leaderboard_base_info, get_markprice
from shared import TARGETED_USER_ADDRESSES, user_addresses_lock

# Konfigurasi logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# Inisialisasi TARGETED_USER_ADDRESSES saat startup
TARGETED_USER_ADDRESSES.extend(load_user_addresses())

ACCOUNT_INFO_URL_TEMPLATE = 'https://hyperdash.info/trader/{}'

def shorten_address(user_address):
    if user_address.startswith("0x") and len(user_address) > 7:
        return user_address[:7]
    return user_address

def modify_data(data) -> pd.DataFrame:
    if not data or 'positions' not in data:
        logging.warning("Invalid data structure received from API.")
        return pd.DataFrame()

    positions = data['positions']
    df = pd.DataFrame(positions)
    
    required_columns = ['coin', 'size', 'leverage', 'entry_price', 'position_value', 'unrealized_pnl']
    missing_cols = [col for col in required_columns if col not in df.columns]
    if missing_cols:
        logging.error(f"Missing required columns: {missing_cols}")
        return pd.DataFrame()

    df.set_index('coin', inplace=True)
    df['estimatedEntrySize'] = df.apply(
        lambda row: round((abs(row['size']) / row['leverage']) * row['entry_price'], 2) 
        if row['leverage'] != 0 else 0, axis=1
    )
    df['estimatedPosition'] = df['size'].apply(lambda x: 'LONG' if x > 0 else 'SHORT')
    df['updateTime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return df[['estimatedPosition', 'leverage', 'estimatedEntrySize', 
              'entry_price', 'position_value', 'unrealized_pnl', 'updateTime']]

previous_symbols = {}
previous_position_results = {}
is_first_runs = {}

async def send_new_position_message(session: aiohttp.ClientSession, symbol, row, user_address):
    short_address = shorten_address(user_address)
    estimated_position = row['estimatedPosition']
    leverage = row['leverage']
    estimated_entry_size = row['estimatedEntrySize']
    entry_price = row['entry_price']
    pnl = row['unrealized_pnl']
    updatetime = row['updateTime']
    profile_url = ACCOUNT_INFO_URL_TEMPLATE.format(user_address)
    pnl_emoji = "🟢" if pnl >= 0 else "🔴"
    message = (
        f"⚠️ [<b>{short_address}</b>]\n"
        f"❇️ <b>New position opened</b>\n\n"
        f"<b>Position:</b> {symbol} {estimated_position} {leverage}X\n\n"
        f"💵 Base currency - USDT\n"
        f"------------------------------\n"
        f"🎯 <b>Entry Price:</b> {entry_price}\n"
        f"💰 <b>Size:</b> {estimated_entry_size}\n"
        f"{pnl_emoji} <b>PnL:</b> {pnl}\n\n"
        f"Last Update:\n"
        f"{updatetime} (UTC+7)\n"
        f"VIEW PROFILE ON HYPERDASH ({profile_url})"
    )
    await telegram_send_message(session, message)

async def send_closed_position_message(session: aiohttp.ClientSession, symbol, row, user_address):
    short_address = shorten_address(user_address)
    estimated_position = row['estimatedPosition']
    leverage = row['leverage']
    updatetime = row['updateTime']
    profile_url = ACCOUNT_INFO_URL_TEMPLATE.format(user_address)
    current_price = await get_markprice(session, symbol)
    message = (
        f"⚠️ [<b>{short_address}</b>]\n"
        f"⛔️ <b>Position closed</b>\n\n"
        f"<b>Position:</b> {symbol} {estimated_position} {leverage}X\n"
        f"💵 <b>Current Price:</b> {current_price} USDT\n\n"
        f"Last Update:\n"
        f"{updatetime} (UTC+7)\n"
        f"VIEW PROFILE ON HYPERDASH ({profile_url})"
    )
    await telegram_send_message(session, message)

async def send_current_positions(session: aiohttp.ClientSession, position_result, user_address):
    short_address = shorten_address(user_address)
    if position_result.empty:
        await telegram_send_message(session, f"⚠️ [<b>{short_address}</b>]\n💎 <b>No positions found</b>")
    else:
        message = f"⚠️ [<b>{short_address}</b>]\n💎 <b>Current positions:</b>\n\n"
        for symbol, row in position_result.iterrows():
            pnl_emoji = "🟢" if row['unrealized_pnl'] >= 0 else "🔴"
            message += (
                f"<b>{symbol}</b> {row['estimatedPosition']} {row['leverage']}X\n"
                f"🎯 <b>Entry:</b> {row['entry_price']}\n"
                f"💰 <b>Size:</b> {row['estimatedEntrySize']}\n"
                f"{pnl_emoji} <b>PnL:</b> {row['unrealized_pnl']}\n"
                f"------------------------------\n"
            )
        message += f"<b>Last Update:</b>\n{row['updateTime']} (UTC+7)\n"
        message += f"<a href='{ACCOUNT_INFO_URL_TEMPLATE.format(user_address)}'><b>VIEW PROFILE ON HYPERDASH</b></a>"
        await telegram_send_message(session, message)

async def monitor_positions():
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                start_time = time.time()
                
                with user_addresses_lock:
                    current_addresses = TARGETED_USER_ADDRESSES.copy()

                for address in current_addresses:
                    if address not in is_first_runs:
                        is_first_runs[address] = True

                tasks = []
                for user_address in current_addresses:
                    leaderboard_info = await get_leaderboard_base_info(session, user_address)

                    if isinstance(leaderboard_info, str):
                        logging.error(f"Error untuk alamat {user_address}: {leaderboard_info}")
                        await telegram_send_message(session, f"Error untuk alamat {user_address}: {leaderboard_info}", telegram_chat_id)
                        continue

                    position_result = modify_data(leaderboard_info)

                    new_symbols = position_result.index.difference(previous_symbols.get(user_address, pd.Index([])))
                    if not is_first_runs[user_address] and not new_symbols.empty:
                        for symbol in new_symbols:
                            tasks.append(send_new_position_message(session, symbol, position_result.loc[symbol], user_address))

                    closed_symbols = previous_symbols.get(user_address, pd.Index([])).difference(position_result.index)
                    if not is_first_runs[user_address] and not closed_symbols.empty:
                        for symbol in closed_symbols:
                            if symbol in previous_position_results.get(user_address, pd.DataFrame()).index:
                                tasks.append(send_closed_position_message(session, symbol, previous_position_results[user_address].loc[symbol], user_address))

                    if is_first_runs[user_address]:
                        tasks.append(send_current_positions(session, position_result, user_address))

                    previous_position_results[user_address] = position_result.copy()
                    previous_symbols[user_address] = position_result.index.copy()
                    is_first_runs[user_address] = False

                if tasks:
                    await asyncio.gather(*tasks)

                ping_time = (time.time() - start_time) * 1000
                current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logging.info(f"✅ Bot is still running | Time: {current_time} | Ping: {ping_time:.2f}ms")
                
                await asyncio.sleep(60)
            
            except Exception as e:
                logging.error(f"Global error occurred: {e}")
                error_message = f"Global error occurred:\n{e}\n\nRetrying after 60s"
                await telegram_send_message(session, error_message, telegram_chat_id)
                await asyncio.sleep(60)

async def main():
    await asyncio.gather(
        telegram_polling(),
        monitor_positions()
    )

if __name__ == "__main__":
    asyncio.run(main())