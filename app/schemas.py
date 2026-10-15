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
from pydantic import BaseModel, Field     # BaseModel 是 Pydantic 的基类


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
