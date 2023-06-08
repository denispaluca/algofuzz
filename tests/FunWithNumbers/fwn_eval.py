from src.ContractFuzzer import ContractState
from src.utils import get_account_balance

address = None
contract_address = None
sender_balance_old = None
contract_algos_old = None
key = 'balance'

def evaluate(exec_account_address: str, contract: ContractState) -> bool:   
    global address, contract_address 
    address = exec_account_address
    contract_address = contract._address

    if not contract.exists_local(address, key):
        return False
    
    if(sender_balance_old == None):
        load_balances(contract)
        return True
    
    cond = balance_increase(contract) or balance_decrease(contract)
    load_balances(contract)
    return cond
    

    

def load_balances(contract: ContractState):
    global sender_balance_old, contract_algos_old
    sender_balance_old = contract.get_local(address, key)
    contract_algos_old = get_account_balance(contract_address)


def balance_increase(contract: ContractState) -> bool:
    global sender_balance_old, contract_algos_old
    sender_balance_new = contract.get_local(address, key)
    contract_algos_new = get_account_balance(contract_address)
    return contract_algos_new >= contract_algos_old and sender_balance_new >= sender_balance_old

def balance_decrease(contract: ContractState) -> bool:
    global sender_balance_old, contract_algos_old
    sender_balance_new = contract.get_local(address, key)
    contract_algos_new = get_account_balance(contract_address)
    return contract_algos_new <= contract_algos_old and sender_balance_new <= sender_balance_old
