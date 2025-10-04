import threading
from collections import defaultdict

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from sqlalchemy import desc, or_, asc, and_

from scraper import google_mail_service
from app.models import Product, OrderDetail
from scraper import uniqlo_crawl
from app.const import *

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
        flash("Đã bắt đầu scan dữ liệu!", "success")  # gửi message
        return redirect(url_for("main.index"))
    except Exception as e:
        return f"Lỗi: {str(e)}"


@main.route("/orders")
def order_index():
    from app import db
    from sqlalchemy import func, case, and_

    try:
        # Tính số đơn theo store_name, chỉ đếm những order_status khác completed/canceled
        results = db.session.query(
            OrderDetail.store_name.label('store_name'),
            func.sum(
                case(
                    (~OrderDetail.order_status.in_(['completed', 'canceled']), 1),
                    else_=0
                )
            ).label('order_count')
        ).filter(OrderDetail.store_name.isnot(None)) \
            .group_by(OrderDetail.store_name).order_by(desc(OrderDetail.update_date)).all()

        summary = [{'store_name': r.store_name, 'order_count': r.order_count} for r in results]

        # Các order gửi về kho
        deliver_to_stock_orders = OrderDetail.query.filter_by(order_status="ready_to_delivery").order_by(
            desc(OrderDetail.update_date)).all()
        summary.append({
            'store_name': DELIVERY_TO_STOCK,
            'order_count': len(deliver_to_stock_orders)
        })

        # Các order đã đặt thành công (không có tracking_code)
        ordered_success_orders = OrderDetail.query.filter_by(order_status="ordered").order_by(
            desc(OrderDetail.update_date)).all()
        summary.append({
            'store_name': ORDER_SUCCESS,
            'order_count': len(ordered_success_orders)
        })

        return render_template("orders_index.html", summary=summary, brand="uniqlo")

    except Exception as e:
        return f"Lỗi: {str(e)}"


@main.route("/order-by-store")
def order_by_store():
    # Lấy ngày từ query string, mặc định hôm nay
    store_name = request.args.get("store")

    if store_name == ORDER_SUCCESS:
        query = OrderDetail.query.filter_by(order_status="ordered").order_by(
            desc(OrderDetail.update_date))
    elif store_name == DELIVERY_TO_STOCK:
        query = OrderDetail.query.filter(
            OrderDetail.delivery_tracking_code.isnot(None)).order_by(desc(OrderDetail.update_date))
    else:
        query = OrderDetail.query.filter_by(store_name=store_name).order_by(desc(OrderDetail.update_date))

    orders_by_store = query.limit(LIMIT_NUMBER).all()

    # Group theo ngày bằng Python
    grouped = defaultdict(list)
    for o in orders_by_store:
        day = o.update_date.date()  # chỉ lấy yyyy-mm-dd
        grouped[day].append(o)

    # Chuyển thành list để dễ render
    summary = [
        {"order_date": day, "orders": items}
        for day, items in sorted(grouped.items(), reverse=True)
    ]

    return render_template("orders_by_date.html", summary=summary, store_name=store_name or "Đặt về kho",
                           brand="uniqlo")


@main.route("/order-by-store-and-create-date")
def order_by_store_and_create_date():
    # Lấy ngày từ query string, mặc định hôm nay
    store_name = request.args.get("store")

    if store_name == ORDER_SUCCESS:
        query = OrderDetail.query.filter_by(order_status="ordered").order_by(
            desc(OrderDetail.update_date))
    elif store_name == DELIVERY_TO_STOCK:
        query = OrderDetail.query.filter(
            OrderDetail.delivery_tracking_code.isnot(None)).order_by(desc(OrderDetail.update_date))
    else:
        query = OrderDetail.query.filter_by(store_name=store_name).order_by(desc(OrderDetail.update_date))

    orders_by_store = query.limit(LIMIT_NUMBER).all()

    # Group theo ngày bằng Python
    grouped = defaultdict(list)
    for o in orders_by_store:
        day = o.send_date.date()  # chỉ lấy yyyy-mm-dd
        grouped[day].append(o)

    # Chuyển thành list để dễ render
    summary = [
        {"order_date": day, "orders": items}
        for day, items in sorted(grouped.items(), reverse=True)
    ]

    return render_template("orders_by_date.html", summary=summary, store_name=store_name, brand="uniqlo")


@main.route("/orders/update-status", methods=["POST"])
def update_order_status():
    from app import db

    data = request.get_json()
    order_ids = data.get("order_ids", [])

    if not order_ids:
        return jsonify({"message": "Chưa có đơn nào được chọn!"}), 400

    # Cập nhật status thành 'completed'
    OrderDetail.query.filter(OrderDetail.id.in_(order_ids)).update(
        {"order_status": "completed"}, synchronize_session=False
    )
    db.session.commit()

    return jsonify({"message": f"Cập nhật thành công {len(order_ids)} đơn hàng."})


@main.route("/orders/search", methods=["POST"])
def search_order():
    searchKey = request.form.get("searchKey", "").strip()  # lấy input và loại khoảng trắng

    if not searchKey:
        return order_index()
        # filter theo name hoặc product_code chứa searchKey
    orders = OrderDetail.query.filter(
        or_(
            OrderDetail.order_code.ilike(f"%{searchKey}%"),
            OrderDetail.store_name.ilike(f"%{searchKey}%"),
            OrderDetail.delivery_company.ilike(f"%{searchKey}%"),
            OrderDetail.receiver_name.ilike(f"%{searchKey}%"),
            OrderDetail.delivery_tracking_code.ilike(f"%{searchKey}%"),
        )
    ).order_by(desc(OrderDetail.send_date)).all()

    # Group theo ngày bằng Python
    grouped = defaultdict(list)
    for o in orders:
        day = o.update_date.date()  # chỉ lấy yyyy-mm-dd
        grouped[day].append(o)

    # Chuyển thành list để dễ render
    summary = [
        {"order_date": day, "orders": items}
        for day, items in sorted(grouped.items(), reverse=True)
    ]

    return render_template("orders_by_date.html", summary=summary, store_name="SEARCH", brand="uniqlo")


@main.route("/scan-email")
def update_all_email_data():
    try:
        t = threading.Thread(target=google_mail_service.start_scan_email)
        t.daemon = True  # Thread tự kết thúc khi app tắt
        t.start()
        flash("Đang scan mail! quay lại sau 5 phút nữa", "success")  # gửi message
        return redirect(url_for("main.order_index"))
    except Exception as e:
        return f"Lỗi: {str(e)}"
