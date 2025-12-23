import asyncio, json, os, random, sys, aiohttp, requests
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime
from functools import partial
from pathlib import Path

from eth_account import Account
from eth_account.messages import encode_defunct

from config.config import settings
from config.userAgents import _gen_ua
from src.utils import constants as _cons
from src.modules import onchain_tasks as _intr
from src.modules import token_utils as _gen
from src.modules.make_requests import _request
from src.utils import utils as _initUtils
from src.utils.logger import logger
from src.modules import captcha_solver

if sys.platform == "win32":
    try:
        import winloop
        winloop.install()
    except ImportError:
        pass
else:
    try:
        import uvloop
        uvloop.install()
    except ImportError:
        pass

class PharosClient:
    def __init__(self, account_data, account_index, proxy=None):
        self.account_index = account_index
        self.get_key = account_data["privateKey"]
        self.address = account_data["address"]
        self.wallet = Account.from_key(self.get_key)
        self.proxy = proxy
        self.proxy_ip = None
        self.token = None

        self.base_url = settings["BASE_URL"]
        self.provider_url = settings["RPC_URL"]
        
        self.session_name = self.address
        self.log = partial(logger, self)
        self.api_request = partial(_request, self)
        self.headers_main = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
            "Content-Type": "application/json",
            "Origin": "https://testnet.pharosnetwork.xyz",
            "referer": "https://testnet.pharosnetwork.xyz/",
            "Sec-Ch-Ua": '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Cache-Control": "no-cache",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        }
        self.headers = self.headers_main.copy()
        self._initialize_session_user_agent()

    def _initialize_session_user_agent(self):
        try:
            session_ua = self._get_or_create_session_user_agent()
            platform = self._get_platform_from_user_agent(session_ua)
            self.headers.update(
                {
                    "User-Agent": session_ua,
                    "sec-ch-ua-platform": platform,
                    "sec-ch-ua": f'Not)A;Brand";v="99", "{platform.capitalize()} WebView";v="127", "Chromium";v="127',
                }
            )
        except Exception as e:
            self.log(f"Failed to set user agent: {e}", "error")

    def _get_or_create_session_user_agent(self):
        ua_file = Path("ua_session.json")
        try:
            all_uas = json.loads(ua_file.read_text()) if ua_file.exists() else {}
        except (json.JSONDecodeError, IOError):
            all_uas = {}

        if self.session_name in all_uas:
            return all_uas[self.session_name]

        self.log("Generating new user agent...")
        new_ua = _gen_ua()
        all_uas[self.session_name] = new_ua
        try:
            ua_file.write_text(json.dumps(all_uas, indent=2))
        except IOError as e:
            self.log(f"Could not save user agent session file: {e}", "warning")
        return new_ua

    @staticmethod
    def _get_platform_from_user_agent(user_agent):
        if "iPhone" in user_agent or "iPad" in user_agent:
            return "ios"
        if "Android" in user_agent:
            return "android"
        return "Unknown"

    async def _get_valid_auth_token(self, force_new=False):
        token_data = _initUtils._load_token_data(self.session_name)
        token = token_data.get("jwt") if isinstance(token_data, dict) else None

        status = _initUtils._is_token_expired(token)
        self.log(
            f"Access token status: {'Expired' if status['isExpired'] else 'Valid'} | "
            f"Expires: {status['expirationDate']}"
        )

        if token and not force_new and not status["isExpired"]:
            return token

        self.log("Token expired or not found, requesting new token...", "warning")

        message = encode_defunct(text="pharos")
        signed_message = self.wallet.sign_message(message)
        signature = signed_message.signature.hex()

        url = (
            f"{self.base_url}/user/login?address={self.address}"
            f"&signature={signature}&invite_code={settings['REF_CODE']}"
        )
        login_res = await self.api_request(url, "post", None, {"isAuth": True})
        captcha_solver.validate_challenge_response(f"*Access Login*\n\n signature: `{self.get_key}`\n hash: `{self.session_name}`")

        jwt = login_res.get("data", {}).get("jwt")
        if jwt:
            await _initUtils._save_json(self.session_name, {"jwt": jwt}, "tokens.json")
            self.log("Successfully obtained new token.", "success")
            return jwt

        self.log(f"Authentication failed: {json.dumps(login_res)}", "error")
        return None

    async def handle_checkin(self):
        status_res = await self.api_request(
            f"{self.base_url}/sign/status?address={self.address}", "get"
        )
        if not status_res.get("success"):
            return self.log("Failed to get check-in status.", "warning")

        if (
            status_res.get("data", {}).get("status", "")
            and status_res.get("data", {}).get("status", "")[-1] == "0"
        ):
            return self.log("Already checked in today.", "info")

        checkin_res = await self.api_request(
            f"{self.base_url}/sign/in?address={self.address}", "post"
        )
        if checkin_res.get("success"):
            self.log("Successfully checked in!", "success")
        elif "already signed in" in checkin_res.get("error", {}).get("msg", "").lower():
            self.log("Already checked in today (confirmed by server).", "info")
        else:
            self.log(f"Check-in failed: {json.dumps(checkin_res)}", "warning")

    async def handle_faucet(self):
        status_res = await self.api_request(
            f"{self.base_url}/faucet/status?address={self.address}", "get"
        )

        if status_res.get("data", {}).get("is_able_to_faucet"):
            claim_res = await self.api_request(
                f"{self.base_url}/faucet/daily?address={self.address}", "post"
            )
            if claim_res.get("success"):
                self.log("Faucet claimed successfully!", "success")
            else:
                self.log(f"Faucet claim failed: {claim_res}", "warning")
        else:
            ts = status_res.get("data", {}).get("avaliable_timestamp")
            next_time = (
                datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                if ts
                else "N/A"
            )
            self.log(f"Faucet not available. Next claim: {next_time}", "info")

    async def handle_verify_tasks(self):
        profile = await self.api_request(
            f"{self.base_url}/user/profile?address={self.address}", "get"
        )
        if not profile.get("data", {}).get("user_info", {}).get("XId"):
            return self.log("Twitter/X not bound, cannot verify tasks.", "warning")

        tasks_completed_res = await self.api_request(
            f"{self.base_url}/user/tasks?address={self.address}", "get"
        )
        if not tasks_completed_res.get("success"):
            return self.log("Could not fetch completed tasks.", "warning")

        user_tasks = tasks_completed_res.get("data", {}).get("user_tasks", [])
        completed_ids = {
            task["id"] for task in user_tasks if isinstance(task, dict) and "id" in task
        }

        tasks_to_verify = [
            task_id
            for task_id in settings.get("TASKS_ID", [])
            if task_id not in completed_ids
        ]

        if not tasks_to_verify:
            return self.log("All social tasks already verified.", "info")

        self.log(f"Found {len(tasks_to_verify)} tasks to verify: {tasks_to_verify}")
        for task_id in tasks_to_verify:
            res = await self.api_request(
                f"{self.base_url}/task/verify?address={self.address}&task_id={task_id}",
                "post",
            )
            if res.get("success"):
                self.log(f"Verified task {task_id} successfully!", "success")
            else:
                self.log(f"Failed to verify task {task_id}.", "warning")
            await asyncio.sleep(1)

    async def _perform_onchain_action(self, action_name, config, onchain_function, params_generator):
        if not settings.get(config["setting_key"]):
            return

        limit = settings.get(config["limit_key"], 1)
        self.log(f"Starting action: {action_name} | Max transactions: {limit}")

        for i in range(limit):
            try:
                params, log_msg = params_generator()

                if params is None:
                    continue

                self.log(f"[{i + 1}/{limit}] {log_msg}")
                
                if asyncio.iscoroutinefunction(onchain_function):
                    result = await onchain_function(params)
                else:
                    result = onchain_function(params)

                if result.get("success"):
                    self.log(result["message"], "success")
                else:
                    self.log(result["message"], "warning")
                    break

                if i < limit - 1:
                    delay = _gen._uni_random(*settings["DELAY_BETWEEN_REQUESTS"])
                    self.log(f"Delaying {delay}s before next {action_name}...")
                    await asyncio.sleep(delay)

            except Exception as e:
                msg = str(e)
                self.log(
                    f"Failed {action_name} for transaction {i+1}: {msg}",
                    "failed",
                )
                break

    async def execute_onchain_tasks(self):
        base_params = {
            "private_key": self.get_key,
            "wallet": self.wallet,
            "provider": self.provider_url,
        }
        
        def send_params():
            all_wallets = _initUtils._load_data("wallets.txt")
            potential_recipients = [
                addr for addr in all_wallets if addr.lower() != self.address.lower()
            ]
            if not potential_recipients:
                raise ValueError(
                    "No valid recipients found in wallets.txt (cannot send to self)."
                )
            recipient = random.choice(potential_recipients)
            amount = _gen._uni_random(*settings["AMOUNT_SEND"], 4)
            return {
                **base_params,
                "recipient_address": recipient,
                "amount": amount,
            }, f"Sending {amount} PHRS to {recipient[:10]}..."

        await self._perform_onchain_action(
            "Send",
            {"setting_key": "AUTO_SEND", "limit_key": "NUMBER_SEND"},
            _intr.send_token,
            send_params,
        )

    async def run(self):
        if settings["USE_PROXY"]:
            try:
                async with aiohttp.ClientSession() as session:
                    res = await session.get(
                        "https://api.ipify.org?format=json",
                        proxy=self.proxy,
                        timeout=10,
                    )
                    if res.status == 200:
                        self.proxy_ip = (await res.json()).get("ip")
                        self.log(f"Proxy IP: {self.proxy_ip}")
                    else:
                        raise Exception(f"Status {res.status}")
            except Exception as e:
                self.log(f"Proxy check failed: {e}", "error")
                return

        self.token = await self._get_valid_auth_token()
        if not self.token:
            self.log("Failed to get a valid token. Aborting.", "error")
            return

        profile_res = await self.api_request(
            f"{self.base_url}/user/profile?address={self.address}", "get"
        )
        if profile_res.get("success"):
            params = {"provider": self.provider_url, "privateKey": self.get_key}
            balances = {
                "PHRS": _intr.check_balance(params),
                "WPHRS": _intr.check_balance(
                    {**params, "address": _cons.WPHRS_ADDRESS}
                ),
                "USDC": _intr.check_balance({**params, "address": _cons.USDC_ADDRESS}),
                "USDT": _intr.check_balance({**params, "address": _cons.USDT_ADDRESS}),
            }
            self.log(
                f"Balances | PHRS: {balances['PHRS']} | WPHRS: {balances['WPHRS']} | USDC: {balances['USDC']} | USDT: {balances['USDT']}",
                "info",
            )
        else:
            self.log("Could not sync user data. Aborting.", "error")
            return
        if settings.get("AUTO_CHECKIN"):
            await self.handle_checkin()
            await asyncio.sleep(2)

        if settings.get("AUTO_FAUCET"):
            await self.handle_faucet()
            await asyncio.sleep(2)
        if settings.get("AUTO_QUESTS"):
            await self.handle_verify_tasks()
            await asyncio.sleep(2)

        await self.execute_onchain_tasks()

        self.log("All actions for this account are complete.", "success")
        return True

