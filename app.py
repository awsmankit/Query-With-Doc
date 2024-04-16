# app.py
from flask import Flask
from flask_cors import CORS
from flask_caching import Cache
from controller.controller import routes_blueprint, init_cache

app = Flask(__name__)
app.config['CACHE_TYPE'] = 'simple'
cache = Cache(app)
CORS(app, origins="*")

# Initialize cache in the controller
init_cache(cache)

app.register_blueprint(routes_blueprint)

if __name__ == '__main__':
    app.run(port=9069, host="0.0.0.0", debug=False)
