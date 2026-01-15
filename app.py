import streamlit as st
from supabase import create_client, Client

# 1. 頁面配置
st.set_page_config(page_title="寶雅庫存系統-北屯東山二", layout="centered")

# 2. 資料庫連線 (請確認這兩行資訊正確)
URL = "https://bxynxysqdfmnxazftzvk.supabase.co"
KEY = "sb_publishable_AxgVxJm1--U6NQJWD_N8ng_yHbBVV-S"
supabase: Client = create_client(URL, KEY)

# 3. 側邊選單
menu = st.sidebar.radio("選單", ["入庫與拍照", "商品出庫", "庫存總覽"])

# --- 功能 1：入庫 ---
if menu == "入庫與拍照":
    st.header("📦 入庫登記")
    # 手機拍照功能
    st.camera_input("📸 拍商品照片", key="cam")
    
    with st.form("in_form", clear_on_submit=True):
        barcode = st.text_input("📋 條碼 (請輸入或掃描)")
        name = st.text_input("🏷️ 品名")
        qty = st.number_input("🔢 數量", min_value=1, value=1)
        loc = st.text_input("📍 儲位")
        
        if st.form_submit_button("確認儲存"):
            if barcode:
                # 檢查是否存在並更新，或直接新增
                res = supabase.table("inventory").select("*").eq("barcode", barcode).execute()
                if res.data:
                    new_q = res.data[0]['quantity'] + qty
                    supabase.table("inventory").update({"quantity": new_q, "name": name, "location": loc}).eq("barcode", barcode).execute()
                    st.success(f"已更新！新庫存：{new_q}")
                else:
                    supabase.table("inventory").insert({"barcode": barcode, "name": name, "quantity": qty, "location": loc}).execute()
                    st.success("新商品已存檔！")
            else:
                st.error("條碼不能為空")

# --- 功能 2：出庫 ---
elif menu == "商品出庫":
    st.header("📤 出庫作業")
    s_barcode = st.text_input("🔍 搜尋條碼")
    if s_barcode:
        res = supabase.table("inventory").select("*").eq("barcode", s_barcode).execute()
        if res.data:
            item = res.data[0]
            st.info(f"品名：{item['name']} | 現有庫存：{item['quantity']}")
            out_q = st.number_input("出庫數量", min_value=1, max_value=item['quantity'])
            if st.button("確認扣除庫存"):
                new_q = item['quantity'] - out_q
                supabase.table("inventory").update({"quantity": new_q}).eq("barcode", s_barcode).execute()
                st.success("出庫成功！")
                st.rerun()
        else:
            st.warning("查無此商品")

# --- 功能 3：總覽 ---
elif menu == "庫存總覽":
    st.header("📋 庫存清單")
    res = supabase.table("inventory").select("*").execute()
    if res.data:
        st.table(res.data)
    else:
        st.write("目前沒有資料")