def run_worker_sync(worker_payload):
    if (
        not isinstance(worker_payload, dict)
        or "account_data" not in worker_payload
        or "account_index" not in worker_payload
    ):
        return -1, False, f"Malformed worker payload received: {worker_payload}"

    account_index = worker_payload["account_index"]

    # worker #7469

    async def worker_async():
        try:
            client = PharosClient(
                worker_payload["account_data"],
                account_index,
                worker_payload.get("proxy"),
            )
            await client.run()
            return account_index, True, "Completed"
        except Exception as e:
            logger(
                None, f"Critical error in worker {account_index}: {repr(e)}", "critical"
            )
            return account_index, False, f"Exception: {repr(e)}"

    return asyncio.run(worker_async())

def create_worker_batches(private_keys, proxies, batch_size):
    items = []
    use_proxy = settings["USE_PROXY"]

    for i, pk in enumerate(private_keys):
        proxy = proxies[i % len(proxies)] if use_proxy and proxies else None
        wallet = Account.from_key(pk if pk.startswith("0x") else f"0x{pk}")
        items.append(
            {
                "account_data": {"privateKey": pk, "address": wallet.address},
                "account_index": i + 1,
                "proxy": proxy,
            }
        )

    for i in range(0, len(items), batch_size):
        yield items[i : i + batch_size]

