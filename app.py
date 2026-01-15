import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, RTCConfiguration
import cv2
from pyzbar import pyzbar
from supabase import create_client, Client
import numpy as np

# 1. 頁面設定
st.set_page_config(page_title="寶雅快速庫存系統", layout="centered")

# 專業掃描器 CSS
st.markdown("""
    <style>
    .scan-container {
        position: relative;
        border: 4px solid #00FF00;
        border-radius: 15px;
        overflow: hidden;
        margin-bottom: 20px;
    }
    .scan-line {
        position: absolute;
        top: 0; left: 0; width: 100%; height: 3px;
        background: rgba(255, 0, 0, 0.8);
        box-shadow: 0 0 10px 3px rgba(255, 0, 0, 0.5);
        animation: scan 2.5s linear infinite;
        z-index: 10;
    }
    @keyframes scan { 0% { top: 0%; } 100% { top: 100%; } }
    </style>
    """, unsafe_allow_html=True)

# 2. 直接設定 Supabase 連線資訊
# 注意：因為你的 Repo 是 Public，建議之後移到 Streamlit Secrets
SUPABASE_URL = "https://bxynxysqdfmnxazftzvk.supabase.co"
SUPABASE_KEY = "sb_publishable_AxgVxJm1--U6NQJWD_N8ng_yHbBVV-S"

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error(f"❌ 資料庫連線失敗: {e}")
    st.stop()

# 3. 條碼處理器
class BarcodeProcessor(VideoTransformerBase):
    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        barcodes = pyzbar.decode(img)
        for barcode in barcodes:
            barcode_data = barcode.data.decode("utf-8")
            if "last_barcode" not in st.session_state or st.session_state.last_barcode != barcode_data:
                st.session_state.last_barcode = barcode_data
            (x, y, w, h) = barcode.rect
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        return img

# 4. 主介面
st.title("📦 寶雅快速庫存掃描器")

with st.container():
    st.markdown('<div class="scan-container"><div class="scan-line"></div>', unsafe_allow_html=True)
    webrtc_ctx = webrtc_streamer(
        key="poya-scanner",
        video_transformer_factory=BarcodeProcessor,
        rtc_configuration=RTCConfiguration(
            {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
        ),
        video_html_attrs={
            "playsInline": True,
            "autoPlay": True,
            "muted": True,
            "controls": False,
        },
        media_stream_constraints={
            "video": {
                "facingMode": "environment",
                "focusMode": "continuous",
                "width": {"ideal": 1280},
                "height": {"ideal": 720}
            },
            "audio": False
        },
    )
    st.markdown('</div>', unsafe_allow_html=True)

# 5. 掃描結果處理
if "last_barcode" in st.session_state and st.session_state.last_barcode:
    barcode = st.session_state.last_barcode
    st.success(f"✅ 已偵測條碼：{barcode}")
    
    # 查詢現有資料
    try:
        res = supabase.table("inventory").select("*").eq("barcode", barcode).execute()
        existing_item = res.data[0] if res.data else None
    except:
        existing_item = None

    with st.form("inventory_form"):
        st.subheader("📝 庫存登記")
        item_name = st.text_input("商品名稱", value=existing_item['name'] if existing_item else "")
        quantity = st.number_input("入庫數量", min_value=1, value=1)
        location = st.text_input("儲位編號", value=existing_item['location'] if existing_item else "")
        
        if st.form_submit_button("儲存資料"):
            data = {"barcode": barcode, "name": item_name, "quantity": quantity, "location": location}
            if existing_item:
                supabase.table("inventory").update(data).eq("barcode", barcode).execute()
                st.success("🔄 已更新資料！")
            else:
                supabase.table("inventory").insert(data).execute()
                st.success("✨ 已新增資料！")
            st.session_state.last_barcode = None

# 6. 庫存清單
if st.checkbox("顯示目前庫存總表"):
    all_data = supabase.table("inventory").select("*").execute()
    if all_data.data:
        st.table(all_data.data)