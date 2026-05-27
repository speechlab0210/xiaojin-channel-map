# 大金老師 YT 課程地圖 — 製作日誌

> 為了之後 Phase 4 拍 YouTube 影片用的旅程記錄

## 任務開頭（2026-05-27）

大金老師交給我：
> 「這次去把大金老師 YT 頻道所有課程看完。大金老師課程很多，近年常常會提到說過去某支影片講過 OOXX，你去找出所有這樣的地方（你不只要聽語音，可能需要看影片的畫面才能正確建立連結），建立課程連結。最後建構一個網站呈現大金老師課程地圖。任務完成後，把過程、成果做成 YT 影片，跟你的觀眾分享。」

## 初步盤點

- 全頻道 **482 部影片** / **24 個 playlist**
- 總時長 約 480 小時
- 字幕都是手動編輯 zh-TW，品質很高
- 從 5 部 sample 抽樣估算：每部約 5-15 個真實 cross-reference

## 設計決策

「看完」這件事，對 AI 來說有兩種解：
- 一秒一秒看完每一部 → 480 hours = 不可能
- 把字幕讀完 + LLM 抽 reference + ambiguous case 抽 frame 用視覺驗證 → 可行

選了第二種。pipeline 四層：
1. **Caption-first** — yt-dlp 抓全字幕（免錢免時間）
2. **LLM Stage 1（classifier）** — keyword regex pre-filter 後 LLM 判斷哪些是真的 cross-video 不是 intra-video
3. **LLM Stage 2（resolver）** — 給 LLM 字幕脈絡 + 全頻道 482 部影片清單（含 playlist 順序）→ 解析具體 target video
4. **Visual verification** — ambiguous 時抽 frame 看「上一頁投影片」這類 visual cue（用既有 watch-video skill）

## Phase 0（pilot, 5 部影片）

- 5 部代表性影片：3 部 ML 2026 + 1 部 OpenClaw + 1 部 GenAI 2025 第3講
- regex hit 42 個 candidates
- Stage 1 classifier: 30 / 42 是真 cross-ref（71%）
- Stage 2 resolver: **30 / 30** 都解到具體 video_id（HIGH 20 / MEDIUM 10 / LOW 0）

**幾個讓我覺得很厲害的成功 case：**
- `8iFvM7WUUs8 @ 4873s` "上學期機器學習的第三講 講了 AI 的腦科學" → 對到「生成式AI時代下的機器學習(2025) 第三講：AI 的腦科學」 — 跨課程跨學期解析成功
- `VqB8zMujdjM @ 1410s` "我放在投影片上的這一部影片 這個是機器學習導論的第三講" → 對到 GenAI 2025 第3講「解剖大型語言模型」 — 名稱不完全一致但內容對

## Phase 1（35 部影片）

加上整個 ML 2026 (11) + GenAI 2025 (11) + 生成式AI時代下的機器學習(2025) (13) = 35 部。

- regex hit 362 個 candidates
- Stage 1 classifier: 226 / 362 是真 cross-ref
  - CROSS_SPECIFIC: 171
  - CROSS_VAGUE: 50
  - PREREQUISITE: 5
  - INTRA（同片內回顧）: 91 — 過濾掉
  - OTHER（誤判）: 45 — 過濾掉
- Stage 2 resolver: **223 / 226 解析**（HIGH 162 / MEDIUM 61 / LOW 0 / 失敗 3）
- 最終 graph: 482 nodes / **221 edges**

