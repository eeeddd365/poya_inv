import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 1. 頁面配置與美化
st.set_page_config(page_title="寶雅庫存管理系統", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    .stTextInput>div>div>input { background-color: #ffffff; }
    /* 卡片式樣式 */
    .inventory-card {
        padding: 15px;
        border-radius: 10px;
        background-color: white;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 15px;
        border-left: 5px solid #ff4b4b;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 資料庫連線 (使用你的 Key)
URL = "https://bxynxysqdfmnxazftzvk.supabase.co"
KEY = "sb_publishable_AxgVxJm1--U6NQJWD_N8ng_yHbBVV-S"

@st.cache_resource
def init_connection():
    return create_client(URL, KEY)

supabase = init_connection()

# 3. 導覽選單
with st.sidebar:
    st.title("🏪 POYA 管理中心")
    st.subheader("北屯東山二店")
    menu = st.radio("功能選單", ["📦 商品入庫", "📤 商品出庫", "📋 庫存總覽"])
    st.divider()
    st.info("💡 提示：手機版請點擊左上角「>」開啟選單")

# --- 功能 1：商品入庫 ---
if menu == "📦 商品入庫":
    st.header("📦 商品入庫登記")
    with st.form("in_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            barcode_in = st.text_input("📋 商品條碼 (必填)", placeholder="輸入或掃描條碼")
            name = st.text_input("🏷️ 商品名稱", placeholder="例如：我的美麗日記面膜")
            location = st.text_input("📍 儲位位置", placeholder="例如：A1-05-3")
        with col2:
            qty = st.number_input("🔢 入庫數量", min_value=1, value=1)
            note = st.text_area("📝 備註", placeholder="批號或效期說明")
        
        submit = st.form_submit_button("🔥 確認入庫儲存")
        
        if submit:
            if not barcode_in:
                st.error("❌ 請輸入條碼！")
            else:
                # 檢查是否已有該商品
                check = supabase.table("inventory").select("*").eq("barcode", barcode_in).execute()
                if check.data:
                    new_qty = check.data[0]['quantity'] + qty
                    supabase.table("inventory").update({
                        "quantity": new_qty, 
                        "name": name if name else check.data[0]['name'], 
                        "location": location if location else check.data[0]['location'], 
                        "note": note
                    }).eq("barcode", barcode_in).execute()
                    st.success(f"✅ 更新成功！現有總庫存：{new_qty}")
                else:
                    supabase.table("inventory").insert({
                        "barcode": barcode_in, 
                        "name": name, 
                        "quantity": qty, 
                        "location": location, 
                        "note": note
                    }).execute()
                    st.success("✨ 新商品入庫成功！")

# --- 功能 2：商品出庫 ---
elif menu == "📤 商品出庫":
    st.header("📤 商品出庫作業")
    search_q = st.text_input("🔍 搜尋關鍵字", placeholder="輸入條碼或名稱關鍵字...")
    
    if search_q:
        # 模糊搜尋
        res = supabase.table("inventory").select("*").or_(f"barcode.ilike.%{search_q}%,name.ilike.%{search_q}%").execute()
        if res.data:
            for item in res.data:
                with st.container():
                    st.markdown(f"""<div class="inventory-card">
                        <b>品名：{item['name']}</b><br>
                        條碼：{item['barcode']}<br>
                        📍 儲位：{item['location']} | 📦 現有庫存：{item['quantity']}
                    </div>""", unsafe_allow_html=True)
                    
                    # 建立每一行的出庫小表單
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        out_qty = st.number_input(f"取出數量", min_value=1, max_value=item['quantity'], key=f"qty_{item['barcode']}")
                    with c2:
                        # 修正後的關鍵點：使用 item['barcode']
                        if st.button("確認", key=f"btn_{item['barcode']}"):
                            new_total = item['quantity'] - out_qty
                            supabase.table("inventory").update({"quantity": new_total}).eq("barcode", item['barcode']).execute()
                            st.toast(f"✅ {item['name']} 已出庫 {out_qty} 件")
                            st.rerun()
        else:
            st.warning("查無此商品。")

# --- 功能 3：庫存總覽 ---
elif menu == "📋 庫存總覽":
    st.header("📋 庫存總覽報表")
    res = supabase.table("inventory").select("*").order("created_at", descending=True).execute()
    
    if res.data:
        df = pd.DataFrame(res.data)
        # 美化表格顯示
        display_df = df[['barcode', 'name', 'quantity', 'location', 'note']].copy()
        display_df.columns = ['條碼', '品名', '庫存量', '儲位', '備註']
        
        st.dataframe(display_df, use_container_width=True)
        
        # 下方的卡片式視圖
        st.subheader("🖼️ 快速視圖")
        cols = st.columns(3)
        for idx, item in enumerate(res.data):
            with cols[idx % 3]:
                st.markdown(f"""
                <div style="background-color:white; padding:10px; border-radius:10px; border:1px solid #ddd; margin-bottom:10px;">
                    <h4 style="margin:0;">📦 {item['name']}</h4>
                    <p style="color:gray; font-size:12px; margin:5px 0;">條碼: {item['barcode']}</p>
                    <b style="color:#ff4b4b;">數量: {item['quantity']}</b><br>
                    <small>📍 {item['location']}</small>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("目前資料庫為空，請先進行入庫。")