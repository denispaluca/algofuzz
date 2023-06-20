from algokit_utils import AppSpecStateDict, get_algod_client
from algofuzz.utils import get_application_address
import base64


def dict_list_to_set(dict_list: list[dict]) -> set[dict]:
    return set([frozenset(d.items()) for d in dict_list])

class ContractState:
    def __init__(self, app_id: int) -> None:
        self._client = get_algod_client()
        self._app_id = app_id
        self._address = get_application_address(app_id)
        self._global_state: AppSpecStateDict = {}
        self._local_state: dict[str, AppSpecStateDict] = {}
        self._creator: str = None

    def load(self, acc_address) -> tuple[dict, dict]:
        old_state = self.get_state()
        self._load_global()
        self._load_local(acc_address)

        return old_state, self.get_state()

    def _load_global(self):
        app_info = self._client.application_info(self._app_id)
        params: dict = app_info.get('params')
        if not params:
            return

        self._creator = params.get('creator')
        global_state = params.get('global-state')
        if not global_state:
            return

        self._global_state = self.__decode_state(global_state)

    def _load_local(self, acc_address: str):
        account_info = self._client.account_application_info(acc_address, self._app_id)
        data: dict = account_info.get('app-local-state')
        if not data:
            return

        local_state = data.get('key-value')
        if not local_state:
            return

        self._local_state[acc_address] = self.__decode_state(local_state)

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

    def get_creator(self):
        return self._creator

    @staticmethod
    def __decode_state(state_object) -> AppSpecStateDict:
        state_dict: AppSpecStateDict = {}
        for state in state_object:
            state_value = state['value']
            value = state_value['uint']
            if state_value['type'] != 2:
                value = state_value['bytes']

            state_dict[base64.b64decode(state['key']).decode()] = value

        return state_dict