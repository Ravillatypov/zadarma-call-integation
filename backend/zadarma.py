import base64
import hmac
import os
from collections import OrderedDict
from hashlib import sha1, md5
from queue import deque
from urllib.parse import urlencode

import aiofiles
import aiohttp
from sanic.log import logger
from settings import Config


class ZadarmaAPI(object):

    def __init__(self, key, secret, is_sandbox=False):
        """
        Constructor
        :param key: key from personal
        :param secret: secret from personal
        :param is_sandbox: (True|False)
        """
        self.key = key
        self.secret = secret
        self.is_sandbox = is_sandbox
        self._numbers = deque()
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

        params = OrderedDict(sorted(params.items()))
        request_url = self.__url_api + method
        logger.info({'method': method, 'type': request_type, 'data': params})
        result = {}
        async with aiohttp.ClientSession(headers=self.__get_headers(method, params)) as session:
            result = await self._do_request(session, request_type, request_url, params)
        logger.info(result)
        return result

    @staticmethod
    async def _do_request(session, request_type: str, url: str, data: dict) -> dict:
        if request_type.lower() == 'get':
            request_params = {'params': data}
        else:
            request_params = {'data': data}

        session_method = getattr(session, request_type.lower())
        async with session_method(url, ssl=Config.ZADARMA_CHECK_SSL, timeout=3, **request_params) as response:
            return await response.json()

    def __get_headers(self, method: str, params: dict) -> dict:
        """
        :param method: API method, including version number
        :param params: Query params dict
        :return: auth header
        """
        params_string = urlencode(params)
        md5hash = md5(params_string.encode('utf8')).hexdigest()
        data = method + params_string + md5hash
        hmac_h = hmac.new(self.secret.encode('utf8'), data.encode('utf8'), sha1)
        bts = bytes(hmac_h.hexdigest(), 'utf8')
        auth = self.key + ':' + base64.b64encode(bts).decode()
        return {'Authorization': auth}

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
            async with aiohttp.ClientSession() as session:
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
        self._numbers = deque(result['numbers'])

    def get_sip_number(self):
        sip = self._numbers.pop()
        self._numbers.appendleft(sip)
        return sip
