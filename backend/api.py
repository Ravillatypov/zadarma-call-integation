from sanic import Blueprint
from sanic.log import logger
from sanic.response import HTTPResponse

from utils import run_call, normalize_dict, event_process

bp = Blueprint('api', url_prefix='/api')


@bp.route('/notify', methods=['POST', 'GET'])
async def notify(request):
    if request.method == 'GET':
        logger.info(request.args)
        zd_echo = request.args.get('zd_echo')
        if zd_echo:
            return HTTPResponse(zd_echo)
    else:
        current_app = request.app
        event = normalize_dict(request.form or request.json)
        logger.info(event)
        if event.get('event', '') == 'NOTIFY_OUT_END':
            current_app.add_task(event_process(event))
    return HTTPResponse('ok')


@bp.route('/call', methods=['POST'])
async def call(request):
    data = normalize_dict(request.form or request.json)
    logger.info(data)
    current_app = request.app
    current_app.add_task(run_call(data))
    return HTTPResponse('ok')
