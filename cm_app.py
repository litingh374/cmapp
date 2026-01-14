import streamlit as st
import pandas as pd
import io
from datetime import date

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="建案行政SOP系統 (無紙化版)",
    page_icon="🏗️",
    layout="wide"
)

# --- CSS 優化 (綠色勾選 + 線上申辦標籤) ---
st.markdown("""
<style>
    /* 勾選框優化 */
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
</style>
""", unsafe_allow_html=True)

st.title("🏗️ 建案開工至放樣 SOP 控管系統 (含無紙化流程)")
st.caption("依據：申辦開工、計劃、放樣用清冊 (終極版) 邏輯 ｜ 整合各縣市無紙化作業規定")

# --- 2. 核心資料庫 (擴充版) ---
def get_initial_sop():
    return {
        "stage_0": [ # 建照領取階段 (大幅擴充)
            {
                "item": "土地與建物權利證明確認", 
                "dept": "業主/地政", 
                "method": "紙本",
                "timing": "【規劃初期】", 
                "docs": "1. 土地登記簿謄本 (第一類)\n2. 土地使用權同意書\n3. 建物測量成果圖 (若有拆除)", 
                "details": "確認產權清楚，無限制登記。若為共有土地需取得全體或依土地法34-1規定辦理。", 
                "done": False, "note": ""
            },
            {
                "item": "建築執照申請書表製作", 
                "dept": "建築師", 
                "method": "線上",
                "timing": "【掛號前】", 
                "docs": "1. 申請書電子檔 (.io)\n2. 概要表、地號表", 
                "details": "⚠️ 必用工具：需使用「建築執照申請書表電子化系統」產製 PDF 與 XML 檔。", 
                "done": False, "note": ""
            },
            {
                "item": "無紙化圖說上傳 (電子簽章)", 
                "dept": "建築師/技師", 
                "method": "線上",
                "timing": "【掛號前】", 
                "docs": "1. 建照圖 (D1)\n2. 結構圖 (S1)\n3. 鑽探報告", 
                "details": "需使用 HICOS 元件及自然人憑證進行電子簽章上傳。\n平台：台北市建管業務E辦網 / 新北市工務局無紙化平台。", 
                "done": False, "note": ""
            },
            {
                "item": "建造執照正式掛號", 
                "dept": "建管處 (建照科)", 
                "method": "紙本",
                "timing": "【送件當日】", 
                "docs": "1. 申請書正本 (需用印)\n2. 簽證表\n3. 委託書", 
                "details": "無紙化政策下，首次掛號仍多需檢附「申請書」與「簽證表」之紙本正本以供存查。", 
                "done": False, "note": ""
            },
            {
                "item": "特殊審查 (都審/水保/開放空間)", 
                "dept": "各主管機關", 
                "method": "混合",
                "timing": "【建照核准前】", 
                "docs": "1. 委員會核定函\n2. 核定報告書", 
                "details": "若案件涉及都市設計審議、水土保持計畫，需先取得核定始得核發建照。", 
                "done": False, "note": ""
            },
            {
                "item": "副本校對與電子檔上傳", 
                "dept": "建管處", 
                "method": "線上",
                "timing": "【決行後】", 
                "docs": "1. 最終核定圖說 (清圖)\n2. 副本圖檔", 
                "details": "審查通過後，需上傳最終版圖說進行「副本校對」，校對無誤後系統產生執照號碼。", 
                "done": False, "note": ""
            },
            {
                "item": "領取建造執照", 
                "dept": "建管處", 
                "method": "臨櫃",
                "timing": "【校對完成後】", 
                "docs": "1. 規費繳納收據\n2. 領照人身分證", 
                "details": "繳納規費後領取建照正本。此時流程正式解鎖，可進入開工申報階段。", 
                "done": False, "note": ""
            },
        ],
        "stage_1": [ # 開工前置與申報
            {"item": "空氣污染防制費申報", "dept": "環保局", "method": "線上", "timing": "【開工前】", "docs": "1. 空汙費申報書 (線上填報)", "details": "至「營建工程空汙費網路申報系統」辦理。", "done": False, "note": ""},
            {"item": "營建廢棄物處理計畫", "dept": "環保局", "method": "線上", "timing": "【開工前】", "docs": "1. 廢棄物計畫書\n2. 土資場同意書", "details": "需至「廢棄物申報及管理資訊系統」解除列管。", "done": False, "note": ""},
            {"item": "現況調查 (鄰房鑑定)", "dept": "技師公會", "method": "紙本", "timing": "【拆除/開工前】", "docs": "1. 鑑定申請書", "details": "務必於動工前完成外業。", "done": False, "note": ""},
            {"item": "建管開工申報", "dept": "建管處 (施工科)", "method": "線上", "timing": "【建照後6個月內】", "docs": "1. 開工申請書\n2. 證書\n3. 保險單", "details": "目前台北/新北皆已推動「免紙本開工」，請至 E 辦網上傳文件。", "done": False, "note": ""}
        ],
        "stage_2": [ # 施工計畫
            {"item": "施工計畫書審查", "dept": "建管處", "method": "線上", "timing": "【放樣前】", "docs": "1. 施工計畫書 PDF", "details": "特殊結構需外審。一般案件可線上上傳核備。", "done": False, "note": ""},
            {"item": "職業安全衛生計畫", "dept": "勞檢處", "method": "線上", "timing": "【開工前】", "docs": "1. 安衛計畫", "details": "危評案件需至職安署網站登錄。", "done": False, "note": ""}
        ],
        "stage_3": [ # 導溝與放樣 (勘驗多為線上預約+現場)
            {"item": "導溝勘驗申報", "dept": "建管處", "method": "線上", "timing": "【計畫核定後】", "docs": "1. 勘驗申請書\n2. 照片", "details": "透過 APP 或網站申報勘驗。", "done": False, "note": ""},
            {"item": "放樣勘驗申報", "dept": "建管處", "method": "線上", "timing": "【結構前】", "docs": "1. 測量報告", "details": "需技師電子簽證。", "done": False, "note": ""}
        ],
        "stage_4": [ # 現場準備 (依清冊邏輯)
             {"item": "基地鑑界 (複丈)", "dept": "地政事務所", "method": "臨櫃", "timing": "【放樣前】", "docs": "1. 複丈申請書", "details": "確認界址點。", "done": False, "note": ""},
             {"item": "施工圍籬架設", "dept": "工地", "method": "現場", "timing": "【開工時】", "docs": "1. 綠美化照片", "details": "需符合圍籬美化規範。", "done": False, "note": ""}
        ]
    }

