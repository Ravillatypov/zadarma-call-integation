from sanic.log import logger
from sanic.response import HTTPResponse

from api import api_bp as bp


@bp.route('/notify', methods=['POST'])
async def out_end(request):
    logger.info(request.form)
    return HTTPResponse('ok')
