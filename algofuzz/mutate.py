import random
from algokit_utils import get_algod_client
from algosdk.abi import *

from algofuzz.utils import dispense, get_account_balance, get_funded_account

# uintN mutator
class UintMutator:
    min = 0
    def __init__(self, N: int = 64):
        self.N = N # bit size
        self.max = 2 ** N - 1 # largest value to mutate to
        self.mutations = [
            self.add,
            self.subtract,
            self.multiply,
            self.divide,
            self.bitwise_and,
            self.bitwise_or,
            self.bitwise_xor,
            self.random_bit_flip
        ]

    def seed(self):
        return 0

    def add(self, value: int):
        if(value == self.max):
            return self.subtract(value)
        
        return value + random.randint(1, self.max - value)
    
    def subtract(self, value: int):
        if(value == self.min):
            return self.add(value)
        
        return value - random.randint(1, value - self.min)
    
    def multiply(self, value: int):
        if(value == self.min):
            return self.add(value)
        
        if(value == self.max):
            return self.divide(value)
        
        return value * random.randint(1, self.max // value)
    
    def divide(self, value: int):
        if(value == self.min):
            return self.add(value)
        
        return value // random.randint(1, value)
    
    def random_bit_flip(self, value: int):
        return value ^ (1 << random.randint(self.min, self.N - 1))
    
    def bitwise_and(self, value: int):
        if(value == self.min):
            return self.add(value)
        return value & random.randint(self.min, self.max)
    
    def bitwise_or(self, value: int):
        return value | random.randint(self.min, self.max)
    
    def bitwise_xor(self, value: int):
        return value ^ random.randint(self.min, self.max)

    def mutate(self, value: int) -> int:
        mutation = random.choice(self.mutations)
        return mutation(value)    
    


# ufixedNxM mutator
class UFixedMutator(UintMutator):
    def __init__(self, N: int, M: int):
        super().__init__(N)
        self.M = M
        self.multiplier = 10 ** M
    

    def mutate(self, value: float):

        return super().mutate(int(value * self.multiplier)) / self.multiplier
    
class StringMutator:
    def __init__(self, max = 256) -> None:
        self.max = max # max length of string
        self.mutations = [
            self.remove_char,
            self.add_char,
            self.flip_char,
        ]

    def seed(self):
        return ""

    def remove_char(self, value: str)-> str:
        if(len(value) == 0):
            return self.add_char(value)
        index = random.randint(0, len(value) - 1)
        return value[:index] + value[index + 1:]
    
    def add_char(self, value: str)-> str:
        if(len(value) == self.max):
            return self.remove_char(value)
        index = random.randint(0, len(value))
        return value[:index] + chr(random.randint(0, 255)) + value[index:]
    
    def flip_char(self, value: str) -> str:
        if(len(value) == 0):
            return self.add_char(value)
        index = random.randint(0, len(value) - 1)
        return value[:index] + chr(random.randint(0, 255)) + value[index + 1:]
    
    def mutate(self, value: str):
        mutation = random.choice(self.mutations)
        return mutation(value)
    

class ByteMutator(UintMutator):
    def __init__(self) -> None:
        super().__init__(8)

class BoolMutator:
    def mutate(self, value: bool):
        return not value
    
    def seed(self):
        return False

class ArrayMutator:
    def __init__(self, arg: ArrayDynamicType, adr: str):
        self.min = 0
        self.max = 2048 // arg.child_type.byte_len()
        self.mutator = get_mutator(arg.child_type, adr)
        self.mutations = [
            self.add_element,
            self.remove_element,
            self.flip_element,
        ]

    def seed(self):
        return []

    def add_element(self, value: list):
        if(len(value) == self.max):
            return self.remove_element(value)

        index = random.randint(0, len(value))
        return value[:index] + [self.mutator.mutate(self.mutator.seed())] + value[index:]
    
    def remove_element(self, value: list):
        if(len(value) == self.min):
            return self.add_element(value)

        index = random.randint(0, len(value) - 1)
        return value[:index] + value[index + 1:]
    
    def flip_element(self, value: list):
        if(len(value) == 0):
            return self.add_element(value)

        index = random.randint(0, len(value) - 1)
        return value[:index] + [self.mutator.mutate(value[index])] + value[index + 1:]
    
    def mutate(self, value: list):
        mutation = random.choice(self.mutations)
        return mutation(value)
    

class ArrayStaticMutator(ArrayMutator):
    def __init__(self, arg: ArrayStaticType, adr: str):
        super().__init__(arg, adr)
        self.max = arg.static_length
        self.min = arg.static_length

    def seed(self):
        return [self.mutator.seed() for _ in range(self.max)]
    
    def mutate(self, value: list):
        return super().flip_element(value)
    
class TupleMutator:
    def __init__(self, args: TupleType, adr: str):
        self.args = args
        self.mutators = [get_mutator(arg, adr) for arg in args.child_types]

    def seed(self):
        return [mutator.seed() for mutator in self.mutators]

    def mutate(self, value: list):
        return [
            mutator.mutate(arg) 
            for mutator, arg 
            in zip(self.mutators, value)
        ]
    
class PaymentObject:
    def __init__(self, amount: int) -> None:
        self.amount = amount

    def __str__(self) -> str:
        return f"Pay {self.amount/1e7} Algos"
    
    def __repr__(self) -> str:
        return self.__str__()

class PaymentMutator:
    def __init__(self, addr: str) -> None:
        self.addr = addr

    def seed(self):
        return PaymentObject(0)
    
    def mutate(self, value: PaymentObject):
        balance, min_balance = get_account_balance(self.addr)
        if balance - min_balance < 1000:
            dispense(get_algod_client(), self.addr, int(2e8))
            balance, min_balance = get_account_balance(self.addr)
        
        half_max = (balance - min_balance - 1000) // 10
        
        value.amount = random.randint(0, half_max)
        return value

class AccountMutator:
    acc = get_funded_account(get_algod_client())[0]

    def seed(self):
        return self.acc
    
    def mutate(self, acc):
        return self.acc

def get_mutator(arg: ABIType | str, addr: str):
    if isinstance(arg, UintType):
        return UintMutator(arg.bit_size)
    elif isinstance(arg, UfixedType):
        return UFixedMutator(arg.bit_size, arg.precision)
    elif isinstance(arg, BoolType):
        return BoolMutator()
    elif isinstance(arg, StringType):
        return StringMutator()
    elif isinstance(arg, ByteType):
        return ByteMutator()
    elif isinstance(arg, ArrayDynamicType):
        return ArrayMutator(arg, addr)
    elif isinstance(arg, ArrayStaticType):
        return ArrayStaticMutator(arg, addr)
    elif isinstance(arg, TupleType):
        return TupleMutator(arg, addr)
    elif arg == 'pay':
        return PaymentMutator(addr)
    elif arg == 'account':
        return AccountMutator()
    else:
        return UintMutator(256)
    

class MethodMutator:
    def __init__(self, method: Method, addr: int) -> None:
        self._mutators = [get_mutator(arg.type, addr) for arg in method.args]
        
    def seed(self):
        return [mutator.seed() for mutator in self._mutators]
        
    def mutate(self, previous_args: list):
        if len(previous_args) == 0:
            return previous_args
        new_args = previous_args.copy()
        ranom_indicies = random.sample(range(len(self._mutators)), random.randint(1, len(self._mutators)))
        for index in ranom_indicies:
            new_args[index] = self._mutators[index].mutate(previous_args[index])

        return new_args

    