"""
API Key 鉴权中间件
"""
from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from config import API_KEY

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """验证请求头中的 API Key"""
    if not api_key or api_key != API_KEY:
        raise HTTPException(status_code=403, detail="无效的 API Key")
    return api_key
