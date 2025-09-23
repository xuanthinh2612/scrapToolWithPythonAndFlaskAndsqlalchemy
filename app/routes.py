from flask import Blueprint, render_template, request, redirect, url_for
from app.models import Product
from sqlalchemy import desc
from scraper import uniqlo_crawl

main = Blueprint("main", __name__)

@main.route("/", methods=["GET"])
def index():
    products = Product.query.order_by(desc(Product.discountFlg)).all()
    return render_template("index.html", products=products)


@main.route("/crawl-uniqlo")
def crawl_uniqlo_route():
    try:
        uniqlo_crawl.uniqlo_crawl()
        return redirect(url_for("main.index"))
    except Exception as e:
        return f"Lỗi: {str(e)}"
