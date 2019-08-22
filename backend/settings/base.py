# base settings
from typing import Iterable


class Config:
    CALL_RECORDS_PATH: str = '/tmp'
    STATIC_PATH: str = ''
    ZADARMA_KEY: str = ''
    ZADARMA_SECRET: str = ''
    SIP_NUMBERS: Iterable[str] = []
    DEBUG: bool = True
    DB_URL: str = 'mysql://myuser:mypass@localhost:3306/somedb'
    DB_INIT: bool = True
