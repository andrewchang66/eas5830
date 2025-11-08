import eth_account
import random
import string
import json
from pathlib import Path
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware  # Necessary for POA chains


def merkle_assignment():
    """
        The only modifications you need to make to this method are to assign
        your "random_leaf_index" and uncomment the last line when you are
        ready to attempt to claim a prime. You will need to complete the
        methods called by this method to generate the proof.
    """
    # Generate the list of primes as integers
    num_of_primes = 8192
    primes = generate_primes(num_of_primes)

    # Create a version of the list of primes in bytes32 format
    leaves = convert_leaves(primes)

    # Build a Merkle tree using the bytes32 leaves as the Merkle tree's leaves
    tree = build_merkle(leaves)

    # Select a random leaf and create a proof for that leaf
    random_leaf_index = 0 #TODO generate a random index from primes to claim (0 is already claimed)
    proof = prove_merkle(tree, random_leaf_index)

    # This is the same way the grader generates a challenge for sign_challenge()
    challenge = ''.join(random.choice(string.ascii_letters) for i in range(32))
    # Sign the challenge to prove to the grader you hold the account
    addr, sig = sign_challenge(challenge)

    if sign_challenge_verify(challenge, addr, sig):
        tx_hash = '0x'
        ###
        # TODO, when you are ready to attempt to claim a prime (and pay gas fees),
        #  complete this method and run your code with the following line un-commented
        ###
        
        tx_hash = send_signed_msg(proof, leaves[random_leaf_index])




def generate_primes(num_primes):
    """
        Function to generate the first 'num_primes' prime numbers
        returns list (with length n) of primes (as ints) in ascending order
    """
    primes_list = []

    ##### TODO YOUR CODE HERE #####

    if num_primes <= 0:
        return primes_list

    import math
    n = max(num_primes, 6)
    limit = int(n * (math.log(n) + math.log(math.log(n)))) + 50
    limit = max(limit, 15000)

    while True:
        sieve = bytearray(b"\x01") * (limit + 1)
        sieve[:2] = b"\x00\x00"
        r = int(limit ** 0.5)
        for p in range(2, r + 1):
            if sieve[p]:
                start = p * p
                sieve[start:limit + 1:p] = b"\x00" * (((limit - start) // p) + 1)
        primes_list = [i for i, is_p in enumerate(sieve) if is_p]
        if len(primes_list) >= num_primes:
            return primes_list[:num_primes]
        limit *= 2

    ##### return primes_list #####


def convert_leaves(primes_list):
    """
        Converts the leaves (primes_list) to bytes32 format
        returns list of primes where list entries are bytes32 encodings of primes_list entries
    """

    # TODO YOUR CODE HERE

    leaves = []
    for p in primes_list:
        # Convert integer -> fixed-width 32-byte big-endian form, then keccak it.
        # (OpenZeppelin Merkle expects bytes32 leaves; we store keccak(bytes) as the leaf.)
        prime_bytes = int.to_bytes(p, 32, byteorder="big")
        leaf = Web3.keccak(prime_bytes)
        leaves.append(leaf)
    return leaves


def build_merkle(leaves):
    """
        Function to build a Merkle Tree from the list of prime numbers in bytes32 format
        Returns the Merkle tree (tree) as a list where tree[0] is the list of leaves,
        tree[1] is the parent hashes, and so on until tree[n] which is the root hash
        the root hash produced by the "hash_pair" helper function
    """

    #TODO YOUR CODE HERE
    if not leaves:
        return []

    tree = [list(leaves)]
    while len(tree[-1]) > 1:
        cur = tree[-1]
        if len(cur) % 2 == 1:
            cur = cur + [cur[-1]]
        nxt = []
        for i in range(0, len(cur), 2):
            a, b = cur[i], cur[i+1]
            nxt.append(hash_pair(a, b))
        tree.append(nxt)

    return tree


def prove_merkle(merkle_tree, random_indx):
    """
        Takes a random_index to create a proof of inclusion for and a complete Merkle tree
        as a list of lists where index 0 is the list of leaves, index 1 is the list of
        parent hash values, up to index -1 which is the list of the root hash.
        returns a proof of inclusion as list of values
    """
    merkle_proof = []
    # TODO YOUR CODE HERE

    if not merkle_tree or random_indx is None:
        return merkle_proof

    idx = int(random_indx)
    for level in merkle_tree[:-1]:
        if len(level) == 1:
            break
        last_ix = len(level) - 1
        sib = idx ^ 1
        if sib > last_ix:
            sib = last_ix
        merkle_proof.append(level[sib])
        idx //= 2

    return merkle_proof


def sign_challenge(challenge):
    """
        Takes a challenge (string)
        Returns address, sig
        where address is an ethereum address and sig is a signature (in hex)
        This method is to allow the auto-grader to verify that you have
        claimed a prime
    """
    acct = get_account()

    addr = acct.address
    eth_sk = acct.key

    # TODO YOUR CODE HERE

    from eth_account.messages import encode_defunct

    sk_path = Path("sk.txt")
    priv = sk_path.read_text().strip()
    if priv.startswith("0x") or priv.startswith("0X"):
        priv = priv[2:]

    message = encode_defunct(text=challenge)

    ##
    
    eth_sig_obj = eth_account.Account.sign_message(message, private_key=acct.key)
    return addr, eth_sig_obj.signature.hex()


def send_signed_msg(proof, random_leaf):
    """
        Takes a Merkle proof of a leaf, and that leaf (in bytes32 format)
        builds signs and sends a transaction claiming that leaf (prime)
        on the contract
    """
    chain = 'bsc'

    acct = get_account()
    address, abi = get_contract_info(chain)
    w3 = connect_to(chain)

    # TODO YOUR CODE HERE
    # Load contract info
    with open("contract_info.json", "r") as f:
        ci = json.load(f)
    net = ci["bsc"]
    contract_address = Web3.to_checksum_address(net["address"])
    abi = net["abi"]

    # Connect to BNB Testnet RPC (you can swap this for your own provider URL)
    # Common public endpoint; replace with your own reliable node if needed.
    rpc_url = "https://data-seed-prebsc-1-s1.binance.org:8545"
    w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 60}))
    # Inject POA middleware for BSC testnet
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    assert w3.is_connected(), "Failed to connect to BSC testnet RPC"

    # Prepare signer
    sk_path = Path("sk.txt")
    priv_hex = sk_path.read_text().strip()
    acct = eth_account.Account.from_key(priv_hex)
    sender = acct.address

    # Instantiate contract
    contract = w3.eth.contract(address=contract_address, abi=abi)

    # Ensure types are correct: proof is list[bytes32], random_leaf is bytes32
    # Build transaction
    tx = contract.functions.submit(proof, random_leaf).build_transaction({
        "from": sender,
        "nonce": w3.eth.get_transaction_count(sender),
        "chainId": 97,  # BSC Testnet
        # Let node estimate gas & price
        "gas": w3.eth.estimate_gas({
            "from": sender,
            "to": contract_address,
            "data": contract.encode_abi(fn_name="submit", args=[proof, random_leaf]),
        }),
        "maxFeePerGas": w3.eth.max_priority_fee + w3.eth.generate_gas_price() if hasattr(w3.eth, "max_priority_fee") else None,
        "maxPriorityFeePerGas": getattr(w3.eth, "max_priority_fee", lambda: None)(),
        # Fallback (for legacy networks): if EIP-1559 fields are None, set legacy gasPrice.
        "gasPrice": w3.eth.gas_price,
    })

    # Clean up fields for EIP-1559 vs legacy depending on node support
    # If node doesn't support EIP-1559, remove 'maxFeePerGas'/'maxPriorityFeePerGas'
    if "maxFeePerGas" in tx and tx["maxFeePerGas"] is None:
        tx.pop("maxFeePerGas", None)
    if "maxPriorityFeePerGas" in tx and tx["maxPriorityFeePerGas"] is None:
        tx.pop("maxPriorityFeePerGas", None)

    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction).hex()

    return tx_hash


