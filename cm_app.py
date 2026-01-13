import streamlit as st
import pandas as pd
from datetime import date, timedelta

# --- 1. 基礎設定 ---
st.set_page_config(page_title="建管流程標準化系統", page_icon="🏗️", layout="wide")

st.title("🏗️ 各縣市建管流程標準化系統")
st.markdown("請選擇案件所在地區，系統將自動載入標準流程樣板供您追蹤。")

# --- 2. 定義標準樣板資料庫 (SOP) ---
# 這裡就是您的「知識庫」，您可以依據公司經驗隨時修改這裡的內容
def get_template_data(city):
    
    # 通用欄位結構
    columns = ["類別", "作業項目", "需準備文件/物品", "承辦單位/對象", "預計天數", "狀態", "備註"]
    
    if city == "台北市":
        data = [
            # 類別, 項目, 文件, 單位, 天數, 完成與否, 備註
            ["行政程序", "掛號申請", "申請書、圖說、謄本、簽證", "北市建管處 (市府路)", 14, False, "需預約掛號"],
            ["行政程序", "建照審查", "建築/結構/水電圖說", "建管處施工科", 30, False, "注意抽查項目"],
            ["工地現場", "拆除前會勘", "現況照片、拆除計畫", "建管處/環保局", 7, False, "需提前5日通知"],
            ["工地現場", "施工圍籬架設", "綠美化帆布、警示燈", "工地現場", 5, False, "需符合北市美化規範"],
            ["工地現場", "放樣勘驗", "經緯儀、測量報告", "建管處/技師公會", 3, False, "需技師到場"],
        ]
    elif city == "新北市":
        data = [
            ["行政程序", "建造執照掛號", "申請書、土地同意書", "新北工務局 (中山路)", 20, False, "協審制度"],
            ["行政程序", "環保逕流廢水申報", "廢水削減計畫書", "新北環保局", 10, False, "開工前完成"],
            ["工地現場", "開工前鄰房現況鑑定", "鑑定報告書", "鑑定公會", 30, False, "避免日後糾紛"],
            ["工地現場", "假設工程申報", "施工計畫書、安衛計畫", "工務局施工科", 14, False, "含鷹架/圍籬"],
            ["工地現場", "一樓版勘驗", "鋼筋無輻射證明、混凝土單", "工務局/公會", 2, False, "無紙化申報"],
        ]
    else: # 台中或其他地區 (範例)
        data = [
            ["行政程序", "建照申請", "基本圖說", "台中都發局", 25, False, ""],
            ["工地現場", "開工申報", "施工計畫", "都發局營造科", 7, False, "需繳空汙費"],
        ]

    # 轉成 DataFrame
    df = pd.DataFrame(data, columns=columns)
    return df

# --- 3. 側邊欄：控制面板 ---
with st.sidebar:
    st.header("📍 專案設定")
    
    # 選擇地區
    selected_city = st.selectbox("選擇案件地區", ["台北市", "新北市", "台中市(範例)"])
    
    # 載入按鈕
    st.info("切換地區後，請按下按鈕載入樣板👇")
    if st.button("📥 載入/重置 標準流程", type="primary"):
        # 將樣板資料存入 Session State (暫存記憶體)
        st.session_state.df_tasks = get_template_data(selected_city)
        st.success(f"已載入 {selected_city} 標準樣板！")

# --- 4. 初始化資料 (第一次打開網頁時) ---
if "df_tasks" not in st.session_state:
    st.session_state.df_tasks = get_template_data("台北市") # 預設載入台北

# --- 5. 主畫面：數據統計與清單 ---

# 計算進度
current_df = st.session_state.df_tasks
total_tasks = len(current_df)
completed_tasks = len(current_df[current_df["狀態"] == True])
pending_tasks = total_tasks - completed_tasks
progress = completed_tasks / total_tasks if total_tasks > 0 else 0

# 顯示頂部儀表板
col1, col2, col3 = st.columns(3)
col1.metric("總作業項目", f"{total_tasks} 項")
col2.metric("待辦事項", f"{pending_tasks} 項", delta=f"-{completed_tasks} 已完成", delta_color="inverse")
col3.markdown(f"**目前總進度**")
col3.progress(progress)

st.divider()

# --- 6. 核心功能：可編輯的清單 ---
st.subheader(f"📋 {selected_city} - 建管與工地執行清單")
st.caption("您可以直接修改內容、勾選完成狀態，或新增特殊事項。")

# 設定欄位編輯屬性
column_cfg = {
    "類別": st.column_config.SelectboxColumn("類別", options=["行政程序", "工地現場", "圖說繪製"], width="medium"),
    "作業項目": st.column_config.TextColumn("作業項目", width="large", required=True),
    "需準備文件/物品": st.column_config.TextColumn("需準備文件/物品", width="large"),
    "承辦單位/對象": st.column_config.SelectboxColumn("送件單位", options=["建管處", "都發局", "環保局", "公會", "工地現場"], width="medium"),
    "預計天數": st.column_config.NumberColumn("天數", format="%d 天"),
    "狀態": st.column_config.CheckboxColumn("完成?", help="勾選代表已完成"),
}

# 顯示表格
edited_df = st.data_editor(
    current_df,
    column_config=column_cfg,
    num_rows="dynamic", # 允許新增刪除
    use_container_width=True,
    key="task_editor"
)

# 當使用者在表格中編輯後，同步更新 session_state，這樣進度條才會動
if not edited_df.equals(current_df):
    st.session_state.df_tasks = edited_df
    st.rerun() # 強制重新整理頁面以更新上方進度條

# --- 7. 分類檢視 (篩選器) ---
st.write("---")
st.subheader("🔍 分類檢視")

tab1, tab2, tab3 = st.tabs(["🔴 未完成項目", "🏢 僅看行政程序", "🚧 僅看工地現場"])

with tab1:
    # 篩選出未完成的
    todo_df = edited_df[edited_df["狀態"] == False]
    if todo_df.empty:
        st.success("太棒了！所有項目皆已完成。")
    else:
        st.dataframe(todo_df[["作業項目", "需準備文件/物品", "承辦單位/對象"]], use_container_width=True)

with tab2:
    admin_df = edited_df[edited_df["類別"] == "行政程序"]
    st.dataframe(admin_df, use_container_width=True)

with tab3:
    site_df = edited_df[edited_df["類別"] == "工地現場"]
    st.dataframe(site_df, use_container_width=True)