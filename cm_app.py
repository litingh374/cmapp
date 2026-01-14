import streamlit as st
import pandas as pd
import io
from datetime import date

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="建案行政SOP系統 (專業版)",
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
    .warning-box {
        background-color: #fff3e0; padding: 10px; border-radius: 5px; 
        border-left: 5px solid #ff9800; font-size: 0.9em; margin-bottom: 5px;
    }
    div[data-testid="stExpander"] { margin-top: -5px; }
</style>
""", unsafe_allow_html=True)

st.title("🏗️ 建案開工至放樣 SOP 控管系統 (專業版)")
st.caption("依據：申辦開工、計劃、放樣用清冊 (終極版) ｜ 內建 NW 文件編碼檢查表")

# --- 2. 核心資料庫 ---
def get_initial_sop():
    return {
        "stage_0": [ 
            {
                "item": "建築執照申請作業", 
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
                "item": "開工前置-鄰房鑑定 (公會)", 
                "dept": "技師公會", 
                "method": "紙本",
                "timing": "【開工前】", 
                "docs": "1. 鑑定申請書\n2. 繳費證明\n3. 鄰房清冊", 
                "details": "⚠️ 強制辦理區域：大同區迪化街區(大稻埕歷史風貌特定區)、拆照/拆併建照案。\n💡 若不辦理需檢附「不作鄰房鑑定切結書」(責任自負)。", 
                "done": False, "note": ""
            },
            {
                "item": "開工前置-廢棄物處理計畫", 
                "dept": "環保局/施工科", 
                "method": "線上",
                "timing": "【開工前】", 
                "docs": "1. 拆除土石方(B5)核准函 (向施工科申請)\n2. 營建混合物(B8)核准函 (向環保局申請)", 
                "details": "拆除規模達地上10層以上，需先辦理拆除計畫外審。若現場無B5土方，列管數量應修正為0。", 
                "done": False, "note": ""
            },
            {
                "item": "開工前置-逕流廢水削減計畫", 
                "dept": "環保局", 
                "method": "線上",
                "timing": "【開工前】", 
                "docs": "1. 削減計畫書\n2. 沉沙池圖說", 
                "details": "⚠️ 門檻：環保局(拆除或建築)面積 × 工期(月) 達 4600 (m²·月) 者均需辦理。", 
                "done": False, "note": ""
            },
            {
                "item": "開工前置-其他事項", 
                "dept": "各單位", 
                "method": "混合",
                "timing": "【開工前】", 
                "docs": "1. 函知警察分局(撤管防空避難)\n2. 工地主任上課證明", 
                "details": "拆照案需函知管區警察分局。工地主任應報名參加建管處施工科之建管作業上課說明。", 
                "done": False, "note": ""
            },
            {
                "item": "開工申報 (正式掛號)", 
                "dept": "建管處", 
                "method": "線上",
                "timing": "【建照後6個月內】", 
                "docs": "詳見「NW文件檢查表」分頁", 
                "details": "需使用 HICOS 憑證元件及工商憑證。線上掛號後 1 日內需將正本親送櫃台審查(核對無誤以系統送出日為準)。", 
                "done": False, "note": ""
            }
        ],
        "stage_2": [ 
            {
                "item": "施工計畫書申報", 
                "dept": "建管處", 
                "method": "線上",
                "timing": "【放樣前】", 
                "docs": "1. 施工計畫書 (PDF)\n2. 技師簽證", 
                "details": "需至建管業務e辦網上傳。如為捷運沿線案，需先通報捷運局。", 
                "done": False, "note": ""
            },
            {
                "item": "職業安全衛生計畫", 
                "dept": "勞檢處", 
                "method": "線上", 
                "timing": "【開工前】", 
                "docs": "1. 安衛計畫書", 
                "details": "至職安署網站登錄。危險性工作場所需丁類審查。", 
                "done": False, "note": ""
            }
        ],
        "stage_3": [ 
            {
                "item": "導溝勘驗申報", 
                "dept": "建管處", 
                "method": "線上",
                "timing": "【施工前2日】", 
                "docs": "1. 勘驗申請書\n2. 照片\n3. 專任人員證書", 
                "details": "屬施工勘驗項目。", 
                "done": False, "note": ""
            }
        ],
        "stage_4": [ 
            {
                "item": "放樣勘驗申報", 
                "dept": "建管處", 
                "method": "線上",
                "timing": "【結構施工前】", 
                "docs": "1. 放樣勘驗報告書\n2. 測量成果圖\n3. 現場照片", 
                "details": "若建照領照後6個月內無法完成放樣，需先辦理開工展期(3個月)或「達開工標準」報備。", 
                "done": False, "note": ""
            },
             {
                "item": "基地鑑界 (複丈)", 
                "dept": "地政事務所", 
                "method": "臨櫃", 
                "timing": "【放樣前】", 
                "docs": "1. 複丈申請書", 
                "details": "確認界址點。", 
                "done": False, "note": ""
            }
        ]
    }

# --- 3. NW 文件清單資料庫 (這是您提供的詳細清單) ---
def get_nw_checklist():
    # 格式：編號, 文件名稱, 用印規定/備註
    return [
        ("NW0100", "建築工程開工申報書", "起造人表頭及位置欄用章、建築師、營造廠、技師、工地主任簽章"),
        ("NW0200", "起造人名冊", "各起造人用起造章"),
        ("NW0300", "承造人名冊", "各承造人簽章"),
        ("NW0400", "監造人名冊", "各監造人簽章"),
        ("NW0500", "建築執照正本/影本", "需掃描正本"),
        ("NW0900", "基地位置圖", "A4大小、營造廠大小章"),
        ("NW1000", "空氣污染防治費收據影本", "含環保局核定單、營造廠大小章"),
        ("NW1100", "逕流廢水削減計畫核備公函", "營造廠大小章"),
        ("NW1300", "施工計畫備查資料表", "營造廠大小章"),
        ("NW1400", "施工計劃書簽章負責表", "起造人、建築師、營造廠、工地主任簽章"),
        ("NW1500", "營造業承攬手冊(登記證書)", "浮貼負責人及技師照片之簽名影本"),
        ("NW1600", "營造業承攬手冊(負責人簽章)", "彩色影印"),
        ("NW1700", "營造業承攬手冊(專任工程人員簽章)", "彩色影印"),
        ("NW1800", "專任工程人員公會會員證", "當年度正本"),
        ("NW1900", "工地主任(會員證)", "營造廠大小章"),
        ("NW2000", "工地主任(執業證)", "營造廠大小章"),
        ("NW2100", "監造建築師(會員證)", "當年度正本"),
        ("NW2200", "監造建築師(執業證/開業證書)", "核對印鑑用"),
        ("NW2300", "鄰房現況鑑定報告/切結書", "有拆除者必備"),
        ("NW2400", "拆除施工計畫書", "有拆除者必備 (依營建署格式)"),
        ("NW2500", "監拆報告書", "有拆除者必備 (建築師用章)"),
        ("NW2600", "拆除剩餘資源備查公文", "都發局核准函"),
        ("NW2700", "拆除廢棄物清理計畫備查公文", "環保局核准函 (營造廠大小章)"),
        ("NW2900", "塔式起重機自主檢查表", "或檢附 NW3000 未使用切結書")
    ]

# --- 4. 初始化 ---
if "sop_data" not in st.session_state:
    st.session_state.sop_data = get_initial_sop()
    
# 初始化 NW 檢查表狀態
if "nw_status" not in st.session_state:
    st.session_state.nw_status = {code: False for code, _, _ in get_nw_checklist()}

data = st.session_state.sop_data

# --- 5. 狀態 Callback ---
def toggle_status(stage_key, index):
    current_status = st.session_state.sop_data[stage_key][index]['done']
    st.session_state.sop_data[stage_key][index]['done'] = not current_status

def toggle_nw(code):
    st.session_state.nw_status[code] = not st.session_state.nw_status[code]

# --- 6. 側邊欄 ---
with st.sidebar:
    st.header("📝 專案基本資料")
    st.text_input("專案名稱", value="範例建案")
    st.text_input("建造執照號碼", placeholder="114建字第00123號")
    st.text_input("基地位置/地號", placeholder="中山區長春段...")
    
    st.divider()
    
    # 進度計算
    s0_total = len(data['stage_0'])
    s0_done = sum(1 for item in data['stage_0'] if item['done'])
    permit_unlocked = (s0_done == s0_total)
    
    if permit_unlocked:
        st.success("✅ 建照領取：完成")
    else:
        st.warning(f"⚠️ 建照領取：{s0_done}/{s0_total}")

    st.divider()
    if st.button("🔄 重置所有進度"):
        st.session_state.sop_data = get_initial_sop()
        st.session_state.nw_status = {code: False for code, _, _ in get_nw_checklist()}
        st.rerun()

# --- 7. 渲染 SOP 列表函數 ---
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
                        # 這裡使用 warning-box 顯示重要限制 (如面積門檻)
                        st.markdown(f"<div class='warning-box'><b>⚠️ 注意事項：</b><br>{item['details']}</div>", unsafe_allow_html=True)
                    
                    new_note = st.text_input("備註", value=item['note'], key=f"note_{stage_key}_{i}", placeholder="輸入文號或筆記...")
                    st.session_state.sop_data[stage_key][i]['note'] = new_note

        st.divider()

# --- 8. 主畫面 ---

current = 0
s1_done = all(i['done'] for i in data['stage_1'])
s2_done = all(i['done'] for i in data['stage_2'])

if permit_unlocked: current += 1
if permit_unlocked and s1_done: current += 1
if current >= 2 and s2_done: current += 1
if current >= 3 and all(i['done'] for i in data['stage_3']): current += 1

st.progress(current/5, text=f"專案總進度")

# [新增] "NW開工文件檢查表" 分頁
tabs = st.tabs(["0.建照領取", "1.開工申報", "📑 NW文件檢查表", "2.施工計畫", "3.導溝勘驗", "4.放樣勘驗"])

with tabs[0]:
    st.subheader("🔑 階段零：建照領取")
    render_stage_detailed("stage_0", is_locked=False)

with tabs[1]:
    st.subheader("📋 階段一：開工申報")
    render_stage_detailed("stage_1", is_locked=not permit_unlocked)

with tabs[2]:
    st.subheader("📑 NW 開工文件編碼與用印檢查表")
    st.info("請依照下表準備 PDF 檔案，檔名需符合 NW 編碼。勾選代表已確認「用印無誤」並「掃描完成」。")
    
    checklist = get_nw_checklist()
    
    # 建立檢查表表格
    for code, name, note in checklist:
        c1, c2, c3 = st.columns([0.5, 4, 5.5])
        with c1:
            st.checkbox(
                "", 
                value=st.session_state.nw_status[code], 
                key=f"nw_{code}",
                on_change=toggle_nw,
                args=(code,)
            )
        with c2:
            # 完成變綠色
            if st.session_state.nw_status[code]:
                st.markdown(f"<span style='color:#2E7D32; font-weight:bold;'>{code} {name}</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"**{code}** {name}")
        with c3:
            st.caption(f"🖊️ {note}")
        st.divider()

with tabs[3]:
    st.subheader("📘 階段二：施工計畫")
    render_stage_detailed("stage_2", is_locked=not (permit_unlocked and s1_done))

with tabs[4]:
    st.subheader("🚧 階段三：導溝勘驗")
    render_stage_detailed("stage_3", is_locked=not (s2_done and s1_done))

with tabs[5]:
    st.subheader("📐 階段四：放樣勘驗")
    render_stage_detailed("stage_4", is_locked=not all(i['done'] for i in data['stage_3']))

# --- 9. Excel 下載 (含檢查表) ---
st.write("---")
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    # Sheet 1: 流程進度
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
    df_export.to_excel(writer, index=False, sheet_name='SOP流程進度')

    # Sheet 2: NW檢查表
    nw_data = []
    for code, name, note in get_nw_checklist():
        nw_data.append({
            "文件編碼": code,
            "文件名稱": name,
            "用印/備註": note,
            "準備狀態": "已完成" if st.session_state.nw_status[code] else "未完成"
        })
    df_nw = pd.DataFrame(nw_data)
    df_nw.to_excel(writer, index=False, sheet_name='NW文件檢查清單')

st.download_button(
    label="📥 下載完整 Excel (含NW檢查表)",
    data=buffer.getvalue(),
    file_name=f"SOP_Construction_Full_{date.today()}.xlsx",
    mime="application/vnd.ms-excel"
)