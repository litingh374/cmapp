import streamlit as st
import pandas as pd
import io
from datetime import date

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="建案行政SOP系統 (全無紙化版)",
    page_icon="🏗️",
    layout="wide"
)

# --- CSS 優化 ---
st.markdown("""
<style>
    /* 勾選框強制綠色 */
    div[data-testid="stCheckbox"] label span[data-checked="true"] {
        background-color: #2E7D32 !important;
        border-color: #2E7D32 !important;
    }
    .stProgress > div > div > div > div { background-color: #2E7D32; }
    
    /* 標籤樣式 */
    .tag-online {
        background-color: #e3f2fd; color: #0d47a1; padding: 2px 8px; 
        border-radius: 4px; font-size: 0.8em; font-weight: bold; border: 1px solid #90caf9;
    }
    .tag-paper {
        background-color: #efebe9; color: #5d4037; padding: 2px 8px; 
        border-radius: 4px; font-size: 0.8em; font-weight: bold; border: 1px solid #bcaaa4;
    }
    /* 資訊框 */
    .info-box {
        background-color: #f8f9fa; padding: 10px; border-radius: 5px; 
        border-left: 5px solid #6c757d; font-size: 0.9em; margin-bottom: 5px;
    }
    /* 調整 expander 間距 */
    div[data-testid="stExpander"] { margin-top: -5px; }
</style>
""", unsafe_allow_html=True)

st.title("🏗️ 建案開工至放樣 SOP 控管系統 (全無紙化版)")
st.caption("目前雙北市之 建照、開工、施工計畫、勘驗申報 皆已支援線上作業。")

# --- 2. 核心資料庫 (依據您的要求，全面更新為線上) ---
def get_initial_sop():
    return {
        "stage_0": [ 
            {
                "item": "建築執照申請 (無紙化)", 
                "dept": "建築師/建管處", 
                "method": "線上",
                "timing": "【掛號階段】", 
                "docs": "1. 申請書電子檔 (XML/PDF)\n2. 建照圖/結構圖 (D1/S1)\n3. 鑽探報告", 
                "details": "透過「建築執照無紙化審查系統」上傳。需使用自然人憑證進行電子簽章。核准後直接線上進行副本校對。", 
                "done": False, "note": ""
            },
            {
                "item": "領取建造執照", 
                "dept": "建管處", 
                "method": "臨櫃", # 領證目前仍多需臨櫃，或郵寄
                "timing": "【校對完成後】", 
                "docs": "1. 規費收據", 
                "details": "雖然審查過程無紙化，但最終「紙本執照」通常仍需臨櫃領取（視各縣市規定）。", 
                "done": False, "note": ""
            }
        ],
        "stage_1": [ 
            {
                "item": "開工申報 (無紙化)", 
                "dept": "建管處 (施工科)", 
                "method": "線上",
                "timing": "【建照後6個月內】", 
                "docs": "1. 開工申請書 (線上填報)\n2. 承造/監造人證書電子檔\n3. 保險單掃描檔", 
                "details": "全面強制線上申辦。請至「建管業務e辦網」或「建築工程施工勘驗申報系統」上傳。", 
                "done": False, "note": ""
            },
            {
                "item": "空氣污染防制費申報", 
                "dept": "環保局", 
                "method": "線上", 
                "timing": "【開工前】", 
                "docs": "1. 申報書\n2. 合約書", 
                "details": "至「營建工程空汙費網路申報系統」辦理。", 
                "done": False, "note": ""
            },
            {
                "item": "營建廢棄物處理計畫", 
                "dept": "環保局", 
                "method": "線上", 
                "timing": "【開工前】", 
                "docs": "1. 解除列管申請", 
                "details": "至「廢棄物申報及管理資訊系統」辦理。", 
                "done": False, "note": ""
            }
        ],
        "stage_2": [ 
            {
                "item": "施工計畫書申報", 
                "dept": "建管處", 
                "method": "線上",
                "timing": "【放樣前】", 
                "docs": "1. 施工計畫書 (PDF檔)\n2. 相關技師簽證", 
                "details": "直接將核定之施工計畫書 PDF 上傳至「建管業務e辦網」。不需再送紙本。", 
                "done": False, "note": ""
            },
            {
                "item": "職業安全衛生計畫", 
                "dept": "勞檢處", 
                "method": "線上", 
                "timing": "【開工前】", 
                "docs": "1. 安衛計畫書", 
                "details": "至職安署網站登錄。", 
                "done": False, "note": ""
            }
        ],
        "stage_3": [ 
            {
                "item": "導溝勘驗申報", 
                "dept": "建管處", 
                "method": "線上",
                "timing": "【施工前2日】", 
                "docs": "1. 勘驗申請書 (線上)\n2. 施工照片 (上傳)\n3. 專任人員證書", 
                "details": "屬「施工勘驗」項目。請至申報系統點選「其他/指定勘驗」或依縣市規定欄位申報。", 
                "done": False, "note": ""
            }
        ],
        "stage_4": [ 
            {
                "item": "放樣勘驗申報", 
                "dept": "建管處", 
                "method": "線上",
                "timing": "【結構施工前】", 
                "docs": "1. 放樣勘驗報告書 (PDF)\n2. 測量成果圖 (PDF)\n3. 現場照片", 
                "details": "這是最重要的線上勘驗點。需將測量成果與技師簽證文件掃描上傳。部分縣市(如新北)因檔案過大，可能採「線上申報+紙本核對」併行。", 
                "done": False, "note": ""
            },
             {
                "item": "基地鑑界 (複丈)", 
                "dept": "地政事務所", 
                "method": "臨櫃", # 鑑界通常還是要臨櫃申請或現場會勘
                "timing": "【放樣前】", 
                "docs": "1. 複丈申請書", 
                "details": "地政業務目前部分可線上申請，但鑑界需排定現場時間，建議臨櫃確認。", 
                "done": False, "note": ""
            }
        ]
    }

