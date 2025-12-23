import time, sys, os
from decimal import Decimal, getcontext
from threading import Lock

from eth_account import Account
from web3 import Web3

from config import config as _conf
from config.config import settings as _sett

wallet_locks = {}
getcontext().prec = 28

sys.stderr = open(os.devnull, 'w')
web3 = Web3(Web3.HTTPProvider(_sett["RPC_URL"]))

def get_wallet_lock(address):
    if address not in wallet_locks:
        wallet_locks[address] = Lock()
    return wallet_locks[address]

def approve_token(token, amount, wallet, web3, router, private_key):
    contract = web3.eth.contract(address=token, abi=_conf.ERC20_ABI)
    current_allowance = contract.functions.allowance(wallet, router.address).call()

    if current_allowance < amount:
        tx = contract.functions.approve(router.address, amount).build_transaction(
            {
                "from": wallet,
                "nonce": web3.eth.get_transaction_count(wallet),
                "gas": 60000,
                "gasPrice": web3.to_wei("1", "gwei"),
            }
        )
        signed = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
        web3.eth.wait_for_transaction_receipt(tx_hash)

def check_balance(params: dict) -> str:
    from datetime import datetime
    token_address = params.get("address")
    provider_url = params.get("provider")
    private_key = params.get("privateKey")
    abi = params.get("abi", _conf.ERC20_ABI)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        if not provider_url or not private_key:
            return "0"

        web3 = Web3(Web3.HTTPProvider(provider_url))
        account = web3.eth.account.from_key(private_key)
        wallet_address = account.address
        short_addr = f"{wallet_address[:6]}...{wallet_address[-4:]}"

        for attempt in range(3):
            try:
                if token_address:
                    token_contract = web3.eth.contract(
                        address=Web3.to_checksum_address(token_address), abi=abi
                    )
                    balance = token_contract.functions.balanceOf(wallet_address).call()
                    decimals = token_contract.functions.decimals().call()
                    human_balance = Decimal(balance) / Decimal(10**decimals)
                else:
                    balance = web3.eth.get_balance(wallet_address)
                    human_balance = Decimal(balance) / Decimal(10**18)

                return format(human_balance, ".4f")

            except Exception as err:
                
                msg = str(err)
                if "busy" in msg.lower() or "service" in msg.lower():
                    time.sleep(1)
                else:
                    return "0"

        print(f"{now} |  ERROR  | {short_addr} | Failed to get balance after retries.")
        return "0"

    except Exception as err:
        print(f"{now} |  ERROR  | {short_addr} | Unexpected error: {str(err)}")
        return "0"

