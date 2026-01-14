import streamlit as st
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
from supabase import create_client, Client
from pyzbar.pyzbar import decode
import cv2
import numpy as np
from PIL import Image
import io

# --- 1. 初始化 Supabase (請替換為你的資訊) ---
SUPABASE_URL = "https://bxynxysqdfmnxazftzvk.supabase.co"
SUPABASE_KEY = "sb_publishable_AxgVxJm1--U6NQJWD_N8ng_yHbBVV-S"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="雲端庫存助手", layout="wide")

# --- 2. 自定義影像處理器 (自動偵測條碼) ---
class BarcodeProcessor(VideoProcessorBase):
    def __init__(self):
        self.last_barcode = None

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        barcodes = decode(img)
        for barcode in barcodes:
            (x, y, w, h) = barcode.rect
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            self.last_barcode = barcode.data.decode("utf-8")
        return frame

# --- 3. 功能函式 ---
def upload_image(barcode, image_data):
    """上傳照片至 Supabase Storage 並回傳 URL"""
    path = f"{barcode}.jpg"
    try:
        # 轉換為 Bytes
        img_byte_arr = io.BytesIO()
        image_data.save(img_byte_arr, format='JPEG')
        
        # 上傳 (upsert=True 代表若重複則覆蓋)
        supabase.storage.from_("photos").upload(
            path=path, file=img_byte_arr.getvalue(), 
            file_options={"content-type": "image/jpeg", "upsert": "true"}
        )
        return supabase.storage.from_("photos").get_public_url(path)
    except Exception as e:
        st.error(f"圖片上傳失敗: {e}")
        return None

# --- 4. 側邊欄選單 ---
st.sidebar.title("選單")
app_mode = st.sidebar.selectbox("切換功能", ["自動掃描與入庫", "庫存總表清單"])

# --- 5. 主程式邏輯 ---
if app_mode == "自動掃描與入庫":
    st.header("📷 即時條碼偵測")
    
    # 啟動相機
    ctx = webrtc_streamer(
        key="scanner",
        video_processor_factory=BarcodeProcessor,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"video": True, "audio": False},
    )

    if ctx.video_processor and ctx.video_processor.last_barcode:
        barcode_val = ctx.video_processor.last_barcode
        st.success(f"🔍 偵測到條碼：{barcode_val}")

        # 查詢資料庫
        res = supabase.table("inventory").select("*").eq("barcode", barcode_val).execute()
        
        if res.data:
            item = res.data[0]
            st.info(f"📦 已有名稱：{item['name']}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"📍 位置：{item['location']}")
                st.write(f"🔢 數量：{item['quantity']}")
                st.write(f"📝 備註：{item['note']}")
            with col2:
                if item['image_url']:
                    st.image(item['image_url'], width=300)
            
            # 快速編輯數量
            new_qty = st.number_input("更新數量", value=item['quantity'])
            if st.button("確認更新數量"):
                supabase.table("inventory").update({"quantity": new_qty}).eq("barcode", barcode_val).execute()
                st.rerun()
        else:
            st.warning("⚠️ 庫存無此資料，請填寫下方資訊建立新項目：")
            with st.form("add_new_item"):
                new_name = st.text_input("物品名稱")
                new_loc = st.text_input("存放位置")
                new_qty = st.number_input("初始數量", min_value=1, value=1)
                new_note = st.text_area("備註")
                new_photo = st.camera_input("拍攝物品照片作為記錄")
                
                if st.form_submit_button("儲存至雲端資料庫"):
                    img_url = ""
                    if new_photo:
                        img_url = upload_image(barcode_val, Image.open(new_photo))
                    
                    supabase.table("inventory").insert({
                        "barcode": barcode_val, "name": new_name,
                        "location": new_loc, "quantity": new_qty,
                        "note": new_note, "image_url": img_url
                    }).execute()
                    st.success("成功建立新庫存！")
                    st.rerun()

elif app_mode == "庫存總表清單":
    st.header("📋 目前所有庫存")
    res = supabase.table("inventory").select("*").execute()
    
    if res.data:
        for item in res.data:
            with st.expander(f"{item['name']} ({item['barcode']})"):
                c1, c2 = st.columns([1, 2])
                with c1:
                    if item['image_url']:
                        st.image(item['image_url'])
                with c2:
                    st.write(f"**位置:** {item['location']}")
                    st.write(f"**數量:** {item['quantity']}")
                    st.write(f"**備註:** {item['note']}")
                    if st.button(f"編輯 {item['barcode']}", key=item['barcode']):
                        st.info("編輯功能可在此擴充為彈窗或跳轉")
    else:
        st.write("目前資料庫空空如也。")