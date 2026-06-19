"""
ecommerce.store — SG电商建站平台 · 电商数据层
使用 JSON 文件存储（原子写入 + 文件锁），实现完整的电商数据管理。
"""

from __future__ import annotations

import csv
try:
    import fcntl
    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False  # Windows
import io
import json
import os
import random
import shutil
import string
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# ──────────────────────────────────────────────────────────────────────────────
# 工具函数
# ──────────────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _gen_id(prefix: str, length: int = 12) -> str:
    """生成  类型前缀_随机字符串  格式的 ID"""
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=length))
    return f"{prefix}{suffix}"


def _data_dir() -> Path:
    """返回 data/ 目录路径（相对于本文件）"""
    return Path(__file__).parent.parent.parent / "data"


def _ensure_data_dir():
    _data_dir().mkdir(parents=True, exist_ok=True)


def _file_path(site_id: str, filename: str) -> Path:
    _ensure_data_dir()
    return _data_dir() / f"{filename}_{site_id}.json"


def _load_json(site_id: str, filename: str, default_factory=list) -> list | dict:
    """线程安全的 JSON 读取；文件不存在时返回 default_factory()"""
    path = _file_path(site_id, filename)
    if not path.exists():
        return default_factory()
    with open(path, "r", encoding="utf-8") as f:
        if _HAS_FCNTL:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
        try:
            data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return default_factory()
    # 兼容两种格式：纯list 或 {"key": [...]} dict
    if isinstance(data, dict) and not isinstance(default_factory(), dict):
        # 期望list但文件是dict，提取第一个value（列表）
        for v in data.values():
            if isinstance(v, list):
                return v
        return []
    return data


def _save_json(site_id: str, filename: str, data: list | dict):
    """
    原子写入：写入临时文件 → fsync → rename。
    自动兼容：如果文件已存在且是dict格式({"key":[...]}), 而data是list，
    则用原dict的key包裹后保存。
    """
    path = _file_path(site_id, filename)
    
    # 自动包裹：如果数据是list但文件已是dict格式，包裹回去
    if isinstance(data, list) and path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if isinstance(existing, dict):
                # 找到对应的key
                for k, v in existing.items():
                    if isinstance(v, list):
                        data = {k: data}
                        break
        except (json.JSONDecodeError, IOError):
            pass
    
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        if _HAS_FCNTL:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    # 数据持久化同步
    try:
        from apis.data_sync import mark_dirty
        mark_dirty(path.name)
    except Exception:
        pass


def _list_to_dict(items: list[dict], key: str = "id") -> dict[str, dict]:
    return {item[key]: item for item in items}


# ──────────────────────────────────────────────────────────────────────────────
# ProductStore
# ──────────────────────────────────────────────────────────────────────────────

