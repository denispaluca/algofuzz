from algokit_utils import ApplicationClient, get_algod_client
from algosdk import abi, atomic_transaction_composer, transaction

from algofuzz.mutate import PaymentObject
from algofuzz.utils import create_app_spec, get_funded_account


class FuzzAppClient(ApplicationClient):

    @property
    def methods(self) -> list[abi.Method]:
        return self.app_spec.contract.methods
    
    def get_method(self, name: str) -> abi.Method:
        return self.app_spec.contract.get_method_by_name(name)
    
    def call(self, method: abi.Method, args: list):
        sp = self.algod_client.suggested_params()
        atc = atomic_transaction_composer.AtomicTransactionComposer()

        args_with_payments = []
        for arg in args:
            if not isinstance(arg, PaymentObject):
                args_with_payments.append(arg)
                continue

            payment = transaction.PaymentTxn(self.sender, sp, self.app_address, arg.amount)
            args_with_payments.append(atomic_transaction_composer.TransactionWithSigner(payment, self.signer))

        atc.add_method_call(
            app_id= self.app_id,
            method= method,
            sender= self.sender,
            sp= sp,
            signer= self.signer,
            method_args= args_with_payments
        )
        txns = atc.gather_signatures()

        dryrun_request = transaction.create_dryrun(self.algod_client, txns)
        dryrun_result = self.algod_client.dryrun(dryrun_request)
        dryrun_txns = dryrun_result['txns']


        coverage: list[int] = []
        for txn in dryrun_txns:
            if not ('app-call-messages' in txn or 'app-call-trace' in txn):
                continue

            msgs = txn['app-call-messages']
            if any([msg == 'REJECT' for msg in msgs]):
                return None, coverage
            
            lines = txn['app-call-trace']
            for line in lines:
                coverage.append(line['line'])

        try:
            txid = self.algod_client.send_transactions(txns)
            result = transaction.wait_for_confirmation(self.algod_client, txid, 0)
        except Exception as e:
            return None, coverage
        
        return result, coverage
    
    @staticmethod
    def from_compiled(approval: str, clear: str, contract: str, schema) -> "FuzzAppClient":
        app_spec = create_app_spec(approval, clear, contract, schema)
        algod_client = get_algod_client()
        account, signer = get_funded_account(algod_client)
        app_client = FuzzAppClient(
            algod_client, 
            app_spec, 
            sender= account.address, 
            signer= signer
        )
        return app_client