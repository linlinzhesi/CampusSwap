# ============================================================
# app/models.py
# 作用：定义「数据模型」，即数据库表的 Python 表示
# 每个类 = 一张表，每个属性 = 一个字段（列）
# ============================================================

from datetime import datetime          # 处理日期时间
# 列类型：Integer整数/String字符串/DateTime日期时间/Text长文本/Numeric精确小数/Float浮点
from sqlalchemy import Column, Integer, String, DateTime, Text, Numeric, Float
from sqlalchemy import ForeignKey      # 外键（表与表之间的关联）
from sqlalchemy.orm import relationship  # 关系（让两个模型能互相访问对方的数据）
from .database import Base             # 导入基类


# ------------------------------------------------------------------
# User 模型：用户表（对应数据库里的 users 表）
# ------------------------------------------------------------------
class User(Base):
    # 表名（数据库里这张表就叫 users）
    __tablename__ = "users"

    # id：主键，自增。每个用户唯一标识
    id = Column(Integer, primary_key=True, index=True)

    # username：用户名，唯一（不能重复），最长 50 字符
    # unique=True 会在数据库层面加唯一约束，防止注册重名
    username = Column(String(50), unique=True, nullable=False, index=True)

    # password：密码的「哈希值」（注意：存的是哈希，不是明文！）
    # 哈希结果较长（bcrypt 是 60 字符），所以给 255 长度
    password = Column(String(255), nullable=False)

    # created_at：注册时间，默认取当前时间
    created_at = Column(DateTime, default=datetime.now)

    # 这个 __repr__ 只是方便打印调试时看得清，不是必须的
    def __repr__(self):
        return f"<User id={self.id} username={self.username}>"


# ------------------------------------------------------------------
# Category 模型：商品分类表（对应 categories 表）
# 例如：图书、数码、生活用品、运动、其他
# ------------------------------------------------------------------
class Category(Base):
    __tablename__ = "categories"

    # id：主键
    id = Column(Integer, primary_key=True, index=True)

    # name：分类名，唯一（不能有两个同名分类）
    name = Column(String(50), unique=True, nullable=False)

    def __repr__(self):
        return f"<Category id={self.id} name={self.name}>"


# ------------------------------------------------------------------
# Product 模型：商品表（对应 products 表）
# 这是本项目的核心表，一个商品就是一行记录
# ------------------------------------------------------------------
class Product(Base):
    __tablename__ = "products"

    # id：主键，自增
    id = Column(Integer, primary_key=True, index=True)

    # title：商品标题（如「九成新《算法导论》」）
    title = Column(String(100), nullable=False)

    # description：商品描述（长文本，如「考研用书，几乎全新」）
    description = Column(Text, nullable=True)

    # price：价格
    # 注意：钱绝不能用 Float（浮点数有精度问题，0.1+0.2≠0.3）
    # 正确做法是用 Numeric(10,2)，精确到分。这是后端的一个经典坑
    price = Column(Numeric(10, 2), nullable=False)

    # category_id：分类，外键指向 categories.id
    # ForeignKey 表示「这个字段的值，必须是另一张表里存在的 id」
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)

    # image_url：商品图片链接（可空，这周先不做图片上传，允许填链接）
    image_url = Column(String(500), nullable=True)

    # seller_id：卖家，外键指向 users.id
    # 这个字段标明了「这个商品是谁发的」，改/删商品时靠它校验归属
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # view_count：浏览量，默认 0，每看一次详情 +1
    view_count = Column(Integer, default=0)

    # status：商品状态，1=在售，0=下架。默认 1（发布即上架）
    status = Column(Integer, default=1)

    # stock：库存数量。默认 1（二手闲置通常只有 1 件）
    # 这是 S3 防超卖的核心字段：下单时会对它做「条件扣减」
    stock = Column(Integer, default=1, nullable=False)

    # created_at：发布时间
    created_at = Column(DateTime, default=datetime.now)

    # ------------------------------------------------------------------
    # relationship：定义「关系」，让我们能方便地从商品对象直接拿到卖家信息
    # 例如：product.seller.username 就能直接拿到卖家的用户名，
    #       不用自己再去查一次 users 表。这是 ORM 的便利之处。
    # ------------------------------------------------------------------
    seller = relationship("User", backref="products")

    # ------------------------------------------------------------------
    # seller_name：这是「虚拟属性」（不是数据库字段，只是个 property）
    # 作用：方便接口返回「卖家用户名」这个展示字段
    # 通过 seller relationship 拿到卖家对象，再取用户名
    # ------------------------------------------------------------------
    @property
    def seller_name(self):
        return self.seller.username if self.seller else None

    def __repr__(self):
        return f"<Product id={self.id} title={self.title} price={self.price}>"


# ------------------------------------------------------------------
# Order 模型：订单表（对应 orders 表）
# S3 新增。用户下单购买商品时，生成一条订单记录
# ------------------------------------------------------------------
class Order(Base):
    __tablename__ = "orders"

    # id：主键，自增
    id = Column(Integer, primary_key=True, index=True)

    # order_no：订单号（业务上的唯一编号，形如 "20261015123045xxxxxx"）
    # unique=True 是关键！这是「幂等性」的保障：
    #   前端每次下单都生成一个唯一 order_no，
    #   如果同一 order_no 重复提交，数据库会因为唯一约束拒绝第二次，
    #   从而防止「重复下单」。这是防重复的核心机制。
    order_no = Column(String(64), unique=True, nullable=False, index=True)

    # product_id：买了哪个商品（外键）
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    # buyer_id：买家（外键，指向 users.id）
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # seller_id：卖家（冗余存一份，方便卖家查自己的订单）
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # quantity：购买数量（二手通常 1 件，但设计上支持多件）
    quantity = Column(Integer, default=1, nullable=False)

    # total_price：订单总金额 = 单价 × 数量
    total_price = Column(Numeric(10, 2), nullable=False)

    # status：订单状态
    #   0=已取消，1=待处理（下单成功），2=已完成
    #   二手交易没有在线支付，所以状态相对简单
    status = Column(Integer, default=1, nullable=False)

    # created_at：下单时间
    created_at = Column(DateTime, default=datetime.now)

    # 关系：方便拿到商品、买家、卖家对象
    product = relationship("Product", foreign_keys=[product_id])
    buyer = relationship("User", foreign_keys=[buyer_id])

    def __repr__(self):
        return f"<Order id={self.id} order_no={self.order_no}>"
