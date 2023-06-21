from dotenv import load_dotenv
load_dotenv()

from json import dumps
from pyteal import *

from algofuzz.ContractState import ContractState
from algofuzz.FuzzAppClient import FuzzAppClient
from algofuzz.combined_fuzzers import TotalCombinedFuzzer

"""
CONTRACT
"""

found = Bytes("found")
other_state = Bytes("other_state")


handle_creation = Seq(
    App.globalPut(found, Int(0)),
    App.globalPut(other_state, Int(0)),
    Approve()
)

router = Router(
    "constants2_contract",
    BareCallActions(
    no_op=OnCompleteAction.create_only(handle_creation),
    opt_in=OnCompleteAction.call_only(Approve()),
    close_out=OnCompleteAction.always(Approve()),
    update_application=OnCompleteAction.never(),
    delete_application=OnCompleteAction.never()
    ),
    clear_state=Approve()
)

@router.method
def payable_method(payment: abi.PaymentTransaction):
    return Seq(
        Assert(payment.get().receiver() == Global.current_application_address()),
        Assert(payment.get().close_remainder_to() == Global.zero_address()),
        If(payment.get().amount() == Int(129),
            App.globalPut(found, Int(1))),
        Approve()
    )

@router.method
def other_function(uint: abi.Uint64):
    return Seq(
        App.globalPut(other_state, Int(1)),
        Approve()
    )

schema = (2,0,0,0)

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
    fuzzer = TotalCombinedFuzzer(FuzzAppClient.from_compiled(*compile()))
    n = fuzzer.start(eval, 1000)
    if n is None:
        print("Not found")
        return
    print(f"Found in {n} runs")


if(__name__ == "__main__"):
    main()