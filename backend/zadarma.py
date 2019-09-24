import base64
import hmac
import json
import os
from asyncio import sleep
from collections import OrderedDict, defaultdict
from hashlib import sha1, md5
from urllib.parse import urlencode

import aiofiles
import aiohttp
from sanic.log import logger


class ZadarmaAPI(object):

    def __init__(self, key, secret, is_sandbox=False, max_channels: int = 1):
        """
        Constructor
        :param key: key from personal
        :param secret: secret from personal
        :param is_sandbox: (True|False)
        """
        self.key = key
        self.secret = secret
        self.is_sandbox = is_sandbox
        self.max_channels = max_channels
        self._dict = defaultdict(int)
        self._lockers = defaultdict(bool)
        self.__url_api = 'https://api.zadarma.com'
        if is_sandbox:
            self.__url_api = 'https://api-sandbox.zadarma.com'
        self.pbx_id = None

    async def call(self,
                   method: str,
                   params: dict = { },
                   request_type: str = 'GET',
                   format: str = 'json',
                   is_auth: bool = True) -> dict:
        """
        Function for send API request
        :param method: API method, including version number
        :param params: Query params
        :param request_type: (get|post|put|delete)
        :param format: (json|xml)
        :param is_auth: (True|False)
        :return: response
        """
        request_type = request_type.upper()
        if request_type not in ('GET', 'POST', 'PUT', 'DELETE'):
            request_type = 'GET'
        params['format'] = format
        auth_str = None
        if is_auth:
            auth_str = self.__get_auth_string_for_header(method, params)

        request_url = self.__url_api + method
        data = json.dumps(params)
        logger.info({'method': method, 'type': request_type, 'data': data, 'auth': auth_str})
        result = {}
        if request_type == 'GET':
            sorted_dict_params = OrderedDict(sorted(params.items()))
            params_string = urlencode(sorted_dict_params)
            request_url += '?' + params_string
            async with aiohttp.ClientSession(headers={ 'Authorization': auth_str }) as session:
                async with session.get(request_url) as response:
                    result = await response.json()
        elif request_type == 'POST':
            async with aiohttp.ClientSession(headers={ 'Authorization': auth_str }) as session:
                async with session.post(request_url, data=data) as response:
                    result = await response.json()
        elif request_type == 'PUT':
            async with aiohttp.ClientSession(headers={ 'Authorization': auth_str }) as session:
                async with session.put(request_url, data=data) as response:
                    result = await response.json()
        logger.info(result)
        return result

    def __get_auth_string_for_header(self, method: str, params: dict) -> str:
        """
        :param method: API method, including version number
        :param params: Query params dict
        :return: auth header
        """
        sorted_dict_params = OrderedDict(sorted(params.items()))
        params_string = urlencode(sorted_dict_params)
        md5hash = md5(params_string.encode('utf8')).hexdigest()
        data = method + params_string + md5hash
        hmac_h = hmac.new(self.secret.encode('utf8'), data.encode('utf8'), sha1)
        bts = bytes(hmac_h.hexdigest(), 'utf8')
        auth = self.key + ':' + base64.b64encode(bts).decode()
        return auth

    async def callback(self, a_number: str, b_number: str) -> dict:
        return await self.call('/v1/request/callback/', {'from': a_number, 'to': b_number})

    async def set_redirect(self, sip: str, to_number: str) -> dict:
        return await self.call('/v1/pbx/redirection/', {
            'pbx_number': f'{self.pbx_id}-{sip}',
            'status': 'on',
            'type': 'phone',
            'destination': to_number,
            'condition': 'always',
            'set_caller_id': 'on'
        }, 'POST')

    async def get_record(self, call_id: str, dir_path: str) -> str:
        result = await self.call('/v1/pbx/record/request/', { 'call_id': call_id })
        link = result.get('link')
        if not link:
            return ''
        filename = os.path.join(dir_path, os.path.basename(link))

        async with aiofiles.open(filename, 'wb') as fd:
            async with aiohttp.ClientSession(connector=self.conn) as session:
                async with session.get(link) as response:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        await fd.write(chunk)
        return filename

    async def get_internal_numbers(self):
        result = await self.call('/v1/pbx/internal/')
        if result.get('status', '') != 'success':
            logger.warning(result)
            return
        self.pbx_id = result['pbx_id']
        for number in result['numbers']:
            await self.call('/v1/pbx/redirection/', {
                'pbx_number': f'{self.pbx_id}-{number}',
                'status': 'off',
            }, 'POST')
            self._dict[number] = self.max_channels

    async def get_sip_number(self):
        result = None
        while not result:
            for k, v in self._dict.items():
                if v:
                    self._dict[k] -= 1
                    result = k
            await sleep(5)
        logger.info({ 'sip_number': result, 'numbers_dict': self._dict })
        return result

    async def get_lock(self, number: str):
        while self._lockers[number]:
            await sleep(1)
        self._lockers[number] = True
        logger.info(f'locked sip number {number}')

    def release_lock(self, number: str):
        self._lockers[number] = False
        logger.info(f'released sip number {number}')

    def release_number(self, number: str):
        if self._dict[number] < self.max_channels:
            self._dict[number] += 1
