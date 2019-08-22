import os
from asyncio import sleep
from datetime import date
from typing import Iterable
from collections import defaultdict
from settings import Config
from zadarma import ZadarmaAPI
from functools import lru_cache


class SIPNumbers:
    def __init__(self, numbers: Iterable[str], max_channels=3):
        self._dict = defaultdict(int)
        self._lockers = defaultdict(bool)
        if max_channels < 1:
            raise ValueError('max_channels must be positive')
        self.max_channels = max_channels
        for key in numbers:
            self._dict[key] = max_channels

    async def get_sip_number(self):
        result = None
        while not result:
            for k, v in self._dict.items():
                if v:
                    self._dict[k] -= 1
                    result = k
            await sleep(5)
        return result

    async def get_lock(self, number: str):
        while self._lockers[number]:
            await sleep(1)
        self._lockers[number] = True

    def release_lock(self, number: str):
        self._lockers[number] = False

    def release_number(self, number: str):
        if self._dict[number] < self.max_channels:
            self._dict[number] += 1


available_sip_numbers = SIPNumbers(Config.SIP_NUMBERS)
zd_client = ZadarmaAPI(Config.ZADARMA_KEY, Config.ZADARMA_SECRET, Config.DEBUG)


@lru_cache(maxsize=1)
def get_download_path(today: str) -> str:
    save_path = os.path.join(Config.CALL_RECORDS_PATH, today)
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    return save_path


async def run_call(a_number: str, b_number: str):
    sip_number = await available_sip_numbers.get_sip_number()
    await available_sip_numbers.get_lock(sip_number)
    zd_client.set_redirect(sip_number, a_number)
    zd_client.callback(sip_number, b_number)
    available_sip_numbers.release_lock(sip_number)
    return


async def record_download(call_id: str):
    await sleep(60)
    today = date.today().isoformat()
    save_path = get_download_path(today)
    await zd_client.get_record(call_id, save_path)
    return


def normalize_dict(data: dict) -> dict:
    result = {}
    for k, v in data.items():
        if isinstance(v, dict):
            result[k] = normalize_dict(v)
        elif isinstance(v, list) and len(v) == 1:
            result[k] = v[0]
        else:
            result[k] = v
    return result


def normalize_number(number: str) -> str:
    if number.startswith('8'):
        return number.replace('8', '7', 1)
    return number
