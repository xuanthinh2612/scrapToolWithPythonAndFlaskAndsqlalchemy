from sqlalchemy import Column, Integer, String, Boolean

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