# NVIDIA Gemma 4 31B IT 多模态 API 实测

测试时间：2026-07-26 05:27–05:33（Asia/Shanghai）

接口：

```text
https://integrate.api.nvidia.com/v1/chat/completions
```

模型：

```text
google/gemma-4-31b-it
```

测试集为 6 张本地生成的确定答案课堂截图，每张 25–31 KB：

1. 柱状图最大值，答案 B
2. 长方形面积，答案 C
3. 表格月度增量，答案 D
4. C 语言循环输出，答案 B
5. 蓝色三角形视觉计数，答案 B
6. 折线图读数，答案 C

## Thinking 开启

参数：

```json
{
  "enable_thinking": true,
  "max_tokens": 16384,
  "temperature": 1,
  "top_p": 0.95,
  "stream": false
}
```

结果：

| 题目 | 预期 | 返回 | 正确 | 总耗时 |
|---|---:|---:|---:|---:|
| 柱状图 | B | B | 是 | 23.829s |
| 几何 | C | C | 是 | 13.960s |
| 表格 | D | D | 是 | 16.280s |
| 代码 | B | B | 是 | 15.415s |
| 视觉计数 | B | B | 是 | 12.881s |
| 折线图 | C | C | 是 | 30.430s |

汇总：

```text
API 完成率：100%
回答准确率：6/6 = 100%
平均：18.799s
中位数：15.848s
P95：28.780s
最短：12.881s
最长：30.430s
```

模型每题生成约 287–1404 个 reasoning tokens，即使最终只返回一个选项，也会明显增加延迟。

## Thinking 关闭

参数：

```json
{
  "enable_thinking": false,
  "max_tokens": 256,
  "temperature": 0.1,
  "top_p": 0.95,
  "stream": false
}
```

首次批次结果：

| 题目 | 结果 | 总耗时 |
|---|---:|---:|
| 柱状图 | B，正确 | 5.436s |
| 几何 | C，正确 | 96.868s，服务端排队异常值 |
| 表格 | 连接超时 | 未完成 |
| 代码 | B，正确 | 3.932s |
| 视觉计数 | B，正确 | 4.004s |
| 折线图 | C，正确 | 3.349s |

表格题随后单独重试：

```text
答案：D，正确
耗时：4.744s
```

汇总：

```text
正常请求典型耗时：3.349–5.436s
正常请求中位数：约 4.0s
已返回答案准确率：100%
首次批次完成率：5/6
失败题重试后：成功且答案正确
```

## 结论

1. `google/gemma-4-31b-it` 对本测试集的图片 OCR、图表读取、代码和简单推理准确率为 100%。
2. 课堂答题必须关闭 thinking；开启后平均接近 19 秒。
3. NVIDIA 公共试用端点存在明显尾延迟，出现过 96.868 秒排队和一次连接超时。
4. 生产配置应保留一次 SDK 重试，并给单次请求设置合理超时。
5. 推荐配置：

```ini
AI_PROVIDER=nvidia
AI_BASE_URL=https://integrate.api.nvidia.com/v1
AI_MODELS=google/gemma-4-31b-it
AI_ENABLE_THINKING=0
AI_TEMPERATURE=0.1
AI_TOP_P=0.95
AI_MAX_TOKENS=1024
AI_MAX_RETRIES=1
NVIDIA_JSON_MODE=off
NVIDIA_INLINE_IMAGE_MAX_BYTES=174080
```

原始 JSON：

```text
tests/nvidia_benchmark_output/report_thinking.json
tests/nvidia_benchmark_output/report_fast.json
```
