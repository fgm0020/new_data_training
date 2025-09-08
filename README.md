# 分批把 CSV 投喂给 Copilot 问问题/做分析（每 3 分钟一批、每批最多 50 个）

本工具将本地目录中的小 CSV 文件分批整理成**提问用 Prompt**（Markdown），并按节奏投喂给 Copilot 聊天（或仅生成 Prompt 供你手动复制）。

## 两种使用方式

- 方式 A（推荐通用）：只生成每一批的 Prompt 文件（.md），你把文件内容复制到你使用的 Copilot Chat 窗口即可（VS Code/浏览器都行）。
- 方式 B（自动发送，依赖本机已安装并登录的 Copilot 命令行聊天）：脚本会把每批 Prompt 直接发给 Copilot 聊天，并把回答保存在本地。

> 提示：命令行聊天的具体参数和非交互能力可能因版本而略有差异；如果自动发送在你机器上不可用，请用方式 A。

## 快速开始

1) 准备环境（Python 3.9+，无需第三方库）
```bash
python -m venv .venv
source .venv/bin/activate   # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) 准备你的 CSV 小文件
- 把拆分好的 CSV 放到一个目录，如 `./chunks`
- 默认仅处理扩展名 `.csv`，可通过 `--pattern` 改为 `**/*.csv`

3) 仅生成 Prompt 文件（稳妥做法）
```bash
python batch_to_copilot.py \
  --source-dir ./chunks \
  --out-dir ./copilot_batches \
  --batch-size 50 \
  --interval-seconds 180 \
  --rows-per-file 3 \
  --max-prompt-bytes 60000 \
  --dry-run
```
- 执行后会在 `./copilot_batches` 下生成类似 `batch_0001_prompt.md` 的文件。
- 打开对应文件，把内容复制到 Copilot Chat，即可发起你的问题与上下文。

4) 自动把每批 Prompt 投喂给命令行里的 Copilot 聊天（可选）
```bash
python batch_to_copilot.py \
  --source-dir ./chunks \
  --out-dir ./copilot_batches \
  --batch-size 50 \
  --interval-seconds 180 \
  --rows-per-file 3 \
  --max-prompt-bytes 60000 \
  --use-cli
```
- 需要你本机已安装并登录命令行 Copilot 聊天。
- 每一批会在本地生成 `batch_XXXX_prompt.md`（提问）和 `batch_XXXX_response.md`（回答）文件。
- 如果自动发送失败，请改用上面的 `--dry-run`，把 Prompt 手动复制到 Copilot Chat。

## 常用参数

- `--source-dir`：CSV 目录
- `--pattern`：文件匹配模式（默认 `**/*.csv`）
- `--batch-size`：每批最多处理的文件数（默认 50）
- `--interval-seconds`：批次间隔秒数（默认 180，即 3 分钟）
- `--rows-per-file`：每个文件采样的行数（默认 3）
- `--max-prompt-bytes`：单次 Prompt 最大字节数上限，超过会自动降采样（默认 60000）
- `--shuffle`：随机打乱文件顺序
- `--prompt-prefix-file`：自定义“问题前缀模板”（Markdown），不指定则用内置默认前缀
- `--use-cli`：尝试自动把 Prompt 发送给命令行里的 Copilot 聊天
- `--dry-run`：仅生成 Prompt 文件，不投喂（推荐先试）
- `--state-file`：断点续传状态文件（默认 `.copilot_feed_state.json`）

## Prompt 结构说明

每批 Prompt 包含：
- 你的“问题前缀”指令（可自定义），例如：
  - 要 Copilot 输出统一字段、如何去重、如何筛选“三个顶会的 AI4S 论文”等
  - 要求回答格式（例如只输出 CSV/JSON 等）
- 对本批每个 CSV 的摘要：
  - 文件名、可能的行数（如果可快速读取）
  - 表头（列名）
  - 前 N 行样例数据
  - 所有样例均以代码块（```csv）包裹，便于 Copilot 解析

注意：为避免超出上下文限制，脚本会控制总长度；如超出，会自动把每个文件的样例行数降为 1，仍超出则只保留表头。

## 预设的问题前缀（默认）

默认前缀会引导 Copilot：
- 将本批 CSV 的信息融合，聚焦 AI4S 论文；
- 判定是否属于你指定的三个顶会（例：NeurIPS/ICLR/ICML）；
- 标准化输出并去重（同题目+作者视为重复）；
- 指定输出为 CSV，仅含你关心的列。

你可以用 `--prompt-prefix-file` 提供自己的前缀模板（Markdown）。

## 小贴士

- 初次建议开 `--dry-run`，检查生成的 Prompt 是否满足你的预期，再决定是否自动投喂。
- 如果你希望更强的压缩（比如只发表头+文件级统计），可把 `--rows-per-file` 设为 0，并开启你自己的前缀模板，引导 Copilot 根据“列名与文件名”做高层分析。