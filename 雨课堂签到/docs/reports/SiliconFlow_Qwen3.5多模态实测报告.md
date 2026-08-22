# SiliconFlow Qwen3.5-27B 多模态实测

## 测试结论

- API：`https://api.siliconflow.cn/v1/chat/completions`
- 模型：`Qwen/Qwen3.5-27B`
- 输入：6 张 960×540 课堂图片题，覆盖柱状图、几何、表格、C 代码、
  视觉计数和折线图。
- 推荐线上配置：`enable_thinking=false`、`image_detail=low`。
- 快速模式：6/6 请求完成，5/6 正确，平均 2.378 秒，中位数 2.372 秒，
  最慢 3.290 秒。
- 快速模式合计：3,486 prompt tokens、36 completion tokens，
  共 3,522 tokens。
- `image_detail=high`：仍为 5/6，平均 2.447 秒，没有修复代码题误判。
- thinking + 2,048 tokens：前五题全部正确，但折线题推理耗尽 2,048 tokens，
  未生成最终 JSON；平均 17.925 秒，最慢 43.670 秒。

## 误判与部署选择

快速模式唯一误判是 C 语言循环平方和，模型把正确的 `30 / B` 选成了
`32 / C`。thinking 能修复该题，但短倒计时下延迟和 token 波动过大。
所以生产默认关闭 thinking，并保留模型路由能力，后续可以把更强模型放到
`SILICONFLOW_MODELS` 首位或作为 fallback。

## 原始证据

- 快速模式：`tests/siliconflow_benchmark_output/report_low_verified.json`
- 高细节模式：`tests/siliconflow_benchmark_output/report_high.json`
- thinking 模式：`tests/siliconflow_benchmark_output/report_thinking_2048.json`
- 可重复脚本：`tests/test_siliconflow_multimodal_benchmark.py`

报告与源码均不保存 API key。
