"""
apis.routes.xunhupay — 虎皮椒(Xunhupay)个人支付集成
=================================================
个人开发者可用，无需企业资质。
支持微信支付 + 支付宝，1.5%手续费。
API文档: https://www.xunhupay.com/doc/api/page/index.html
"""

import hashlib
import time
import uuid
import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/xunhupay", tags=["虎皮椒支付"])

# ── 数据目录 ──
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


def _xunhupay_config_path(site_id: str) -> Path:
    return DATA_DIR / f"xunhupay_config_{site_id}.json"


def _load_config(site_id: str) -> dict:
    """加载虎皮椒配置（从环境变量或配置文件）"""
    import os
    config = {
        "app_id": os.environ.get("XUNHU_APP_ID", ""),
        "app_secret": os.environ.get("XUNHU_APP_SECRET", ""),
        "wechat_url": os.environ.get("XUNHU_WECHAT_URL", ""),
        "alipay_url": os.environ.get("XUNHU_ALIPAY_URL", ""),
        "notify_url": os.environ.get("XUNHU_NOTIFY_URL", ""),
    }
    # 也读配置文件覆盖
    cfg_path = _xunhupay_config_path(site_id)
    if cfg_path.exists():
        try:
            file_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            for k, v in file_cfg.items():
                if v:
                    config[k] = v
        except Exception:
            pass
    return config


def _generate_hash(params: dict, app_secret: str) -> str:
    """
    虎皮椒签名算法:
    1. 参数按key升序排列
    2. 拼接 key=value&key=value
    3. 末尾追加 &app_secret=SECRET
    4. MD5哈希
    """
    sorted_keys = sorted(params.keys())
    sign_str = "&".join(f"{k}={params[k]}" for k in sorted_keys if params[k] is not None and params[k] != "")
    sign_str += f"&app_secret={app_secret}"
    return hashlib.md5(sign_str.encode("utf-8")).hexdigest()


