import os
import requests
import pandas as pd
from datetime import datetime
import pytz
import time
from io import StringIO
import re
import html
import traceback

# ดึงค่าจาก GitHub Secrets
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

BASE_URL = "https://raw.githubusercontent.com/pageth/Vol2VolData/main"

def get_summary():
    try:
        tz_th = pytz.timezone('Asia/Bangkok')
        now_th = datetime.now(tz_th)
        time_str = now_th.strftime('%H:%M')
        
        # ใส่ timestamp ป้องกันการติด Cache เพื่อให้ได้ข้อมูลล่าสุดเสมอ
        cache_buster = int(time.time())
        
        # 1. ดึงข้อมูล Raw สดใหม่จากต้นฉบับ
        res_intra_resp = requests.get(f"{BASE_URL}/IntradayData.txt?v={cache_buster}", timeout=10)
        res_oi_resp = requests.get(f"{BASE_URL}/OIData.txt?v={cache_buster}", timeout=10)

        if res_intra_resp.status_code != 200 or res_oi_resp.status_code != 200:
            print(f"❌ Failed to fetch raw data. Intraday: {res_intra_resp.status_code}, OI: {res_oi_resp.status_code}")
            return None

        res_intra_raw = res_intra_resp.text
        res_oi_raw = res_oi_resp.text
        
        # 2. สกัดชื่อซีรีย์จากบรรทัดแรก
        series_name = "N/A"
        lines = [line.strip() for line in res_intra_raw.split('\n') if line.strip()]
        if lines:
            series_match = re.search(r'^(.+?)\s+vs', lines[0])
            if series_match:
                series_name = series_match.group(1).strip()

        # 3. แปลงเป็น Dataframe
        df_i = pd.read_csv(StringIO(res_intra_raw), skiprows=2)
        df_o = pd.read_csv(StringIO(res_oi_raw), skiprows=2)
        
        df_i.columns = df_i.columns.str.strip()
        df_o.columns = df_o.columns.str.strip()

        required_cols = ['Strike', 'Put', 'Call']
        if not all(col in df_i.columns for col in required_cols):
            print(f"❌ Intraday Columns missing. Found: {list(df_i.columns)}")
            return None

        # --- [คำนวณ GOLD INTRADAY] ---
        p_in_total = int(df_i['Put'].sum())
        c_in_total = int(df_i['Call'].sum())
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

        # --- [จัดรูปแบบข้อความรายงาน] ---
        msg = f"📊 <b>GOLD UPDATE</b> | {time_str} น.\n"
        msg += f"🗓️ <b>ซีรีย์:</b> {html.escape(series_name)}\n\n"
        
        msg += f"📊 <b>GOLD INTRADAY</b>\n───────────────\n"
        msg += f"🟠 Put:  {p_in_total:,} (+{p_in_diff:,})\n"
        msg += f"🔵 Call: {c_in_total:,} (+{c_in_diff:,})\n"
        msg += f"⚖️ Ratio: 1 : {ratio}\n\n"
        
        msg += f"📍 <b>TOP ACTIVE</b>\n"
        for i, (_, row) in enumerate(top_i.iterrows(), 1):
            strike = int(row['Strike'])
            total = int(row['Total'])
            p_val = int(row['Put'])
            c_val = int(row['Call'])
            diff_val = c_val if c_val > 0 else p_val 
            
            icon = "1️⃣" if i == 1 else "2️⃣"
            msg += f"{icon} <b>{strike:,}</b> | {total:,} (+{diff_val:,})\n"
            msg += f"    └ P:{p_val:,} / C:{c_val:,}+{diff_val:,}\n"
            
        msg += f"───────────────\n📊 <b>GOLD OI</b>\n───────────────\n"
        msg += f"🟠 Put:  {p_oi_total:,}\n"
        msg += f"🔵 Call: {c_oi_total:,}\n\n"
        
        msg += f"📍 <b>TOP ACTIVE</b>\n"
        for i, (_, row) in enumerate(top_o.iterrows(), 1):
            strike = int(row['Strike'])
            total = int(row['Total'])
            p_val = int(row['Put'])
            c_val = int(row['Call'])
            
            icon = "1️⃣" if i == 1 else "2️⃣"
            msg += f"{icon} <b>{strike:,}</b> | {total:,}\n"
            msg += f"    └ P:{p_val:,} / C:{c_val:,}\n"
            
        msg += f"───────────────\n✅ บันทึกเรียบร้อย"
        return msg

    except Exception as e:
        print(f"❌ Error during data processing: {e}")
        traceback.print_exc()
        return None

def send_to_telegram(caption_text):
    api_photo_url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    api_message_url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    
    # ดึงรูปภาพต้นฉบับล่าสุดแบบสดใหม่โดยต่อ Cache Buster
    cache_buster = int(time.time())
    img_url = f"{BASE_URL}/Intraday%2BOI.png?v={cache_buster}"
    local_image_path = "Intraday_OI_latest.png"
    
    try:
        # 1. โหลดรูปภาพต้นฉบับอัปเดตล่าสุดมาเก็บชั่วคราว
        print("📥 Downloading latest image from source...")
        img_resp = requests.get(img_url, timeout=15)
        
        image_downloaded = False
        if img_resp.status_code == 200:
            with open(local_image_path, "wb") as f:
                f.write(img_resp.content)
            image_downloaded = True
            print("✅ Latest image downloaded successfully!")
        else:
            print(f"⚠️ Failed to download latest image (Status: {img_resp.status_code})")

        # 2. ส่งรูปพร้อมข้อความเข้า Telegram
        if image_downloaded and os.path.exists(local_image_path):
            print("📸 Sending latest Photo and Caption to Telegram...")
            with open(local_image_path, 'rb') as img_file:
                files = {'photo': img_file}
                payload = {
                    "chat_id": CHAT_ID,
                    "caption": caption_text,
                    "parse_mode": "HTML"
                }
                r = requests.post(api_photo_url, data=payload, files=files, timeout=20)
                print(f"Telegram Photo Status: {r.status_code}")
                if r.status_code != 200:
                    print(f"❌ Telegram Error (Photo): {r.text}")
                
                # ลบไฟล์ชั่วคราวหลังส่งเสร็จ
                img_file.close()
                os.remove(local_image_path)
                    
        else:
            # สำรอง: ถ้ารูปโหลดไม่ได้จริงๆ ให้ส่งข้อความออกไปก่อนเพื่อไม่ให้ขาดช่วง
            print("⚠️ Sending text only...")
            payload_text = {
                "chat_id": CHAT_ID,
                "text": caption_text,
                "parse_mode": "HTML"
            }
            r = requests.post(api_message_url, data=payload_text, timeout=10)
            print(f"Telegram Text-Only Status: {r.status_code}")
            
    except Exception as e:
        print(f"❌ Error sending to Telegram: {e}")

if __name__ == "__main__":
    if TOKEN and CHAT_ID:
        summary_text = get_summary()
        if summary_text:
            send_to_telegram(summary_text)
        else:
            print("❌ Failed to generate summary text. Check data format.")
    else:
        print("❌ Secrets Missing: Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")
