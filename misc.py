import logging

# Konfigurasi logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DEFAULT_HEADERS = {
    'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
    'Accept-Encoding': "gzip, deflate, br, zstd",
    'Content-Type': "application/json",
    'sec-ch-ua-platform': "\"Linux\"",
    'sec-ch-ua': "\"Chromium\";v=\"134\", \"Not:A-Brand\";v=\"24\", \"Brave\";v=\"134\"",
    'sec-ch-ua-mobile': "?0",
    'Sec-GPC': "1",
    'Accept-Language': "en-US,en;q=0.9",
    'Origin': "https://hyperdash.info",
    'Sec-Fetch-Site': "cross-site",
    'Sec-Fetch-Mode': "cors",
    'Sec-Fetch-Dest': "empty",
    'Referer': "https://hyperdash.info/"
}

def get_header(custom_headers: dict = None) -> dict:
    """
    Membuat header HTTP untuk request ke API Hyperliquid.
    
    :param custom_headers: Header tambahan atau override (opsional).
    :return: Dictionary yang berisi header HTTP.
    :example: 
        >>> get_header({'Authorization': 'Bearer token'})
        {'User-Agent': ..., 'Authorization': 'Bearer token', ...}
    """
    headers = DEFAULT_HEADERS.copy()
    if custom_headers:
        headers.update(custom_headers)
    logging.debug("Generated HTTP headers for API request.")
    return headers

def get_json(user_address: str, request_type: str = "clearinghouseState") -> dict:
    """
    Membuat payload JSON untuk request ke API Hyperliquid.
    
    :param user_address: Alamat pengguna (misalnya, "0x5d2f4460ac3514ada79f5d9838916e508ab39bb7").
    :param request_type: Tipe request API (default: "clearinghouseState").
    :return: Dictionary yang berisi payload JSON.
    :raises ValueError: Jika user_address tidak valid.
    :example:
        >>> get_json("0x1234", "metaAndAssetCtxs")
        {'type': 'metaAndAssetCtxs', 'user': '0x1234'}
    """
    if not isinstance(user_address, str) or not user_address.startswith("0x"):
        logging.error(f"Invalid user_address format: {user_address}")
        raise ValueError("user_address harus berupa string dan diawali '0x'.")
    
    payload = {
        "type": request_type,
        "user": user_address
    }
    logging.debug(f"Generated JSON payload: {payload}")
    return payload