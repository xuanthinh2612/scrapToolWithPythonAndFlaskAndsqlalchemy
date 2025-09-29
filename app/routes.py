from flask import Blueprint, render_template, request, redirect, url_for
from app.models import Product, OrderDetail
from sqlalchemy import desc, or_, asc, func
from scraper import uniqlo_crawl
from app.google_mail_service import get_order_detail, update_order_detail
import threading
from datetime import datetime, timedelta

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
        t.daemon = True  # Thread tự kết thúc khi app tắt
        t.start()

        return redirect(url_for("main.index"))
    except Exception as e:
        return f"Lỗi: {str(e)}"


@main.route("/emails")
def order_index():
    from app import db
    try:
        results = db.session.query(
            func.date(OrderDetail.update_date).label('order_day'),
            func.count(OrderDetail.id).label('email_count')
        ).group_by(func.date(OrderDetail.update_date)).order_by(desc(OrderDetail.update_date)).all()

        # Chuyển kết quả thành list dict để dễ dùng trong template
        summary = [{'day': r.order_day, 'count': r.email_count} for r in results]

        return render_template("orders_index.html", summary=summary, brand="uniqlo")
    except Exception as e:
        return f"Lỗi: {str(e)}"


@main.route("/order-by-date")
def order_by_date():
    # Lấy ngày từ query string, mặc định hôm nay
    date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    target_date = datetime.strptime(date_str, "%Y-%m-%d")
    # Ngày tiếp theo để làm ranh giới 23:59:59
    next_day = target_date + timedelta(days=1)

    orders_by_date = OrderDetail.query.filter(OrderDetail.update_date >= target_date,
                                              OrderDetail.update_date < next_day).all()
    return render_template("orders_by_date.html", orders=orders_by_date, brand="uniqlo")


@main.route("/orders/search", methods=["POST"])
def search_order():
    searchKey = request.form.get("searchKey", "").strip()  # lấy input và loại khoảng trắng

    if not searchKey:
        return order_index()
    else:
        # filter theo name hoặc product_code chứa searchKey
        orders = OrderDetail.query.filter(
            or_(
                OrderDetail.order_code.ilike(f"%{searchKey}%"),
                OrderDetail.store_name.ilike(f"%{searchKey}%"),
                OrderDetail.delivery_company.ilike(f"%{searchKey}%"),
                OrderDetail.receiver_name.ilike(f"%{searchKey}%"),
                OrderDetail.order_status.ilike(f"%{searchKey}%"),
                OrderDetail.delivery_tracking_code.ilike(f"%{searchKey}%"),
            )
        ).order_by(desc(OrderDetail.send_date)).all()

    return render_template("orders_by_date.html", orders=orders, brand="uniqlo")


@main.route("/scan-email")
def update_all_email_data():
    try:
        get_order_detail()
        update_order_detail()
        return redirect(url_for("main.order_index"))
    except Exception as e:
        return f"Lỗi: {str(e)}"
