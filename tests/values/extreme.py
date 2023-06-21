from dotenv import load_dotenv
load_dotenv()

from json import dumps
from pyteal import *

from algofuzz.ContractState import ContractState
from algofuzz.FuzzAppClient import FuzzAppClient
from algofuzz.combined_fuzzers import PartialCombinedFuzzer, TotalCombinedFuzzer

"""
CONTRACT
"""

found = Bytes("found")


handle_creation = Seq(
    App.globalPut(found, Int(0)),
    Approve()
)

router = Router(
    "extreme_contract",
    BareCallActions(
    no_op=OnCompleteAction.create_only(handle_creation),
    opt_in=OnCompleteAction.call_only(Approve()),
    close_out=OnCompleteAction.always(Approve()),
    update_application=OnCompleteAction.never(),
    delete_application=OnCompleteAction.never()
    ),
    clear_state=Approve()
)


MAX8 = Int(2**8 - 1)
@router.method
def testMax8(v: abi.Uint8):
    return Seq(
        If(v.get() == MAX8,
            App.globalPut(found, Int(1))),
        Approve()
    )

MAX16 = Int(2**16 - 1)
@router.method
def testMax16(v: abi.Uint16):
    return Seq(
        If(v.get() == MAX16,
            App.globalPut(found, Int(1))),
        Approve()
    )

MAX32 = Int(2**32 - 1)
@router.method
def testMax32(v: abi.Uint32):
    return Seq(
        If(v.get() == MAX32,
            App.globalPut(found, Int(1))),
        Approve()
    )

MAX64 = Int(2**64 - 1)
@router.method
def testMax64(v: abi.Uint64):
    return Seq(
        If(v.get() == MAX64,
            App.globalPut(found, Int(1))),
        Approve()
    )

schema = (1,0,0,0)

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
    fuzzer = PartialCombinedFuzzer(FuzzAppClient.from_compiled(*compile()))
    n = fuzzer.start(eval, 1000)
    if n is None:
        print("Not found")
        return
    print(f"Found in {n} runs")


if(__name__ == "__main__"):
    main()