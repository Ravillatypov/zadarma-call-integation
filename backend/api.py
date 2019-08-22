from sanic import Blueprint
from sanic.log import logger
from sanic.response import HTTPResponse

from utils import run_call, record_download, available_sip_numbers, normalize_dict, normalize_number

bp = Blueprint('api', url_prefix='/api')


@bp.route('/notify', methods=['POST', 'GET'])
async def notify(request):
    if request.method == 'GET':
        logger.info(request.args)
        zd_echo = request.args.get('zd_echo')
        if zd_echo:
            return HTTPResponse(zd_echo)
    else:
        logger.info(request.form)
        current_app = request.app
        event = normalize_dict(request.form)
        if event['event'] == 'NOTIFY_OUT_END':
            available_sip_numbers.release_number(event['internal'])
            if event['is_recorded'] and event['call_id_with_rec']:
                current_app.add_task(record_download(event['call_id_with_rec']))
    return HTTPResponse('ok')


@bp.route('/call', methods=['POST'])
async def call(request):
    data = normalize_dict(request.form)
    logger.info(data)
    current_app = request.app
    a_number = normalize_number(data['first_number'])
    b_number = normalize_number(data['second_number'])
    current_app.add_task(run_call(a_number, b_number))
    return HTTPResponse('ok')
