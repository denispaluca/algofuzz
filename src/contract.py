from algosdk import transaction, account, abi, atomic_transaction_composer, logic
import base64
from src.mutate import PaymentObject
from src.utils import get_algod_client, get_accounts, get_application_address

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


def compile_program(source: str):
    compile_response = algod_client.compile(source)
    return base64.b64decode(compile_response['result'])


def deploy(approval: str, clear: str, schema: list[int]) -> tuple[int, tuple[str, str]]:
    owner_acc = account.generate_account()
    private_key, address = owner_acc
    dispense(address)

    approval_program = compile_program(approval)
    clear_program = compile_program(clear)

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


def call(method: abi.Method, acc: tuple[str, str], app_id: int, args: list):
    private_key, address = acc
    sp = algod_client.suggested_params()
    atc = atomic_transaction_composer.AtomicTransactionComposer()

    tx_signer = atomic_transaction_composer.AccountTransactionSigner(private_key)
    args_with_payments = []
    for arg in args:
        if not isinstance(arg, PaymentObject):
            args_with_payments.append(arg)
            continue

        payment = transaction.PaymentTxn(address, sp, logic.get_application_address(app_id), arg.amount)
        args_with_payments.append(atomic_transaction_composer.TransactionWithSigner(payment, tx_signer))

    atc.add_method_call(
        app_id= app_id,
        method= method,
        sender= address,
        sp= sp,
        signer= tx_signer,
        method_args= args_with_payments
    )
    txns = atc.gather_signatures()

    dryrun_request = transaction.create_dryrun(algod_client, txns)
    dryrun_result = algod_client.dryrun(dryrun_request)
    dryrun_txns = dryrun_result['txns']


    # drr = dryrun_results.DryrunResponse(dryrun_result)

    coverage: list[int] = []
    for txn in dryrun_txns:
        if not ('app-call-messages' in txn or 'app-call-trace' in txn):
            continue

        msgs = txn['app-call-messages']
        if any([msg == 'REJECTED' for msg in msgs]):
            return None, coverage
        
        lines = txn['app-call-trace']
        for line in lines:
            coverage.append(line['line'])

    try:
        txid = algod_client.send_transactions(txns)
        result = transaction.wait_for_confirmation(algod_client, txid, 0)
    except Exception as e:
        return None, coverage
    
    return result, coverage

def opt_in(acc: tuple[str, str], app_id: int):
    private_key, address = acc
    sp = algod_client.suggested_params()
    optin_tx = transaction.ApplicationOptInTxn(address, sp, app_id)
    signed_tx = optin_tx.sign(private_key)
    txid = algod_client.send_transaction(signed_tx)
    result = transaction.wait_for_confirmation(algod_client, txid)
    return result


StateDict = dict[str | int, str | int]


def dict_list_to_set(dict_list: list[dict]) -> set[dict]:
    return set([frozenset(d.items()) for d in dict_list])


class ContractState:
    def __init__(self, app_id: int) -> None:
        self._app_id = app_id
        self._address = get_application_address(app_id)
        self._global_state: StateDict = {}
        self._local_state: dict[str, StateDict] = {}
        self._global_state_history: list[StateDict] = []
        self._local_state_history: dict[str, list[StateDict]] = {}
        self._creator: str = None

    def load(self, acc_address):
        self._load_global()
        self._load_local(acc_address)
        
    def _load_global(self):
        app_info = algod_client.application_info(self._app_id)
        params: dict = app_info.get('params')
        if not params:
            return
        
        self._creator = params.get('creator')
        global_state = params.get('global-state')
        if not global_state:
            return
        
        self._global_state = self.__decode_state(global_state)
        self._global_state_history.append(self._global_state)

    def _load_local(self, acc_address: str):
        account_info = algod_client.account_application_info(acc_address, self._app_id)
        data: dict = account_info.get('app-local-state')
        if not data:
            return
        
        local_state = data.get('key-value')
        if not local_state:
            return
        
        self._local_state[acc_address] = self.__decode_state(local_state)
        if(acc_address not in self._local_state_history):
            self._local_state_history[acc_address] = []
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

    def count_unique_global_states(self):
        return len(dict_list_to_set(self._global_state_history))

    def count_unique_local_states(self):
        result = 0
        for val in self._local_state_history.values():
            result += len(dict_list_to_set(val))
        return result

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
