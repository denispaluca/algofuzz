from algokit_utils import AppSpecStateDict, get_algod_client
from algofuzz.FuzzAppClient import FuzzAppClient
from algofuzz.mutate import AccountMutator
from algofuzz.utils import get_application_address
import base64


def dict_list_to_set(dict_list: list[dict]) -> set[dict]:
    return set([frozenset(d.items()) for d in dict_list])

class ContractState:
    def __init__(self, app: FuzzAppClient) -> None:
        self._app = app
        self._address = app.app_address
        self._client = get_algod_client()
        self._global_state: AppSpecStateDict = {}
        self._local_state: dict[str, AppSpecStateDict] = {}

    def load(self, acc_address) -> tuple[dict, dict]:
        old_state = self.get_state()
        self._global_state = self._app.get_global_state()
        self._local_state = self._app.get_local_state(acc_address)

        return old_state, self.get_state()

    def get_state(self) -> dict:
        return {
            'global': self._global_state,
            'local': self._local_state
        }

    def exists_global(self, key: str) -> bool:
        return key in self._global_state

    def get_global(self, key: str) -> str | int:
        return self._global_state[key]


    def exists_local(self, account_address: str, key: str) -> bool:
        return key in self._local_state[account_address]

    def get_local(self, account_address: str, key: str) -> str | int:
        return self._local_state[account_address][key]
    
    def get_receiver(self) -> str:
        return AccountMutator.acc.address

    def get_creator(self):
        return self._creator
