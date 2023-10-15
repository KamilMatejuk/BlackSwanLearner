import connexion
from flask import jsonify
from decouple import Config, RepositoryEnv
from flask_socketio import SocketIO

from schemas_request import StartRequest
from learn import get_signals_for_timerange, parse_urls, run_test, get_stats


def validate(cls):
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                data = cls(**connexion.request.json)
                data.validate()
            except Exception as ex:
                return jsonify({"error": "Invalid request schema", "details": str(ex)}), 401
            return func(data)
        return wrapper
    return decorator


'''
{
  "asset": "BTCUSDT",
  "interval": "1d",
  "starting_value": 1000000,
  "start_time": 1503100799999,
  "end_time": 1693180799999,
  "model_url": { "host": "127.0.0.1", "port": 51002, "slug": "" },
  "signals": [
    { "name": "price",
      "url": { "host": "127.0.0.1", "port": 50001, "slug": "/price/range/{asset}/{interval}/{start_time}/{end_time}" } },
    { "name": "volume",
      "url": { "host": "127.0.0.1", "port": 50001, "slug": "/price/range/{asset}/{interval}/{start_time}/{end_time}/volume" } },
    { "name": "rsi",
      "url": { "host": "127.0.0.1", "port": 50001, "slug": "/price/range/{asset}/{interval}/{start_time}/{end_time}/rsi" } },
    { "name": "macd",
      "url": { "host": "127.0.0.1", "port": 50001, "slug": "/price/range/{asset}/{interval}/{start_time}/{end_time}/macd" } },
    { "name": "EMA_12",
      "url": { "host": "127.0.0.1", "port": 50001, "slug": "/price/range/{asset}/{interval}/{start_time}/{end_time}/EMA_12" } },
    { "name": "EMA_26",
      "url": { "host": "127.0.0.1", "port": 50001, "slug": "/price/range/{asset}/{interval}/{start_time}/{end_time}/EMA_26" } }
  ]
}
'''
import sys
@validate(StartRequest)
def start_learning(data: StartRequest):
    data = parse_urls(data)
    signals = get_signals_for_timerange(data.signals)
    sys.stderr.write(f'signals\n{signals}\n')
    results = run_test(signals, data.model_url, data.starting_value)
    sys.stderr.write(f'results\n{results}\n')
    stats = get_stats(signals, results, data.starting_value)
    sys.stderr.write(f'stats\n{stats}\n')
    return stats, 200


config = Config(RepositoryEnv('.env.local'))
port = config.get('PORT')
app = connexion.FlaskApp(__name__,
        server='tornado',
        specification_dir='',
        options={'swagger_url': '/swagger-ui'})
app.add_api('openapi.yaml')
print(f' * Checkout SwaggerUI http://127.0.0.1:{port}/swagger-ui/')
socketio = SocketIO(app.app)
socketio.run(app.app, port=port)
