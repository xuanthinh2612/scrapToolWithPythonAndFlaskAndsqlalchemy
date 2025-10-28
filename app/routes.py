import threading
from collections import defaultdict

from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from sqlalchemy import desc, or_, asc, and_
from sqlalchemy.sql.coercions import expect

from scraper import google_mail_service
from app.models import Product, OrderDetail, ProductColor, ProductSize, PreOrderInfo
from scraper import uniqlo_crawl
from app.const import *

main = Blueprint("main", __name__)


@main.route("/", methods=["GET"])
def index():
    return redirect(url_for("main.uniqlo_index"))


@main.route("/uniqlo", methods=["GET"])
def uniqlo_index():
    category = request.args.get("category", "women")
    products = (
        Product.query.filter_by(category=category, type="uniqlo").order_by(desc((Product.follow_flag))).order_by(
            desc(Product.discountFlg))
        .order_by(asc(Product.current_price)).all())
    return render_template("index.html", products=products, brand="uniqlo")


@main.route("/uniqlo/sale", methods=["GET"])
def uniqlo_sale():
    products = Product.query.filter_by(discountFlg=True, type="uniqlo").order_by(asc(Product.current_price)).all()
    return render_template("index.html", products=products, brand="uniqlo")


@main.route("/gu", methods=["GET"])
def gu_index():
    category = request.args.get("category", "women")
    products = (Product.query.filter_by(category=category, type="gu").order_by(desc((Product.follow_flag))).order_by(
        desc(Product.discountFlg))
                .order_by(asc(Product.current_price)).all())
    return render_template("index.html", products=products, brand="gu")


@main.route("/gu/sale", methods=["GET"])
def gu_sale():
    products = Product.query.filter_by(discountFlg=True, type="gu").order_by(asc(Product.current_price)).all()
    return render_template("index.html", products=products, brand="gu")


@main.route("/follow-product", methods=["GET"])
def follow_product():
    products = Product.query.filter_by(follow_flag=True).order_by(asc(Product.current_price)).all()
    return render_template("index.html", products=products, brand="uniqlo")


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


