"""
apis.routes.admin_ecommerce — 管理员电商API路由

所有端点需要管理员JWT认证。
管理后台前端调用这些API管理商品/订单/优惠券/支付/运费/站点配置。
"""

import csv
import io
import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from apis.routes.auth import require_admin, _load_users, _is_pro
from core.ecommerce.store import (
    ProductStore, OrderStore, CouponStore, ReviewStore,
    ShippingStore, PaymentConfigStore, SiteConfigStore,
)

router = APIRouter(prefix="/admin/ecommerce", tags=["管理-电商"])

# 默认站点ID（单站点模式，后续可扩展多站点）
DEFAULT_SITE = "default"


def _get_site_id(request: Request) -> str:
    """从请求头或查询参数获取site_id，默认default"""
    return request.query_params.get("site_id", DEFAULT_SITE)


# ═══════════════════════════════════════════════════════════
#  仪表盘
# ═══════════════════════════════════════════════════════════

@router.get("/dashboard")
async def dashboard(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    order_store = OrderStore(site_id)
    product_store = ProductStore(site_id)
    users = _load_users()

    stats = order_store.get_stats(days=7)

    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    total_users = len(users)
    pro_users = sum(1 for u in users.values() if _is_pro(u))
    active_today = sum(1 for u in users.values() if u.get("usage", {}).get(today, 0) > 0)

    return {
        "today_orders": stats.get("today_orders", 0),
        "yesterday_orders": stats.get("yesterday_orders", 0),
        "order_change": stats.get("order_change", "0%"),
        "revenue": stats.get("today_revenue", 0),
        "yesterday_revenue": stats.get("yesterday_revenue", 0),
        "revenue_change": stats.get("revenue_change", "0%"),
        "new_users": active_today,
        "total_users": total_users,
        "pro_users": pro_users,
        "conversion_rate": stats.get("conversion_rate", "0%"),
        "orders_7d": stats.get("orders_7d", []),
        "low_stock_products": product_store.get_low_stock_products(threshold=10),
    }


# ═══════════════════════════════════════════════════════════
#  商品管理
# ═══════════════════════════════════════════════════════════

@router.get("/products")
async def list_products(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = ProductStore(site_id)
    category = request.query_params.get("category")
    status = request.query_params.get("status")
    keyword = request.query_params.get("keyword")
    page = int(request.query_params.get("page", 1))
    per_page = int(request.query_params.get("per_page", 20))

    result = store.list_products(category=category, status=status or None, page=page, per_page=per_page)

    # 统一返回格式
    response = {
        "products": result.get("items", []),
        "pagination": {
            "total": result.get("total", 0),
            "page": result.get("page", 1),
            "per_page": result.get("per_page", 20),
            "pages": result.get("pages", 0),
        }
    }

    # 关键词过滤
    if keyword:
        kw = keyword.lower()
        response["products"] = [
            p for p in response["products"]
            if kw in p.get("name", "").lower() or kw in p.get("description", "").lower()
        ]
        response["pagination"]["total"] = len(response["products"])

    return response


@router.get("/products/{product_id}")
async def get_product(product_id: str, request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = ProductStore(site_id)
    product = store.get_product(product_id)
    if not product:
        raise HTTPException(404, "商品不存在")
    return product


@router.post("/products")
async def create_product(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = ProductStore(site_id)
    body = await request.json()

    # 验证必填字段
    if not body.get("name"):
        raise HTTPException(422, "商品名称必填")
    if not body.get("variants"):
        raise HTTPException(422, "至少需要一个规格变体")

    # 为变体生成ID和SKU
    for v in body["variants"]:
        if not v.get("id"):
            v["id"] = "var_" + uuid.uuid4().hex[:8]
        if not v.get("sku"):
            v["sku"] = "SKU-" + uuid.uuid4().hex[:6].upper()

    product = store.create_product(body)
    return product


@router.put("/products/{product_id}")
async def update_product(product_id: str, request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = ProductStore(site_id)
    body = await request.json()

    existing = store.get_product(product_id)
    if not existing:
        raise HTTPException(404, "商品不存在")

    product = store.update_product(product_id, body)
    return product


@router.delete("/products/{product_id}")
async def delete_product(product_id: str, request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = ProductStore(site_id)
    ok = store.delete_product(product_id)
    if not ok:
        raise HTTPException(404, "商品不存在")
    return {"success": True}


@router.post("/products/batch-status")
async def batch_update_product_status(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = ProductStore(site_id)
    body = await request.json()
    product_ids = body.get("product_ids", [])
    status = body.get("status")

    if status not in ("active", "draft", "archived"):
        raise HTTPException(400, "状态只能是 active/draft/archived")

    count = store.batch_update_status(product_ids, status)
    return {"success": True, "updated": count}


@router.get("/products/export")
async def export_products(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = ProductStore(site_id)
    csv_content = store.export_products_csv()

    output = io.BytesIO(csv_content.encode("utf-8-sig"))
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=products_{site_id}.csv"},
    )


@router.post("/products/import")
async def import_products(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = ProductStore(site_id)
    body = await request.json()
    csv_content = body.get("csv", "")
    result = store.import_products_csv(csv_content)
    return result


# ═══════════════════════════════════════════════════════════
#  分类管理
# ═══════════════════════════════════════════════════════════

@router.get("/categories")
async def list_categories(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = ProductStore(site_id)
    return store.list_categories()


@router.post("/categories")
async def create_category(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = ProductStore(site_id)
    body = await request.json()
    if not body.get("name"):
        raise HTTPException(422, "分类名称必填")
    return store.create_category(
        name=body["name"],
        parent_id=body.get("parent_id"),
        sort_order=body.get("sort_order", 0),
    )


@router.put("/categories/{cat_id}")
async def update_category(cat_id: str, request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = ProductStore(site_id)
    body = await request.json()
    return store.update_category(cat_id, body)


@router.delete("/categories/{cat_id}")
async def delete_category(cat_id: str, request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = ProductStore(site_id)
    ok = store.delete_category(cat_id)
    if not ok:
        raise HTTPException(404, "分类不存在")
    return {"success": True}


# ═══════════════════════════════════════════════════════════
#  订单管理
# ═══════════════════════════════════════════════════════════

@router.get("/orders")
async def list_orders(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = OrderStore(site_id)
    status = request.query_params.get("status")
    page = int(request.query_params.get("page", 1))
    per_page = int(request.query_params.get("per_page", 20))
    return store.list_orders(status=status, page=page, per_page=per_page)


@router.get("/orders/{order_id}")
async def get_order(order_id: str, request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = OrderStore(site_id)
    order = store.get_order(order_id)
    if not order:
        raise HTTPException(404, "订单不存在")
    return order


@router.put("/orders/{order_id}/status")
async def update_order_status(order_id: str, request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = OrderStore(site_id)
    body = await request.json()
    new_status = body.get("status")
    note = body.get("note", "")

    valid = ("pending", "paid", "shipped", "completed", "cancelled", "refunding", "refunded")
    if new_status not in valid:
        raise HTTPException(400, f"状态必须是: {', '.join(valid)}")

    order = store.update_order_status(order_id, new_status, note)
    return order


@router.put("/orders/{order_id}/tracking")
async def add_tracking(order_id: str, request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = OrderStore(site_id)
    body = await request.json()
    tracking = body.get("tracking_number", "")
    carrier = body.get("carrier", "")

    if not tracking:
        raise HTTPException(422, "运单号必填")

    order = store.add_tracking(order_id, tracking, carrier)
    return order


@router.post("/orders/{order_id}/refund")
async def refund_order(order_id: str, request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = OrderStore(site_id)
    body = await request.json()
    amount = body.get("amount", 0)
    reason = body.get("reason", "")

    if amount <= 0:
        raise HTTPException(400, "退款金额必须大于0")

    order = store.refund_order(order_id, amount, reason)
    return order


@router.post("/orders/batch-status")
async def batch_update_orders(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = OrderStore(site_id)
    body = await request.json()
    order_ids = body.get("order_ids", [])
    status = body.get("status")

    count = store.batch_update_status(order_ids, status)
    return {"success": True, "updated": count}


@router.get("/orders/export")
async def export_orders(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = OrderStore(site_id)
    csv_content = store.export_orders_csv()

    output = io.BytesIO(csv_content.encode("utf-8-sig"))
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=orders_{site_id}.csv"},
    )


# ═══════════════════════════════════════════════════════════
#  优惠券管理
# ═══════════════════════════════════════════════════════════

@router.get("/coupons")
async def list_coupons(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = CouponStore(site_id)
    return store.list_coupons()


@router.post("/coupons")
async def create_coupon(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = CouponStore(site_id)
    body = await request.json()

    if not body.get("code"):
        raise HTTPException(422, "优惠券代码必填")
    if body.get("type") not in ("percent", "fixed", "freeshipping"):
        raise HTTPException(400, "类型只能是 percent/fixed/freeshipping")
    if body.get("value", 0) <= 0 and body["type"] != "freeshipping":
        raise HTTPException(400, "面值必须大于0")

    return store.create_coupon(body)


@router.delete("/coupons/{coupon_id}")
async def delete_coupon(coupon_id: str, request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = CouponStore(site_id)
    ok = store.delete_coupon(coupon_id)
    if not ok:
        raise HTTPException(404, "优惠券不存在")
    return {"success": True}


# ═══════════════════════════════════════════════════════════
#  支付配置
# ═══════════════════════════════════════════════════════════

@router.get("/payment-config")
async def get_payment_config(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = PaymentConfigStore(site_id)
    return store.get_config()


@router.put("/payment-config/{channel}")
async def update_payment_config(channel: str, request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = PaymentConfigStore(site_id)

    if channel not in ("wechat", "alipay", "paypal"):
        raise HTTPException(400, "渠道只能是 wechat/alipay/paypal")

    body = await request.json()
    return store.update_config(channel, body)


@router.post("/payment-config/{channel}/test")
async def test_payment_config(channel: str, request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = PaymentConfigStore(site_id)

    if channel not in ("wechat", "alipay", "paypal"):
        raise HTTPException(400, "渠道只能是 wechat/alipay/paypal")

    return store.test_config(channel)


# ═══════════════════════════════════════════════════════════
#  运费配置
# ═══════════════════════════════════════════════════════════

@router.get("/shipping-config")
async def get_shipping_config(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = ShippingStore(site_id)
    return store.get_config()


@router.put("/shipping-config")
async def update_shipping_config(request: Request, admin=Depends(require_admin)):
    try:
        site_id = _get_site_id(request)
        store = ShippingStore(site_id)
        body = await request.json()
        return store.update_config(body)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新运费配置失败: {e}")
        raise HTTPException(500, "更新运费配置失败")


# ═══════════════════════════════════════════════════════════
#  站点配置
# ═══════════════════════════════════════════════════════════

@router.get("/site-config")
async def get_site_config(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = SiteConfigStore(site_id)
    return store.get_config()


@router.put("/site-config")
async def update_site_config(request: Request, admin=Depends(require_admin)):
    try:
        site_id = _get_site_id(request)
        store = SiteConfigStore(site_id)
        body = await request.json()
        return store.update_config(body)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新站点配置失败: {e}")
        raise HTTPException(500, "更新站点配置失败")


@router.get("/themes")
async def get_themes(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    store = SiteConfigStore(site_id)
    return store.get_themes()


# ═══════════════════════════════════════════════════════════
#  客户管理
# ═══════════════════════════════════════════════════════════

@router.get("/customers")
async def list_customers(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    order_store = OrderStore(site_id)

    page = int(request.query_params.get("page", 1))
    per_page = int(request.query_params.get("per_page", 20))

    # 从订单中聚合客户信息
    all_orders = order_store.list_orders(page=1, per_page=9999).get("orders", [])
    customer_map = {}
    for o in all_orders:
        phone = o.get("customer", {}).get("phone", "")
        if not phone:
            continue
        if phone not in customer_map:
            customer_map[phone] = {
                "id": "cust_" + phone[-4:],
                "name": o.get("customer", {}).get("name", ""),
                "phone": phone,
                "email": o.get("customer", {}).get("email", ""),
                "order_count": 0,
                "total_spent": 0,
                "last_order": "",
            }
        customer_map[phone]["order_count"] += 1
        customer_map[phone]["total_spent"] += o.get("total", 0)
        customer_map[phone]["last_order"] = o.get("created_at", "")

    customers = sorted(customer_map.values(), key=lambda c: c["last_order"], reverse=True)
    total = len(customers)
    start = (page - 1) * per_page
    page_customers = customers[start:start + per_page]

    return {
        "customers": page_customers,
        "pagination": {
            "page": page, "per_page": per_page,
            "total": total, "total_pages": (total + per_page - 1) // per_page,
        },
    }


@router.get("/customers/{customer_id}")
async def get_customer(customer_id: str, request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    order_store = OrderStore(site_id)

    # 查找客户的所有订单
    all_orders = order_store.list_orders(page=1, per_page=9999).get("orders", [])
    customer_orders = []
    customer_info = {}
    for o in all_orders:
        phone = o.get("customer", {}).get("phone", "")
        if phone and "cust_" + phone[-4:] == customer_id:
            customer_orders.append(o)
            if not customer_info:
                customer_info = o.get("customer", {})

    return {
        "customer": customer_info,
        "orders": customer_orders,
    }


# ═══════════════════════════════════════════════════════════
#  备份与恢复
# ═══════════════════════════════════════════════════════════

@router.post("/backup")
async def create_backup(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    import zipfile
    import tempfile

    backup_data = {}
    data_dir = Path("data")
    for f in data_dir.glob(f"*_{site_id}.json"):
        backup_data[f.name] = json.loads(f.read_text(encoding="utf-8"))

    # 也备份通用数据
    for name in ["users.json", "codes.json"]:
        f = data_dir / name
        if f.exists():
            backup_data[name] = json.loads(f.read_text(encoding="utf-8"))

    backup_id = "bak_" + uuid.uuid4().hex[:8]
    backup_content = json.dumps(backup_data, ensure_ascii=False, indent=2)

    # 保存备份文件
    backup_dir = Path("data/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"{backup_id}.json"
    backup_path.write_text(backup_content, encoding="utf-8")

    return {
        "success": True,
        "backup_id": backup_id,
        "size": len(backup_content),
        "download_url": f"/api/v1/admin/ecommerce/backup/{backup_id}/download",
    }


@router.get("/backup/{backup_id}/download")
async def download_backup(backup_id: str, request: Request, admin=Depends(require_admin)):
    backup_path = Path("data/backups") / f"{backup_id}.json"
    if not backup_path.exists():
        raise HTTPException(404, "备份不存在")

    content = backup_path.read_text(encoding="utf-8")
    output = io.BytesIO(content.encode("utf-8"))
    return StreamingResponse(
        output,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename=backup_{backup_id}.json"},
    )


@router.post("/restore")
async def restore_backup(request: Request, admin=Depends(require_admin)):
    body = await request.json()
    backup_data = body.get("data", {})
    site_id = _get_site_id(request)

    if not backup_data:
        raise HTTPException(400, "无备份数据")

    restored = 0
    data_dir = Path("data")
    for filename, content in backup_data.items():
        if filename.endswith(".json"):
            f = data_dir / filename
            f.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
            restored += 1

    return {"success": True, "restored_files": restored}


# ═══════════════════════════════════════════════════════════
#  操作日志
# ═══════════════════════════════════════════════════════════

@router.get("/audit-log")
async def get_audit_log(request: Request, admin=Depends(require_admin)):
    site_id = _get_site_id(request)
    log_path = Path("data") / f"audit_{site_id}.json"

    if not log_path.exists():
        return {"logs": [], "pagination": {"page": 1, "total": 0}}

    logs = json.loads(log_path.read_text(encoding="utf-8"))
    page = int(request.query_params.get("page", 1))
    per_page = int(request.query_params.get("per_page", 50))

    total = len(logs)
    start = (page - 1) * per_page
    page_logs = logs[start:start + per_page]

    return {
        "logs": page_logs,
        "pagination": {
            "page": page, "per_page": per_page,
            "total": total, "total_pages": (total + per_page - 1) // per_page,
        },
    }
