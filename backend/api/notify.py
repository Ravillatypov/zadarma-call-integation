from sanic import Blueprint
from sanic.response import HTTPResponse
from sanic.log import logger
from db import r_db


bp = Blueprint('notify', url_prefix='/api/notify')


@bp.route('/out_end', methods=['POST'])
async def out_end(request):
    logger.info(request.form)
    number = request.form.get('internal')
    r_db.sadd('sip_numbers', number)
    return HTTPResponse('ok')


@bp.route('/record', methods=['POST'])
async def record(request):
    logger.info(request.form)
    call_id = request.form.get('call_id_with_rec')
    r_db.sadd('records_to_downloads', call_id)
    return HTTPResponse('ok')
