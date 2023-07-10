from dotenv import load_dotenv;
load_dotenv()


from json import dumps
from pyteal import *

from algofuzz.ContractState import ContractState
from algofuzz.FuzzAppClient import FuzzAppClient
from algofuzz.fuzzers import Driver, PartialFuzzer, TotalFuzzer

"""
CONTRACT
"""

ret = Bytes("ret")
z_ = Bytes("z")


handle_creation = Seq(
    App.globalPut(ret, Int(0)),
    App.globalPut(z_, Int(0)),
    Approve()
)

router = Router(
    "bar_contract",
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
def bar(w: abi.Uint64, x: abi.Uint64, y: abi.Uint64, z: abi.Uint64, a: abi.Uint64):
    reti = ScratchVar(TealType.uint64)
    return Seq(
        reti.store(Int(0)),
        If(x.get() % Int(2) == Int(0),
           Seq(
                reti.store(Int(256)),
                If(y.get() % Int(2) == Int(0),
                    reti.store(Int(257))),
                w.set(w.get() % reti.load()),
                While(w.get() != Int(0)).Do(
                    w.set(w.get() - Int(1)),
                ),
                z.set(z.get() % reti.load()),
                While(z.get() != reti.load()).Do(
                    z.set(z.get() + Int(1)),
                ),
            ),
            reti.store(Int(3) * a.get() *a.get() + Int(7) * a.get() + Int(101)),
        ),
        App.globalPut(ret, reti.load()),
        App.globalPut(z_, z.get()),
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
    ret = state.get_global("ret")
    z = state.get_global("z")
    return ret == z or ret != 5687


"""
Execution
"""
def main():
    fuzzer = TotalFuzzer(FuzzAppClient.from_compiled(*compile()))
    n = fuzzer.start(eval, 1000, Driver.COMBINED)
    


if(__name__ == "__main__"):
    main()