import random
from algosdk.abi import *

# uintN mutator
class UintMutator:
    seed = 0
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
    seed = ""
    def __init__(self, max = 256) -> None:
        self.max = max # max length of string
        self.mutations = [
            self.remove_char,
            self.add_char,
            self.flip_char,
        ]

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
    seed = False
    def mutate(self, value: bool):
        return not value

class ArrayMutator:
    seed = []
    def __init__(self, arg: ArrayDynamicType):
        self.min = 0
        self.max = 2048 // arg.child_type.byte_len()
        self.mutator = get_mutator(arg.child_type)
        self.mutations = [
            self.add_element,
            self.remove_element,
            self.flip_element,
        ]

    def add_element(self, value: list):
        if(len(value) == self.max):
            return self.remove_element(value)

        index = random.randint(0, len(value))
        return value[:index] + [self.mutator.mutate(value[index])] + value[index:]
    
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
    def __init__(self, arg: ArrayStaticType):
        super().__init__(arg)
        self.max = arg.static_length
        self.min = arg.static_length
        self.seed = [self.mutator.seed for _ in range(arg.static_length)]
    
    def mutate(self, value: list):
        return super().flip_element(value)
    
class TupleMutator:
    def __init__(self, args: TupleType):
        self.seed = [get_mutator(arg.type).seed for arg in args.child_types]
        self.args = args
        self.mutators = [get_mutator(arg.type) for arg in args.child_types]

    def mutate(self, value: list):
        return [
            mutator.mutate(arg) 
            for mutator, arg 
            in zip(self.mutators, value)
        ]

def get_mutator(arg: ABIType):
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
        return ArrayMutator(arg)
    elif isinstance(arg, ArrayStaticType):
        return ArrayMutator(arg)
    elif isinstance(arg, TupleType):
        return TupleMutator(arg)
    else:
        return UintMutator(256)
    

class MethodMutator:
    def __init__(self, method: Method) -> None:
        self._mutators = [get_mutator(arg.type) for arg in method.args]
        
    def mutate(self, previous_args: list):
        return [
            mutator.mutate(arg) 
            for mutator, arg 
            in zip(self._mutators, previous_args)
        ]

    