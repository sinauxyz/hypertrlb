# shared.py
import threading

# Variabel global untuk caching user_addresses
TARGETED_USER_ADDRESSES = []
user_addresses_lock = threading.Lock()