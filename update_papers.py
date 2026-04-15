import os
import json
import requests
import datetime
from google import genai

# 從環境變數讀取 API Key (GitHub Secrets)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("找不到 GEMINI_API_KEY 環境變數！")

# 使用新版的 Client 初始化方式
client = genai.Client(api_key=GEMINI_API_KEY)

def fetch_latest_pubmed(keyword="GELITA collagen OR bioactive collagen peptides", max_results=1):
    print(f"正在 PubMed 搜尋關鍵字: {keyword}")
    search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={keyword}&retmode=json&retmax={max_results}&sort=date"
    search_res = requests.get(search_url).json()
    id_list = search_res.get("esearchresult", {}).get("idlist", [])
    
    if not id_list:
        print("未找到新文獻。")
        return None
    
    latest_id = id_list[0]
    print(f"找到最新文獻 ID: {latest_id}")
    
    fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={latest_id}&retmode=json"
    fetch_res = requests.get(fetch_url).json()
    
    paper_data = fetch_res.get("result", {}).get(latest_id, {})
    title = paper_data.get("title", "")
    pubdate = paper_data.get("pubdate", "")[:4] 
    authors = ", ".join([a.get("name", "") for a in paper_data.get("authors", [])][:2]) + " et al."
    journal = paper_data.get("fulljournalname", "")
    
    abstract_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={latest_id}&retmode=text&rettype=abstract"
    abstract_text = requests.get(abstract_url).text
    
    return {
        "id": f"pmid_{latest_id}",
        "title": title,
        "authors": authors,
        "journal": journal,
        "year": int(pubdate) if pubdate.isdigit() else datetime.datetime.now().year,
        "pubmedUrl": f"https://pubmed.ncbi.nlm.nih.gov/{latest_id}/",
        "abstract": abstract_text
    }

def generate_summary_with_gemini(paper_info):
    print("正在交由 Gemini 進行科學機制分析...")
    prompt = f"""
    你是一位嚴謹的生化與食品科學專家。請基於第一性原理，閱讀以下醫學文獻摘要，將其轉化為嚴格的 JSON 格式。
    
    要求：
    1. brand: 判斷最相關的 GELITA 產品線 (VERISOL, FORTIGEL, BODYBALANCE, FORTIBONE, TENDOFORTE, PeptENDURE, PETAGILE)。若無明確提及，請根據目標組織推斷。
    2. tags: 3 個與底層機制或臨床指標相關的中文標籤 (如: ["纖維母細胞", "膠原合成", "皮膚彈性"])。
    3. summary: 撰寫約 80 字的中文總結。必須包含具體科學數據 (如 P-value、百分比或樣本數)，指出對細胞或受體的底層機制作用。絕不使用無根據的比喻。

    文獻資訊：
    標題：{paper_info['title']}
    摘要：{paper_info['abstract']}
    
    請只輸出 JSON，勿包含 Markdown 標記：
    {{
      "brand": "品牌",
      "tags": ["標籤1", "標籤2", "標籤3"],
      "summary": "科學總結"
    }}
    """
    
    try:
        # 【修正1】將模型升級為最新的 gemini-2.0-flash
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        # 【修正2】移除 response.text，避免發生 UnboundLocalError 崩潰
        print(f"呼叫 Gemini 或解析 JSON 時發生錯誤: {e}")
        return None

def main():
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            db = json.load(f)
    except FileNotFoundError:
        print("找不到 data.json。")
        return

    latest_paper = fetch_latest_pubmed()
    if not latest_paper:
        return

    existing_ids = [p['id'] for p in db.get('papers', [])]
    if latest_paper['id'] in existing_ids:
        print("此文獻已存在，跳過更新。")
        return

    ai_analysis = generate_summary_with_gemini(latest_paper)
    if not ai_analysis:
        return

    new_entry = {
        "id": latest_paper['id'],
        "title": latest_paper['title'],
        "authors": latest_paper['authors'],
        "journal": latest_paper['journal'],
        "year": latest_paper['year'],
        "brand": ai_analysis.get('brand', 'GELITA'),
        "tags": ai_analysis.get('tags', []),
        "summary": ai_analysis.get('summary', ''),
        "pubmedUrl": latest_paper['pubmedUrl']
    }

    db['papers'].insert(0, new_entry)
    db['lastUpdated'] = datetime.datetime.now().strftime("%Y-%m-%d")

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    
    print(f"成功寫入 {new_entry['id']}！")

if __name__ == "__main__":
    main()
