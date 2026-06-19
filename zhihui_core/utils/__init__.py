"""
core.utils.jwt_helper — 智谱AI JWT签名工具
智谱API key格式: {id}.{secret}，不能直接作Bearer token，需HMAC-SHA256签发JWT
"""
import time, jwt, os

def generate_token(api_key: str = None, exp_seconds: int = 3600) -> str:
    """从智谱API key生成JWT token"""
    key = api_key or os.environ.get("ZHIPUAI_API_KEY", "")
    if not key or "." not in key:
        # 不是{id}.{secret}格式，原样返回（兼容直接token）
        return key
    
    api_id, api_secret = key.split(".", 1)
    payload = {
        "api_key": api_id,
        "exp": int(time.time()) + exp_seconds,
        "timestamp": int(time.time()),
    }
    return jwt.encode(payload, api_secret, algorithm="HS256", headers={"alg": "HS256", "sign_type": "SIGN"})
