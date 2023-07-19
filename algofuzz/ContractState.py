from copy import deepcopy
from algokit_utils import AppSpecStateDict, get_algod_client
from algofuzz.FuzzAppClient import FuzzAppClient
from algofuzz.mutate import AccountMutator


def dict_list_to_set(dict_list: list[dict]) -> set[dict]:
    return set([frozenset(d.items()) for d in dict_list])

State = dict[bytes | str, bytes | str | int]
class ContractState:
    def __init__(self, app: FuzzAppClient) -> None:
        self._app = app
        self._address = app.app_address
        self._client = get_algod_client()
        self._global_state: State = {}
        self._local_state: dict[str, State] = {}

    def load(self) -> tuple[dict, dict]:
        old_state = self.get_state()
        self._global_state = self._app.get_global_state()

        for acc in AccountMutator.accs:
            self._local_state[acc.address] = self._app.get_local_state(acc.address)

        return old_state, self.get_state()

    def get_state(self) -> dict:
        return {
            'global': self._global_state.copy(),
            'local': deepcopy(self._local_state)
        }

    def exists_global(self, key: str) -> bool:
        return key in self._global_state

    def get_global(self, key: str) -> str | int:
        return self._global_state[key]


    def exists_local(self, account_address: str, key: str) -> bool:
        return key in self._local_state[account_address]

    def get_local(self, account_address: str, key: str) -> str | int:
        return self._local_state[account_address][key]
    
    def get_creator(self):
        return self._creator
