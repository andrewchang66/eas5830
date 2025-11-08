#!/bin/python
import hashlib
import os
import random


def mine_block(k, prev_hash, transactions):
    """
        k - Number of trailing zeros in the binary representation (integer)
        prev_hash - the hash of the previous block (bytes)
        rand_lines - a set of "transactions," i.e., data to be included in this block (list of strings)

        Complete this function to find a nonce such that 
        sha256( prev_hash + rand_lines + nonce )
        has k trailing zeros in its *binary* representation
    """
    if not isinstance(k, int) or k < 0:
        print("mine_block expects positive integer")
        return b'\x00'

    ##### TODO your code to find a nonce here
    
    # Precompute the constant prefix: prev_hash followed by all transactions (as UTF-8 bytes) in order
    assert isinstance(prev_hash, (bytes, bytearray)), 'prev_hash must be bytes'
    assert isinstance(transactions, list), 'transactions must be a list of strings'
    prefix_bytes = prev_hash + b''.join([t.encode('utf-8') for t in transactions])

    # Brute-force search for a nonce (as ASCII-encoded decimal) such that
    # SHA256(prefix_bytes + nonce).digest() has at least k trailing zero *bits*.
    i = 0
    while True:
        nonce = str(i).encode('utf-8')  # nonce must be bytes
        digest = hashlib.sha256(prefix_bytes + nonce).digest()

        # Count trailing zero bits (LSBs) in the digest, scanning from the last byte backwards
        tz = 0
        for b in reversed(digest):
            if b == 0:
                tz += 8
                continue
            # Add number of trailing zeros in this non-zero byte using bit trick: (b & -b)
            tz += ((b & -b).bit_length() - 1)
            break
        
        if tz >= k:
            break
        i += 1

    #####
    

    assert isinstance(nonce, bytes), 'nonce should be of type bytes'
    return nonce


def get_random_lines(filename, quantity):
    """
    This is a helper function to get the quantity of lines ("transactions")
    as a list from the filename given. 
    Do not modify this function
    """
    lines = []
    with open(filename, 'r') as f:
        for line in f:
            lines.append(line.strip())

    random_lines = []
    for x in range(quantity):
        random_lines.append(lines[random.randint(0, quantity - 1)])
    return random_lines


if __name__ == '__main__':
    # This code will be helpful for your testing
    filename = "bitcoin_text.txt"
    num_lines = 10  # The number of "transactions" included in the block

    # The "difficulty" level. For our blocks this is the number of Least Significant Bits
    # that are 0s. For example, if diff = 5 then the last 5 bits of a valid block hash would be zeros
    # The grader will not exceed 20 bits of "difficulty" because larger values take to long
    diff = 20

    transactions = get_random_lines(filename, num_lines)
    nonce = mine_block(diff, transactions)
    print(nonce)
