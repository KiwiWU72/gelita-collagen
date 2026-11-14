"""
GELITA BCP PubMed 自動更新腳本 v2.1
搜尋策略：品牌名稱 + 核心研究者雙重驗證，確保每篇都是 GELITA BCP® 相關論文
"""

import os
import json
import time
import datetime
import urllib.request
import urllib.parse

from google import genai
from google.genai import types

# ==========================================
# 1. 初始化
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("找不到 GEMINI_API_KEY 環境變數！")

# gemini-1.5-flash 已於 2025 年停用，改用新版 google-genai SDK
# 依序嘗試；Google 常停用舊模型，第一個可用的就會被採用
GEMINI_MODELS = [m for m in [
    os.environ.get("GEMINI_MODEL"),
    "gemini-flash-latest",
    "gemini-3.8-flash",
    "gemini-3-flash",
] if m]
GEMINI_FAILURES = 0
client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(timeout=60_000),  # 單次呼叫最多 60 秒，避免卡死
)

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# ==========================================
# 2. GELITA 驗證白名單
# ==========================================

# 官方品牌名稱（出現即 100% 確認為 GELITA 論文）
GELITA_BRANDS = [
    "VERISOL", "FORTIGEL", "BODYBALANCE", "FORTIBONE",
    "TENDOFORTE", "PeptENDURE", "PETAGILE", "CURADERM"
]

# 核心研究者姓氏（幾乎專屬於 GELITA BCP 研究）
GELITA_AUTHORS_LAST = [
    "Oesser", "Schunck", "Zdzieblik", "Jendricke",
    "Kirmse", "Centner", "Jerger", "Bischof", "Dressler",
    "Praet", "Dobenecker", "Knefeli"
]

# GELITA 研究特有術語
GELITA_TERMS = [
    "SPECIFIC BIOACTIVE COLLAGEN PEPTIDES",
    "SPECIFIC COLLAGEN PEPTIDES",
    "BCP\u00ae",
    "GELITA"
]

# ==========================================
# 3. PubMed 搜尋策略（三層）
# ==========================================
SEARCH_QUERIES = [
    # 策略一：GELITA 官方品牌名稱（最精準，100% GELITA）
    "VERISOL OR FORTIGEL OR BODYBALANCE OR FORTIBONE OR TENDOFORTE OR PeptENDURE OR PETAGILE OR CURADERM",

    # 策略二：核心研究者 + 膠原蛋白胜肽（Oesser/Schunck 幾乎只發表 GELITA 研究）
    "(Oesser S[Author] OR Schunck M[Author] OR Zdzieblik D[Author] OR Jendricke P[Author]) AND collagen peptides",

    # 策略三：新生代 GELITA 研究者
    "(Centner C[Author] OR Jerger S[Author] OR Bischof K[Author] OR Dressler P[Author]) AND collagen peptides",
]

# ==========================================
# 4. PubMed API 工具函式
# ==========================================
def pubmed_search(query, max_results=5):
    """搜尋 PubMed，回傳 PMID 列表（最新排序）"""
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": max_results,
        "sort": "date"
    })
    url = f"{BASE_URL}esearch.fcgi?{params}"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())
        ids = data.get("esearchresult", {}).get("idlist", [])
        print(f"  → 找到 {len(ids)} 篇")
        return ids
    except Exception as e:
        print(f"  → 搜尋失敗: {e}")
        return []


def pubmed_fetch(pmid):
    """取得單篇論文的元數據與摘要"""
    summary_url = f"{BASE_URL}esummary.fcgi?db=pubmed&id={pmid}&retmode=json"
    abstract_url = f"{BASE_URL}efetch.fcgi?db=pubmed&id={pmid}&retmode=text&rettype=abstract"

    try:
        with urllib.request.urlopen(summary_url, timeout=15) as resp:
            summary_data = json.loads(resp.read())
        paper = summary_data.get("result", {}).get(pmid, {})

        time.sleep(0.35)  # NCBI rate limit: 3 req/sec

        with urllib.request.urlopen(abstract_url, timeout=15) as resp:
            abstract = resp.read().decode("utf-8")

        title = paper.get("title", "").replace("[", "").replace("]", "").rstrip(".")
        pubdate = paper.get("pubdate", "")[:4]
        authors_raw = paper.get("authors", [])
        author_names = [a.get("name", "") for a in authors_raw[:3]]
        if len(authors_raw) > 3:
            author_names.append("et al.")
        authors = ", ".join(author_names)
        journal = paper.get("fulljournalname", "")

        return {
            "pmid": pmid,
            "title": title,
            "authors": authors,
            "journal": journal,
            "year": int(pubdate) if pubdate.isdigit() else datetime.datetime.now().year,
            "abstract": abstract,
            "pubmedUrl": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        }
    except Exception as e:
        print(f"  → 取得 PMID {pmid} 失敗: {e}")
        return None

