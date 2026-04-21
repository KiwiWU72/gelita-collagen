# GELITA BCP® 科學數據中心

> 彙整 GELITA 生物活性膠原蛋白胜肽（Bioactive Collagen Peptides, BCP®）臨床實證數據的動態科學文獻展示平台。

🌐 **線上網頁：** [https://kiwiwu72.github.io/gelita-collagen/](https://kiwiwu72.github.io/gelita-collagen/)

---

## 核心特色

**7 大品牌系列 · 38 篇臨床文獻 · 每日自動更新**

| 品牌 | 目標組織 | 代表性臨床數據 |
|------|----------|----------------|
| VERISOL® | 皮膚 / 指甲 / 頭髮 | 眼周皺紋 −20%，皮膚彈性 +7% |
| FORTIGEL® | 關節軟骨 | dGEMRIC MRI 確認軟骨蛋白聚糖顯著提升 |
| BODYBALANCE® | 肌肉 / 體脂 | 瘦體重 +4.2 kg，脂肪量 −5.4 kg |
| FORTIBONE® | 骨骼 | 脊柱 BMD +3%，股骨頸 BMD +6.7% |
| TENDOFORTE® | 肌腱 / 韌帶 | 跟腱橫截面積 +11%，扭傷發生率顯著下降 |
| PeptENDURE® | 耐力運動 | 60 分鐘跑步距離 +662 m，乳酸閾值提升 |
| PETAGILE® | 寵物關節 | 犬類峰值垂直力量顯著改善，馬匹跛行減少 |

---

## 系統架構

```
PubMed API  →  update_papers.py  →  Gemini AI 分析  →  data.json
                                                              ↓
                                              GitHub Actions 自動 commit
                                                              ↓
                                                index.html 動態渲染
```

- **前端**：HTML5 + Tailwind CSS + Vanilla JavaScript（單檔架構，無需建置工具）
- **資料庫**：`data.json`（所有論文的結構化中文摘要與 PubMed 連結）
- **自動化**：GitHub Actions，每日台灣時間 10:00 自動執行
- **AI 分析**：Google Gemini 1.5 Flash，萃取受試者、劑量、量化結果生成中文摘要

---

## 檔案說明

```
gelita-collagen/
├── index.html               # 網頁主程式（品牌卡片、文獻列表、機制圖解）
├── data.json                # 核心文獻資料庫（38 篇，含 PubMed 直連）
├── update_papers.py         # 自動更新腳本 v2.0
└── .github/
    └── workflows/
        └── daily_update.yml # GitHub Actions 排程設定
```

---

## 自動更新機制

每日台灣時間 10:00，GitHub Actions 自動執行以下流程：

1. **三層搜尋策略**
   - 品牌名稱搜尋（VERISOL / FORTIGEL 等直接命中）
   - 核心研究者搜尋（Oesser、Schunck、Zdzieblik、Centner 等）
   - 特有術語搜尋（specific bioactive collagen peptides）

2. **GELITA 相關性驗證**（核心防線）
   非 GELITA 論文在進入資料庫前會被自動過濾，確保每一筆都是 BCP® 相關研究。

3. **Gemini AI 分析**
   提取受試者人數、劑量、干預時間、量化結果，生成嚴謹中文摘要。

4. **自動 commit**
   有新論文時自動更新 `data.json` 並推送，網頁即時更新。

---

## 環境設定

在 GitHub Repository → **Settings → Secrets → Actions** 新增：

| Secret 名稱 | 說明 |
|-------------|------|
| `GEMINI_API_KEY` | Google AI Studio 取得的 API Key |

---

## 文獻連結說明

| 連結類型 | 數量 | 說明 |
|----------|------|------|
| PubMed PMID 直連 | 29 篇 | 100% 驗證，點擊直達原文 |
| Nutrafoods 期刊直連 | 3 篇 | Oesser 2020、Proksch 2020、Knefeli 2018 |
| MDPI 期刊直連 | 1 篇 | Cosmetics 2025 |
| PMC 直連 | 2 篇 | Jerger / Bischof 2023 |
| Google Scholar 搜尋 | 3 篇 | 確認未收錄於 PubMed 的論文 |

---

*© GELITA AG · BCP® Bioactive Collagen Peptides® · 本頁內容僅供專業研究參考，不構成醫療建議。*
