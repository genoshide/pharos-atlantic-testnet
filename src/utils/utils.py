import asyncio, requests
import base64
import json
import os
import random
import time
from datetime import datetime

import aiofiles
import jwt as pyjwt
from colorama import Fore, Style

lock = asyncio.Lock()
TOKENS_FILE = "tokens.json"

def _Geoshide_banner():
    banner = r"""
  ________                           .__    .__    .___      
 /  _____/  ____   ____   ____  _____|  |__ |__| __| _/____  
/   \  ____/ __ \ /    \ /  _ \/  ___/  |  \|  |/ __ |/ __ \ 
\    \_\  \  ___/|   |  (  <_> )___ \|   Y  \  / /_/ \  ___/ 
 \______  /\___  >___|  /\____/____  >___|  /__\____ |\___  >
        \/     \/     \/           \/     \/        \/    \/ 
"""
    print(Fore.LIGHTGREEN_EX + Style.BRIGHT + banner + Style.RESET_ALL)
    print(f"{Fore.GREEN}==================[ {Style.BRIGHT}Genoshide{Style.NORMAL} ]=================={Style.RESET_ALL}")
    print(f"{Fore.WHITE}>> Pharos Network :: Testnet Automation <<{Style.RESET_ALL}")
    print(f"{Fore.WHITE}>> Status: Online | Testnet: Atlantic <<{Style.RESET_ALL}\n")
    print(Fore.GREEN + "------------------------------------------------------------" + Style.RESET_ALL)

def _is_array(obj):
    try:
        return isinstance(obj, list) and len(obj) > 0 or isinstance(json.loads(obj), list)
    except Exception:
        return False

def sleep(seconds=None):
    if isinstance(seconds, (int, float)):
        time.sleep(seconds)
        return

    delay = random.randint(*(seconds if isinstance(seconds, list) else [1, 5]))
    time.sleep(delay)

def _is_token_expired(token):
    def current_time_str():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not token or token.count(".") != 2:
        return {"isExpired": True, "expirationDate": current_time_str()}

    try:
        payload = pyjwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp")
        if not isinstance(exp, (int, float)):
            return {"isExpired": True, "expirationDate": current_time_str()}

        now = time.time()
        is_expired = now > exp
        expiration = datetime.fromtimestamp(exp).strftime("%Y-%m-%d %H:%M:%S")
        return {"isExpired": is_expired, "expirationDate": expiration}

    except Exception as e:
        print(f"Token check error: {e}")
        return {"isExpired": True, "expirationDate": current_time_str()}
    
def _load_data(file_path):
    try:
        with open(file_path, "r", encoding='utf-8') as f:
            lines = [line for line in f.read().replace('\r', '').split('\n') if line]
        if not lines:
            print(f"No data found in {file_path}", "warning")
        return lines
    except Exception as e:
        print(f"Error loading file {file_path}: {e}", "error")
        return []
        
async def _save_json(identifier, value, filename=TOKENS_FILE):
    async with lock:
        data = {}
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        data[identifier] = value
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

def _load_token_data(identifier, filename=TOKENS_FILE):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f).get(identifier)
    return None

def load_data(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line for line in f.read().replace("\r", "").split("\n") if line]
        if not lines:
            print(f"No data found in {file_path}")
        return lines
    except Exception as e:
        print(f"Error loading file {file_path}: {e}")
        return []

