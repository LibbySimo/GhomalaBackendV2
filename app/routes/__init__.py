from flask import Flask
from .api import api


def register_blueprints(app: Flask):
    app.register_blueprint(api)
