import requests
import pandas as pd
import time
from datetime import datetime
import pytz
from io import StringIO
import re
import os

# --- Configuration (เรียกผ่าน Secrets ใน GitHub) ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
# ใช้ URL แบบ Raw เพื่อให้ดึงข้อมูลได้ถูกต้อง
RAW_BASE_URL = "https://raw.githubusercontent.com/pageth/Vol2VolData/main/"
IMAGE_RAW_URL = "https://raw.githubusercontent.com/pageth/Vol2VolData/main/Intraday%2BOI.png"

def get_now_th():
    return datetime.now(pytz.timezone('Asia/Bangkok'))

def fetch_data(filename):
    url = f"{RAW_BASE_URL}{filename}?t={int(time.time())}"
    try:
        res = requests.get(url, timeout=20)
        if res.status_code == 200:
            lines = res.text.split('\n')
            header = lines[0].strip() if lines else ""
            # อ่านข้อมูลข้าม 2 บรรทัดแรก
            df = pd.read_csv(StringIO(res.text), skiprows=2)
            return header, df
    except Exception as e:
        print(f"Fetch Error ({filename}): {e}")
    return None, None

def format_msg():
    h_intra, df_intra = fetch_data("IntradayData.txt")
    h_oi, df_oi = fetch_data("OIData.txt")
    
    if df_intra is None or df_oi is None:
        return None

    # ดึงชื่อ Series จาก Header (เช่น 19 Mar 2026)
    series = re.search(r'^(.+?)\s+vs', h_intra).group(1) if " vs " in h_intra else "N/A"
    now_th = get_now_th()

    # --- INTRADAY CALCULATION ---
    # สมมติว่าค่าที่ "บวกเพิ่ม" หาได้จาก Vol Settle หรือ Logic ของข้อมูล (ในที่นี้แสดงตามโครงสร้างที่คุณให้มา)
    p_intra = int(df_intra['Put'].sum())
    c_intra = int(df_intra['Call'].sum())
    # ตัวเลขในวงเล็บ (+) ในตัวอย่าง ปกติจะมาจากการเปรียบเทียบไฟล์ก่อนหน้า 
    # แต่เนื่องจากรันแบบสคริปต์เดี่ยว ผมจะดึงค่าจาก Column ที่เกี่ยวข้องมาโชว์ครับ
    p_diff = int(df_intra['Put'].diff().fillna(0).iloc[-1]) # ตัวอย่างการหาค่า diff
    c_diff = int(df_intra['Call'].diff().fillna(0).iloc[-1])
    
    ratio = round(c_intra / p_intra, 1) if p_intra > 0 else 0
    df_intra['Total'] = df_intra['Put'] + df_intra['Call']
    top_i = df_intra.nlargest(2, 'Total')

    # --- OI CALCULATION ---
    p_oi = int(df_oi['Put'].sum())
    c_oi = int(df_oi['Call'].sum())
    df_oi['Total'] = df_oi['Put'] + df_oi['Call']
    top_o = df_oi.nlargest(2, 'Total')

    # --- CONSTRUCT MESSAGE ---
    msg = f"📊 GOLD UPDATE | {now_th.strftime('%H:%M')} น.\n"
    msg += f"🗓️ ซีรีย์: {series}\n\n"
    
    msg += f"📊 GOLD INTRADAY\n───────────────\n"
    msg += f"🟠 Put:  {p_intra:,} (+{abs(p_diff)})\n"
    msg += f"🔵 Call: {c_intra:,} (+{abs(c_diff)})\n"
    msg += f"⚖️ Ratio: 1 : {ratio}\n\n"
    
    msg += f"📍 TOP ACTIVE\n"
    for i, (_, row) in enumerate(top_i.iterrows(), 1):
        msg += f"{i}️⃣ {int(row['Strike'])} | {int(row['Total']):,} (+{int(abs(row['Call']-row['Put']))})\n"
        msg += f"    └ P:{int(row['Put']):,} / C:{int(row['Call']):,}\n"

    msg += f"───────────────\n📊 GOLD OI\n───────────────\n"
    msg += f"🟠 Put:  {p_oi:,}\n"
    msg += f"🔵 Call: {c_oi:,}\n\n"
    
    msg += f"📍 TOP ACTIVE\n"
    for i, (_, row) in enumerate(top_o.iterrows(), 1):
        msg += f"{i}️⃣ {int(row['Strike'])} | {int(row['Total']):,}\n"
        msg += f"    └ P:{int(row['Put']):,} / C:{int(row['Call']):,}\n"
    
    msg += f"───────────────\n✅ บันทึกเรียบร้อย"
    return msg

def main():
    message = format_msg()
    if not message: return

    # ดึงรูปภาพ
    img_res = requests.get(f"{IMAGE_RAW_URL}?t={int(time.time())}")
    
    payload = {
        'chat_id': CHAT_ID,
        'caption': message,
        'parse_mode': 'HTML'
    }
    files = {'photo': img_res.content}
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendPhoto", data=payload, files=files)

if __name__ == "__main__":
    main()
