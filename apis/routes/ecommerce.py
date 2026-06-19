"""
apis.routes.ecommerce — 前台电商 API

路由前缀: /api/v1/shop/{site_id}
接收前端（生成的电商网站）的请求，实现商品浏览、购物车、结算、评价功能。

访客购物车基于 Cookie（sg_cart_id）识别，无需登录。
管理 API（商品/订单管理）放在 auth.py 中。
"""

from apis.file_lock import safe_read_json, safe_write_json
import json
import uuid
import time
import hashlib
import hmac
import secrets
import base64
import logging
from datetime import datetime
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Any

logger = logging.getLogger(__name__)
from apis.routes.auth import get_current_user, _is_pro
from fastapi import APIRouter, HTTPException, Request, Depends, Cookie, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from collections import defaultdict
import time as _time

router = APIRouter(prefix="/shop", tags=["电商前台"])

# ── 优惠券速率限制（后端）───────────────────────────
_coupon_attempts: defaultdict[str, list[float]] = defaultdict(list)
COUPON_RATE_LIMIT = 10  # 每IP每分钟最多10次
COUPON_RATE_WINDOW = 60  # 秒

def _check_coupon_rate(ip: str) -> None:
    now = _time.time()
    cutoff = now - COUPON_RATE_WINDOW
    _coupon_attempts[ip] = [t for t in _coupon_attempts[ip] if t > cutoff]
    if len(_coupon_attempts[ip]) >= COUPON_RATE_LIMIT:
        raise HTTPException(429, "优惠码尝试太频繁，请稍后再试")
    _coupon_attempts[ip].append(now)

# ══════════════════════════════════════════════════════════════
# 数据目录 & JSON 工具
# ══════════════════════════════════════════════════════════════
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)

def _site_config_path(site_id: str) -> Path:
    return DATA_DIR / f"site_config_{site_id}.json"

def _products_path(site_id: str) -> Path:
    return DATA_DIR / f"products_{site_id}.json"

def _orders_path(site_id: str) -> Path:
    return DATA_DIR / f"orders_{site_id}.json"

def _cart_path(cart_id: str) -> Path:
    return DATA_DIR / f"carts_{cart_id}.json"

def _coupons_path(site_id: str) -> Path:
    return DATA_DIR / f"coupons_{site_id}.json"

def _reviews_path(site_id: str) -> Path:
    return DATA_DIR / f"reviews_{site_id}.json"

def _shipping_path(site_id: str) -> Path:
    return DATA_DIR / f"shipping_{site_id}.json"

def _payment_config_path(site_id: str) -> Path:
    return DATA_DIR / f"payment_config_{site_id}.json"

def _load_json(path: Path) -> Any:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None

