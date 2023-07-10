import hashlib
import json
import pickle
import random
from typing import Callable, Set, Union, Sequence, Dict, List
from algosdk import (abi)
from algofuzz.FuzzAppClient import FuzzAppClient

from algofuzz.mutate import MethodMutator
from algofuzz.ContractState import ContractState
from enum import Enum
from abc import ABC, abstractmethod
import curses

class Driver(Enum):
    COVERAGE = 0
    STATE = 1
    COMBINED = 2

class Seed:
    """Represent an input with additional attributes"""

    def __init__(self, data) -> None:
        """Initialize from seed data"""
        self.data = data

        self.coverage: Set[int] = set()
        self.transition: tuple[dict,dict] = None
        self.distance: Union[int, float] = -1
        self.energy = 0.0

    def __str__(self):
        """Returns data as string representation of the seed"""
        return self.data.__str__()

    __repr__ = __str__


def getPathID(coverage: set[int]) -> str:
    """Returns a unique hash for the covered statements"""
    pickled = pickle.dumps(sorted(coverage))
    return hashlib.md5(pickled).hexdigest()


def get_transition_id(transition: tuple[dict, dict]) -> str:
    pickled = json.dumps(transition, sort_keys=True).encode()
    return hashlib.md5(pickled).hexdigest()

class PowerSchedule:
    def __init__(self, exponent: int = 5, trans_coef = 0.5) -> None:
        self.path_frequency: Dict = {}
        self.transition_frequency: Dict = {}
        self.exponent = exponent
        self.trans_coef = trans_coef

    def assignEnergy(self, population: Sequence[Seed]) -> None:
        for seed in population:
            transition_id, path_id = None, None
            if seed.transition is not None:
                transition_id = get_transition_id(seed.transition)
                if transition_id not in self.transition_frequency:
                    self.transition_frequency[transition_id] = 1

            if seed.coverage is not None:
                path_id = getPathID(seed.coverage)
                if path_id not in self.path_frequency:
                    self.path_frequency[path_id] = 1
            
            

            trans_freq = self.transition_frequency.get(transition_id, 0)
            path_freq = self.path_frequency.get(path_id, 0)
            weighted_freqs = self.trans_coef * trans_freq + (1 - self.trans_coef) * path_freq
            seed.energy = 1 / (weighted_freqs ** self.exponent)

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
    
    def addTransition(self, transition: tuple[dict, dict] | None) -> bool:
        if transition is None:
            return False
        
        transition_id = get_transition_id(transition)
        if transition_id not in self.transition_frequency:
            self.transition_frequency[transition_id] = 1
            return True
        
        self.transition_frequency[transition_id] += 1
        return False
    
    def addPath(self, path: Set[int] | None) -> bool:
        if path is None:
            return False
        
        path_id = getPathID(path)
        if path_id not in self.path_frequency:
            self.path_frequency[path_id] = 1
            return True
        
        self.path_frequency[path_id] += 1
        return False

Candidate = tuple[str, list]

class ContractFuzzer(ABC):
    def __init__(self, app_client: FuzzAppClient):
        self.app_client = app_client

    def start(self, eval: Callable[[str, ContractState], bool], runs: int = 100, driver: Driver = Driver.COMBINED) -> int | None:
        self.rejected_calls = 0
        self.covered_lines: Set[int] = set()
        self.driver = driver
        self.app_client.create()
        self.lines_count = self.app_client.approval_line_count
        try:
            self.app_client.opt_in()
        except:
            pass
        
        self.contract_state = ContractState(self.app_client)
        self.contract_state.load(self.app_client.sender)

        self._setup()


        stdscr = curses.initscr()

        stdscr.addstr(0, 0, f"Fuzzing contract {self.app_client.app_name} (id: {self.app_client.app_id}) from account {self.app_client.sender}")

        for i in range(runs):
            self._call()


            stdscr.addstr(2, 0, f"Calls executed: \t{i+1}/{runs}")
            stdscr.addstr(3, 0, f"Calls rejected: \t{self.rejected_calls}\n")
            if self.driver != Driver.STATE:
                stdscr.addstr(4, 0, f"Lines covered: \t\t{len(self.covered_lines)}/{self.lines_count} ({len(self.covered_lines) / self.lines_count * 100:.2f}%)")
            if self.driver != Driver.COVERAGE:
                stdscr.addstr(5, 0, f"State transitions: \t{self._count_transitions()}\n")
            stdscr.refresh()

            if not self._eval(eval):
                break
            

            
    @abstractmethod
    def _setup(self):
        pass

    @abstractmethod
    def _count_transitions(self) -> int:
        pass

    def _create_power_schedule(self) -> PowerSchedule:
        match self.driver:
            case Driver.STATE: return PowerSchedule(trans_coef=1.0)
            case Driver.COVERAGE: return PowerSchedule(trans_coef=0.0)
            case Driver.COMBINED: return PowerSchedule(trans_coef=0.5)

    def _eval(self, eval):
        eval_res = eval(self.app_client.sender, self.contract_state)
        return eval_res

    def _call(self):
        method_name, args = self.fuzz()
        method = self.app_client.get_method(method_name)

        is_state_driven = self.driver == Driver.STATE
        res, cov = ((self.app_client.call_no_cov(method, args), None) 
            if is_state_driven 
            else self.app_client.call(method, args)) 

        if(not res):
            self.rejected_calls += 1
            return
        
        if cov is not None:
            self.covered_lines.update(cov)
        
        loaded = self.contract_state.load(self.app_client.sender) 
        transition = loaded if self.driver != Driver.COVERAGE else None

        self._update(cov, transition)

    @abstractmethod
    def fuzz(self) -> Candidate:
        pass
        
    @abstractmethod
    def _update(self, cov: set[int], transition: tuple[dict, dict]) -> None:
        pass


