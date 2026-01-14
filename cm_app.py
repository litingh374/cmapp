import streamlit as st
import pandas as pd
import io
from datetime import date

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="建案行政流程控管系統",
    page_icon="🏗️",
    layout="wide"
)

# --- CSS 優化 (讓鎖定的狀態更明顯) ---
st.markdown("""
<style>
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    .locked-stage {
        padding: 15px;
        border-radius: 5px;
        background-color: #ffebee;
        border: 1px solid #ffcdd2;
        color: #c62828;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏗️ 建案開工至放樣勘驗 - 流程控管系統")
st.markdown("### 依據：建照領取 ➡️ 開工申報 ➡️ 施工計畫 ➡️ 導溝/放樣勘驗")

# --- 2. 核心資料結構 (SOP) ---
# 定義每個階段的清單，這對應到您的 PDF 內容
def get_initial_data():
    return {
        "stage_0": [ # 關鍵前置
            {"item": "建築師-建照執照領取", "doc": "建照正本", "owner": "建築師", "done": False, "note": "必須完成才能啟動後續"},
            {"item": "建照圖說核對", "doc": "建築/結構/水電圖", "owner": "工務部", "done": False, "note": "確認圖說版本與建照一致"}
        ],
        "stage_1": [ # 開工申報準備 (PDF中的開工前準備)
            {"item": "空氣污染防制費(首期)申報", "doc": "空汙費申報書、合約", "owner": "環保局", "done": False, "note": ""},
            {"item": "營建廢棄物處理計畫書", "doc": "廢棄物計畫書、土資場同意書", "owner": "環保局", "done": False, "note": ""},
            {"item": "逕流廢水削減計畫", "doc": "削減計畫書", "owner": "環保局", "done": False, "note": ""},
            {"item": "鄰房現況鑑定申請", "doc": "鑑定申請書、繳費", "owner": "技師公會", "done": False, "note": "開工前需完成外業"},
            {"item": "五大管線查詢", "doc": "管線圖", "owner": "各管線單位", "done": False, "note": ""},
            {"item": "建管開工申報(無紙化)", "doc": "承造/監造證書、保險單", "owner": "建管處", "done": False, "note": "正式掛號"}
        ],
        "stage_2": [ # 施工計畫
            {"item": "施工計畫書撰寫", "doc": "施工計畫書初稿", "owner": "工務部", "done": False, "note": "含防災、交維"},
            {"item": "施工計畫說明會(公會)", "doc": "簡報資料", "owner": "外審委員", "done": False, "note": "需召開說明會"},
            {"item": "施工計畫書核定", "doc": "核定函", "owner": "建管處", "done": False, "note": "取得核備文號"}
        ],
        "stage_3": [ # 導溝勘驗 (針對連續壁或擋土措施)
            {"item": "導溝單元劃分確認", "doc": "單元分割圖", "owner": "工地/廠商", "done": False, "note": ""},
            {"item": "導溝施工與檢測", "doc": "自主檢查表", "owner": "工地", "done": False, "note": ""},
            {"item": "導溝勘驗申報", "doc": "勘驗申請書、照片", "owner": "建管處/公會", "done": False, "note": "需技師簽證"}
        ],
        "stage_4": [ # 放樣勘驗 (正式結構體放樣)
            {"item": "基地鑑界", "doc": "土地複丈成果圖", "owner": "地政事務所", "done": False, "note": "確認界址"},
            {"item": "基準點/水準點引測", "doc": "測量報告", "owner": "測量廠商", "done": False, "note": ""},
            {"item": "放樣勘驗申報", "doc": "勘驗申請書、測量成果", "owner": "建管處", "done": False, "note": "這一步完成後才算正式進入結構體"}
        ]
    }

# 初始化 Session State
if "project_data" not in st.session_state:
    st.session_state.project_data = get_initial_data()

data = st.session_state.project_data

# --- 3. 側邊欄與重置 ---
with st.sidebar:
    st.header("📝 專案資訊")
    st.text_input("專案名稱", value="範例建案")
    
    st.divider()
    
    # 這裡顯示一個全域狀態
    # 檢查建照是否完成
    permit_done = all(item['done'] for item in data['stage_0'])
    if permit_done:
        st.success("✅ 建照已領取 (流程解鎖)")
    else:
        st.error("⛔ 建照尚未領取 (流程鎖定)")
        
    st.divider()
    if st.button("🔄 重置所有進度"):
        st.session_state.project_data = get_initial_data()
        st.rerun()

# --- 4. 邏輯控制函數 ---
def render_task_list(stage_key, is_locked=False):
    """
    用來渲染每一個階段的清單
    is_locked: 如果為 True，則所有勾選框都不能按
    """
    df = pd.DataFrame(data[stage_key])
    
    if is_locked:
        st.markdown('<div class="locked-stage">⚠️ 此階段鎖定中：請先完成上一階段之關鍵項目（如建照領取、計畫核定等）。</div>', unsafe_allow_html=True)
    
    # 遍歷每一個項目並顯示
    for i, row in df.iterrows():
        col1, col2, col3, col4 = st.columns([0.5, 3, 3, 2])
        
        # Checkbox (狀態)
        with col1:
            # 唯一的 Key 是確保 streamlit 分得清楚每個勾選框
            checked = st.checkbox(
                "", 
                value=row['done'], 
                key=f"{stage_key}_{i}", 
                disabled=is_locked # 這裡就是鎖定機制的關鍵
            )
            # 即時更新資料
            data[stage_key][i]['done'] = checked
        
        # 顯示內容
        with col2:
            st.write(f"**{row['item']}**")
        with col3:
            st.caption(f"📄 {row['doc']}")
        with col4:
            # 備註欄位 (就算是鎖定狀態，也允許使用者看，但不一定給寫，這裡我設為可寫方便筆記，但不會存檔進流程邏輯)
            new_note = st.text_input(
                "備註", 
                value=row['note'], 
                key=f"note_{stage_key}_{i}",
                label_visibility="collapsed",
                disabled=is_locked
            )
            data[stage_key][i]['note'] = new_note
        
        st.divider()

# --- 5. 主畫面流程 ---

# 進度條計算
total_stages = 5
current_stage = 0
if permit_done: current_stage += 1 # 建照拿到了，進入開工準備
if permit_done and all(i['done'] for i in data['stage_1']): current_stage += 1 # 開工準備完了，進施工計畫
if current_stage >= 2 and all(i['done'] for i in data['stage_2']): current_stage += 1 # 計畫完了，進導溝
if current_stage >= 3 and all(i['done'] for i in data['stage_3']): current_stage += 1 # 導溝完了，進放樣

st.progress(current_stage / total_stages, text=f"目前流程進度：第 {current_stage + 1} 階段")

# 分頁顯示
tab0, tab1, tab2, tab3, tab4 = st.tabs([
    "0. 建築師作業 (建照)", 
    "1. 開工申報準備", 
    "2. 施工計畫", 
    "3. 導溝勘驗", 
    "4. 放樣勘驗"
])

# === Tab 0: 建築師作業 (源頭) ===
with tab0:
    st.subheader("🔑 階段零：建造執照領取")
    st.info("此階段為整個系統的鑰匙，勾選完成後，後續欄位才會解鎖。")
    render_task_list("stage_0", is_locked=False) # 這一關永遠不鎖

# === Tab 1: 開工申報準備 ===
with tab1:
    st.subheader("📋 階段一：開工申報相關行政流程")
    # 判斷邏輯：如果 Tab 0 (Stage 0) 沒做完，這裡就鎖起來
    is_locked_1 = not all(item['done'] for item in data['stage_0'])
    render_task_list("stage_1", is_locked=is_locked_1)

# === Tab 2: 施工計畫 ===
with tab2:
    st.subheader("📘 階段二：施工計畫書製作與審查")
    # 判斷邏輯：通常要開工申報準備得差不多，或至少建照要有
    # 這裡依照您的嚴格邏輯，假設必須先把 "開工申報準備" 完成才能專心跑計畫? 
    # 或者只要有建照就可以跑計畫? 
    # 依照實務，通常有建照就可以開始寫計畫，但這裡我先設為「建照拿到」即可解鎖，
    # 若您希望「開工申報項目全完」才解鎖，可改成 `is_locked=not all(item['done'] for item in data['stage_1'])`
    is_locked_2 = not all(item['done'] for item in data['stage_0']) 
    render_task_list("stage_2", is_locked=is_locked_2)

# === Tab 3: 導溝勘驗 ===
with tab3:
    st.subheader("🚧 階段三：導溝勘驗 (連續壁/擋土)")
    st.info("需確認施工計畫已核定，且開工申報已完成。")
    # 邏輯：必須「施工計畫核定」且「開工申報項目」都完成
    stage_1_done = all(item['done'] for item in data['stage_1'])
    stage_2_done = all(item['done'] for item in data['stage_2'])
    is_locked_3 = not (stage_1_done and stage_2_done)
    render_task_list("stage_3", is_locked=is_locked_3)

# === Tab 4: 放樣勘驗 ===
with tab4:
    st.subheader("📐 階段四：放樣勘驗")
    # 邏輯：導溝勘驗完成後
    stage_3_done = all(item['done'] for item in data['stage_3'])
    is_locked_4 = not stage_3_done
    render_task_list("stage_4", is_locked=is_locked_4)

# --- 6. 匯出 Excel ---
st.write("---")
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    # 把所有階段的資料合併成一個 Sheet 比較好讀
    all_rows = []
    for k, v in data.items():
        for item in v:
            item['階段代號'] = k
            all_rows.append(item)
    
    df_export = pd.DataFrame(all_rows)
    # 調整欄位順序
    df_export = df_export[["階段代號", "item", "doc", "owner", "done", "note"]]
    df_export.columns = ["階段", "作業項目", "應備文件", "承辦單位", "完成狀態", "備註"]
    
    df_export.to_excel(writer, index=False, sheet_name='工程流程總表')
    
    # 格式化
    workbook = writer.book
    worksheet = writer.sheets['工程流程總表']
    format_wrap = workbook.add_format({'text_wrap': True})
    worksheet.set_column('B:B', 30, format_wrap) # 項目
    worksheet.set_column('C:C', 40, format_wrap) # 文件

st.download_button(
    label="📥 下載完整流程 Excel",
    data=buffer.getvalue(),
    file_name=f"工程流程控管_{date.today()}.xlsx",
    mime="application/vnd.ms-excel"
)