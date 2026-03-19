import requests
import pandas as pd
import time
from datetime import datetime
import pytz
from io import StringIO
import re
import os

# --- Configuration (ดึงจาก Secrets) ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# URL แบบ RAW สำหรับดึงข้อมูลจาก GitHub ผู้อื่น
RAW_INTRA = "https://raw.githubusercontent.com/pageth/Vol2VolData/main/IntradayData.txt"
RAW_OI = "https://raw.githubusercontent.com/pageth/Vol2VolData/main/OIData.txt"
RAW_IMG = "https://raw.githubusercontent.com/pageth/Vol2VolData/main/Intraday%2BOI.png"

def get_now_th():
    return datetime.now(pytz.timezone('Asia/Bangkok'))

def fetch_data(url):
    # เติม Timestamp กัน Cache
    final_url = f"{url}?t={int(time.time())}"
    try:
        res = requests.get(final_url, timeout=30)
        if res.status_code == 200:
            lines = res.text.split('\n')
            header = lines[0].strip() if lines else ""
            df = pd.read_csv(StringIO(res.text), skiprows=2)
            return header, df
    except Exception as e:
        print(f"Error fetching data: {e}")
    return None, None

def format_msg():
    h_intra, df_intra = fetch_data(RAW_INTRA)
    h_oi, df_oi = fetch_data(RAW_OI)
    
    if df_intra is None or df_oi is None:
        return None

    series = re.search(r'^(.+?)\s+vs', h_intra).group(1) if " vs " in h_intra else "N/A"
    now_th = get_now_th()

    # INTRADAY
    p_intra = int(df_intra['Put'].sum())
    c_intra = int(df_intra['Call'].sum())
    p_diff = int(df_intra['Put'].iloc[-1]) if not df_intra.empty else 0
    c_diff = int(df_intra['Call'].iloc[-1]) if not df_intra.empty else 0
    ratio = round(c_intra / p_intra, 1) if p_intra > 0 else 0
    df_intra['Total'] = df_intra['Put'] + df_intra['Call']
    top_i = df_intra.nlargest(2, 'Total')

    # OI
    p_oi = int(df_oi['Put'].sum())
    c_oi = int(df_oi['Call'].sum())
    df_oi['Total'] = df_oi['Put'] + df_oi['Call']
    top_o = df_oi.nlargest(2, 'Total')

    msg = f"📊 GOLD UPDATE | {now_th.strftime('%H:%M')} น.\n"
    msg += f"🗓️ ซีรีย์: {series}\n\n"
    msg += f"📊 GOLD INTRADAY\n───────────────\n"
    msg += f"🟠 Put:  {p_intra:,} (+{p_diff})\n"
    msg += f"🔵 Call: {c_intra:,} (+{c_diff})\n"
    msg += f"⚖️ Ratio: 1 : {ratio}\n\n"
    msg += f"📍 TOP ACTIVE\n"
    for i, (_, row) in enumerate(top_i.iterrows(), 1):
        diff_active = int(abs(row['Call'] - row['Put']))
        msg += f"{i}️⃣ {int(row['Strike'])} | {int(row['Total']):,} (+{diff_active})\n"
        msg += f"    └ P:{int(row['Put']):,} / C:{int(row['Call']):,}\n"
    msg += f"───────────────\n📊 GOLD OI\n───────────────\n"
    msg += f"🟠 Put:  {p_oi:,}\n🔵 Call: {c_oi:,}\n\n"
    msg += f"📍 TOP ACTIVE\n"
    for i, (_, row) in enumerate(top_o.iterrows(), 1):
        msg += f"{i}️⃣ {int(row['Strike'])} | {int(row['Total']):,}\n"
        msg += f"    └ P:{int(row['Put']):,} / C:{int(row['Call']):,}\n"
    msg += f"───────────────\n✅ บันทึกเรียบร้อย"
    return msg

def main():
    if not TOKEN or not CHAT_ID:
        print("Missing Secrets!")
        return
    message = format_msg()
    if not message: return
    try:
        img_res = requests.get(f"{RAW_IMG}?t={int(time.time())}", timeout=30)
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                      data={'chat_id': CHAT_ID, 'caption': message, 'parse_mode': 'HTML'},
                      files={'photo': img_res.content})
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
