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
