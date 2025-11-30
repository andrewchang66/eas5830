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
           
    # Load contract info for both chains
    info_source = get_contract_info("source", contract_info)
    info_dest   = get_contract_info("destination", contract_info)

    # Load warden private key (stored under source in contract_info.json)
    warden_key = info_source["private_key"]

    # Connect to both chains
    w3_src = connect_to("source")       # Avalanche Fuji
    w3_dst = connect_to("destination")  # BSC Testnet

    # Instantiate contract objects
    src_contract = w3_src.eth.contract(
        address=Web3.to_checksum_address(info_source["address"]),
        abi=info_source["abi"]
    )

    dst_contract = w3_dst.eth.contract(
        address=Web3.to_checksum_address(info_dest["address"]),
        abi=info_dest["abi"]
    )

    # Warden accounts on both chains
    acct_src = w3_src.eth.account.from_key(warden_key)
    acct_dst = w3_dst.eth.account.from_key(warden_key)

    # Determine block ranges (last 5 blocks)
    latest_src = w3_src.eth.block_number
    latest_dst = w3_dst.eth.block_number

    start_src = max(0, latest_src - 5)
    start_dst = max(0, latest_dst - 5)

    # If chain == "source": handle Deposit → wrap on BSC

    if chain == "source":
        print(f"Scanning SOURCE chain (Avalanche Fuji) blocks {start_src} → {latest_src}")

        try:
            deposit_filter = src_contract.events.Deposit.create_filter(
                fromBlock=start_src,
                toBlock=latest_src
            )
            events = deposit_filter.get_all_entries()
        except Exception as e:
            print("Error creating Deposit filter:", e)
            return 0

        for ev in events:
            token     = ev["args"]["token"]
            recipient = ev["args"]["recipient"]
            amount    = ev["args"]["amount"]

            print(f"Found Deposit: token={token}, recipient={recipient}, amount={amount}")
            print("Calling wrap() on destination (BSC)…")

            try:
                nonce = w3_dst.eth.get_transaction_count(acct_dst.address)
                tx = dst_contract.functions.wrap(
                    Web3.to_checksum_address(token),
                    Web3.to_checksum_address(recipient),
                    int(amount)
                ).build_transaction({
                    "from": acct_dst.address,
                    "nonce": nonce,
                    "gasPrice": w3_dst.eth.gas_price,
                    "chainId": w3_dst.eth.chain_id,
                })

                # Estimate gas
                tx["gas"] = w3_dst.eth.estimate_gas(tx)

                signed = acct_dst.sign_transaction(tx)
                tx_hash = w3_dst.eth.send_raw_transaction(signed.rawTransaction)
                print("Sent wrap() tx:", tx_hash.hex())

            except Exception as e:
                print("wrap() call failed:", e)

        return 1

    # If chain == "destination": handle Unwrap → withdraw on Avax

    if chain == "destination":
        print(f"Scanning DESTINATION chain (BSC Testnet) blocks {start_dst} → {latest_dst}")

        try:
            unwrap_filter = dst_contract.events.Unwrap.create_filter(
                fromBlock=start_dst,
                toBlock=latest_dst
            )
            events = unwrap_filter.get_all_entries()
        except Exception as e:
            print("Error creating Unwrap filter:", e)
            return 0

        for ev in events:
            # Event arg names depend on your Solidity definition; supporting common variants:
            underlying = ev["args"].get("underlying_token") or ev["args"].get("underlying")
            recipient  = ev["args"].get("to")  # recipient on source chain
            amount     = ev["args"]["amount"]

            print(f"Found Unwrap: underlying={underlying}, to={recipient}, amount={amount}")
            print("Calling withdraw() on source (Avalanche)…")

            try:
                nonce = w3_src.eth.get_transaction_count(acct_src.address)
                tx = src_contract.functions.withdraw(
                    Web3.to_checksum_address(underlying),
                    Web3.to_checksum_address(recipient),
                    int(amount)
                ).build_transaction({
                    "from": acct_src.address,
                    "nonce": nonce,
                    "gasPrice": w3_src.eth.gas_price,
                    "chainId": w3_src.eth.chain_id,
                })

                tx["gas"] = w3_src.eth.estimate_gas(tx)

                signed = acct_src.sign_transaction(tx)
                tx_hash = w3_src.eth.send_raw_transaction(signed.rawTransaction)
                print("Sent withdraw() tx:", tx_hash.hex())

            except Exception as e:
                print("withdraw() call failed:", e)

        return 1

        ###########

    
