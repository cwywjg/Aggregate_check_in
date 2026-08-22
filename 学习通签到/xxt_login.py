# -*- coding: utf-8 -*-
"""
超星学习通移动端协议登录与凭证提取客户端
=============================================
特性说明：
1. 零第三方库依赖：纯内置 urllib + cookiejar + 纯 Python MD5 签名计算。
2. 双鉴权模式支持：
   - 模式一：【手机号 + 短信验证码】快捷登录（含毫秒级时间戳加盐签名）
   - 模式二：【手机号 / 学号 / 账号 + 密码】标准 Passport 登录
3. 跨平台交互适配：兼容 Windows IDE / 终端标准输入，避免 getpass 阻塞挂起。
4. 全流程链路打通：Passport 鉴权 -> SSO 单点登录身份同步 -> 机构与学校绑定提取 -> 本地 Cookie 持久化。
5. 凭证复用：生成的 chaoxing_cookies.json 可直接供全并发扫码签到、活动监听使用。
"""

import os
import sys
import json
import time
import ssl
import hashlib
import urllib.request
import urllib.parse
import http.cookiejar

# ============================ 核心协议常量与接口地址 ============================
# 超星 Passport 接口端点
PASSPORT_API_HOST = "https://passport2-api.chaoxing.com"
# 超星 SSO 单点登录与身份同步端点
SSO_API_HOST = "https://sso.chaoxing.com"
# 超星移动端学习空间端点
MOBILE_LEARN_HOST = "https://mobilelearn.chaoxing.com"

# 发送短信验证码签名固定盐 (Passport Salt - 逆向自移动端 dex / lib)
CAPTCHA_SALT = "jsDyctOCnay7uotq"

# 移动端标准 User-Agent (Dalvik Android 模拟协议指纹)
APP_USER_AGENT = (
    "Dalvik/2.1.0 (Linux; U; Android 13; Pixel 4 Build/TP1A.221005.002.B2) "
    "(schild:741b9b3a452d4c8cf1404a753adb59c7) (device:Pixel 4) Language/zh_CN_#Hans "
    "com.chaoxing.mobile/ChaoXingStudy_3_7.0.0_android_phone_10989_340 "
    "(@Kalimdor)_7d39900fc23745a78f4e5d1322846acb"
)