# --- 3. 自動修復 (強制更新資料結構) ---
# 為了讓您看到最新的「無紙化」設定，這裡會強制重置一次資料
if "sop_data" in st.session_state:
    # 簡單判斷：如果第一項還是舊的名稱，就重置
    if "無紙化" not in st.session_state.sop_data["stage_0"][0]["item"]:
        st.session_state.sop_data = get_initial_sop()
        st.rerun()

if "sop_data" not in st.session_state:
    st.session_state.sop_data = get_initial_sop()

data = st.session_state.sop_data

# --- 4. 狀態 Callback ---
def toggle_status(stage_key, index):
    current_status = st.session_state.sop_data[stage_key][index]['done']
    st.session_state.sop_data[stage_key][index]['done'] = not current_status

# --- 5. 側邊欄 ---
with st.sidebar:
    st.header("📝 專案資訊")
    st.text_input("專案名稱", value="範例建案")
    
    st.divider()
    
    # 計算進度
    s0_total = len(data['stage_0'])
    s0_done = sum(1 for item in data['stage_0'] if item['done'])
    permit_unlocked = (s0_done == s0_total)
    
    if permit_unlocked:
        st.success("✅ 建照領取：全部完成")
    else:
        st.warning(f"⚠️ 建照領取：{s0_done}/{s0_total}")
    
    if permit_unlocked:
        st.info("🔓 後續線上申報已解鎖")

    st.divider()
    if st.button("🔄 重置所有進度"):
        st.session_state.sop_data = get_initial_sop()
        st.rerun()

