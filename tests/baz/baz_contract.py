from pyteal import *
from json import dumps


handle_creation = Seq(
    App.globalPut(Bytes("state1"), Int(0)),
    App.globalPut(Bytes("state2"), Int(0)),
    App.globalPut(Bytes("state3"), Int(0)),
    App.globalPut(Bytes("state4"), Int(0)),
    App.globalPut(Bytes("state5"), Int(0)),
    Approve()
)

router = Router(
    "baz_contract",
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
def baz(a: abi.Uint64, b: abi.Uint64, c: abi.Uint64):
    d = ScratchVar(TealType.uint64)
    return Seq(
        d.store(b.get() + c.get()),
        If(d.load() < Int(1),
            Seq(
                If(b.get() < Int(3),
                    Seq(
                        App.globalPut(Bytes("state1"), Int(1)),
                        Approve())),

                If(a.get() < Int(42),
                    Seq(
                        App.globalPut(Bytes("state2"), Int(1)),
                        Approve())),

                App.globalPut(Bytes("state3"), Int(1)),
                Approve()),

            Seq(
                If(c.get() < Int(42),
                    Seq(
                        App.globalPut(Bytes("state4"), Int(1)),
                        Approve())),

                App.globalPut(Bytes("state1"), Int(1)),
                Approve())
        )
    )

schema = (5,0,0,0)

def compile():
    approval, clear, contract = router.compile_program(version=8)
    return approval, clear, dumps(contract.dictify()), schema
