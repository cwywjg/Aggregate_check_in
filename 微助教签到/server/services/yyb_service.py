"""
yyb-go HTTP API 封装（持久化 httpx 客户端）
"""
import httpx
from config import YYB_GO_URL


class YYBService:
    """封装 yyb-go 的所有 HTTP API 调用"""

    def __init__(self, base_url: str = YYB_GO_URL):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=10.0),
            limits=httpx.Limits(max_keepalive_connections=50, max_connections=100)
        )

    async def close(self):
        """关闭持久化 HTTP 客户端"""
        await self._client.aclose()

    async def health(self) -> dict:
        r = await self._client.get(f"{self.base_url}/health", timeout=5)
        r.raise_for_status()
        return r.json()

    # ── 账号管理 ──

    async def get_accounts(self) -> list[dict]:
        """获取 yyb-go 中所有已保存的账号"""
        r = await self._client.get(f"{self.base_url}/accounts", timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("data", []) or []

    async def get_account_by_ref(self, ref: str) -> dict | None:
        """通过 ref 查找账号"""
        accounts = await self.get_accounts()
        for acc in accounts:
            if acc.get("openid") == ref or str(acc.get("id")) == ref:
                return acc
        return None

    async def delete_account(self, ref: str) -> dict:
        r = await self._client.delete(f"{self.base_url}/accounts", params={"ref": ref}, timeout=10)
        r.raise_for_status()
        return r.json()

    async def refresh_account(self, ref: str = None) -> dict:
        """刷新账号存活状态"""
        body = {"ref": ref} if ref else {}
        r = await self._client.post(f"{self.base_url}/accounts/refresh", json=body, timeout=15)
        r.raise_for_status()
        return r.json()

    def get_avatar_url(self, ref: str) -> str:
        """获取头像 URL（同步方法，无需 async）"""
        return f"{self.base_url}/accounts/avatar?ref={ref}"

    # ── 扫码登录 ──

    async def create_qr_session(self, as_base64: bool = True) -> dict:
        """创建扫码登录会话"""
        r = await self._client.post(
            f"{self.base_url}/qr",
            params={"as_base64": "true" if as_base64 else "false"},
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
        return data.get("data", {})

    async def poll_qr_session(self, session_id: str) -> dict:
        """轮询扫码状态"""
        r = await self._client.get(f"{self.base_url}/qr/{session_id}/poll", timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("data", {})

    async def confirm_qr_session(self, session_id: str) -> dict:
        """确认扫码并保存账号"""
        r = await self._client.post(f"{self.base_url}/qr/{session_id}/confirm", timeout=15)
        r.raise_for_status()
        data = r.json()
        return data.get("data", {})

    # ── 小程序 Code 获取 ──

    async def get_code(self, ref: str, app_id: str) -> str:
        """获取指定账号、指定小程序的 code"""
        r = await self._client.post(
            f"{self.base_url}/wxapp/getCode",
            json={"ref": ref, "app_id": app_id},
            timeout=15
        )
        r.raise_for_status()
        data = r.json()
        if data.get("code") != 0:
            raise Exception(f"获取 code 失败: {data.get('msg', '未知错误')}")
        return data["data"]["result"]["code"]


# 全局单例
yyb_service = YYBService()
