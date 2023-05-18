from pathlib import Path
from algosdk import transaction, account, abi, atomic_transaction_composer, dryrun_results
import base64
from utils import get_algod_client, get_accounts

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


def call(method: abi.Method, acc: tuple[str, str], app_id: int, args):
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

    dryrun_request = transaction.create_dryrun(algod_client, txns)
    dryrun_result = algod_client.dryrun(dryrun_request)
    dryrun_txns = dryrun_result['txns']
    # drr = dryrun_results.DryrunResponse(dryrun_result)

    coverage: list[int] = []
    for txn in dryrun_txns:
        lines = txn['app-call-trace']
        for line in lines:
            coverage.append(line['line'])

    txid = algod_client.send_transactions(txns)
    result = transaction.wait_for_confirmation(algod_client, txid, 0)
    return result, coverage


StateDict = dict[str | int, str | int]


class ContractState:
    _global_state: StateDict
    _local_state: dict[str, StateDict] = {}
    _global_state_history: list[StateDict] = []
    _local_state_history: dict[str, list[StateDict]] = {}
    _creator: str
    _app_id: int

    def __init__(self, app_id: int) -> None:
        self._app_id = app_id

    def load(self, acc_address):
        data = algod_client.account_application_info(acc_address, self._app_id)
        app_data = data['created-app']
        self._creator = data['creator']
        if 'global-state' in app_data:
            self._global_state = self.__decode_state(app_data['global-state'])
            self._global_state_history.append(self._global_state)
        if 'local-state' in app_data:
            self._local_state[acc_address] = self.__decode_state(app_data['local-state'])
            self._local_state_history[acc_address].append(self._local_state[acc_address])

    def exists_global(self, key: str) -> bool:
        return key in self._global_state

    def get_global(self, key: str) -> str | int:
        return self._global_state[key]

    def get_global_history(self):
        return self._global_state_history.copy()

    def exists_local(self, account_address: str, key: str) -> bool:
        return key in self._local_state[account_address]

    def get_local(self, account_address: str, key: str) -> str | int:
        return self._local_state[account_address][key]

    def get_local_history(self):
        return self._local_state_history.copy()

    def get_creator(self):
        return self._creator

    @staticmethod
    def __decode_state(state_object) -> StateDict:
        state_dict: StateDict = {}
        for state in state_object:
            state_value = state['value']
            value = state_value['uint']
            if state_value['type'] != 2:
                value = state_value['bytes']

            state_dict[base64.b64decode(state['key']).decode()] = value

        return state_dict
