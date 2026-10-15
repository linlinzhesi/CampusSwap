# ============================================================
# app/routers/orders.py
# 作用：订单模块的所有接口（S3 核心）
#
# 这里实现了两个后端最重要的「高并发/一致性」技术点：
#   1. 防超卖（库存扣减的原子性）
#   2. 幂等性（防止重复下单）
# 面试几乎必问，务必理解透。
# ============================================================

import uuid                                            # 生成唯一编号（备用）
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError              # 捕获「唯一约束冲突」异常

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user


router = APIRouter(prefix="/api/orders", tags=["订单"])


# ------------------------------------------------------------------
# 接口 1：下单（核心接口，需要登录）
# 访问：POST /api/orders
# 请求体：{"product_id": 1, "quantity": 1, "order_no": "唯一订单号"}
#
# 这是整个项目技术含量最高的接口，逻辑分几步，逐步看：
# ------------------------------------------------------------------
@router.post("", response_model=schemas.OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(
    order: schemas.OrderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """下单购买商品（含防超卖 + 幂等保护）"""

    # ---------- 第一步：幂等检查（先于一切） ----------
    # 先查这个 order_no 是否已经下过单。如果已经存在，直接返回已存在的订单，
    # 不再往下扣库存。这样「重复提交」在任何情况下都能被正确拦截，
    # 而不是等扣完库存才发现重复。
    existing = db.query(models.Order).filter(models.Order.order_no == order.order_no).first()
    if existing:
        # 幂等：返回「已存在」，HTTP 409 冲突
        raise HTTPException(status_code=409, detail=f"订单已存在（订单号 {order.order_no}），请勿重复提交")

    # ---------- 第二步：查商品 ----------
    product = db.query(models.Product).filter(models.Product.id == order.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    if product.status != 1:
        raise HTTPException(status_code=400, detail="商品已下架")
    # 不能买自己发布的商品（业务规则，可选）
    if product.seller_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能购买自己发布的商品")

    # ---------- 第三步：防超卖 —— 原子扣减库存 ----------
    # 这是关键！我们用「条件 UPDATE」在数据库层面原子地扣库存：
    #
    #   UPDATE products
    #   SET stock = stock - :qty
    #   WHERE id = :pid AND stock >= :qty
    #
    # 为什么这样能防超卖？
    #   - 「判断库存够不够」和「扣库存」在【同一条 SQL】里完成，
    #     数据库会保证这条语句的执行是原子的（不会被并发打断）。
    #   - 如果两个请求同时来，数据库会串行处理，第一个扣成功（stock 变 0），
    #     第二个再来时 stock >= qty 不成立，更新影响 0 行 → 我们据此报「库存不足」。
    #
    # 如果用「先查库存再扣」的两步写法（先 SELECT 再 UPDATE），
    # 两个请求可能都查到 stock=1，然后都去扣，就超卖了。这就是「两步」的经典 bug。
    from sqlalchemy import update
    result = db.execute(
        update(models.Product)
        .where(models.Product.id == order.product_id, models.Product.stock >= order.quantity)
        .values(stock=models.Product.stock - order.quantity)
    )
    # rowcount = 实际被更新的行数。0 表示库存不够（没更新到）
    if result.rowcount == 0:
        raise HTTPException(status_code=400, detail="库存不足")

    # ---------- 第四步：生成订单 ----------
    total = product.price * order.quantity
    new_order = models.Order(
        order_no=order.order_no,              # 幂等键
        product_id=order.product_id,
        buyer_id=current_user.id,
        seller_id=product.seller_id,
        quantity=order.quantity,
        total_price=total,
        status=1,                              # 待处理
    )
    db.add(new_order)
    try:
        db.commit()
    except IntegrityError:
        # 兜底：极端并发下，两个请求同时通过了第一步检查、又同时写订单，
        # 唯一约束会兜住最后一个（这是数据库层面的最终保障）。
        db.rollback()
        raise HTTPException(status_code=409, detail=f"订单已存在（订单号 {order.order_no}），请勿重复提交")

    db.refresh(new_order)
    return new_order


# ------------------------------------------------------------------
# 接口 2：查询我的订单（作为买家的订单，需要登录）
# 访问：GET /api/orders
# ------------------------------------------------------------------
@router.get("", response_model=list[schemas.OrderOut])
def list_my_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """查询当前用户作为买家的所有订单"""
    orders = (
        db.query(models.Order)
        .filter(models.Order.buyer_id == current_user.id)
        .order_by(models.Order.created_at.desc())
        .all()
    )
    # 给每个订单附带商品标题（方便前端展示）
    for o in orders:
        o.product_title = o.product.title if o.product else None
    return orders


# ------------------------------------------------------------------
# 接口 3：查询我卖出的订单（作为卖家的订单，需要登录）
# 访问：GET /api/orders/sold
# ------------------------------------------------------------------
@router.get("/sold", response_model=list[schemas.OrderOut])
def list_sold_orders(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """查询当前用户作为卖家的订单（谁买了我的东西）"""
    orders = (
        db.query(models.Order)
        .filter(models.Order.seller_id == current_user.id)
        .order_by(models.Order.created_at.desc())
        .all()
    )
    for o in orders:
        o.product_title = o.product.title if o.product else None
    return orders
