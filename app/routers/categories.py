# ============================================================
# app/routers/categories.py
# 作用：分类模块的接口（获取分类列表、创建分类）
# 分类是商品的前置数据，先有分类，商品才能挂到分类下
# ============================================================

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from .. import models
from ..database import get_db


router = APIRouter(prefix="/api/categories", tags=["分类"])


# 分类的响应结构（简单，直接用 Pydantic 定义在这里即可）
class CategoryOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


# ------------------------------------------------------------------
# 接口：获取全部分类
# 访问：GET /api/categories
# ------------------------------------------------------------------
@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db)):
    """返回所有分类（按 id 升序）"""
    return db.query(models.Category).order_by(models.Category.id).all()
