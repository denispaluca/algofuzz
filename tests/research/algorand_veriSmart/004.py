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
standard = Bytes("standard")
name = Bytes("name")
symbol = Bytes("symbol")
decimals = Bytes("decimals")
total_supply = Bytes("total_supply")

"""LOCAL"""
balance_of = Bytes("balance_of")
allowance_for = Bytes("allowance_for")
allowance = Bytes("allowance")

handle_creation = Seq(
    App.globalPut(total_supply, Int(100000)),
    App.globalPut(standard, Bytes("Token 0.1")),
    App.globalPut(name, Bytes("TESTBtfund.ru")),
    App.globalPut(symbol, Bytes("TST")),
    App.globalPut(decimals, Int(0)),
    Approve()
)

handle_optin = Seq(
    If(Txn.sender() == Global.creator_address()).Then(
        App.localPut(Int(0), balance_of, Int(100000))
    ).Else(App.localPut(Int(0), balance_of, Int(0))),
    Approve()
)

router = Router(
    "MyToken_contract",
    BareCallActions(
    no_op=OnCompleteAction.create_only(handle_creation),
    opt_in=OnCompleteAction.call_only(handle_optin),
    close_out=OnCompleteAction.always(Approve()),
    update_application=OnCompleteAction.never(),
    delete_application=OnCompleteAction.never()
    ),
    clear_state=Approve()
)

@router.method
def transfer(to: abi.Account, value: abi.Uint64):
    return Seq(
        If(App.localGet(Int(0), balance_of) < value.get()).Then(Reject()),
        # check for overflow
        If(App.localGet(to.address(), balance_of) + value.get() < App.localGet(to.address(), balance_of)).Then(Reject()),
        App.localPut(Int(0), balance_of, App.localGet(Int(0), balance_of) - value.get()),
        App.localPut(to.address(), balance_of, App.localGet(to.address(), balance_of) + value.get()),
        Approve()
    )


@router.method
def approve(spender: abi.Account, value: abi.Uint64, *, output: abi.Bool):
    return Seq(
        App.localPut(Int(0), allowance_for, spender.address()),
        App.localPut(Int(0), allowance, value.get()),
        output.set(True)
    )

# @router.method
# def approveAndCall(spender: abi.Account, value: abi.Uint64, extra_data: Bytes):
#     return Seq(
#         App.localPut(Int(0), allowance_for, spender.address()),
#         App.localPut(spender.address(), allowance, value.get()),
#         App.localPut(spender.address(), Bytes("receive_token"), extra_data),
#         Approve()
#     )

def transfer_from(_from: abi.Account, to: abi.Account, value: abi.Uint64):
    return Seq(
        If(App.localGet(_from.address(), balance_of) < value.get()).Then(Reject()),
        # check for overflow
        If(App.localGet(to.address(), balance_of) + value.get() < App.localGet(to.address(), balance_of)).Then(Reject()),
        # check can transfer
        If(App.localGet(_from.address(), allowance_for) != to.address()).Then(Reject()),
        # check has enough allowance
        If(App.localGet(_from.address(), allowance) < value.get()).Then(Reject()),
        App.localPut(_from.address(), balance_of, App.localGet(_from.address(), balance_of) - value.get()),
        App.localPut(to.address(), balance_of, App.localGet(to.address(), balance_of) + value.get()),
        App.localPut(_from.address(), allowance, App.localGet(_from.address(), allowance) - value.get()),
        Approve()
    )

schema = (2,3,3,0)

def compile():
    approval, clear, contract = router.compile_program(version=8)
    return approval, clear, dumps(contract.dictify()), schema


"""
Execution
"""
def main():
    fuzzer = PartialFuzzer(FuzzAppClient.from_compiled(*compile()))
    n = fuzzer.start(runs=1000, driver=Driver.COVERAGE)


if(__name__ == "__main__"):
    main()