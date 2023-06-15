from algofuzz.ContractState import ContractState


def evaluate(exec_account_address: str, contract: ContractState) -> bool:    
    return flag1_is_zero(contract)


def flag1_is_zero(contract: ContractState) -> bool:
    if not contract.exists_global('flag1'):
        return False
    
    flag1 = contract.get_global('flag1')
    cond = flag1 == 0
    return cond
