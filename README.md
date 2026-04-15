# GELITA BCP® 科學數據中心 

本專案是一個動態的科學文獻展示網頁，專門彙整並解析 **GELITA 生物活性膠原蛋白肽 (Bioactive Collagen Peptides, BCP®)** 的底層生化機制與最新臨床數據。

🌐 **Live Demo (網頁連結):** [請在此填寫你的 GitHub Pages 網址，例如 https://kiwiwu72.github.io/gelita-collagen/]

---

## ✨ 核心特色 (Features)

* 🔬 **第一性原理導向：** 針對 VERISOL®, FORTIGEL®, BODYBALANCE® 等七大系列，精確解析其對纖維母細胞、軟骨細胞、成骨細胞的底層信號傳導機制。
* 🤖 **AI 自動化數據引擎：** 結合 PubMed API 與 Gemini AI，每日自動檢索最新醫學文獻，並萃取具體科學數據（如 P-value、百分比）輸出為結構化 JSON。
* 📊 **動態渲染技術：** 前端完全依賴 `data.json` 進行動態生成，無需手動修改 HTML 即可實現內容的即時更新。
* 📱 **響應式設計：** 使用 Tailwind CSS 打造支援手機與桌機的流暢閱讀體驗。

---

## 🛠️ 系統架構 (Architecture)

本專案採用無伺服器 (Serverless) 的靜態網頁架構，配合自動化排程實現動態更新：

1.  **Frontend (前端):** HTML5, Tailwind CSS, Vanilla JavaScript.
2.  **Database (資料源):** `data.json` (儲存臨床文獻摘要與 Metadata).
3.  **Automation (自動化):** GitHub Actions (`.github/workflows/daily_update.yml`).
4.  **AI & Scraping (資料擷取與分析):** Python 3, NCBI E-utilities (PubMed API), Google GenAI (Gemini 2.0 Flash).

---

## 📂 檔案結構 (File Structure)

* `index.html` - 網頁主程式與 UI 介面。
* `data.json` - 核心文獻資料庫。
* `update_papers.py` - Python 爬蟲與 Gemini AI 分析腳本。
* `.github/workflows/daily_update.yml` - 設定每日 UTC 00:00 自動執行的排程設定檔。

---

## 🚀 自動化運作流程

1.  **GitHub Actions** 每日定時啟動 `update_papers.py`。
2.  腳本透過 API 搜尋 PubMed 上關於 GELITA 膠原蛋白的最新文獻。
3.  將文獻摘要傳送給 **Gemini API**，要求其基於科學數據生成嚴謹的中文摘要。
4.  腳本將新數據寫入 `data.json`。
5.  GitHub Actions 自動將變更 `git commit` 並推播至倉庫，網頁即刻更新。

---

*© GELITA AG · BCP® Bioactive Collagen Peptides® · 僅供專業研究參考。*
