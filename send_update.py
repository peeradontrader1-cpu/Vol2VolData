import os
import requests
import pandas as pd
import time
from datetime import datetime
import pytz
from io import StringIO
import re

# ดึงค่าจาก GitHub Secrets
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# URL ข้อมูล Raw
RAW_INTRA = "https://raw.githubusercontent.com/pageth/Vol2VolData/main/IntradayData.txt"
RAW_OI = "https://raw.githubusercontent.com/pageth/Vol2VolData/main/OIData.txt"
RAW_IMG = "https://raw.githubusercontent.com/pageth/Vol2VolData/main/Intraday%2BOI.png"

def get_now_th():
    return datetime.now(pytz.timezone('Asia/Bangkok'))

def fetch_data(url):
    try:
        r = requests.get(f"{url}?t={int(time.time())}", timeout=30)
        if r.status_code == 200:
            return r.text
    except:
        return None
    return None

def main():
    txt_intra = fetch_data(RAW_INTRA)
    txt_oi = fetch_data(RAW_OI)
    
    if not txt_intra or not txt_oi:
        print("Error: ดึงข้อมูลไม่ได้")
        return

    # อ่านข้อมูลข้าม Header 2 บรรทัดแรก
    df_intra = pd.read_csv(StringIO(txt_intra), skiprows=2)
    df_oi = pd.read_csv(StringIO(txt_oi), skiprows=2)
    
    # สกัดชื่อ Series จากบรรทัดแรก
    series = re.search(r'^(.+?)\s+vs', txt_intra.split('\n')[0]).group(1) if " vs " in txt_intra else "N/A"
    now_th = get_now_th()

    # --- คำนวณตามคำสั่งใหม่ ---
    p_intra = int(df_intra['Put'].sum())
    c_intra = int(df_intra['Call'].sum())
    ratio = round(c_intra / p_intra, 1) if p_intra > 0 else 0
    
    # ดึงค่าเปลี่ยนแปลงล่าสุด (บรรทัดสุดท้าย)
    p_diff = int(df_intra['Put'].iloc[-1])
    c_diff = int(df_intra['Call'].iloc[-1])

    df_intra['Total'] = df_intra['Put'] + df_intra['Call']
    top_intra = df_intra.nlargest(2, 'Total')

    df_oi['Total'] = df_oi['Put'] + df_oi['Call']
    top_oi = df_oi.nlargest(2, 'Total')

    # --- จัดรูปแบบข้อความเป๊ะๆ ---
    msg = f"📊 GOLD UPDATE | {now_th.strftime('%H:%M')} น.\n"
    msg += f"🗓️ ซีรีย์: {series}\n\n"
    msg += f"📊 GOLD INTRADAY\n───────────────\n"
    msg += f"🟠 Put:  {p_intra:,} (+{p_diff})\n"
    msg += f"🔵 Call: {c_intra:,} (+{c_diff})\n"
    msg += f"⚖️ Ratio: 1 : {ratio}\n\n"
    msg += f"📍 TOP ACTIVE\n"
    for i, (_, row) in enumerate(top_intra.iterrows(), 1):
        msg += f"{i}️⃣ {int(row['Strike'])} | {int(row['Total']):,} (+{int(abs(row['Call']-row['Put']))})\n"
        msg += f"    └ P:{int(row['Put']):,} / C:{int(row['Call']):,}\n"
    
    msg += f"───────────────\n📊 GOLD OI\n───────────────\n"
    msg += f"🟠 Put:  {int(df_oi['Put'].sum()):,}\n"
    msg += f"🔵 Call: {int(df_oi['Call'].sum()):,}\n\n"
    msg += f"📍 TOP ACTIVE\n"
    for i, (_, row) in enumerate(top_oi.iterrows(), 1):
        msg += f"{i}️⃣ {int(row['Strike'])} | {int(row['Total']):,}\n    └ P:{int(row['Put']):,} / C:{int(row['Call']):,}\n"
    msg += f"───────────────\n✅ บันทึกเรียบร้อย"

    # --- ส่งรูปภาพ + ข้อความ ---
    try:
        img_res = requests.get(f"{RAW_IMG}?t={int(time.time())}").content
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", 
                      data={'chat_id': CHAT_ID, 'caption': msg, 'parse_mode': 'HTML'},
                      files={'photo': img_res})
        print("Success!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