# ==========================================
# 5. GELITA 相關性驗證（核心防線）
# ==========================================
def validate_gelita(paper):
    """
    驗證論文是否確為 GELITA BCP® 相關研究。
    回傳 (is_gelita: bool, detected_brand: str or None)

    任一條件成立即通過：
    1. 標題/摘要出現 GELITA 官方品牌名稱
    2. 作者欄位包含核心研究者姓氏
    3. 摘要出現 GELITA 特有術語
    """
    full_text = (paper.get("title", "") + " " + paper.get("abstract", "")).upper()
    authors_str = paper.get("authors", "").upper()

    # 排除更正啟事／勘誤（不是新研究）
    title_up = paper.get("title", "").upper()
    if any(w in title_up for w in ("CORRIGENDUM", "ERRATUM", "CORRECTION")):
        print("  ✗ 更正啟事，跳過")
        return False, None

    # 必須跟膠原蛋白有關（避免 BodyBalance 運動課程這類同名誤判）
    if "COLLAGEN" not in full_text and "GELATIN" not in full_text:
        print("  ✗ 內容與膠原蛋白無關，跳過")
        return False, None

    # 驗證一：品牌名稱（最強憑證）
    for brand in GELITA_BRANDS:
        if brand.upper() in full_text:
            print(f"  ✓ 品牌驗證：{brand}")
            return True, brand

    # 驗證二：核心研究者姓氏
    for last_name in GELITA_AUTHORS_LAST:
        if last_name.upper() in authors_str:
            print(f"  ✓ 研究者驗證：{last_name}")
            return True, None

    # 驗證三：特定術語
    for term in GELITA_TERMS:
        if term in full_text:
            print(f"  ✓ 術語驗證：{term}")
            return True, None

    print(f"  ✗ 非 GELITA 論文，跳過")
    return False, None

# ==========================================
# 6. Gemini 智能分析
# ==========================================
def analyze_with_gemini(paper, detected_brand=None):
    """使用 Gemini 分析論文，生成結構化中文摘要"""

    if detected_brand:
        brand_instruction = f'brand 固定填入 "{detected_brand}"（已從論文直接偵測）。'
    else:
        brand_instruction = (
            "請根據研究目標組織推斷 brand："
            "皮膚/指甲/頭髮→VERISOL，關節/軟骨→FORTIGEL，"
            "肌肉/體脂→BODYBALANCE，骨骼/骨密度→FORTIBONE，"
            "肌腱/韌帶→TENDOFORTE，耐力/跑步→PeptENDURE，"
            "犬貓/馬→PETAGILE，傷口/異位性皮膚/牙齦→CURADERM。"
        )

    prompt = f"""你是一位嚴謹的生化與食品科學專家，專門研究 GELITA 膠原蛋白胜肽（BCP®）。

【任務】分析以下論文，輸出純 JSON，不得含任何 Markdown。

【品牌】{brand_instruction}

【tags】3個中文標籤，聚焦底層機制或臨床量化指標，
例如：["纖維母細胞增殖+31%", "骨密度BMD+3%", "dGEMRIC軟骨再生"]

【summary】80字以內中文科學總結，必須包含：
① 受試者人數與特徵  ② 每日劑量與干預時間  ③ 主要量化結果（%或p值）

【論文資訊】
標題：{paper['title']}
期刊：{paper['journal']}（{paper['year']}）
作者：{paper['authors']}
摘要：{paper['abstract'][:2500]}

輸出格式（只輸出此 JSON，不含其他文字）：
{{"brand": "...", "tags": ["...", "...", "..."], "summary": "..."}}"""

    try:
        last_err = None
        for m in GEMINI_MODELS:
            for attempt in range(3):
                try:
                    response = client.models.generate_content(model=m, contents=prompt)
                    clean = response.text.replace("```json", "").replace("```", "").strip()
                    return json.loads(clean)
                except Exception as e:
                    last_err = e
                    msg = str(e)
                    print(f"  → 模型 {m} 第{attempt+1}次失敗：{msg[:110]}")
                    if ("503" in msg or "504" in msg or "429" in msg) and attempt < 2:
                        time.sleep(20)  # 伺服器忙碌，稍等再試
                        continue
                    break
        raise last_err
    except Exception as e:
        global GEMINI_FAILURES
        GEMINI_FAILURES += 1
        print(f"  → Gemini 分析失敗: {e}")
        return None

def abstract_excerpt(text, n=260):
    """從 PubMed 純文字摘要取一段正文"""
    body = " ".join(l.strip() for l in text.splitlines() if l.strip())
    i = body.find("Abstract")
    body = body[i + 8:] if i >= 0 else body
    return body[:n].strip() + "…"


