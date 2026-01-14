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

# --- CSS 優化 (美化鎖定與提示框) ---
st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #2E7D32; }
    .locked-stage { 
        padding: 15px; border-radius: 5px; background-color: #f5f5f5; 
        border: 1px solid #ddd; color: #888; font-style: italic;
    }
    .info-box {
        background-color: #e3f2fd; padding: 10px; border-radius: 5px; border-left: 5px solid #2196f3;
        font-size: 0.9em; margin-bottom: 5px;
    }
    .warning-box {
        background-color: #fff3e0; padding: 10px; border-radius: 5px; border-left: 5px solid #ff9800;
        font-size: 0.9em;
    }
    /* 讓 Checkbox 看起來更明顯 */
    div[data-testid="stCheckbox"] label {
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏗️ 建案開工至放樣 SOP 系統")
st.caption("操作說明：✅ 打勾代表已完成，⬜ 空白代表未完成。")

# --- 2. 核心資料庫 (定義所有欄位預設為 False) ---
def get_detailed_sop():
    return {
        "stage_0": [
            {
                "item": "建築師-建照執照領取",
                "dept": "建築師事務所",
                "timing": "【專案啟動】",
                "docs": "1. 建造執照正本\n2. 核准圖說",
                "details": "這是所有流程的起點。需確認建照號碼、起造人名稱無誤。",
                "done": False, # 預設 False (未勾選)
                "note": ""
            }
        ],
        "stage_1": [ 
            {
                "item": "空氣污染防制費 (首期) 申報",
                "dept": "環保局 (空噪科)",
                "timing": "【開工前】",
                "docs": "1. 空汙費申報書\n2. 建照影本\n3. 工程合約書",
                "details": "⚠️ 限制：未繳納空汙費者，無法申報開工。",
                "done": False, 
                "note": ""
            },
            {
                "item": "營建工程廢棄物處理計畫書",
                "dept": "環保局 / 工務局",
                "timing": "【開工前】",
                "docs": "1. 廢棄物處置計畫書\n2. 土資場收容同意書",
                "details": "需取得核定函後始得運土。",
                "done": False, 
                "note": ""
            },
            {
                "item": "逕流廢水削減計畫",
                "dept": "環保局 (水保科)",
                "timing": "【開工前】",
                "docs": "1. 削減計畫書\n2. 沉沙池設置圖說",
                "details": "規劃工區臨時排水路徑。",
                "done": False, 
                "note": ""
            },
            {
                "item": "現況調查 (鄰房鑑定申請)",
                "dept": "技師公會",
                "timing": "【拆除/開工前】",
                "docs": "1. 鑑定申請書\n2. 鄰房清冊",
                "details": "⚠️ 極重要：務必於實際動工前完成。",
                "done": False, 
                "note": ""
            },
            {
                "item": "五大管線查詢",
                "dept": "各管線單位",
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
                "details": "⚠️ 期限：逾期未開工建照將作廢。",
                "done": False, 
                "note": ""
            }
        ],
        "stage_2": [ 
            {
                "item": "施工計畫書 (含防災/交維)",
                "dept": "建管處 / 外審",
                "timing": "【放樣前】",
                "docs": "1. 施工計畫書\n2. 簡報資料",
                "details": "特殊結構或深開挖需進行外審。",
                "done": False, 
                "note": ""
            },
            {
                "item": "職業安全衛生管理計畫",
                "dept": "勞檢處",
                "timing": "【開工前】",
                "docs": "1. 安衛計畫書\n2. 人員證照",
                "details": "危險性工作場所需丁類審查。",
                "done": False, 
                "note": ""
            }
        ],
        "stage_3": [ 
            {
                "item": "導溝施工與單元劃分",
                "dept": "工地現場",
                "timing": "【連續壁前】",
                "docs": "1. 單元分割圖\n2. 自主檢查表",
                "details": "確認導溝位置與鋪面。",
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

# --- 3. 初始化 Session State (確保資料載入) ---
if "sop_data" not in st.session_state:
    st.session_state.sop_data = get_detailed_sop()

data = st.session_state.sop_data

# --- 4. 側邊欄：控制面板 ---
with st.sidebar:
    st.header("⚙️ 專案設定")
    st.text_input("專案名稱", value="範例建案")
    
    st.divider()
    
    # 這裡顯示全域狀態
    permit_done = all(item['done'] for item in data['stage_0'])
    
    if permit_done:
        st.success("🟢 狀態：建照已領取 (系統解鎖)")
    else:
        st.error("🔴 狀態：建照尚未領取 (系統鎖定)")

    st.divider()
    
    # [修正點] 強力重置按鈕
    # 如果您看到預設是打勾的，請按這個按鈕，它會強制把所有勾選取消
    if st.button("🔄 重置所有進度 (清空勾選)", type="primary"):
        st.session_state.sop_data = get_detailed_sop() # 重新載入全 False 的資料
        st.rerun() # 重新整理頁面

# --- 5. 渲染列表的函數 ---
def render_stage_detailed(stage_key, is_locked=False):
    stage_items = data[stage_key]
    
    if is_locked:
        st.markdown(f'<div class="locked-stage">🔒 此階段鎖定中：請先完成上一階段關鍵項目（如建照領取、開工申報等）。</div>', unsafe_allow_html=True)

    for i, item in enumerate(stage_items):
        # 使用 container 讓排版整齊
        with st.container():
            col1, col2 = st.columns([0.5, 9.5])
            
            # Checkbox 區
            with col1:
                # [修正點] 這裡的 key 加上了 'v2'，避免跟舊的暫存打架
                checked = st.checkbox(
                    "", 
                    value=item['done'], 
                    key=f"{stage_key}_{i}_v2", 
                    disabled=is_locked,
                    help="點擊勾選代表「已完成」"
                )
                data[stage_key][i]['done'] = checked
            
            # 詳細內容區
            with col2:
                # 標題變色邏輯
                title = f"**{item['item']}**"
                dept_badge = f" `🏢 {item['dept']}`"
                
                if item['done']:
                    # 完成時顯示綠色打勾標題
                    st.markdown(f"✅ ~~{item['item']}~~ (已完成)", help="此項目已完成")
                else:
                    # 未完成顯示正常標題
                    with st.expander(f"{title} {dept_badge}", expanded=False):
                        # 詳細資訊
                        st.markdown(f"<div class='info-box'><b>🕒 時限：</b>{item['timing']}</div>", unsafe_allow_html=True)
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("**📄 應備文件：**")
                            st.text(item['docs'])
                        with c2:
                            if item['details']:
                                st.markdown(f"<div class='warning-box'><b>⚠️ 注意：</b><br>{item['details']}</div>", unsafe_allow_html=True)
                        
                        # 備註欄
                        data[stage_key][i]['note'] = st.text_input(
                            "備註/文號", 
                            value=item['note'], 
                            key=f"note_{stage_key}_{i}_v2",
                            placeholder="輸入備註...",
                            disabled=is_locked
                        )
        st.divider()

# --- 6. 主畫面流程 ---

# 進度條
current_stage = 0
total_stages = 5
if permit_done: current_stage += 1
if permit_done and all(i['done'] for i in data['stage_1']): current_stage += 1
if current_stage >= 2 and all(i['done'] for i in data['stage_2']): current_stage += 1
if current_stage >= 3 and all(i['done'] for i in data['stage_3']): current_stage += 1

st.progress(current_stage/total_stages, text=f"目前進度：第 {current_stage} / {total_stages} 階段")

# 分頁
tab0, tab1, tab2, tab3, tab4 = st.tabs([
    "0.建照領取", "1.開工申報準備", "2.施工計畫", "3.導溝勘驗", "4.放樣勘驗"
])

with tab0:
    st.subheader("🔑 階段零：建照領取")
    render_stage_detailed("stage_0")

with tab1:
    st.subheader("📋 階段一：開工申報準備")
    is_locked = not permit_done
    render_stage_detailed("stage_1", is_locked)

with tab2:
    st.subheader("📘 階段二：施工計畫")
    is_locked = not (permit_done and all(i['done'] for i in data['stage_1']))
    render_stage_detailed("stage_2", is_locked)

with tab3:
    st.subheader("🚧 階段三：導溝勘驗")
    is_locked = not (all(i['done'] for i in data['stage_2']))
    render_stage_detailed("stage_3", is_locked)

with tab4:
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
    cols = ["階段代號", "item", "dept", "timing", "docs", "details", "done", "note"]
    df_export = df_export[cols]
    df_export.columns = ["階段", "項目", "單位", "時限", "文件", "注意", "完成", "備註"]
    df_export.to_excel(writer, index=False, sheet_name='SOP')

st.download_button(
    label="📥 下載 Excel 進度表",
    data=buffer.getvalue(),
    file_name=f"SOP_Status_{date.today()}.xlsx",
    mime="application/vnd.ms-excel"
)