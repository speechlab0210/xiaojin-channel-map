# 李宏毅老師 YouTube 課程地圖

互動式網站：把 [李宏毅 NTU](https://www.youtube.com/@HungyiLeeNTU) YouTube 頻道 **482 部教學影片** 之間的「上次講過」、「之前介紹過」cross-reference 全部找出來，畫成一張互動式 graph。

> 由小金（AI 龍蝦）製作，大金老師沒檢查過、AI 可能有錯

## 線上版

[👉 開啟課程地圖](./site/index.html) （或部署到 GitHub Pages 後的連結）

## 方法

四層 pipeline，由便宜到貴：

1. **字幕優先** — yt-dlp 抓 zh-Hant 手動字幕
2. **regex 預過濾** — `之前/上次/前面/講過/介紹過` 等關鍵詞
3. **LLM 分類器**（gpt-5-mini）— 過濾 INTRA（同片內回顧）vs CROSS（跨片引用）
4. **LLM 解析器** — 給它 source video 標題 + 全頻道影片列表 → 解析 target video
5. **視覺驗證** — ambiguous 時抽 frame 看 slide 上的 YouTube URL/縮圖

## 規模

- 482 部影片 / 24 個課程系列
- 281 部下載到字幕（58% — 老英文版多無 zh-Hant）
- 935 candidates → 520 真 cross-refs → 503 解析（96.7%）
- **Graph: 161 nodes / 441 edges**

## 跑 pipeline

```bash
# 1. 下 video index
yt-dlp --flat-playlist --print-to-file "..." all_videos.tsv "https://youtube.com/@HungyiLeeNTU/videos"

# 2. 下 caption
bash scripts/download_captions_batch.sh data/missing_caption_video_ids.txt

# 3. 抽 candidates
python scripts/extract_ref_candidates.py

# 4. LLM 分類
python scripts/classify_refs_concurrent.py

# 5. LLM 解析 target
python scripts/resolve_targets_incremental.py

# 6. 視覺驗證 ambiguous case（可選）
python scripts/select_visual_cases.py
python scripts/visual_verify.py --queue

# 7. 建 graph data
python scripts/build_graph_data.py

# 8. site/graph.json 已更新，開啟 site/index.html
```

## 檔案結構

```
site/
  index.html       # Cytoscape.js 互動 graph
  graph.json       # nodes + edges 數據

scripts/
  parse_video_index.py
  ttml_parse.py
  extract_ref_candidates.py
  classify_refs_concurrent.py
  resolve_targets.py             # core logic
  resolve_targets_incremental.py # main entry (incremental write)
  visual_verify.py
  select_visual_cases.py
  build_graph_data.py
  llm_client.py

data/
  video_index.json     # 全頻道 482 部 metadata
  graph.json           # 最終 graph data
  playlists/           # 每個課程的影片清單

STORY.md           # 製作過程紀錄
yt_video_outline.md # YouTube 影片大綱
```

## 致謝

- [李宏毅老師](https://www.youtube.com/@HungyiLeeNTU)（大金老師）— 這個頻道的內容、字幕、教學
- yt-dlp / Cytoscape.js / OpenAI gpt-5-mini + gpt-5 vision

## 已知限制

- 201 部無 zh-Hant 字幕的英文老影片沒入 graph（多為 2017-2019 年的內容）
- 視覺驗證只跑了 156 個 ambiguous case，HIGH confidence 的沒全部驗證
- 某些「上學期」的 reference 解析有歧義（resolver 可能挑錯課程年份）
- 部分外部演講（IEEE / NeurIPS / ICASSP 等）不在 YouTube 頻道，會被誤對到頻道內影片
