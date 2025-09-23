from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_code = Column(String(50), unique=True)
    name = Column(String(255))
    old_price = Column(Integer)
    current_price = Column(Integer)
    discountFlg = Column(Boolean)
    link = Column(String(500))
    imageLink = Column(String(500))