from typing import Literal
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
x = Bytes("x")

handle_creation = Seq(
    App.globalPut(found, Int(0)),
    App.globalPut(x, Int(123456)),
    Approve()
)

router = Router(
    "sarray_contract",
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
def find(array: abi.StaticArray[abi.Uint32, Literal[10]]):
    i = ScratchVar(TealType.uint64)
    return Seq(
        For(i.store(Int(0)), i.load() < array.length(), i.store(i.load() + Int(1))).Do(
            array[i.load()].use(
                lambda val: If(val.get() == App.globalGet(x), 
                    App.globalPut(found, Int(1))))
        ),
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
    fuzzer = TotalFuzzer(FuzzAppClient.from_compiled(*compile()))
    n = fuzzer.start(eval, 1000)
    if n is None:
        print("Not found")
        return
    print(f"Found in {n} runs")


if(__name__ == "__main__"):
    main()