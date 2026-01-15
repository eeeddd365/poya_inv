import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, RTCConfiguration
import cv2
from pyzbar import pyzbar
from supabase import create_client, Client
import numpy as np

# 1. 介面優化
st.set_page_config(page_title="寶雅快速庫存 - 極速版", layout="centered")

st.markdown("""
    <style>
    /* 專業掃描框外框 */
    .scan-container {
        position: relative;
        border: 4px solid #00FF00;
        border-radius: 15px;
        overflow: hidden;
        margin-bottom: 20px;
    }
    /* 動態紅光掃描線 */
    .scan-line {
        position: absolute;
        top: 0; left: 0; width: 100%; height: 4px;
        background: rgba(255, 0, 0, 0.9);
        box-shadow: 0 0 15px 5px rgba(255, 0, 0, 0.6);
        animation: scan 1.5s linear infinite;
        z-index: 10;
    }
    @keyframes scan { 0% { top: 0%; } 100% { top: 100%; } }
    /* 掃描成功提示色 */
    .stSuccess { animation: pulse 0.5s; }
    @keyframes pulse { 0% { opacity: 0.5; } 100% { opacity: 1; } }
    </style>
    """, unsafe_allow_html=True)

# 2. 資料庫連線 (直接填入你的 Key)
SUPABASE_URL = "https://bxynxysqdfmnxazftzvk.supabase.co"
SUPABASE_KEY = "sb_publishable_AxgVxJm1--U6NQJWD_N8ng_yHbBVV-S"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 3. 強化版條碼處理器 (支援 QR Code + 各類條碼)
class BarcodeProcessor(VideoTransformerBase):
    def transform(self, frame):
        img = frame.to_ndarray(format="bgr24")
        
        # 轉換成灰階提高識別率
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # 增加對比度
        gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        # 掃描一維與二維條碼
        barcodes = pyzbar.decode(gray)
        
        for barcode in barcodes:
            barcode_data = barcode.data.decode("utf-8")
            
            # 存入 Session State 觸發前端更新
            if "last_barcode" not in st.session_state or st.session_state.last_barcode != barcode_data:
                st.session_state.last_barcode = barcode_data
            
            # 在畫面畫出偵測框
            (x, y, w, h) = barcode.rect
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 3)
            cv2.putText(img, "SUCCESS!", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
        return img

# 4. 主介面設計
st.title("⚡ 寶雅極速庫存系統")
st.caption("請對準商品條碼或 QR Code，掃描成功後會自動彈出表單")

# 初始化掃描結果
if "last_barcode" not in st.session_state:
    st.session_state.last_barcode = None

# 掃描區域
with st.container():
    st.markdown('<div class="scan-container"><div class="scan-line"></div>', unsafe_allow_html=True)
    webrtc_ctx = webrtc_streamer(
        key="fast-scanner",
        video_transformer_factory=BarcodeProcessor,
        rtc_configuration=RTCConfiguration(
            {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
        ),
        video_html_attrs={
            "playsInline": True, "autoPlay": True, "muted": True, "controls": False,
        },
        media_stream_constraints={
            "video": {
                "facingMode": "environment",
                "focusMode": "continuous",
                "width": {"ideal": 1280}, "height": {"ideal": 720}
            },
            "audio": False
        },
    )
    st.markdown('</div>', unsafe_allow_html=True)

# 5. 掃描後的連動反應 (這是快速建立的關鍵)
if st.session_state.last_barcode:
    barcode = st.session_state.last_barcode
    
    # 強力提示
    st.success(f"🎯 掃描成功！條碼編號：{barcode}")
    
    # 立即從資料庫抓取現有資料
    try:
        res = supabase.table("inventory").select("*").eq("barcode", barcode).execute()
        existing_item = res.data[0] if res.data else None
    except:
        existing_item = None

    # 快速填寫表單
    with st.expander("📝 點擊填寫庫存資訊", expanded=True):
        with st.form("inventory_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                item_name = st.text_input("📦 商品名稱", value=existing_item['name'] if existing_item else "")
                location = st.text_input("📍 儲位編號", value=existing_item['location'] if existing_item else "", placeholder="例如: B2-12")
            with col2:
                quantity = st.number_input("🔢 入庫數量", min_value=1, value=1)
                
            save_btn = st.form_submit_button("🔥 立即存檔")
            
            if save_btn:
                new_data = {
                    "barcode": barcode,
                    "name": item_name,
                    "quantity": quantity,
                    "location": location
                }
                if existing_item:
                    supabase.table("inventory").update(new_data).eq("barcode", barcode).execute()
                else:
                    supabase.table("inventory").insert(new_data).execute()
                
                st.balloons() # 撒花慶祝
                st.toast("資料已儲存到 Supabase！", icon="✅")
                # 重置掃描狀態，準備下一次掃描
                st.session_state.last_barcode = None
                st.rerun()

# 6. 底部的快速預覽
if st.checkbox("🔍 檢視庫存清單"):
    all_res = supabase.table("inventory").select("*").order("created_at", descending=True).limit(5).execute()
    if all_res.data:
        st.table(all_res.data)