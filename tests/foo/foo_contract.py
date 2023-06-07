from pyteal import *
from json import dumps


x = Bytes("x")
y = Bytes("y")
state = Bytes("state")
handle_creation = Seq(
    App.globalPut(x, Int(0)),
    App.globalPut(y, Int(0)),
    App.globalPut(state, Int(0)),
    Approve()
)

router = Router(
    "foo_contract",
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
def Bar():
    return Seq(
        If(App.globalGet(x) == Int(42),
           App.globalPut(state, Int(1))),

        Approve()
    )

@router.method
def SetY(val: abi.Uint64):
    return Seq(
        App.globalPut(y, val.get()),
        Approve()
    )

@router.method
def IncX():
    return Seq(
        App.globalPut(x, App.globalGet(x) + Int(1)),
        Approve()
    )

@router.method
def CopyY():
    return Seq(
        App.globalPut(x, App.globalGet(y)),
        Approve()
    )


schema = (3,0,0,0)

def compile():
    approval, clear, contract = router.compile_program(version=8)
    return approval, clear, dumps(contract.dictify()), schema
