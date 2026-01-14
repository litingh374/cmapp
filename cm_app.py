import streamlit as st
import pandas as pd
import io
from datetime import date

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="建案行政SOP系統 (智能切換版)",
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
    
    /* 拆除案件專屬標籤 */
    .tag-demo {
        background-color: #ffebee; color: #c62828; padding: 2px 8px; 
        border-radius: 4px; font-size: 0.8em; font-weight: bold; border: 1px solid #ef9a9a;
    }

    /* 關鍵警語 */
    .critical-info {
        color: #d32f2f; font-size: 0.9em; font-weight: bold; margin-left: 25px; margin-bottom: 5px;
        background-color: #ffebee; padding: 2px 8px; border-radius: 4px; display: inline-block;
    }
    
    /* 資訊框 */
    .info-box {
        background-color: #f8f9fa; padding: 10px; border-radius: 5px; 
        border-left: 5px solid #6c757d; font-size: 0.9em; margin-bottom: 5px;
    }
    .nw-header {
        background-color: #e8f5e9; padding: 10px; border-radius: 5px; 
        border: 1px solid #c8e6c9; margin-bottom: 10px; font-weight: bold; color: #2e7d32;
    }
    div[data-testid="stExpander"] { margin-top: -5px; }
</style>
""", unsafe_allow_html=True)

st.title("🏗️ 建案開工至放樣 SOP 控管系統 (智能切換版)")
st.caption("系統將依據您選擇的「新建」或「拆併建」類型，自動篩選所需項目。")

# --- 2. 核心資料庫 (標註 'demo_only' 屬性) ---
def get_initial_sop():
    return {
        "stage_0": [ 
            {
                "item": "建築執照申請作業", 
                "dept": "建築師/建管處", 
                "method": "線上",
                "timing": "【掛號階段】", 
                "docs": "1. 申請書電子檔 (XML/PDF)\n2. 建照圖/結構圖 (D1/S1)\n3. 鑽探報告", 
                "critical": "", 
                "details": "透過「建築執照無紙化審查系統」上傳。需使用自然人憑證進行電子簽章。核准後直接線上進行副本校對。", 
                "demo_only": False, # 通用
                "done": False, "note": ""
            },
            {
                "item": "領取建造執照", 
                "dept": "建管處", 
                "method": "臨櫃", 
                "timing": "【校對完成後】", 
                "docs": "1. 規費收據", 
                "critical": "",
                "details": "雖然審查過程無紙化，但最終「紙本執照」通常仍需臨櫃領取（視各縣市規定）。", 
                "demo_only": False,
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
                "critical": "⚠️ 大同區迪化街區、拆照案強制辦理", 
                "details": "拆併建照案若不辦理需檢附「不作鄰房鑑定切結書」(責任自負)。如鄰房屬老舊建物，需增加安全及補強評估報告。", 
                "demo_only": False, # 新建也可能需要，但拆除更強制
                "done": False, "note": ""
            },
            {
                "item": "開工前置-廢棄物處理計畫 (拆除)", 
                "dept": "施工科/環保局", 
                "method": "線上",
                "timing": "【開工前】", 
                "docs": "1. 拆除土石方(B5)核准函\n2. 營建混合物(B8)核准函", 
                "critical": "⚠️ 拆除規模達地上10層以上，需先辦理拆除計畫外審", 
                "details": "若現場無B5土方，列管數量應修正為0。需向施工科申請 B5，向環保局申請 B8。", 
                "demo_only": True, # [關鍵] 只有拆除案需要顯示
                "done": False, "note": ""
            },
            {
                "item": "開工前置-逕流廢水削減計畫", 
                "dept": "環保局", 
                "method": "線上",
                "timing": "【開工前】", 
                "docs": "1. 削減計畫書\n2. 沉沙池圖說", 
                "critical": "⚠️ 門檻：面積 × 工期(月) 達 4600 (m²·月) 均需辦理", 
                "details": "包含拆除工程或建築工程，只要符合上述公式即須辦理。", 
                "demo_only": False,
                "done": False, "note": ""
            },
            {
                "item": "開工前置-撤管防空避難設備", 
                "dept": "警察分局", 
                "method": "紙本",
                "timing": "【開工前】", 
                "docs": "1. 函知公文", 
                "critical": "", 
                "details": "函知管區警察分局，撤管拆照建物之防空避難設備。", 
                "demo_only": True, # [關鍵] 只有拆除案需要
                "done": False, "note": ""
            },
            {
                "item": "開工前置-其他事項", 
                "dept": "各單位", 
                "method": "混合",
                "timing": "【開工前】", 
                "docs": "1. 工地主任上課證明", 
                "critical": "",
                "details": "工地主任應報名參加建管處施工科之建管作業上課說明。", 
                "demo_only": False,
                "done": False, "note": ""
            },
            {
                "item": "開工申報 (正式掛號)", 
                "dept": "建管處", 
                "method": "線上",
                "timing": "【建照後6個月內】", 
                "docs": "⚠️ 請務必確認上方 NW 文件皆已備齊", 
                "critical": "⚠️ 線上掛號後 1 日內需親送正本核對", 
                "details": "需使用 HICOS 憑證元件及工商憑證。核對無誤以系統送出日為準。", 
                "demo_only": False,
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
                "critical": "⚠️ 捷運沿線案：需先通報捷運局", 
                "details": "需至建管業務e辦網上傳。", 
                "demo_only": False,
                "done": False, "note": ""
            },
            {
                "item": "職業安全衛生計畫", 
                "dept": "勞檢處", 
                "method": "線上", 
                "timing": "【開工前】", 
                "docs": "1. 安衛計畫書", 
                "critical": "⚠️ 危險性工作場所：需丁類審查",
                "details": "至職安署網站登錄。", 
                "demo_only": False,
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
                "critical": "",
                "details": "屬施工勘驗項目。", 
                "demo_only": False,
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
                "critical": "⚠️ 若期限內無法放樣，需先辦理展期或「達開工標準」",
                "details": "需將測量成果與技師簽證文件掃描上傳。", 
                "demo_only": False,
                "done": False, "note": ""
            },
             {
                "item": "基地鑑界 (複丈)", 
                "dept": "地政事務所", 
                "method": "臨櫃", 
                "timing": "【放樣前】", 
                "docs": "1. 複丈申請書", 
                "critical": "",
                "details": "確認界址點。", 
                "demo_only": False,
                "done": False, "note": ""
            }
        ]
    }

# --- 3. NW 文件清單 (標註 'demo_only') ---
def get_nw_checklist():
    # 格式：編號, 名稱, 備註, 是否僅拆除案需要 (True/False)
    return [
        ("NW0100", "建築工程開工申報書", "起造人表頭及位置欄用章、建築師、營造廠、技師、工地主任簽章", False),
        ("NW0200", "起造人名冊", "各起造人用起造章", False),
        ("NW0300", "承造人名冊", "各承造人簽章", False),
        ("NW0400", "監造人名冊", "各監造人簽章", False),
        ("NW0500", "建築執照正本/影本", "需掃描正本", False),
        ("NW0900", "基地位置圖", "A4大小、營造廠大小章", False),
        ("NW1000", "空氣污染防治費收據影本", "含環保局核定單、營造廠大小章", False),
        ("NW1100", "逕流廢水削減計畫核備公函", "營造廠大小章", False),
        ("NW1300", "施工計畫備查資料表", "營造廠大小章", False),
        ("NW1400", "施工計劃書簽章負責表", "起造人、建築師、營造廠、工地主任簽章", False),
        ("NW1500", "營造業承攬手冊(登記證書)", "浮貼負責人及技師照片之簽名影本", False),
        ("NW1600", "營造業承攬手冊(負責人簽章)", "彩色影印", False),
        ("NW1700", "營造業承攬手冊(專任工程人員簽章)", "彩色影印", False),
        ("NW1800", "專任工程人員公會會員證", "當年度正本", False),
        ("NW1900", "工地主任(會員證)", "營造廠大小章", False),
        ("NW2000", "工地主任(執業證)", "營造廠大小章", False),
        ("NW2100", "監造建築師(會員證)", "當年度正本", False),
        ("NW2200", "監造建築師(執業證/開業證書)", "核對印鑑用", False),
        ("NW2300", "鄰房現況鑑定報告/切結書", "有拆除者必備", True), # 拆除案
        ("NW2400", "拆除施工計畫書", "有拆除者必備 (依營建署格式)", True), # 拆除案
        ("NW2500", "監拆報告書", "有拆除者必備 (建築師用章)", True), # 拆除案
        ("NW2600", "拆除剩餘資源備查公文", "都發局核准函", True), # 拆除案
        ("NW2700", "拆除廢棄物清理計畫備查公文", "環保局核准函 (營造廠大小章)", True), # 拆除案
        ("NW2900", "塔式起重機自主檢查表", "或檢附 NW3000 未使用切結書", False)
    ]

# --- 4. 初始化 ---
if "sop_data" not in st.session_state:
    st.session_state.sop_data = get_initial_sop()

if "nw_status" not in st.session_state:
    st.session_state.nw_status = {code: False for code, _, _, _ in get_nw_checklist()}

# --- 5. 側邊欄 ---
with st.sidebar:
    st.header("📝 專案基本資料")
    
    # [新增] 案件類型選擇器
    project_type = st.radio(
        "案件類型", 
        ["素地新建案", "拆除併建造執照案"],
        help="選擇「拆除併建造」會自動顯示拆除相關檢查項目"
    )
    is_demo_project = (project_type == "拆除併建造執照案")
    
    st.divider()
    
    st.text_input("專案名稱", value="範例建案")
    st.text_input("建造執照號碼", placeholder="114建字第00123號")
    st.text_input("基地位置/地號", placeholder="中山區長春段...")
    
    st.divider()
    
    # 重新載入按鈕
    if st.button("🔄 重置/重新載入"):
        st.session_state.sop_data = get_initial_sop()
        st.session_state.nw_status = {code: False for code, _, _, _ in get_nw_checklist()}
        st.rerun()

data = st.session_state.sop_data

# --- 6. Callback ---
def toggle_status(stage_key, index):
    st.session_state.sop_data[stage_key][index]['done'] = not st.session_state.sop_data[stage_key][index]['done']

def toggle_nw(code):
    st.session_state.nw_status[code] = not st.session_state.nw_status[code]

# --- 7. 渲染函數 (含動態過濾) ---
def render_stage_detailed(stage_key, is_locked=False):
    stage_items = data[stage_key]
    
    if is_locked:
        st.markdown('<div class="locked-stage">🔒 此階段鎖定中 (請先完成上一階段)</div>', unsafe_allow_html=True)

    visible_count = 0
    for i, item in enumerate(stage_items):
        # [關鍵邏輯] 過濾掉不需要顯示的項目
        # 如果項目標記為 demo_only=True，但專案是 素地新建 (is_demo_project=False)，則跳過不顯示
        if item.get("demo_only") and not is_demo_project:
            continue
            
        visible_count += 1
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
                # 標籤
                method = item.get('method', '現場')
                method_tag = ""
                if method == "線上":
                    method_tag = '<span class="tag-online">🔵 線上申辦</span>'
                elif method == "臨櫃":
                    method_tag = '<span class="tag-paper">🟤 臨櫃/紙本</span>'
                else:
                    method_tag = f'<span class="tag-paper">{method}</span>'

                # 如果是拆除專用，加個特別標籤
                demo_tag = ""
                if item.get("demo_only"):
                    demo_tag = '<span class="tag-demo">🏗️ 拆除專項</span>'

                title_html = f"**{item['item']}** {method_tag} {demo_tag} <span style='color:#666; font-size:0.9em'>(🏢 {item['dept']})</span>"
                
                if item['done']:
                    st.markdown(f"<span style='color:#2E7D32; font-weight:bold;'>✅ {item['item']}</span>", unsafe_allow_html=True)
                else:
                    st.markdown(title_html, unsafe_allow_html=True)
                
                if item.get("critical"):
                    st.markdown(f"<div class='critical-info'>{item['critical']}</div>", unsafe_allow_html=True)

                with st.expander("🔽 詳細指引與備註", expanded=False):
                    st.markdown(f"**🕒 時機：** {item['timing']}")
                    st.markdown(f"**📄 應備文件：**\n{item['docs']}")
                    if item['details']:
                        st.markdown(f"<div class='info-box'>💡 <b>作業指引：</b><br>{item['details']}</div>", unsafe_allow_html=True)
                    
                    new_note = st.text_input("備註", value=item['note'], key=f"note_{stage_key}_{i}", placeholder="輸入文號或筆記...")
                    st.session_state.sop_data[stage_key][i]['note'] = new_note

        st.divider()
    
    if visible_count == 0:
        st.info("此階段無相關項目需辦理。")

# --- 8. 主流程 ---

# 進度解鎖邏輯 (簡單版：建照完成即解鎖後續)
s0_done = all(item['done'] for item in data['stage_0'])
permit_unlocked = s0_done

tabs = st.tabs(["0.建照領取", "1.開工申報(掛號)", "2.施工計畫", "3.導溝勘驗", "4.放樣勘驗"])

with tabs[0]:
    st.subheader("🔑 階段零：建照領取")
    render_stage_detailed("stage_0", is_locked=False)

with tabs[1]:
    st.subheader("📋 階段一：開工申報 (含NW文件檢查)")
    
    if not permit_unlocked:
        st.markdown('<div class="locked-stage">🔒 請先完成建照領取階段</div>', unsafe_allow_html=True)
    else:
        # [動態 NW 檢查表]
        with st.expander("📑 點此展開「NW 開工文件準備檢查表」", expanded=True):
            st.markdown('<div class="nw-header">請確認以下 PDF 檔案已備齊並完成用印/掃描：</div>', unsafe_allow_html=True)
            checklist = get_nw_checklist()
            
            # 計數顯示
            nw_count = 0
            for code, name, note, demo_only in checklist:
                # 過濾邏輯
                if demo_only and not is_demo_project:
                    continue
                
                nw_count += 1
                c1, c2, c3 = st.columns([0.5, 4, 5.5])
                with c1:
                    st.checkbox("", value=st.session_state.nw_status[code], key=f"nw_{code}", on_change=toggle_nw, args=(code,))
                with c2:
                    # 拆除項目特別標示
                    d_tag = '<span class="tag-demo">拆</span>' if demo_only else ""
                    if st.session_state.nw_status[code]:
                        st.markdown(f"<span style='color:#2E7D32; font-weight:bold;'>{code} {name} {d_tag}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"**{code}** {name} {d_tag}", unsafe_allow_html=True)
                with c3:
                    st.caption(f"🖊️ {note}")
            
            if is_demo_project:
                st.info(f"已顯示 {nw_count} 項文件 (含拆除專用文件)。")
            else:
                st.info(f"已顯示 {nw_count} 項文件 (隱藏拆除專用文件)。")

        st.markdown("---")
        st.markdown("### ✅ 正式申報流程")
        render_stage_detailed("stage_1", is_locked=False)

with tabs[2]:
    st.subheader("📘 階段二：施工計畫")
    render_stage_detailed("stage_2", is_locked=not permit_unlocked)

with tabs[3]:
    st.subheader("🚧 階段三：導溝勘驗")
    render_stage_detailed("stage_3", is_locked=not permit_unlocked)

with tabs[4]:
    st.subheader("📐 階段四：放樣勘驗")
    render_stage_detailed("stage_4", is_locked=not permit_unlocked)

# --- 9. Excel 下載 (含動態過濾) ---
st.write("---")
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    # SOP 匯出
    all_rows = []
    for k, v in data.items():
        for item in v:
            # 匯出時也過濾
            if item.get("demo_only") and not is_demo_project:
                continue
            item_copy = item.copy()
            item_copy['階段代號'] = k
            all_rows.append(item_copy)
    df_export = pd.DataFrame(all_rows)
    df_export['申辦方式'] = df_export.apply(lambda x: x.get('method', '現場'), axis=1)
    df_export = df_export[["階段代號", "item", "申辦方式", "dept", "critical", "timing", "docs", "details", "done", "note"]]
    df_export.columns = ["階段", "項目", "申辦方式", "單位", "重要限制", "時限", "文件", "指引", "完成", "備註"]
    df_export.to_excel(writer, index=False, sheet_name='SOP流程進度')

    # NW 匯出
    nw_data = []
    for code, name, note, demo_only in get_nw_checklist():
        if demo_only and not is_demo_project:
            continue
        nw_data.append({
            "文件編碼": code,
            "文件名稱": name,
            "用印/備註": note,
            "專案類型": "拆除專用" if demo_only else "一般",
            "準備狀態": "已完成" if st.session_state.nw_status[code] else "未完成"
        })
    df_nw = pd.DataFrame(nw_data)
    df_nw.to_excel(writer, index=False, sheet_name='NW文件檢查清單')

st.download_button(
    label="📥 下載 Excel 進度表",
    data=buffer.getvalue(),
    file_name=f"SOP_Smart_{date.today()}.xlsx",
    mime="application/vnd.ms-excel"
)