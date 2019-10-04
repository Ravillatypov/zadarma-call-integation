import os
from asyncio import sleep
from datetime import date, datetime, timedelta

from settings import Config
from zadarma import ZadarmaAPI
from functools import lru_cache
from dataclasses import dataclass
from models import CallRecords
from sanic.log import logger


@dataclass
class CallInfo:
    a_number: str = ''
    b_number: str = ''
    sip_number: str = ''
    internal_id: int = 0


zd_client = ZadarmaAPI(Config.ZADARMA_KEY, Config.ZADARMA_SECRET, Config.DEBUG, max_channels=Config.ZADARMA_CHANNELS)
calls = []


@lru_cache(maxsize=1)
def get_download_path(today: str) -> str:
    save_path = os.path.join(Config.CALL_RECORDS_PATH, today)
    if not os.path.exists(save_path):
        os.mkdir(save_path)
    return save_path


async def run_call(data: dict):
    if not zd_client.pbx_id:
        await zd_client.get_internal_numbers()
    a_number = normalize_number(data['first_number'])
    b_number = normalize_number(data['second_number'])
    internal_id = int(data['slave_id'])
    sip_number = await zd_client.get_sip_number()
    await zd_client.get_lock(sip_number)
    status = await zd_client.set_redirect(sip_number, a_number)
    if status['status'] == 'success':
        await zd_client.callback(sip_number, b_number)
    else:
        await zd_client.call('/v1/request/callback/', {'from': a_number, 'to': b_number, 'sip': sip_number})
    zd_client.release_lock(sip_number)
    calls.append(CallInfo(a_number, b_number,  sip_number, internal_id))
    return


async def record_download(call_id: str):
    await sleep(60)
    today = date.today().isoformat()
    save_path = get_download_path(today)
    logger.info(save_path)
    return await zd_client.get_record(call_id, save_path)


async def event_process(event: dict):
    if event.get('call_id_with_rec') is None:
        return
    sip_number = event['internal']
    dst_number = event['destination']
    if len(sip_number) > len(dst_number):
        sip_number, dst_number = dst_number, sip_number
    zd_client.release_number(sip_number)
    audio_file, a_number, internal_id = '', '', 0
    audio_file = await record_download(event['call_id_with_rec'])
    if audio_file:
        audio_file = os.path.relpath(audio_file, Config.STATIC_PATH)
    call_start = datetime.fromisoformat(event['call_start'])
    duration = int(event['duration'])
    call_end = call_start + timedelta(seconds=duration)
    call_lst = list(filter(lambda x: x.sip_number == sip_number and x.b_number == dst_number, calls))
    if call_lst:
        call = call_lst[-1]
        calls.remove(call)
        internal_id = call.internal_id
        a_number = call.a_number

    call_record = CallRecords(
        master_id=1,
        slave_id=internal_id,
        internal_id=int(event['call_id_with_rec'].replace('.', '')),
        status=1 if event['disposition'] == 'answered' else 0,
        direction=2,
        source_number=a_number,
        destination_number=dst_number,
        call_started_datetime=call_start,
        call_ended_datetime=call_end,
        ringing_time=0,
        talking_time=duration,
        audio_file=audio_file,
        internal_number=sip_number,
        unique_id=event.get('call_id_with_rec') or event.get('pbx_call_id'),
        service_data='{}'
    )

    await call_record.save()


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
