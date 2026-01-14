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

# --- CSS 優化 (關鍵修改：將勾選框改為綠色) ---
st.markdown("""
<style>
    /* 強制將 Checkbox 打勾後的顏色改為綠色 (工程 Pass 色) */
    div[data-testid="stCheckbox"] label span[data-checked="true"] {
        background-color: #2E7D32 !important; /* 綠色背景 */
        border-color: #2E7D32 !important;
    }
    
    /* 讓進度條也呈現綠色 */
    .stProgress > div > div > div > div { background-color: #2E7D32; }
    
    /* 鎖定狀態的樣式 */
    .locked-stage { 
        padding: 15px; border-radius: 5px; background-color: #f5f5f5; 
        border: 1px solid #ddd; color: #888; font-style: italic;
    }
    
    /* 資訊框樣式 */
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
st.markdown("### 狀態指示：⬜ 空白=未辦理 ｜ ✅ 綠色打勾=已完成")

# --- 2. 核心資料庫 ---
def get_sop_data():
    return {
        "stage_0": [
            {
                "item": "建築師-建照執照領取",
                "dept": "建築師事務所",
                "timing": "【專案啟動】",
                "docs": "1. 建造執照正本\n2. 核准圖說",
                "details": "這是流程起點。需確認建照號碼、起造人名稱無誤。",
                "done": False,
                "note": ""
            }
        ],
        "stage_1": [ 
            {
                "item": "空氣污染防制費 (首期) 申報",
                "dept": "環保局 (空噪科)",
                "timing": "【開工前】",
                "docs": "1. 空汙費申報書\n2. 建照影本\n3. 工程合約書",
                "details": "⚠️ 未繳納空汙費者，無法申報開工。",
                "done": False,
                "note": ""
            },
            {
                "item": "營建工程廢棄物處理計畫書",
                "dept": "環保局 / 工務局",
                "timing": "【開工前】",
                "docs": "1. 廢棄物處置計畫書\n2. 土資場收容同意書",
                "details": "需確認土資場有剩餘容量，核定後始得運土。",
                "done": False,
                "note": ""
            },
            {
                "item": "逕流廢水削減計畫",
                "dept": "環保局 (水保科)",
                "timing": "【開工前】",
                "docs": "1. 削減計畫書\n2. 沉沙池設置圖說",
                "details": "規劃工區臨時排水路徑與沉沙池。",
                "done": False,
                "note": ""
            },
            {
                "item": "現況調查 (鄰房鑑定申請)",
                "dept": "技師公會",
                "timing": "【拆除/開工前】",
                "docs": "1. 鑑定申請書\n2. 鄰房清冊",
                "details": "⚠️ 務必於「實際動工」前完成，避免損鄰爭議。",
                "done": False,
                "note": ""
            },
            {
                "item": "五大管線查詢",
                "dept": "管線單位",
                "timing": "【規劃階段】",
                "docs": "1. 現況圖\n2. 建照地號清單",
                "details": "確認基地內外管線分布。",
                "done": False,
                "note": ""
            },
            {
                "item": "建管開工申報 (正式掛號)",
                "dept": "建管處 (施工科)",
                "timing": "【取得建照後6個月內】",
                "docs": "1. 開工申請書\n2. 證書影本\n3. 保險單\n4. 環保核定函",
                "details": "⚠️ 逾期未開工建照將作廢 (可展延一次)。",
                "done": False,
                "note": ""
            }
        ],
        "stage_2": [ 
            {
                "item": "施工計畫書 (含交通/防災)",
                "dept": "建管處 / 外審",
                "timing": "【放樣勘驗前】",
                "docs": "1. 施工計畫書\n2. 簡報資料",
                "details": "特殊結構或深開挖需進行外審。需召開說明會。",
                "done": False,
                "note": ""
            },
            {
                "item": "職業安全衛生管理計畫",
                "dept": "勞動檢查處",
                "timing": "【開工前】",
                "docs": "1. 安衛計畫書\n2. 人員證照",
                "details": "危險性工作場所需另進行丁類審查。",
                "done": False,
                "note": ""
            }
        ],
        "stage_3": [ 
            {
                "item": "導溝施工與單元劃分",
                "dept": "工地現場",
                "timing": "【連續壁施作前】",
                "docs": "1. 單元分割圖\n2. 自主檢查表",
                "details": "確認導溝位置與鋪面完成。",
                "done": False,
                "note": ""
            },
            {
                "item": "導溝勘驗申報",
                "dept": "建管處 / 公會",
                "timing": "【計畫核定後】",
                "docs": "1. 勘驗申請書\n2. 施工照片\n3. 簽證文件",
                "details": "需完成圍籬與告示牌。",
                "done": False,
                "note": ""
            }
        ],
        "stage_4": [ 
            {
                "item": "基地鑑界 (複丈)",
                "dept": "地政事務所",
                "timing": "【放樣前】",
                "docs": "1. 土地複丈申請書",
                "details": "確認建築線與地界一致。",
                "done": False,
                "note": ""
            },
            {
                "item": "放樣勘驗申報",
                "dept": "建管處",
                "timing": "【結構施工前】",
                "docs": "1. 放樣勘驗報告\n2. 測量成果圖",
                "details": "完成後正式進入結構體施工。",
                "done": False,
                "note": ""
            }
        ]
    }

# --- 3. 初始化 ---
if "sop_data" not in st.session_state:
    st.session_state.sop_data = get_sop_data()

data = st.session_state.sop_data

# --- 4. 側邊欄 ---
with st.sidebar:
    st.header("📝 專案資訊")
    st.text_input("專案名稱", value="範例建案")
    
    # 狀態顯示
    permit_done = all(item['done'] for item in data['stage_0'])
    if permit_done:
        st.success("✅ 建照已領取")
    else:
        st.warning("⚠️ 尚未領取建照")

    st.divider()
    # 重置按鈕
    if st.button("🔄 重置所有進度 (清空)"):
        st.session_state.sop_data = get_sop_data()
        st.rerun()

# --- 5. 渲染函數 (視覺優化版) ---
def render_stage_detailed(stage_key, is_locked=False):
    stage_items = data[stage_key]
    
    if is_locked:
        st.caption("🔒 此階段目前鎖定中 (請先完成上一階段)")

    for i, item in enumerate(stage_items):
        with st.container():
            col1, col2 = st.columns([0.5, 9.5])
            
            # Checkbox
            with col1:
                # 這裡的 value 綁定的是 item['done']
                # 當使用者勾選時，會變成 True (完成)
                checked = st.checkbox(
                    "", 
                    value=item['done'], 
                    key=f"{stage_key}_{i}", 
                    disabled=is_locked
                )
                data[stage_key][i]['done'] = checked
            
            # 內容區
            with col2:
                # 視覺處理：已完成變綠色，未完成保持原樣
                if item['done']:
                    # 完成狀態：綠色字體 + 打勾圖示
                    st.markdown(
                        f"<div style='color:#2E7D32; font-weight:bold;'>"
                        f"✅ {item['item']} <span style='font-size:0.8em; color:#666;'>(已完成)</span>"
                        f"</div>", 
                        unsafe_allow_html=True
                    )
                else:
                    # 未完成狀態：使用 Expander 顯示詳細資訊
                    title = f"**{item['item']}** (🏢 {item['dept']})"
                    with st.expander(title, expanded=False):
                        st.markdown(f"**🕒 時限：** {item['timing']}")
                        st.markdown(f"**📄 應備文件：**\n{item['docs']}")
                        if item['details']:
                            st.info(f"💡 {item['details']}")
                        
                        # 備註輸入
                        data[stage_key][i]['note'] = st.text_input(
                            "備註/文號", 
                            value=item['note'], 
                            key=f"note_{stage_key}_{i}",
                            placeholder="輸入備註...",
                            disabled=is_locked
                        )
        st.divider()

# --- 6. 主流程分頁 ---

# 進度條
current = 0
if permit_done: current += 1
if permit_done and all(i['done'] for i in data['stage_1']): current += 1
if current >= 2 and all(i['done'] for i in data['stage_2']): current += 1
if current >= 3 and all(i['done'] for i in data['stage_3']): current += 1
st.progress(current/5, text=f"流程進度")

# 分頁籤
tabs = st.tabs(["0.建照領取", "1.開工申報準備", "2.施工計畫", "3.導溝勘驗", "4.放樣勘驗"])

with tabs[0]:
    st.subheader("🔑 階段零：建照領取")
    render_stage_detailed("stage_0")

with tabs[1]:
    st.subheader("📋 階段一：開工申報準備")
    render_stage_detailed("stage_1", is_locked=not permit_done)

with tabs[2]:
    st.subheader("📘 階段二：施工計畫")
    is_locked = not (permit_done and all(i['done'] for i in data['stage_1']))
    render_stage_detailed("stage_2", is_locked)

with tabs[3]:
    st.subheader("🚧 階段三：導溝勘驗")
    is_locked = not (all(i['done'] for i in data['stage_2']))
    render_stage_detailed("stage_3", is_locked)

with tabs[4]:
    st.subheader("📐 階段四：放樣勘驗")
    is_locked = not (all(i['done'] for i in data['stage_3']))
    render_stage_detailed("stage_4", is_locked)

# --- 7. 下載 ---
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
    # 整理欄位
    df_export = df_export[["階段代號", "item", "dept", "timing", "docs", "details", "done", "note"]]
    df_export.columns = ["階段", "項目", "單位", "時限", "文件", "注意", "完成", "備註"]
    
    df_export.to_excel(writer, index=False, sheet_name='SOP詳表')
    
    # 調整格式
    workbook = writer.book
    worksheet = writer.sheets['SOP詳表']
    fmt = workbook.add_format({'text_wrap': True, 'valign': 'top'})
    worksheet.set_column('B:B', 25, fmt)
    worksheet.set_column('E:E', 40, fmt)

st.download_button(
    label="📥 下載 Excel",
    data=buffer.getvalue(),
    file_name=f"SOP_Status_{date.today()}.xlsx",
    mime="application/vnd.ms-excel"
)