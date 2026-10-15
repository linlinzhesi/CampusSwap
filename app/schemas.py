# ============================================================
# app/schemas.py
# 作用：定义「请求/响应的数据结构」（也叫 Pydantic 模型 / DTO）
#
# 为什么要单独用 schemas，而不是直接用 models？
#   因为「数据库表的结构」和「接口输入输出的结构」是不同的：
#   - 接口不该把密码哈希返回给用户
#   - 注册时不该要求用户传 id（id 是数据库自动生成的）
#   schemas 就是用来「定义接口对外长什么样」，顺便做参数校验。
# ============================================================

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field     # BaseModel 是 Pydantic 的基类
from decimal import Decimal               # 精确小数（钱的正确类型）


# ------------------------------------------------------------------
# 注册请求体：用户注册时，前端要传来的字段
# ------------------------------------------------------------------
class UserCreate(BaseModel):
    # username：用户名，最少 3 个字符（防止过短）
    username: str = Field(..., min_length=3, max_length=50)
    # password：密码，最少 6 个字符
    password: str = Field(..., min_length=6, max_length=50)


# ------------------------------------------------------------------
# 登录请求体
# ------------------------------------------------------------------
class UserLogin(BaseModel):
    username: str
    password: str


# ------------------------------------------------------------------
# 用户信息响应体：返回给前端时，只给「安全」的字段
# 注意：这里没有 password 字段，因为密码绝不能返回出去
# ------------------------------------------------------------------
class UserOut(BaseModel):
    id: int
    username: str
    created_at: datetime

    # 这行让 Pydantic 能直接从 SQLAlchemy 模型对象里取字段值
    # （否则它不认识 SQLAlchemy 的对象，会报错）
    class Config:
        from_attributes = True


# ------------------------------------------------------------------
# 登录成功后的响应体：返回 token 和用户信息
# ------------------------------------------------------------------
class Token(BaseModel):
    access_token: str       # JWT 令牌字符串
    token_type: str = "bearer"   # 令牌类型（固定写法，业界惯例）
    user: UserOut           # 顺便返回用户信息，前端省一次请求


# ============================================================
# 以下是商品模块相关的 schemas
# ============================================================

# ------------------------------------------------------------------
# 发布/创建商品的请求体
# ------------------------------------------------------------------
class ProductCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)   # 标题，必填
    description: Optional[str] = None                        # 描述，可空
    price: Decimal = Field(..., gt=0)                        # 价格，必须 > 0
    category_id: Optional[int] = None                        # 分类 id，可空
    image_url: Optional[str] = None                          # 图片链接，可空
    stock: int = Field(1, ge=1)                              # 库存，默认 1，至少 1


# ------------------------------------------------------------------
# 更新商品的请求体（所有字段都可选，只更新传了的字段）
# Optional = 可以不传这个字段
# ------------------------------------------------------------------
class ProductUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0)
    category_id: Optional[int] = None
    image_url: Optional[str] = None
    status: Optional[int] = None    # 1=在售，0=下架
    stock: Optional[int] = Field(None, ge=0)   # 库存，允许设为 0（售罄）


# ------------------------------------------------------------------
# 商品响应体：返回给前端时，附带卖家用户名
# ------------------------------------------------------------------
class ProductOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    price: Decimal
    category_id: Optional[int]
    image_url: Optional[str]
    seller_id: int
    view_count: int
    status: int
    stock: int
    created_at: datetime
    # 卖家用户名（从 relationship 拿的，方便前端直接显示「卖家：张三」）
    seller_name: Optional[str] = None

    class Config:
        from_attributes = True


# ------------------------------------------------------------------
# 商品列表响应体：分页结果
# total = 符合条件的总条数，items = 当前页的商品列表
# 前端靠 total 算「一共有几页」，靠 items 渲染当前页
# ------------------------------------------------------------------
class ProductListOut(BaseModel):
    total: int
    items: List[ProductOut]
    page: int
    size: int


# ============================================================
# 以下是订单模块相关的 schemas（S3）
# ============================================================

# ------------------------------------------------------------------
# 下单请求体
# order_no：订单号（幂等键），由前端生成并保证唯一
#           例如用「时间戳 + 随机数」生成
# ------------------------------------------------------------------
class OrderCreate(BaseModel):
    product_id: int
    quantity: int = Field(1, ge=1)        # 购买数量，至少 1
    order_no: str = Field(..., min_length=1, max_length=64)  # 幂等键，必填


# ------------------------------------------------------------------
# 订单响应体
# ------------------------------------------------------------------
class OrderOut(BaseModel):
    id: int
    order_no: str
    product_id: int
    buyer_id: int
    seller_id: int
    quantity: int
    total_price: Decimal
    status: int
    created_at: datetime
    # 附带的展示信息（方便前端直接显示）
    product_title: Optional[str] = None

    class Config:
        from_attributes = True
