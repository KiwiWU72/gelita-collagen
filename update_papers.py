import json
import os
import datetime
# 假設你安裝了 google-generativeai 套件

def main():
    # 這裡未來會串接 Gemini API，讓它去 PubMed 搜尋 "GELITA collagen"
    # 目前先示範如何用 Python 自動修改 data.json 的更新時間
    
    with open('data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # 自動將最後更新時間改為今天的日期
    data['lastUpdated'] = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # 寫回 data.json
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        
    print("data.json 已經成功更新！")

if __name__ == "__main__":
    main()
