from flask import Blueprint, render_template, request, redirect, url_for
from app.models import Product
from sqlalchemy import desc, or_, asc
from scraper import uniqlo_crawl
import threading

main = Blueprint("main", __name__)

@main.route("/", methods=["GET"])
def index():
    return redirect(url_for("main.uniqlo_index"))

@main.route("/uniqlo", methods=["GET"])
def uniqlo_index():
    category = request.args.get("category", "women")
    products = (Product.query.filter_by(category=category, type="uniqlo").order_by(desc(Product.discountFlg))
                .order_by(asc(Product.current_price)).all())
    return render_template("index.html", products=products, brand="uniqlo")

@main.route("/uniqlo/sale", methods=["GET"])
def uniqlo_sale():
    products = Product.query.filter_by(discountFlg=True, type="uniqlo").order_by(asc(Product.current_price)).all()
    return render_template("index.html", products=products, brand="uniqlo")

@main.route("/gu", methods=["GET"])
def gu_index():
    category = request.args.get("category", "women")
    products = (Product.query.filter_by(category=category, type="gu").order_by(desc(Product.discountFlg))
                .order_by(asc(Product.current_price)).all())
    return render_template("index.html", products=products, brand="gu")

@main.route("/gu/sale", methods=["GET"])
def gu_sale():
    products = Product.query.filter_by(discountFlg=True, type="gu").order_by(asc(Product.current_price)).all()
    return render_template("index.html", products=products, brand="gu")

@main.route("/search", methods=["POST"])
def search():
    searchKey = request.form.get("searchKey", "").strip()  # lấy input và loại khoảng trắng
    
    if not searchKey:
        return index()
    else:
        # filter theo name hoặc product_code chứa searchKey
        products = Product.query.filter(
            or_(
                Product.name.ilike(f"%{searchKey}%"),
                Product.product_code.ilike(f"%{searchKey}%")
            )
        ).order_by(desc(Product.discountFlg)).order_by(asc(Product.current_price)).all()

    return render_template("index.html", products=products, brand="uniqlo")

@main.route("/start-crawl")
def crawl_uniqlo_route():
    try:
        # Tạo thread chạy crawl
        t = threading.Thread(target=uniqlo_crawl.start_crawl_uniqlo)
        t.daemon = True   # Thread tự kết thúc khi app tắt
        t.start()

        return redirect(url_for("main.index"))
    except Exception as e:
        return f"Lỗi: {str(e)}"
