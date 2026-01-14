import streamlit as st
import pandas as pd
import io
from datetime import date

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="建案行政SOP系統 (旗艦參數版)",
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
    .tag-online { background-color: #e3f2fd; color: #0d47a1; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; border: 1px solid #90caf9; }
    .tag-paper { background-color: #efebe9; color: #5d4037; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; border: 1px solid #bcaaa4; }
    .tag-demo { background-color: #ffcdd2; color: #b71c1c; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; border: 1px solid #ef9a9a; }

    /* 關鍵警語 */
    .critical-info {
        color: #d32f2f; font-size: 0.9em; font-weight: bold; margin-left: 25px; margin-bottom: 5px;
        background-color: #ffebee; padding: 2px 8px; border-radius: 4px; display: inline-block;
    }
    
    /* 資訊框 */
    .info-box { background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 5px solid #6c757d; font-size: 0.9em; margin-bottom: 5px; }
    .step-box { background-color: #e0f7fa; padding: 10px; border-radius: 5px; font-size: 0.9em; margin-top: 5px; }
    
    .nw-header { background-color: #e8f5e9; padding: 10px; border-radius: 5px; border: 1px solid #c8e6c9; margin-bottom: 10px; font-weight: bold; color: #2e7d32; }
    div[data-testid="stExpander"] { margin-top: -5px; }
</style>
""", unsafe_allow_html=True)

st.title("🏗️ 建案開工至放樣 SOP 控管系統 (旗艦參數版)")
st.caption("依據：申辦開工終極版清冊 + 實務門檻參數自動判斷")

# --- 2. 側邊欄：參數輸入 (這是系統變聰明的關鍵) ---
with st.sidebar:
    st.header("⚙️ 專案參數設定")
    
    # 案件類型
    project_type = st.radio("案件類型", ["素地新建案", "拆除併建造執照案"])
    is_demo_project = (project_type == "拆除併建造執照案")
    
    st.divider()
    
    # 規模參數 (用來觸發條件)
    st.subheader("📏 工程規模 (自動判斷審查門檻)")
    total_area = st.number_input("總樓地板面積 (m²)", value=0, step=100, help="超過10000m²需交維計畫")
    base_area = st.number_input("基地/施工面積 (m²)", value=0, step=100, help="計算逕流廢水用")
    duration_month = st.number_input("預計工期 (月)", value=12, step=1)
    
    excavation_depth = st.number_input("開挖深度 (m)", value=0.0, step=0.5, help="超過12m或地下3層需外審")
    building_height = st.number_input("建築高度 (m)", value=0.0, step=1.0, help="超過50m或15層需外審")
    span_rc = st.number_input("RC最大跨距 (m)", value=0.0, step=0.5, help="超過12m需外審")
    
    # 計算邏輯
    is_traffic_plan_needed = total_area > 10000
    is_water_plan_needed = (base_area * duration_month) >= 4600
    is_external_review_needed = (
        excavation_depth > 12 or 
        building_height > 50 or 
        span_rc > 12 or 
        base_area > 3000
    )
    is_danger_d_needed = (
        building_height >= 80 or 
        excavation_depth >= 18 # 簡化判斷
    )

    st.divider()
    if st.button("🔄 重置/重新載入"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

# --- 3. 核心資料庫 ---
def get_initial_sop():
    # 根據輸入參數動態生成警語
    water_msg = "⚠️ 需辦理 (數值達標)" if is_water_plan_needed else "✅ 免辦理 (未達4600門檻)"
    traffic_msg = "⚠️ 強制辦理 (面積>10000m²)" if is_traffic_plan_needed else ""
    external_msg = "⚠️ 需辦理施工計畫外審 (公會審查)" if is_external_review_needed else ""
    danger_msg = "⚠️ 需辦理丁類危評" if is_danger_d_needed else ""

    return {
        "stage_0": [ 
            {
                "item": "建築執照申請作業", "dept": "建築師/建管處", "method": "線上", "timing": "【掛號階段】", 
                "docs": "1. 申請書電子檔\n2. 書圖文件", "critical": "", 
                "details": "透過無紙化審查系統上傳。需使用自然人憑證。", "demo_only": False, "done": False, "note": ""
            },
            {
                "item": "領取建造執照", "dept": "建管處", "method": "臨櫃", "timing": "【校對完成後】", 
                "docs": "1. 規費收據", "critical": "", 
                "details": "繳納規費後領取紙本執照。", "demo_only": False, "done": False, "note": ""
            }
        ],
        "stage_1": [ 
            {
                "item": "空氣污染防制費申報", "dept": "環保局", "method": "線上", "timing": "【開工前】", 
                "docs": "1. 申報書\n2. 合約書影本\n3. 建照影本", 
                "critical": "⚠️ 面積>500m²或金額>500萬者需列管 B8", 
                "details": """
                **臺北市營建工程空污費網路申報系統 (作業步驟)：**
                1. 註冊帳號 (02-27208889#7252)
                2. 系統登入
                3. 填寫資料及上傳文件
                4. 查詢審查進度
                5. 下載繳款書 (Email通知)
                6. 繳款
                """, 
                "demo_only": False, "done": False, "note": ""
            },
            {
                "item": "建照科行政驗收抽查", "dept": "建管處(建照科)", "method": "臨櫃", "timing": "【開工申報前】", 
                "docs": "1. 抽查紀錄表\n2. 缺失改善報告", 
                "critical": "⚠️ 關鍵門檻：缺失修正後，方得辦理開工", 
                "details": "單一拆照或拆併建照案(公會協審案件)必辦。", "demo_only": True, "done": False, "note": ""
            },
            {
                "item": "撤管防空避難設備", "dept": "警察分局", "method": "紙本", "timing": "【開工前】", 
                "docs": "1. 函知公文 (取得掛件收文戳章)", "critical": "", 
                "details": "函知管區警察分局。", "demo_only": True, "done": False, "note": ""
            },
            {
                "item": "開工前置-逕流廢水削減計畫", "dept": "環保局", "method": "線上", "timing": "【開工前】", 
                "docs": "1. 削減計畫書\n2. 沉沙池圖說", 
                "critical": water_msg, 
                "details": "門檻：面積 × 工期(月) 達 4600 (m²·月) 均需辦理。屬環評基地需經公會審查。", 
                "demo_only": False, "done": False, "note": ""
            },
            {
                "item": "開工申報 (正式掛號)", "dept": "建管處", "method": "線上", "timing": "【建照後6個月內】", 
                "docs": "⚠️ 確認 NW 文件備齊 (詳見上方檢查表)", 
                "critical": "⚠️ 線上掛號後 1 日內需親送正本核對", 
                "details": "需使用 HICOS 憑證元件及工商憑證。", "demo_only": False, "done": False, "note": ""
            }
        ],
        "stage_2": [ 
            {
                "item": "施工計畫說明會 (外審)", "dept": "相關公會", "method": "會議", "timing": "【計畫核定前】", 
                "docs": "1. 施工計畫書\n2. 簡報", 
                "critical": external_msg, 
                "details": """
                **需辦理外審條件 (符合其一即須辦理)：**
                1. 山坡地開挖整地 > 3000m²
                2. 開挖深 > 12m 或地下 > 3層 或範圍 > 3000m²
                3. 高度 > 50m 或 > 15層
                4. RC跨距 > 12m 或 鋼骨 > 35m
                5. 擋土結構 > 9m
                6. 地質敏感區 (士林蘭雅、基隆河新生地等)
                7. 列管廠商 (如: 華大成, 互助, 根基, 忠明等)
                """, 
                "demo_only": False, "done": False, "note": ""
            },
            {
                "item": "交通維持計畫", "dept": "交通局", "method": "紙本", "timing": "【施工計畫前】", 
                "docs": "1. 交維計畫書", 
                "critical": traffic_msg, 
                "details": "樓地板面積總和超過 10000m² 者強制辦理。需配合施工大門、車行坡道、塔吊作業規劃。", 
                "demo_only": False, "done": False, "note": ""
            },
            {
                "item": "危險性工作場所評估 (丁類)", "dept": "勞檢處", "method": "線上", "timing": "【開工前】", 
                "docs": "1. 危評報告書", 
                "critical": danger_msg, 
                "details": "建築高度>80m、開挖>18m且面積>500m²、模板支撐高度>7m等。", 
                "demo_only": False, "done": False, "note": ""
            },
            {
                "item": "舊屋拆除與廢棄物結案", "dept": "環保局/建管處", "method": "線上", "timing": "【拆除後】", 
                "docs": "1. 結案申報書", 
                "critical": "⚠️ B5/B8 未結案，無法進行放樣", 
                "details": "拆除完成後，需將廢棄物清理計畫結案。", "demo_only": True, "done": False, "note": ""
            }
        ],
        "stage_3": [ 
            {
                "item": "導溝勘驗申報", "dept": "建管處", "method": "線上", "timing": "【施工前2日】", 
                "docs": "1. 申請書\n2. 照片", "critical": "", 
                "details": "", "demo_only": False, "done": False, "note": ""
            }
        ],
        "stage_4": [ 
             {
                "item": "地界複丈/路心樁復原", "dept": "地政事務所", "method": "臨櫃", "timing": "【拆除後、放樣前】", 
                "docs": "1. 複丈申請書", "critical": "", 
                "details": "拆除後需重新確認地界。", "demo_only": True, "done": False, "note": ""
            },
            {
                "item": "放樣勘驗申報", "dept": "建管處", "method": "線上", "timing": "【結構施工前】", 
                "docs": "1. 報告書\n2. 成果圖", "critical": "", 
                "details": "若期限內無法放樣，需辦理達開工標準。", "demo_only": False, "done": False, "note": ""
            }
        ]
    }

# --- 3. NW 文件清單 (深度整合用印細節) ---
def get_nw_checklist():
    # 格式：編號, 名稱, 詳細備註(用印), 是否僅拆除案
    return [
        ("NW0100", "建築工程開工申報書", "起造人表頭及位置欄用章、建築師、營造廠、技師、工地主任簽章", False),
        ("NW0200", "起造人名冊", "各起造人用起造章", False),
        ("NW0500", "建築執照正本/影本", "需掃描正本 (若變更過起造人需附變更申請書)", False),
        ("NW0900", "基地位置圖", "A4大小、營造廠大小章", False),
        ("NW1000", "空氣污染防治費收據影本", "含環保局核定單、營造廠大小章", False),
        ("NW1100", "逕流廢水削減計畫核備公函", "營造廠大小章 (達4600門檻者必備)", False),
        ("NW1400", "施工計劃書簽章負責表", "起造人、建築師、營造廠、工地主任簽章", False),
        ("NW1500", "營造業承攬手冊(登記證書)", "浮貼負責人及技師照片之簽名影本", False),
        ("NW1600", "營造業承攬手冊(負責人簽章)", "彩色影印", False),
        ("NW1700", "營造業承攬手冊(專任工程人員簽章)", "彩色影印", False),
        ("NW1800", "專任工程人員公會會員證", "當年度正本 (主任建築師附及格證書)", False),
        ("NW1900", "工地主任(會員證)", "營造廠大小章", False),
        ("NW2000", "工地主任(執業證)", "營造廠大小章", False),
        ("NW2100", "監造建築師(會員證)", "當年度正本", False),
        ("NW2200", "監造建築師(執業證/開業證書)", "核對印鑑用 (若非原設計人需附開業手冊正本)", False),
        ("NW2300", "鄰房現況鑑定報告/切結書", "拆照案強制鑑定 / 素地可切結", False), 
        ("NW2400", "拆除施工計畫書", "依營建署格式 (起造人/建築師/營造廠/技師簽章)", True), 
        ("NW2500", "監拆報告書", "建管網站下載 (建築師用章)", True), 
        ("NW2600", "拆除剩餘資源備查公文", "都發局核准函 (B5)", True), 
        ("NW2700", "拆除廢棄物清理計畫備查公文", "環保局核准函 (B8)", True), 
        ("NW2900", "塔式起重機自主檢查表", "無則附 NW3000 切結書", False),
        ("NW9900", "其他文件", "如：合約封面/總價頁(山坡地案)、候選綠建築證書(公有>5000萬)", False)
    ]

# --- 4. 初始化 ---
if "sop_data" not in st.session_state:
    st.session_state.sop_data = get_initial_sop()

if "nw_status" not in st.session_state:
    st.session_state.nw_status = {code: False for code, _, _, _ in get_nw_checklist()}

data = st.session_state.sop_data

# --- 5. Callback ---
def toggle_status(stage_key, index):
    st.session_state.sop_data[stage_key][index]['done'] = not st.session_state.sop_data[stage_key][index]['done']

def toggle_nw(code):
    st.session_state.nw_status[code] = not st.session_state.nw_status[code]

# --- 6. 渲染 SOP 列表 ---
def render_stage_detailed(stage_key, is_locked=False):
    stage_items = data[stage_key]
    if is_locked:
        st.markdown('<div class="locked-stage">🔒 此階段鎖定中 (請先完成上一階段)</div>', unsafe_allow_html=True)

    visible_count = 0
    for i, item in enumerate(stage_items):
        if item.get("demo_only") and not is_demo_project:
            continue
            
        visible_count += 1
        with st.container():
            col1, col2 = st.columns([0.5, 9.5])
            with col1:
                st.checkbox("", value=item['done'], key=f"chk_{stage_key}_{i}", on_change=toggle_status, args=(stage_key, i), disabled=is_locked)
            with col2:
                method = item.get('method', '現場')
                method_tag = f'<span class="tag-online">🔵 線上</span>' if method == "線上" else f'<span class="tag-paper">🟤 {method}</span>'
                demo_tag = '<span class="tag-demo">🏗️ 拆除專項</span>' if item.get("demo_only") else ""
                
                title_html = f"**{item['item']}** {method_tag} {demo_tag} <span style='color:#666; font-size:0.9em'>(🏢 {item['dept']})</span>"
                if item['done']:
                    st.markdown(f"<span style='color:#2E7D32; font-weight:bold;'>✅ {item['item']}</span>", unsafe_allow_html=True)
                else:
                    st.markdown(title_html, unsafe_allow_html=True)
                
                # 自動判斷的警語
                if item.get("critical"):
                     st.markdown(f"<div class='critical-info'>{item['critical']}</div>", unsafe_allow_html=True)

                with st.expander("🔽 詳細指引與備註", expanded=False):
                    st.markdown(f"**🕒 時機：** {item['timing']}")
                    st.markdown(f"**📄 應備文件：**\n{item['docs']}")
                    if item['details']:
                        st.markdown(f"<div class='info-box'>💡 <b>作業指引：</b><br>{item['details']}</div>", unsafe_allow_html=True)
                    new_note = st.text_input("備註", value=item['note'], key=f"note_{stage_key}_{i}")
                    st.session_state.sop_data[stage_key][i]['note'] = new_note
        st.divider()
    
    if visible_count == 0:
        st.info("此階段無相關項目需辦理。")

# --- 7. 主流程 ---
s0_done = all(item['done'] for item in data['stage_0'])
permit_unlocked = s0_done

tabs = st.tabs(["0.建照領取", "1.開工申報(掛號)", "2.施工計畫/拆除", "3.導溝勘驗", "4.放樣勘驗"])

with tabs[0]:
    st.subheader("🔑 階段零：建照領取")
    render_stage_detailed("stage_0", is_locked=False)

with tabs[1]:
    st.subheader("📋 階段一：開工申報 (含NW文件檢查)")
    if not permit_unlocked:
        st.markdown('<div class="locked-stage">🔒 請先完成建照領取階段</div>', unsafe_allow_html=True)
    else:
        with st.expander("📑 「NW 開工文件」準備檢查表 (掛號前必備)", expanded=True):
            st.markdown('<div class="nw-header">請確認以下 PDF 檔案已備齊並完成用印/掃描：</div>', unsafe_allow_html=True)
            for code, name, note, demo_only in get_nw_checklist():
                if demo_only and not is_demo_project: continue
                c1, c2, c3 = st.columns([0.5, 4, 5.5])
                with c1: st.checkbox("", value=st.session_state.nw_status[code], key=f"nw_{code}", on_change=toggle_nw, args=(code,))
                with c2: 
                    d_tag = '<span class="tag-demo">拆</span>' if demo_only else ""
                    st.markdown(f"<span style='{'color:#2E7D32; font-weight:bold;' if st.session_state.nw_status[code] else ''}'>{code} {name} {d_tag}</span>", unsafe_allow_html=True)
                with c3: st.caption(f"🖊️ {note}")
        
        st.markdown("---")
        st.markdown("### ✅ 正式申報流程")
        render_stage_detailed("stage_1", is_locked=False)

with tabs[2]:
    st.subheader("📘 階段二：施工計畫 & 拆除作業")
    render_stage_detailed("stage_2", is_locked=not permit_unlocked)

with tabs[3]:
    st.subheader("🚧 階段三：導溝勘驗")
    render_stage_detailed("stage_3", is_locked=not permit_unlocked)

with tabs[4]:
    st.subheader("📐 階段四：放樣勘驗")
    render_stage_detailed("stage_4", is_locked=not permit_unlocked)

# --- 8. Excel 下載 ---
st.write("---")
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    all_rows = []
    for k, v in data.items():
        for item in v:
            if item.get("demo_only") and not is_demo_project: continue
            item_copy = item.copy()
            item_copy['階段代號'] = k
            all_rows.append(item_copy)
    df_export = pd.DataFrame(all_rows)
    df_export = df_export[["階段代號", "item", "critical", "docs", "details", "done", "note"]]
    df_export.to_excel(writer, index=False, sheet_name='SOP')
    
st.download_button("📥 下載 Excel", buffer.getvalue(), f"SOP_{date.today()}.xlsx", "application/vnd.ms-excel")