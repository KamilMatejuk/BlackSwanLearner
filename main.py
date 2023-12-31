import glob
import json
import connexion
from flask import jsonify
from decouple import Config, RepositoryEnv
from flask_socketio import SocketIO

from schemas_request import StartRequest, ContinueRequest
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
  "repeat": 1,
  "model_url": { "host": "127.0.0.1", "port": 51002, "slug": "" },
  "signals": [
    { "name": "price",
      "url": { "host": "127.0.0.1", "port": 50001, "slug": "/price/range/{asset}/{interval}/{start_time}/{end_time}" } },
    { "name": "volume",
      "url": { "host": "127.0.0.1", "port": 50001, "slug": "/indicators/range/{asset}/{interval}/{start_time}/{end_time}/volume" } },
    { "name": "rsi",
      "url": { "host": "127.0.0.1", "port": 50001, "slug": "/indicators/range/{asset}/{interval}/{start_time}/{end_time}/rsi" } },
    { "name": "macd",
      "url": { "host": "127.0.0.1", "port": 50001, "slug": "/indicators/range/{asset}/{interval}/{start_time}/{end_time}/macd" } },
    { "name": "EMA_12",
      "url": { "host": "127.0.0.1", "port": 50001, "slug": "/indicators/range/{asset}/{interval}/{start_time}/{end_time}/EMA_12" } },
    { "name": "EMA_26",
      "url": { "host": "127.0.0.1", "port": 50001, "slug": "/indicators/range/{asset}/{interval}/{start_time}/{end_time}/EMA_26" } }
  ]
}
'''
@validate(StartRequest)
def start_learning(data: StartRequest):
    data = parse_urls(data)
    signals = get_signals_for_timerange(data.signals)
    id, results = run_test(signals, data.model_url, data.starting_value)
    full_stats = get_stats(id, signals, results, data.starting_value)
    if data.repeat > 1:
        full_stats = [full_stats]
        for _ in range(data.repeat - 1):
            _, results = run_test(signals, data.model_url, data.starting_value, id)
            stats = get_stats(id, signals, results, data.starting_value)
            full_stats.append(stats)
    return full_stats, 200


'''
{
  "id": "018b35478fa57f4b8e02f34a17ad84d5",
  "asset": "BTCUSDT",
  "interval": "1d",
  "starting_value": 1000000,
  "start_time": 1503100799999,
  "end_time": 1693180799999,
  "repeat": 1,
  "model_url": { "host": "127.0.0.1", "port": 51002, "slug": "" },
  "signals": [
    { "name": "price",
      "url": { "host": "127.0.0.1", "port": 50001, "slug": "/price/range/{asset}/{interval}/{start_time}/{end_time}" } },
    { "name": "volume",
      "url": { "host": "127.0.0.1", "port": 50001, "slug": "/indicators/range/{asset}/{interval}/{start_time}/{end_time}/volume" } },
    { "name": "rsi",
      "url": { "host": "127.0.0.1", "port": 50001, "slug": "/indicators/range/{asset}/{interval}/{start_time}/{end_time}/rsi" } },
    { "name": "macd",
      "url": { "host": "127.0.0.1", "port": 50001, "slug": "/indicators/range/{asset}/{interval}/{start_time}/{end_time}/macd" } },
    { "name": "EMA_12",
      "url": { "host": "127.0.0.1", "port": 50001, "slug": "/indicators/range/{asset}/{interval}/{start_time}/{end_time}/EMA_12" } },
    { "name": "EMA_26",
      "url": { "host": "127.0.0.1", "port": 50001, "slug": "/indicators/range/{asset}/{interval}/{start_time}/{end_time}/EMA_26" } }
  ]
}
'''
@validate(ContinueRequest)
def continue_learning(data: ContinueRequest):
    data = parse_urls(data)
    signals = get_signals_for_timerange(data.signals)
    _, results = run_test(signals, data.model_url, data.starting_value, data.id)
    full_stats = get_stats(data.id, signals, results, data.starting_value)
    if data.repeat > 1:
        full_stats = [full_stats]
        for _ in range(data.repeat - 1):
            _, results = run_test(signals, data.model_url, data.starting_value, data.id)
            stats = get_stats(data.id, signals, results, data.starting_value)
            full_stats.append(stats)
    return full_stats, 200


def stats(id: str):
    try:
        data = []
        for file in sorted(glob.glob(f'data/transactions_{id}*.json')):
            with open(file) as f:
                transactions = json.load(f)
            data.append({
                'number_of_transactions': len(transactions),
                'number_of_transactions_profit': len([t for t in transactions if t['profit'] > 0]),
                'number_of_transactions_loss': len([t for t in transactions if t['profit'] < 0]),
                'overall_profit': 0 if len(transactions) == 0 else sum([t['profit'] for t in transactions]) / transactions[0]['starting'],
            })
        return data, 200
    except Exception as ex:
        return jsonify({"error": "Invalid request schema", "details": str(ex)}), 401


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