# Helper functions that do not need to be modified
def connect_to(chain):
    """
        Takes a chain ('avax' or 'bsc') and returns a web3 instance
        connected to that chain.
    """
    if chain not in ['avax','bsc']:
        print(f"{chain} is not a valid option for 'connect_to()'")
        return None
    if chain == 'avax':
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc"  # AVAX C-chain testnet
    else:
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/"  # BSC testnet
    w3 = Web3(Web3.HTTPProvider(api_url))
    # inject the poa compatibility middleware to the innermost layer
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    return w3


def get_account():
    """
        Returns an account object recovered from the secret key
        in "sk.txt"
    """
    cur_dir = Path(__file__).parent.absolute()
    with open(cur_dir.joinpath('sk.txt'), 'r') as f:
        sk = f.readline().rstrip()
    if sk[0:2] == "0x":
        sk = sk[2:]
    return eth_account.Account.from_key(sk)


def get_contract_info(chain):
    """
        Returns a contract address and contract abi from "contract_info.json"
        for the given chain
    """
    contract_file = Path(__file__).parent.absolute() / "contract_info.json"
    if not contract_file.is_file():
        contract_file = Path(__file__).parent.parent.parent / "tests" / "contract_info.json"
    with open(contract_file, "r") as f:
        d = json.load(f)
        d = d[chain]
    return d['address'], d['abi']


def sign_challenge_verify(challenge, addr, sig):
    """
        Helper to verify signatures, verifies sign_challenge(challenge)
        the same way the grader will. No changes are needed for this method
    """
    eth_encoded_msg = eth_account.messages.encode_defunct(text=challenge)

    if eth_account.Account.recover_message(eth_encoded_msg, signature=sig) == addr:
        print(f"Success: signed the challenge {challenge} using address {addr}!")
        return True
    else:
        print(f"Failure: The signature does not verify!")
        print(f"signature = {sig}\naddress = {addr}\nchallenge = {challenge}")
        return False


def hash_pair(a, b):
    """
        The OpenZeppelin Merkle Tree Validator we use sorts the leaves
        https://github.com/OpenZeppelin/openzeppelin-contracts/blob/master/contracts/utils/cryptography/MerkleProof.sol#L217
        So you must sort the leaves as well

        Also, hash functions like keccak are very sensitive to input encoding, so the solidity_keccak function is the function to use

        Another potential gotcha, if you have a prime number (as an int) bytes(prime) will *not* give you the byte representation of the integer prime
        Instead, you must call int.to_bytes(prime,'big').
    """
    if a < b:
        return Web3.solidity_keccak(['bytes32', 'bytes32'], [a, b])
    else:
        return Web3.solidity_keccak(['bytes32', 'bytes32'], [b, a])


if __name__ == "__main__":
    merkle_assignment()
