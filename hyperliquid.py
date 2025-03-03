import aiohttp
import json
import logging
from misc import get_header, get_json

logging.basicConfig(level=logging.INFO)

API_URL = "https://api.hyperliquid.xyz/info"

def _safe_float(value, default=0.0) -> float:
    try:
        return float(value or default) if value is not None else default
    except (ValueError, TypeError):
        return default

async def get_markprice(session: aiohttp.ClientSession, symbol: str) -> str:
    """
    Mendapatkan harga mark (mark price) dari Hyperliquid API secara asinkronus.
    
    :param session: aiohttp ClientSession untuk request.
    :param symbol: Simbol trading (misalnya, BTC, ETH).
    :return: Harga mark atau pesan kesalahan jika gagal.
    """
    payload = {"type": "metaAndAssetCtxs"}
    
    try:
        logging.debug(f"Fetching mark price for {symbol}")
        async with session.post(API_URL, data=json.dumps(payload), headers=get_header()) as response:
            response.raise_for_status()
            data = await response.json()

            for asset in data[1]:
                if asset.get('name') == symbol and 'markPx' in asset:
                    logging.debug(f"Mark price for {symbol}: {asset['markPx']}")
                    return asset['markPx']
        
        logging.warning(f"Symbol {symbol} not found")
        return f"Symbol {symbol} not found in the response."
    except aiohttp.ClientError as e:
        logging.error(f"Error fetching mark price for {symbol}: {e}")
        return f"Error occurred while fetching mark price: {e}"

async def get_position(session: aiohttp.ClientSession, user_address: str) -> list | str:
    """
    Mendapatkan posisi trading dari Hyperliquid API secara asinkronus.
    
    :param session: aiohttp ClientSession untuk request.
    :param user_address: Alamat pengguna.
    :return: List posisi trading atau pesan kesalahan jika gagal.
    """
    payload = get_json(user_address)
    
    try:
        logging.debug(f"Fetching positions for {user_address}")
        async with session.post(API_URL, data=json.dumps(payload), headers=get_header()) as response:
            response.raise_for_status()
            data = await response.json()

            positions = data.get("assetPositions", [])
            position_data = []

            for position in positions:
                pos_info = position.get("position", {})
                position_data.append({
                    "coin": pos_info.get("coin", ""),
                    "size": _safe_float(pos_info.get("szi")),
                    "entry_price": _safe_float(pos_info.get("entryPx")),
                    "position_value": _safe_float(pos_info.get("positionValue")),
                    "unrealized_pnl": _safe_float(pos_info.get("unrealizedPnl")),
                    "leverage": _safe_float(pos_info.get("leverage", {}).get("value")),
                    "margin_used": _safe_float(pos_info.get("marginUsed")),
                    "liquidation_price": _safe_float(pos_info.get("liquidationPx")),
                    "max_leverage": _safe_float(pos_info.get("maxLeverage")),
                    "cum_funding": pos_info.get("cumFunding", {})
                })
        
        logging.debug(f"Found {len(position_data)} positions for {user_address}")
        return position_data
    except aiohttp.ClientError as e:
        logging.error(f"Error fetching positions for {user_address}: {e}")
        return f"Error occurred while fetching positions: {e}"

async def get_leaderboard_base_info(session: aiohttp.ClientSession, user_address: str) -> dict | str:
    """
    Mendapatkan informasi dasar tentang trader dari Hyperliquid API secara asinkronus.
    
    :param session: aiohttp ClientSession untuk request.
    :param user_address: Alamat pengguna (misalnya, "0x5d2f4460ac3514ada79f5d9838916e508ab39bb7").
    :return: Dict informasi trader atau pesan kesalahan jika gagal.
    """
    payload = get_json(user_address)  # Payload dari misc.py
    
    try:
        logging.info(f"Fetching leaderboard data for {user_address}")
        async with session.post(API_URL, data=json.dumps(payload), headers=get_header()) as response:
            # Pastikan status response OK sebelum membaca JSON
            if response.status != 200:
                error_text = await response.text()
                raise aiohttp.ClientResponseError(
                    response.request_info,
                    response.history,
                    status=response.status,
                    message=f"Unexpected status: {error_text}"
                )
            
            data = await response.json()
            logging.debug(f"Raw API response for {user_address}: {data}")

            # Ekstrak data dengan fallback jika kunci tidak ada
            margin_summary = data.get("marginSummary", {})
            asset_positions = data.get("assetPositions", [])

            leaderboard_info = {
                "user_address": user_address,
                "profile_url": f"https://hyperdash.info/trader/{user_address}",
                "account_value": _safe_float(margin_summary.get("accountValue")),
                "total_notional_position": _safe_float(margin_summary.get("totalNtlPos")),
                "total_raw_usd": _safe_float(margin_summary.get("totalRawUsd")),
                "total_margin_used": _safe_float(margin_summary.get("totalMarginUsed")),
                "withdrawable": _safe_float(data.get("withdrawable")),
                "positions": []
            }

            # Proses posisi trading
            for position in asset_positions:
                pos_info = position.get("position", {})
                position_data = {
                    "coin": pos_info.get("coin", ""),
                    "size": _safe_float(pos_info.get("szi")),
                    "entry_price": _safe_float(pos_info.get("entryPx")),
                    "position_value": _safe_float(pos_info.get("positionValue")),
                    "unrealized_pnl": _safe_float(pos_info.get("unrealizedPnl")),
                    "leverage": _safe_float(pos_info.get("leverage", {}).get("value")),
                    "margin_used": _safe_float(pos_info.get("marginUsed")),
                    "liquidation_price": _safe_float(pos_info.get("liquidationPx")),
                    "max_leverage": _safe_float(pos_info.get("maxLeverage")),
                    "cum_funding": pos_info.get("cumFunding", {})
                }
                leaderboard_info["positions"].append(position_data)

            logging.info(f"Successfully processed leaderboard info for {user_address}")
            return leaderboard_info

    except aiohttp.ClientResponseError as e:
        logging.error(f"HTTP error fetching leaderboard info for {user_address}: {e}")
        return f"Error occurred while fetching leaderboard info: {e}"
    except aiohttp.ClientError as e:
        logging.error(f"Network error fetching leaderboard info for {user_address}: {e}")
        return f"Error occurred while fetching leaderboard info: {e}"
    except Exception as e:
        logging.error(f"Unexpected error fetching leaderboard info for {user_address}: {e}")
        return f"Error occurred while fetching leaderboard info: {e}"