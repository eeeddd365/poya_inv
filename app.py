import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 1. 頁面配置
st.set_page_config(page_title="寶雅庫存管理系統", layout="wide")

# 2. 資料庫連線
URL = "https://bxynxysqdfmnxazftzvk.supabase.co"
KEY = "sb_publishable_AxgVxJm1--U6NQJWD_N8ng_yHbBVV-S"
supabase: Client = create_client(URL, KEY)

# 3. 側邊導覽
with st.sidebar:
    st.title("🏪 POYA 管理中心")
    menu = st.radio("功能選單", ["📦 商品入庫 (含拍照)", "📤 商品出庫", "📋 庫存總覽"])

# --- 功能 1：商品入庫 (加入拍照功能) ---
if menu == "📦 商品入庫 (含拍照)":
    st.header("📦 商品入庫與拍照登記")
    
    # 加入相機元件
    img_file = st.camera_input("📸 請拍攝商品或條碼備查")
    if img_file:
        st.success("照片已暫存")

    with st.form("in_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            barcode_in = st.text_input("📋 商品條碼", placeholder="手動輸入或使用掃描槍")
            name = st.text_input("🏷️ 商品名稱")
        with col2:
            qty = st.number_input("🔢 入庫數量", min_value=1, value=1)
            location = st.text_input("📍 儲位位置")
        
        if st.form_submit_button("確認入庫"):
            if barcode_in:
                # 簡單檢查並存檔
                data = {"barcode": barcode_in, "name": name, "quantity": qty, "location": location}
                supabase.table("inventory").upsert(data, on_conflict="barcode").execute()
                st.success(f"✅ 條碼 {barcode_in} 處理完成")
                st.balloons()
            else:
                st.error("請輸入條碼")

# --- 功能 2：商品出庫 (修復錯誤) ---
elif menu == "📤 商品出庫":
    st.header("📤 商品出庫作業")
    search_q = st.text_input("🔍 搜尋商品條碼")
    
    if search_q:
        res = supabase.table("inventory").select("*").ilike("barcode", f"%{search_q}%").execute()
        if res.data:
            for item in res.data:
                st.info(f"品名：{item['name']} | 庫存：{item['quantity']} | 位置：{item['location']}")
                out_qty = st.number_input(f"出庫數量 ({item['barcode']})", min_value=1, max_value=item['quantity'], key=f"q_{item['barcode']}")
                if st.button(f"確認出庫 {item['barcode']}"):
                    new_q = item['quantity'] - out_qty
                    supabase.table("inventory").update({"quantity": new_q}).eq("barcode", item['barcode']).execute()
                    st.success("出庫成功！")
                    st.rerun()
        else:
            st.warning("查無此商品")

# --- 功能 3：庫存總覽 (修復排序錯誤) ---
elif menu == "📋 庫存總覽":
    st.header("📋 庫存總覽清單")
    # 移除 .order("created_at") 避免因為欄位不存在而報錯
    res = supabase.table("inventory").select("*").execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("目前無庫存資料")