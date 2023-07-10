from typing import Literal
from dotenv import load_dotenv

load_dotenv()

from json import dumps
from pyteal import *

from algofuzz.ContractState import ContractState
from algofuzz.FuzzAppClient import FuzzAppClient

from algofuzz.fuzzers import TotalFuzzer
from algofuzz.fuzzers import TotalFuzzer

"""
CONTRACT
"""

found = Bytes("found")

handle_creation = Seq(
    App.globalPut(found, Int(0)),
    Approve()
)

router = Router(
    "sarray-mutations_contract",
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
def find(array: abi.DynamicBytes):
    return Seq(
        If(array.length() < Int(3))
            .Then(Approve()),
        If(array.get() == Bytes("abcdef123"))
            .Then(Approve()),
        array[Int(0)].use(
            lambda index1: If(index1.get() == Btoi(Bytes("a")))
                .Then(array[Int(1)].use(
                    lambda index2: If(index2.get() == Btoi(Bytes("b")))
                        .Then(array[Int(2)].use(
                            lambda index3: If(index3.get() == Btoi(Bytes("c")))
                                .Then(App.globalPut(found, Int(1)))))))),
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


if(__name__ == "__main__"):
    main()