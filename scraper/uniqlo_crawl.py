from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import mysql.connector

# Kết nối MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1010",
    database="uniqlo"
)
cursor = conn.cursor()


options = Options()
# options.add_argument("--headless")
driver = webdriver.Chrome(options=options)

driver.get("https://www.uniqlo.com/jp/ja/women/dresses-and-skirts/dresses-and-jumpsuits")
# driver.get("https://www.uniqlo.com/jp/ja/women/bottoms/wide-pants?path=%2C%2C1623%2C")
time.sleep(3)  # chờ JS load

SCROLL_PAUSE_TIME = 2
last_height = driver.execute_script("return document.body.scrollHeight")
current_scroll = 0

while True:
    # Cuộn xuống cuối trang
    SCROLL_STEP = 500  # cuộn từng bước 300px

    while current_scroll < last_height:
        # Cuộn thêm 300px
        current_scroll += SCROLL_STEP
        driver.execute_script(f"window.scrollTo(0, {current_scroll});")
        time.sleep(0.2)


    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    # Chờ lazy-load
    time.sleep(SCROLL_PAUSE_TIME)
    
    # Lấy chiều cao mới của trang
    new_height = driver.execute_script("return document.body.scrollHeight")
    
    # Nếu không thay đổi → đã cuộn hết
    if new_height == last_height:
        break
    last_height = new_height

print("Đã cuộn tới cuối trang")


# Lấy tất cả span có data-testid="CoreBody"
products = driver.find_elements(By.CSS_SELECTOR, "a.product-tile__link")
print("Tong so san pham: " + str(len(products)))

for p in products:
    link = p.get_attribute("href")
    product_code = link.split("/products/E")[1].split("-")[0]
    imageLink = p.find_element(By.CSS_SELECTOR, "img").get_attribute("src")
    name = p.find_element(By.CSS_SELECTOR, "div.product-tile--vertical__content-area div[data-testid='ITOTypography']:nth-child(2)").text
    productPriceDiv = p.find_element(By.CSS_SELECTOR, "div.product-tile--vertical__content-area div[data-testid='ITOContentAlignment'] div[data-testid='ITOTypography']")
    price = int(productPriceDiv.text.replace("¥", "").replace(",", ""))
    discountFlg = "ito-attention-text-color" in productPriceDiv.get_attribute("class")
    # Lưu vào DB
    sql = "INSERT INTO products (product_code, name, price, discountFlg, link, imageLink) VALUES (%s, %s, %s, %s, %s, %s)"
    values = (product_code, name, price, discountFlg, link, imageLink)
    cursor.execute(sql, values)

conn.commit()
cursor.close()
conn.close()
driver.quit()