def send_token(params: dict) -> dict:
    recipient_address = params.get("recipient_address")
    amount = params.get("amount")
    private_key = params.get("private_key")
    provider_url = params.get("provider")

    web3 = Web3(Web3.HTTPProvider(provider_url))
    account = Account.from_key(private_key)
    wallet_address = account.address

    try:
        amount_in_wei = web3.to_wei(str(amount), "ether")
        balance = web3.eth.get_balance(wallet_address)

        if balance < web3.to_wei("0.0001", "ether"):
            return {
                "tx": None,
                "success": False,
                "message": "Insufficient PHRS for transfer",
            }

        estimated_gas = 21000
        gas_price = web3.to_wei("1", "gwei")
        min_required = amount_in_wei + (estimated_gas * gas_price)

        if balance < min_required:
            return {
                "tx": None,
                "success": False,
                "message": f"Insufficient PHRS. Need at least {web3.from_wei(min_required, 'ether')} PHRS, have {web3.from_wei(balance, 'ether')} PHRS.",
            }

        nonce = web3.eth.get_transaction_count(wallet_address, "pending")
        tx = {
            "to": Web3.to_checksum_address(recipient_address),
            "value": amount_in_wei,
            "gas": estimated_gas,
            "gasPrice": gas_price,
            "nonce": nonce,
            "chainId": int(_sett["CHAIN_ID"]),
        }

        signed_tx = Account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = web3.to_hex(tx_hash)

        for _ in range(60):
            try:
                receipt = web3.eth.get_transaction_receipt(tx_hash)
                if receipt:
                    break
            except:
                pass
            time.sleep(2)
        else:
            return {
                "tx": tx_hash_hex,
                "success": False,
                "message": f"Transaction sent but not confirmed after 120s. Check: {_sett['EXPLORER_URL']}{tx_hash_hex}",
            }

        return {
            "tx": tx_hash_hex,
            "success": True,
            "message": f"Send {amount} PHRS! Transaction Hash: {_sett['EXPLORER_URL']}{tx_hash_hex}",
        }

    except Exception as error:
        msg = str(error)

        if "replacement transaction underpriced" in msg or "replay" in msg.lower():
            msg = "TX_REPLAY_ATTACK: Nonce or gas conflict"
        elif "not in the chain after" in msg:
            msg = "Transaction timed out before confirmation"

        return {
            "tx": None,
            "success": False,
            "message": f"Error Send: {msg}",
        }
    
    """
async def swap_token(params):
    from decimal import Decimal
    from web3 import Web3
    from eth_account import Account
    import time
    from aiohttp import ClientSession

    web3 = Web3(Web3.HTTPProvider(params["provider"]))
    if not web3.is_connected():
        return {"success": False, "message": "Could not connect to provider."}

    account = Account.from_key(params["private_key"])
    wallet = account.address
    is_faros = _sett.get("FAROSWAP", False)

    try:
        latest_block = web3.eth.get_block('latest')
        base_fee = latest_block.get('baseFeePerGas', web3.to_wei('1', 'gwei'))
        max_priority_fee = web3.to_wei('1', 'gwei') 
        max_fee_per_gas = base_fee + max_priority_fee

        token_map = _const.TOKEN_MAP_FAROS if is_faros else _const.TOKEN_MAP
        token_in_symbol = params["token_in"]
        token_out_symbol = params["token_out"]
        token_in_address = Web3.to_checksum_address(token_map.get(token_in_symbol))
        token_out_address = Web3.to_checksum_address(token_map.get(token_out_symbol))

        if not token_in_address or not token_out_address:
            return {"success": False, "message": f"Token {token_in_symbol} or {token_out_symbol} not found."}

        token_contract = web3.eth.contract(address=token_in_address, abi=_conf.ERC20_ABI)
        decimals = token_contract.functions.decimals().call()
        amount_in = int(Decimal(params["amount"]) * (10 ** decimals))

        if amount_in == 0:
            return {"success": False, "message": "Calculated swap amount is zero."}
        
        current_nonce = web3.eth.get_transaction_count(wallet)

        if is_faros:
            async with ClientSession() as session:
                tx_route_data = await get_dodo_route_from_api(
                    session, token_in_address, token_out_address, amount_in, wallet
                )

            if not tx_route_data:
                return {"success": False, "message": "Failed to get route from DODO API."}

            target_contract = Web3.to_checksum_address(tx_route_data.get("to"))
            
            allowance = token_contract.functions.allowance(wallet, target_contract).call()
            if allowance < amount_in:
                approve_tx = token_contract.functions.approve(target_contract, amount_in).build_transaction({
                    "from": wallet, "nonce": current_nonce, "gas": 100000, 
                    "maxFeePerGas": max_fee_per_gas, "maxPriorityFeePerGas": max_priority_fee
                })
                signed_approve = account.sign_transaction(approve_tx)
                web3.eth.send_raw_transaction(signed_approve.raw_transaction)
                web3.eth.wait_for_transaction_receipt(signed_approve.hash)
                current_nonce += 1
            
            tx_to_estimate = {
                "to": target_contract, "from": wallet, "value": int(tx_route_data.get("value", 0)),
                "data": tx_route_data.get("data"), "nonce": current_nonce, "chainId": int(_sett["CHAIN_ID"])
            }
        
        else:
            router_address = Web3.to_checksum_address(_const.SWAP_ROUTER_ADDRESS)
            router_abi = _conf.ROUTER_ABI

            allowance = token_contract.functions.allowance(wallet, router_address).call()
            if allowance < amount_in:
                approve_tx = token_contract.functions.approve(router_address, amount_in).build_transaction({
                    "from": wallet, "nonce": current_nonce, "gas": 100000,
                    "maxFeePerGas": max_fee_per_gas, "maxPriorityFeePerGas": max_priority_fee
                })
                signed_approve = account.sign_transaction(approve_tx)
                web3.eth.send_raw_transaction(signed_approve.raw_transaction)
                web3.eth.wait_for_transaction_receipt(signed_approve.hash)
                current_nonce += 1
            
            router = web3.eth.contract(address=router_address, abi=router_abi)
            deadline = int(time.time()) + 600
            
            params_struct = {
                "tokenIn": token_in_address,
                "tokenOut": token_out_address,
                "fee": 3000,
                "recipient": wallet,
                "deadline": deadline,
                "amountIn": amount_in,
                "amountOutMinimum": 1,
                "sqrtPriceLimitX96": 0
            }

            encoded_input = router.functions.exactInputSingle(params_struct).build_transaction({
                "from": wallet, "nonce": current_nonce
            })["data"]

            tx_to_estimate = router.functions.multicall(deadline, [encoded_input]).build_transaction({
                "from": wallet, "nonce": current_nonce, "value": 0, "chainId": int(_sett["CHAIN_ID"])
            })

        estimated_gas = web3.eth.estimate_gas(tx_to_estimate)
        
        final_tx = {
            **tx_to_estimate,
            "gas": int(estimated_gas * 1.25),
            "maxFeePerGas": max_fee_per_gas,
            "maxPriorityFeePerGas": max_priority_fee
        }

        signed_tx = account.sign_transaction(final_tx)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
        tx_url = f"{_sett['EXPLORER_URL']}{web3.to_hex(tx_hash)}"

        return {
            "tx_hash": web3.to_hex(tx_hash),
            "success": receipt.status == 1,
            "message": f"Swap {params['token_in']} → {params['token_out']} {'success' if receipt.status == 1 else 'failed'}: {tx_url}"
        }
    except Exception as e:
        return {"success": False, "message": f"An error occurred in swap_token: {str(e)}"}
    
def wrap_token(params):
    from web3 import Web3
    from eth_account import Account

    action = params["action"]
    amount = params["amount"]
    private_key = params["private_key"]
    rpc_url = params["provider"]

    web3 = Web3(Web3.HTTPProvider(rpc_url))
    account = Account.from_key(private_key)
    wallet_address = account.address

    if _sett.get("FAROSWAP", False):
        contract_address = _const.WPHRS_ADDRESS_FAROS
        contract = web3.eth.contract(address=contract_address, abi=_conf.FAROS_ABI)
    else:
        contract_address = _const.WPHRS_ADDRESS
        contract = web3.eth.contract(address=contract_address, abi=_conf.SWAP_ABI)

    try:
        phrs_balance = web3.eth.get_balance(wallet_address)
        if phrs_balance < web3.to_wei("0.0001", "ether"):
            return {
                "tx": None,
                "success": False,
                "message": "Insufficient PHRS for transaction fees",
            }

        amount_wei = web3.to_wei(str(amount), "ether")
        nonce = web3.eth.get_transaction_count(wallet_address, "pending")
        gas_price = web3.to_wei("1", "gwei")

        if action == "unwrap":
            wphrs_contract = web3.eth.contract(address=contract_address, abi=_conf.ERC20_ABI)
            wphrs_balance = wphrs_contract.functions.balanceOf(wallet_address).call()

            if wphrs_balance < amount_wei:
                return {
                    "tx": None,
                    "success": False,
                    "message": f"Insufficient WPHRS balance for unwrap (have {wphrs_balance / 1e18:.6f})",
                }

        if action == "wrap":
            tx = contract.functions.deposit().build_transaction({
                "from": wallet_address,
                "value": amount_wei,
                "gas": 60000,
                "gasPrice": gas_price,
                "nonce": nonce,
                "chainId": int(_sett["CHAIN_ID"]),
            })
        elif action == "unwrap":
            tx = contract.functions.withdraw(amount_wei).build_transaction({
                "from": wallet_address,
                "gas": 60000,
                "gasPrice": gas_price,
                "nonce": nonce,
                "chainId": int(_sett["CHAIN_ID"]),
            })
        else:
            return {
                "tx": None,
                "success": False,
                "message": f"Invalid action: {action}",
            }

        signed_tx = web3.eth.account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

        tx_url = f"{_sett['EXPLORER_URL']}{web3.to_hex(tx_hash)}"

        return {
            "tx": web3.to_hex(tx_hash),
            "success": receipt.status == 1,
            "message": f"{action.title()} {amount} {'success' if receipt.status == 1 else 'failed'}: Transaction Hash: {tx_url}",
        }

    except Exception as error:
        return {
            "tx": None,
            "success": False,
            "message": f"{action.title()} {amount} failed: {str(error)}",
        }

def check_balance(params: dict) -> str:
    from datetime import datetime
    token_address = params.get("address")
    provider_url = params.get("provider")
    private_key = params.get("privateKey")
    abi = params.get("abi", _conf.ERC20_ABI)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        if not provider_url or not private_key:
            return "0"

        web3 = Web3(Web3.HTTPProvider(provider_url))
        account = web3.eth.account.from_key(private_key)
        wallet_address = account.address
        short_addr = f"{wallet_address[:6]}...{wallet_address[-4:]}"

        for attempt in range(3):
            try:
                if token_address:
                    token_contract = web3.eth.contract(
                        address=Web3.to_checksum_address(token_address), abi=abi
                    )
                    balance = token_contract.functions.balanceOf(wallet_address).call()
                    decimals = token_contract.functions.decimals().call()
                    human_balance = Decimal(balance) / Decimal(10**decimals)
                else:
                    balance = web3.eth.get_balance(wallet_address)
                    human_balance = Decimal(balance) / Decimal(10**18)

                return format(human_balance, ".4f")

            except Exception as err:
                
                msg = str(err)
                if "busy" in msg.lower() or "service" in msg.lower():
                    time.sleep(1)
                else:
                    return "0"

        print(f"{now} |  ERROR  | {short_addr} | Failed to get balance after retries.")
        return "0"

    except Exception as err:
        print(f"{now} |  ERROR  | {short_addr} | Unexpected error: {str(err)}")
        return "0"

def send_token(params: dict) -> dict:
    recipient_address = params.get("recipient_address")
    amount = params.get("amount")
    private_key = params.get("private_key")
    provider_url = params.get("provider")

    web3 = Web3(Web3.HTTPProvider(provider_url))
    account = Account.from_key(private_key)
    wallet_address = account.address

    try:
        amount_in_wei = web3.to_wei(str(amount), "ether")
        balance = web3.eth.get_balance(wallet_address)

        if balance < web3.to_wei("0.0001", "ether"):
            return {
                "tx": None,
                "success": False,
                "message": "Insufficient PHRS for transfer",
            }

        estimated_gas = 21000
        gas_price = web3.to_wei("1", "gwei")
        min_required = amount_in_wei + (estimated_gas * gas_price)

        if balance < min_required:
            return {
                "tx": None,
                "success": False,
                "message": f"Insufficient PHRS. Need at least {web3.from_wei(min_required, 'ether')} PHRS, have {web3.from_wei(balance, 'ether')} PHRS.",
            }

        nonce = web3.eth.get_transaction_count(wallet_address, "pending")
        tx = {
            "to": Web3.to_checksum_address(recipient_address),
            "value": amount_in_wei,
            "gas": estimated_gas,
            "gasPrice": gas_price,
            "nonce": nonce,
            "chainId": int(_sett["CHAIN_ID"]),
        }

        signed_tx = Account.sign_transaction(tx, private_key)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash_hex = web3.to_hex(tx_hash)

        for _ in range(60):
            try:
                receipt = web3.eth.get_transaction_receipt(tx_hash)
                if receipt:
                    break
            except:
                pass
            time.sleep(2)
        else:
            return {
                "tx": tx_hash_hex,
                "success": False,
                "message": f"Transaction sent but not confirmed after 120s. Check: {_sett['EXPLORER_URL']}{tx_hash_hex}",
            }

        return {
            "tx": tx_hash_hex,
            "success": True,
            "message": f"Send {amount} PHRS! Transaction Hash: {_sett['EXPLORER_URL']}{tx_hash_hex}",
        }

    except Exception as error:
        msg = str(error)

        if "replacement transaction underpriced" in msg or "replay" in msg.lower():
            msg = "TX_REPLAY_ATTACK: Nonce or gas conflict"
        elif "not in the chain after" in msg:
            msg = "Transaction timed out before confirmation"

        return {
            "tx": None,
            "success": False,
            "message": f"Error Send: {msg}",
        }
    
def add_liquidity_uniswap_v3(params):
    try:
        web3 = Web3(Web3.HTTPProvider(params["provider"]))
        if not web3.is_connected():
            return {"success": False, "message": "Could not connect to provider."}

        account = Account.from_key(params["private_key"])
        wallet = account.address

        is_faros = _sett.get("FAROSWAP", False)
        token_map = _const.TOKEN_MAP_FAROS if is_faros else _const.TOKEN_MAP
        pool_map = _const.POOL_MAP_ADDRESS if not is_faros else {}

        original_token0_symbol = params["token0"]
        original_token1_symbol = params["token1"]
        addr0_orig = token_map.get(original_token0_symbol)
        addr1_orig = token_map.get(original_token1_symbol)

        if not addr0_orig or not addr1_orig:
            return {"success": False, "message": "Invalid token symbol in parameters."}

        if addr0_orig.lower() < addr1_orig.lower():
            token0_symbol, token1_symbol = original_token0_symbol, original_token1_symbol
            token0_address, token1_address = Web3.to_checksum_address(addr0_orig), Web3.to_checksum_address(addr1_orig)
        else:
            token0_symbol, token1_symbol = original_token1_symbol, original_token0_symbol
            token0_address, token1_address = Web3.to_checksum_address(addr1_orig), Web3.to_checksum_address(addr0_orig)

        if is_faros:
            token0_contract = web3.eth.contract(address=token0_address, abi=_conf.ERC20_ABI)
            token1_contract = web3.eth.contract(address=token1_address, abi=_conf.ERC20_ABI)

            token0_decimals = token0_contract.functions.decimals().call()
            token1_decimals = token1_contract.functions.decimals().call()

            raw_amount0 = int(Decimal(params["amount"]) * (10 ** token0_decimals))
            raw_amount1 = int(Decimal(params["amount1"]) * (10 ** token1_decimals))

            if raw_amount0 == 0 or raw_amount1 == 0:
                return {"success": False, "message": "Amount too low to proceed."}

            manager_address = Web3.to_checksum_address(_const.POSITION_MANAGER_ADDRESS_FAROS)
            nonce = web3.eth.get_transaction_count(wallet)

            for token_contract, raw_amount in [(token0_contract, raw_amount0), (token1_contract, raw_amount1)]:
                allowance = token_contract.functions.allowance(wallet, manager_address).call()
                if allowance < raw_amount:
                    tx_approve = token_contract.functions.approve(manager_address, raw_amount).build_transaction({
                        "from": wallet, "nonce": nonce, "gas": 100_000,
                        "gasPrice": web3.eth.gas_price, "chainId": int(_sett["CHAIN_ID"]),
                    })
                    signed_approve = web3.eth.account.sign_transaction(tx_approve, params["private_key"])
                    web3.eth.send_raw_transaction(signed_approve.raw_transaction)
                    web3.eth.wait_for_transaction_receipt(signed_approve.hash)
                    nonce += 1
            
            dodo_pool_address = _const.DODO_POOL_MAP.get((token0_symbol, token1_symbol)) or \
                                _const.DODO_POOL_MAP.get((token1_symbol, token0_symbol))

            if not dodo_pool_address:
                return {"success": False, "message": f"DODO Pool address not found for {token0_symbol}-{token1_symbol} in _const.DODO_POOL_MAP"}

            slippage_tolerance = Decimal('0.005')
            min_amount0 = int(raw_amount0 * (Decimal(1) - slippage_tolerance))
            min_amount1 = int(raw_amount1 * (Decimal(1) - slippage_tolerance))

            manager_contract = web3.eth.contract(address=manager_address, abi=_conf.FAROS_POOL_ABI)
            deadline = int(time.time()) + 600

            tx = manager_contract.functions.addLiquidity(
                Web3.to_checksum_address(dodo_pool_address),
                raw_amount0,
                raw_amount1,
                min_amount0,
                min_amount1,
                0,
                deadline
            ).build_transaction({
                "from": wallet, "nonce": nonce, "gas": 800_000,
                "gasPrice": web3.eth.gas_price, "chainId": int(_sett["CHAIN_ID"]),
            })

            signed_tx = web3.eth.account.sign_transaction(tx, params["private_key"])
            tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            tx_url = f"{_sett['EXPLORER_URL']}{web3.to_hex(tx_hash)}"

            return {
                "tx_hash": web3.to_hex(tx_hash),
                "success": receipt.status == 1,
                "message": f"Add Liquidity (Faroswap/DODO) | {token0_symbol} + {token1_symbol} | Tx: {tx_url}",
            }

        else:
            pool_address = pool_map.get((token0_symbol, token1_symbol)) or pool_map.get((token1_symbol, token0_symbol))
            if not pool_address:
                return {"success": False, "message": f"Unknown Uniswap pool address for pair {token0_symbol}-{token1_symbol}."}
            
            pool_address = Web3.to_checksum_address(pool_address)
            pool_contract = web3.eth.contract(address=pool_address, abi=_conf.UNISWAP_POOL_ABI)
            
            sqrt_price_x96 = pool_contract.functions.slot0().call()[0]
            price = (Decimal(sqrt_price_x96) / (1 << 96)) ** 2

            input_token_symbol = params["input_token"]
            input_amount = Decimal(params["amount"])

            if input_token_symbol == token0_symbol:
                amount0_desired, amount1_desired = input_amount, input_amount * price
            elif input_token_symbol == token1_symbol:
                amount1_desired, amount0_desired = input_amount, input_amount / price
            else:
                return {"success": False, "message": f"Input token '{input_token_symbol}' does not match pool pair {token0_symbol}-{token1_symbol}."}

            token0_contract = web3.eth.contract(address=token0_address, abi=_conf.ERC20_ABI)
            token1_contract = web3.eth.contract(address=token1_address, abi=_conf.ERC20_ABI)
            dec0 = token0_contract.functions.decimals().call()
            dec1 = token1_contract.functions.decimals().call()

            raw_amount0 = int(amount0_desired * (Decimal(10) ** dec0))
            raw_amount1 = int(amount1_desired * (Decimal(10) ** dec1))

            if raw_amount0 == 0 or raw_amount1 == 0:
                return {"success": False, "message": f"Cannot add liquidity with 0 tokens. Raw amounts are too low."}

            manager_address = Web3.to_checksum_address(_const.POSITION_MANAGER_ADDRESS)
            manager_contract = web3.eth.contract(address=manager_address, abi=_conf.POSITION_MANAGER_ABI)
            nonce = web3.eth.get_transaction_count(wallet)

            for token_contract, raw_amount in [(token0_contract, raw_amount0), (token1_contract, raw_amount1)]:
                allowance = token_contract.functions.allowance(wallet, manager_address).call()
                if allowance < raw_amount:
                    tx_approve = token_contract.functions.approve(manager_address, raw_amount).build_transaction({
                        "from": wallet, "nonce": nonce, "gas": 100_000,
                        "gasPrice": web3.eth.gas_price, "chainId": int(_sett["CHAIN_ID"]),
                    })
                    signed_tx = web3.eth.account.sign_transaction(tx_approve, params["private_key"])
                    web3.eth.send_raw_transaction(signed_tx.raw_transaction)
                    web3.eth.wait_for_transaction_receipt(signed_tx.hash)
                    nonce += 1

            deadline = int(time.time()) + 600
            fee = 500
            tick_lower = -600000
            tick_upper = 600000

            existing_token_id = None
            for i in range(manager_contract.functions.balanceOf(wallet).call()):
                token_id = manager_contract.functions.tokenOfOwnerByIndex(wallet, i).call()
                pos = manager_contract.functions.positions(token_id).call()
                if (pos[2].lower() == token0_address.lower() and pos[3].lower() == token1_address.lower() and
                    pos[4] == fee and pos[5] == tick_lower and pos[6] == tick_upper):
                    existing_token_id = token_id
                    break

            datas = []
            if existing_token_id:
                tx_data = manager_contract.functions.increaseLiquidity({
                    "tokenId": existing_token_id, "amount0Desired": raw_amount0, "amount1Desired": raw_amount1,
                    "amount0Min": 0, "amount1Min": 0, "deadline": deadline,
                }).build_transaction({"from": wallet})["data"]
            else:
                tx_data = manager_contract.functions.mint({
                    "token0": token0_address, "token1": token1_address, "fee": fee,
                    "tickLower": tick_lower, "tickUpper": tick_upper, "amount0Desired": raw_amount0,
                    "amount1Desired": raw_amount1, "amount0Min": 0, "amount1Min": 0,
                    "recipient": wallet, "deadline": deadline,
                }).build_transaction({"from": wallet})["data"]

            datas.append(tx_data)
            datas.append(manager_contract.functions.refundETH().build_transaction({"from": wallet})["data"])

            multicall_tx = manager_contract.functions.multicall(datas).build_transaction({
                "from": wallet, "nonce": nonce, "gas": 1_500_000,
                "gasPrice": web3.eth.gas_price, "value": 0, "chainId": int(_sett["CHAIN_ID"]),
            })

            signed_tx = web3.eth.account.sign_transaction(multicall_tx, params["private_key"])
            tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
            tx_url = f"{_sett['EXPLORER_URL']}{web3.to_hex(tx_hash)}"

            if receipt.status == 1:
                return {
                    "tx_hash": web3.to_hex(tx_hash), "success": True,
                    "message": f"Add Liquidity {'(increase)' if existing_token_id else '(mint)'} | "
                               f"{token0_symbol} + {token1_symbol} | Tx: {tx_url}",
                }
            else:
                return {"success": False, "message": f"Uniswap V3 transaction failed. Tx: {tx_url}"}

    except Exception as e:
        return {
            "tx_hash": None,
            "success": False,
            "message": f"Add Liquidity failed due to an unhandled error: {str(e)}",
        }
    """