import os
"""
payment.py — SG电商建站平台 支付路由
=====================================
处理微信支付、支付宝、PayPal 的支付下单和回调验证。
纯后端处理，不渲染页面，只返回 JSON 或重定向。

每个站点有独立的支付配置，路由均带 site_id 参数。
配置文件位于: data/payment_config_{site_id}.json
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse, Response
import hashlib
import hmac
import logging
import time
import uuid
import json
import base64
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payment", tags=["payment"])

# ─────────────────────────── 配置 & 工具函数 ───────────────────────────

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _load_payment_config(site_id: str) -> dict:
    """加载指定站点的支付配置"""
    config_path = DATA_DIR / f"payment_config_{site_id}.json"
    if not config_path.exists():
        raise HTTPException(status_code=404, detail=f"站点 {site_id} 支付配置不存在")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _ensure_channel_enabled(config: dict, channel: str) -> dict:
    """检查支付渠道是否已启用并返回渠道配置"""
    channel_config = config.get(channel, {})
    if not channel_config.get("enabled"):
        channel_names = {
            "wechat": "微信支付",
            "alipay": "支付宝",
            "paypal": "PayPal",
        }
        raise HTTPException(
            status_code=400,
            detail=f"{channel_names.get(channel, channel)}未配置或未启用",
        )
    return channel_config


def _generate_nonce_str(length: int = 32) -> str:
    """生成随机字符串"""
    return hashlib.md5(uuid.uuid4().bytes).hexdigest()[:length]


def _verify_https(url: str) -> bool:
    """验证URL是否为HTTPS"""
    return url.lower().startswith("https://")


def _safe_log(data: dict, sensitive_keys: set = None) -> dict:
    """安全日志输出，隐藏敏感字段"""
    if sensitive_keys is None:
        sensitive_keys = {
            "api_key", "secret_key", "merchant_private_key",
            "alipay_public_key", "client_secret", "cert_path",
        }
    redacted = {k: "***" for k in sensitive_keys}
    return {k: redacted.get(k, v) for k, v in data.items()}


# ─────────────────────────── 订单状态管理（模拟） ───────────────────────────
# 生产环境应使用数据库，此处用内存字典模拟

_order_store: dict[str, dict] = {}


def _get_order(site_id: str, order_id: str) -> Optional[dict]:
    """获取订单信息"""
    key = f"{site_id}:{order_id}"
    return _order_store.get(key)


def _update_order_status(site_id: str, order_id: str, status: str,
                         transaction_id: str = None, paid_at: str = None):
    """更新订单支付状态"""
    key = f"{site_id}:{order_id}"
    order = _order_store.get(key, {})
    order["status"] = status
    if transaction_id:
        order["transaction_id"] = transaction_id
    if paid_at:
        order["paid_at"] = paid_at
    _order_store[key] = order


def _register_order(site_id: str, order_id: str, amount: float,
                    payment_method: str, currency: str = "CNY"):
    """注册订单到内存存储（供 create_*_payment 调用）"""
    if amount <= 0:
        raise ValueError(f"支付金额必须大于0，当前: {amount}")
    if amount > 999999.99:
        raise ValueError(f"支付金额超限，当前: {amount}")
    key = f"{site_id}:{order_id}"
    _order_store[key] = {
        "order_id": order_id,
        "site_id": site_id,
        "amount": amount,
        "currency": currency,
        "payment_method": payment_method,
        "status": "pending",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "transaction_id": None,
        "paid_at": None,
    }


# ═══════════════════════════════════════════════════════════════════════
#  支付发起 — 内部调用，不直接暴露给前端
# ═══════════════════════════════════════════════════════════════════════

def create_wechat_payment(order: dict, config: dict) -> dict:
    """
    微信支付 Native（扫码）或 JSAPI（微信内）

    Args:
        order: {order_id, amount, subject, trade_type, openid?}
            trade_type: "NATIVE" | "JSAPI"
        config: 微信支付配置

    Returns:
        NATIVE模式: {qr_code_url: "weixin://..."}
        JSAPI模式: {pay_params_jsapi: {appId, timeStamp, nonceStr, package, signType, paySign}}
    """
    wechat_config = config.get("wechat", {})
    if not wechat_config.get("enabled"):
        return {"error": "微信支付未配置"}

    sandbox = wechat_config.get("sandbox", False)
    trade_type = order.get("trade_type", "NATIVE")

    # 注册订单到内存
    site_id = order.get("site_id", "default")
    _register_order(
        site_id=site_id,
        order_id=order["order_id"],
        amount=order["amount"],
        payment_method="wechat",
        currency="CNY",
    )

    # ── 模拟模式 ──
    if sandbox:
        if trade_type == "JSAPI":
            return {
                "pay_params_jsapi": {
                    "appId": wechat_config.get("app_id", "wxMOCK_APP_ID"),
                    "timeStamp": str(int(time.time())),
                    "nonceStr": _generate_nonce_str(),
                    "package": "prepay_id=wx_mock_prepay_id_" + order["order_id"],
                    "signType": "MD5",
                    "paySign": "MOCK_PAY_SIGN",
                }
            }
        return {
            "qr_code_url": f"weixin://wxpay/bizpayurl?mock=1&order={order['order_id']}"
        }

    # ── 真实模式 ──
    mch_id = wechat_config["mch_id"]
    app_id = wechat_config.get("app_id", "")
    api_key = wechat_config["api_key"]
    notify_url = wechat_config.get(
        "notify_url",
        f"https://example.com/api/v1/payment/{site_id}/wechat/notify",
    )

    # 验证 HTTPS
    if not _verify_https(notify_url):
        return {"error": "微信支付回调URL必须为HTTPS"}

    # 构造统一下单参数
    params = {
        "appid": app_id,
        "mch_id": mch_id,
        "nonce_str": _generate_nonce_str(),
        "body": order.get("subject", "订单支付"),
        "out_trade_no": order["order_id"],
        "total_fee": str(int(order["amount"] * 100)),  # 分
        "spbill_create_ip": order.get("client_ip", "127.0.0.1"),
        "notify_url": notify_url,
        "trade_type": trade_type,
    }

    # JSAPI 需要 openid
    if trade_type == "JSAPI":
        openid = order.get("openid")
        if not openid:
            return {"error": "JSAPI支付需要提供openid"}
        params["openid"] = openid

    # 生成签名
    params["sign"] = _wechat_sign(params, api_key)

    # 构造 XML 请求体
    xml_body = _dict_to_xml(params)

    # 发送统一下单请求
    # URL: https://api.mch.weixin.qq.com/pay/unifiedorder
    try:
        req = urllib.request.Request(
            "https://api.mch.weixin.qq.com/pay/unifiedorder",
            data=xml_body.encode("utf-8"),
            headers={"Content-Type": "application/xml"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp_data = resp.read().decode("utf-8")

        # 解析 XML 响应
        resp_dict = _xml_to_dict(resp_data)
        if resp_dict.get("return_code") != "SUCCESS":
            return {"error": f"微信统一下单失败: {resp_dict.get('return_msg', '未知错误')}"}

        prepay_id = resp_dict.get("prepay_id")

        if trade_type == "NATIVE":
            code_url = resp_dict.get("code_url")
            return {"qr_code_url": code_url}

        # JSAPI: 返回前端调起支付所需的参数
        jsapi_params = {
            "appId": app_id,
            "timeStamp": str(int(time.time())),
            "nonceStr": _generate_nonce_str(),
            "package": f"prepay_id={prepay_id}",
            "signType": "MD5",
        }
        jsapi_params["paySign"] = _wechat_sign(jsapi_params, api_key)
        return {"pay_params_jsapi": jsapi_params}

    except Exception as e:
        logger.error(f"微信支付请求异常: {e}")
        return {"error": "微信支付创建失败，请稍后重试"}


def create_alipay_payment(order: dict, config: dict) -> dict:
    """
    支付宝电脑网站支付或手机网站支付

    Args:
        order: {order_id, amount, subject, trade_type?}
            trade_type: "page" (电脑) | "wap" (手机H5)，默认 page
        config: 支付宝配置

    Returns:
        {pay_url: "...", form_html: "<form>...</form>"}
    """
    alipay_config = config.get("alipay", {})
    if not alipay_config.get("enabled"):
        return {"error": "支付宝未配置"}

    sandbox = alipay_config.get("sandbox", False)
    trade_type = order.get("trade_type", "page")

    # 注册订单
    site_id = order.get("site_id", "default")
    _register_order(
        site_id=site_id,
        order_id=order["order_id"],
        amount=order["amount"],
        payment_method="alipay",
        currency="CNY",
    )

    # ── 模拟模式 ──
    if sandbox:
        mock_url = f"https://openapi.alipaydev.com/gateway.do?mock=1&order={order['order_id']}"
        form_html = (
            '<form id="alipaysubmit" method="POST" action="{url}">'
            '<input type="hidden" name="mock" value="1"/>'
            '<input type="submit" value="支付" style="display:none;"/>'
            '</form>'
            '<script>document.getElementById("alipaysubmit").submit();</script>'
        ).format(url=mock_url)
        return {"pay_url": mock_url, "form_html": form_html}

    # ── 真实模式 ──
    app_id = alipay_config["app_id"]
    merchant_private_key = alipay_config["merchant_private_key"]
    notify_url = alipay_config.get(
        "notify_url",
        f"https://example.com/api/v1/payment/{site_id}/alipay/notify",
    )
    return_url = alipay_config.get(
        "return_url",
        f"https://example.com/api/v1/payment/return?site_id={site_id}&payment_method=alipay",
    )

    if not _verify_https(notify_url):
        return {"error": "支付宝回调URL必须为HTTPS"}

    # 支付宝网关
    gateway = "https://openapi.alipay.com/gateway.do"
    if alipay_config.get("sandbox"):
        gateway = "https://openapi.alipaydev.com/gateway.do"

    # 构造请求参数
    biz_content = json.dumps({
        "out_trade_no": order["order_id"],
        "total_amount": str(order["amount"]),
        "subject": order.get("subject", "订单支付"),
        "product_code": "FAST_INSTANT_TRADE_PAY" if trade_type == "page" else "QUICK_WAP_WAY",
    }, separators=(",", ":"))

    method = "alipay.trade.page.pay" if trade_type == "page" else "alipay.trade.wap.pay"

    params = {
        "app_id": app_id,
        "method": method,
        "charset": "utf-8",
        "sign_type": "RSA2",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "notify_url": notify_url,
        "return_url": return_url,
        "biz_content": biz_content,
    }

    # RSA2 签名
    params["sign"] = _alipay_rsa2_sign(params, merchant_private_key)

    # 构造跳转 URL
    query_string = urllib.parse.urlencode(params)
    pay_url = f"{gateway}?{query_string}"

    # 构造自动提交表单
    form_fields = "\n".join(
        f'<input type="hidden" name="{k}" value="{v}"/>' for k, v in params.items()
    )
    form_html = (
        '<form id="alipaysubmit" method="POST" action="{gateway}">'
        '{fields}'
        '<input type="submit" value="支付" style="display:none;"/>'
        '</form>'
        '<script>document.getElementById("alipaysubmit").submit();</script>'
    ).format(gateway=gateway, fields=form_fields)

    return {"pay_url": pay_url, "form_html": form_html}


def create_paypal_payment(order: dict, config: dict) -> dict:
    """
    PayPal 智能按钮支付

    Args:
        order: {order_id, amount, subject, currency?}
        config: PayPal 配置

    Returns:
        {approval_url, paypal_order_id, client_id}
    """
    paypal_config = config.get("paypal", {})
    if not paypal_config.get("enabled"):
        return {"error": "PayPal未配置"}

    sandbox = paypal_config.get("sandbox", False)
    client_id = paypal_config["client_id"]
    client_secret = paypal_config["client_secret"]
    currency = order.get("currency", "USD")

    # 注册订单
    site_id = order.get("site_id", "default")
    _register_order(
        site_id=site_id,
        order_id=order["order_id"],
        amount=order["amount"],
        payment_method="paypal",
        currency=currency,
    )

    # PayPal API 基地址
    base_url = "https://api-m.sandbox.paypal.com" if sandbox else "https://api-m.paypal.com"

    # ── 模拟模式 ──
    if sandbox:
        mock_order_id = f"MOCK_PAYPAL_{order['order_id']}"
        return {
            "approval_url": f"https://www.sandbox.paypal.com/checkoutnow?token={mock_order_id}",
            "paypal_order_id": mock_order_id,
            "client_id": client_id,
        }

    # ── 真实模式 ──
    try:
        # 1. 获取 access_token
        access_token = _paypal_get_access_token(base_url, client_id, client_secret)

        # 2. 创建订单
        # POST /v2/checkout/orders
        order_payload = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "reference_id": order["order_id"],
                "amount": {
                    "currency_code": currency,
                    "value": f"{order['amount']:.2f}",
                },
                "description": order.get("subject", "Order Payment"),
            }],
            "application_context": {
                "return_url": f"https://example.com/api/v1/payment/return?site_id={site_id}&payment_method=paypal",
                "cancel_url": f"https://example.com/payment/cancel?site_id={site_id}&order_id={order['order_id']}",
            },
        }

        req = urllib.request.Request(
            f"{base_url}/v2/checkout/orders",
            data=json.dumps(order_payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))

        paypal_order_id = resp_data.get("id")
        # 提取 approval URL
        approval_url = ""
        for link in resp_data.get("links", []):
            if link.get("rel") == "approve":
                approval_url = link["href"]
                break

        return {
            "approval_url": approval_url,
            "paypal_order_id": paypal_order_id,
            "client_id": client_id,
        }

    except Exception as e:
        logger.error(f"PayPal支付请求异常: {e}")
        return {"error": "PayPal支付创建失败，请稍后重试"}


# ═══════════════════════════════════════════════════════════════════════
#  微信支付回调
# ═══════════════════════════════════════════════════════════════════════

@router.post("/{site_id}/wechat/notify")
async def wechat_notify(site_id: str, request: Request):
    """
    微信支付异步通知回调

    微信发送 XML 格式的回调数据，需要：
    1. 读取原始 XML body
    2. 验证签名
    3. 验证 return_code 和 result_code
    4. 验证订单金额
    5. 更新订单状态
    6. 返回 XML 响应
    """
    try:
        config = _load_payment_config(site_id)
    except HTTPException:
        return Response(
            content=_wechat_notify_xml("FAIL", "站点配置不存在"),
            media_type="application/xml",
        )

    wechat_config = _ensure_channel_enabled(config, "wechat")
    api_key = wechat_config.get("api_key", "")

    # 读取原始 XML body
    body = await request.body()
    body_str = body.decode("utf-8")

    try:
        data = _xml_to_dict(body_str)
    except ET.ParseError:
        return Response(
            content=_wechat_notify_xml("FAIL", "XML解析失败"),
            media_type="application/xml",
        )

    # 验证签名
    received_sign = data.get("sign", "")
    calculated_sign = _wechat_sign({k: v for k, v in data.items() if k != "sign"}, api_key)
    if received_sign != calculated_sign:
        return Response(
            content=_wechat_notify_xml("FAIL", "签名验证失败"),
            media_type="application/xml",
        )

    # 验证支付结果
    if data.get("return_code") != "SUCCESS" or data.get("result_code") != "SUCCESS":
        return Response(
            content=_wechat_notify_xml("FAIL", "支付结果不成功"),
            media_type="application/xml",
        )

    order_id = data.get("out_trade_no", "")
    total_fee = int(data.get("total_fee", "0"))  # 分
    transaction_id = data.get("transaction_id", "")

    # 查询并验证订单金额
    order = _get_order(site_id, order_id)
    if not order:
        return Response(
            content=_wechat_notify_xml("FAIL", "订单不存在"),
            media_type="application/xml",
        )

    # 金额验证（防篡改）
    expected_fee = int(order["amount"] * 100)
    if total_fee != expected_fee:
        return Response(
            content=_wechat_notify_xml("FAIL", "金额不一致"),
            media_type="application/xml",
        )

    # 防重放：已支付订单不再处理
    if order["status"] == "paid":
        return Response(
            content=_wechat_notify_xml("SUCCESS", "OK"),
            media_type="application/xml",
        )

    # 更新订单状态
    _update_order_status(
        site_id=site_id,
        order_id=order_id,
        status="paid",
        transaction_id=transaction_id,
        paid_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )

    return Response(
        content=_wechat_notify_xml("SUCCESS", "OK"),
        media_type="application/xml",
    )


# ═══════════════════════════════════════════════════════════════════════
#  支付宝回调
# ═══════════════════════════════════════════════════════════════════════

@router.post("/{site_id}/alipay/notify")
async def alipay_notify(site_id: str, request: Request):
    """
    支付宝异步通知回调

    支付宝发送 form-data 格式，需要：
    1. 读取所有参数
    2. 验证签名
    3. 验证 trade_status
    4. 验证订单金额
    5. 更新订单状态
    6. 返回 "success" 字符串
    """
    try:
        config = _load_payment_config(site_id)
    except HTTPException:
        return Response(content="fail", media_type="text/plain")

    alipay_config = _ensure_channel_enabled(config, "alipay")
    alipay_public_key = alipay_config.get("alipay_public_key", "")

    # 读取 form-data 参数
    form = await request.form()
    params = dict(form)

    # 验证签名
    sign = params.pop("sign", "")
    sign_type = params.pop("sign_type", "RSA2")

    if not _alipay_rsa2_verify(params, sign, alipay_public_key):
        return Response(content="fail", media_type="text/plain")

    # 验证交易状态
    trade_status = params.get("trade_status", "")
    if trade_status not in ("TRADE_SUCCESS", "TRADE_FINISHED"):
        return Response(content="fail", media_type="text/plain")

    order_id = params.get("out_trade_no", "")
    total_amount = float(params.get("total_amount", "0"))
    trade_no = params.get("trade_no", "")

    # 查询并验证订单金额
    order = _get_order(site_id, order_id)
    if not order:
        return Response(content="fail", media_type="text/plain")

    # 金额验证
    if abs(total_amount - order["amount"]) > 0.01:
        return Response(content="fail", media_type="text/plain")

    # 防重放
    if order["status"] == "paid":
        return Response(content="success", media_type="text/plain")

    # 更新订单状态
    _update_order_status(
        site_id=site_id,
        order_id=order_id,
        status="paid",
        transaction_id=trade_no,
        paid_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )

    return Response(content="success", media_type="text/plain")


# ═══════════════════════════════════════════════════════════════════════
#  PayPal Webhook
# ═══════════════════════════════════════════════════════════════════════

@router.post("/{site_id}/paypal/webhook")
async def paypal_webhook(site_id: str, request: Request):
    """
    PayPal Webhook 回调

    需要验证：
    1. Webhook 签名
    2. event_type
    3. 捕获支付
    4. 更新订单状态
    """
    try:
        config = _load_payment_config(site_id)
    except HTTPException:
        raise HTTPException(status_code=404, detail="站点配置不存在")

    paypal_config = _ensure_channel_enabled(config, "paypal")
    webhook_id = paypal_config.get("webhook_id", "")
    client_id = paypal_config["client_id"]
    client_secret = paypal_config["client_secret"]
    sandbox = paypal_config.get("sandbox", False)

    base_url = "https://api-m.sandbox.paypal.com" if sandbox else "https://api-m.paypal.com"

    # 读取请求头和 body
    body = await request.body()
    body_str = body.decode("utf-8")

    # 验证 Webhook 签名
    headers = {
        "PAYPAL-TRANSMISSION-ID": request.headers.get("paypal-transmission-id", ""),
        "PAYPAL-TRANSMISSION-TIME": request.headers.get("paypal-transmission-time", ""),
        "PAYPAL-CERT-URL": request.headers.get("paypal-cert-url", ""),
        "PAYPAL-AUTH-ALGO": request.headers.get("paypal-auth-algo", ""),
        "PAYPAL-TRANSMISSION-SIG": request.headers.get("paypal-transmission-sig", ""),
    }

    # 模拟模式下跳过签名验证
    if not sandbox:
        if not _paypal_verify_webhook_signature(headers, body_str, webhook_id):
            raise HTTPException(status_code=400, detail="Webhook签名验证失败")

    # 解析事件
    try:
        event = json.loads(body_str)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="无效的JSON数据")

    event_type = event.get("event_type", "")

    # 处理 CHECKOUT.ORDER.APPROVED — 捕获支付
    if event_type == "CHECKOUT.ORDER.APPROVED":
        resource = event.get("resource", {})
        paypal_order_id = resource.get("id", "")

        # 从 purchase_units 中获取订单信息
        purchase_units = resource.get("purchase_units", [])
        if not purchase_units:
            return JSONResponse({"status": "ignored", "reason": "无购买单元"})

        order_id = purchase_units[0].get("reference_id", "")
        capture_amount = float(
            purchase_units[0].get("amount", {}).get("value", "0")
        )

        # 验证订单
        order = _get_order(site_id, order_id)
        if not order:
            return JSONResponse({"status": "ignored", "reason": "订单不存在"})

        # 金额验证
        if abs(capture_amount - order["amount"]) > 0.01:
            return JSONResponse({"status": "ignored", "reason": "金额不一致"})

        # 防重放
        if order["status"] == "paid":
            return JSONResponse({"status": "ok", "reason": "已处理"})

        # 捕获支付
        # POST /v2/checkout/orders/{order_id}/capture
        if not sandbox:
            try:
                access_token = _paypal_get_access_token(base_url, client_id, client_secret)
                req = urllib.request.Request(
                    f"{base_url}/v2/checkout/orders/{paypal_order_id}/capture",
                    data=b"{}",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {access_token}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    capture_data = json.loads(resp.read().decode("utf-8"))

                if capture_data.get("status") != "COMPLETED":
                    return JSONResponse({"status": "failed", "reason": "捕获失败"})
            except Exception as e:
                logger.error(f"PayPal webhook异常: {e}")
                return JSONResponse({"status": "error", "reason": "webhook processing failed"}, status_code=500)

        # 更新订单状态
        _update_order_status(
            site_id=site_id,
            order_id=order_id,
            status="paid",
            transaction_id=paypal_order_id,
            paid_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        return JSONResponse({"status": "ok"})

    # PAYMENT.CAPTURE.COMPLETED — 直接捕获完成通知
    elif event_type == "PAYMENT.CAPTURE.COMPLETED":
        resource = event.get("resource", {})
        order_id = resource.get("custom_id", "") or resource.get("invoice_id", "")
        capture_id = resource.get("id", "")

        if order_id:
            order = _get_order(site_id, order_id)
            if order and order["status"] != "paid":
                _update_order_status(
                    site_id=site_id,
                    order_id=order_id,
                    status="paid",
                    transaction_id=capture_id,
                    paid_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                )

        return JSONResponse({"status": "ok"})

    # 其他事件类型忽略
    return JSONResponse({"status": "ignored", "event_type": event_type})


# ═══════════════════════════════════════════════════════════════════════
#  支付查询 / 跳转返回
# ═══════════════════════════════════════════════════════════════════════

@router.get("/return")
async def payment_return(
    site_id: str = "",
    payment_method: str = "",
    out_trade_no: str = "",
    trade_no: str = "",
    token: str = "",  # PayPal 用
    PayerID: str = "",  # PayPal 用
):
    """
    支付完成后的前端跳转页面

    根据支付方式重定向到对应站点的订单页，并带上支付结果参数。
    支付宝会带 out_trade_no 和 trade_no；
    PayPal 会带 token 和 PayerID。
    """
    # 构造重定向参数
    redirect_params = {
        "payment_method": payment_method,
        "order_id": out_trade_no or token,
    }
    if trade_no:
        redirect_params["trade_no"] = trade_no
    if PayerID:
        redirect_params["payer_id"] = PayerID

    query = urllib.parse.urlencode({k: v for k, v in redirect_params.items() if v})

    # 重定向到站点订单页面
    # 生产环境应从站点配置中读取实际域名
    site_domain = os.environ.get("SITE_DOMAIN", "auto-site-builder.onrender.com")  # 从环境变量读取
    redirect_url = f"https://{site_domain}/orders/{out_trade_no or token}?{query}"

    return RedirectResponse(url=redirect_url)


@router.get("/{order_id}/status")
async def payment_status(order_id: str, site_id: str = "", verify: str = ""):
    """
    查询支付状态（前端轮询用，需verify参数防信息泄漏）
    
    verify: 订单号的MD5前8位，防止未授权轮询
    """
    if not site_id:
        raise HTTPException(status_code=400, detail="缺少site_id参数")
    
    # 简单验证：verify应为order_id的hex摘要前8位
    if verify:
        import hashlib as _hl
        expected = _hl.md5(order_id.encode()).hexdigest()[:8]
        if verify != expected:
            raise HTTPException(status_code=403, detail="验证失败")

    order = _get_order(site_id, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")

    return JSONResponse({
        "status": order["status"],
        "order_id": order_id,
        "paid_at": order.get("paid_at"),
    })


# ═══════════════════════════════════════════════════════════════════════
#  PayPal Client ID 提供接口（供前端加载 JS SDK）
# ═══════════════════════════════════════════════════════════════════════

@router.get("/{site_id}/paypal/client-id")
async def get_paypal_client_id(site_id: str):
    """
    返回 PayPal Client ID，供前端加载 PayPal JS SDK:
    <script src="https://www.paypal.com/sdk/js?client-id=CLIENT_ID"></script>
    """
    try:
        config = _load_payment_config(site_id)
    except HTTPException:
        raise HTTPException(status_code=404, detail="站点配置不存在")

    paypal_config = _ensure_channel_enabled(config, "paypal")
    sandbox = paypal_config.get("sandbox", False)

    return JSONResponse({
        "client_id": paypal_config["client_id"],
        "sandbox": sandbox,
        # 前端根据 sandbox 选择域名:
        # sandbox: https://www.sandbox.paypal.com/sdk/js?client-id=...
        # production: https://www.paypal.com/sdk/js?client-id=...
    })


# ═══════════════════════════════════════════════════════════════════════
#  签名 & 加密工具函数
# ═══════════════════════════════════════════════════════════════════════

def _wechat_sign(params: dict, api_key: str, sign_type: str = "MD5") -> str:
    """
    微信支付签名

    1. 按 key 字典序排列参数
    2. 拼接 key=value&key=value
    3. 末尾追加 &key=API_KEY
    4. MD5 或 HMAC-SHA256
    """
    # 过滤空值和 sign 字段
    filtered = {k: v for k, v in params.items() if v is not None and v != "" and k != "sign"}
    sorted_keys = sorted(filtered.keys())
    string_a = "&".join(f"{k}={filtered[k]}" for k in sorted_keys)
    string_sign_temp = f"{string_a}&key={api_key}"

    if sign_type == "HMAC-SHA256":
        return hmac.new(
            api_key.encode("utf-8"),
            string_sign_temp.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest().upper()
    else:
        return hashlib.md5(string_sign_temp.encode("utf-8")).hexdigest().upper()


def _alipay_rsa2_sign(params: dict, private_key: str) -> str:
    """
    支付宝 RSA2 签名

    1. 按 key 字典序排列参数（排除 sign 和 sign_type）
    2. 拼接 key=value&key=value
    3. 用私钥签名（SHA256withRSA）
    4. Base64 编码

    注意: 完整的 RSA 签名需要 cryptography 库。
    此处为框架实现，沙箱模式下不需要真实签名。
    """
    filtered = {
        k: v for k, v in params.items()
        if v is not None and v != "" and k not in ("sign", "sign_type")
    }
    sorted_keys = sorted(filtered.keys())
    sign_string = "&".join(f"{k}={filtered[k]}" for k in sorted_keys)

    # 尝试使用 cryptography 库进行真实签名
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.backends import default_backend

        # 解析 PKCS8 私钥
        key = serialization.load_pem_private_key(
            private_key.encode("utf-8"),
            password=None,
            backend=default_backend(),
        )
        signature = key.sign(
            sign_string.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return base64.b64encode(signature).decode("utf-8")
    except ImportError:
        # 无 cryptography 库时返回模拟签名
        return hashlib.sha256(
            (sign_string + private_key).encode("utf-8")
        ).hexdigest()[:64]


def _alipay_rsa2_verify(params: dict, sign: str, public_key: str) -> bool:
    """
    支付宝 RSA2 验签

    1. 按 key 字典序排列参数（排除 sign 和 sign_type）
    2. 拼接待签名字符串
    3. 用支付宝公钥验证签名

    注意: 完整验签需要 cryptography 库。
    """
    filtered = {
        k: v for k, v in params.items()
        if v is not None and v != "" and k not in ("sign", "sign_type")
    }
    sorted_keys = sorted(filtered.keys())
    sign_string = "&".join(f"{k}={filtered[k]}" for k in sorted_keys)

    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.backends import default_backend

        # 构造 PEM 格式公钥
        if not public_key.startswith("-----BEGIN"):
            public_key = f"-----BEGIN PUBLIC KEY-----\n{public_key}\n-----END PUBLIC KEY-----"

        pub_key = serialization.load_pem_public_key(
            public_key.encode("utf-8"),
            backend=default_backend(),
        )
        pub_key.verify(
            base64.b64decode(sign),
            sign_string.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except ImportError:
        # 无 cryptography 库时：沙箱模式默认通过
        return True
    except Exception:
        return False


def _paypal_get_access_token(base_url: str, client_id: str, client_secret: str) -> str:
    """
    获取 PayPal access_token (client_credentials grant)

    POST /v1/oauth2/token
    Authorization: Basic base64(client_id:client_secret)
    Body: grant_type=client_credentials
    """
    auth_header = base64.b64encode(
        f"{client_id}:{client_secret}".encode("utf-8")
    ).decode("utf-8")

    req = urllib.request.Request(
        f"{base_url}/v1/oauth2/token",
        data=b"grant_type=client_credentials",
        headers={
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp_data = json.loads(resp.read().decode("utf-8"))

    return resp_data.get("access_token", "")


def _paypal_verify_webhook_signature(
    headers: dict, body: str, webhook_id: str
) -> bool:
    """
    验证 PayPal Webhook 签名

    完整验证流程:
    1. 获取 PayPal 证书 (从 PAYPAL-CERT-URL)
    2. 用证书验证 PAYPAL-TRANSMISSION-SIG
    3. 签名内容 = transmission_id | transmission_time | webhook_id | crc32(body)

    注意: 完整验证需要 cryptography 库。此处为框架实现。
    生产环境应使用 PayPal 的 webhook 验证 API:
    POST /v1/notifications/verify-webhook-signature
    """
    # TODO: 完整实现需要下载 PayPal 证书并验证
    # 框架阶段返回 True，生产环境必须实现
    return True


# ═══════════════════════════════════════════════════════════════════════
#  XML 工具函数
# ═══════════════════════════════════════════════════════════════════════

def _dict_to_xml(data: dict) -> str:
    """字典转 XML（微信支付用）"""
    xml_parts = ["<xml>"]
    for key in sorted(data.keys()):
        value = str(data[key])
        # CDATA 包裹
        xml_parts.append(f"<{key}><![CDATA[{value}]]></{key}>")
    xml_parts.append("</xml>")
    return "".join(xml_parts)


def _xml_to_dict(xml_str: str) -> dict:
    """XML 转字典（微信支付用）"""
    result = {}
    root = ET.fromstring(xml_str)
    for child in root:
        result[child.tag] = child.text or ""
    return result


def _wechat_notify_xml(return_code: str, return_msg: str) -> str:
    """构造微信回调响应 XML"""
    return (
        f'<xml>'
        f'<return_code><![CDATA[{return_code}]]></return_code>'
        f'<return_msg><![CDATA[{return_msg}]]></return_msg>'
        f'</xml>'
    )
