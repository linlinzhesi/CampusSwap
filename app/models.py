# ============================================================
# app/models.py
# 作用：定义「数据模型」，即数据库表的 Python 表示
# 每个类 = 一张表，每个属性 = 一个字段（列）
# ============================================================

from datetime import datetime          # 处理日期时间
from sqlalchemy import Column, Integer, String, DateTime   # 列类型
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
