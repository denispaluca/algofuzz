from dotenv import load_dotenv

from algofuzz.utils import get_account_balance
load_dotenv()

from json import dumps
from pyteal import *

from algofuzz.ContractState import ContractState
from algofuzz.FuzzAppClient import FuzzAppClient
from algofuzz.fuzzers import Driver, PartialFuzzer, TotalFuzzer
from algofuzz.fuzzers import TotalFuzzer

"""
CONTRACT
"""

"""GLOBAL"""
token1 = Bytes("token1")
token2 = Bytes("token2")
reserve1 = Bytes("reserve1")
reserve2 = Bytes("reserve2")
balance2 = Bytes("balance2")

paused = Bytes("paused")
issue_rate = Bytes("issue_rate")
redeem_rate = Bytes("redeem_rate")
spread = Int(20) # 5% spread or divided by 20

"""LOCAL"""
shares = Bytes("shares")
balance_of = Bytes("balance_of")

handle_creation = Seq(
    App.globalPut(token1, Bytes("ALGO")),
    App.globalPut(token2, Bytes("aUSDT")),
    App.globalPut(total_issued, Int(0)),
    App.globalPut(paused, Int(0)),
    App.globalPut(issue_rate, Int(105)), # 1 Algo = 0.105 aUSDT or 1 Algo = 105 mili aUSDT
    App.globalPut(redeem_rate, Int(115)), # 
    Approve()
)

handle_optin = Seq(
    App.localPut(Int(0), aUSD_balance, Int(0)),
    Approve()
)

router = Router(
    "ExchangeToken_contract",
    BareCallActions(
    no_op=OnCompleteAction.create_only(handle_creation),
    opt_in=OnCompleteAction.call_only(handle_optin),
    close_out=OnCompleteAction.always(Approve()),
    update_application=OnCompleteAction.never(),
    delete_application=OnCompleteAction.never()
    ),
    clear_state=Approve()
)

def only_creator():
    return If(Txn.sender() != Global.creator_address()).Then(Reject())

@router.method
def swap_algo(algos: abi.PaymentTransaction):
    amount_with_fee = ScratchVar(TealType.uint64)
    amount_out = ScratchVar(TealType.uint64)
    return Seq(
        If(algos.get().receiver() != Global.current_application_address()).Then(Reject()),
        If(algos.get().close_remainder_to() != Global.zero_address()).Then(Reject()),
        If(algos.get().amount() == Int(0)).Then(Reject()),
        amount_with_fee.store(algos.get().amount() * 997 / 1000),
        If(amount_with_fee.load() == Int(0)).Then(Reject()),
        amount_out.store(amount_with_fee.load() * App.globalGet(reserve2) / (App.globalGet(reserve1) + amount_with_fee.load())),
        If(amount_out.load() == Int(0)).Then(Reject()),
        If(amount_out.load() > App.globalGet(balance2)).Then(Reject()),
        App.globalPut(reserve1, App.globalGet(reserve1) + amount_with_fee.load()),
        App.globalPut(reserve2, App.globalGet(reserve2) - amount_out.load()),
        App.globalPut(balance2, App.globalGet(balance2) - amount_out.load()),
        Approve()
    )

@router.method
def swap_ausdt(amount: abi.Uint64):
    amount_with_fee = ScratchVar(TealType.uint64)
    amount_out = ScratchVar(TealType.uint64)
    return Seq(
        If(amount.get() == Int(0)).Then(Reject()),
        amount_with_fee.store(amount.get() * 997 / 1000),
        If(amount_with_fee.load() == Int(0)).Then(Reject()),
        amount_out.store(amount_with_fee.load() * App.globalGet(reserve1) / (App.globalGet(reserve2) + amount_with_fee.load())),
        If(amount_out.load() == Int(0)).Then(Reject()),
        App.globalPut(reserve2, App.globalGet(reserve2) + amount_with_fee.load()),
        App.globalPut(balance2, App.globalGet(balance2) + amount.get()),
        App.globalPut(reserve1, App.globalGet(reserve1) - amount_out.load()),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.Payment,
            TxnField.amount: amount_out.load(),
            TxnField.receiver: Txn.sender(),
        }),
        Approve()
    )



