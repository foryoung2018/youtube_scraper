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

## 命令

### 搜索视频

```bash
python main.py search "python tutorial" -n 5
```

| 参数 | 说明 |
| --- | --- |
| `query` | 搜索关键词 |
| `-n, --max-results` | 最大结果数（默认 5） |

### 搜索频道视频

通过频道名或 URL 列出该频道最近的视频：

```bash
python main.py channel "@GoogleDevelopers" -n 10
python main.py channel "drbergchinese"
python main.py channel "https://www.youtube.com/@xxx/videos" -n 3
```

> 支持频道名（自动搜索定位）、@handle、完整频道 URL。

### 查看视频元数据

```bash
python main.py info "https://www.youtube.com/watch?v=NWwHEp4ReYk"
```

输出 JSON 格式，包含标题、时长、播放量、点赞数、上传日期、标签等信息。

### 下载视频

```bash
python main.py download "https://www.youtube.com/watch?v=NWwHEp4ReYk"
python main.py download "URL" -o "./my_videos"
```

| 参数 | 说明 |
| --- | --- |
| `url` | 视频链接 |
| `-a, --audio` | 仅下载音频，转为 mp3 |
| `-o, --output` | 输出目录（默认 ./downloads） |

### 列出播放列表

```bash
python main.py playlist "https://www.youtube.com/playlist?list=..."
```

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `YT_OUTPUT_DIR` | `./downloads` | 下载输出目录 |
| `YT_MAX_DOWNLOADS` | `5` | 搜索/频道默认最大结果数 |
| `YT_TIMEOUT` | `30` | 请求超时（秒） |

## 典型用法

```bash
# 1. 先搜索某博主频道
python main.py channel "@drbergchinese" -n 5

# 2. 下载感兴趣的某个视频
python main.py download "https://www.youtube.com/watch?v=xxx" -o "./drbergchinese"

# 3. 只下音频
python main.py download -a "https://www.youtube.com/watch?v=xxx"
```
