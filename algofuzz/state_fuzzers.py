import hashlib
import json
import pickle
import random
from typing import Callable, Set, Union, Sequence, Dict, List
from algosdk import (abi)
from algofuzz.FuzzAppClient import FuzzAppClient
from algofuzz.CoverageHistory import CoverageHistory

from algofuzz.mutate import MethodMutator
from algofuzz.ContractState import ContractState

class Seed:
    """Represent an input with additional attributes"""

    def __init__(self, data) -> None:
        """Initialize from seed data"""
        self.data = data

        self.transition: tuple[dict,dict] = None
        self.distance: Union[int, float] = -1
        self.energy = 0.0

    def __str__(self):
        """Returns data as string representation of the seed"""
        return self.data.__str__()

    __repr__ = __str__




def get_transition_id(transition: tuple[dict, dict]) -> str:
    pickled = json.dumps(transition, sort_keys=True).encode()
    return hashlib.md5(pickled).hexdigest()

class PowerSchedule:
    def __init__(self, exponent: int = 5) -> None:
        self.transition_frequency: Dict = {}
        self.exponent = exponent

    def assignEnergy(self, population: Sequence[Seed]) -> None:
        for seed in population:
            path_id = get_transition_id(seed.transition)
            if path_id not in self.transition_frequency:
                self.transition_frequency[path_id] = 1
            
            seed.energy = 1 / (self.transition_frequency[path_id] ** self.exponent)

    def normalizedEnergy(self, population: Sequence[Seed]) -> List[float]:
        energy = list(map(lambda seed: seed.energy, population))
        sum_energy = sum(energy)  
        assert sum_energy != 0
        norm_energy = list(map(lambda nrg: nrg / sum_energy, energy))
        return norm_energy

    def choose(self, population: Sequence[Seed]) -> Seed:
        self.assignEnergy(population)
        norm_energy = self.normalizedEnergy(population)
        seed: Seed = random.choices(population, weights=norm_energy)[0]
        return seed
    
    def addTransition(self, transition: tuple[dict, dict]) -> bool:
        transition_id = get_transition_id(transition)
        if transition_id not in self.transition_frequency:
            self.transition_frequency[transition_id] = 1
            return True
        
        self.transition_frequency[transition_id] += 1
        return False


class MethodFuzzer:
    def __init__(self, method: abi.Method, addr: str):
        self.method = method
        self.mutator = MethodMutator(method, addr)
        self.seeds = [self.mutator.seed()]
        self.seed_index = 0
        self.population = []
        self.inputs = []
        self.schedule = PowerSchedule()
        
    def create_candidate(self):
        """Returns an input generated by fuzzing a seed in the population"""
        candidate = None
        if len(self.population) > 0:
            seed = self.schedule.choose(self.population)
            candidate = seed.data
        else:
            candidate = random.choice(self.inputs)

        # Stacking: Apply multiple mutations to generate the candidate
        trials = min(len(candidate), 1 << random.randint(1, 5))
        for i in range(trials):
            candidate = self.mutator.mutate(candidate)
        return candidate
    
    def update(self, transition: tuple[dict, dict] ) -> None:
        is_new = self.schedule.addTransition(transition)

        if is_new:
            seed = Seed(self.inp)
            seed.transition = transition
            self.population.append(seed)

    def fuzz(self):
        if self.seed_index < len(self.seeds):
            # Still seeding
            self.inp = self.seeds[self.seed_index]
            self.seed_index += 1
        else:
            # Mutating
            self.inp = self.create_candidate()

        self.inputs.append(self.inp)
        return self.inp

class PartialStateFuzzer:
    def __init__(self, app_client: FuzzAppClient):
        self.app_client = app_client

    def start(self, eval: Callable[[str, ContractState], bool], runs: int = 100):
        self.app_client.create()
        self.app_client.opt_in()
        self.contract_state = ContractState(self.app_client.app_id)
        self.contract_state.load(self.app_client.sender)

        self.method_fuzzers = {method.name: MethodFuzzer(method, self.app_client.sender) for method in self.app_client.methods}

        print(f"Fuzzing contract {self.app_client.app_name} (id: {self.app_client.app_id}) from account {self.app_client.sender}")

        return self._fuzz(eval, runs)
    
    def _fuzz_method(self, method: abi.Method):
        print(f"Calling {method.name} with input:")
        method_fuzzer = self.method_fuzzers[method.name]
        input = method_fuzzer.fuzz()
        print(input)

        res = self.app_client.call_no_cov(method, input)
        transition = self.contract_state.load(self.app_client.sender)
        method_fuzzer.update(transition)
            
    def _fuzz(self, eval: Callable[[str, ContractState], bool], runs: int = 1000) -> int | None:
        for i in range(runs):
            method = random.choice(self.app_client.methods)
            self._fuzz_method(method)
            res = eval(self.app_client.sender, self.contract_state)

            if not res:
                return i

    
class TotalStateFuzzer:
    def __init__(self, app_client: FuzzAppClient):
        self.app_client = app_client

    
    def mutate(self, value: tuple[str, list]):
        method, args = value
        mutator = self.method_mutators[method]
        return (method, mutator.mutate(args))

    def create_candidate(self) -> tuple[str, list]:
        """Returns an input generated by fuzzing a seed in the population"""
        candidate = None
        if len(self.population) > 0:
            seed = self.schedule.choose(self.population)
            candidate = seed.data
        else:
            candidate = random.choice(self.inputs)

        # Stacking: Apply multiple mutations to generate the candidate
        trials = min(len(candidate), 1 << random.randint(1, 5))
        for i in range(trials):
            candidate = self.mutate(candidate)
        return candidate
    
    def fuzz(self):
        if self.seed_index < len(self.seeds):
            # Still seeding
            self.inp = self.seeds[self.seed_index]
            self.seed_index += 1
        else:
            # Mutating
            self.inp = self.create_candidate()

        self.inputs.append(self.inp)
        return self.inp
    

    def start(self, eval: Callable[[str, ContractState], bool], runs: int = 100) -> int | None:
        self.app_client.create()
        self.app_client.opt_in()
        
        self.contract_state = ContractState(self.app_client.app_id)
        self.contract_state.load(self.app_client.sender)

        self.method_mutators = {method.name: MethodMutator(method, self.app_client.sender) for method in self.app_client.methods}
        self.seeds = [(method.name, self.method_mutators[method.name].seed()) for method in self.app_client.methods]
        self.seed_index = 0
        self.population: list[Seed] = []
        self.inputs = []
        self.schedule = PowerSchedule()

        print(f"Fuzzing contract {self.app_client.app_name} (id: {self.app_client.app_id}) from account {self.app_client.sender}")

        for i in range(runs):
            self._call()
            if not self._eval(eval):
                return i

    def _eval(self, eval):
        eval_res = eval(self.app_client.sender, self.contract_state)
        return eval_res

    def _call(self):
        method_name, args = self.fuzz()
        print(f"Calling {method_name} with {args}")
        method = self.app_client.get_method(method_name)
        res = self.app_client.call_no_cov(method, args)


        transition = self.contract_state.load(self.app_client.sender)
        is_new = self.schedule.addTransition(transition)
        if is_new:
            seed = Seed(self.inp)
            seed.transition = transition
            self.population.append(seed)
    


        
    
    
    