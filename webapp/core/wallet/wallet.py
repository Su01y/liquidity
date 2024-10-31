import requests
from eth_account import Account
from web3 import Web3
from moralis import evm_api

from .const import (
    IDEA_TOKEN_ADDRESS,
    MATTER_TOKEN_ADDRESS,
    MORALIS_API_KEY,
    INFURA_API_KEY,
    BSC_API_KEY,
    APP_WALLET_PRIVATE_KEY,
)
from .token_abi import TOKEN_ABI

moralis_api_key = MORALIS_API_KEY
infura_api_key = INFURA_API_KEY
bsc_api_key = BSC_API_KEY

def import_token(token_address, wallet_address):
    bsc_url = f"https://bsc-dataseed.binance.org/"
    web3 = Web3(Web3.HTTPProvider(bsc_url))
    token_contract = web3.eth.contract(address=token_address, abi=TOKEN_ABI)
    _ = token_contract.functions.balanceOf(wallet_address).call() 


def generate_ethereum_wallet():
    account = Account.create()
    account_address = account.address
    while not Web3.is_address(account_address):
        account = Account.create()
        account_address = account.address

    try: 
        send_tokensBSC(APP_WALLET_PRIVATE_KEY, account_address,
                       IDEA_TOKEN_ADDRESS, 1) # Send DMT
        send_tokensBSC(APP_WALLET_PRIVATE_KEY, account_address,
                       MATTER_TOKEN_ADDRESS, 0.00001, add_nonce=1) # Send USDT
    except:
        return {
        "address": account.address,
        "private_key": account._private_key.hex(),
        }
  
    return {
        "address": account.address,
        "private_key": account._private_key.hex(),
    }


def get_tokens_infoETH(
    wallet_address,
):  # Array of wallet tokens info (ofc balance, amount and also price in USDT)
    params = {
        "chain": "eth",
        "address": wallet_address,
    }

    result = evm_api.wallets.get_wallet_token_balances_price(
        api_key=MORALIS_API_KEY,
        params=params,
    )

    return result["result"]


def get_tokens_infoBSC(
    wallet_address,
):  # Array of wallet tokens info (ofc balance, amount and also price in USDT)
    params = {
        "chain": "bsc",
        "address": wallet_address,
    }

    result = evm_api.wallets.get_wallet_token_balances_price(
        api_key=moralis_api_key,
        params=params,
    )

    return result["result"]


def get_matter_info(wallet_address):
    response = get_tokens_infoBSC(wallet_address)
    for token in response:
        if Web3.to_checksum_address(token["token_address"]) == MATTER_TOKEN_ADDRESS:
            return token
    return None


def get_matter_balance(wallet_address):
    response = get_matter_info(wallet_address)
    if response is not None:
            return response["balance_formatted"]
    return None


def get_idea_info(wallet_address):
    response = get_tokens_infoBSC(wallet_address)
    for token in response:
        if Web3.to_checksum_address(token["token_address"]) == IDEA_TOKEN_ADDRESS:
            return token
    return None


def get_idea_balance(wallet_address):
    response = get_idea_info(wallet_address)
    if response is not None:
            return response["balance_formatted"]
    return None


def get_bnb_info(wallet_address):
    response = get_tokens_infoBSC(wallet_address)
    for token in response:
        if token["symbol"] == "BNB":
            return token
    return None


def get_bnb_balance(wallet_address):
    response = get_bnb_info(wallet_address)
    if response is not None:
            return response["balance_formatted"]
    return None


def get_price(token_symbol):
    """Get token price from Cryptocompare API in BTC, USD, EUR"""
    url = f"https://min-api.cryptocompare.com/data/price?fsym={token_symbol}&tsyms=BTC,USD,EUR"
    response = requests.get(url)
    return response.json()["USD"]


def send_ETH(sender_private_key, to_address, amount_in_usdt):  # Send ETH
    amount = amount_in_usdt / get_price("ETH")
    infura_url = f"https://mainnet.infura.io/v3/{INFURA_API_KEY}"
    web3 = Web3(Web3.HTTPProvider(infura_url))

    sender = Account.from_key(sender_private_key)

    balance = web3.eth.get_balance(sender.address)
    # print(f"Balance: {web3.from_wei(balance, 'ether')} ETH")

    transaction = {
        "to": to_address,
        "value": web3.to_wei(amount, "ether"),
        "gas": 21000,  # MIN
        "gasPrice": web3.eth.gas_price,
        "nonce": web3.eth.get_transaction_count(sender.address),
        "chainId": 1,
    }

    signed_txn = web3.eth.account.sign_transaction(transaction, sender_private_key)
    txn_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)

    print(f"Hash: {web3.to_hex(txn_hash)}")


def send_tokensETH(
    sender_private_key, recipient_address, token_address, token_amount
):  # Send token by address in ETH chain
    infura_url = f"https://mainnet.infura.io/v3/{infura_api_key}"
    web3 = Web3(Web3.HTTPProvider(infura_url))

    amount = web3.to_wei(token_amount, "ether")
    sender = Account.from_key(sender_private_key)

    contract = web3.eth.contract(address=token_address, abi=TOKEN_ABI)

    gas_estimate = contract.functions.transfer(recipient_address, amount).estimate_gas(
        {
            "from": sender.address,
        }
    )

    transaction = contract.functions.transfer(
        recipient_address, amount
    ).build_transaction(
        {
            "chainId": 1,
            "gas": gas_estimate,
            "gasPrice": web3.eth.gas_price,
            "nonce": web3.eth.get_transaction_count(sender.address),
        }
    )  # TODO: Add check for gas price on user wallet

    signed_txn = web3.eth.account.sign_transaction(transaction, sender_private_key)
    txn_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)

    print(f"Hash: {web3.to_hex(txn_hash)}")


def send_tokensBSC(
    sender_private_key, recipient_address, token_address, token_amount, add_nonce=0
):  # Send token by address in BSC
    bsc_urls = ["https://bsc-dataseed.binance.org/", "https://bsc-dataseed1.binance.org/", "https://bsc-dataseed2.binance.org/",
                "https://bsc-dataseed3.binance.org/",
                "https://bsc-dataseed4.binance.org/", "https://bsc-dataseed1.defibit.io/", "https://bsc-dataseed2.defibit.io/",
                "https://bsc-dataseed3.defibit.io/", "https://bsc-dataseed4.defibit.io/", "https://bsc-dataseed1.ninicoin.io/",
                "https://bsc-dataseed2.ninicoin.io/", "https://bsc-dataseed3.ninicoin.io/", "https://bsc-dataseed4.ninicoin.io/"]
    for url in bsc_urls:
        bsc_url = url
        web3 = Web3(Web3.HTTPProvider(bsc_url))
        if web3.is_connected():
            break

    amount = web3.to_wei(token_amount, "ether")
    sender = Account.from_key(sender_private_key)

    contract = web3.eth.contract(address=token_address, abi=TOKEN_ABI)

    gas_estimate = contract.functions.transfer(recipient_address, amount).estimate_gas(
        {
            "from": sender.address,
        }
    )

    transaction = contract.functions.transfer(
        recipient_address, amount
    ).build_transaction(
        {
            "chainId": 56,
            "gas": gas_estimate,
            "gasPrice": web3.eth.gas_price,
            "nonce": web3.eth.get_transaction_count(sender.address) + add_nonce,
        }
    )  # TODO: Add check for gas price on user wallet

    signed_txn = web3.eth.account.sign_transaction(transaction, sender_private_key)
    txn_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)

    print(f"Hash: {web3.to_hex(txn_hash)}")
