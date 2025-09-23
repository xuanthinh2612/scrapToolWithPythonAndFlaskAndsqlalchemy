from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base

def create_app():
    app = Flask(__name__)
    
    # Cấu hình DB
    # engine = create_engine('mysql+mysqlconnector://root:your_password@localhost/uniqlo')
    # Base.metadata.create_all(engine)
    
    # Session = sessionmaker(bind=engine)
    # app.db_session = Session()  # gắn session vào app
    
    # Import routes
    from app import routes
    app.register_blueprint(routes.bp)
    
    return app
