from algofuzz.ContractState import ContractState
from algofuzz.utils import get_account_balance

address = None
contract_address = None
sender_balance_old = 0
contract_algos_old = 0
key = 'balance'

def evaluate(exec_account_address: str, contract: ContractState) -> bool:   
    global address, contract_address, sender_balance_old, contract_algos_old, key
    address = exec_account_address
    contract_address = contract._address

    if not contract.exists_local(address, key):
        return False
    
    sender_balance_new = contract.get_local(address, key)
    contract_algos_new, _ = get_account_balance(contract_address)
    
    balance_increase = contract_algos_new > contract_algos_old and sender_balance_new > sender_balance_old
    balance_decrease = contract_algos_new < contract_algos_old and sender_balance_new < sender_balance_old
    balances_equal = contract_algos_new == contract_algos_old and sender_balance_new == sender_balance_old

    cond = balance_increase or balance_decrease or balances_equal
    
    if(not cond):
        x = 1

    sender_balance_old = sender_balance_new
    contract_algos_old = contract_algos_new

    return cond