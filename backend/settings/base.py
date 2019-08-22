# base settings
from typing import Iterable


class Config:
    CALL_RECORDS_PATH: str = '/tmp'
    ZADARMA_KEY: str = ''
    ZADARMA_SECRET: str = ''
    SIP_NUMBERS: Iterable[str] = []
    DEBUG: bool = True
