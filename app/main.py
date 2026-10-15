# ============================================================
# app/main.py
# 作用：FastAPI 应用入口，定义所有接口（路由）
# 这是项目的「门面」，所有请求都从这里进来
# ============================================================

from datetime import datetime                    # 处理时间

from fastapi import FastAPI, Depends, HTTPException, status   # FastAPI 核心
from fastapi.middleware.cors import CORSMiddleware           # CORS 跨域中间件
from fastapi.staticfiles import StaticFiles                  # 静态文件服务（托管前端页面）
from fastapi.responses import FileResponse                   # 返回文件（用于返回首页 HTML）
import os                                                   # 操作系统路径处理
from sqlalchemy.orm import Session              # 数据库会话类型

from . import models, schemas, security         # 导入我们的模型、数据结构、安全工具
from .database import engine, get_db, Base      # 导入数据库引擎、会话、基类
from .deps import get_token                     # 导入「从请求头取 token」的依赖
from .routers import products, categories, orders   # 导入商品、分类、订单路由


# ------------------------------------------------------------------
# 第一步：创建 FastAPI 应用实例
# title：应用名，会显示在接口文档页面上
# ------------------------------------------------------------------
app = FastAPI(title="校园二手交易平台")


# ------------------------------------------------------------------
# CORS 跨域支持（重要！）
# 什么是 CORS？浏览器出于安全，默认禁止网页调用「不同源」的接口。
# 我们加这个中间件，就是「告诉浏览器：允许哪些来源的网页调我的接口」。
# 这里开发阶段先允许所有来源（allow_origins=["*"]），生产环境要收紧。
# ------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # 允许所有来源（开发用；生产要改成具体域名）
    allow_credentials=True,
    allow_methods=["*"],           # 允许所有 HTTP 方法（GET/POST/PUT/DELETE...）
    allow_headers=["*"],           # 允许所有请求头
)


# ------------------------------------------------------------------
# 前端页面目录路径
# 前端文件放在项目根目录下的 static/ 文件夹里
# ------------------------------------------------------------------
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")


# ------------------------------------------------------------------
# 第二步：应用启动时，自动创建数据库表
# 原理：Base.metadata.create_all(engine) 会根据 models.py 里定义的类，
#       自动在 MySQL 里建出对应的表（如果表不存在的话）
# 注意：这只适合「开发阶段」偷懒用；生产环境一般用迁移工具(Alembic)管理表结构
# ------------------------------------------------------------------
@app.on_event("startup")
def startup():
    # 先确保数据库存在，再建表
    _create_database_if_not_exists()
    Base.metadata.create_all(bind=engine)
    # 初始化默认分类（如果分类表是空的，就写入几个常用分类）
    _init_default_categories()


def _init_default_categories():
    """第一次启动时，写入几个默认商品分类"""
    from .database import SessionLocal
    db = SessionLocal()
    try:
        # 如果 categories 表已经有数据了，就跳过（避免重复插入）
        if db.query(models.Category).count() > 0:
            return
        # 默认分类列表
        default_names = ["图书教材", "数码电子", "生活用品", "运动户外", "服饰鞋包", "其他"]
        for name in default_names:
            db.add(models.Category(name=name))
        db.commit()
    finally:
        db.close()


def _create_database_if_not_exists():
    """如果 campus_market 数据库不存在，就先创建它。
    因为 SQLAlchemy 连不上「不存在的数据库」，所以要先手动建库。"""
    from sqlalchemy import create_engine, text
    # 注意：这里不带数据库名，只连 MySQL 服务器本身
    from .config import DATABASE_URL
    # 从完整 URL 里拆出「不带库名」的服务器地址
    server_url = DATABASE_URL.rsplit("/", 1)[0] + "/"
    tmp_engine = create_engine(server_url, pool_pre_ping=True)
    with tmp_engine.connect() as conn:
        # 用 CREATE DATABASE IF NOT EXISTS 建库（存在就不重复建）
        conn.execute(text("CREATE DATABASE IF NOT EXISTS campus_market DEFAULT CHARACTER SET utf8mb4"))
        conn.commit()
    tmp_engine.dispose()


# ------------------------------------------------------------------
# 接口 1：健康检查
# 作用：确认服务是否活着，返回一个简单的状态
# 访问：GET /  →  返回 {"status": "ok", "message": "..."}
# ------------------------------------------------------------------
@app.get("/")
def root():
    """返回前端首页（真正的网页界面）"""
    # 如果 static/index.html 存在，就返回它；否则返回 JSON 提示
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "status": "ok",
        "message": "校园二手交易平台 API 运行中",
        "docs": "访问 /docs 查看交互式接口文档",
    }


# ------------------------------------------------------------------
# 接口 2：用户注册
# 访问：POST /api/auth/register
# 请求体：{"username": "xxx", "password": "xxx"}
# ------------------------------------------------------------------
@app.post("/api/auth/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """注册新用户"""
    # 1. 检查用户名是否已存在（查数据库）
    exists = db.query(models.User).filter(models.User.username == user.username).first()
    if exists:
        # 已存在就报 400 错误，提示用户名被占用
        raise HTTPException(status_code=400, detail="用户名已被注册")

    # 2. 把明文密码「哈希」后再存库（绝不存明文！）
    hashed = security.hash_password(user.password)

    # 3. 创建用户对象，写进数据库
    new_user = models.User(username=user.username, password=hashed)
    db.add(new_user)     # 加入会话（暂未提交）
    db.commit()          # 提交事务（真正写进数据库）
    db.refresh(new_user) # 刷新，拿到数据库自动生成的 id、created_at

    # 4. 返回用户信息（不含密码）
    return new_user


# ------------------------------------------------------------------
# 接口 3：用户登录
# 访问：POST /api/auth/login
# 请求体：{"username": "xxx", "password": "xxx"}
# 返回：token + 用户信息
# ------------------------------------------------------------------
@app.post("/api/auth/login", response_model=schemas.Token)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    """用户登录，成功返回 token"""
    # 1. 按用户名查用户
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    # 2. 校验：用户不存在 或 密码不对，都报「用户名或密码错误」
    #    （故意不区分「用户不存在」和「密码错」，避免泄露账号是否存在）
    if not db_user or not security.verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 3. 校验通过，生成 token
    token = security.create_access_token(db_user.id)

    # 4. 返回 token + 用户信息
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": db_user,
    }


# ------------------------------------------------------------------
# 接口 4：获取当前登录用户信息（需要带 token）
# 访问：GET /api/users/me
# 请求头：Authorization: Bearer <你的token>
# 这是一个「受保护」的接口示例：只有登录了才能访问
# ------------------------------------------------------------------
@app.get("/api/users/me", response_model=schemas.UserOut)
def get_me(token: str = Depends(get_token), db: Session = Depends(get_db)):
    """返回当前登录用户的信息"""
    # 1. 解析 token，拿到 user_id；不合法会抛异常
    try:
        user_id = security.decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")

    # 2. 按 id 查用户
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 3. 返回用户信息
    return db_user


# ------------------------------------------------------------------
# 挂载商品、分类路由
# 把 routers 里定义的接口「注册」到主应用上
# ------------------------------------------------------------------
app.include_router(products.router)
app.include_router(categories.router)
app.include_router(orders.router)


# ------------------------------------------------------------------
# 托管前端静态文件（CSS、JS 等）
# 注意：这行必须放在「所有路由之后」，否则会拦截 API 请求
# 作用：把 static 目录下的文件暴露出去，浏览器可以访问 /static/xxx
# ------------------------------------------------------------------
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


