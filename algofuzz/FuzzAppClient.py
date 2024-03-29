from algokit_utils import Account, ApplicationClient, get_algod_client
from algosdk import abi, atomic_transaction_composer, transaction

from algofuzz.mutate import AccountMutator, PaymentObject
from algofuzz.utils import create_app_spec
from algosdk.error import AlgodHTTPError

ASSERTION_FAIL_TEXT = 'assert failed'

class FuzzAppClient(ApplicationClient):

    @property
    def methods(self) -> list[abi.Method]:
        return self.app_spec.contract.methods
    
    @property
    def approval_disassembled(self) -> str:
        response = self.algod_client.disassemble(self.approval.raw_binary)
        result = response.get('result', '')
        return result.split('\n')
    
    @property
    def approval_line_count(self) -> int:
        return len(self.approval_disassembled)

    def opt_in_all(self) -> None:
        self.opt_in()
        creator = AccountMutator().seed()
        for account in AccountMutator.accs:
            if account.address == creator.address:
                continue

            self.change_sender(account)
            self.opt_in()

        self.change_sender(creator)
    
    def change_sender(self, account: Account) -> None:
        self.sender = account.address
        self.signer = account.signer

    def get_method(self, name: str) -> abi.Method:
        return self.app_spec.contract.get_method_by_name(name)
    
    def call(self, method: abi.Method, args: list):
        txns = self._prepare_txns(method, args)

        dryrun_request = transaction.create_dryrun(self.algod_client, txns)
        dryrun_result = self.algod_client.dryrun(dryrun_request)
        dryrun_txns = dryrun_result['txns']


        coverage: list[int] = []
        for txn in dryrun_txns:
            if not ('app-call-messages' in txn or 'app-call-trace' in txn):
                continue

            msgs = txn['app-call-messages']
            if any([msg == 'REJECT' for msg in msgs]):
                assertion_failed = self.foundAssertFail(msgs)
                return None, None, assertion_failed
            
            lines = txn['app-call-trace']
            for line in lines:
                coverage.append(line['line'])

        try:
            txid = self.algod_client.send_transactions(txns)
            result = transaction.wait_for_confirmation(self.algod_client, txid, 0)
        except AlgodHTTPError as e:
            return None, None, self.foundAssertFail(e.args)
        except Exception as e:
            return None, None, False
        
        return result, coverage, False

    @staticmethod
    def foundAssertFail(msgs):
        return any([ASSERTION_FAIL_TEXT in msg for msg in msgs])
    
    def call_no_cov(self, method, args):
        txns = self._prepare_txns(method, args)
        try:
            txid = self.algod_client.send_transactions(txns)
            result = transaction.wait_for_confirmation(self.algod_client, txid, 0)
        except AlgodHTTPError as e:
            return None, None, self.foundAssertFail(e.args)
        except Exception as e:
            return None, None, False
        
        return result, None, False

    def _prepare_txns(self, method, args):
        sp = self.algod_client.suggested_params()
        atc = atomic_transaction_composer.AtomicTransactionComposer()

        args_with_payments = []
        for arg in args:
            if isinstance(arg, PaymentObject):
                payment = transaction.PaymentTxn(self.sender, sp, self.app_address, arg.amount)
                args_with_payments.append(atomic_transaction_composer.TransactionWithSigner(payment, self.signer))
                continue

            if isinstance(arg, Account):
                args_with_payments.append(arg.address)
                continue

            args_with_payments.append(arg)


        atc.add_method_call(
            app_id= self.app_id,
            method= method,
            sender= self.sender,
            sp= sp,
            signer= self.signer,
            method_args= args_with_payments
        )
        txns = atc.gather_signatures()
        return txns
    
    @staticmethod
    def from_compiled(approval: str, clear: str, contract: str, schema) -> "FuzzAppClient":
        app_spec = create_app_spec(approval, clear, contract, schema)
        algod_client = get_algod_client()
        account = AccountMutator().seed()
        app_client = FuzzAppClient(
            algod_client, 
            app_spec, 
            sender= account.address, 
            signer= account.signer
        )
        return app_client