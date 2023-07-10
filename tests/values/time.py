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

start = Bytes("start")
marked = Bytes("marked")



handle_creation = Seq(
    App.globalPut(start, Global.latest_timestamp()),
    App.globalPut(marked, Global.latest_timestamp()),
    Approve()
)

router = Router(
    "time_contract",
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
def mark():
    return Seq(
        App.globalPut(marked, Global.latest_timestamp()),
        Approve()
    )


schema = (2,0,0,0)

def compile():
    approval, clear, contract = router.compile_program(version=8)
    return approval, clear, dumps(contract.dictify()), schema


"""
Evaluation / Property Test
"""
def timepassed(address: str, state: ContractState) -> bool:
    start = state.get_global("start")
    marked = state.get_global("marked")
    return start == marked

def moretimepassed(address, state: ContractState):
    start = state.get_global("start")
    marked = state.get_global("marked")
    minute = 60 
    return start + minute > marked 


"""
Execution
"""
def main():
    fuzzer = TotalFuzzer(FuzzAppClient.from_compiled(*compile()))
    n = fuzzer.start(moretimepassed, 10000)
    if n is None:
        print("Not found")
        return
    print(f"Found in {n} runs")


if(__name__ == "__main__"):
    main()