class MethodFuzzer:
    def __init__(self, method: abi.Method, addr: str, schedule: PowerSchedule):
        self.method = method
        self.mutator = MethodMutator(method, addr)
        self.seeds = [self.mutator.seed()]
        self.seed_index = 0
        self.population = []
        self.schedule = schedule
    
    def fuzz(self):
        if self.seed_index < len(self.seeds):
            # Still seeding
            self.inp = self.seeds[self.seed_index]
            self.seed_index += 1
        else:
            # Mutating
            self.inp = self.create_candidate()

        return self.inp
        
    def create_candidate(self):
        """Returns an input generated by fuzzing a seed in the population"""
        candidate = None
        if len(self.population) > 0:
            seed = self.schedule.choose(self.population)
            candidate = seed.data
        else:
            candidate = random.choice(self.seeds)

        # Stacking: Apply multiple mutations to generate the candidate
        trials = min(len(candidate), 1 << random.randint(1, 5))
        for i in range(trials):
            candidate = self.mutator.mutate(candidate)
        return candidate
    
    def update(self, cov: set[int], transition: tuple[dict, dict]) -> None:
        is_new_coverage = self.schedule.addPath(cov)
        is_new_transition = self.schedule.addTransition(transition)

        if is_new_transition or is_new_coverage:
            seed = Seed(self.inp)
            seed.transition = transition
            seed.coverage = cov
            self.population.append(seed)

class PartialFuzzer(ContractFuzzer):
    def _setup(self):
        self.method_fuzzers = {
            method.name: MethodFuzzer(method, self.app_client.sender, self._create_power_schedule()) 
            for method in self.app_client.methods
        }

    def _count_transitions(self) -> int:
        transitions = set()
        for method_fuzzer in self.method_fuzzers.values():
            transitions.update(method_fuzzer.schedule.transition_frequency.keys())
        return len(transitions)

    def fuzz(self) -> Candidate:
        method = random.choice(self.app_client.methods)
        method_fuzzer = self.method_fuzzers[method.name]
        self.inp: Candidate = method.name, method_fuzzer.fuzz()
        return self.inp
    
    def _update(self, cov: set[int], transition: tuple[dict, dict]) -> None:
        method = self.app_client.get_method(self.inp[0])
        method_fuzzer = self.method_fuzzers[method.name]
        method_fuzzer.update(cov, transition)

    


class TotalFuzzer(ContractFuzzer):    
    def _setup(self):
        self.method_mutators = {method.name: MethodMutator(method, self.app_client.sender) for method in self.app_client.methods}
        self.seeds = [(method.name, self.method_mutators[method.name].seed()) for method in self.app_client.methods]
        self.seed_index = 0
        self.population: list[Seed] = []
        self.schedule = self._create_power_schedule()

    def _count_transitions(self) -> int:
        return len(self.schedule.transition_frequency.keys())

    def fuzz(self):
        if self.seed_index < len(self.seeds):
            # Still seeding
            self.inp = self.seeds[self.seed_index]
            self.seed_index += 1
        else:
            # Mutating
            self.inp = self.create_candidate()

        return self.inp
    
    def create_candidate(self):
        candidate = None
        if len(self.population) > 0:
            seed = self.schedule.choose(self.population)
            candidate = seed.data
        else:
            candidate = random.choice(self.seeds)

        # Stacking: Apply multiple mutations to generate the candidate
        trials = min(len(candidate), 1 << random.randint(1, 5))
        for i in range(trials):
            candidate = self.mutate(candidate)
        return candidate
    
    def mutate(self, value: tuple[str, list]):
        method, args = value
        mutator = self.method_mutators[method]
        return (method, mutator.mutate(args))

    def _update(self, cov: set[int], transition: tuple[dict, dict]) -> None:
        is_new_transition = self.schedule.addTransition(transition) 
        is_new_coverage = self.schedule.addPath(cov)

        if is_new_coverage or is_new_transition:
            seed = Seed(self.inp)
            seed.transition = transition
            seed.coverage = cov
            self.population.append(seed) 
