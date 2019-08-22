from sanic.log import logger
from sanic.response import HTTPResponse

from api import api_bp as bp


@bp.route('/notify', methods=['POST', 'GET'])
async def out_end(request):
    logger.info(request.form)
    logger.info(request.args)
    zd_echo = request.args.get('zd_echo')
    if zd_echo:
        return HTTPResponse(zd_echo)
    return HTTPResponse('ok')
