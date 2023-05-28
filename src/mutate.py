import random

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