def _save_json(path: Path, data: Any):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _round_money(amount: Any) -> float:
    """精确到分，保留2位小数"""
    d = Decimal(str(amount))
    return float(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

# ══════════════════════════════════════════════════════════════
# site_id 验证依赖
# ══════════════════════════════════════════════════════════════
async def _verify_site(request: Request, site_id: str) -> dict:
    """验证 site_id 存在，防止跨站点访问"""
    config = _load_json(_site_config_path(site_id))
    if config is None:
        raise HTTPException(404, "站点不存在")
    return config

# ══════════════════════════════════════════════════════════════
# 商品数据层（JSON-backed Store）
# ══════════════════════════════════════════════════════════════
class ProductStore:
    """商品存储，读写 data/products_{site_id}.json"""

    def __init__(self, site_id: str):
        self.path = _products_path(site_id)

    def _load(self) -> dict:
        data = _load_json(self.path)
        if not data:
            return {"products": []}
        # 兼容 core.ecommerce.store 存的纯 list 格式
        if isinstance(data, list):
            return {"products": data}
        return data

    def list(
        self,
        category: str = None,
        keyword: str = None,
        featured: bool = False,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        """商品列表，支持筛选和分页"""
        data = self._load()
        products = data.get("products", [])

        # 筛选
        if category:
            products = [p for p in products if p.get("category_id") == category or p.get("category") == category]
        if keyword:
            kw = keyword.lower()
            products = [
                p for p in products
                if kw in p.get("name", "").lower()
                or kw in p.get("description", "").lower()
            ]
        if featured:
            products = [p for p in products if p.get("featured", False)]

        # 排序：上架时间倒序
        products = sorted(products, key=lambda p: p.get("created_at", ""), reverse=True)

        total = len(products)
        total_pages = (total + per_page - 1) // per_page
        start = (page - 1) * per_page
        page_products = products[start : start + per_page]

        # 价格范围（从 variants 或 顶层 price 取）
        all_prices = []
        for p in data.get("products", []):
            if p.get("price"):
                all_prices.append(p["price"])
            elif p.get("variants"):
                for v in p["variants"]:
                    if v.get("price"):
                        all_prices.append(v["price"])
        filters = {
            "min_price": min(all_prices) if all_prices else 0,
            "max_price": max(all_prices) if all_prices else 0,
        }

        # 分类聚合
        cat_map: dict = {}
        for p in data.get("products", []):
            cid = p.get("category_id") or p.get("category")
            if cid:
                cat_map[cid] = cat_map.get(cid, 0) + 1
        categories = [{"id": k, "count": v} for k, v in cat_map.items()]

        return {
            "products": page_products,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
            },
            "categories": categories,
            "filters": filters,
        }

    def get(self, product_id: str) -> Optional[dict]:
        """商品详情"""
        data = self._load()
        for p in data.get("products", []):
            if p.get("id") == product_id:
                return p
        return None

    def related(self, product_id: str, limit: int = 4) -> list:
        """相关商品（同分类）"""
        product = self.get(product_id)
        if not product:
            return []
        data = self._load()
        cid = product.get("category_id") or product.get("category")
        related = [
            p for p in data.get("products", [])
            if p.get("id") != product_id and (p.get("category_id") or p.get("category")) == cid
        ]
        return related[:limit]

    def reduce_stock(self, variant_id: str, qty: int) -> bool:
        """扣减库存（返回是否成功，库存不足时返回False）"""
        data = self._load()
        updated = False
        for p in data.get("products", []):
            for v in p.get("variants", []):
                if v.get("id") == variant_id:
                    current = v.get("stock", 0)
                    if current < qty:
                        return False  # 库存不足，不扣减
                    v["stock"] = current - qty
                    updated = True
        if updated:
            _save_json(self.path, data)
        return updated

    def stock_of(self, product_id: str, variant_id: str) -> int:
        """查询库存"""
        p = self.get(product_id)
        if not p:
            return 0
        for v in p.get("variants", []):
            if v.get("id") == variant_id:
                return v.get("stock", 0)
        return 0


class CategoryStore:
    """分类存储，读写 site_config（内含分类树）"""

    def __init__(self, site_id: str):
        self.site_id = site_id

    def tree(self) -> list:
        """返回树状分类列表"""
        config = _load_json(_site_config_path(self.site_id))
        return config.get("categories", []) if config else []


class CartStore:
    """购物车存储，读写 data/carts_{cart_id}.json"""

    def __init__(self, cart_id: str):
        self.cart_id = cart_id
        self.path = _cart_path(cart_id)

    def _load(self) -> dict:
        data = _load_json(self.path)
        return data if data else {"items": [], "coupon_code": None}

    def _save(self, data: dict):
        _save_json(self.path, data)

    def get(self) -> dict:
        return self._load()

    def add_item(self, product_id: str, variant_id: str, quantity: int) -> dict:
        """添加商品到购物车"""
        data = self._load()
        items = data.get("items", [])

        # 检查是否已存在（同一商品+规格）
        for item in items:
            if item["product_id"] == product_id and item["variant_id"] == variant_id:
                item["quantity"] += quantity
                self._save(data)
                return data

        items.append({
            "id": uuid.uuid4().hex[:12],
            "product_id": product_id,
            "variant_id": variant_id,
            "quantity": quantity,
            "added_at": datetime.now().isoformat(),
        })
        data["items"] = items
        self._save(data)
        return data

    def update_item(self, item_id: str, quantity: int) -> dict:
        """修改商品数量"""
        data = self._load()
        items = data.get("items", [])
        for item in items:
            if item["id"] == item_id:
                if quantity <= 0:
                    items.remove(item)
                else:
                    item["quantity"] = quantity
                self._save(data)
                return data
        raise HTTPException(404, "购物车项不存在")

    def remove_item(self, item_id: str) -> dict:
        """删除购物车商品"""
        data = self._load()
        items = data.get("items", [])
        for i, item in enumerate(items):
            if item["id"] == item_id:
                items.pop(i)
                data["items"] = items
                self._save(data)
                return data
        raise HTTPException(404, "购物车项不存在")

    def clear(self) -> dict:
        """清空购物车"""
        self._save({"items": [], "coupon_code": None})
        return {"items": [], "coupon_code": None}

    def apply_coupon(self, code: str, site_id: str) -> dict:
        """应用优惠券"""
        coupons_data = _load_json(_coupons_path(site_id))
        if not coupons_data:
            raise HTTPException(400, "优惠券不存在")

        # 兼容 list 和 dict 两种格式
        coupons = coupons_data if isinstance(coupons_data, list) else coupons_data.get("coupons", [])
        found = None
        for c in coupons:
            if c.get("code", "").upper() == code.upper():
                found = c
                break

        if not found:
            raise HTTPException(400, "优惠券不存在")
        if found.get("used_count", 0) >= found.get("max_uses", 999):
            raise HTTPException(400, "优惠券已用完")
        if found.get("min_order", 0) > 0:
            raise HTTPException(400, f"订单金额需满{found['min_order']}元")

        data = self._load()
        data["coupon_code"] = code.upper()
        self._save(data)
        return data

    def remove_coupon(self) -> dict:
        """移除优惠券"""
        data = self._load()
        data["coupon_code"] = None
        self._save(data)
        return data


class OrderStore:
    """订单存储，读写 data/orders_{site_id}.json"""

    def __init__(self, site_id: str):
        self.site_id = site_id
        self.path = _orders_path(site_id)

    def _load(self) -> dict:
        data = _load_json(self.path)
        if not data:
            return {"orders": []}
        if isinstance(data, list):
            return {"orders": data}
        return data

    def _save(self, data: dict):
        _save_json(self.path, data)

    def create(
        self,
        items: list,
        shipping_address: dict,
        payment_method: str,
        coupon_code: str,
        notes: str,
        site_id: str,
        cart_id: str = None,
    ) -> dict:
        """创建订单"""
        order_id = uuid.uuid4().hex[:12]
        order_no = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}{secrets.token_hex(2).upper()}"
        now = datetime.now().isoformat()

        order = {
            "id": order_id,
            "order_no": order_no,
            "status": "pending",
            "items": items,
            "shipping_address": shipping_address,
            "payment_method": payment_method,
            "coupon_code": coupon_code or None,
            "notes": notes or "",
            "subtotal": 0,
            "shipping_fee": 0,
            "discount": 0,
            "total": 0,
            "cart_id": cart_id,
            "created_at": now,
            "paid_at": None,
            "pay_url": None,
        }

        data = self._load()
        data.setdefault("orders", []).append(order)
        self._save(data)
        return order

    def get(self, order_id: str) -> Optional[dict]:
        """查询订单"""
        data = self._load()
        for o in data.get("orders", []):
            if o.get("id") == order_id:
                return o
        return None

    def get_by_no(self, order_no: str) -> Optional[dict]:
        """按订单号查询"""
        data = self._load()
        for o in data.get("orders", []):
            if o.get("order_no") == order_no:
                return o
        return None

    def update_status(self, order_id: str, status: str) -> Optional[dict]:
        """更新订单状态"""
        data = self._load()
        for o in data.get("orders", []):
            if o.get("id") == order_id:
                o["status"] = status
                if status == "paid":
                    o["paid_at"] = datetime.now().isoformat()
                self._save(data)
                return o
        return None

    def update_pay_url(self, order_id: str, pay_url: str) -> Optional[dict]:
        """存储支付链接"""
        data = self._load()
        for o in data.get("orders", []):
            if o.get("id") == order_id:
                o["pay_url"] = pay_url
                self._save(data)
                return o
        return None

    def list_by_contact(self, contact: str) -> list:
        """按手机号或邮箱查询订单列表"""
        data = self._load()
        results = []
        for o in data.get("orders", []):
            addr = o.get("shipping_address", {})
            phone = addr.get("phone", "")
            if phone == contact or addr.get("email") == contact:
                results.append(o)
        return sorted(results, key=lambda o: o.get("created_at", ""), reverse=True)