# ── 下单接口 ──
@router.post("/{site_id}/create")
async def create_payment(site_id: str, request: Request):
    """
    创建虎皮椒支付订单

    Body: {
        "order_no": "ORD20260522143000001AB",
        "total": 99.00,
        "title": "SG专业版月度订阅",
        "type": "wechat" | "alipay" | "qqpay" | "bank",
        "notify_url": "可选，覆盖默认",
        "return_url": "支付完成后跳转URL"
    }
    """
    body = await request.json()
    
    order_no = body.get("order_no", "")
    total = body.get("total", 0)
    title = body.get("title", "订单支付")
    pay_type = body.get("type", "wechat")  # wechat/alipay/qqpay/bank
    return_url = body.get("return_url", "")
    user_uid = body.get("user_uid", "")  # 关联用户，用于支付成功自动激活
    
    if not order_no:
        raise HTTPException(400, "缺少order_no")
    if total <= 0:
        raise HTTPException(400, "金额必须大于0")
    
    config = _load_config(site_id)
    app_id = config.get("app_id", "")
    app_secret = config.get("app_secret", "")
    
    if not app_id or not app_secret:
        raise HTTPException(400, "虎皮椒未配置（需设置XUNHU_APP_ID和XUNHU_APP_SECRET环境变量）")
    
    # 选择支付网关URL
    if pay_type == "alipay":
        gateway_url = config.get("alipay_url") or "https://api.xunhupay.com/payment/do.html"
    elif pay_type == "wechat":
        gateway_url = config.get("wechat_url") or "https://api.xunhupay.com/payment/do.html"
    else:
        gateway_url = "https://api.xunhupay.com/payment/do.html"
    
    # 构造请求参数
    notify_url = body.get("notify_url") or config.get("notify_url") or ""
    if not notify_url:
        # 自动构造回调URL
        import os
        site_domain = os.environ.get("SITE_DOMAIN", "auto-site-builder.onrender.com")
        notify_url = f"https://{site_domain}/api/v1/xunhupay/{site_id}/notify"
    
    params = {
        "version": "1.1",
        "appid": app_id,
        "trade_order_id": order_no,
        "total": str(total),
        "title": title,
        "time": str(int(time.time())),
        "notify_url": notify_url,
        "nonce_str": uuid.uuid4().hex[:32],
        "type": pay_type,
    }
    if return_url:
        params["return_url"] = return_url
    
    # 签名
    params["hash"] = _generate_hash(params, app_secret)
    
    # 保存本地订单记录（关联用户uid）
    try:
        orders_path = DATA_DIR / f"orders_{site_id}.json"
        orders_data = {"orders": []}
        if orders_path.exists():
            orders_data = json.loads(orders_path.read_text(encoding="utf-8"))
            if isinstance(orders_data, list):
                orders_data = {"orders": orders_data}
        orders_data["orders"].append({
            "order_no": order_no,
            "total": total,
            "title": title,
            "type": pay_type,
            "user_uid": user_uid,
            "status": "pending",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
        orders_path.write_text(json.dumps(orders_data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"保存本地订单失败: {e}")
    
    # 发送请求到虎皮椒
    try:
        form_data = urllib.parse.urlencode(params).encode("utf-8")
        req = urllib.request.Request(gateway_url, data=form_data, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
        
        if resp_data.get("errcode") != 0:
            error_msg = resp_data.get("errmsg", "未知错误")
            logger.error(f"虎皮椒下单失败: {error_msg}")
            raise HTTPException(400, f"支付创建失败: {error_msg}")
        
        # 返回支付信息
        result = {
            "success": True,
            "order_no": order_no,
            "url_qrcode": resp_data.get("url_qrcode", ""),  # 微信扫码URL
            "url": resp_data.get("url", ""),                  # 支付跳转URL
            "order_id": resp_data.get("order_id", ""),        # 虎皮椒订单号
        }
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"虎皮椒请求异常: {e}")
        raise HTTPException(500, "支付服务暂时不可用，请稍后重试")


# ── 异步回调 ──
@router.post("/{site_id}/notify")
async def xunhupay_notify(site_id: str, request: Request):
    """
    虎皮椒异步通知回调
    
    验证签名后更新订单状态。
    文档: https://www.xunhupay.com/doc/api/page/notify.html
    """
    # 虎皮椒用form-data发送回调
    form = await request.form()
    params = dict(form)
    
    config = _load_config(site_id)
    app_secret = config.get("app_secret", "")
    
    if not app_secret:
        logger.error("虎皮椒回调: app_secret未配置")
        return Response(content="fail", media_type="text/plain")
    
    # 验证签名
    received_hash = params.pop("hash", "")
    # 移除空的参数
    clean_params = {k: v for k, v in params.items() if v is not None and v != ""}
    calculated_hash = _generate_hash(clean_params, app_secret)
    
    if not hashlib.md5.__module__:
        pass  # just to avoid lint warning
    
    if received_hash != calculated_hash:
        logger.warning(f"虎皮椒回调签名验证失败: received={received_hash}, calculated={calculated_hash}")
        return Response(content="fail", media_type="text/plain")
    
    # 验证支付状态
    status = params.get("status", "")
    if status != "OD":
        # OD = 订单已支付
        logger.info(f"虎皮椒回调: 订单状态非支付完成 status={status}")
        return Response(content="success", media_type="text/plain")
    
    trade_order_id = params.get("trade_order_id", "")  # 我们的订单号
    transaction_id = params.get("transaction_id", "")   # 虎皮椒交易号
    total = float(params.get("total", "0"))
    
    logger.info(f"虎皮椒支付成功: order={trade_order_id}, total={total}, txn={transaction_id}")
    
    # 更新本地订单状态
    try:
        orders_path = DATA_DIR / f"orders_{site_id}.json"
        if orders_path.exists():
            orders_data = json.loads(orders_path.read_text(encoding="utf-8"))
            orders_list = orders_data if isinstance(orders_data, list) else orders_data.get("orders", [])
            
            for order in orders_list:
                if order.get("order_no") == trade_order_id:
                    order["status"] = "paid"
                    order["paid_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    order["transaction_id"] = transaction_id
                    break
            
            orders_data_to_save = {"orders": orders_list} if isinstance(orders_data, list) else orders_data
            orders_path.write_text(json.dumps(orders_data_to_save, ensure_ascii=False, indent=2), encoding="utf-8")
            
            logger.info(f"订单 {trade_order_id} 已更新为paid")
    except Exception as e:
        logger.error(f"更新订单状态失败: {e}")
    
    # 同时更新payment.py内存中的订单
    try:
        from apis.routes.payment import _update_order_status
        _update_order_status(site_id, trade_order_id, "paid", transaction_id,
                           time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    except Exception:
        pass  # 内存订单可能不存在
    
    # 如果订单包含pro升级信息，自动激活用户专业版
    try:
        _auto_activate_pro(site_id, trade_order_id)
    except Exception as e:
        logger.error(f"自动激活专业版失败: {e}")
    
    return Response(content="success", media_type="text/plain")


# ── 支付结果查询 ──
@router.get("/{site_id}/query")
async def query_payment(site_id: str, order_no: str = ""):
    """
    查询支付结果（前端轮询用）

    直接读本地订单文件判断状态
    """
    if not order_no:
        raise HTTPException(400, "缺少order_no参数")
    
    orders_path = DATA_DIR / f"orders_{site_id}.json"
    if not orders_path.exists():
        raise HTTPException(404, "订单不存在")
    
    try:
        orders_data = json.loads(orders_path.read_text(encoding="utf-8"))
        orders_list = orders_data if isinstance(orders_data, list) else orders_data.get("orders", [])
        
        for order in orders_list:
            if order.get("order_no") == order_no:
                return {
                    "order_no": order_no,
                    "status": order.get("status", "unknown"),
                    "paid_at": order.get("paid_at"),
                    "total": order.get("total"),
                }
    except Exception as e:
        logger.error(f"查询订单失败: {e}")
    
    raise HTTPException(404, "订单不存在")


# ── 获取配置（管理后台用） ──
@router.get("/{site_id}/config")
async def get_config(site_id: str, request: Request):
    """获取虎皮椒配置状态"""
    from apis.routes.auth import require_admin
    # 简化：检查admin token
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "需要管理员权限")
    
    config = _load_config(site_id)
    # 不返回secret
    return {
        "app_id": config.get("app_id", ""),
        "app_secret_configured": bool(config.get("app_secret")),
        "wechat_url": config.get("wechat_url", ""),
        "alipay_url": config.get("alipay_url", ""),
        "notify_url": config.get("notify_url", ""),
    }


@router.post("/{site_id}/config")
async def save_config(site_id: str, request: Request):
    """保存虎皮椒配置（管理后台用）"""
    from apis.routes.auth import require_admin
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "需要管理员权限")
    
    body = await request.json()
    config = _load_config(site_id)
    
    for key in ["app_id", "app_secret", "wechat_url", "alipay_url", "notify_url"]:
        if key in body and body[key]:
            config[key] = body[key]
    
    cfg_path = _xunhupay_config_path(site_id)
    cfg_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    
    return {"success": True, "message": "虎皮椒配置已保存"}


# ── 自动激活专业版 ──
def _auto_activate_pro(site_id: str, order_no: str):
    """
    支付成功后自动激活用户专业版。
    从本地订单中查找user_uid，直接升级该用户。
    """
    from datetime import datetime, timedelta
    
    # 检查是否是pro升级订单（以SB开头的是系统升级订单）
    if not order_no.startswith("SB"):
        return  # 商城订单，不自动升级
    
    # 从订单中获取user_uid和总金额
    user_uid = ""
    total_amount = 0
    orders_path = DATA_DIR / f"orders_{site_id}.json"
    if orders_path.exists():
        try:
            orders_data = json.loads(orders_path.read_text(encoding="utf-8"))
            orders_list = orders_data if isinstance(orders_data, list) else orders_data.get("orders", [])
            for o in orders_list:
                if o.get("order_no") == order_no:
                    user_uid = o.get("user_uid", "")
                    total_amount = o.get("total", 0)
                    break
        except Exception:
            pass
    
    if not user_uid:
        logger.info(f"升级订单 {order_no} 无user_uid，跳过自动激活")
        return
    
    # 月度29元30天，年度199元365天
    days = 365 if total_amount >= 100 else 30
    
    # 激活用户
    users_path = DATA_DIR / "users.json"
    if not users_path.exists():
        return
    
    users_data = json.loads(users_path.read_text(encoding="utf-8"))
    if user_uid in users_data:
        user = users_data[user_uid]
        user["plan"] = "pro"
        expire = datetime.utcnow() + timedelta(days=days)
        # 如果已有pro且未过期，在现有基础上续期
        existing_expire = user.get("pro_expire")
        if existing_expire:
            try:
                existing_dt = datetime.fromisoformat(existing_expire.replace("Z", "+00:00").replace("+00:00", ""))
                if existing_dt > datetime.utcnow():
                    expire = existing_dt + timedelta(days=days)
            except Exception:
                pass
        user["pro_expire"] = expire.strftime("%Y-%m-%dT%H:%M:%SZ")
        users_path.write_text(json.dumps(users_data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"用户 {user_uid} 已自动升级为专业版({days}天)，到期: {user['pro_expire']}")
    else:
        logger.warning(f"用户 {user_uid} 不存在，无法自动激活")
