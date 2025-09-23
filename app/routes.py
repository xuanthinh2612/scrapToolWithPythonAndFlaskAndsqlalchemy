from flask import Blueprint, render_template, current_app
from app.models import Product

bp = Blueprint('main', __name__)

@bp.route("/")
def index():
    # session = current_app.db_session
    # products = session.query(Product).all()
    # return render_template("index.html", products=products)
    return render_template("index.html")