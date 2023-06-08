import os
import base64
from dataclasses import dataclass
from typing import List

from algosdk import transaction, logic
from algosdk.v2client import algod, indexer
from algosdk.atomic_transaction_composer import AccountTransactionSigner
from algosdk.kmd import KMDClient
from algosdk.wallet import Wallet

KMD_ADDRESS = "http://localhost"
KMD_TOKEN = "a" * 64
KMD_PORT = os.getenv("KMD_PORT", default="4002")
KMD_URL = f"{KMD_ADDRESS}:{KMD_PORT}"

DEFAULT_KMD_WALLET_NAME = "unencrypted-default-wallet"
DEFAULT_KMD_WALLET_PASSWORD = ""

ALGOD_ADDRESS = "http://localhost"
ALGOD_TOKEN = "a" * 64
ALGOD_PORT = os.getenv("ALGOD_PORT", default="4001")
ALGOD_URL = f"{ALGOD_ADDRESS}:{ALGOD_PORT}"

INDEXER_ADDRESS = "http://localhost"
INDEXER_TOKEN = "a" * 64
INDEXER_PORT = os.getenv("INDEXER_PORT", default="8980")
INDEXER_URL = f"{INDEXER_ADDRESS}:{INDEXER_PORT}"


def get_algod_client(
    addr: str = ALGOD_URL, token: str = ALGOD_TOKEN
) -> algod.AlgodClient:
    return algod.AlgodClient(algod_token=token, algod_address=addr)


def get_kmd_client(addr: str = KMD_URL, token: str = KMD_TOKEN) -> KMDClient:
    """creates a new kmd client using the default sandbox parameters"""
    return KMDClient(kmd_token=token, kmd_address=addr)


def get_indexer_client(
    addr: str = INDEXER_URL, token: str = INDEXER_TOKEN
) -> indexer.IndexerClient:
    """creates a new indexer client using the default sandbox parameters"""
    return indexer.IndexerClient(indexer_token=token, indexer_address=addr)


def get_sandbox_default_wallet() -> Wallet:
    """returns the default sandbox kmd wallet"""
    return Wallet(
        wallet_name=DEFAULT_KMD_WALLET_NAME,
        wallet_pswd=DEFAULT_KMD_WALLET_PASSWORD,
        kmd_client=get_kmd_client(),
    )


@dataclass
class SandboxAccount:
    """SandboxAccount is a simple dataclass to hold a sandbox account details"""

    #: The address of a sandbox account
    address: str
    #: The base64 encoded private key of the account
    private_key: str
    #: An AccountTransactionSigner that can be used as a TransactionSigner
    signer: AccountTransactionSigner


def get_accounts(
    kmd_address: str = KMD_URL,
    kmd_token: str = KMD_TOKEN,
    wallet_name: str = DEFAULT_KMD_WALLET_NAME,
    wallet_password: str = DEFAULT_KMD_WALLET_PASSWORD,
) -> List[SandboxAccount]:
    """gets all the accounts in the sandbox kmd, defaults
    to the `unencrypted-default-wallet` created on private networks automatically
    """

    kmd = KMDClient(kmd_token, kmd_address)
    wallets = kmd.list_wallets()

    wallet_id = None
    for wallet in wallets:
        if wallet["name"] == wallet_name:
            wallet_id = wallet["id"]
            break

    if wallet_id is None:
        raise Exception("Wallet not found: {}".format(wallet_name))

    wallet_handle = kmd.init_wallet_handle(wallet_id, wallet_password)

    try:
        addresses = kmd.list_keys(wallet_handle)
        private_keys = [
            kmd.export_key(wallet_handle, wallet_password, addr)
            for addr in addresses
        ]
        kmd_accounts = [
            SandboxAccount(
                addresses[i],
                private_keys[i],
                AccountTransactionSigner(private_keys[i]),
            )
            for i in range(len(private_keys))
        ]
    finally:
        kmd.release_wallet_handle(wallet_handle)

    return kmd_accounts


def get_account_balance(
    address: str,
    algod_address: str = ALGOD_URL,
    algod_token: str = ALGOD_TOKEN,
) -> int:
    """returns the balance of an account"""
    algod_client = algod.AlgodClient(algod_token, algod_address)
    account_info = algod_client.account_info(address)
    return account_info.get("amount")


def get_application_address(
    app_id: int
) -> str:
    """returns the address of an application given its id"""
    return logic.get_application_address(app_id)