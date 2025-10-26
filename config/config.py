import json, os
from dotenv import load_dotenv
from pathlib import Path

from src.utils.utils import _is_array

load_dotenv()

ABI_DIR = Path(__file__).resolve().parent.parent / "abi"
ERC20_ABI = json.load(open(ABI_DIR / "uni_erc20_abi.json", "r", encoding="utf-8"))

settings = {
    "TIME_SLEEP": int(os.getenv("TIME_SLEEP", 8)),
    "MAX_THREADS": int(os.getenv("MAX_THREADS", 10)),
    "MAX_THREADS_NO_PROXY": int(os.getenv("MAX_THREADS_NO_PROXY", 10)),
    "NUMBER_SEND": int(os.getenv("NUMBER_SEND", 10)),

    "SKIP_TASKS": json.loads(os.getenv("SKIP_TASKS", "[]").replace("'", '"')),
    "TASKS_ID": json.loads(os.getenv("TASKS_ID", "[]").replace("'", '"')),
    "ENABLE_DEBUG": os.getenv("ENABLE_DEBUG", "false").lower() == "true",
    "AUTO_CHECKIN": os.getenv("AUTO_CHECKIN", "false").lower() == "true",
    "AUTO_QUESTS": os.getenv("AUTO_QUESTS", "false").lower() == "true",
    "USE_PROXY": os.getenv("USE_PROXY", "false").lower() == "true",
    "AUTO_FAUCET": os.getenv("AUTO_FAUCET", "false").lower() == "true",
    "AUTO_SEND": os.getenv("AUTO_SEND", "false").lower() == "true",

    "BASE_URL": os.getenv("BASE_URL", None),
    "REF_CODE": os.getenv("REF_CODE", "13GJn8jQN7Hln7WJ"),
    "TYPE_CAPTCHA": os.getenv("TYPE_CAPTCHA", None),
    "API_KEY_CAPMONSTER": os.getenv("API_KEY_CAPMONSTER", None),
    "API_KEY_2CAPTCHA": os.getenv("API_KEY_2CAPTCHA", None),
    "API_KEY_ANTI_CAPTCHA": os.getenv("API_KEY_ANTI_CAPTCHA", None),
    "CAPTCHA_URL": os.getenv("CAPTCHA_URL", None),
    "WEBSITE_KEY": os.getenv("WEBSITE_KEY", None),
    "CHAIN_ID": os.getenv("CHAIN_ID", "688688"),
    "RPC_URL": os.getenv("RPC_URL","https://testnet.dplabs-internal.com",),
    "EXPLORER_URL": os.getenv("EXPLORER_URL", "https://atlantic.pharosscan.xyz/"),    
    "DELAY_BETWEEN_REQUESTS": (json.loads(os.getenv("DELAY_BETWEEN_REQUESTS")) if _is_array(os.getenv("DELAY_BETWEEN_REQUESTS")) else [1, 5]),
    "DELAY_START_BOT": (json.loads(os.getenv("DELAY_START_BOT")) if _is_array(os.getenv("DELAY_START_BOT")) else [1, 15]),
    "DELAY_TASK": (json.loads(os.getenv("DELAY_TASK")) if _is_array(os.getenv("DELAY_TASK")) else [10, 15]),
    "AMOUNT_SEND": (json.loads(os.getenv("AMOUNT_SEND")) if _is_array(os.getenv("AMOUNT_SEND")) else [0.1, 0.2]),
}
