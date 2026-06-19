"""
core.utils.jwt_helper — 智谱AI JWT签名工具
智谱API key格式: {id}.{secret}，不能直接作Bearer token，需HMAC-SHA256签发JWT
"""
import time, os

def generate_token(api_key: str = None, exp_seconds: int = 3600) -> str:
    """从智谱API key生成JWT token"""
    key = api_key or os.environ.get("ZHIPUAI_API_KEY", "")
    if not key or "." not in key:
        return key
    
    try:
        import jwt as pyjwt
    except ImportError:
        # jwt不可用，尝试用hmac手动构建
        import hmac, hashlib, base64, json
        api_id, api_secret = key.split(".", 1)
        
        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256", "sign_type": "SIGN"}, separators=(',', ':')).encode()
        ).rstrip(b'=').decode()
        
        payload_data = {
            "api_key": api_id,
            "exp": int(time.time()) + exp_seconds,
            "timestamp": int(time.time()),
        }
        payload = base64.urlsafe_b64encode(
            json.dumps(payload_data, separators=(',', ':')).encode()
        ).rstrip(b'=').decode()
        
        sign_str = f"{header}.{payload}"
        sig = hmac.new(
            api_secret.encode(),
            sign_str.encode(),
            hashlib.sha256
        ).digest()
        signature = base64.urlsafe_b64encode(sig).rstrip(b'=').decode()
        
        return f"{sign_str}.{signature}"
    
    api_id, api_secret = key.split(".", 1)
    payload = {
        "api_key": api_id,
        "exp": int(time.time()) + exp_seconds,
        "timestamp": int(time.time()),
    }
    return pyjwt.encode(payload, api_secret, algorithm="HS256", headers={"alg": "HS256", "sign_type": "SIGN"})
