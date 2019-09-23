import base64
import hmac
import json
import os
from collections import OrderedDict
from hashlib import sha1, md5
from urllib.parse import urlencode

from sanic.log import logger
import aiofiles
import aiohttp


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
        self.__url_api = 'https://api.zadarma.com'
        if is_sandbox:
            self.__url_api = 'https://api-sandbox.zadarma.com'

    async def call(self,
                   method: str,
                   params: dict = {},
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
        allowed_type = ['GET', 'POST', 'PUT', 'DELETE']
        if request_type not in allowed_type:
            request_type = 'GET'
        params['format'] = format
        auth_str = None
        if is_auth:
            auth_str = self.__get_auth_string_for_header(method, params)

        request_url = self.__url_api + method
        data = json.dumps(params)
        result = {}
        if request_type == 'GET':
            sorted_dict_params = OrderedDict(sorted(params.items()))
            params_string = urlencode(sorted_dict_params)
            request_url += '?' + params_string
            async with aiohttp.ClientSession() as session:
                async with session.get(request_url, headers={'Authorization': auth_str}) as response:
                    result = await response.json()
        elif request_type == 'POST':
            async with aiohttp.ClientSession() as session:
                async with session.post(request_url, headers={'Authorization': auth_str}, data=data) as response:
                    result = await response.json()
        elif request_type == 'PUT':
            async with aiohttp.ClientSession() as session:
                async with session.post(request_url, headers={'Authorization': auth_str}, data=data) as response:
                    result = await response.json()
        logger.info({'result': result, 'method': method, 'type': request_type})
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

    async def callback(self, a_number: str, b_number: str) -> str:
        return await self.call('/v1/request/callback/', {'from': a_number, 'to': b_number})

    async def set_redirect(self, sip: str, to_number: str) -> dict:
        return await self.call('/v1/pbx/redirection/', {
            'pbx_number': sip,
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