class CouponStore:
    """优惠券存储"""

    def __init__(self, site_id: str):
        self.site_id = site_id
        self.path = _coupons_path(site_id)

    def _load(self) -> dict:
        data = _load_json(self.path)
        if not data:
            return {"coupons": []}
        if isinstance(data, list):
            return {"coupons": data}
        return data

    def validate(self, code: str, subtotal: float) -> dict:
        """验证优惠券并计算折扣"""
        coupons = self._load().get("coupons", [])
        for c in coupons:
            if c.get("code", "").upper() != code.upper():
                continue
            if c.get("used_count", 0) >= c.get("max_uses", 999):
                raise HTTPException(400, "优惠券已用完")
            min_order = c.get("min_order", 0)
            if min_order > 0 and subtotal < min_order:
                raise HTTPException(400, f"订单金额需满{min_order}元")

            discount_type = c.get("type", "percent")
            discount_value = c.get("value", 0)
            if discount_type == "percent":
                discount = round(subtotal * discount_value / 100, 2)
            else:
                discount = min(discount_value, subtotal)
            return {"discount": _round_money(discount), "coupon": c}
        raise HTTPException(400, "优惠券无效")

    def increment_use(self, code: str):
        """使用计数 +1"""
        if not code:
            return
        data = self._load()
        for c in data.get("coupons", []):
            if c.get("code", "").upper() == code.upper():
                c["used_count"] = c.get("used_count", 0) + 1
                _save_json(self.path, data)
                return


