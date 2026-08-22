"""
文件上传代理路由
代理 OSS 签名获取和文件直传
"""
import time
import string
import random
import httpx
from fastapi import APIRouter, Depends, UploadFile, File, Form
from auth import verify_api_key
from services.teachermate import get_tm_session
from models.database import get_master_ref

router = APIRouter(prefix="/api/upload", tags=["upload"], dependencies=[Depends(verify_api_key)])


def generate_oss_key(filename: str) -> str:
    """生成 OSS 文件名: {5位随机串}-{毫秒时间戳}-{原文件名}"""
    chars = string.ascii_letters + string.digits
    rand = ''.join(random.choice(chars) for _ in range(5))
    ts = int(time.time() * 1000)
    return f"{rand}-{ts}-{filename}"


@router.post("/image")
async def upload_image(file: UploadFile = File(...), ref: str = Form(None)):
    """上传图片到 OSS"""
    return await _upload_to_oss(file, "image/png", ref)


@router.post("/audio")
async def upload_audio(file: UploadFile = File(...), ref: str = Form(None)):
    """上传录音到 OSS"""
    return await _upload_to_oss(file, "audio/mp3", ref)


async def _upload_to_oss(file: UploadFile, content_type: str, ref: str = None):
    """通用 OSS 上传"""
    # 使用指定账号或主账号的 session
    if not ref:
        ref = await get_master_ref()
    if not ref:
        return {"success": False, "message": "没有可用账号"}

    session = get_tm_session(ref)

    try:
        # 1. 获取 OSS 签名
        sig = await session.get_oss_signature(content_type)

        # 2. 生成 key
        key = generate_oss_key(file.filename or "file")

        # 3. 读取文件内容
        file_data = await file.read()

        # 4. 构造 FormData 并上传
        async with httpx.AsyncClient(timeout=30) as client:
            # OSS 要求 fields 在 file 之前
            files_payload = {
                "Signature": (None, sig["signature"]),
                "OSSAccessKeyId": (None, sig["accessKeyId"]),
                "policy": (None, sig["policy"]),
                "success_action_status": (None, "200"),
                "key": (None, key),
                "file": (file.filename, file_data, content_type),
            }

            resp = await client.post(sig["host"], files=files_payload)

            if resp.status_code == 200:
                return {
                    "success": True,
                    "fileKey": key,
                    "url": f"{sig['host']}/{key}",
                }
            else:
                return {
                    "success": False,
                    "message": f"OSS 上传失败: {resp.status_code}",
                    "detail": resp.text[:200],
                }

    except Exception as e:
        return {"success": False, "message": str(e)}
