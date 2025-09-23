from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()


def create_app():
    app = Flask(__name__)

    # Cấu hình MySQL
    app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://root:1010@localhost:3306/uniqlo"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    migrate.init_app(app, db)

    # import models để migrate nhận diện
    from app import models

    # register blueprint hoặc routes
    from app.routes import main
    app.register_blueprint(main)

    return app