class ReviewStore:
    """评价存储"""

    def __init__(self, site_id: str):
        self.site_id = site_id
        self.path = _reviews_path(site_id)

    def _load(self) -> dict:
        data = _load_json(self.path)
        if not data:
            return {"reviews": []}
        if isinstance(data, list):
            return {"reviews": data}
        return data

    def list_by_product(self, product_id: str, page: int = 1, per_page: int = 10) -> dict:
        """商品评价列表"""
        data = self._load()
        reviews = [r for r in data.get("reviews", []) if r.get("product_id") == product_id]
        reviews = sorted(reviews, key=lambda r: r.get("created_at", ""), reverse=True)

        total = len(reviews)
        total_pages = (total + per_page - 1) // per_page
        start = (page - 1) * per_page
        page_reviews = reviews[start : start + per_page]

        # 评分统计
        all_ratings = [r.get("rating", 5) for r in reviews]
        avg = round(sum(all_ratings) / len(all_ratings), 1) if all_ratings else 5.0

        return {
            "reviews": page_reviews,
            "rating": {"average": avg, "count": total},
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
            },
        }

    def add(
        self,
        product_id: str,
        order_no: str,
        phone: str,
        rating: int,
        content: str,
        images: list = None,
    ) -> dict:
        """添加评价（需订单验证）"""
        # 验证订单
        orders_data = _load_json(_orders_path(self.site_id))
        if orders_data:
            orders_list = orders_data if isinstance(orders_data, list) else orders_data.get("orders", [])
            found = False
            for o in orders_list:
                addr = o.get("shipping_address", {})
                if (
                    o.get("order_no") == order_no
                    and addr.get("phone") == phone
                    and o.get("status") == "paid"
                ):
                    found = True
                    break
            if not found:
                raise HTTPException(403, "订单验证失败：订单号或手机号不匹配，或订单未支付")

        # 检查是否已评价
        data = self._load()
        for r in data.get("reviews", []):
            if r.get("order_no") == order_no and r.get("product_id") == product_id:
                raise HTTPException(400, "该订单已评价过此商品")

        review = {
            "id": uuid.uuid4().hex[:12],
            "product_id": product_id,
            "order_no": order_no,
            "rating": max(1, min(5, rating)),
            "content": content,
            "images": images or [],
            "created_at": datetime.now().isoformat(),
        }
        data.setdefault("reviews", []).append(review)
        _save_json(self.path, data)
        return review


class ShippingStore:
    """运费模板存储"""

    def __init__(self, site_id: str):
        self.site_id = site_id
        self.path = _shipping_path(site_id)

    def _load(self) -> dict:
        data = _load_json(self.path)
        return data if data else {"zones": [], "free_shipping_threshold": 0}

    def list_zones(self) -> list:
        """配送区域列表"""
        data = self._load()
        return data.get("zones", [])

    def calc_shipping(self, province: str, subtotal: float) -> list:
        """计算可用运费方式"""
        data = self._load()
        zones = data.get("zones", [])
        free_threshold = data.get("free_shipping_threshold", 0)

        if subtotal >= free_threshold:
            return [{"name": "包邮", "price": 0, "estimated_days": "3-7"}]

        matched = []
        for zone in zones:
            provinces = [p.lower() for p in zone.get("provinces", [])]
            if province.lower() in provinces or not provinces:
                matched.append({
                    "name": zone.get("name", "标准配送"),
                    "price": _round_money(zone.get("fee", 0)),
                    "estimated_days": zone.get("estimated_days", "3-7"),
                })
        if not matched:
            matched.append({"name": "标准配送", "price": _round_money(10), "estimated_days": "3-7"})
        return matched


class PaymentConfigStore:
    """支付配置存储"""

    def __init__(self, site_id: str):
        self.site_id = site_id
        self.path = _payment_config_path(site_id)

    def _load(self) -> dict:
        data = _load_json(self.path)
        return data if data else {}

    def get_channel(self, method: str) -> Optional[dict]:
        """获取指定支付渠道配置"""
        data = self._load()
        channels = data.get("channels", {})
        return channels.get(method)

    def get_public_config(self) -> dict:
        """前台可见的支付配置概要"""
        data = self._load()
        channels = data.get("channels", {})
        return {
            "enabled_methods": [k for k, v in channels.items() if v],
            "currency": data.get("currency", "CNY"),
        }


