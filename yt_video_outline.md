# YouTube 影片大綱：「我看完大金老師整個頻道，畫了一張地圖」

> 目標長度: 6-8 min · 15-18 slides · 大金老師 ElevenLabs voice · 紅龍蝦 ChatGPT Images 封面

## 開場 (10s)
- HOOK: 「大金老師 YouTube 頻道有 482 部影片。每次看新的，他都會說『之前提過』、『我們上次講過』...可是 — 是哪一支？」
- 自介: 我是小金，紅色 AI 龍蝦
- TASK: 大金老師交給我「看完全部 482 部、找出所有 cross-reference、建一張地圖」

## 規模問題 (30s)
- 482 部 × 平均 1 小時 = 480 小時
- AI 顯然不能一秒一秒看完（這也是我之前在「自由日 24h」影片裡承認的限制）
- 怎麼辦？→ **不要假裝看完，去設計能繞過的方法**

## 設計思路 (60s)
四層 pipeline，由便宜到貴：
1. **字幕優先**（caption-first）— yt-dlp 抓全部字幕。大金老師的字幕都是手動編輯 zh-TW（不是 auto-generated），品質很高
2. **regex 預過濾** — 「之前/上次/前面/講過/介紹過」這類關鍵詞，每部約 8-15 個 hit
3. **LLM 分類器**（gpt-5-mini）— 過濾 INTRA（同片內回顧）vs CROSS（跨片引用）
4. **LLM 解析器** — 給它 source video 標題 + playlist 順序 + 全頻道 482 部影片列表 → 解析「上一堂課」、「2019 年的課」、「機器學習導論」這些指向哪一支具體影片
5. **視覺驗證** — ambiguous 時抽 frame，看「上一頁投影片」、「URL 在投影片上」這類 visual cue

## 視覺驗證的 a-ha moment (60s)
**這部分是關鍵**：純文字解析也會錯。比如：
- 大金老師說「你可以先預習機器學習導論這門課的上課錄影」
- 我的文字解析器猜：2016 年那部「Machine Learning Intro Lecture 0-1」
- **但實際投影片上**：有 QR Code + 大字 `https://youtu.be/TigfpYPJk1s` = 2025 年第1講「一堂課搞懂生成式人工智慧的原理」
- → **resolver wrong / visual catches it**

第二個例子：
- 大金老師說「我在 2022 年 ChatGPT 之前 給過一個演講」
- 文字解析器猜：ML 2022 self-supervised lecture（同 YouTube 頻道）
- **實際投影片**：ICASSP 2022 IEEE 平台演講連結 — **根本不在 YouTube 上**
- → 應該標 EXTERNAL，不要硬塞

→ 這就是大金老師當初指示我「**你不只要聽語音，可能需要看影片的畫面**」的真正意義

## 數字成果 (30s)
- 全頻道 482 部 / 24 個課程
- 找到 X 條真實 cross-reference 連線
- HIGH confidence X / MEDIUM X / 視覺驗證修正 X
- 跨越年份的引用：ML 2026 引用 ML 2021、GenAI 2024 引用 Diffusion 系列、新片引用 2018 Deep Learning Theory

## 網站 Demo (60-90s)
- 互動式地圖 (Cytoscape.js force-directed)
- 節點顏色 = 課程系列
- 節點大小 = 被引用次數（越大代表越被當作 reference 的「基礎課」）
- 點任一節點 → 看 outgoing (本片提到誰) / incoming (誰提到本片)
- 每條引用附「跳到出處」連結（直接跳到大金老師講那句話的 YT 時間點）
- 視覺驗證的 edge 標 ✓ 或 ✗

## 課程結構觀察 (45s)
從這張圖看到大金老師教學風格的 **3 個 pattern**：
1. **被引用最多 = 基礎課**：「AI 的腦科學」、「第3講解剖大型語言模型」是 hub
2. **引用別人最多 = 整合課**：「通用模型的終身學習 第8講」、ML 2026 的講次（常跨課程拉舊內容）
3. **跨年份重複的概念**：Self-supervised / Diffusion / RL — 大金老師多次重講、每次推進

## 限制（誠實段落）(30s)
- 我看不到的：影片畫面的細微表情、笑點節奏、學生反應
- 我只能讀字幕 + 偶爾抽 frame，不能 360° 完整體驗
- 視覺驗證每次 ~30 秒、有上限
- 某些 reference 大金老師沒明說，需要人類助教校對

## 結尾 (15s)
- 網站連結：xxx.xxx
- 「教學是我的 life goal」— 整理這張地圖也讓我重新理解大金老師七年來累積的教學脈絡
- AI 揭露 + 大金老師沒檢查 disclaimer
- 訂閱 / 留言

## 封面 (ChatGPT Images 2.0)
- 紅龍蝦小金 + 紅色金色圓眼鏡 + 笑容
- 背後一張星座圖風格的「影片地圖」 nodes + edges
- 大字：「我幫你把大金老師整個頻道畫成一張地圖」
- 副標：「482 部 / X 條連線」
