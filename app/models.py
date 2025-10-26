from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

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
    follow_flag = Column(Boolean, default=False, nullable=False)

    colors = relationship("ProductColor", back_populates="product", cascade="all, delete-orphan")


class ProductColor(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("product.id"), nullable=False)
    color_name = Column(String(255))
    color_code = Column(String(255))
    sizes = relationship("ProductSize", back_populates="color", cascade="all, delete-orphan")
    imageLink = Column(String(500))  # ✅ để lưu link ảnh chip

    product = relationship("Product", back_populates="colors")


class ProductSize(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    color_id = Column(Integer, ForeignKey("product_color.id"), nullable=False)
    size_name = Column(String(255))

    color = relationship("ProductColor", back_populates="sizes")


class OrderDetail(db.Model):
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
    delivery_tracking_link = Column(String(500))
    order_status = Column(String(50))
