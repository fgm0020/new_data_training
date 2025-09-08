# 分批上传 CSV 到 GitHub 仓库（每 3 分钟 50 个）

本工具用于将本地目录中的小 CSV 文件，按固定节奏分批上传到 GitHub 仓库中：
- 默认：每 3 分钟上传 50 个文件（可通过参数自定义）
- 每一批会以一次提交（commit）落到目标分支与目录
- 支持断点续传（本地状态文件 .upload_state.json）

上传完成后，你可以把仓库链接发给协作方（例如 Copilot Chat），对方就能按批次读取 CSV 进行处理。

## 快速开始

### 1) 准备环境

- Python 3.9+
- 一个具备 `repo` 权限的 GitHub Personal Access Token（经典 Token 或者细粒度 Token，需允许对应仓库的写权限）

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

将 GitHub Token 放到环境变量：
```bash
export GITHUB_TOKEN=ghp_xxx...   # Windows PowerShell: $env:GITHUB_TOKEN="ghp_xxx..."
```

### 2) 准备你的 CSV 小文件

- 假设你已经把原始超大 CSV 拆分成小文件，放在一个目录，如 `./chunks`
- 默认脚本只会处理扩展名为 `.csv` 的文件

### 3) 运行脚本

```bash
python upload_csv_batches.py \
  --repo fgm0020/AI_for_Science_paper_collection \
  --source-dir ./chunks \
  --dest-dir ai4s/csv_incoming \
  --branch main \
  --batch-size 50 \
  --interval-seconds 180
```

参数说明：
- `--repo`：目标仓库，格式 `owner/repo`
- `--source-dir`：本地 CSV 小文件目录
- `--dest-dir`：上传到仓库内的目标目录（会自动创建层级）
- `--branch`：目标分支（默认 `main`）
- `--batch-size`：每批文件数（默认 50）
- `--interval-seconds`：每批间隔秒数（默认 180，即 3 分钟）
- `--shuffle`：可选，随机打乱文件顺序
- `--dry-run`：可选，仅打印将要上传哪些文件，不真正上传
- `--state-file`：可选，自定义断点续传状态文件路径（默认在当前目录 `.upload_state.json`）

示例：随机顺序上传，每 3 分钟 50 个
```bash
python upload_csv_batches.py \
  --repo fgm0020/AI_for_Science_paper_collection \
  --source-dir ./chunks \
  --dest-dir ai4s/csv_incoming \
  --batch-size 50 \
  --interval-seconds 180 \
  --shuffle
```

### 4) 断点续传

- 脚本会在本地生成 `.upload_state.json`，记录已上传的文件。
- 如果中断，重新运行同样的命令即可从未上传的文件继续。

### 5) 提交信息

每个提交的 message 形如：
```
AI4S CSV batch #<N> (50 files) to ai4s/csv_incoming
```
并在消息体里列出本批次文件清单，方便在 GitHub 上回溯。

## 常见问题

- Q: GitHub Actions 能否定时每 3 分钟发一批？
  - A: GitHub Actions 的定时（cron）一般最短 5 分钟；若要 3 分钟节奏，建议用本地脚本。也可以用 Actions 启动单次作业后在作业里 `sleep 180` 循环多次，但不如本地脚本直观可控。

- Q: 会不会触发风控？
  - A: 无法保证，但使用正常的 API、合理的节奏（例如每 3 分钟 50 个），相较一次性大量并发请求，更不容易触发异常。

- Q: 目标路径里已有同名文件怎么办？
  - A: 本工具基于本地状态文件避免重复；若你手动删除了状态文件，脚本会当作新文件再推送并覆盖仓库中的同名路径。

## 完成后协作

当你上传了前几批，请把仓库链接发给我，并告诉我 CSV 的字段含义。我就能读取这些 CSV，开始整理三个顶会（例如 NeurIPS/ICLR/ICML 或 AAAI/CVPR/ICML 等）的 AI4S 论文清单。
