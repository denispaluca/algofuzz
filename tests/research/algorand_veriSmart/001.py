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
allowance = Bytes("allowance")

handle_creation = Seq(
    App.globalPut(total_supply, Int(10000)),
    App.globalPut(standard, Bytes("Token 0.1")),
    App.globalPut(name, Bytes("megabank")),
    App.globalPut(symbol, Bytes("xUSD")),
    App.globalPut(decimals, Int(0)),
    Approve()
)

handle_optin = Seq(
    If(Txn.sender() == Global.creator_address()).Then(
        App.localPut(Int(0), balance_of, App.globalGet(total_supply))
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
def transfer(to: abi.Account, value: abi.Uint64, ):
    return Seq(
        If(App.localGet(Int(0), balance_of) < value.get()).Then(Reject()),
        # check for overflow
        If(App.localGet(to.address(), balance_of) + value.get() < App.localGet(to.address(), balance_of)).Then(Reject()),
        App.localPut(Int(0), balance_of, App.localGet(Int(0), balance_of) - value.get()),
        App.localPut(to.address(), balance_of, App.localGet(to.address(), balance_of) + value.get()),
        Approve()
    )


schema = (2,3,2,0)

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