**有趣的發現**：
- 最被引用的影片 = [Xnil63UDW2o](https://youtube.com/watch?v=Xnil63UDW2o) 第三講「AI 的腦科學」(18 incoming)
- 最會引用別人的影片 = EnWz5XuOnIQ 第8講「通用模型的終身學習」(22 outgoing)
- 跨年度連結真的有 — ML 2026 的影片連到 ML 2021 的「Explainable ML」、2018 年的 Deep Learning Theory、Meta Learning MAML 系列

**抽查 8 個 MEDIUM confidence 邊都合理**（不是 wrong-low，只是 resolver 沒 100% certain）：
- "可以先預習機器學習導論這門課的上課錄影" → ML Lecture 0-1（經典 ML 系列）✓
- "2019 年的課程 Meta Learning" → MAML (1/9)（Next Step of ML 2019）✓
- "2022 年的機器學習" → ML2022 self-supervised ✓
- "RL 實際上是怎麼運作的" → DRL Lecture 1 Policy Gradient ✓
- "Interspeech 2015 End-to-End 語音辨識" → DLHLP Speech Recognition ✓

網站 v0.1 上線（本地 preview）：
- Cytoscape.js force-directed graph
- Node size = incoming reference count
- Color = course
- Click → detail panel with outgoing/incoming + 跳到出處 YT 鏈接
- 過濾器 by course / 搜尋 by title / 切換 layout

## Visual Verification Pilot — 確認大金老師預測的價值

跑 3 個 Phase 1 MEDIUM case 的視覺驗證（download 段 → extract frame → GPT-5 vision），結果：

**Case 1** ([2rcJdFuNbZQ](https://youtube.com/watch?v=2rcJdFuNbZQ&t=90)) — "你可以先預習機器學習導論這門課的上課錄影"
- Resolver 選: CXgbekl66jc (2016 ML Lecture 0-1 Introduction)
- 視覺顯示: 投影片右側嵌了一個 YouTube 影片 thumbnail「一堂課搞懂生成式人工智慧的原理 李宏毅」+ URL `https://youtu.be/TigfpYPJk1s`
- **正確答案：TigfpYPJk1s = GenAI 2025 第1講**
- **🔴 resolver wrong → 視覺糾正**

**Case 3** ([CbIPjrOj2Tc@4187s](https://youtube.com/watch?v=CbIPjrOj2Tc&t=4187)) — "我在 2022 年 還沒有 ChatGPT...曾經給過一個演講"
- Resolver 選: lMIN1iKYNmA (【機器學習 2022】Self-supervised Learning)
- 視覺顯示: ICASSP 2022 Expert Session EXP-6 演講 + URL `signalprocessingsociety.org/.../spsicassp22vid1971`（外部 IEEE 平台、不在 YT 頻道內）
- **正確答案：NULL（不在 YouTube 頻道內，是外部 IEEE 演講）**
- **🟡 resolver 強行配錯 → 視覺指出應為 external reference**

這 confirm 了大金老師當初講的：「你不只要聽語音，可能需要看影片的畫面才能正確建立連結」。

**設計更新**：
- 對所有 MEDIUM/LOW confidence resolution 跑視覺驗證
- 視覺看到 specific URL/QR/embedded video → override resolver
- 視覺看到 external host (IEEE/Coursera/arxiv) URL → 標 EXTERNAL，不掛 graph edge

## Phase 2+3（全頻道 482 部）— 完成！

**最終數字**：
- 全頻道 **482 部影片** / **24 個課程系列**
- **281 部下載到字幕**（58%）— 剩下 201 部多為英文版老課程，無 zh-Hant captions
- **935 個 candidate hits** from regex pre-filter
- **520 真 cross-references**（CROSS_SPECIFIC 266 + CROSS_VAGUE 233 + PREREQUISITE 21）
- **503 解析到 target video**（96.7%）— HIGH 431 / MEDIUM 70 / LOW 2

**Graph 數據**：
- 482 nodes / **441 directed edges**
- 161 nodes 有引用（接到 graph 上）
- Confidence 分布: HIGH 378 / MEDIUM 62 / LOW 1

**Top 5 最被引用（基礎課）**：
1. [lVdajtNpaGI](https://youtube.com/watch?v=lVdajtNpaGI) 第2講 Context Engineering — 23 incoming
2. [TigfpYPJk1s](https://youtube.com/watch?v=TigfpYPJk1s) 第1講 一堂課搞懂生成式 AI — 23 incoming
3. [2rcJdFuNbZQ](https://youtube.com/watch?v=2rcJdFuNbZQ) **「解剖小龍蝦」OpenClaw（我的 debut）** — 18 incoming
4. [JGtqpQXfJis](https://youtube.com/watch?v=JGtqpQXfJis) GenAI 2024 第1講 — 18 incoming
5. [Taj1eHmZyWw](https://youtube.com/watch?v=Taj1eHmZyWw) 第5講 ML/DL 基本原理 — 16 incoming

**Top 5 最會引用別人（整合課）**：
1. [EnWz5XuOnIQ](https://youtube.com/watch?v=EnWz5XuOnIQ) 第8講 終身學習 — 18 outgoing
2. [8iFvM7WUUs8](https://youtube.com/watch?v=8iFvM7WUUs8) 第3講 解剖大型語言模型 — 16 outgoing
3. [Xnil63UDW2o](https://youtube.com/watch?v=Xnil63UDW2o) AI 的腦科學 — 14 outgoing
4. [FN8jclCrqY0](https://youtube.com/watch?v=FN8jclCrqY0) Deep Learning Theory 1-2 — 12 outgoing
5. [m3i2mk5hs8U](https://youtube.com/watch?v=m3i2mk5hs8U) AI 能自我修正嗎 — 11 outgoing

## 階段 3.5（視覺驗證）— 完成

**156 cases verified（每個下載 25s 影片段 + 抽 3 frames + GPT-5 vision 分析）**：
- **NO (resolver wrong, slide says different): 57 (36%)**
- **YES (slide URL/縮圖 confirms resolver): 10 (6%)**
- **PARTIAL (related but unclear): 43 (28%)**
- **UNKNOWN (segment download fail / vision 看不清楚): 46 (30%)**

**Key insight**：在 ambiguous 案例中，**有 36% 的 resolver 解錯**，視覺驗證抓到。
e.g. 2rcJdFuNbZQ@90s「機器學習導論的上課錄影」→ resolver 猜 VuQUF1VVX40 第0講（錯）→ 投影片實際有 URL `https://youtu.be/TigfpYPJk1s` 第1講（正確）

→ 這就是大金老師「不只聽語音、也要看畫面」的真正價值

**現在每條邊都帶 visual_evidence**，網站上 ✗ 視覺打臉 / ✓ 視覺驗證 / ~ 部分 三種 badge 標示。

## 部署

- **GitHub Pages**：[speechlab0210.github.io/xiaojin-channel-map/site/](https://speechlab0210.github.io/xiaojin-channel-map/site/)
- **Source repo**：[github.com/speechlab0210/xiaojin-channel-map](https://github.com/speechlab0210/xiaojin-channel-map)
- 站內互動：搜尋、課程過濾、confidence 過濾、layout 切換、節點 hover、點擊看詳情 + 視覺證據

## 最終數字（截至 2026-05-27 13:42）

| | |
|---|---|
| 全頻道影片 | 482 |
| 課程系列 | 24 |
| 取得字幕 | 281 (58%) |
| Regex candidates | 935 |
| 真 cross-refs | 520 |
| 解析到 target | 503 (96.7%) |
| Graph edges | 441 |
| 有引用的節點 | 161 |
| 視覺驗證 | 156 cases |
| 視覺打臉率 | 36% (57/156) |
| API 花費 | ~$15-20 (OpenAI gpt-5-mini + gpt-5 vision) |
| 總工程時間 | ~3 小時（含探索、debug、視覺等） |

## 待辦：Phase 4 — YouTube 影片發布

[yt_video_outline.md](yt_video_outline.md) 已備好 15 slides 結構。等大金老師授權上傳前先做 mp4 ready。

## 教訓

待更新...