@router.method
def set_exchange_rate(new_rate: abi.Uint64):
    absolute_spread = ScratchVar(TealType.uint64)
    new_issue_rate = ScratchVar(TealType.uint64)
    return Seq(
        only_creator(),
        If(new_rate.get() == Int(0)).Then(Reject()),
        absolute_spread.store(new_rate.get() / spread),
        If(absolute_spread.load() == Int(0)).Then(Reject()),
        new_issue_rate.store(new_rate.get() - absolute_spread.load()),
        If(new_issue_rate.load() == Int(0)).Then(Reject()),
        App.globalPut(issue_rate, new_issue_rate.load()),
        App.globalPut(redeem_rate, new_rate.get() + absolute_spread.load()),
        Approve()
    )


microAlgosPerAlgo = Int(1000000)
@router.method
def buy(payment: abi.PaymentTransaction):
    tether_to_issue = ScratchVar(TealType.uint64)
    payment_to_refund = ScratchVar(TealType.uint64)
    acc_balance = ScratchVar(TealType.uint64)
    return Seq(
        payment_check(payment),
        tether_to_issue.store(payment.get().amount() * App.globalGet(issue_rate) / microAlgosPerAlgo),
        If(tether_to_issue.load() == Int(0)).Then(Reject()),
        App.globalPut(total_issued, App.globalGet(total_issued) + tether_to_issue.load()),
        App.localPut(Int(0), aUSD_balance, App.localGet(Int(0), aUSD_balance) + tether_to_issue.load()),
        
        # refund excess payment if possible
        payment_to_refund.store(payment.get().amount() - (tether_to_issue.load() * microAlgosPerAlgo / App.globalGet(issue_rate))),
        If(payment_to_refund.load() == Int(0)).Then(Approve()),
        acc_balance.store(Balance(Global.current_application_address())),
        If(acc_balance.load() < payment_to_refund.load() + MinBalance(Global.current_application_address()) + Global.min_txn_fee())
            .Then(Approve()),
        
        # there is enough balance to refund
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.Payment,
            TxnField.amount: payment_to_refund.load(),
            TxnField.receiver: Txn.sender(),
        }),
        InnerTxnBuilder.Submit(),
        Approve()
    )


def payment_check(payment: abi.PaymentTransaction):
    return Seq(
        If(payment.get().receiver() != Global.current_application_address()).Then(Reject()),
        If(payment.get().close_remainder_to() != Global.zero_address()).Then(Reject()),
        If(payment.get().amount() == Int(0)).Then(Reject())
    )

@router.method
def sell(aUSDT_to_redeem: abi.Uint64):
    micro_algo_to_redeem = ScratchVar(TealType.uint64)
    return Seq(
        If(aUSDT_to_redeem.get() == Int(0)).Then(Reject()),
        If(aUSDT_to_redeem.get() > App.localGet(Int(0), aUSD_balance)).Then(Reject()),
        micro_algo_to_redeem.store(aUSDT_to_redeem.get() * microAlgosPerAlgo / App.globalGet(redeem_rate)),
        If(micro_algo_to_redeem.load() == Int(0)).Then(Reject()),

        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.Payment,
            TxnField.amount: micro_algo_to_redeem.load(),
            TxnField.receiver: Txn.sender(),
        }),
        InnerTxnBuilder.Submit(),

        App.globalPut(total_issued, App.globalGet(total_issued) - aUSDT_to_redeem.get()),
        App.localPut(Int(0), aUSD_balance, App.localGet(Int(0), aUSD_balance) - aUSDT_to_redeem.get()),
        Approve()
    )

@router.method
def transfer(aUSD_to_transfer: abi.Uint64, receiver: abi.Account):
    return Seq(
        If(aUSD_to_transfer.get() == Int(0)).Then(Reject()),
        If(aUSD_to_transfer.get() > App.localGet(Int(0), aUSD_balance)).Then(Reject()),
        App.localPut(Int(0), aUSD_balance, App.localGet(Int(0), aUSD_balance) - aUSD_to_transfer.get()),
        App.localPut(receiver.address(), aUSD_balance, App.localGet(receiver.address(), aUSD_balance) + aUSD_to_transfer.get()),
        Approve()
    )


schema = (4,0,1,0)

def compile():
    approval, clear, contract = router.compile_program(version=8)
    return approval, clear, dumps(contract.dictify()), schema


"""
Evaluation / Property Test
"""
def eval(address: str, state: ContractState) -> bool:
    found = state.get_global("found")
    return found == 0 


"""
Execution
"""
def main():
    fuzzer = TotalFuzzer(FuzzAppClient.from_compiled(*compile()))
    n = fuzzer.start(runs=1000, driver=Driver.COMBINED)


if(__name__ == "__main__"):
    main()