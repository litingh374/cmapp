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
    div[data-testid="stExpander"] { margin-top: -5px; }
</style>
""", unsafe_allow_html=True)

st.title("🏗️ 建案開工至放樣 SOP 控管系統")
st.caption("依據：申辦開工、計劃、放樣用清冊 (終極版) 邏輯 ｜ 整合無紙化申辦資訊")

# --- 2. 核心資料庫 ---
def get_initial_sop():
    return {
        "stage_0": [ 
            {
                "item": "建築執照申請作業", # 已移除(無紙化)字樣
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
                "method": "臨櫃", 
                "timing": "【校對完成後】", 
                "docs": "1. 規費收據", 
                "details": "雖然審查過程無紙化，但最終「紙本執照」通常仍需臨櫃領取（視各縣市規定）。", 
                "done": False, "note": ""
            }
        ],
        "stage_1": [ 
            {
                "item": "開工申報", 
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
                "details": "需將測量成果與技師簽證文件掃描上傳。部分縣市可能採「線上申報+紙本核對」併行。", 
                "done": False, "note": ""
            },
             {
                "item": "基地鑑界 (複丈)", 
                "dept": "地政事務所", 
                "method": "臨櫃", 
                "timing": "【放樣前】", 
                "docs": "1. 複丈申請書", 
                "details": "地政業務目前部分可線上申請，但鑑界需排定現場時間，建議臨櫃確認。", 
                "done": False, "note": ""
            }
        ]
    }

# --- 3. 自動修復與初始化 ---
# 確保資料結構與最新版一致
if "sop_data" not in st.session_state:
    st.session_state.sop_data = get_initial_sop()
else:
    # 簡單防呆：如果舊資料的第一項標題還包含(無紙化)，就重置
    if "(無紙化)" in st.session_state.sop_data["stage_0"][0]["item"]:
        st.session_state.sop_data = get_initial_sop()
        st.rerun()

data = st.session_state.sop_data

# --- 4. 狀態 Callback ---
def toggle_status(stage_key, index):
    current_status = st.session_state.sop_data[stage_key][index]['done']
    st.session_state.sop_data[stage_key][index]['done'] = not current_status

# --- 5. 側邊欄：新增詳細欄位 ---
with st.sidebar:
    st.header("📝 專案基本資料")
    
    # [新增] 更多欄位供填寫
    st.text_input("專案名稱", value="範例建案")
    st.text_input("建造執照號碼", value="", placeholder="例：114建字第00123號")
    st.text_input("基地位置/地號", value="", placeholder="例：中山區長春段...")
    st.text_input("設計建築師", value="", placeholder="XX 建築師事務所")
    
    st.divider()
    
    # 進度計算
    s0_total = len(data['stage_0'])
    s0_done = sum(1 for item in data['stage_0'] if item['done'])
    permit_unlocked = (s0_done == s0_total)
    
    if permit_unlocked:
        st.success("✅ 建照領取：完成")
    else:
        st.warning(f"⚠️ 建照領取：{s0_done}/{s0_total}")
    
    if permit_unlocked:
        st.info("🔓 後續流程已解鎖")

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
            
            with col1:
                st.checkbox(
                    "", 
                    value=item['done'], 
                    key=f"chk_{stage_key}_{i}", 
                    on_change=toggle_status, 
                    args=(stage_key, i),
                    disabled=is_locked
                )
            
            with col2:
                method = item.get('method', '現場')
                method_tag = ""
                if method == "線上":
                    method_tag = '<span class="tag-online">🔵 線上申辦</span>'
                elif method == "臨櫃":
                    method_tag = '<span class="tag-paper">🟤 臨櫃/紙本</span>'
                else:
                    method_tag = f'<span class="tag-paper">{method}</span>'

                title_html = f"**{item['item']}** {method_tag} <span style='color:#666; font-size:0.9em'>(🏢 {item['dept']})</span>"
                
                if item['done']:
                    st.markdown(f"<span style='color:#2E7D32; font-weight:bold;'>✅ {item['item']}</span>", unsafe_allow_html=True)
                else:
                    st.markdown(title_html, unsafe_allow_html=True)

                with st.expander("🔽 詳細指引與備註", expanded=False):
                    st.markdown(f"**🕒 時機：** {item['timing']}")
                    st.markdown(f"**📄 應備文件：**\n{item['docs']}")
                    if item['details']:
                        st.markdown(f"<div class='info-box'>💡 <b>作業指引：</b><br>{item['details']}</div>", unsafe_allow_html=True)
                    
                    new_note = st.text_input("備註", value=item['note'], key=f"note_{stage_key}_{i}", placeholder="輸入文號或筆記...")
                    st.session_state.sop_data[stage_key][i]['note'] = new_note

        st.divider()

# --- 7. 主流程 ---

current = 0
s1_done = all(i['done'] for i in data['stage_1'])
s2_done = all(i['done'] for i in data['stage_2'])

if permit_unlocked: current += 1
if permit_unlocked and s1_done: current += 1
if current >= 2 and s2_done: current += 1
if current >= 3 and all(i['done'] for i in data['stage_3']): current += 1

st.progress(current/5, text=f"專案總進度")

# [修正] 移除標題中的(無紙化)字樣
tabs = st.tabs(["0.建照領取", "1.開工申報", "2.施工計畫", "3.導溝勘驗", "4.放樣勘驗"])

with tabs[0]:
    st.subheader("🔑 階段零：建照領取")
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
    file_name=f"SOP_Construction_{date.today()}.xlsx",
    mime="application/vnd.ms-excel"
)