# --- 3. 初始化 Session State ---
if "sop_data" not in st.session_state:
    st.session_state.sop_data = get_initial_sop()

data = st.session_state.sop_data

# --- 4. 狀態切換 Callback ---
def toggle_status(stage_key, index):
    current_status = st.session_state.sop_data[stage_key][index]['done']
    st.session_state.sop_data[stage_key][index]['done'] = not current_status

# --- 5. 側邊欄 ---
with st.sidebar:
    st.header("📝 專案資訊")
    st.text_input("專案名稱", value="範例建案")
    
    st.divider()
    
    # 計算建照領取進度
    s0_total = len(data['stage_0'])
    s0_done = sum(1 for item in data['stage_0'] if item['done'])
    permit_unlocked = (s0_done == s0_total)
    
    if permit_unlocked:
        st.success("✅ 建照領取：全部完成")
    else:
        st.warning(f"⚠️ 建照領取：{s0_done}/{s0_total}")

    st.divider()
    if st.button("🔄 重置所有進度"):
        st.session_state.sop_data = get_initial_sop()
        st.rerun()

# --- 6. 渲染函數 (含線上標籤) ---
def render_stage_detailed(stage_key, is_locked=False):
    stage_items = data[stage_key]
    
    if is_locked:
        st.markdown('<div class="locked-stage">🔒 此階段鎖定中 (請先完成上一階段)</div>', unsafe_allow_html=True)

    for i, item in enumerate(stage_items):
        with st.container():
            col1, col2 = st.columns([0.5, 9.5])
            
            # Checkbox
            with col1:
                st.checkbox(
                    "", 
                    value=item['done'], 
                    key=f"chk_{stage_key}_{i}", 
                    on_change=toggle_status, 
                    args=(stage_key, i),
                    disabled=is_locked
                )
            
            # 內容顯示
            with col2:
                # 判斷標籤顏色
                method_tag = ""
                if item.get('method') == "線上":
                    method_tag = '<span class="tag-online">🔵 線上申辦</span>'
                elif item.get('method') == "紙本" or item.get('method') == "臨櫃":
                    method_tag = '<span class="tag-paper">🟤 紙本/臨櫃</span>'
                else:
                    method_tag = f'<span class="tag-paper">{item.get("method", "現場")}</span>'

                title_html = f"**{item['item']}** {method_tag} <span style='color:#666; font-size:0.9em'>(🏢 {item['dept']})</span>"
                
                with st.expander(f"詳細資訊", expanded=False):
                    # 這裡用 markdown 渲染 HTML 標題
                    st.markdown(title_html, unsafe_allow_html=True) 
                    
                    st.markdown(f"**🕒 時機：** {item['timing']}")
                    st.markdown(f"**📄 應備文件：**\n{item['docs']}")
                    if item['details']:
                        st.markdown(f"<div class='info-box'>💡 <b>作業指引：</b><br>{item['details']}</div>", unsafe_allow_html=True)
                    
                    # 備註
                    new_note = st.text_input("備註", value=item['note'], key=f"note_{stage_key}_{i}")
                    st.session_state.sop_data[stage_key][i]['note'] = new_note

                # 在 Expander 外面顯示簡潔標題 (方便快速瀏覽)
                if not item['done']:
                    st.markdown(title_html, unsafe_allow_html=True)
                else:
                    # 完成後變淡並顯示標題
                    st.markdown(f"<span style='color:#2E7D32; font-weight:bold;'>✅ {item['item']}</span>", unsafe_allow_html=True)

        st.divider()

# --- 7. 主流程分頁 ---

# 進度計算
current = 0
s1_done = all(i['done'] for i in data['stage_1'])
s2_done = all(i['done'] for i in data['stage_2'])

if permit_unlocked: current += 1
if permit_unlocked and s1_done: current += 1
if current >= 2 and s2_done: current += 1
if current >= 3 and all(i['done'] for i in data['stage_3']): current += 1

st.progress(current/5, text=f"專案總進度")

tabs = st.tabs(["0.建照領取 (無紙化)", "1.開工申報", "2.施工計畫", "3.導溝勘驗", "4.放樣勘驗"])

with tabs[0]:
    st.subheader("🔑 階段零：建照領取與無紙化作業")
    render_stage_detailed("stage_0", is_locked=False)

with tabs[1]:
    st.subheader("📋 階段一：開工申報準備")
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
    df_export = df_export[["階段代號", "item", "method", "dept", "timing", "docs", "details", "done", "note"]]
    df_export.columns = ["階段", "項目", "申辦方式", "單位", "時限", "文件", "指引", "完成", "備註"]
    df_export.to_excel(writer, index=False, sheet_name='SOP詳表')

st.download_button(
    label="📥 下載 Excel 進度表",
    data=buffer.getvalue(),
    file_name=f"SOP_Paperless_{date.today()}.xlsx",
    mime="application/vnd.ms-excel"
)