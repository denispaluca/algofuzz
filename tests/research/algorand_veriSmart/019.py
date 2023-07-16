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
owner = Bytes("owner")
start_time = Bytes("start_time")
burned = Bytes("burned")


"""LOCAL"""
balance_of = Bytes("balance_of")
allowance_for = Bytes("allowance_for")
allowance = Bytes("allowance")


initial_supply = Int(500000000)
handle_creation = Seq(
    App.globalPut(standard, Bytes("ERC20")),
    App.globalPut(name, Bytes("Edgeless")),
    App.globalPut(symbol, Bytes("EDG")),
    App.globalPut(decimals, Int(0)),
    App.globalPut(total_supply, initial_supply),
    App.globalPut(owner, Global.creator_address()),
    App.globalPut(start_time, Int(1490112000)),
    App.globalPut(burned, Int(0)),

    Approve()
)

handle_optin = Seq(
    If(Txn.sender() == Global.creator_address()).Then(
        App.localPut(Int(0), balance_of, initial_supply)
    ).Else(App.localPut(Int(0), balance_of, Int(0))),
    Approve()
)

router = Router(
    "RiptoBuxToken_contract",
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
        If(Global.latest_timestamp() < App.globalGet(start_time)).Then(Reject() ),
        # prevent owner from spending in first year
        If(Txn.sender() == App.globalGet(owner) and Global.latest_timestamp() < App.globalGet(start_time) + Int(31536000) and App.localGet(Int(0), balance_of) - value.get() < initial_supply).Then(Reject()),
        App.localPut(Int(0), balance_of, App.localGet(Int(0), balance_of) - value.get()),
        App.localPut(to.address(), balance_of, App.localGet(to.address(), balance_of) + value.get()),
        Approve()
    )

@router.method
def transferFrom(_from: abi.Account, to: abi.Account, value: abi.Uint64):
    return Seq(
        If(Global.latest_timestamp() < App.globalGet(start_time) and _from.address() != App.globalGet(owner)).Then(Reject()),
        If(Txn.sender() == App.globalGet(owner) and Global.latest_timestamp() < App.globalGet(start_time) + Int(31536000) and App.localGet(Int(0), balance_of) - value.get() < initial_supply).Then(Reject()),
        If(App.localGet(_from.address(), allowance_for) != Txn.sender()).Then(Reject()),
        App.localPut(_from.address(), balance_of, App.localGet(_from.address(), balance_of) - value.get()),
        App.localPut(to.address(), balance_of, App.localGet(to.address(), balance_of) + value.get()),
        App.localPut(_from.address(), allowance, App.localGet(_from.address(), allowance) - value.get()),
        Approve()
    )

@router.method
def approve(spender: abi.Account, value: abi.Uint64, *, output: abi.Bool):
    return Seq(
        App.localPut(Int(0), allowance_for, spender.address()),
        App.localPut(Int(0), allowance, value.get()),
        output.set(True)
    )

@router.method
def burn():
    difference = ScratchVar()
    return Seq(
        If(App.globalGet(burned) == Int(0)).Then(Reject()),
        If(Global.latest_timestamp() < App.globalGet(start_time)).Then(Reject()),
        difference.store(App.localGet(App.globalGet(owner), balance_of) - Int(60000000)),
        App.localPut(App.globalGet(owner), balance_of, Int(60000000)),
        App.globalPut(total_supply, App.globalGet(total_supply) - difference.load()),
        App.globalPut(burned, Int(1)),
        Approve()
    )

# @router.method
# def approveAndCall(spender: abi.Account, value: abi.Uint64, extra_data: Bytes):
#     return Seq(
#         App.localPut(Int(0), allowance_for, spender.address()),
#         App.localPut(spender.address(), allowance, value.get()),
#         App.localPut(spender.address(), Bytes("receive_token"), extra_data),
#         Approve()
#     )

schema = (4,4,2,1)

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