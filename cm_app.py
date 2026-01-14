import streamlit as st
import pandas as pd
import io
from datetime import date

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="建案行政SOP系統",
    page_icon="🏗️",
    layout="wide"
)

# --- CSS 優化 (綠色勾選框) ---
st.markdown("""
<style>
    /* 強制將 Checkbox 打勾後的顏色改為綠色 (工程 Pass 色) */
    div[data-testid="stCheckbox"] label span[data-checked="true"] {
        background-color: #2E7D32 !important;
        border-color: #2E7D32 !important;
    }
    /* 進度條顏色 */
    .stProgress > div > div > div > div { background-color: #2E7D32; }
    
    /* 鎖定狀態 */
    .locked-stage { 
        padding: 15px; border-radius: 5px; background-color: #f5f5f5; 
        border: 1px solid #ddd; color: #888; font-style: italic;
    }
    /* 資訊框 */
    .info-box {
        background-color: #e3f2fd; padding: 10px; border-radius: 5px; border-left: 5px solid #2196f3;
        font-size: 0.9em; margin-bottom: 5px;
    }
    .warning-box {
        background-color: #fff3e0; padding: 10px; border-radius: 5px; border-left: 5px solid #ff9800;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏗️ 建案開工至放樣 SOP 控管系統")

# --- 2. 核心資料庫 ---
def get_initial_sop():
    return {
        "stage_0": [
            {"item": "建築師-建照執照領取", "dept": "建築師事務所", "timing": "【專案啟動】", "docs": "1. 建造執照正本\n2. 核准圖說", "details": "需確認建照號碼、起造人名稱無誤。", "done": False, "note": ""},
        ],
        "stage_1": [ 
            {"item": "空氣污染防制費 (首期) 申報", "dept": "環保局 (空噪科)", "timing": "【開工前】", "docs": "1. 空汙費申報書\n2. 建照影本", "details": "未繳納無法申報開工。", "done": False, "note": ""},
            {"item": "營建工程廢棄物處理計畫書", "dept": "環保局 / 工務局", "timing": "【開工前】", "docs": "1. 廢棄物處置計畫書\n2. 土資場同意書", "details": "需確認土資場容量。", "done": False, "note": ""},
            {"item": "逕流廢水削減計畫", "dept": "環保局 (水保科)", "timing": "【開工前】", "docs": "1. 削減計畫書", "details": "規劃工區排水。", "done": False, "note": ""},
            {"item": "現況調查 (鄰房鑑定申請)", "dept": "技師公會", "timing": "【拆除/開工前】", "docs": "1. 鑑定申請書", "details": "務必於動工前完成。", "done": False, "note": ""},
            {"item": "五大管線查詢", "dept": "管線單位", "timing": "【規劃階段】", "docs": "1. 現況圖", "details": "確認管線分布。", "done": False, "note": ""},
            {"item": "建管開工申報 (正式掛號)", "dept": "建管處", "timing": "【建照後6個月內】", "docs": "1. 開工申請書\n2. 證書影本\n3. 保險單", "details": "逾期建照作廢。", "done": False, "note": ""}
        ],
        "stage_2": [ 
            {"item": "施工計畫書 (含交通/防災)", "dept": "建管處", "timing": "【放樣前】", "docs": "1. 施工計畫書", "details": "特殊結構需外審。", "done": False, "note": ""},
            {"item": "職業安全衛生管理計畫", "dept": "勞檢處", "timing": "【開工前】", "docs": "1. 安衛計畫書", "details": "危評審查。", "done": False, "note": ""}
        ],
        "stage_3": [ 
            {"item": "導溝施工與單元劃分", "dept": "工地現場", "timing": "【連續壁前】", "docs": "1. 單元圖", "details": "確認鋪面。", "done": False, "note": ""},
            {"item": "導溝勘驗申報", "dept": "建管處", "timing": "【計畫核定後】", "docs": "1. 申請書\n2. 照片", "details": "需完成圍籬。", "done": False, "note": ""}
        ],
        "stage_4": [ 
            {"item": "基地鑑界 (複丈)", "dept": "地政事務所", "timing": "【放樣前】", "docs": "1. 複丈申請書", "details": "確認界址。", "done": False, "note": ""},
            {"item": "放樣勘驗申報", "dept": "建管處", "timing": "【結構前】", "docs": "1. 報告書", "details": "正式進入結構體。", "done": False, "note": ""}
        ]
    }

# --- 3. 初始化 Session State ---
if "sop_data" not in st.session_state:
    st.session_state.sop_data = get_initial_sop()

# 為了方便存取，建立一個縮寫變數 (參照)
data = st.session_state.sop_data

# --- 4. 關鍵功能：狀態切換回調函數 (Callback) ---
# 這個函數會在使用者點擊勾選框的「瞬間」執行，確保資料先更新，再重新整理畫面
def toggle_status(stage_key, index):
    # 切換 True/False 狀態
    current_status = st.session_state.sop_data[stage_key][index]['done']
    st.session_state.sop_data[stage_key][index]['done'] = not current_status

# --- 5. 側邊欄：即時運算狀態 ---
# 因為有了 callback，這裡讀到的 data 絕對是最新的
with st.sidebar:
    st.header("📝 專案資訊")
    st.text_input("專案名稱", value="範例建案")
    
    st.divider()
    
    # 計算各階段完成度
    stage0_done = all(item['done'] for item in data['stage_0'])
    stage1_done = all(item['done'] for item in data['stage_1'])
    
    st.markdown("### 🚦 階段狀態監控")
    
    if stage0_done:
        st.success("✅ 建照領取：已完成")
    else:
        st.error("⛔ 建照領取：未完成")
        
    if stage0_done and stage1_done:
        st.success("✅ 開工申報：已完成")
    elif stage0_done and not stage1_done:
        st.warning("⚠️ 開工申報：進行中")
    else:
        st.info("⚪ 開工申報：等待中")

    st.divider()
    if st.button("🔄 重置所有進度"):
        st.session_state.sop_data = get_initial_sop()
        st.rerun()

# --- 6. 渲染函數 ---
def render_stage_detailed(stage_key, is_locked=False):
    stage_items = data[stage_key]
    
    if is_locked:
        st.markdown('<div class="locked-stage">🔒 此階段鎖定中 (請先完成上一階段)</div>', unsafe_allow_html=True)

    for i, item in enumerate(stage_items):
        with st.container():
            col1, col2 = st.columns([0.5, 9.5])
            
            # Checkbox 區
            with col1:
                # 這裡使用 on_change 來綁定我們寫好的 toggle_status 函數
                # args 傳遞參數給函數，告訴它是哪個階段的第幾個項目
                st.checkbox(
                    "", 
                    value=item['done'], 
                    key=f"chk_{stage_key}_{i}", # 使用唯一的 key
                    on_change=toggle_status, 
                    args=(stage_key, i),
                    disabled=is_locked
                )
            
            # 內容顯示區
            with col2:
                # 標題只顯示文字，不加圖示 (因為勾選框已經是綠色的了)
                title = f"**{item['item']}** (🏢 {item['dept']})"
                
                # 詳細資訊摺疊區
                with st.expander(title, expanded=False):
                    st.markdown(f"**🕒 時限：** {item['timing']}")
                    st.markdown(f"**📄 應備文件：**\n{item['docs']}")
                    if item['details']:
                        st.info(f"💡 {item['details']}")
                    
                    # 備註欄 (使用 key 避免重置)
                    # 注意：文字輸入框更新時，我們直接將值寫入 session_state
                    new_note = st.text_input(
                        "備註", 
                        value=item['note'], 
                        key=f"note_{stage_key}_{i}"
                    )
                    # 即時更新備註到資料庫
                    st.session_state.sop_data[stage_key][i]['note'] = new_note
        
        st.divider()

# --- 7. 主流程分頁 ---

# 進度條計算
current = 0
if stage0_done: current += 1
if stage0_done and stage1_done: current += 1
if current >= 2 and all(i['done'] for i in data['stage_2']): current += 1
if current >= 3 and all(i['done'] for i in data['stage_3']): current += 1

st.progress(current/5, text=f"專案總進度")

# 分頁籤
tabs = st.tabs(["0.建照領取", "1.開工申報準備", "2.施工計畫", "3.導溝勘驗", "4.放樣勘驗"])

with tabs[0]:
    st.subheader("🔑 階段零：建照領取")
    render_stage_detailed("stage_0", is_locked=False)

with tabs[1]:
    st.subheader("📋 階段一：開工申報準備")
    # 鎖定邏輯：如果階段0沒做完，這裡就鎖住
    render_stage_detailed("stage_1", is_locked=not stage0_done)

with tabs[2]:
    st.subheader("📘 階段二：施工計畫")
    # 鎖定邏輯：階段1沒做完，這裡就鎖住
    locked = not (stage0_done and stage1_done)
    render_stage_detailed("stage_2", is_locked=locked)

with tabs[3]:
    st.subheader("🚧 階段三：導溝勘驗")
    locked = not (all(i['done'] for i in data['stage_2']) and stage1_done)
    render_stage_detailed("stage_3", is_locked=locked)

with tabs[4]:
    st.subheader("📐 階段四：放樣勘驗")
    locked = not all(i['done'] for i in data['stage_3'])
    render_stage_detailed("stage_4", is_locked=locked)

# --- 8. Excel 下載 (保持原樣) ---
st.write("---")
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    all_rows = []
    for k, v in data.items():
        for item in v:
            item_copy = item.copy()
            item_copy['階段代號'] = k
            all_rows.append(item_copy)
    df_export = pd.DataFrame(all_rows)
    df_export = df_export[["階段代號", "item", "dept", "timing", "docs", "details", "done", "note"]]
    df_export.columns = ["階段", "項目", "單位", "時限", "文件", "注意", "完成", "備註"]
    df_export.to_excel(writer, index=False, sheet_name='SOP詳表')
    workbook = writer.book
    worksheet = writer.sheets['SOP詳表']
    fmt = workbook.add_format({'text_wrap': True, 'valign': 'top'})
    worksheet.set_column('B:B', 25, fmt)
    worksheet.set_column('E:E', 40, fmt)

st.download_button(
    label="📥 下載 Excel 進度表",
    data=buffer.getvalue(),
    file_name=f"SOP_Status_{date.today()}.xlsx",
    mime="application/vnd.ms-excel"
)