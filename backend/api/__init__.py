from sanic import Blueprint

api_bp = Blueprint('api', url_prefix='/api')

from api import notify
