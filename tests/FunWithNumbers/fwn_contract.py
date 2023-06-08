from pyteal import *
from json import dumps


tokensPerAlgo = Int(10)
microAlgosPerAlgo = Int(1000000)
balance = Bytes("balance")

handle_creation = Seq(
    App.localPut(Int(0), balance, Int(0)),
    Approve()
)

router = Router(
    "fwn_contract",
    BareCallActions(
    no_op=OnCompleteAction.create_only(Approve()),
    opt_in=OnCompleteAction.call_only(handle_creation),
    close_out=OnCompleteAction.always(Approve()),
    update_application=OnCompleteAction.never(),
    delete_application=OnCompleteAction.never()
    ),
    clear_state=Approve()
)

@router.method
def buyTokens(payment: abi.PaymentTransaction):
    tokens = ScratchVar(TealType.uint64)
    return Seq(
        Assert(payment.get().amount() > Int(0)),
        Assert(payment.get().receiver() == Global.current_application_address()),
        Assert(payment.get().close_remainder_to() == Global.zero_address()),
        tokens.store(payment.get().amount() / microAlgosPerAlgo * tokensPerAlgo),
        App.localPut(Int(0), balance, App.localGet(Int(0), balance) + tokens.load()),

        Approve()
    )

@router.method
def sellTokens(tokens: abi.Uint64):
    return Seq(
        Assert(tokens.get() > Int(0)),
        Assert(tokens.get() <= App.localGet(Int(0), balance)),
        App.localPut(Int(0), balance, App.localGet(Int(0), balance) - tokens.get()),
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields({
            TxnField.type_enum: TxnType.Payment,
            TxnField.amount: tokens.get() * microAlgosPerAlgo / tokensPerAlgo,
            TxnField.receiver: Txn.sender(),
        }),
        InnerTxnBuilder.Submit(),
        Approve()
    )

schema = (0,0,1,0)

def compile():
    approval, clear, contract = router.compile_program(version=8)
    return approval, clear, dumps(contract.dictify()), schema




if __name__ == "__main__":
    import os
    import json

    path = os.path.dirname(os.path.abspath(__file__))
    approval, clear, contract = router.compile_program(version=8)

    # Dump out the contract as json that can be read in by any of the SDKs
    with open(os.path.join(path, "artifacts/contract.json"), "w") as f:
        f.write(json.dumps(contract.dictify(), indent=2))

    # Write out the approval and clear programs
    with open(os.path.join(path, "artifacts/approval.teal"), "w") as f:
        f.write(approval)

    with open(os.path.join(path, "artifacts/clear.teal"), "w") as f:
        f.write(clear)