from flask import Blueprint, render_template, request, redirect, url_for
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import os

main = Blueprint("main", __name__)
is_running = False

def start_crawl_uniqlo():
    from run import app  # import app ở đây

    global is_running
    if is_running: return
    is_running = True

    # Đường dẫn tuyệt đối đến folder chứa file này
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(BASE_DIR, "data", "productAllURL.txt")

    urls = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:  # bỏ dòng trống
                continue
            parts = line.split(",", 1)  # tách thành 2 phần (category, url)
            if len(parts) == 2:
                category, url = parts
                urls.append((category.strip(), url.strip()))

    # gọi crawl cho từng category + url
    try:
        # crawl code
        for category, url in urls:
            print(f"▶ Crawling {category} - {url}")
                # Tạo app context cho thread này
            with app.app_context():
                uniqlo_crawl(category, url)  #  db.session.commit() sẽ hoạt động trong context
    finally:
        is_running = False

    return urls


def uniqlo_crawl(category, url):
    from app import db
    from app.models import Product

    options = Options()
    # options.add_argument("--headless")  # bật nếu muốn chạy ngầm
    driver = webdriver.Chrome(options=options)

    driver.get(url)
    time.sleep(3)

    SCROLL_PAUSE_TIME = 2
    last_height = driver.execute_script("return document.body.scrollHeight")
    current_scroll = 0

    while True:
        SCROLL_STEP = 500
        while current_scroll < last_height:
            current_scroll += SCROLL_STEP
            driver.execute_script(f"window.scrollTo(0, {current_scroll});")
            time.sleep(0.2)

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(SCROLL_PAUSE_TIME)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    products = driver.find_elements(By.CSS_SELECTOR, "a.product-tile__link")
    for p in products:
        try:
            link = p.get_attribute("href")
            product_code = link.split("/products/E")[1].split("-")[0]
            imageLink = p.find_element(By.CSS_SELECTOR, "img").get_attribute("src")
            name = p.find_element(By.CSS_SELECTOR,
                                  "div.product-tile--vertical__content-area div[data-testid='ITOTypography']:nth-child(2)").text
            productPriceDiv = p.find_element(By.CSS_SELECTOR,
                                             "div.product-tile--vertical__content-area div[data-testid='ITOContentAlignment'] div[data-testid='ITOTypography']")
            price = int(productPriceDiv.text.replace("¥", "").replace(",", ""))
            discountFlg = "ito-attention-text-color" in productPriceDiv.get_attribute("class")

            # Check xem product đã tồn tại chưa
            existing_product = Product.query.filter_by(product_code=product_code, link = link).first()
            if existing_product:
                # Update thông tin nếu đã tồn tại
                existing_product.name = name
                existing_product.current_price = price
                if price > existing_product.old_price:
                    existing_product.old_price = price
                existing_product.discountFlg = discountFlg
                existing_product.link = link
                existing_product.imageLink = imageLink
            else:
                # Thêm mới
                new_product = Product(
                    category=category,
                    product_code=product_code,
                    name=name,
                    old_price=price,
                    current_price=price,
                    discountFlg=discountFlg,
                    link=link,
                    imageLink=imageLink
                )
                db.session.add(new_product)
        except Exception as e:
            print("Lỗi khi check sản phẩm:", e)
            driver.quit()


    db.session.commit()
    driver.quit()
