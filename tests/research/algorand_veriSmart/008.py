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
name = Bytes("name")
symbol = Bytes("symbol")
decimals = Bytes("decimals")
version = Bytes("version")
total_supply = Bytes("total_supply")
owner = Bytes("owner")


"""LOCAL"""
balance_of = Bytes("balance_of")
allowance_for = Bytes("allowance_for")
allowance = Bytes("allowance")

handle_creation = Seq(
    App.globalPut(name, Bytes("ROUND")),
    App.globalPut(symbol, Bytes("ROUND")),
    App.globalPut(decimals, Int(6)),
    App.globalPut(version, Bytes("0.1")),
    App.globalPut(total_supply, Int(1000000000 * 10**6)),
    App.globalPut(owner, Global.creator_address()),

    Approve()
)

handle_optin = Seq(
    If(Txn.sender() == Global.creator_address()).Then(
        App.localPut(Int(0), balance_of, App.globalGet(total_supply))
    ).Else(App.localPut(Int(0), balance_of, Int(0))),
    Approve()
)

router = Router(
    "RoundToken_contract",
    BareCallActions(
    no_op=OnCompleteAction.create_only(handle_creation),
    opt_in=OnCompleteAction.call_only(handle_optin),
    close_out=OnCompleteAction.always(Approve()),
    update_application=OnCompleteAction.never(),
    delete_application=OnCompleteAction.never()
    ),
    clear_state=Approve()
)

@Subroutine(TealType.uint64)
def check_if_to_contract(to):
    return If(to == Global.current_application_address()).Then(
        Return(Int(1))
    ).Else(
        Return(Int(0))
    )

@router.method
def replace_owner(new_owner: abi.Account):
    return Seq(
        If(Txn.sender() != App.globalGet(owner)).Then(Reject()),
        App.globalPut(owner, new_owner.address()),
        Approve()
    )

@router.method
def transfer(to: abi.Account, value: abi.Uint64):
    return Seq(
        If(check_if_to_contract(to.address()) == Int(1)).Then(Reject()),
        If(value.get() <= Int(0)).Then(Reject()),
        If(App.localGet(Int(0), balance_of) < value.get()).Then(Reject()),
        App.localPut(Int(0), balance_of, App.localGet(Int(0), balance_of) - value.get()),
        App.localPut(to.address(), balance_of, App.localGet(to.address(), balance_of) + value.get()),
        Approve()
    )

@router.method
def transferFrom(_from: abi.Account, to: abi.Account, value: abi.Uint64):
    return Seq(
        If(check_if_to_contract(to.address()) == Int(1)).Then(Reject()),
        If(App.localGet(_from.address(), balance_of) < value.get()).Then(Reject()),
        If(App.localGet(_from.address(), allowance_for) != Txn.sender()).Then(Reject()),
        If(App.localGet(_from.address(), allowance) < value.get()).Then(Reject()),
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

# @router.method
# def approveAndCall(spender: abi.Account, value: abi.Uint64, extra_data: Bytes):
#     return Seq(
#         App.localPut(Int(0), allowance_for, spender.address()),
#         App.localPut(spender.address(), allowance, value.get()),
#         App.localPut(spender.address(), Bytes("receive_token"), extra_data),
#         Approve()
#     )

schema = (2,4,2,1)

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