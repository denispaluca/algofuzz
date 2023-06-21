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

n = Bytes("n")



handle_creation = Seq(
    App.globalPut(n, Int(0)),
    Approve()
)

router = Router(
    "findSmall_contract",
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
def set(i: abi.Uint64):
    return Seq(
        App.globalPut(n, i.get()),
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
    n = state.get_global("n")
    return n - 256 != 31


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