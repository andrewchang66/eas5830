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

    # 1. 設定 warden 私鑰
    WARDEN_PRIVATE_KEY = "0xb2567941b5da28eef618f671b105053fc2950928e0439a9eb7d6993e8adf3830"

    # 小 helper：從私鑰算出 warden address
    def get_warden_address(w3):
        acct = w3.eth.account.from_key(WARDEN_PRIVATE_KEY)
        return acct.address

    # 小 helper：用 warden 私鑰送交易
    def send_tx(w3, fn):
        warden_addr = get_warden_address(w3)
        nonce = w3.eth.get_transaction_count(warden_addr)
        gas_price = w3.eth.gas_price

        tx = fn.build_transaction({
            "from": warden_addr,
            "nonce": nonce,
            "gasPrice": gas_price,
        })

        # 預估 gas
        gas_estimate = w3.eth.estimate_gas(tx)
        tx["gas"] = gas_estimate

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=WARDEN_PRIVATE_KEY)

        # 兼容不同 web3 版本：可能是 rawTransaction 或 raw_transaction
        raw_tx = getattr(signed_tx, "rawTransaction", None)
        if raw_tx is None:
            raw_tx = getattr(signed_tx, "raw_transaction")

        tx_hash = w3.eth.send_raw_transaction(raw_tx)
        print("  → sent tx:", tx_hash.hex())
        return tx_hash

    # 連線到 source / destination 兩條鏈
    w3_source = connect_to('source')
    w3_destination = connect_to('destination')

    if (not w3_source.is_connected()) or (not w3_destination.is_connected()):
        print("Failed to connect to RPCs")
        return 0

    # 讀 contract_info.json 拿地址與 ABI
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

    # 掃「最後 5 個 blocks」：用在 Source 的 Deposit
    latest_src_block = w3_source.eth.block_number
    from_src_block = max(0, latest_src_block - 4)

    # =========================================================
    # A. 在 source 鏈找 Deposit → destination 鏈呼叫 wrap()
    # =========================================================
    try:
        # Source.sol: event Deposit( address indexed token, address indexed recipient, uint256 amount );
        deposit_event = src_contract.events.Deposit
        deposit_logs = deposit_event.get_logs(
            from_block=from_src_block,
            to_block=latest_src_block
        )
    except Exception as e:
        print("Error fetching Deposit events:", e)
        deposit_logs = []

    if len(deposit_logs) > 0:
        print(
            f"Found {len(deposit_logs)} Deposit event(s) on source "
            f"(blocks {from_src_block}–{latest_src_block})"
        )

    for log in deposit_logs:
        args = log["args"]
        try:
            token     = args["token"]
            recipient = args["recipient"]
            amount    = args["amount"]
        except KeyError as e:
            print("Deposit event args mismatch, missing:", e)
            continue

        print(f"Processing Deposit: token={token}, recipient={recipient}, amount={amount}")

        try:
            # Destination.wrap:
            # function wrap(address _underlying_token, address _recipient, uint256 _amount ) public onlyRole(WARDEN_ROLE)
            fn = dst_contract.functions.wrap(token, recipient, amount)
        except Exception as e:
            print("Error building wrap() call:", e)
            continue

        try:
            send_tx(w3_destination, fn)
        except Exception as e:
            print("Error sending wrap() tx:", e)

    # =========================================================
    # B. 在 destination 鏈找 Unwrap → source 鏈呼叫 withdraw()
    #    這裡只掃「最後 1～2 個 blocks」，避免 BSC RPC 的 limit exceeded
    # =========================================================

    # 當前最新的目的鏈區塊
    latest_dst_block = w3_destination.eth.block_number

    # 我們往回掃最多 5 個區塊：latest, latest-1, ..., latest-4
    unwrap_logs = []
    try:
        unwrap_event = dst_contract.events.Unwrap
    except Exception as e:
        print("Error getting Unwrap event object:", e)
        unwrap_event = None

    if unwrap_event is not None:
        # 從最新往回找
        start_block = latest_dst_block
        end_block = max(0, latest_dst_block - 4)

        for b in range(start_block, end_block - 1, -1):  # 例如 100,99,98,97,96
            try:
                logs = unwrap_event.get_logs(from_block=b, to_block=b)
            except Exception as e:
                # 如果這個 block 撞到 limit 或其他錯誤，就跳過看前一個
                print(f"Error fetching Unwrap events for block {b}: {getattr(e, 'args', e)}")
                continue

            if logs:
                print(f"Found {len(logs)} Unwrap event(s) on destination at block {b}")
                unwrap_logs.extend(logs)
                # 一旦在某個 block 找到，就可以 break（避免重複處理太多不同 unwrap）
                break

    # 處理剛剛找到的 unwrap_logs
    for log in unwrap_logs:
        args = log["args"]
        try:
            underlying_token = args["underlying_token"]
            wrapped_token    = args["wrapped_token"]   # debug 用，不直接用到
            frm              = args["frm"]             # unwrap 發起者
            to               = args["to"]              # 要在 source 領回的人
            amount           = args["amount"]
        except KeyError as e:
            print("Unwrap event args mismatch, missing:", e)
            continue

        print(
            f"Processing Unwrap: underlying={underlying_token}, wrapped={wrapped_token}, "
            f"from={frm}, to={to}, amount={amount}"
        )

        try:
            # Source.withdraw:
            # function withdraw(address _token, address _recipient, uint256 _amount )
            fn = src_contract.functions.withdraw(underlying_token, to, amount)
        except Exception as e:
            print("Error building withdraw() call:", e)
            continue

        try:
            send_tx(w3_source, fn)
        except Exception as e:
            print("Error sending withdraw() tx:", e)
