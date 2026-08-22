import os
os.environ["YYB_GO_URL"] = "http://127.0.0.1:8000"

import asyncio
import base64
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from services.yyb_service import yyb_service

async def main():
    try:
        res = await yyb_service.create_qr_session(as_base64=True)
        session_id = res.get("session_id")
        b64 = res.get("qr_base64")
        
        # 保存为图片
        if b64:
            if b64.startswith("data:image"):
                b64 = b64.split(",")[1]
            with open("wechat_login_qr.png", "wb") as f:
                f.write(base64.b64decode(b64))
            print(f"====================================")
            print(f"二维码已保存到 server/wechat_login_qr.png，请打开扫码。")
            print(f"扫码后，我将自动确认登录...")
            print(f"====================================")
            
            # 轮询
            while True:
                poll = await yyb_service.poll_qr_session(session_id)
                status = poll.get("status")
                if status == "scanned":
                    print("已扫码，请在手机上点击确认...")
                elif status == "confirmed":
                    print("手机已确认！正在保存账号...")
                    await yyb_service.confirm_qr_session(session_id)
                    print("账号登录成功！")
                    break
                elif status == "expired":
                    print("二维码已过期，请重新运行。")
                    break
                await asyncio.sleep(2)
    except Exception as e:
        print("错误:", e)

asyncio.run(main())