@main.route("/toggle-follow", methods=["POST"])
def toggle_follow():
    from app import db
    data = request.get_json()
    product_id = data.get("product_id")

    if not product_id:
        return jsonify({"message": "Thiếu ID sản phẩm"}), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify({"message": "Không tìm thấy sản phẩm"}), 404

    product.follow_flag = not product.follow_flag  # Đảo trạng thái
    db.session.commit()

    status = "followed" if product.follow_flag else "unfollowed"
    return jsonify({"message": f"Đã {status} sản phẩm {product.name}", "follow_flag": product.follow_flag})


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
        deliver_to_stock_orders = OrderDetail.query.filter_by(order_status=READY_TO_DELIVERY_STATUS).order_by(
            desc(OrderDetail.update_date)).all()
        summary.append({
            'store_name': DELIVERY_TO_STOCK,
            'order_count': len(deliver_to_stock_orders)
        })

        # Các order đã đặt thành công (không có tracking_code)
        ordered_success_orders = OrderDetail.query.filter_by(order_status=ORDERED_STATUS).order_by(
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
        query = OrderDetail.query.filter_by(order_status=ORDERED_STATUS).order_by(
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
        query = OrderDetail.query.filter_by(order_status=ORDERED_STATUS).order_by(
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
        {"order_status": COMPLETED_STATUS}, synchronize_session=False
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


@main.route("/update-product", methods=["POST"])
def update_product():
    """
    Khi người dùng nhấn nút 'update':
    - Nhận product_id từ client
    - Mở trang product.link bằng Selenium (headless)
    - Lấy danh sách màu + ảnh chip
    - Cập nhật lại vào DB
    """
    from app import db
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    import time

    data = request.get_json()
    product_id = data.get("product_id")

    if not product_id:
        return jsonify({"message": "Thiếu ID sản phẩm"}), 400

    # --- Lấy sản phẩm từ DB ---
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"message": "Không tìm thấy sản phẩm"}), 404

    # --- Cấu hình Selenium ---
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get(product.link)
        time.sleep(5)  # chờ trang SPA render
        # 🎨 Lấy danh sách màu
        colors = []
        # 🎯 Tìm <ul> chứa danh sách màu
        ul_selector = "ul.content-alignment.collection-list-horizontal"
        ul_element = driver.find_element(By.CSS_SELECTOR, ul_selector)
        # product_price = driver.find_element(By.CSS_SELECTOR, "p.fr-ec-price-text.fr-ec-price-text--large").text.replace("¥", "").replace(",", "")
        # 🎨 Lặp qua từng <li> (mỗi màu)
        li_elements = ul_element.find_elements(By.CSS_SELECTOR, "li.collection-list-horizontal__item")

        colors = []
        sizes = {}

        for li in li_elements:
            try:
                button = li.find_element(By.CSS_SELECTOR, "button.chip")
                color_code = button.get_attribute("value") or ""
                img = button.find_element(By.TAG_NAME, "img")
                color_name = img.get_attribute("alt") or ""
                image_link = img.get_attribute("src") or ""

                colors.append({
                    "color_code": color_code.strip(),
                    "color_name": color_name.strip(),
                    "imageLink": image_link.strip()
                })

                # Click qua mỗi color để lấy size 
                button.click()
                size_group_selector = "div.size-chip-group"
                size_group_element = driver.find_element(By.CSS_SELECTOR, size_group_selector)
                size_elements = size_group_element.find_elements(By.CSS_SELECTOR, "div.size-chip-wrapper")
                size_by_color = []
                for size in size_elements:
                    # size_name = size.find_element(By.CSS_SELECTOR, "button.chip div[data-testid='ITOContentAlignment'] div.typography").text
                    size_name = size.find_element(By.CSS_SELECTOR, "div[data-testid='ITOTypography']").text
                    size_over_flg = size.find_elements(By.CSS_SELECTOR, "div.strike")

                    if not size_over_flg:
                        size_by_color.append({
                            "size_name": size_name.strip(),
                        })

                sizes[color_name.strip()] = size_by_color

            except Exception as e:
                print(f"Lỗi khi lấy màu: {e}")

        # # --- Cập nhật DB ---
        # # Xóa danh sách màu cũ (nếu có cascade delete-orphan)
        # UDPATE Product info
        product.colors.clear()
        # product.current_price = product_price

        # Cập nhật màu có thể đặt hàng
        for color_data in colors:
            color_obj = ProductColor(
                color_name=color_data["color_name"],
                imageLink=color_data["imageLink"],
                color_code=color_data["color_code"],
                product=product,
            )

            size_list = sizes.get(color_data["color_name"], [])
            for size_data in size_list:
                size_obj = ProductSize(
                    color=color_obj,
                    size_name=size_data["size_name"]
                )
                db.session.add(size_obj)

            db.session.add(color_obj)

        db.session.commit()

        return jsonify({
            "message": f"Đã cập nhật {len(colors)} màu cho sản phẩm {product.name}",
            "colors": colors
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Lỗi khi xử lý Selenium: {str(e)}"}), 500

    finally:
        driver.quit()


@main.route("/get-product-color-and-size", methods=["POST"])
def get_product_color_and_size():
    from app import db

    """
    Khi người dùng nhấn nút 'Đặt hàng':
    - Nhận product_id từ client
    - Lấy danh sách màu + ảnh chip từ DB
    """

    data = request.get_json()
    product_id = data.get("product_id")

    if not product_id:
        return jsonify({"message": "Thiếu ID sản phẩm"}), 400

    # --- Lấy sản phẩm từ DB ---
    product = Product.query.get(product_id)
    if not product:
        return jsonify({"message": "Không tìm thấy sản phẩm"}), 404

    # Tạo danh sách màu sắc và kích thước
    colors = []
    for color in product.colors:
        size_data = []
        for size in color.sizes:
            size_data.append({
                "size_name": size.size_name,
            })

        colors.append({
            "color_name": color.color_name,
            "color_code": color.color_code,
            "imageLink": color.imageLink,
            "sizes": size_data  # Thêm danh sách kích thước vào mỗi màu
        })

    try:
        return jsonify({
            "message": f"Thông tin sản phẩm {product.name}",
            "product": {
                "id": product.id,
                "name": product.name,
                "imageLink": product.imageLink,
                "colors": colors
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Lỗi khi xử lý: {str(e)}"}), 500


@main.route("/submit-order", methods=["POST"])
def save_product_to_print_list():
    from app import db

    data = request.get_json()
    order_list = data.get("quantities")

    if not order_list:
        return jsonify({"message": "Loi khong co san pham"}), 400
    try:
        for order in order_list:
            product = Product.query.get(order["product_id"])
            product_code = product.product_code
            color = order["color"]
            size = order["size"]
            quantity = order["quantity"]

            pre_order_info_exist = PreOrderInfo.query.filter_by(product_code=product_code, color=color,
                                                                size=size).first()

            if pre_order_info_exist:
                pre_order_info_exist.quantity += quantity
                db.session.add(pre_order_info_exist)
            else:
                pre_order_info_obj = PreOrderInfo(
                    product_code=product_code,
                    color=color,
                    quantity=quantity,
                    size=size,
                    price=product.current_price,
                    link=product.link)
                db.session.add(pre_order_info_obj)
        db.session.commit()

        return jsonify({"message": f"Thêm thành công!"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Lỗi khi xử lý: {str(e)}"}), 500


@main.route("/pre-order-info", methods=["GET"])
def go_to_cart():
    pre_order_list = PreOrderInfo.query.all()
    return render_template("pre_order_list.html", pre_order_list=pre_order_list, brand="uniqlo")


@main.route("/export-pre-order-data", methods=["POST"])
def export_product_to_order():
    from io import StringIO
    import csv
    from flask import Response

    data = PreOrderInfo.query.all()

    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(["No", "Code", "Quantity", "Size", "Color", "Price", "URL"])
    count = 1
    for row in data:
        writer.writerow([
            count,
            row.product_code,
            row.quantity,
            row.size,
            row.color,
            row.price,
            row.link
        ])
        count += 1

    output = si.getvalue()
    si.close()

    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=pre_order_export.csv"}
    )

@main.route("/delete-pre-order/<int:item_id>", methods=["DELETE"])
def delete_pre_order(item_id):
    from flask import jsonify
    from app.models import PreOrderInfo  # tùy theo cấu trúc project của bạn
    from app import db  # hoặc current_app.db nếu bạn đang dùng factory

    item = PreOrderInfo.query.get(item_id)
    if not item:
        return jsonify({"success": False, "error": "Item not found"}), 404

    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@main.route("/delete-all-pre-order", methods=["DELETE"])
def delete_all_pre_order():
    from flask import jsonify
    from app.models import PreOrderInfo
    from app import db

    try:
        db.session.query(PreOrderInfo).delete()  # xóa toàn bộ bảng
        db.session.commit()
        return jsonify({"success": True, "message": "Đã xóa toàn bộ PreOrderInfo"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

