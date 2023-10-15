import connexion
from flask import jsonify
from decouple import Config, RepositoryEnv
from flask_socketio import SocketIO


def hello(name: str):
    try:
        assert name.lower() != "world", "Hello World is to basic"
    except Exception as ex:
        return jsonify({"error": "Invalid request schema", "details": str(ex)}), 401

    return f'Hello {name}', 200


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
