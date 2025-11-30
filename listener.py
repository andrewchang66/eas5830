from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware #Necessary for POA chains
from datetime import datetime
import json
import pandas as pd


def connect_to(chain):
    if chain == 'source':  # The source contract chain is avax
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc" #AVAX C-chain testnet

    if chain == 'destination':  # The destination contract chain is bsc
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/" #BSC testnet

    if chain in ['source','destination']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        # inject the poa compatibility middleware to the innermost layer
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    return w3


def get_contract_info(chain, contract_info):
    """
        Load the contract_info file into a dictionary
        This function is used by the autograder and will likely be useful to you
    """
    try:
        with open(contract_info, 'r')  as f:
            contracts = json.load(f)
    except Exception as e:
        print( f"Failed to read contract info\nPlease contact your instructor\n{e}" )
        return 0
    return contracts[chain]



def scan_blocks(chain, contract_info="contract_info.json"):
    """
        chain - (string) should be either "source" or "destination"
        Scan the last 5 blocks of the source and destination chains
        Look for 'Deposit' events on the source chain and 'Unwrap' events on the destination chain
        When Deposit events are found on the source chain, call the 'wrap' function the destination chain
        When Unwrap events are found on the destination chain, call the 'withdraw' function on the source chain
    """

    # This is different from Bridge IV where chain was "avax" or "bsc"
    if chain not in ['source','destination']:
        print( f"Invalid chain: {chain}" )
        return 0
    
    ##### YOUR CODE HERE #####

    # 1. 設定 warden 私鑰（同時在 Source / Destination 合約上擁有 WARDEN_ROLE）
    WARDEN_PRIVATE_KEY = "0xYOUR_WARDEN_PRIVATE_KEY_HERE"

    if WARDEN_PRIVATE_KEY == "0xYOUR_WARDEN_PRIVATE_KEY_HERE":
        print("Please set WARDEN_PRIVATE_KEY in bridge.py")
        return 0

    # helper：從私鑰算 address
    def get_warden_address(w3):
        acct = w3.eth.account.from_key(WARDEN_PRIVATE_KEY)
        return acct.address

    # helper：用 warden 私鑰送交易
    def send_tx(w3, fn):
        """
        fn: 合約函式物件，例如 contract.functions.wrap(...) / withdraw(...)
        """
        warden_addr = get_warden_address(w3)
        nonce = w3.eth.get_transaction_count(warden_addr)
        gas_price = w3.eth.gas_price

        tx = fn.build_transaction({
            "from": warden_addr,
            "nonce": nonce,
            "gasPrice": gas_price,
        })

        gas_estimate = w3.eth.estimate_gas(tx)
        tx["gas"] = gas_estimate

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=WARDEN_PRIVATE_KEY)

        raw_tx = getattr(signed_tx, "rawTransaction", None)
        if raw_tx is None:
            raw_tx = getattr(signed_tx, "raw_transaction")

        tx_hash = w3.eth.send_raw_transaction(raw_tx)
        print("  → sent tx:", tx_hash.hex())
        return tx_hash

    # 2. 連線兩條鏈
    w3_source = connect_to('source')
    w3_destination = connect_to('destination')

    if (not w3_source.is_connected()) or (not w3_destination.is_connected()):
        print("Failed to connect to RPCs")
        return 0

    # 3. 從 contract_info.json 拿到合約地址 & ABI
    src_info = get_contract_info('source', contract_info)
    dst_info = get_contract_info('destination', contract_info)

    try:
        src_addr = Web3.to_checksum_address(src_info["address"])
        dst_addr = Web3.to_checksum_address(dst_info["address"])
        src_abi  = src_info["abi"]
        dst_abi  = dst_info["abi"]
    except Exception as e:
        print("Error parsing contract_info.json:", e)
        return 0

    src_contract = w3_source.eth.contract(address=src_addr, abi=src_abi)
    dst_contract = w3_destination.eth.contract(address=dst_addr, abi=dst_abi)

    # 4. 取兩條鏈的最新 block，向前掃最後 5 個 block
    latest_src_block = w3_source.eth.block_number
    latest_dst_block = w3_destination.eth.block_number

    from_src_block = max(0, latest_src_block - 4)
    from_dst_block = max(0, latest_dst_block - 4)

    # =========================================================
    # A. Source 鏈：Deposit → Destination.wrap
    # =========================================================
    try:
        # 用 create_filter / get_all_entries（Bridge IV style）
        deposit_filter = src_contract.events.Deposit.create_filter(
            from_block=from_src_block,
            to_block=latest_src_block,
            argument_filters={}
        )
        deposit_events = deposit_filter.get_all_entries()
    except Exception as e:
        print("Error fetching Deposit events:", e)
        deposit_events = []

    if len(deposit_events) > 0:
        print(
            f"Found {len(deposit_events)} Deposit event(s) on source "
            f"(blocks {from_src_block}-{latest_src_block})"
        )

    for ev in deposit_events:
        try:
            token     = ev.args["token"]
            recipient = ev.args["recipient"]
            amount    = int(ev.args["amount"])
        except Exception as e:
            print("Deposit event args mismatch:", e)
            continue

        print(f"Processing Deposit: token={token}, recipient={recipient}, amount={amount}")

        try:
            # Destination.wrap(address _underlying_token, address _recipient, uint256 _amount)
            fn_wrap = dst_contract.functions.wrap(token, recipient, amount)
        except Exception as e:
            print("Error building wrap() call:", e)
            continue

        try:
            send_tx(w3_destination, fn_wrap)
        except Exception as e:
            print("Error sending wrap() tx:", e)

    # =========================================================
    # B. Destination 鏈：Unwrap → Source.withdraw
    # =========================================================
    try:
        unwrap_filter = dst_contract.events.Unwrap.create_filter(
            from_block=from_dst_block,
            to_block=latest_dst_block,
            argument_filters={}
        )
        unwrap_events = unwrap_filter.get_all_entries()
    except Exception as e:
        print("Error fetching Unwrap events:", e)
        unwrap_events = []

    if len(unwrap_events) > 0:
        print(
            f"Found {len(unwrap_events)} Unwrap event(s) on destination "
            f"(blocks {from_dst_block}-{latest_dst_block})"
        )

    for ev in unwrap_events:
        try:
            underlying_token = ev.args["underlying_token"]
            wrapped_token    = ev.args["wrapped_token"]  # debug 用
            frm              = ev.args["frm"]
            to               = ev.args["to"]
            amount           = int(ev.args["amount"])
        except Exception as e:
            print("Unwrap event args mismatch:", e)
            continue

        print(
            f"Processing Unwrap: underlying={underlying_token}, wrapped={wrapped_token}, "
            f"from={frm}, to={to}, amount={amount}"
        )

        try:
            # Source.withdraw(address _token, address _recipient, uint256 _amount)
            fn_withdraw = src_contract.functions.withdraw(underlying_token, to, amount)
        except Exception as e:
            print("Error building withdraw() call:", e)
            continue

        try:
            send_tx(w3_source, fn_withdraw)
        except Exception as e:
            print("Error sending withdraw() tx:", e)

    return 1
