import os
import requests
import pandas as pd
from datetime import datetime
import pytz
import time
from io import StringIO
import re

# ดึงค่าจาก GitHub Secrets
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def get_summary():
    try:
        tz_th = pytz.timezone('Asia/Bangkok')
        now_th = datetime.now(tz_th)
        time_str = now_th.strftime('%H:%M')
        
        cache_buster = int(time.time())
        base_url = "https://raw.githubusercontent.com/pageth/Vol2VolData/main"
        
        # ดึงข้อมูล Raw แบบสดใหม่
        res_intra_raw = requests.get(f"{base_url}/IntradayData.txt?v={cache_buster}").text
        res_oi_raw = requests.get(f"{base_url}/OIData.txt?v={cache_buster}").text
        
        # สกัดชื่อซีรีย์จากบรรทัดแรก (เช่น 19 Mar 2026)
        series_match = re.search(r'^(.+?)\s+vs', res_intra_raw.split('\n')[0])
        series_name = series_match.group(1) if series_match else "N/A"

        # อ่านข้อมูลโดยข้าม 2 บรรทัดแรก (Header ของไฟล์)
        df_i = pd.read_csv(StringIO(res_intra_raw), skiprows=2)
        df_o = pd.read_csv(StringIO(res_oi_raw), skiprows=2)
        
        # --- [คำนวณ GOLD INTRADAY] ---
        p_in_total = int(df_i['Put'].sum())
        c_in_total = int(df_i['Call'].sum())
        # ดึงค่าล่าสุด (บรรทัดสุดท้าย) มาเป็นค่า Diff
        p_in_diff = int(df_i['Put'].iloc[-1]) if not df_i.empty else 0
        c_in_diff = int(df_i['Call'].iloc[-1]) if not df_i.empty else 0
        ratio = round(c_in_total / p_in_total, 1) if p_in_total > 0 else 0
        
        df_i['Total'] = df_i['Put'] + df_i['Call']
        top_i = df_i.nlargest(2, 'Total')

        # --- [คำนวณ GOLD OI] ---
        p_oi_total = int(df_o['Put'].sum())
        c_oi_total = int(df_o['Call'].sum())
        df_o['Total'] = df_o['Put'] + df_o['Call']
        top_o = df_o.nlargest(2, 'Total')

        # --- [จัดรูปแบบข้อความตามตัวอย่าง] ---
        msg = f"📊 GOLD UPDATE | {time_str} น.\n"
        msg += f"🗓️ ซีรีย์: {series_name}\n\n"
        
        msg += f"📊 GOLD INTRADAY\n───────────────\n"
        msg += f"🟠 Put:  {p_in_total:,} (+{p_in_diff})\n"
        msg += f"🔵 Call: {c_in_total:,} (+{c_in_diff})\n"
        msg += f"⚖️ Ratio: 1 : {ratio}\n\n"
        
        msg += f"📍 TOP ACTIVE\n"
        for i, (_, row) in enumerate(top_i.iterrows(), 1):
            strike = int(row['Strike'])
            total = int(row['Total'])
            p_val = int(row['Put'])
            c_val = int(row['Call'])
            # สมมติค่า Diff ของ Strike นั้นๆ คือค่าที่โหลดมาล่าสุดในแถว
            diff_val = c_val if c_val > 0 else p_val 
            
            icon = "1️⃣" if i == 1 else "2️⃣"
            msg += f"{icon} {strike} | {total:,} (+{diff_val})\n"
            msg += f"    └ P:{p_val:,} / C:{c_val:,}+{diff_val}\n"
            
        msg += f"───────────────\n📊 GOLD OI\n───────────────\n"
        msg += f"🟠 Put:  {p_oi_total:,}\n"
        msg += f"🔵 Call: {c_oi_total:,}\n\n"
        
        msg += f"📍 TOP ACTIVE\n"
        for i, (_, row) in enumerate(top_o.iterrows(), 1):
            strike = int(row['Strike'])
            total = int(row['Total'])
            p_val = int(row['Put'])
            c_val = int(row['Call'])
            
            icon = "1️⃣" if i == 1 else "2️⃣"
            msg += f"{icon} {strike} | {total:,}\n"
            msg += f"    └ P:{p_val:,} / C:{c_val:,}\n"
            
        msg += f"───────────────\n✅ บันทึกเรียบร้อย"
        return msg
    except Exception as e:
        print(f"Error during calculation: {e}")
        return None

def send_to_telegram(caption_text):
    # ดึงรูปภาพพร้อม Cache Buster
    img_url = f"https://raw.githubusercontent.com/pageth/Vol2VolData/main/Intraday%2BOI.png?v={int(time.time())}"
    api_url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    
    payload = {
        "chat_id": CHAT_ID,
        "photo": img_url,
        "caption": caption_text,
        "parse_mode": "HTML" # ใช้ HTML เพื่อให้เส้นคั่นแสดงผลได้เสถียร
    }
    
    try:
        r = requests.post(api_url, data=payload)
        print(f"Telegram Response: {r.status_code}")
    except Exception as e:
        print(f"Error sending to Telegram: {e}")

if __name__ == "__main__":
    if TOKEN and CHAT_ID:
        summary_text = get_summary()
        if summary_text:
            send_to_telegram(summary_text)
    else:
        print("❌ Secrets Missing: Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