def retry_pending(db):
    """補做先前 Gemini 失敗的條目"""
    fixed = 0
    for p in db.get("papers", []):
        if not p.get("pending"):
            continue
        print(f"🔁 補摘要：{p['title'][:60]}")
        ai = analyze_with_gemini({"title": p["title"], "journal": p["journal"], "year": p["year"],
                                  "authors": p["authors"], "abstract": p.get("abstract", "")},
                                 p["brand"] if p["brand"] != "GELITA" else None)
        if ai:
            p.update(brand=ai.get("brand", p["brand"]), tags=ai.get("tags", p["tags"]),
                     summary=ai.get("summary", p["summary"]))
            p.pop("pending", None); p.pop("abstract", None)
            fixed += 1
    return fixed

# ==========================================
# 7. 主程式
# ==========================================
def main():
    print("=" * 55)
    print(f"  GELITA BCP PubMed 更新腳本 v2.1")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 55)

    # 讀取現有 data.json
    try:
        with open("data.json", "r", encoding="utf-8") as f:
            db = json.load(f)
    except FileNotFoundError:
        print("找不到 data.json，請確認檔案是否存在。")
        return

    # 建立已存在 PMID 集合（防止重複）
    existing_pmids = set()
    for p in db.get("papers", []):
        url = p.get("pubmedUrl", "")
        if "pubmed.ncbi.nlm.nih.gov/" in url and "?term=" not in url:
            pmid = url.rstrip("/").split("/")[-1]
            if pmid.isdigit():
                existing_pmids.add(pmid)
        pid = p.get("id", "")
        if pid.startswith("pmid_"):
            existing_pmids.add(pid[5:])

    print(f"現有論文：{len(db.get('papers', []))} 篇，已知 PMID：{len(existing_pmids)} 個\n")

    fixed_count = retry_pending(db)

    # 收集候選 PMID
    candidate_pmids = []
    for query in SEARCH_QUERIES:
        print(f"🔍 搜尋：{query[:72]}")
        pmids = pubmed_search(query, max_results=5)
        new_ones = [p for p in pmids if p not in existing_pmids and p not in candidate_pmids]
        candidate_pmids.extend(new_ones)
        time.sleep(0.5)

    candidate_pmids = list(dict.fromkeys(candidate_pmids))  # 去重
    print(f"\n共 {len(candidate_pmids)} 篇候選論文，開始逐一驗證...\n")

    added_count = 0

    for pmid in candidate_pmids[:10]:  # 單次最多處理 10 篇
        print(f"--- PMID {pmid} ---")

        paper = pubmed_fetch(pmid)
        if not paper:
            continue

        print(f"  標題：{paper['title'][:65]}...")

        # GELITA 相關性驗證（核心防線）
        is_gelita, detected_brand = validate_gelita(paper)
        if not is_gelita:
            continue

        # Gemini 分析
        print("  Gemini 分析中...")
        ai_data = analyze_with_gemini(paper, detected_brand)
        pending = False
        if not ai_data:
            # Gemini 失敗也先收錄，之後每次執行再補中文摘要
            pending = True
            ai_data = {"brand": detected_brand or "GELITA", "tags": ["待AI摘要"],
                       "summary": "（中文摘要待補）" + abstract_excerpt(paper["abstract"])}

        # 組合新條目
        new_entry = {
            "id": f"pmid_{pmid}",
            "title": paper["title"],
            "authors": paper["authors"],
            "journal": paper["journal"],
            "year": paper["year"],
            "brand": ai_data.get("brand", detected_brand or "GELITA"),
            "tags": ai_data.get("tags", []),
            "summary": ai_data.get("summary", ""),
            "pubmedUrl": paper["pubmedUrl"]
        }
        if pending:
            new_entry["pending"] = True
            new_entry["abstract"] = paper["abstract"][:3000]

        db["papers"].insert(0, new_entry)
        existing_pmids.add(pmid)
        added_count += 1
        print(f"  ✅ 已加入：[{new_entry['brand']}] {paper['title'][:50]}...\n")

        time.sleep(1)

    # 寫回 data.json
    if added_count > 0 or fixed_count > 0:
        db["lastUpdated"] = datetime.datetime.now().strftime("%Y-%m-%d")
        with open("data.json", "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 完成！共新增 {added_count} 篇 GELITA 論文，data.json 已更新。")
    else:
        print("\n📋 今日無新增 GELITA 論文。")

    if GEMINI_FAILURES:
        # 論文已先收錄；這裡只在 Actions 留下警示
        print(f"::warning::有 {GEMINI_FAILURES} 次 Gemini 摘要失敗，相關論文標記為『待AI摘要』，下次執行會自動補做")


if __name__ == "__main__":
    main()
