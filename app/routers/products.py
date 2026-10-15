# ============================================================
# app/routers/products.py
# 作用：商品模块的所有接口（路由）
#
# 为什么单独放一个 routers 目录？
#   随着功能变多，如果所有接口都堆在 main.py，文件会越来越长、难维护。
#   所以按「业务模块」拆分：用户相关在 main.py，商品相关在这个文件。
#   这是后端项目的标准组织方式（分层 + 分模块）。
# ============================================================

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_user


# ------------------------------------------------------------------
# 创建一个「路由对象」
# prefix="/api/products"：这个文件里所有接口的路径都会自动带上这个前缀
# tags=["商品"]：在接口文档里把这些接口归到「商品」分组
# ------------------------------------------------------------------
router = APIRouter(prefix="/api/products", tags=["商品"])


# ------------------------------------------------------------------
# 接口 1：发布商品（需要登录）
# 访问：POST /api/products
# 请求体：{"title": "...", "price": 10.5, "category_id": 1, ...}
# ------------------------------------------------------------------
@router.post("", response_model=schemas.ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(
    product: schemas.ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),  # 自动拿到当前登录用户
):
    """发布一个新商品。seller 自动设为当前登录用户"""
    # 如果传了 category_id，先校验这个分类是否存在
    if product.category_id is not None:
        category = db.query(models.Category).filter(models.Category.id == product.category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="分类不存在")

    # 创建商品对象，seller_id 用当前登录用户的 id
    # 注意：seller_id 来自 token，而不是前端传参——这样用户无法冒充别人发商品
    new_product = models.Product(
        title=product.title,
        description=product.description,
        price=product.price,
        category_id=product.category_id,
        image_url=product.image_url,
        seller_id=current_user.id,   # 关键：卖家是「当前登录用户」，不是前端传的
    )
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


# ------------------------------------------------------------------
# 接口 2：浏览商品列表（公开，无需登录）
# 访问：GET /api/products?page=1&size=10&category_id=1&keyword=书
#
# 支持三个筛选条件（都是可选的）：
#   - page/size：分页（第几页、每页几条）
#   - category_id：按分类筛选
#   - keyword：按关键词搜索（模糊匹配标题或描述）
# ------------------------------------------------------------------
@router.get("", response_model=schemas.ProductListOut)
def list_products(
    page: int = Query(1, ge=1),           # 页码，默认 1，最小 1
    size: int = Query(10, ge=1, le=100),  # 每页条数，默认 10，范围 1~100
    category_id: Optional[int] = Query(None),  # 分类筛选，可空
    keyword: Optional[str] = Query(None),      # 关键词搜索，可空
    db: Session = Depends(get_db),
):
    """分页浏览商品，支持分类筛选和关键词搜索"""

    # 1. 先构造一个「基础查询」，默认只看「在售」的商品
    #    （status == 1 表示在售，下架的商品不展示给买家）
    query = db.query(models.Product).filter(models.Product.status == 1)

    # 2. 如果传了分类，追加分类筛选条件
    if category_id is not None:
        query = query.filter(models.Product.category_id == category_id)

    # 3. 如果传了关键词，追加模糊搜索
    #    like 是 SQL 的模糊匹配，%关键字% 表示「包含这个关键字」
    #    or_ 表示「标题或描述」只要有一个匹配就返回
    if keyword:
        from sqlalchemy import or_
        query = query.filter(or_(
            models.Product.title.like(f"%{keyword}%"),
            models.Product.description.like(f"%{keyword}%"),
        ))

    # 4. 先查「总条数」（用于前端算总页数）
    total = query.count()

    # 5. 分页：offset 跳过前面几页，limit 只取当前页
    #    例：page=2, size=10 → offset=10, limit=10 → 取第 11~20 条
    #    再按「发布时间倒序」排列（最新的在前）
    products = query.order_by(models.Product.created_at.desc()) \
                    .offset((page - 1) * size) \
                    .limit(size) \
                    .all()

    # 6. 返回结果
    return {
        "total": total,
        "items": products,
        "page": page,
        "size": size,
    }


# ------------------------------------------------------------------
# 接口 3：查看商品详情（公开，无需登录）
# 访问：GET /api/products/{id}
# 特殊逻辑：每访问一次，浏览量 view_count +1
# ------------------------------------------------------------------
@router.get("/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """查看商品详情，浏览量 +1"""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 浏览量 +1（访问详情就计数）
    product.view_count += 1
    db.commit()
    db.refresh(product)
    return product


# ------------------------------------------------------------------
# 接口 4：修改自己的商品（需要登录，且只能改自己的）
# 访问：PUT /api/products/{id}
# 请求体：只传要改的字段（如 {"price": 8.5}）
# ------------------------------------------------------------------
@router.put("/{product_id}", response_model=schemas.ProductOut)
def update_product(
    product_id: int,
    product_data: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """修改商品，仅限卖家本人"""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 关键：校验「这个商品是不是当前登录用户发布的」
    # 如果不是，报 403 禁止操作（防止用户改别人的商品，这叫「越权防护」）
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作他人的商品")

    # 只更新「前端实际传了」的字段（exclude_unset 会自动忽略没传的字段）
    data = product_data.model_dump(exclude_unset=True)

    # 如果要改分类，校验新分类是否存在
    if "category_id" in data and data["category_id"] is not None:
        category = db.query(models.Category).filter(models.Category.id == data["category_id"]).first()
        if not category:
            raise HTTPException(status_code=400, detail="分类不存在")

    # 逐个字段赋值更新
    for field, value in data.items():
        setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


# ------------------------------------------------------------------
# 接口 5：下架/删除商品（需要登录，且只能删自己的）
# 访问：DELETE /api/products/{id}
# 这里用「软下架」：把 status 设为 0，而不是真的从数据库删掉
# 这样数据还在，只是买家看不到了（实际项目常用软删除，便于追溯）
# ------------------------------------------------------------------
@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """下架商品（软删除），仅限卖家本人"""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")

    # 越权防护：只能下架自己的商品
    if product.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作他人的商品")

    # 软删除：status 设为 0（下架），数据保留
    product.status = 0
    db.commit()
    # 204 表示「成功但无返回内容」
    return None
