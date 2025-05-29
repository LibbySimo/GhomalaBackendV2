from flask import Flask
from app.routes import register_blueprints
from app.extension import cors

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')


    # add extensions
    cors.init_app(app)


    # register Blueprint
    register_blueprints(app)


    @app.route("/")
    def hello():
        return("Document API is Live")

    return app