# ══════════════════════════════════════════════════════════════
# 金额计算工具
# ══════════════════════════════════════════════════════════════
def _calc_order_totals(
    items: list,
    shipping_fee: float,
    coupon_code: str,
    site_id: str,
) -> dict:
    """计算订单各项金额"""
    product_store = ProductStore(site_id)

    subtotal = Decimal("0")
    for item in items:
        product = product_store.get(item["product_id"])
        if not product:
            raise HTTPException(400, f"商品不存在: {item['product_id']}")

        # 价格可能在顶层 price 或 variants 中
        price_val = product.get("price", 0)
        if not price_val and product.get("variants"):
            variant_id = item.get("variant_id", "")
            for v in product["variants"]:
                if v.get("id") == variant_id or not variant_id:
                    price_val = v.get("price", 0)
                    break
        price = Decimal(str(price_val))
        qty = item["quantity"]
        subtotal += price * qty

    subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    discount = Decimal("0")
    if coupon_code:
        coupon_store = CouponStore(site_id)
        result = coupon_store.validate(coupon_code, float(subtotal))
        discount = Decimal(str(result["discount"]))

    discount = discount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = (subtotal + Decimal(str(shipping_fee)) - discount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = max(total, Decimal("0"))

    return {
        "subtotal": float(subtotal),
        "shipping_fee": float(shipping_fee),
        "discount": float(discount),
        "total": float(total),
    }


# ══════════════════════════════════════════════════════════════
# 请求模型
# ══════════════════════════════════════════════════════════════
class CheckoutItem(BaseModel):
    product_id: str
    variant_id: str = ""
    quantity: int = 1

class ShippingAddress(BaseModel):
    name: str
    phone: str
    province: str
    city: str
    district: str = ""
    address: str
    postal_code: str = ""
    email: str = ""

class CheckoutReq(BaseModel):
    items: list[CheckoutItem] = []
    shipping_address: ShippingAddress
    payment_method: str
    coupon_code: str = ""
    notes: str = ""

class AddCartItem(BaseModel):
    product_id: str
    variant_id: str = ""
    quantity: int = 1

class UpdateCartItem(BaseModel):
    quantity: int

class CouponApply(BaseModel):
    code: str

class ReviewSubmit(BaseModel):
    order_no: str
    phone: str
    rating: int = 5
    content: str = ""
    images: list[str] = []

class OrderVerify(BaseModel):
    order_no: str
    phone: str

# ══════════════════════════════════════════════════════════════
# 购物车 ID 工具
# ══════════════════════════════════════════════════════════════
COOKIE_CART_KEY = "sg_cart_id"

def _get_or_create_cart_id(request: Request, response: JSONResponse = None) -> str:
    """从 Cookie 获取或创建新的 cart_id"""
    cart_id = request.cookies.get(COOKIE_CART_KEY)
    if not cart_id:
        cart_id = uuid.uuid4().hex
        if response is not None:
            response.set_cookie(
                key=COOKIE_CART_KEY,
                value=cart_id,
                httponly=True,
                samesite="lax",
                max_age=365 * 24 * 3600,
            )
    return cart_id


# ══════════════════════════════════════════════════════════════
# API 端点
# ══════════════════════════════════════════════════════════════

# ── 1. 商品浏览 ────────────────────────────────────────────

@router.get("/products")
async def list_products(
    request: Request,
    site_id: str,
    category: str = Query(None, description="分类ID"),
    keyword: str = Query(None, description="搜索关键词"),
    featured: bool = Query(False, description="仅精选"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    """商品列表（支持 category/keyword/featured 筛选，分页）"""
    await _verify_site(request, site_id)
    store = ProductStore(site_id)
    return store.list(category=category, keyword=keyword, featured=featured, page=page, per_page=per_page)


@router.get("/products/{product_id}")
async def get_product(product_id: str, request: Request, site_id: str):
    """商品详情（含 variants/stock/reviews 聚合）"""
    config = await _verify_site(request, site_id)
    store = ProductStore(site_id)
    product = store.get(product_id)
    if not product:
        raise HTTPException(404, "商品不存在")

    # 库存状态
    total_stock = sum(v.get("stock", 0) for v in product.get("variants", []))
    if total_stock == 0:
        stock_status = "out_of_stock"
    elif total_stock < 5:
        stock_status = "low_stock"
    else:
        stock_status = "in_stock"

    # 评分
    review_store = ReviewStore(site_id)
    review_data = review_store.list_by_product(product_id, page=1, per_page=3)

    # 相关商品
    related = store.related(product_id)

    # 站点语言/SEO
    site_config = config if isinstance(config, dict) else {}
    lang = site_config.get("language", "zh-CN")

    result = {
        **product,
        "stock_status": stock_status,
        "rating": review_data.get("rating", {"average": 5.0, "count": 0}),
        "review_samples": review_data.get("reviews", []),
        "related_products": related,
        "seo_title": product.get("seo_title") or product.get("name"),
        "seo_description": product.get("seo_description") or product.get("description", "")[:200],
        "lang": lang,
    }
    return result


@router.get("/categories")
async def list_categories(request: Request, site_id: str):
    """分类列表（树状结构）"""
    await _verify_site(request, site_id)
    store = CategoryStore(site_id)
    return {"categories": store.tree()}


@router.get("/featured")
async def get_featured(request: Request, site_id: str):
    """精选商品（首页用）"""
    await _verify_site(request, site_id)
    store = ProductStore(site_id)
    return store.list(featured=True, per_page=8)


# ── 2. 购物车 ────────────────────────────────────────────

@router.get("/cart")
async def get_cart(request: Request, site_id: str):
    """获取当前购物车（从 Cookie 读取 cart_id）"""
    await _verify_site(request, site_id)
    cart_id = _get_or_create_cart_id(request)
    cart_store = CartStore(cart_id)
    cart = cart_store.get()
    return cart


@router.post("/cart/items")
async def add_cart_item(
    request: Request,
    site_id: str,
    body: AddCartItem,
):
    """添加商品到购物车"""
    await _verify_site(request, site_id)

    if body.quantity < 1:
        raise HTTPException(400, "数量至少为1")

    # 验证商品存在
    product_store = ProductStore(site_id)
    product = product_store.get(body.product_id)
    if not product:
        raise HTTPException(404, "商品不存在")

    # 验证库存
    variant_id = body.variant_id
    stock = product_store.stock_of(body.product_id, variant_id)
    if stock < body.quantity:
        raise HTTPException(400, {"detail": "库存不足", "available": stock})

    cart_store = CartStore(_get_or_create_cart_id(request))
    cart = cart_store.add_item(body.product_id, variant_id, body.quantity)
    return {"success": True, "cart": cart}


@router.put("/cart/items/{item_id}")
async def update_cart_item(
    request: Request,
    site_id: str,
    item_id: str,
    body: UpdateCartItem,
):
    """修改购物车商品数量"""
    try:
        await _verify_site(request, site_id)
        cart_store = CartStore(_get_or_create_cart_id(request))
        cart = cart_store.update_item(item_id, body.quantity)
        return {"success": True, "cart": cart}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新购物车失败: {e}")
        raise HTTPException(500, "更新购物车商品失败")


@router.delete("/cart/items/{item_id}")
async def remove_cart_item(request: Request, site_id: str, item_id: str):
    """删除购物车商品"""
    try:
        await _verify_site(request, site_id)
        cart_store = CartStore(_get_or_create_cart_id(request))
        cart = cart_store.remove_item(item_id)
        return {"success": True, "cart": cart}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除购物车商品失败: {e}")
        raise HTTPException(500, "删除购物车商品失败")


@router.delete("/cart")
async def clear_cart(request: Request, site_id: str):
    """清空购物车"""
    try:
        await _verify_site(request, site_id)
        cart_store = CartStore(_get_or_create_cart_id(request))
        cart_store.clear()
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清空购物车失败: {e}")
        raise HTTPException(500, "清空购物车失败")


@router.post("/cart/apply-coupon")
async def apply_coupon(request: Request, site_id: str, body: CouponApply):
    """应用优惠券（带后端速率限制）"""
    ip = request.headers.get("x-forwarded-for", "").split(",")[0].strip() or request.headers.get("x-real-ip", "").strip() or (request.client.host if request.client else "unknown")
    _check_coupon_rate(ip)
    try:
        await _verify_site(request, site_id)
        cart_store = CartStore(_get_or_create_cart_id(request))
        cart = cart_store.apply_coupon(body.code, site_id)
        return {"success": True, "cart": cart}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"应用优惠券失败: {e}")
        raise HTTPException(500, "应用优惠券失败")


@router.delete("/cart/coupon")
async def remove_coupon(request: Request, site_id: str):
    """移除优惠券"""
    await _verify_site(request, site_id)
    cart_store = CartStore(_get_or_create_cart_id(request))
    cart = cart_store.remove_coupon()
    return {"success": True, "cart": cart}


@router.get("/cart/shipping")
async def get_cart_shipping(
    request: Request,
    site_id: str,
    province: str = Query(...),
    city: str = Query(""),
):
    """获取可用运费方式（需配送地址）"""
    await _verify_site(request, site_id)
    shipping_store = ShippingStore(site_id)
    full_province = f"{province}{city}".strip()
    cart_store = CartStore(_get_or_create_cart_id(request))
    cart = cart_store.get()

    # 计算小计
    product_store = ProductStore(site_id)
    subtotal = 0
    for item in cart.get("items", []):
        p = product_store.get(item["product_id"])
        if p:
            subtotal += p.get("price", 0) * item["quantity"]
    subtotal = float(subtotal)

    methods = shipping_store.calc_shipping(province, subtotal)
    return {"methods": methods}


# ── 3. 结算与订单 ────────────────────────────────────────

@router.post("/checkout")
async def checkout(request: Request, site_id: str, body: CheckoutReq):
    """创建订单"""
    await _verify_site(request, site_id)

    addr = body.shipping_address
    if not addr.phone:
        raise HTTPException(400, "收货人手机号不能为空")

    product_store = ProductStore(site_id)
    cart_store = CartStore(_get_or_create_cart_id(request))
    shipping_store = ShippingStore(site_id)

    # ── 确定结算商品 ──
    if body.items:
        # 直接从请求下单
        items = [i.model_dump() for i in body.items]
    else:
        # 从购物车读取
        cart = cart_store.get()
        items = [
            {
                "product_id": it["product_id"],
                "variant_id": it["variant_id"],
                "quantity": it["quantity"],
            }
            for it in cart.get("items", [])
        ]
        if not items:
            raise HTTPException(400, "购物车为空")

    # ── 验证商品 & 库存 ──
    for item in items:
        product = product_store.get(item["product_id"])
        if not product:
            raise HTTPException(400, f"商品不存在: {item['product_id']}")
        stock = product_store.stock_of(item["product_id"], item.get("variant_id", ""))
        if stock < item["quantity"]:
            raise HTTPException(400, {"detail": "库存不足", "available": stock, "product": item["product_id"]})

    # ── 计算运费 ──
    province = addr.province
    subtotal = sum(
        (product_store.get(i["product_id"]) or {}).get("price", 0) * i["quantity"]
        for i in items
    )
    shipping_methods = shipping_store.calc_shipping(province, subtotal)
    shipping_fee = shipping_methods[0]["price"] if shipping_methods else 0

    # ── 计算金额 ──
    coupon_code = body.coupon_code or cart_store.get().get("coupon_code")
    totals = _calc_order_totals(items, shipping_fee, coupon_code, site_id)

    # ── 创建订单 ──
    order_store = OrderStore(site_id)
    order = order_store.create(
        items=items,
        shipping_address=addr.model_dump(),
        payment_method=body.payment_method,
        coupon_code=coupon_code,
        notes=body.notes,
        site_id=site_id,
        cart_id=_get_or_create_cart_id(request),
    )

    # 更新金额
    order["subtotal"] = totals["subtotal"]
    order["shipping_fee"] = totals["shipping_fee"]
    order["discount"] = totals["discount"]
    order["total"] = totals["total"]

    # 保存
    data = _load_json(_orders_path(site_id))
    if not data:
        data = {"orders": []}
    elif isinstance(data, list):
        data = {"orders": data}
    for i, o in enumerate(data["orders"]):
        if o["id"] == order["id"]:
            data["orders"][i] = order
            break
    _save_json(_orders_path(site_id), data)

    # ── 扣减库存 ──
    for item in items:
        ok = product_store.reduce_stock(item.get("variant_id", ""), item["quantity"])
        if not ok:
            logger.warning(f"库存扣减失败: variant={item.get('variant_id')}, qty={item['quantity']}")

    # ── 标记优惠券已使用 ──
    if coupon_code:
        CouponStore(site_id).increment_use(coupon_code)

    # ── 清除购物车优惠券，保留商品（下次可重新下单）──
    # （购物车在用户主动清空时才清除）

    return {
        "order_id": order["id"],
        "order_no": order["order_no"],
        "total": totals["total"],
        "payment_url": None,  # 前端后续调用 /payment/{order_id}/url 获取
    }


@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    request: Request,
    site_id: str,
    order_no: str = Query(None),
    phone: str = Query(None),
):
    """订单详情（需验证手机号或邮箱）"""
    await _verify_site(request, site_id)
    store = OrderStore(site_id)
    order = store.get(order_id)
    if not order:
        raise HTTPException(404, "订单不存在")

    # 手机号/邮箱验证
    if order_no and phone:
        if order["order_no"] != order_no or order["shipping_address"].get("phone") != phone:
            raise HTTPException(403, "验证信息不匹配")
    else:
        raise HTTPException(400, "请提供 order_no 和 phone 参数进行验证")

    return order


@router.get("/orders/{order_id}/status")
async def get_order_status(order_id: str, request: Request, site_id: str, phone: str = Query("", description="收货人手机号验证")):
    """轮询订单支付状态（需手机号验证）"""
    await _verify_site(request, site_id)
    store = OrderStore(site_id)
    order = store.get(order_id)
    if not order:
        raise HTTPException(404, "订单不存在")
    # Verify phone number
    if phone and order.get("shipping_address", {}).get("phone") != phone:
        raise HTTPException(403, "手机号验证失败")

    return {
        "order_id": order["id"],
        "order_no": order["order_no"],
        "status": order["status"],
        "paid_at": order.get("paid_at"),
    }


# ── 4. 评价 ──────────────────────────────────────────────

@router.get("/products/{product_id}/reviews")
async def list_reviews(
    product_id: str,
    request: Request,
    site_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
):
    """商品评价列表（分页）"""
    await _verify_site(request, site_id)
    store = ReviewStore(site_id)
    return store.list_by_product(product_id, page=page, per_page=per_page)


@router.post("/products/{product_id}/reviews")
async def submit_review(
    product_id: str,
    request: Request,
    site_id: str,
    body: ReviewSubmit,
):
    """提交评价（需订单验证：order_no + 手机号）"""
    await _verify_site(request, site_id)
    if body.rating < 1 or body.rating > 5:
        raise HTTPException(400, "评分需在 1-5 之间")
    if not body.content:
        raise HTTPException(400, "评价内容不能为空")

    store = ReviewStore(site_id)
    review = store.add(
        product_id=product_id,
        order_no=body.order_no,
        phone=body.phone,
        rating=body.rating,
        content=body.content,
        images=body.images or [],
    )
    return {"success": True, "review": review}


# ── 5. 支付获取 ──────────────────────────────────────────

@router.get("/payment/{order_id}/url")
async def get_payment_url(order_id: str, request: Request, site_id: str):
    """获取支付跳转URL"""
    await _verify_site(request, site_id)

    order_store = OrderStore(site_id)
    order = order_store.get(order_id)
    if not order:
        raise HTTPException(404, "订单不存在")
    if order["status"] not in ("pending", "unpaid"):
        raise HTTPException(400, f"订单状态不支持支付：{order['status']}")

    method = order["payment_method"]
    payment_store = PaymentConfigStore(site_id)
    channel_config = payment_store.get_channel(method)

    if not channel_config:
        raise HTTPException(400, {"detail": "该支付方式暂不可用", "payment_method": method})

    # ── 根据支付方式生成支付 URL ──
    order_no = order["order_no"]
    total_fee = round(order["total"], 2)
    pay_url = None
    qr_code = None
    pay_params: dict = {}

    if method == "wechat":
        # 微信 Native 支付
        mch_id = channel_config.get("mch_id", "")
        api_key = channel_config.get("api_key", "")
        app_id = channel_config.get("app_id", "")

        if not all([mch_id, api_key, app_id]):
            raise HTTPException(400, {"detail": "微信支付参数未配置完整", "payment_method": "wechat"})

        # 构造统一起订单请求
        nonce_str = secrets.token_hex(16)
        time_stamp = str(int(time.time()))
        trade_type = "NATIVE"
        notify_url = channel_config.get("notify_url", "")

        # 签名
        sign_str = (
            f"appid={app_id}&body=SG订单&mch_id={mch_id}&nonce_str={nonce_str}"
            f"&notify_url={notify_url}&out_trade_no={order_no}&total_fee={int(total_fee*100)}"
            f"&trade_type={trade_type}&key={api_key}"
        )
        sign = hashlib.md5(sign_str.encode()).hexdigest().upper()

        # 返回微信统一下单 URL（前端自行调用）
        pay_url = (
            f"https://api.mch.weixin.qq.com/pay/unifiedorder?"
            f"appid={app_id}&body=SG订单&mch_id={mch_id}&nonce_str={nonce_str}"
            f"&notify_url={notify_url}&out_trade_no={order_no}"
            f"&total_fee={int(total_fee*100)}&trade_type={trade_type}&sign={sign}"
        )
        pay_params = {"app_id": app_id, "trade_type": trade_type}  # mch_id removed for security

    elif method == "alipay":
        # 支付宝电脑网站支付
        app_id = channel_config.get("app_id", "")
        private_key = channel_config.get("private_key", "")
        alipay_public_key = channel_config.get("alipay_public_key", "")
        notify_url = channel_config.get("notify_url", "")

        if not all([app_id, private_key, alipay_public_key]):
            raise HTTPException(400, {"detail": "支付宝参数未配置完整", "payment_method": "alipay"})

        # 支付宝签名参数构造（简化，实际建议用 alipay-sdk）
        params = {
            "app_id": app_id,
            "method": "alipay.trade.page.pay",
            "charset": "UTF-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "biz_content": json.dumps({
                "out_trade_no": order_no,
                "total_amount": str(total_fee),
                "subject": f"SG订单{order_no}",
                "product_code": "FAST_INSTANT_TRADE_PAY",
            }),
            "notify_url": notify_url,
            "return_url": channel_config.get("return_url", ""),
        }

        # 签名（rsa2_sign 需 pycryptodome，这里返回签名参数供前端处理）
        # Strip sensitive keys before returning to frontend
        pay_params = {k: v for k, v in params.items() if k not in ("sign",)}
        pay_url = f"https://openapi.alipay.com/gateway.do?{_urlencode(params)}"

    elif method == "paypal":
        # PayPal Checkout
        client_id = channel_config.get("client_id", "")
        client_secret = channel_config.get("client_secret", "")
        mode = channel_config.get("mode", "sandbox")

        if not client_id:
            raise HTTPException(400, {"detail": "PayPal 参数未配置完整", "payment_method": "paypal"})

        base_url = (
            "https://api-m.sandbox.paypal.com" if mode == "sandbox"
            else "https://api-m.paypal.com"
        )
        token_url = f"{base_url}/v1/oauth2/token"
        order_url = f"{base_url}/v2/checkout/orders"

        # 获取 Access Token
        import base64 as b64
        credentials = b64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        token_resp = httpx_post(token_url, {
            "grant_type": "client_credentials",
        }, {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        })
        access_token = token_resp.get("access_token", "")

        # 创建 PayPal 订单
        paypal_order = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "reference_id": order_no,
                "amount": {
                    "currency_code": channel_config.get("currency", "USD"),
                    "value": f"{total_fee:.2f}",
                },
            }],
        }
        order_resp = httpx_post(order_url, paypal_order, {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        })
        # Extract Approval URL (client_secret never leaves backend)
        for link in order_resp.get("links", []):
            if link.get("rel") == "approve":
                pay_url = link["href"]
                break

    else:
        raise HTTPException(400, {"detail": "不支持的支付方式", "payment_method": method})

    # 存储 pay_url 以便回调时关联
    order_store.update_pay_url(order_id, pay_url)

    return {
        "payment_url": pay_url,
        "qr_code": qr_code,
        "pay_params": pay_params,
    }


