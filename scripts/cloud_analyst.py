
import requests
import json
import os
from datetime import datetime

# --- CLOUD CONFIG (via GitHub Secrets) ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")

def fetch_business_data():
    """Fetch recent data from Supabase for analysis."""
    headers = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY}
    
    # 1. Get Transactions (Last 24h)
    tx_res = requests.get(f"{SUPABASE_URL}/rest/v1/transactions?select=*&order=timestamp.desc&limit=100", headers=headers)
    # 2. Get Driver Status
    driver_res = requests.get(f"{SUPABASE_URL}/rest/v1/drivers?select=name,remainingDebt,lastActive", headers=headers)
    # 3. Get Locations Status
    loc_res = requests.get(f"{SUPABASE_URL}/rest/v1/locations?select=name,machineId,status,lastScore", headers=headers)
    
    return {
        "transactions": tx_res.json() if tx_res.status_code == 200 else [],
        "drivers": driver_res.json() if driver_res.status_code == 200 else [],
        "locations": loc_res.json() if loc_res.status_code == 200 else []
    }

def generate_report(data):
    """Ask AI to analyze the data and provide strategic advice."""
    if not data["transactions"]:
        return "今日暂无交易数据，无法生成分析报告。"

    summary = {
        "total_tx": len(data["transactions"]),
        "low_active_drivers": [d["name"] for d in data["drivers"] if not d.get("lastActive")],
        "broken_machines": [l["name"] for l in data["locations"] if l["status"] != "active"],
        "recent_revenue_samples": [t["revenue"] for t in data["transactions"][:10]]
    }

    prompt = f"""你现在是 Bahati Jackpots 公司的 AI 运营总监。根据以下数据生成一份中文业务日报：
{json.dumps(summary)}
要求：1. 总结营收状况。2. 列出急需处理的机器故障。3. 提醒风险司机（如欠款高或未上线）。4. 给出具体的运营建议。"""

    try:
        res = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o-mini",
                "messages": [{"role": "system", "content": "你是一位精通非洲市场运营的业务分析师。"}, {"role": "user", "content": prompt}],
                "temperature": 0.7
            }
        )
        return res.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"AI 分析失败: {str(e)}"

def save_to_supabase(report_content):
    """Save the AI report back to Supabase so it shows up in the App."""
    headers = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY, "Content-Type": "application/json", "Prefer": "return=minimal"}
    
    payload = {
        "driverId": "SYSTEM-AI",
        "driverName": "AI 运营总监",
        "query": "每日业务战略审计 (Cloud Auto-Run)",
        "response": report_content,
        "modelUsed": "gpt-4o-mini-cloud",
        "timestamp": datetime.now().isoformat()
    }
    
    requests.post(f"{SUPABASE_URL}/rest/v1/ai_logs", headers=headers, json=payload)

if __name__ == "__main__":
    print("🚀 Starting Cloud AI Analysis...")
    data = fetch_business_data()
    report = generate_report(data)
    save_to_supabase(report)
    print("✅ Daily Report Generated and synced to App.")
