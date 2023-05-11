from pathlib import Path
from algosdk import transaction, account, abi, atomic_transaction_composer
import base64
from utils import get_algod_client, get_accounts
from typing import Union
algod_client = get_algod_client()
accounts = get_accounts()
funding_account = accounts[0]

def dispense(addr):
    sp = algod_client.suggested_params()
    ptxn = transaction.PaymentTxn(
        funding_account.address, sp, addr, int(1e8)
    ).sign(funding_account.private_key)
    txid = algod_client.send_transaction(ptxn)
    transaction.wait_for_confirmation(algod_client, txid, 4)

def compile_program(source_path: Path):
    with open(source_path) as f:
        source_file = f.read()
    
    compile_response = algod_client.compile(source_file)
    return base64.b64decode(compile_response['result'])

def deploy(approval_path: Path, clear_path: Path, schema: list[int]):
    owner_acc = account.generate_account()
    private_key, address = owner_acc
    dispense(address)

    approval_program = compile_program(approval_path)
    clear_program = compile_program(clear_path)

    global_schema = transaction.StateSchema(num_uints=schema[0], num_byte_slices=schema[1])
    local_schema = transaction.StateSchema(num_uints=schema[2], num_byte_slices=schema[3])

    sp = algod_client.suggested_params()
    app_create_tx = transaction.ApplicationCreateTxn(
        sender=address,
        sp=sp,
        on_complete=transaction.OnComplete.NoOpOC,
        approval_program=approval_program, 
        clear_program=clear_program,
        global_schema=global_schema,
        local_schema=local_schema,
    )

    signed_tx = app_create_tx.sign(private_key=private_key)
    txid = algod_client.send_transaction(signed_tx)
    result = transaction.wait_for_confirmation(algod_client, txid, 2)
    return result['application-index'], owner_acc



def call(method: abi.Method, acc: tuple[str,str], app_id: int, args):
    private_key, address = acc
    sp = algod_client.suggested_params()
    atc = atomic_transaction_composer.AtomicTransactionComposer()
    tx_signer = atomic_transaction_composer.AccountTransactionSigner(private_key)
    atc.add_method_call(
        app_id, 
        method, 
        address, 
        sp, 
        tx_signer,
        args
    )
    txns = atc.gather_signatures()

    txid = algod_client.send_transactions(txns)
    result = transaction.wait_for_confirmation(algod_client, txid, 0)
    return result
    drr = transaction.create_dryrun(algod_client, txns)

    with open("dryrun.msgp", "wb") as f:
        f.write(base64.b64decode(encoding.msgpack_encode(drr)))


    dryrun_request = transaction.create_dryrun(algod_client, txns)

    # Pass dryrun request to algod server
    dryrun_result = algod_client.dryrun(dryrun_request)
    print(dryrun_result)
    drr = dryrun_results.DryrunResponse(dryrun_result)

    for txn in drr.txns:
        print(txn.app_trace())

DictStrInt = dict[Union[str, int], Union[str, int]]
class ContractAccountState:
    global_state: DictStrInt
    local_state: DictStrInt
    def __init__(self, acc_address: str, app_id: int) -> None:
        data = algod_client.account_application_info(acc_address, app_id)
        app_data = data['created-app']

        if 'global-state' in app_data:
            self.global_state = self.__decode_state(app_data['global-state'])

        if 'local-state' in app_data:
            self.local_state = self.__decode_state(app_data['local-state'])

    def exists_global(self, key: str) -> bool:
        return key in self.global_state
    
    def get_global(self, key: str) -> str | int:
        return self.global_state[key]
    
    def exists_local(self, key: str) -> bool:
        return key in self.local_state
    
    def get_local(self, key: str) -> str | int:
        return self.local_state[key]
    
    def __decode_state(self, state_object) -> DictStrInt:
        state_dict: DictStrInt = {}
        for state in state_object:
            state_value = state['value']
            value = state_value['uint']
            if state_value['type'] != 2:
                value = state_value['bytes']
            
            state_dict[base64.b64decode(state['key']).decode()] = value

        return state_dict