# --- 6. 渲染函數 (位置互換 + 線上標籤) ---
def render_stage_detailed(stage_key, is_locked=False):
    stage_items = data[stage_key]
    
    if is_locked:
        st.markdown('<div class="locked-stage">🔒 此階段鎖定中 (請先完成上一階段)</div>', unsafe_allow_html=True)

    for i, item in enumerate(stage_items):
        with st.container():
            col1, col2 = st.columns([0.5, 9.5])
            
            # 1. 勾選框
            with col1:
                st.checkbox(
                    "", 
                    value=item['done'], 
                    key=f"chk_{stage_key}_{i}", 
                    on_change=toggle_status, 
                    args=(stage_key, i),
                    disabled=is_locked
                )
            
            # 2. 內容顯示
            with col2:
                # 準備標籤
                method = item.get('method', '現場')
                method_tag = ""
                if method == "線上":
                    method_tag = '<span class="tag-online">🔵 線上申辦</span>'
                elif method == "臨櫃":
                    method_tag = '<span class="tag-paper">🟤 臨櫃/紙本</span>'
                else:
                    method_tag = f'<span class="tag-paper">{method}</span>'

                # 準備標題 HTML
                title_html = f"**{item['item']}** {method_tag} <span style='color:#666; font-size:0.9em'>(🏢 {item['dept']})</span>"
                
                # 名稱顯示 (已完成變綠色)
                if item['done']:
                    st.markdown(f"<span style='color:#2E7D32; font-weight:bold;'>✅ {item['item']}</span>", unsafe_allow_html=True)
                else:
                    st.markdown(title_html, unsafe_allow_html=True)

                # 詳細資訊 (放在名稱下方)
                with st.expander("🔽 詳細指引與備註", expanded=False):
                    st.markdown(f"**🕒 時機：** {item['timing']}")
                    st.markdown(f"**📄 應備文件：**\n{item['docs']}")
                    if item['details']:
                        st.markdown(f"<div class='info-box'>💡 <b>作業指引：</b><br>{item['details']}</div>", unsafe_allow_html=True)
                    
                    new_note = st.text_input("備註", value=item['note'], key=f"note_{stage_key}_{i}", placeholder="輸入文號或筆記...")
                    st.session_state.sop_data[stage_key][i]['note'] = new_note

        st.divider()

# --- 7. 主流程 ---

# 進度計算
current = 0
s1_done = all(i['done'] for i in data['stage_1'])
s2_done = all(i['done'] for i in data['stage_2'])

if permit_unlocked: current += 1
if permit_unlocked and s1_done: current += 1
if current >= 2 and s2_done: current += 1
if current >= 3 and all(i['done'] for i in data['stage_3']): current += 1

st.progress(current/5, text=f"專案總進度 (目前階段: {current})")

tabs = st.tabs(["0.建照領取 (無紙化)", "1.開工申報", "2.施工計畫", "3.導溝勘驗", "4.放樣勘驗"])

with tabs[0]:
    st.subheader("🔑 階段零：建照領取 (無紙化)")
    render_stage_detailed("stage_0", is_locked=False)

with tabs[1]:
    st.subheader("📋 階段一：開工申報")
    render_stage_detailed("stage_1", is_locked=not permit_unlocked)

with tabs[2]:
    st.subheader("📘 階段二：施工計畫")
    render_stage_detailed("stage_2", is_locked=not (permit_unlocked and s1_done))

with tabs[3]:
    st.subheader("🚧 階段三：導溝勘驗")
    render_stage_detailed("stage_3", is_locked=not (s2_done and s1_done))

with tabs[4]:
    st.subheader("📐 階段四：放樣勘驗")
    render_stage_detailed("stage_4", is_locked=not all(i['done'] for i in data['stage_3']))

# --- 8. Excel 下載 ---
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
    df_export['申辦方式'] = df_export.apply(lambda x: x.get('method', '現場'), axis=1)
    df_export = df_export[["階段代號", "item", "申辦方式", "dept", "timing", "docs", "details", "done", "note"]]
    df_export.columns = ["階段", "項目", "申辦方式", "單位", "時限", "文件", "指引", "完成", "備註"]
    df_export.to_excel(writer, index=False, sheet_name='SOP詳表')

st.download_button(
    label="📥 下載 Excel 進度表",
    data=buffer.getvalue(),
    file_name=f"SOP_Online_Full_{date.today()}.xlsx",
    mime="application/vnd.ms-excel"
)