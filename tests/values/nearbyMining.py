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

x = Bytes("x")



handle_creation = Seq(
    App.globalPut(x, Int(0)),
    Approve()
)

router = Router(
    "nearby_contract",
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
def set(v: abi.Uint64):
    return Seq(
        App.globalPut(x, v.get()),
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
    x = state.get_global("x")
    if x <= 181888880989308019:
        return True
    
    if x >= 181888880989308021:
        return True
    
    return False


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