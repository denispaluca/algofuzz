from dotenv import load_dotenv

from algofuzz.utils import get_account_balance
load_dotenv()

from json import dumps
from pyteal import *

from algofuzz.ContractState import ContractState
from algofuzz.FuzzAppClient import FuzzAppClient
from algofuzz.fuzzers import Driver, PartialFuzzer, TotalFuzzer
from algofuzz.fuzzers import TotalFuzzer

"""
CONTRACT
"""

"""GLOBAL"""
# Ownable
owner = Bytes("owner")
# ERC20Basic
total_supply = Bytes("total_supply")
# BasicToken
basis_points_rate = Bytes("basis_points_rate")
maximum_fee = Bytes("maximum_fee")
# Pausable
paused = Bytes("paused")
# Blacklist
## blacklisted_<address> shows the blacklist status x3
blacklisted = Bytes("blacklisted_")
# TetherToken
name = Bytes("name")
symbol = Bytes("symbol")
decimals = Bytes("decimals")



"""LOCAL"""
#BasicToken
balance_of = Bytes("balance_of")
#StandardToken
## allowed_<address> shows the allowance x3
allowed = Bytes("allowed_")



initial_supply = Int(100000000000)
handle_creation = Seq(
    App.globalPut(owner, Global.creator_address()),
    App.globalPut(paused, Int(0)),
    App.globalPut(name, Bytes("Algo Tether USD")),
    App.globalPut(symbol, Bytes("aUSDT")),
    App.globalPut(decimals, Int(6)),
    App.globalPut(total_supply, initial_supply),
    Approve()
)

handle_optin = Seq(
    If(Txn.sender() == Global.creator_address())
        .Then(App.localPut(Int(0), balance_of, initial_supply))
        .Else(App.localPut(Int(0), balance_of, Int(0))),
    Approve()
)

router = Router(
    "AlgoTether_contract",
    BareCallActions(
    no_op=OnCompleteAction.create_only(handle_creation),
    opt_in=OnCompleteAction.call_only(handle_optin),
    close_out=OnCompleteAction.always(Approve()),
    update_application=OnCompleteAction.never(),
    delete_application=OnCompleteAction.never()
    ),
    clear_state=Approve()
)

# Ownable
def only_owner():
    return If(Txn.sender() != App.globalGet(owner)).Then(Reject())

@router.method
def transfer_ownership(new_owner: abi.Account):
    return Seq(
        only_owner(),
        App.globalPut(owner, new_owner.address()),
        Approve()
    )

# BasicToken
@router.method
def transfer(to: abi.Account, value: abi.Uint64):
    fee = ScratchVar(TealType.uint64)
    send_amount = ScratchVar(TealType.uint64)
    return Seq(
        If(value.get() == Int(0)).Then(Reject()),
        fee.store(value.get() * App.globalGet(basis_points_rate) / Int(10000)),
        If(fee.load() > App.globalGet(maximum_fee)).Then(fee.store(App.globalGet(maximum_fee))),
        send_amount.store(value.get() - fee.load()),
        App.localPut(Int(0), balance_of, App.localGet(Int(0), balance_of) - value.get()),
        App.localPut(to.address(), balance_of, App.localGet(to.address(), balance_of) + send_amount.load()),
        If(fee.load() > Int(0)).Then(
            App.localPut(App.globalGet(owner), balance_of, App.localGet(App.globalGet(owner), balance_of) + fee.load())
        ),
        Approve()
    )



# StandardToken
@router.method
def transfer_from(from_: abi.Account, to: abi.Account, value: abi.Uint64):
    allowance = ScratchVar(TealType.uint64)
    fee = ScratchVar(TealType.uint64)
    send_amount = ScratchVar(TealType.uint64)
    return Seq(
        If(value.get() == Int(0)).Then(Reject()),
        fee.store(value.get() * App.globalGet(basis_points_rate) / Int(10000)),
        If(fee.load() > App.globalGet(maximum_fee)).Then(fee.store(App.globalGet(maximum_fee))),
        
        allowance.store(App.localGet(from_.address(), allowed_key())),
        
        App.localPut(from_.address(), allowed_key(), allowance.load() - value.get()),
        App.localPut(from_.address(), balance_of, App.localGet(from_.address(), balance_of) - value.get()),
        send_amount.store(value.get() - fee.load()),
        App.localPut(to.address(), balance_of, App.localGet(to.address(), balance_of) + send_amount.load()),
        If(fee.load() > Int(0)).Then(
            App.localPut(App.globalGet(owner), balance_of, App.localGet(App.globalGet(owner), balance_of) + fee.load())
        ),
        Approve()
    )

def allowed_key():
    return Concat(allowed, Txn.sender())

@router.method
def approve(spender: abi.Account, value: abi.Uint64):
    return Seq(
        App.localPut(Int(0), Concat(allowed, spender.address()), value.get()),
        Approve()
    )


# Pausable
def whenNotPaused():
    return If(App.globalGet(paused) != Int(0)).Then(Reject())

def whenPaused():
    return If(App.globalGet(paused) != Int(1)).Then(Reject())

@router.method
def pause():
    return Seq(
        only_owner(),
        whenNotPaused(),
        App.globalPut(paused, Int(1)),
        Approve()
    )

@router.method
def unpause():
    return Seq(
        only_owner(),
        whenPaused(),
        App.globalPut(paused, Int(0)),
        Approve()
    )

# Blacklist
@router.method
def add_blacklist(evilUser: abi.Account):
    return Seq(
        only_owner(),
        App.globalPut(Concat(blacklisted, evilUser.address()), Int(1)),
        Approve()
    )

@router.method
def remove_blacklist(clearedUser: abi.Account):
    return Seq(
        only_owner(),
        App.globalPut(Concat(blacklisted, clearedUser.address()), Int(0)),
        Approve()
    )

@router.method
def destroy_black_funds(blackListedUser: abi.Account):
    return Seq(
        only_owner(),
        If(App.globalGet(Concat(blacklisted, blackListedUser.address())) == Int(1))
            .Then(
                App.localPut(blackListedUser.address(), balance_of, Int(0)),
                App.globalPut(total_supply, App.globalGet(total_supply) - App.localGet(blackListedUser.address(), balance_of))
            ),
        Approve()
    )

# TetherToken
@router.method
def issue(amount: abi.Uint64):
    return Seq(
        only_owner(),
        If(App.globalGet(total_supply) + amount.get() < amount.get()).Then(Reject()),
        If(App.localGet(Int(0), balance_of) + amount.get() < amount.get()).Then(Reject()),
        App.localPut(Int(0), balance_of, App.localGet(Int(0), balance_of) + amount.get()),
        App.globalPut(total_supply, App.globalGet(total_supply) + amount.get()),
        Approve()
    )

@router.method
def redeem(amount: abi.Uint64):
    return Seq(
        only_owner(),
        If(App.globalGet(total_supply) < amount.get()).Then(Reject()),
        If(App.localGet(Int(0), balance_of) < amount.get()).Then(Reject()),
        App.localPut(Int(0), balance_of, App.localGet(Int(0), balance_of) - amount.get()),
        App.globalPut(total_supply, App.globalGet(total_supply) - amount.get()),
        Approve()
    )

schema = (8,3,4,0)

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
    fuzzer = PartialFuzzer(FuzzAppClient.from_compiled(*compile()))
    n = fuzzer.start(runs=1000, driver=Driver.COVERAGE)


if(__name__ == "__main__"):
    main()