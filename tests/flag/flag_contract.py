from pyteal import *
from json import dumps


handle_creation = Seq(
    App.globalPut(Bytes("flag0"), Int(0)),
    App.globalPut(Bytes("flag1"), Int(0)),
    Approve()
)

router = Router(
    "flag_contract",
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
def set1(val: abi.Uint64):
    return Seq(
        If(val.get() % Int(100) == Int(23),
            App.globalPut(Bytes('flag0'), Int(1))),

        Approve()
    )

@router.method
def set2(val: abi.Uint64):
    return Seq(
        If(And(
                val.get() % Int(10) == Int(5),
                App.globalGet(Bytes('flag0')) == Int(1)
            ),

            App.globalPut(Bytes('flag1'), Int(1))),

        Approve()
    )


schema = (2,0,0,0)

def compile():
    approval, clear, contract = router.compile_program(version=8)
    return approval, clear, dumps(contract.dictify()), schema
