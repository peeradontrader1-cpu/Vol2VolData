import os
import requests
import pandas as pd
from datetime import datetime
import pytz  # สำหรับจัดการ Timezone

# ข้อมูลการเชื่อมต่อ (แนะนำให้ใช้ค่าเดิมที่คุณตั้งไว้)
TOKEN = "8738260894:AAGah4mPDvoUeLmiMTlzkGAlZaAqyP7b5o4"
CHAT_ID = "-1003709177186"

def get_summary():
    try:
        # 1. ตั้งค่าเวลาให้เป็นประเทศไทย (+7)
        tz_th = pytz.timezone('Asia/Bangkok')
        now_th = datetime.now(tz_th)
        time_str = now_th.strftime('%H:%M')
        date_str = now_th.strftime('%d %b %Y')

        # 2. ดึงข้อมูล Intraday
        url_intra = "https://raw.githubusercontent.com/peeradontrader1-cpu/Vol2VolData/main/IntradayData.txt"
        df_intra = pd.read_csv(url_intra, skiprows=2)
        intra_call = int(df_intra['Call'].sum())
        intra_put = int(df_intra['Put'].sum())
        intra_ratio = round(intra_put / intra_call, 2) if intra_call > 0 else 0
        
        # หา Top Active จาก Intraday
        df_intra['Total'] = df_intra['Call'] + df_intra['Put']
        top_intra = df_intra.loc[df_intra['Total'].idxmax()]

        # 3. ดึงข้อมูล OI
        url_oi = "https://raw.githubusercontent.com/peeradontrader1-cpu/Vol2VolData/main/OIData.txt"
        df_oi = pd.read_csv(url_oi, skiprows=2)
        oi_call = int(df_oi['Call'].sum())
        oi_put = int(df_oi['Put'].sum())

        # 4. จัดรูปแบบข้อความ (Caption)
        message = (
            f"📊 *GOLD UPDATE* | {time_str} น.\n"
            f"📅 ซีรีย์: {date_str}\n\n"
            f"📊 *GOLD INTRADAY*\n"
            f"────────────────\n"
            f"🟠 Put: {intra_put:,}\n"
            f"🔵 Call: {intra_call:,}\n"
            f"⚖️ Ratio (P/C): {intra_ratio}\n\n"
            f"📍 *TOP ACTIVE*\n"
            f"1️⃣ {int(top_intra['Strike'])} | {int(top_intra['Total']):,}\n"
            f"   └ P:{int(top_intra['Put'])} / C:{int(top_intra['Call'])}\n\n"
            f"📊 *GOLD OI*\n"
            f"────────────────\n"
            f"🟠 Put: {oi_put:,}\n"
            f"🔵 Call: {oi_call:,}\n"
            f"────────────────\n"
            f"✅ บันทึกเรียบร้อย"
        )
        return message
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

def send_to_telegram(caption_text):
    image_url = "https://raw.githubusercontent.com/peeradontrader1-cpu/Vol2VolData/main/Intraday%2BOI.png"
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHAT_ID,
        "photo": image_url,
        "caption": caption_text,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=payload)

if __name__ == "__main__":
    summary = get_summary()
    send_to_telegram(summary)
