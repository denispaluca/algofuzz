from pathlib import Path
from algosdk import transaction, account
from algosdk.v2client import algod
import base64

from utils import get_accounts

algod_address = "http://localhost:4001"
algod_token = "a" * 64
algod_client = algod.AlgodClient(algod_token, algod_address)

info = algod_client.account_application_info("OK7NNBWAABFAZYNSOVMN5KDHHHK6JVVKYUFMDNLVABRFG25UUBPILIAXDY", 42)
print(info)