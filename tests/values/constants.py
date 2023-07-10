from dotenv import load_dotenv
load_dotenv()

from json import dumps
from pyteal import *

from algofuzz.ContractState import ContractState
from algofuzz.FuzzAppClient import FuzzAppClient
from algofuzz.fuzzers import TotalFuzzer

"""
CONTRACT
"""

found = Bytes("found")
found_large = Bytes("found_large")



handle_creation = Seq(
    App.globalPut(found, Int(0)),
    App.globalPut(found_large, Int(0)),
    Approve()
)

router = Router(
    "constants_contract",
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
def find(i: abi.Uint64):
    return Seq(
        If(i.get() == Int(1447),
            App.globalPut(found, Int(1))),
        If(i.get() == Int(133700000000),
           App.globalPut(found, Int(0))),
        If(i.get() == Int(6352867677480783442),
           App.globalPut(found_large, Int(1))),
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
    found_large = state.get_global("found_large")
    return found == 0 and found_large == 0


"""
Execution
"""
def main():
    fuzzer = TotalFuzzer(FuzzAppClient.from_compiled(*compile()))
    n = fuzzer.start(eval, 1000)


if(__name__ == "__main__"):
    main()