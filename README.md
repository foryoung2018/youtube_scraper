# YouTube Scraper

基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 的 YouTube 视频爬取工具。

## 安装

```bash
pip install -r requirements.txt
```

可选：安装 ffmpeg 以获得更好的下载质量

```bash
# Windows (scoop)
scoop install ffmpeg
# macOS
brew install ffmpeg
# Linux
sudo apt install ffmpeg
```

## 监听博主配置

在项目根目录创建 `author` 文件，每行一个频道 @handle（支持 `#` 注释）：

```
@drbergchinese
@dlw2023
# @someotherchannel
```

## 命令

### 浏览监听博主最新视频

```bash
python main.py list
python main.py list -n 3               # 每个频道显示 3 条
python main.py list -n 5 -f my_authors  # 自定义 author 文件
python main.py list -q                  # 快速模式（不获取播放量和日期）
python main.py list -v                  # 详细过程输出
```

输出示例：

```
@dlw2023:
  [VIDEO]   我反对这门亲事！...  |  59,894 views  |  20260522  |  https://www.youtube.com/watch?v=xxx
  [SHORT]   迪拜迪拜焉能不败...  |  42,240 views  |  20260321  |  https://www.youtube.com/shorts/xxx
  [MEMBERS] 会员专属视频...      |  9,999 views  |  20260520  |  https://www.youtube.com/watch?v=xxx
```

| 标签 | 含义 |
| --- | --- |
| `[VIDEO]` | 普通视频 |
| `[SHORT]` | Shorts 短视频 |
| `[MEMBERS]` | 频道会员专属 |

| 参数 | 说明 |
| --- | --- |
| `-n, --max-results` | 每个频道最多显示几条（默认 5） |
| `-f, --file` | author 文件路径（默认 `./author`） |
| `-q, --quick` | 快速模式，不获取播放量/日期/会员状态 |
| `-v, --verbose` | 显示每一步的抓取过程 |

### 搜索频道视频

通过频道名或 URL 列出该频道最近的视频：

```bash
python main.py channel "@GoogleDevelopers" -n 10
python main.py channel "@drbergchinese"
python main.py channel "@drbergchinese" -d   # 详细模式（含播放量和日期）
python main.py channel "https://www.youtube.com/@xxx/videos" -n 3
```

| 参数 | 说明 |
| --- | --- |
| `channel` | 频道 @handle、名称或完整 URL |
| `-n, --max-results` | 最大结果数（默认 5） |
| `-d, --detail` | 显示完整元数据（播放量、日期），较慢 |

### 搜索视频

```bash
python main.py search "python tutorial" -n 5
```

| 参数 | 说明 |
| --- | --- |
| `query` | 搜索关键词 |
| `-n, --max-results` | 最大结果数（默认 5） |

### 查看视频元数据

```bash
python main.py info "https://www.youtube.com/watch?v=NWwHEp4ReYk"
```

输出 JSON 格式，包含标题、时长、播放量、点赞数、上传日期、标签等信息。

### 下载视频

```bash
python main.py download "https://www.youtube.com/watch?v=NWwHEp4ReYk"
python main.py download "URL" -o "./my_videos"
python main.py download -a "URL"          # 仅下载音频，转为 mp3
```

| 参数 | 说明 |
| --- | --- |
| `url` | 视频链接 |
| `-a, --audio` | 仅下载音频，转为 mp3 |
| `-o, --output` | 输出目录（默认 ./downloads） |

### 下载最高画质

```bash
python main.py best "https://www.youtube.com/watch?v=xxx"
python main.py best "URL" -o "./my_videos"
```

分别下载最高画质视频流和最高音质音频流，**不合并**为两个独立文件。

| 参数 | 说明 |
| --- | --- |
| `url` | 视频链接 |
| `-o, --output` | 输出目录（默认 ./downloads） |

### 列出播放列表

```bash
python main.py playlist "https://www.youtube.com/playlist?list=..."
```

### 智能发现博主

用自然语言描述你想找的博主类型，通过 YouTube 搜索 + 大模型分析推荐匹配的频道：

```bash
# 智能搜索（需先配置大模型 API Key，见环境变量）
python main.py discover "医疗健康科普 中文 医生 疾病预防" -n 5
python main.py discover "财经投资 股市分析 中文" -n 5
python main.py discover "中文科技类博主，关注AI和编程" -n 10

# 把推荐的频道加入监听列表
python main.py discover "医疗科普" -n 5 -a 1 3
```

**提示词建议** — 描述越具体结果越精准：
```
"类型 语言 关键词1 关键词2..."

好的: "中文科技博主 AI大模型 编程"  "医疗科普 中医 疾病预防 养生"
差的: "找博主"  "好玩"
```

| 参数 | 说明 |
| --- | --- |
| `query` | 用自然语言描述你想找的博主类型 |
| `-n, --max-results` | 最多推荐几条（默认 10） |
| `-a, --add` | 将推荐的频道加入 author 文件（如 `-a 1 3` 添加第 1、3 个） |
| `-f, --file` | author 文件路径（默认 `./author`） |

> **无需 API Key 也能用**，会展示频道名、订阅数、简介并按订阅数排序。
> **配置大模型后**，获得 AI 评分（⭐）和中文推荐理由。

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `YT_OUTPUT_DIR` | `./downloads` | 下载输出目录 |
| `YT_MAX_DOWNLOADS` | `5` | 搜索/频道默认最大结果数 |
| `YT_TIMEOUT` | `30` | 请求超时（秒） |
| `YT_DISCOVER_RESULTS` | `10` | discover 默认推荐数 |
| `OPENAI_API_KEY` | — | 大模型 API Key（支持 OpenAI / DeepSeek 等） |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | API 地址（DeepSeek: `https://api.deepseek.com/v1`） |
| `OPENAI_MODEL` | `gpt-4o-mini` | 模型名（DeepSeek: `deepseek-chat`） |

### 配置示例（PowerShell）

```powershell
# DeepSeek
$env:OPENAI_API_KEY = "sk-xxx"
$env:OPENAI_BASE_URL = "https://api.deepseek.com/v1"
$env:OPENAI_MODEL = "deepseek-chat"

# OpenAI
$env:OPENAI_API_KEY = "sk-xxx"
# BASE_URL 和 MODEL 用默认值即可
```

## 典型用法

```bash
# 1. 智能发现新博主（需配置 OPENAI_API_KEY）
python main.py discover "中文AI科技博主" -n 10

# 2. 将推荐的博主加入监听列表
python main.py discover "医疗科普 中文" -n 5 -a 1 2

# 3. 浏览所有监听博主的最新内容
python main.py list -n 5 -v

# 4. 搜索某博主频道
python main.py channel "@drbergchinese" -n 5 -d

# 5. 下载感兴趣的某个视频
python main.py download "https://www.youtube.com/watch?v=xxx" -o "./drbergchinese"

# 6. 最高画质下载（视频和音频分开）
python main.py best "https://www.youtube.com/watch?v=xxx"

# 7. 只下音频
python main.py download -a "https://www.youtube.com/watch?v=xxx"
```