# ============================ 客户端核心类 ============================
class XueXiTongClient:
    """学习通网络协议客户端封装"""

    def __init__(self, cookie_file="chaoxing_cookies.json"):
        self.cookie_file = cookie_file
        self.cookie_jar = http.cookiejar.CookieJar()
        
        # 创建支持忽略 SSL 证书校验的 Handler（便于在代理/抓包网络下顺畅调试）
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE
        https_handler = urllib.request.HTTPSHandler(context=ssl_ctx)
        
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar),
            https_handler
        )
        self.user_info = None

    def _request(self, url: str, data: dict = None, headers: dict = None) -> dict:
        """
        统一底层 HTTP 请求封装
        :param url: 目标 URL
        :param data: POST 字典参数 (如为 None 则发起 GET 请求)
        :param headers: 额外请求头
        :return: JSON 解析后的 dict 或错误字典
        """
        req_headers = {
            "User-Agent": APP_USER_AGENT,
            "Accept-Language": "zh_CN_#Hans",
            "Accept-Encoding": "identity",
            "Connection": "Keep-Alive",
        }
        if headers:
            req_headers.update(headers)

        req_data = None
        if data is not None:
            req_headers["Content-Type"] = "application/x-www-form-urlencoded"
            req_data = urllib.parse.urlencode(data).encode("utf-8")

        req = urllib.request.Request(url, data=req_data, headers=req_headers)
        try:
            with self.opener.open(req, timeout=15) as resp:
                resp_text = resp.read().decode("utf-8", errors="ignore")
                try:
                    return json.loads(resp_text)
                except Exception:
                    return {"raw_text": resp_text}
        except urllib.error.HTTPError as e:
            err_text = e.read().decode("utf-8", errors="ignore")
            return {"error": f"HTTP Error {e.code}", "raw_text": err_text}
        except Exception as e:
            return {"error": str(e)}

    def get_cookies_dict(self) -> dict:
        """获取当前 Session 中的所有 Cookie 键值对"""
        cookies = {}
        for cookie in self.cookie_jar:
            cookies[cookie.name] = cookie.value
        return cookies

    def save_cookies(self):
        """将 Session Cookies 和用户信息持久化保存到本地 JSON 文件"""
        data = {
            "save_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "cookies": self.get_cookies_dict(),
            "user_info": self.user_info
        }
        with open(self.cookie_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[+] 登录凭证已成功持久化至: {os.path.abspath(self.cookie_file)}")

    def send_sms_captcha(self, phone: str) -> bool:
        """
        发送短信验证码
        -------------------------------------------------------------
        协议核心签名逻辑：
        raw_sign = f"{phone}{CAPTCHA_SALT}{timestamp}"
        enc = md5(raw_sign).hexdigest()
        -------------------------------------------------------------
        :param phone: 11位手机号
        :return: 发送是否成功
        """
        timestamp = int(time.time() * 1000)
        # 计算移动端签名: MD5(手机号 + 固定盐 + 毫秒时间戳)
        raw_sign = f"{phone}{CAPTCHA_SALT}{timestamp}"
        enc = hashlib.md5(raw_sign.encode("utf-8")).hexdigest()

        url = f"{PASSPORT_API_HOST}/api/sendcaptcha"
        data = {
            "to": phone,
            "countrycode": "86",
            "time": str(timestamp),
            "enc": enc
        }

        print(f"[*] 正在向手机号 {phone} 发送短信验证码...")
        resp = self._request(url, data=data)
        if resp.get("status") is True:
            print("[+] 短信验证码发送成功！请注意查收手机短信。")
            return True
        else:
            msg = resp.get("mes") or resp.get("error") or "未知错误"
            print(f"[-] 验证码发送失败: {msg}")
            return False

    def login(self, uname: str, code: str, is_sms_login: bool = False) -> bool:
        """
        执行移动端 Passport 登录鉴权
        -------------------------------------------------------------
        请求端点: /v11/loginregister?cx_xxt_passport=json
        loginType: "2" 为短信验证码登录, "1" 为账号密码登录
        -------------------------------------------------------------
        :param uname: 手机号 / 账号 / 学号
        :param code: 短信验证码 或 登录密码
        :param is_sms_login: True 为验证码登录，False 为密码登录
        :return: 登录是否成功
        """
        url = f"{PASSPORT_API_HOST}/v11/loginregister?cx_xxt_passport=json"
        
        # 移动端 passport 登录参数
        data = {
            "uname": str(uname).strip(),
            "code": str(code).strip(),
            "loginType": "2" if is_sms_login else "1",
            "countrycode": "86",
            "roleSelect": "true"
        }

        mode_name = "短信验证码" if is_sms_login else "账号密码"
        print(f"[*] 正在提交登录验证 ({mode_name})...")
        resp = self._request(url, data=data)

        if resp.get("status") is True:
            print("[+] Passport 账号验证通过！")
            cookies = self.get_cookies_dict()
            uid = cookies.get("UID") or cookies.get("_uid")
            print(f"[+] 提取到核心用户标识 UID: {uid}")

            # 换取 SSO 完整用户信息与高校绑定状态
            sso_url = resp.get("url") or f"{SSO_API_HOST}/apis/login/userLogin4Uname.do?_from=passport"
            self._sync_sso_info(sso_url)
            self.save_cookies()
            return True
        else:
            msg = resp.get("mes") or resp.get("msg2") or resp.get("error") or "账号或密码/验证码错误"
            print(f"[-] 登录失败: {msg}")
            return False

    def _sync_sso_info(self, sso_url: str):
        """换取 SSO 用户画像、真实姓名、学号与高校机构绑定信息"""
        print("[*] 正在同步用户信息与机构绑定...")
        resp = self._request(sso_url, data={})
        msg = resp.get("msg", {})
        if isinstance(msg, dict):
            self.user_info = {
                "uid": msg.get("uid"),
                "puid": msg.get("puid"),
                "name": msg.get("name"),
                "nick": msg.get("nick"),
                "schoolname": msg.get("schoolname"),
                "uname": msg.get("uname"),
                "phone": msg.get("phone"),
                "fid": msg.get("fid"),
                "dxfid": msg.get("dxfid")
            }
            print("=" * 50)
            print("              【登录成功 - 用户档案】")
            print(f"  用户姓名: {self.user_info.get('name')}")
            print(f"  所属高校: {self.user_info.get('schoolname') or '未认证机构/个人'}")
            print(f"  学号/工号: {self.user_info.get('uname')}")
            print(f"  用户 UID: {self.user_info.get('uid')} (puid: {self.user_info.get('puid')})")
            print(f"  绑定手机: {self.user_info.get('phone')}")
            print("=" * 50)
        else:
            print(f"[!] 同步 SSO 信息响应: {resp}")


# ============================ 交互式命令行入口 ============================
def interactive_main():
    print("""
=====================================================
          超星学习通 移动端登录交互终端
=====================================================
  [1] 手机号 + 短信验证码登录
  [2] 手机号 / 账号 + 密码登录
  [0] 退出
=====================================================
""")
    client = XueXiTongClient(cookie_file="chaoxing_cookies.json")

    while True:
        choice = input("请选择登录模式 [1/2/0]: ").strip()
        if choice == "1":
            phone = input("请输入手机号: ").strip()
            if not phone:
                print("[-] 手机号不能为空！")
                continue
            if not client.send_sms_captcha(phone):
                continue
            code = input("请输入收到的 4-6 位短信验证码: ").strip()
            if not code:
                print("[-] 验证码不能为空！")
                continue
            success = client.login(uname=phone, code=code, is_sms_login=True)
            if success:
                print("\n[√] 登录流程完毕！已生成 chaoxing_cookies.json，可供后续签到业务使用。")
            break

        elif choice == "2":
            uname = input("请输入手机号 / 学号 / 账号: ").strip()
            if not uname:
                print("[-] 账号不能为空！")
                continue
            
            pwd = input("请输入密码: ").strip()
            if not pwd:
                print("[-] 密码不能为空！")
                continue
                
            success = client.login(uname=uname, code=pwd, is_sms_login=False)
            if success:
                print("\n[√] 登录流程完毕！已生成 chaoxing_cookies.json，可供后续签到业务使用。")
            break

        elif choice == "0":
            print("[*] 已退出。")
            sys.exit(0)
        else:
            print("[-] 无效输入，请输入 1、2 或 0！")

if __name__ == "__main__":
    interactive_main()
