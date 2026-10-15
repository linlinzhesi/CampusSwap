# ============================================================
# app/deps.py
# 作用：定义「依赖函数」（Dependency），供各接口复用
#
# 什么是依赖函数？
#   FastAPI 里，很多接口都需要「先校验登录、拿到当前用户」这个前置步骤。
#   与其在每个接口里重复写这段代码，不如把它抽成一个函数，
#   然后在接口参数里写 `Depends(get_current_user)` 就能自动调用。
#   这就是 FastAPI 的「依赖注入」——代码复用、逻辑集中、易维护。
# ============================================================

from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from . import models, security
from .database import get_db


# ------------------------------------------------------------------
# 依赖：从请求头提取 Bearer token
# 返回 token 字符串；没带或格式错就报 401
# ------------------------------------------------------------------
def get_token(authorization: str = Header(None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少登录凭证")
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="登录凭证格式错误")
    return parts[1]


# ------------------------------------------------------------------
# 依赖：获取「当前登录的用户」
# 这是最常用的一个依赖：任何需要登录的接口，都可以用它拿到用户对象
#
# 用法：在接口函数参数里写  current_user: models.User = Depends(get_current_user)
# FastAPI 会自动执行这个函数，把返回的用户对象传进接口
# ------------------------------------------------------------------
def get_current_user(
    token: str = Depends(get_token),   # 先依赖 get_token 拿到 token
    db: Session = Depends(get_db),     # 再依赖 get_db 拿到数据库会话
) -> models.User:
    """解析 token，返回当前登录用户；token 无效则报 401"""
    # 1. 解析 token 拿到 user_id，解析失败说明 token 非法/过期
    try:
        user_id = security.decode_access_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")

    # 2. 按 id 查用户
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    # 3. 返回用户对象，供接口使用
    return user