class ProductStore:
    """商品、分类、库存管理"""

    PRODUCTS_FILE = "products"
    CATEGORIES_FILE = "categories"

    def __init__(self, site_id: str):
        self.site_id = site_id
        self._lock = threading.Lock()

    # ── 商品 CRUD ──────────────────────────────────────────────────────────────

    def list_products(
        self,
        category: str | None = None,
        page: int = 1,
        per_page: int = 20,
        status: str = "active",
    ) -> dict:
        products = _load_json(self.site_id, self.PRODUCTS_FILE, list)
        if status:
            products = [p for p in products if p.get("status") == status]
        if category:
            products = [p for p in products if p.get("category") == category]
        total = len(products)
        start = (page - 1) * per_page
        end = start + per_page
        return {
            "items": products[start:end],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }

    def get_product(self, product_id: str) -> dict | None:
        products = _load_json(self.site_id, self.PRODUCTS_FILE, list)
        return next((p for p in products if p["id"] == product_id), None)

    def create_product(self, data: dict) -> dict:
        with self._lock:
            products = _load_json(self.site_id, self.PRODUCTS_FILE, list)
            now = _now_iso()
            product = {
                "id": _gen_id("prod_"),
                "name": data.get("name", ""),
                "description": data.get("description", ""),
                "category": data.get("category", ""),
                "images": data.get("images", []),
                "variants": data.get("variants", []),
                "status": data.get("status", "active"),
                "seo_title": data.get("seo_title", ""),
                "seo_description": data.get("seo_description", ""),
                "specs": data.get("specs", []),
                "featured": data.get("featured", False),
                "sort_order": data.get("sort_order", 0),
                "created_at": now,
                "updated_at": now,
            }
            products.append(product)
            _save_json(self.site_id, self.PRODUCTS_FILE, products)
        return product

    def update_product(self, product_id: str, data: dict) -> dict:
        with self._lock:
            products = _load_json(self.site_id, self.PRODUCTS_FILE, list)
            idx = next((i for i, p in enumerate(products) if p["id"] == product_id), None)
            if idx is None:
                raise ValueError(f"Product not found: {product_id}")
            # 允许更新字段（不可直接改 id / created_at）
            updatable = [
                "name", "description", "category", "images", "variants",
                "status", "seo_title", "seo_description", "specs",
                "featured", "sort_order",
            ]
            for k in updatable:
                if k in data:
                    products[idx][k] = data[k]
            products[idx]["updated_at"] = _now_iso()
            _save_json(self.site_id, self.PRODUCTS_FILE, products)
            return products[idx]

    def delete_product(self, product_id: str) -> bool:
        with self._lock:
            products = _load_json(self.site_id, self.PRODUCTS_FILE, list)
            before = len(products)
            products = [p for p in products if p["id"] != product_id]
            if len(products) == before:
                return False
            _save_json(self.site_id, self.PRODUCTS_FILE, products)
            return True

    def batch_update_status(self, product_ids: list[str], status: str) -> int:
        with self._lock:
            products = _load_json(self.site_id, self.PRODUCTS_FILE, list)
            now = _now_iso()
            count = 0
            for p in products:
                if p["id"] in product_ids:
                    p["status"] = status
                    p["updated_at"] = now
                    count += 1
            _save_json(self.site_id, self.PRODUCTS_FILE, products)
            return count

    # ── 分类 ───────────────────────────────────────────────────────────────────

    def list_categories(self) -> list[dict]:
        return _load_json(self.site_id, self.CATEGORIES_FILE, list)

    def create_category(self, name: str, parent_id: str | None = None, sort_order: int = 0) -> dict:
        with self._lock:
            categories = _load_json(self.site_id, self.CATEGORIES_FILE, list)
            category = {
                "id": _gen_id("cat_"),
                "name": name,
                "parent_id": parent_id,
                "sort_order": sort_order,
                "created_at": _now_iso(),
            }
            categories.append(category)
            _save_json(self.site_id, self.CATEGORIES_FILE, categories)
            return category

    def update_category(self, cat_id: str, data: dict) -> dict:
        with self._lock:
            categories = _load_json(self.site_id, self.CATEGORIES_FILE, list)
            idx = next((i for i, c in enumerate(categories) if c["id"] == cat_id), None)
            if idx is None:
                raise ValueError(f"Category not found: {cat_id}")
            for k, v in data.items():
                if k not in ("id", "created_at"):
                    categories[idx][k] = v
            _save_json(self.site_id, self.CATEGORIES_FILE, categories)
            return categories[idx]

    def delete_category(self, cat_id: str) -> bool:
        with self._lock:
            categories = _load_json(self.site_id, self.CATEGORIES_FILE, list)
            before = len(categories)
            categories = [c for c in categories if c["id"] != cat_id]
            if len(categories) == before:
                return False
            _save_json(self.site_id, self.CATEGORIES_FILE, categories)
            return True

    # ── 库存 ───────────────────────────────────────────────────────────────────

    def check_stock(self, product_id: str, variant_id: str, quantity: int) -> bool:
        product = self.get_product(product_id)
        if not product:
            return False
        for v in product.get("variants", []):
            if v["id"] == variant_id:
                return v.get("stock", 0) >= quantity
        return False

    def deduct_stock(self, product_id: str, variant_id: str, quantity: int) -> bool:
        """乐观锁：先读取检查，命中后再写入（两阶段均在锁内）"""
        with self._lock:
            products = _load_json(self.site_id, self.PRODUCTS_FILE, list)
            idx = next((i for i, p in enumerate(products) if p["id"] == product_id), None)
            if idx is None:
                return False
            vidx = next(
                (j for j, v in enumerate(products[idx]["variants"]) if v["id"] == variant_id),
                None,
            )
            if vidx is None:
                return False
            if products[idx]["variants"][vidx].get("stock", 0) < quantity:
                return False
            products[idx]["variants"][vidx]["stock"] -= quantity
            products[idx]["updated_at"] = _now_iso()
            _save_json(self.site_id, self.PRODUCTS_FILE, products)
            return True

    def get_low_stock_products(self, threshold: int = 10) -> list[dict]:
        products = _load_json(self.site_id, self.PRODUCTS_FILE, list)
        result = []
        for p in products:
            low_variants = [
                v for v in p.get("variants", []) if v.get("stock", 0) <= threshold
            ]
            if low_variants:
                result.append({**p, "low_stock_variants": low_variants})
        return result

    # ── 批量导入导出 ───────────────────────────────────────────────────────────

    def export_products_csv(self) -> str:
        products = _load_json(self.site_id, self.PRODUCTS_FILE, list)
        output = io.StringIO()
        fieldnames = [
            "id", "name", "description", "category", "status",
            "price", "compare_price", "sku", "stock", "weight",
            "images", "featured", "sort_order",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for p in products:
            for v in p.get("variants", [{}]):
                writer.writerow({
                    "id": p["id"],
                    "name": p["name"],
                    "description": p.get("description", ""),
                    "category": p.get("category", ""),
                    "status": p.get("status", "active"),
                    "price": v.get("price", ""),
                    "compare_price": v.get("compare_price", ""),
                    "sku": v.get("sku", ""),
                    "stock": v.get("stock", ""),
                    "weight": v.get("weight", ""),
                    "images": ",".join(p.get("images", [])),
                    "featured": p.get("featured", ""),
                    "sort_order": p.get("sort_order", ""),
                })
        return output.getvalue()

    def import_products_csv(self, csv_content: str) -> dict:
        input_stream = io.StringIO(csv_content)
        reader = csv.DictReader(input_stream)
        products = _load_json(self.site_id, self.PRODUCTS_FILE, list)
        product_map: dict[str, dict] = _list_to_dict(products)
        created, updated, errors = 0, 0, []

        for row_num, row in enumerate(reader, start=2):
            try:
                pid = row.get("id", "").strip()
                name = row.get("name", "").strip()
                if not name:
                    errors.append(f"Row {row_num}: missing name")
                    continue

                variant_data = {
                    "id": _gen_id("var_"),
                    "name": row.get("sku", name),
                    "sku": row.get("sku", ""),
                    "price": float(row["price"]) if row.get("price") else 0,
                    "compare_price": float(row["compare_price"]) if row.get("compare_price") else None,
                    "stock": int(row["stock"]) if row.get("stock") else 0,
                    "weight": float(row["weight"]) if row.get("weight") else 0,
                    "image": "",
                }

                if pid and pid in product_map:
                    p = product_map[pid]
                    p["name"] = name
                    p["description"] = row.get("description", p.get("description", ""))
                    p["category"] = row.get("category", p.get("category", ""))
                    p["status"] = row.get("status", p.get("status", "active"))
                    p["variants"].append(variant_data)
                    p["updated_at"] = _now_iso()
                    updated += 1
                else:
                    now = _now_iso()
                    new_product = {
                        "id": pid or _gen_id("prod_"),
                        "name": name,
                        "description": row.get("description", ""),
                        "category": row.get("category", ""),
                        "images": [],
                        "variants": [variant_data],
                        "status": row.get("status", "active"),
                        "seo_title": "",
                        "seo_description": "",
                        "specs": [],
                        "featured": row.get("featured", "false").lower() == "true",
                        "sort_order": int(row["sort_order"]) if row.get("sort_order") else 0,
                        "created_at": now,
                        "updated_at": now,
                    }
                    products.append(new_product)
                    product_map[new_product["id"]] = new_product
                    created += 1
            except Exception as e:
                errors.append(f"Row {row_num}: {e}")

        _save_json(self.site_id, self.PRODUCTS_FILE, products)
        return {"created": created, "updated": updated, "errors": errors}


# ──────────────────────────────────────────────────────────────────────────────
# OrderStore
# ──────────────────────────────────────────────────────────────────────────────

class OrderStore:
    """订单管理（含统计）"""

    ORDERS_FILE = "orders"

    def __init__(self, site_id: str):
        self.site_id = site_id
        self._lock = threading.Lock()

    def _next_order_no(self) -> str:
        """生成 SG + YYYYMMDD + 6位序号"""
        today = datetime.now().strftime("%Y%m%d")
        orders = _load_json(self.site_id, self.ORDERS_FILE, list)
        today_orders = [
            o for o in orders
            if o.get("order_no", "").startswith(f"SG{today}")
        ]
        seq = len(today_orders) + 1
        return f"SG{today}{seq:06d}"

    def create_order(self, data: dict) -> dict:
        with self._lock:
            orders = _load_json(self.site_id, self.ORDERS_FILE, list)
            now = _now_iso()
            order = {
                "id": _gen_id("ord_"),
                "order_no": self._next_order_no(),
                "items": data.get("items", []),
                "subtotal": data.get("subtotal", 0),
                "shipping_fee": data.get("shipping_fee", 0),
                "discount": data.get("discount", 0),
                "coupon_code": data.get("coupon_code", ""),
                "total": data.get("total", 0),
                "currency": data.get("currency", "CNY"),
                "status": "pending",
                "payment": {
                    "method": data.get("payment_method", "wechat"),
                    "status": "pending",
                    "transaction_id": "",
                },
                "shipping": {
                    "address": data.get("shipping_address", {}),
                    "carrier": "",
                    "tracking_number": "",
                    "status": "unshipped",
                },
                "customer": data.get("customer", {}),
                "notes": [],
                "logs": [{"action": "created", "time": now, "detail": "Order created"}],
                "created_at": now,
                "updated_at": now,
            }
            orders.append(order)
            _save_json(self.site_id, self.ORDERS_FILE, orders)
            return order

    def get_order(self, order_id: str) -> dict | None:
        orders = _load_json(self.site_id, self.ORDERS_FILE, list)
        return next((o for o in orders if o["id"] == order_id), None)

    def list_orders(
        self,
        status: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        orders = _load_json(self.site_id, self.ORDERS_FILE, list)
        if status:
            orders = [o for o in orders if o.get("status") == status]
        # 按时间倒序
        orders.sort(key=lambda o: o.get("created_at", ""), reverse=True)
        total = len(orders)
        start = (page - 1) * per_page
        end = start + per_page
        return {
            "items": orders[start:end],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }

    def update_order_status(self, order_id: str, status: str, note: str = "") -> dict:
        valid = {
            "pending", "paid", "shipped", "completed",
            "cancelled", "refunding", "refunded",
        }
        if status not in valid:
            raise ValueError(f"Invalid status: {status}")
        with self._lock:
            orders = _load_json(self.site_id, self.ORDERS_FILE, list)
            idx = next((i for i, o in enumerate(orders) if o["id"] == order_id), None)
            if idx is None:
                raise ValueError(f"Order not found: {order_id}")
            now = _now_iso()
            orders[idx]["status"] = status
            orders[idx]["updated_at"] = now
            log_entry = {"action": "status_change", "time": now, "detail": f"Status → {status}"}
            if note:
                log_entry["note"] = note
            orders[idx]["logs"].append(log_entry)
            # 同步 payment.status
            if status == "paid":
                orders[idx]["payment"]["status"] = "paid"
            elif status == "refunded":
                orders[idx]["payment"]["status"] = "refunded"
            _save_json(self.site_id, self.ORDERS_FILE, orders)
            return orders[idx]

    def add_tracking(
        self,
        order_id: str,
        tracking_number: str,
        carrier: str,
    ) -> dict:
        with self._lock:
            orders = _load_json(self.site_id, self.ORDERS_FILE, list)
            idx = next((i for i, o in enumerate(orders) if o["id"] == order_id), None)
            if idx is None:
                raise ValueError(f"Order not found: {order_id}")
            now = _now_iso()
            orders[idx]["shipping"]["tracking_number"] = tracking_number
            orders[idx]["shipping"]["carrier"] = carrier
            orders[idx]["shipping"]["status"] = "shipped"
            orders[idx]["updated_at"] = now
            orders[idx]["logs"].append({
                "action": "tracking_added",
                "time": now,
                "detail": f"{carrier}: {tracking_number}",
            })
            _save_json(self.site_id, self.ORDERS_FILE, orders)
            return orders[idx]

    def refund_order(self, order_id: str, amount: float, reason: str) -> dict:
        with self._lock:
            orders = _load_json(self.site_id, self.ORDERS_FILE, list)
            idx = next((i for i, o in enumerate(orders) if o["id"] == order_id), None)
            if idx is None:
                raise ValueError(f"Order not found: {order_id}")
            now = _now_iso()
            orders[idx]["status"] = "refunded"
            orders[idx]["payment"]["status"] = "refunded"
            orders[idx]["updated_at"] = now
            orders[idx]["logs"].append({
                "action": "refunded",
                "time": now,
                "detail": f"Refund {amount}: {reason}",
            })
            _save_json(self.site_id, self.ORDERS_FILE, orders)
            return orders[idx]

    def batch_update_status(self, order_ids: list[str], status: str) -> int:
        with self._lock:
            orders = _load_json(self.site_id, self.ORDERS_FILE, list)
            now = _now_iso()
            count = 0
            for o in orders:
                if o["id"] in order_ids:
                    o["status"] = status
                    o["updated_at"] = now
                    o["logs"].append({"action": "batch_status_change", "time": now, "detail": f"→ {status}"})
                    count += 1
            _save_json(self.site_id, self.ORDERS_FILE, orders)
            return count

    def export_orders_csv(self) -> str:
        orders = _load_json(self.site_id, self.ORDERS_FILE, list)
        output = io.StringIO()
        fieldnames = [
            "id", "order_no", "status", "customer_name", "customer_phone",
            "subtotal", "shipping_fee", "discount", "total", "currency",
            "payment_method", "payment_status", "tracking_number", "carrier",
            "created_at",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for o in orders:
            cust = o.get("customer", {})
            pay = o.get("payment", {})
            ship = o.get("shipping", {})
            writer.writerow({
                "id": o["id"],
                "order_no": o.get("order_no", ""),
                "status": o.get("status", ""),
                "customer_name": cust.get("name", ""),
                "customer_phone": cust.get("phone", ""),
                "subtotal": o.get("subtotal", ""),
                "shipping_fee": o.get("shipping_fee", ""),
                "discount": o.get("discount", ""),
                "total": o.get("total", ""),
                "currency": o.get("currency", "CNY"),
                "payment_method": pay.get("method", ""),
                "payment_status": pay.get("status", ""),
                "tracking_number": ship.get("tracking_number", ""),
                "carrier": ship.get("carrier", ""),
                "created_at": o.get("created_at", ""),
            })
        return output.getvalue()

    def get_stats(self, days: int = 7) -> dict:
        """统计数据：今日订单/收入，对比昨日，7日趋势"""
        orders = _load_json(self.site_id, self.ORDERS_FILE, list)
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        yesterday_start = today_start - timedelta(days=1)

        def parse(s: str) -> datetime:
            return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)

        def paid_orders(os: list[dict]) -> list[dict]:
            return [o for o in os if o.get("status") in ("paid", "shipped", "completed")]

        def in_range(os: list[dict], start: datetime, end: datetime) -> list[dict]:
            return [
                o for o in os
                if start <= parse(o.get("created_at", "")) < end
            ]

        today = in_range(orders, today_start, now)
        yesterday = in_range(orders, yesterday_start, today_start)

        today_paid = paid_orders(today)
        yesterday_paid = paid_orders(yesterday)

        def revenue(os: list[dict]) -> float:
            return sum(o.get("total", 0) for o in os)

        # 7日趋势
        from datetime import timedelta
        trend = []
        for i in range(6, -1, -1):
            d_start = today_start - timedelta(days=i)
            d_end = d_start + timedelta(days=1)
            day_orders = paid_orders(in_range(orders, d_start, d_end))
            trend.append({
                "date": d_start.strftime("%Y-%m-%d"),
                "orders": len(day_orders),
                "revenue": revenue(day_orders),
            })

        def pct(a: float, b: float) -> float | None:
            if b == 0:
                return None
            return round((a - b) / b * 100, 2)

        return {
            "today": {
                "orders": len(today_paid),
                "revenue": revenue(today_paid),
                "vs_yesterday_orders": pct(len(today_paid), len(yesterday_paid)),
                "vs_yesterday_revenue": pct(revenue(today_paid), revenue(yesterday_paid)),
            },
            "trend_7d": trend,
        }


# ──────────────────────────────────────────────────────────────────────────────
# CouponStore
# ──────────────────────────────────────────────────────────────────────────────

class CouponStore:
    """优惠券管理"""

    COUPONS_FILE = "coupons"

    def __init__(self, site_id: str):
        self.site_id = site_id
        self._lock = threading.Lock()

    def list_coupons(self) -> list[dict]:
        return _load_json(self.site_id, self.COUPONS_FILE, list)

    def create_coupon(self, data: dict) -> dict:
        with self._lock:
            coupons = _load_json(self.site_id, self.COUPONS_FILE, list)
            coupon = {
                "id": _gen_id("coup_"),
                "code": data.get("code", "").upper(),
                "type": data.get("type", "fixed"),  # percent / fixed / freeshipping
                "value": float(data.get("value", 0)),
                "min_amount": float(data.get("min_amount", 0)),
                "max_uses": int(data.get("max_uses", 0)),
                "used_count": 0,
                "start_date": data.get("start_date", ""),
                "end_date": data.get("end_date", ""),
                "status": data.get("status", "active"),
                "created_at": _now_iso(),
            }
            coupons.append(coupon)
            _save_json(self.site_id, self.COUPONS_FILE, coupons)
            return coupon

    def validate_coupon(self, code: str, cart_total: float) -> dict:
        coupons = _load_json(self.site_id, self.COUPONS_FILE, list)
        now = datetime.now(timezone.utc)
        coupon = next(
            (c for c in coupons if c.get("code", "").upper() == code.upper()),
            None,
        )
        if not coupon:
            return {"valid": False, "discount": 0, "message": "优惠券不存在"}

        if coupon.get("status") != "active":
            return {"valid": False, "discount": 0, "message": "优惠券已停用"}

        if coupon.get("max_uses", 0) > 0 and coupon.get("used_count", 0) >= coupon["max_uses"]:
            return {"valid": False, "discount": 0, "message": "优惠券已用完"}

        start = coupon.get("start_date")
        end = coupon.get("end_date")
        if start:
            try:
                if datetime.fromisoformat(start) > now:
                    return {"valid": False, "discount": 0, "message": "优惠券尚未开始"}
            except ValueError:
                pass
        if end:
            try:
                if datetime.fromisoformat(end) < now:
                    return {"valid": False, "discount": 0, "message": "优惠券已过期"}
            except ValueError:
                pass

        if cart_total < coupon.get("min_amount", 0):
            return {
                "valid": False,
                "discount": 0,
                "message": f"满 {coupon['min_amount']} 元可用",
            }

        discount = 0.0
        if coupon["type"] == "percent":
            discount = round(cart_total * coupon["value"] / 100, 2)
        elif coupon["type"] == "fixed":
            discount = min(coupon["value"], cart_total)
        # freeshipping: discount 由运费模块另行处理，此处仅标记有效
        return {"valid": True, "discount": discount, "message": "可用"}

    def delete_coupon(self, coupon_id: str) -> bool:
        with self._lock:
            coupons = _load_json(self.site_id, self.COUPONS_FILE, list)
            before = len(coupons)
            coupons = [c for c in coupons if c["id"] != coupon_id]
            if len(coupons) == before:
                return False
            _save_json(self.site_id, self.COUPONS_FILE, coupons)
            return True


# ──────────────────────────────────────────────────────────────────────────────
# ReviewStore
# ──────────────────────────────────────────────────────────────────────────────

class ReviewStore:
    """商品评价管理"""

    REVIEWS_FILE = "reviews"

    def __init__(self, site_id: str):
        self.site_id = site_id
        self._lock = threading.Lock()

    def list_reviews(
        self,
        product_id: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        reviews = _load_json(self.site_id, self.REVIEWS_FILE, list)
        if product_id:
            reviews = [r for r in reviews if r.get("product_id") == product_id]
        reviews.sort(key=lambda r: r.get("created_at", ""), reverse=True)
        total = len(reviews)
        start = (page - 1) * per_page
        end = start + per_page
        return {
            "items": reviews[start:end],
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
        }

    def create_review(self, data: dict) -> dict:
        with self._lock:
            reviews = _load_json(self.site_id, self.REVIEWS_FILE, list)
            review = {
                "id": _gen_id("rev_"),
                "product_id": data.get("product_id", ""),
                "rating": int(data.get("rating", 5)),
                "content": data.get("content", ""),
                "images": data.get("images", []),
                "user_name": data.get("user_name", "匿名用户"),
                "user_id": data.get("user_id", ""),
                "status": data.get("status", "approved"),
                "created_at": _now_iso(),
            }
            reviews.append(review)
            _save_json(self.site_id, self.REVIEWS_FILE, reviews)
            return review

    def get_product_rating(self, product_id: str) -> dict:
        reviews = _load_json(self.site_id, self.REVIEWS_FILE, list)
        product_reviews = [
            r for r in reviews
            if r.get("product_id") == product_id and r.get("status") == "approved"
        ]
        if not product_reviews:
            return {"average": 0, "count": 0, "distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}}
        total = sum(r["rating"] for r in product_reviews)
        dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for r in product_reviews:
            dist[r["rating"]] = dist.get(r["rating"], 0) + 1
        return {
            "average": round(total / len(product_reviews), 2),
            "count": len(product_reviews),
            "distribution": dist,
        }


# ──────────────────────────────────────────────────────────────────────────────
# ShippingStore
# ──────────────────────────────────────────────────────────────────────────────

class ShippingStore:
    """物流配置与费用计算"""

    SHIPPING_FILE = "shipping"

    def __init__(self, site_id: str):
        self.site_id = site_id

    def get_config(self) -> dict:
        default = {
            "methods": [
                {"id": "sf", "name": "顺丰速运", "description": "1-2个工作日", "base_fee": 12},
                {"id": "ems", "name": "EMS", "description": "3-5个工作日", "base_fee": 8},
                {"id": "yt", "name": "圆通快递", "description": "3-7个工作日", "base_fee": 5},
            ],
            "free_shipping_min": 199,
            "default_method": "sf",
        }
        return _load_json(self.site_id, self.SHIPPING_FILE, dict) or default

    def update_config(self, data: dict) -> dict:
        config = self.get_config()
        for k, v in data.items():
            if k != "id":
                config[k] = v
        _save_json(self.site_id, self.SHIPPING_FILE, config)
        return config

    def calculate_shipping(self, items: list[dict], address: dict) -> dict:
        """
        items: [{"weight": 200, "quantity": 2, "price": 89}, ...]
        address: {"province": "广东", ...}
        """
        config = self.get_config()
        total_weight = sum(item.get("weight", 0) * item.get("quantity", 1) for item in items)
        # 首重 1kg，续重 0.5kg
        base_weight = 1000  # grams
        extra_units = max(0, (total_weight - base_weight) / 500)

        available = []
        free_min = config.get("free_shipping_min", 199)
        order_total = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)

        for method in config.get("methods", []):
            base = method.get("base_fee", 10)
            extra_fee = round(extra_units * 2, 2)  # 续重每500g加2元
            fee = round(base + extra_fee, 2)
            if order_total >= free_min:
                fee = 0.0
            available.append({
                "id": method["id"],
                "name": method["name"],
                "description": method.get("description", ""),
                "fee": fee,
                "estimated_days": method.get("description", ""),
            })

        return {
            "items": available,
            "total_weight": total_weight,
            "order_total": order_total,
            "free_threshold": free_min,
            "free_shipping": order_total >= free_min,
            "default_method": config.get("default_method", "sf"),
        }


# ──────────────────────────────────────────────────────────────────────────────
# PaymentConfigStore
# ──────────────────────────────────────────────────────────────────────────────

class PaymentConfigStore:
    """支付渠道配置（脱敏存储）"""

    PAYMENT_FILE = "payment_config"

    def __init__(self, site_id: str):
        self.site_id = site_id

    def _mask(self, value: str) -> str:
        if not value or len(value) < 6:
            return "****"
        return value[:3] + "***" + value[-3:]

    def get_config(self) -> dict:
        raw = _load_json(self.site_id, self.PAYMENT_FILE, dict) or {}
        masked = {}
        for channel in ("wechat", "alipay", "paypal"):
            ch = raw.get(channel, {})
            masked[channel] = {
                "enabled": ch.get("enabled", False),
                "app_id": self._mask(ch.get("app_id", "")),
                "merchant_id": self._mask(ch.get("merchant_id", "")),
                "api_key": self._mask(ch.get("api_key", "")),
            }
        return masked

    def update_config(self, channel: str, data: dict) -> dict:
        if channel not in ("wechat", "alipay", "paypal"):
            raise ValueError(f"Unknown channel: {channel}")
        raw = _load_json(self.site_id, self.PAYMENT_FILE, dict) or {}
        raw[channel] = {
            "enabled": data.get("enabled", True),
            "app_id": data.get("app_id", ""),
            "merchant_id": data.get("merchant_id", ""),
            "api_key": data.get("api_key", ""),
        }
        _save_json(self.site_id, self.PAYMENT_FILE, raw)
        return self.get_config()

    def test_config(self, channel: str) -> dict:
        raw = _load_json(self.site_id, self.PAYMENT_FILE, dict) or {}
        ch = raw.get(channel, {})
        app_id = ch.get("app_id", "")
        merchant_id = ch.get("merchant_id", "")
        api_key = ch.get("api_key", "")
        if not all([app_id, merchant_id, api_key]):
            return {"success": False, "message": "配置不完整，请填写所有必填字段"}
        # 模拟测试：检查字段格式
        if channel == "wechat" and not app_id.startswith("wx"):
            return {"success": False, "message": "微信 AppID 格式错误（应以 wx 开头）"}
        if channel == "alipay" and not merchant_id.startswith("20"):
            return {"success": False, "message": "支付宝商户号格式错误"}
        if channel == "paypal" and "@" not in api_key:
            return {"success": False, "message": "PayPal 配置格式错误"}
        return {"success": True, "message": "配置正确（模拟测试通过）"}


# ──────────────────────────────────────────────────────────────────────────────
# SiteConfigStore
# ──────────────────────────────────────────────────────────────────────────────

class SiteConfigStore:
    """站点全局配置（主题、语言、货币、Logo 等）"""

    SITE_CONFIG_FILE = "site_config"

    PRESET_THEMES = [
        {"id": "minimal", "name": "极简白", "preview": "/themes/minimal/preview.png"},
        {"id": "nature", "name": "自然绿", "preview": "/themes/nature/preview.png"},
        {"id": "dark", "name": "暗夜黑", "preview": "/themes/dark/preview.png"},
        {"id": "bloom", "name": "花语粉", "preview": "/themes/bloom/preview.png"},
        {"id": "nordic", "name": "北欧灰", "preview": "/themes/nordic/preview.png"},
        {"id": "vintage", "name": "复古棕", "preview": "/themes/vintage/preview.png"},
    ]

    def __init__(self, site_id: str):
        self.site_id = site_id

    def get_config(self) -> dict:
        default = {
            "theme": "minimal",
            "language": "zh-CN",
            "currency": "CNY",
            "currency_symbol": "¥",
            "logo": "",
            "favicon": "",
            "site_name": "我的商店",
            "site_description": "",
            "contact_email": "",
            "seo": {},
        }
        stored = _load_json(self.site_id, self.SITE_CONFIG_FILE, dict) or {}
        return {**default, **stored}

    def update_config(self, data: dict) -> dict:
        config = self.get_config()
        for k, v in data.items():
            if k != "id":
                config[k] = v
        _save_json(self.site_id, self.SITE_CONFIG_FILE, config)
        return config

    def get_themes(self) -> list[dict]:
        return self.PRESET_THEMES
