from sanic import Sanic
from sanic.response import json

from api import bp
from settings import Config

app = Sanic()
app.config.from_object(Config)
app.blueprint(bp)


@app.route('/')
async def index(request):
    return json({ 'success': True, 'data': None })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
