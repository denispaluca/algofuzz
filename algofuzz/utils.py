import os
from dataclasses import dataclass
from typing import List
from algokit_utils import Account, ApplicationSpecification, CallConfig, get_algod_client

from algosdk import transaction, logic, abi
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

INDEXER_ADDRESS = "http://localhost"
INDEXER_TOKEN = "a" * 64
INDEXER_PORT = os.getenv("INDEXER_PORT", default="8980")
INDEXER_URL = f"{INDEXER_ADDRESS}:{INDEXER_PORT}"


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
    address: str
) -> tuple[int,int]:
    """returns the balance of an account"""
    algod_client = get_algod_client()
    account_info = algod_client.account_info(address)
    min_balance = account_info.get("min-balance")
    return account_info.get("amount"), min_balance


def get_application_address(
    app_id: int
) -> str:
    """returns the address of an application given its id"""
    return logic.get_application_address(app_id)


def dispense(algod_client: algod.AlgodClient, address: str, amount: int) -> None:
    sp = algod_client.suggested_params()
    accounts = get_accounts()
    dispenser = accounts[0]
    ptxn = transaction.PaymentTxn(
        sender=dispenser.address, sp=sp, receiver=address, amt=amount
    ).sign(dispenser.private_key)
    txid = algod_client.send_transaction(ptxn)
    transaction.wait_for_confirmation(algod_client, txid, 0)

def get_funded_account(algod_client: algod.AlgodClient) -> tuple[Account, AccountTransactionSigner]:
    account = Account.new_account()
    dispense(algod_client, account.address, int(2e8))
    return account, AccountTransactionSigner(account.private_key)
    
def create_app_spec(approval: str, clear: str, contract: str, schema: tuple[int, int, int, int]) -> ApplicationSpecification:
    return ApplicationSpecification(
        approval_program=approval,
        clear_program=clear,
        contract=abi.Contract.from_json(contract),
        global_state_schema=transaction.StateSchema(schema[0], schema[1]),
        local_state_schema=transaction.StateSchema(schema[2], schema[3]),
        hints={},
        schema={},
        bare_call_config={
            "no_op": CallConfig.CREATE,
            "opt_in": CallConfig.CALL
        },
    )