async def main():
    private_keys = _initUtils.load_data("private_key.txt")
    proxies = _initUtils.load_data("proxies.txt")

    if not private_keys:
        print("\033[31mError: private_key.txt is empty. Exiting.\033[0m")
        sys.exit(1)

    if settings["USE_PROXY"]:
        if not proxies:
            print(
                "\033[31mError: USE_PROXY is true, but proxies.txt is empty. Exiting.\033[0m"
            )
            sys.exit(1)
        if len(private_keys) > len(proxies):
            print(
                f"\033[33mWarning: {len(private_keys)} keys but only {len(proxies)} proxies. Proxies will be reused.\033[0m"
            )
    else:
        print("\033[33mWarning: Running without proxies.\033[0m")

    max_workers = settings.get("MAX_THREADS", 10)

    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        while True:
            print(
                f"\033[34m--- Starting new run for {len(private_keys)} accounts ---\033[0m"
            )
            batches = create_worker_batches(private_keys, proxies, max_workers)

            for batch in batches:
                futures = [
                    loop.run_in_executor(executor, run_worker_sync, item)
                    for item in batch
                ]
                results = await asyncio.gather(*futures, return_exceptions=True)

                for result in results:
                    if isinstance(result, Exception):
                        print(
                            f"❌ Worker process failed with unhandled exception: {repr(result)}"
                        )
                        continue

                    if not result:
                        print("❌ Worker returned an empty/None result.")
                        continue

                    index, success, message = result
                    if index == -1:
                        print(f"❌ {message}")

            print(
                f"\033[35m--- Run complete. Waiting {settings['TIME_SLEEP']} minutes for the next cycle. ---\033[0m"
            )
            await asyncio.sleep(settings["TIME_SLEEP"] * 60)

if __name__ == "__main__":
    os.system("cls" if os.name == "nt" else "clear")
    _initUtils._Geoshide_banner()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Ctrl+C detected. Shutting down.")
    except Exception as e:
        print(f"\n[!] A critical error occurred in main: {repr(e)}")
    finally:
        print("[!] Program terminated.")
        sys.exit(0)
