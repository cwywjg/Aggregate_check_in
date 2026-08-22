# 常见踩坑与故障排查 FAQ (Frequently Asked Questions)

> 本文档汇总了在开发、测试、多平台编译（Uni-App / Android / iOS / H5）及服务器生产部署（Linux / Docker / Nginx）过程中最常见的 20+ 个核心问题与排查解决方案。

---

## 目录
- [一、 鉴权、Token 与签名常见问题](#一-鉴权token-与签名常见问题)
  - [Q1: 学习通短信验证码提示“签名校验失败 / 参数非法”？](#q1-学习通短信验证码提示签名校验失败--参数非法)
  - [Q2: 微助教扫码提示 403 Forbidden 或“API Key 无效”？](#q2-微助教扫码提示-403-forbidden-或api-key-无效)
  - [Q3: 微助教提示“账号登录已过期，需重新扫码”？](#q3-微助教提示账号登录已过期需重新扫码)
  - [Q4: 雨课堂提示 sessionid 失效或 401 Unauthorized？](#q4-雨课堂提示-sessionid-失效或-401-unauthorized)
- [二、 部署、网络与端口问题](#二-部署网络与端口问题)
  - [Q5: 启动服务提示 `Address already in use` 端口冲突？](#q5-启动服务提示-address-already-in-use-端口冲突)
  - [Q6: 客户端连接服务器提示“网络连接失败 / 无法访问”？](#q6-客户端连接服务器提示网络连接失败--无法访问)
  - [Q7: 前端 H5 模式或跨域请求报 CORS 拦截错误？](#q7-前端-h5-模式或跨域请求报-cors-拦截错误)
  - [Q8: 配置 HTTPS 后 WebSocket (WSS) 无法连接或报 Mixed Content？](#q8-配置-https-后-websocket-wss-无法连接或报-mixed-content)
- [三、 协议打卡与业务逻辑问题](#三-协议打卡与业务逻辑问题)
  - [Q9: 学习通提示“二维码已失效”，如何使用精准打捞功能？](#q9-学习通提示二维码已失效如何使用精准打捞功能)
  - [Q10: 微助教 GPS 签到如何避免多个账号在同一个坐标被系统风控？](#q10-微助教-gps-签到如何避免多个账号在同一个坐标被系统风控)
  - [Q11: 微助教答题提交选择题为什么必须传字典对象而非整数数组？](#q11-微助教答题提交选择题为什么必须传字典对象而非整数数组)
  - [Q12: 雨课堂 AI 解题出现超时或未返回标准 JSON？](#q12-雨课堂-ai-解题出现超时或未返回标准-json)
- [四、 Uni-App 打包与移动端配置问题](#四-uni-app-打包与移动端配置问题)
  - [Q13: Android 打包后扫码页面黑屏或无法打开摄像头？](#q13-android-打包后扫码页面黑屏或无法打开摄像头)
  - [Q14: H5 或微信小程序端编译提示 `uni.scanCode` 不支持？](#q14-h5-或微信小程序端编译提示-uniscancode-不支持)
  - [Q15: 真机运行时提示 `http://` 无法访问明文网络？](#q15-真机运行时提示-http-无法访问明文网络)

---

## 一、 鉴权、Token 与签名常见问题

### Q1: 学习通短信验证码提示“签名校验失败 / 参数非法”？
* **原因分析**：
  1. 签名计算的时间戳（`time`）使用了秒级（10位）而非毫秒级（13位）时间戳。
  2. 签名 Salt 盐被修改或拼接顺序错误。
* **解决方案**：
  确保签名逻辑严格遵循：
  ```python
  import time, hashlib
  timestamp = int(time.time() * 1000) # 13位毫秒
  raw = f"{phone}jsDyctOCnay7uotq{timestamp}"
  enc = hashlib.md5(raw.encode('utf-8')).hexdigest().lower()
  ```

---

### Q2: 微助教扫码提示 403 Forbidden 或“API Key 无效”？
* **原因分析**：
  前端 App 发起请求时携带的 `X-API-Key` 与后端服务器环境变量 `API_KEY` 不一致。
* **解决方案**：
  1. 检查后端 `server/.env` 或 Supervisor 配置中的 `API_KEY`：
     ```bash
     grep "API_KEY" /home/ubuntu/projects/微助教签到/server/.env
     ```
  2. 在 App 设置页的“服务器地址与 API Key”中填入完全相同的密钥并重新连接。

---

### Q3: 微助教提示“账号登录已过期，需重新扫码”？
* **原因分析**：
  微信官方限制了底层凭证的最大存活期（约 30 天未通信将强制重登），或者三层主动保活引擎被暂停。
* **解决方案**：
  1. 访问 Web 管理控制台（`http://<IP>:17521/070419`）。
  2. 点击“添加新账号 / 重新扫码”，微信扫码授权后系统自动入库并恢复存活状态。
  3. 确认后端后台保活引擎正在持续运行：
     ```bash
     curl -s http://127.0.0.1:17521/health | jq .keepalive
     ```

---

### Q4: 雨课堂提示 sessionid 失效或 401 Unauthorized？
* **原因分析**：
  雨课堂账号在其他设备上重复扫码登录或原 Cookie 超过 30 天有效期。
* **解决方案**：
  1. 在手机上重新登录雨课堂微信小程序或网页端，在抓包或控制台中获取最新 `sessionid` 与 `sid`。
  2. 打开 App“账号管理”，点击编辑账号，粘贴最新 Cookie 保存即可。

---

## 二、 部署、网络与端口问题

### Q5: 启动服务提示 `Address already in use` 端口冲突？
* **原因分析**：
  已有残留的 Python/Node 进程占用了 `17521`、`5000` 或 `8999` 端口。
* **解决方案**：
  ```bash
  # 查找占用端口的 PID
  sudo lsof -i :17521
  # 或使用 netstat
  sudo netstat -tulpn | grep 17521

  # 强制杀死对应进程
  sudo kill -9 <PID>
  ```

---

### Q6: 客户端连接服务器提示“网络连接失败 / 无法访问”？
* **排查步骤**：
  1. **检查服务监听地址**：必须绑定在 `0.0.0.0`，若绑定在 `127.0.0.1` 则仅允许本机内部回环访问。
  2. **检查云服务器安全组**：登录腾讯云/阿里云控制台，确认实例安全组入方向放行了对应端口（如 `17521`, `5000`, `80`, `443`）。
  3. **检查系统 UFW 防火墙**：
     ```bash
     sudo ufw status
     sudo ufw allow 17521/tcp
     sudo ufw allow 5000/tcp
     ```

---

### Q7: 前端 H5 模式或跨域请求报 CORS 拦截错误？
* **原因分析**：
  浏览器同源策略拦截了跨端口请求。
* **解决方案**：
  后端已配置 FastAPI `CORSMiddleware` 与 Flask-CORS。若经过 Nginx 转发，请确保 Nginx 没有重复添加引发冲突的 `Access-Control-Allow-Origin` 响应头。

---

### Q8: 配置 HTTPS 后 WebSocket (WSS) 无法连接或报 Mixed Content？
* **原因分析**：
  HTTPS 页面不允许直接建立不加密的 `ws://` 连接，必须升级为 `wss://`。
* **解决方案**：
  在 Nginx 配置文件中加入 WebSocket 升级指令：
  ```nginx
  proxy_http_version 1.1;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  ```

---

## 三、 协议打卡与业务逻辑问题

### Q9: 学习通提示“二维码已失效”，如何使用精准打捞功能？
* **特性说明**：
  学习通动态二维码每 5~10 秒刷新一次。当某一批账号中部分由于网络抖动错过上一轮有效时间时，系统自动将失败账号推入“打捞队列”。
* **操作步骤**：
  1. 待老师大屏幕上二维码刷新后，点击弹窗底部的 **“🎯 扫新码打捞”** 按钮。
  2. 手机扫描新码后，系统将**仅针对上一轮未成功的账号**并发注入新签名，避免已成功的账号重复打卡。

---

### Q10: 微助教 GPS 签到如何避免多个账号在同一个坐标被系统风控？
* **技术保障**：
  系统已内置 **Physics Jitter（5~10 米物理微扰动算法）**。在用户输入的基准经纬度周围，自动为每一个账号生成独立的微米级随机坐标偏移，确保既在地理围栏内部，又在物理空间上分散独立。

---

### Q11: 微助教答题提交选择题为什么必须传字典对象而非整数数组？
* **底层协议规范**：
  微助教官方前端解析选择题作答数据时，严格要求数据结构为 `[{"index": 0}, {"index": 1}]`。若提交 `[0, 1]`，服务端后端 ORM 会在解析 `rank` 字段时抛出 500 异常导致提交作答失败。

---

### Q12: 雨课堂 AI 解题出现超时或未返回标准 JSON？
* **优化建议**：
  1. 切换至速度更快的国内多模态大模型 API（如 SiliconFlow 提供的 `Qwen/Qwen2.5-VL-72B-Instruct`）。
  2. 在 `.env` 中开启极速模式：`SILICONFLOW_IMAGE_DETAIL=low`。
  3. 系统已内置多模型双通道故障转移机制（Thinking 竞速失败自动无缝回退至 Fast 通道）。

---

## 四、 Uni-App 打包与移动端配置问题

### Q13: Android 打包后扫码页面黑屏或无法打开摄像头？
* **原因分析**：
  缺少 Android 原生相机权限配置。
* **解决方案**：
  检查 `manifest.json` 中的 `app-plus` -> `distribute` -> `android` -> `permissions`，确保声明了：
  ```json
  "<uses-permission android:name=\"android.permission.CAMERA\"/>",
  "<uses-permission android:name=\"android.permission.INTERNET\"/>"
  ```

---

### Q14: H5 或微信小程序端编译提示 `uni.scanCode` 不支持？
* **原因分析**：
  PC 端普通浏览器没有原生摄像头调用 API。
* **解决方案**：
  建议将 Uni-App 项目发行打包为 **Android APK** 或 **iOS App**。若在 H5 端测试，可使用内置的手动粘贴二维码 URL / Extra 字符串打卡模式。

---

### Q15: 真机运行时提示 `http://` 无法访问明文网络？
* **原因分析**：
  Android 9.0+ 及 iOS 默认强制要求 HTTPS (Cleartext Traffic Restricted)。
* **解决方案**：
  1. 生产环境推荐配置 Nginx + Let's Encrypt SSL 域名证书。
  2. 开发调试阶段，在 `manifest.json` 的 `app-plus` 中开启明文传输允许：
     ```json
     "android": {
         "useCleartextTraffic": true
     }
     ```