def _urlencode(params: dict) -> str:
    """简单 URL 编码"""
    from urllib.parse import urlencode
    return urlencode(params)


def httpx_post(url: str, json_data: dict, headers: dict) -> dict:
    """内部 POST 工具（用于支付网关调用）"""
    try:
        import httpx
    except ImportError:
        raise HTTPException(500, "httpx 未安装，无法调用支付接口")
    with httpx.Client(timeout=15) as client:
        resp = client.post(url, json=json_data, headers=headers)
        return resp.json()


# ── 6. 站点配置 ──────────────────────────────────────────

@router.get("/config")
async def get_site_config(request: Request, site_id: str):
    """获取站点配置（主题/货币/语言/支付配置概要等前台信息）"""
    config = await _verify_site(request, site_id)
    payment_store = PaymentConfigStore(site_id)
    return {
        "site_id": site_id,
        "theme": config.get("theme", "default"),
        "currency": config.get("currency", "CNY"),
        "currency_symbol": config.get("currency_symbol", "¥"),
        "language": config.get("language", "zh-CN"),
        "site_name": config.get("site_name", ""),
        "logo": config.get("logo", ""),
        "payment": payment_store.get_public_config(),
    }


@router.get("/shipping/zones")
async def get_shipping_zones(request: Request, site_id: str):
    """获取配送区域列表"""
    await _verify_site(request, site_id)
    store = ShippingStore(site_id)
    data = store._load()
    return {
        "zones": data.get("zones", []),
        "free_shipping_threshold": data.get("free_shipping_threshold", 0),
    }