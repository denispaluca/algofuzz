from contract import ContractAccountState
from abc import ABC, abstractmethod

#class Property(ABC):
#    def __init__(self, key: str, contract: ContractAccountState) -> None:
#        self._contract = contract
#        self._key = key
#    
#    @abstractmethod
#    def check(self) -> bool:
#        pass
#
#class CounterPropertyCheck(Property):
#
#    def check(self) -> bool:
#        ...
#
#    
#
#class SetPropertyCheck(Property):
#
#    def check(self) -> bool:
#        ...
#
#
#
#bug_oracle: List[Property]


def evaluate(account_address: str, app_id: int) -> bool:
    contract = ContractAccountState(account_address, app_id)
    
    return count2_always1(contract)

def count2_always1(contract: ContractAccountState) -> bool:
    key = 'count2'
    if not contract.exists_global(key):
        return False
    

    count2 = contract.get_global(key)

    
    cond = count2 == 1

    if not cond:
        print("FAILEDDDDD")
    return cond
