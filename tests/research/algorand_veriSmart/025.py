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
owner = Bytes("owner")

"""LOCAL"""
balance_of = Bytes("balance_of")

handle_creation = Seq(
    App.globalPut(owner, Global.creator_address()),
    Approve()
)

handle_optin = Seq(
    If(Txn.sender() == Global.creator_address()).Then(
        App.localPut(Int(0), balance_of, Int(1000))
    ).Else(App.localPut(Int(0), balance_of, Int(0))),
    Approve()
)

router = Router(
    "TestingToken_contract",
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
def send(to: abi.Account, value: abi.Uint64, ):
    return Seq(
        If(App.localGet(Int(0), balance_of) < value.get()).Then(Reject()),
        # check for overflow
        If(App.localGet(to.address(), balance_of) + value.get() < App.localGet(to.address(), balance_of)).Then(Reject()),
        If(value.get() < Int(0)).Then(Reject()),
        App.localPut(Int(0), balance_of, App.localGet(Int(0), balance_of) - value.get()),
        App.localPut(to.address(), balance_of, App.localGet(to.address(), balance_of) + value.get()),
        Approve()
    )


schema = (0,1,1,0)

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