# 🔍 雨课堂 Dart AOT 逆向分析实时线索日志 (Reverse Analysis Notes)

本文档实时记录在深挖 `blutter_out` / Dart AOT 反汇编与符号信息过程中发现的所有有价值线索、隐藏接口、数据结构细节与协议规范。

---

## 一、 已定位的关键 Dart 源码文件映射

| 模块分类 | Dart 文件路径 | 功能说明 |
| :--- | :--- | :--- |
| **网络请求核心** | `asm/rain/network/yuketang.dart` | HTTP 请求统一封装、Header 设置、API 端点配置 |
| **WS 消息控制器** | `asm/rain/websocket/ws_connector.dart` | WebSocket 连接建立、重连机制、心跳保活 |
| **WS 接收处理器** | `asm/rain/websocket/processer/receiver_processer.dart` | 学生端 WS 消息帧路由与解包 (`sendsproblem` 等) |
| **WS 操控处理器** | `asm/rain/websocket/processer/remote_control_processer.dart` | 教师/遥控端 WS 消息处理 |
| **答题实体 Bean** | `asm/rain/receiver_page/bean/new_bean/problem_answer_bean.dart` | 答题提交与响应的 JSON 序列化模型 |
| **WS 操作模型** | `asm/rain/model/wss_operation_model.dart` | WS Operation (`op`) 枚举与数据结构映射 |
| **单选题界面控制器** | `asm/rain/receiver_page/single_choice_question_page.dart` | 单选题答案组装与提交触发 |
| **多选题界面控制器** | `asm/rain/receiver_page/multiple_choice_question_page.dart` | 多选题答案组装与提交触发 |
| **填空题界面控制器** | `asm/rain/receiver_page/fill_blank_question_page.dart` | 填空题答案组装与提交触发 |
| **主观/简答题控制器** | `asm/rain/receiver_page/subjective_question_page.dart` | 简答题/图片视频组装与提交触发 |
| **投票题界面控制器** | `asm/rain/receiver_page/vote_question_page.dart` | 投票题答案组装与提交触发 |
| **课堂调度主页面** | `asm/rain/receiver_page/receiver_class_page.dart` | 课堂状态监听、签到、全局 WS 事件绑定 |

---

## 二、 逆向过程实时线索记录（持续更新）

### 1. WebSocket 事件处理全量 OpCodes (包含存疑项校验)
在 `asm/rain/websocket/processer/receiver_processer.dart` 中成功提取学生端支持的全量 WebSocket `op` 路由分支：
* **`hello`** -> `HelloOp` (握手/初始化响应)
* **`sendsproblem`** -> `WssSendsproblemOp` (题目下发/推送)
* **`sproblemshown`** -> `WssSproblemshownOp` (题目展示/显示)
* **`probleminfo`** -> `WssProbleminfoOp` (题目信息更新)
* **`unlockproblem`** -> `WssUnlockProblemOp` (✅ **确认存在！地址 0x1316dd4，非仅 Web 端，客户端在接收器中解包并触发 EventBus**)
* **`extendtime`** -> `WssExtenttimeOp` (答题时间延长)
* **`slidenav`** -> `WssSlidenavOp` (PPT 幻灯片导航)
* **`closedmask`** -> `WssCloseMaskOp` (关闭遮罩/弹层)
* **`problemremark`** -> `WssProblemrearkOp` (题目点评/备注)
* **`redpacket`** -> `WssRedpacketOp` (课堂红包下发)
* **`showfinished`** -> `MessageEventOp` (展示完成通知)
* **`remotedeprived`** -> `WssRemoteDeprivedOp` (遥控/控制权变更)
* **`launchgroup`** -> `WssReceiverGroup` (小组讨论/答题启动)
* **`newdanmu` / `turnondanmu` / `turnoffdanmu` / `danmushown`** (弹幕控制指令)

### 2. 答题 Payload (`result` 字段) 各题型序列化标准（答对 Question 2）
经对 `single_choice_question_page.dart` (addr `0xf33838`)、`multiple_choice_question_page.dart` (addr `0xefe65c`)、`subjective_question_page.dart` (addr `0xf3ee38` / `0xf3f3c4`) 的反汇编深挖，推导出 `result` 字段的官方标准 JSON 数据结构：

* **单选题 (problemType = 0)**：`result` 为选项 Key 字母字符串数组，例如 `["A"]`（由 `_SingleChoiceQuestionState::result` 拼接 String 返回）。
* **多选题 (problemType = 1)**：`result` 为多选 Key 字母字符串数组，按字母升序排序，例如 `["A", "C", "D"]`。
* **投票题 (problemType = 2)**：`result` 为选中的选项 Key 字母字符串数组，例如 `["A"]` 或 `["A", "B"]`。
* **填空题 (problemType = 3)**：`result` 为每个空的填空文本数组，例如 `["答案1", "答案2"]`（校验 `cbnz` 提示"不能为空"）。
* **简答题/主观题 (problemType = 4)**：✅ **确认标准格式为 JSON 对象！** 在 `subjective_question_page.dart` line 14236-14251 中显式对 Map 进行赋值：
  ```json
  {
    "content": "回答文本...",
    "pics": [],
    "videos": []
  }
  ```
  > ⚠️ **发现不一致线索**：云端 `ykt_ws_engine.py` 曾使用纯文本数组 `["一段文字"]`，这与客户端实际代码中的 Object 结构冲突。**需将服务端 `ykt_ws_engine.py` 统一更正为 `{content, pics, videos}` 对象结构。**

* **`problemId` 数据类型**：在 Map 组装与 `problem_answer_bean.dart` 解析中，序列化保持为 Integer 数值（或标准 Numeric 字符串），推导出建议统一下发 Number/Integer。

---


