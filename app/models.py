from sqlalchemy import Column, Integer, String, Boolean, DateTime

from app import db


class Product(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_code = Column(String(50))
    name = Column(String(255))
    old_price = Column(Integer)
    current_price = Column(Integer)
    discountFlg = Column(Boolean)
    link = Column(String(500))
    imageLink = Column(String(500))
    category = Column(String(255))
    type = Column(String(255))


class OrderDetail(db.Model):
    status = ["ordered", "ready_to_delivery", "ready_to_receive", "completed", "canceled"]
    id = Column(Integer, primary_key=True, autoincrement=True)
    send_date = Column(DateTime())
    update_date = Column(DateTime())
    sender = Column(String(50))
    receiver_email = Column(String(50))
    order_code = Column(String(50))
    mail_content = Column(String(2000))
    receiver_name = Column(String(255))
    delivery_plan = Column(String(500))
    store_name = Column(String(50))
    receive_dead_line = Column(DateTime())
    delivery_company = Column(String(50))
    delivery_tracking_code = Column(String(50))
    order_status = Column(String(50))
