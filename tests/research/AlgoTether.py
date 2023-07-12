from dotenv import load_dotenv
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
total_issued = Bytes("total_issued")
paused = Bytes("paused")
issue_rate = Bytes("issue_rate")
redeem_rate = Bytes("redeem_rate")
spread = Int(20) # 5% spread or divided by 20

"""LOCAL"""
aUSDT_balance = Bytes("aUSDT_balance") # stored as mili aUSDT where 1 mili aUSDT = 0.001 aUSDT with 3 decimals


handle_creation = Seq(
    App.globalPut(total_issued, Int(0)),
    App.globalPut(paused, Int(0)),
    App.globalPut(issue_rate, Int(102)), # 1 Algo = 0.102 aUSDT or 1 microAlgo = 102 mili aUSDT
    App.globalPut(redeem_rate, Int(107)), # 
    Approve()
)

handle_optin = Seq(
    App.localPut(Int(0), aUSDT_balance, Int(0)),
    Approve()
)

router = Router(
    "AlgoTether_contract",
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

def pause_check():
    return If(App.globalGet(paused) == Int(1)).Then(Reject())

@router.method
def pause():
    return Seq(
        only_creator(),
        App.globalPut(paused, Int(1)),
        Approve()
    )

@router.method
def unpause():
    return Seq(
        only_creator(),
        App.globalPut(paused, Int(0)),
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

@router.method
def issue(payment: abi.PaymentTransaction):
    tether_to_issue = ScratchVar(TealType.uint64)
    payment_to_refund = ScratchVar(TealType.uint64)
    return Seq(
        pause_check(),
        payment_check(payment),
        tether_to_issue.store(payment.get().amount() / App.globalGet(issue_rate)),
        If(tether_to_issue.load() == Int(0)).Then(Reject()),
        payment_to_refund.store(payment.get().amount() - (tether_to_issue.load() * App.globalGet(issue_rate))),
        If(payment_to_refund.load() > Int(0)).Then(
            Seq(
                InnerTxnBuilder.Begin(),
                InnerTxnBuilder.SetFields({
                    TxnField.type_enum: TxnType.Payment,
                    TxnField.amount: payment_to_refund.load(),
                    TxnField.receiver: Txn.sender(),
                }),
            )
        ),
        App.globalPut(total_issued, App.globalGet(total_issued) + tether_to_issue.load()),
        App.localPut(Int(0), aUSDT_balance, App.localGet(Int(0), aUSDT_balance) + tether_to_issue.load()),
        Approve()
    )


def payment_check(payment: abi.PaymentTransaction):
    return Seq(
        If(payment.get().receiver() != Global.current_application_address()).Then(Reject()),
        If(payment.get().close_remainder_to() != Global.zero_address()).Then(Reject()),
        If(payment.get().amount() == Int(0)).Then(Reject())
    )

@router.method
def redeem(aUSDT_to_redeem: abi.Uint64):
    return Seq(
        pause_check(),
        If(aUSDT_to_redeem.get() == Int(0)).Then(Reject()),
        If(aUSDT_to_redeem.get() > App.localGet(Int(0), aUSDT_balance)).Then(Reject()),
        App.globalPut(total_issued, App.globalGet(total_issued) - aUSDT_to_redeem.get()),
        App.localPut(Int(0), aUSDT_balance, App.localGet(Int(0), aUSDT_balance) - aUSDT_to_redeem.get()),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.Payment,
            TxnField.amount: aUSDT_to_redeem.get() * App.globalGet(redeem_rate),
            TxnField.receiver: Txn.sender(),
        }),
        InnerTxnBuilder.Submit(),
        Approve()
    )

@router.method
def transfer(aUSDT_to_transfer: abi.Uint64, receiver: abi.Account):
    return Seq(
        pause_check(),
        If(aUSDT_to_transfer.get() == Int(0)).Then(Reject()),
        If(aUSDT_to_transfer.get() > App.localGet(Int(0), aUSDT_balance)).Then(Reject()),
        App.localPut(Int(0), aUSDT_balance, App.localGet(Int(0), aUSDT_balance) - aUSDT_to_transfer.get()),
        App.localPut(receiver.address(), aUSDT_balance, App.localGet(receiver.address(), aUSDT_balance) + aUSDT_to_transfer.get()),
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
    n = fuzzer.start(runs=1000)


if(__name__ == "__main__"):
    main()