import streamlit as st
import pandas as pd
import io  # [修正] 補上這個必要的套件
from datetime import date

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="建案行政SOP系統 (最終修復版)",
    page_icon="🏗️",
    layout="wide"
)

# --- 2. 🛡️ 版本控制與強制重置 ---
# 只要這個數字改變，使用者的瀏覽器暫存就會被強制清空，解決所有新舊資料衝突
CURRENT_VERSION = 5.2

if "data_version" not in st.session_state:
    st.session_state.clear()
    st.session_state.data_version = CURRENT_VERSION
elif st.session_state.data_version != CURRENT_VERSION:
    st.session_state.clear()
    st.session_state.data_version = CURRENT_VERSION
    st.rerun()

# --- CSS 美化 ---
st.markdown("""
<style>
    div[data-testid="stCheckbox"] label span[data-checked="true"] {
        background-color: #2E7D32 !important;
        border-color: #2E7D32 !important;
    }
    .stProgress > div > div > div > div { background-color: #2E7D32; }
    .tag-online { background-color: #e3f2fd; color: #0d47a1; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; border: 1px solid #90caf9; }
    .tag-paper { background-color: #efebe9; color: #5d4037; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; border: 1px solid #bcaaa4; }
    .tag-demo { background-color: #ffcdd2; color: #b71c1c; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; border: 1px solid #ef9a9a; }
    .critical-info {
        color: #d32f2f; font-size: 0.9em; font-weight: bold; margin-left: 25px; margin-bottom: 5px;
        background-color: #ffebee; padding: 2px 8px; border-radius: 4px; display: inline-block;
    }
    .info-box { background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 5px solid #6c757d; font-size: 0.9em; margin-bottom: 5px; }
    .nw-header { background-color: #e8f5e9; padding: 10px; border-radius: 5px; border: 1px solid #c8e6c9; margin-bottom: 10px; font-weight: bold; color: #2e7d32; }
    div[data-testid="stExpander"] { margin-top: -5px; }
</style>
""", unsafe_allow_html=True)

st.title("🏗️ 建案開工至放樣 SOP 控管系統 (最終修復版)")
st.caption("已修復：重複文件報錯問題、解鎖邏輯、Excel下載功能")

# --- 3. 定義完整文件清單 (資料庫) ---
def get_all_checklists():
    # 1. 開工申報 (NW0100-NW3100)
    list_start = [
        ("NW0100", "建築工程開工申報書", "起造/建築/營造/技師/工地主任簽章", False),
        ("NW0200", "起造人名冊", "各起造人用起造章", False),
        ("NW0500", "建築執照正本/影本", "需掃描正本", False),
        ("NW0900", "基地位置圖", "A4大小、營造廠大小章", False),
        ("NW1000", "空氣污染防治費收據影本", "含核定單、營造廠大小章", False),
        ("NW1100", "逕流廢水削減計畫核備公函", "營造廠大小章 (達4600門檻者)", False),
        ("NW1500", "營造業承攬手冊(登記證書)", "浮貼負責人及技師照片之簽名影本", False),
        ("NW1600", "營造業承攬手冊(負責人簽章)", "彩色影印", False),
        ("NW1700", "營造業承攬手冊(專任工程人員簽章)", "彩色影印", False),
        ("NW1800", "專任工程人員公會會員證", "當年度正本", False),
        ("NW1900", "工地主任(會員證)", "營造廠大小章", False),
        ("NW2000", "工地主任(執業證)", "營造廠大小章", False),
        ("NW2100", "監造建築師(會員證)", "當年度正本", False),
        ("NW2300", "鄰房現況鑑定報告/切結書", "拆照案強制鑑定 / 素地可切結", False), 
        ("NW2400", "拆除施工計畫書", "依營建署格式", True), 
        ("NW2500", "監拆報告書", "建築師用章", True), 
        ("NW2600", "拆除剩餘資源備查公文(B5)", "都發局核准函", True), 
        ("NW2700", "拆除廢棄物清理計畫備查公文(B8)", "環保局核准函", True),
        ("NW2900", "塔式起重機自主檢查表", "無則附切結書", False)
    ]
    
    # 2. 施工計畫 (NW3200-NW9900) - 包含重複的 NW0500 等
    list_plan = [
        ("NW0500", "建築執照", "掃描正本", False),
        ("NW1300", "施工計畫備查資料表", "建管處網站下載", False),
        ("NW1400", "施工計畫書簽章負責表", "起造/建築/營造/技師簽章", False),
        ("NW3200", "施工計畫書申請備案報告表", "承造人蓋章", False),
        ("NW3300", "施工計畫書", "含防災應變、觀測系統、安全支撐", False),
        ("NW3400", "工程告示牌設計圖", "起造/建築/營造用章", False),
        ("NW3500", "工地主任證書/勞保", "無則免", False),
        ("NW3600", "勞安人員證書/勞保", "營造廠蓋章", False),
        ("NW3700", "申報勘驗順序表", "承造/技師/監造簽章確認 (逆打需加附開口示意)", False),
        ("NW3800", "預定施工進度表", "建築師/承造人蓋章", False),
        ("NW3900", "公共管線查線函", "五大管線回函 (5樓/2000m²以下免附)", False),
        ("NW4000", "緊急應變計畫", "含緊急聯絡名冊", False),
        ("NW4200", "工程材料品質管理計畫", "併檢附結構材料強度圖說", False),
        ("NW4300", "運送憑證應辦事項及聯單管制", "", False),
        ("NW4700", "鷹架/圍籬/大門大樣圖", "建築師/營造廠/技師用章", False),
        ("NW4800", "平面安全設施配置圖", "繪於建照核准圖", False),
        ("NW4900", "四向立面安全設施配置圖", "繪於建照核准圖(含鷹架/護網/帆布)", False),
        ("NW5000", "配筋圖", "需至建築師公會用印 (A3圖說)", False),
        ("NW5100", "圍籬綠美化圖說", "含維護及回收計畫 (臨10M路需綠化)", False),
        ("NW5300", "交通維持計畫核准函", "達10000m²者必備", False),
        ("NW5400", "施工計畫說明會審查函", "達外審標準者必備", False),
        ("NW5500", "塔式起重機審查核可函", "勞檢處/交通局核准", False),
        ("NW5700", "觀測系統平面圖及應變計畫", "開挖深達1.5m者必備", False),
        ("NW5800", "安全支撐及擋土措施圖說", "開挖深達1.5m者必備", False),
        ("NW5900", "施工構台應力分析", "開挖面積>500m²者必備", False),
        ("NW9900", "其他文件", "建築線指示圖、複丈成果圖、鑽探報告", False)
    ]

    # 3. 放樣勘驗 (NS0100-NS9900)
    list_ns = [
        ("NS0100", "建築工程勘驗申報書", "完整填註及用章", False),
        ("NS0200", "建築執照存根", "含變更設計", False),
        ("NS0300", "勘驗順序表", "確認目前進度", False),
        ("NS0400", "必需勘驗部分申報表", "", False),
        ("NS0600", "專任工程人員督察記錄表", "", False),
        ("NS0700", "施工勘驗報告表", "承造人+技師", False),
        ("NS0800", "監造人現地勘驗檢查報告表", "", False),
        ("NS0900", "勘驗現場照片", "建物立面、告示牌、綠美化、四向鋼筋", False),
        ("NS0901", "勘驗人員照片", "監造人、技師、工地主任合照", False),
        ("NS1100", "鋼筋保證書", "", False),
        ("NS1200", "鋼筋無放射性污染證明書", "", False),
        ("NS1300", "鋼筋品質證明書", "含出廠證明", False),
        ("NS1400", "預拌混凝土品質保證書", "", False),
        ("NS1500", "氯離子含量檢測報告書", "含試驗數據", False),
        ("NS2100", "放樣切結書", "", False),
        ("NS2200", "公會抽查紀錄表", "二樓版/十樓版", False),
        ("NS2600", "專業工項施作情形表", "", False),
        ("NS3300", "施工日誌", "有技術士應再填寫技術士簽章表", False)
    ]
    return list_start, list_plan, list_ns

# --- 4. 側邊欄：參數輸入 ---
with st.sidebar:
    st.header("⚙️ 專案參數設定")
    project_type = st.radio("案件類型", ["素地新建案", "拆除併建造執照案"])
    is_demo_project = (project_type == "拆除併建造執照案")
    
    st.divider()
    
    st.subheader("📏 工程規模")
    total_area = st.number_input("總樓地板面積 (m²)", value=0, step=100)
    base_area = st.number_input("基地/施工面積 (m²)", value=0, step=100)
    duration_month = st.number_input("預計工期 (月)", value=12, step=1)
    
    excavation_depth = st.number_input("開挖深度 (m)", value=0.0, step=0.5)
    building_height = st.number_input("建築高度 (m)", value=0.0, step=1.0)
    
    # 計算邏輯
    pollution_value = base_area * duration_month
    is_water_plan_needed = pollution_value >= 4600
    is_traffic_plan_needed = total_area > 10000
    is_external_review_needed = (excavation_depth > 12 or building_height > 50 or base_area > 3000)
    
    st.divider()
    if st.button("🔄 強制重置 (修復錯誤)"):
        st.session_state.clear()
        st.rerun()

# --- 5. 核心 SOP 資料庫 ---
def get_initial_sop():
    water_msg = f"⚠️ 數值 {pollution_value} (達4600門檻) 需辦理" if is_water_plan_needed else "✅ 免辦理"
    traffic_msg = "⚠️ 強制辦理 (面積>10000m²)" if is_traffic_plan_needed else ""
    external_msg = "⚠️ 需辦理施工計畫外審" if is_external_review_needed else ""

    return {
        "stage_0": [ 
            {"item": "建築執照申請作業", "dept": "建築師/建管處", "method": "線上", "timing": "【掛號階段】", "docs": "1. 申請書電子檔\n2. 書圖文件", "critical": "", "details": "透過無紙化審查系統上傳。", "demo_only": False, "done": False, "note": ""},
            {"item": "領取建造執照", "dept": "建管處", "method": "臨櫃", "timing": "【校對完成後】", "docs": "1. 規費收據", "critical": "", "details": "繳納規費後領取紙本執照。", "demo_only": False, "done": False, "note": ""}
        ],
        "stage_1": [ 
            {"item": "空氣污染防制費申報", "dept": "環保局", "method": "線上", "timing": "【開工前】", "docs": "1. 合約書影本\n2. 建照影本", "critical": "⚠️ 首期申報：山坡地案需附詳細合約明細", "details": "**臺北市營建工程空污費網路申報系統**\n1. 註冊帳號\n2. 上傳文件\n3. 下載繳款書\n4. 繳款\n(面積>500m²需列管B8)", "demo_only": False, "done": False, "note": ""},
            {"item": "建照科行政驗收抽查", "dept": "建管處", "method": "臨櫃", "timing": "【開工申報前】", "docs": "1. 抽查紀錄表", "critical": "⚠️ 關鍵門檻：缺失修正後，方得辦理開工", "details": "單一拆照或拆併建照案必辦。", "demo_only": True, "done": False, "note": ""},
            {"item": "撤管防空避難設備", "dept": "警察分局", "method": "紙本", "timing": "【開工前】", "docs": "1. 函知公文", "critical": "", "details": "取得掛件收文戳章。", "demo_only": True, "done": False, "note": ""},
            {"item": "開工前置-逕流廢水削減計畫", "dept": "環保局", "method": "線上", "timing": "【開工前】", "docs": "1. 削減計畫書", "critical": water_msg, "details": "門檻：面積 × 工期 >= 4600", "demo_only": False, "done": False, "note": ""},
            {"item": "開工申報 (正式掛號)", "dept": "建管處", "method": "線上", "timing": "【建照後6個月內】", "docs": "⚠️ 確認 NW 開工文件備齊", "critical": "⚠️ 線上掛號後 1 日內需親送正本核對", "details": "需使用 HICOS 憑證元件。核對無誤以系統送出日為準。", "demo_only": False, "done": False, "note": ""}
        ],
        "stage_2": [ 
            {"item": "施工計畫說明會 (外審)", "dept": "相關公會", "method": "會議", "timing": "【計畫核定前】", "docs": "1. 施工計畫書\n2. 簡報", "critical": external_msg, "details": "深開挖(>12m)、高樓層(>50m)、地質敏感區需辦理。", "demo_only": False, "done": False, "note": ""},
            {"item": "交通維持計畫", "dept": "交通局", "method": "紙本", "timing": "【施工計畫前】", "docs": "1. 交維計畫書", "critical": traffic_msg, "details": "樓地板面積>10000m²強制辦理。需配合施工大門、車行坡道。", "demo_only": False, "done": False, "note": ""},
            {"item": "施工計畫書核備 (上傳)", "dept": "建管處", "method": "線上", "timing": "【放樣前】", "docs": "⚠️ 確認 NW 施工計畫文件備齊", "critical": "", "details": "**無紙化規定**：\n1. 掃描 A3/A4 格式 PDF。\n2. 配筋圖需至公會用印。\n3. 圖說檔案編號 NW4700~NW5000。", "demo_only": False, "done": False, "note": ""},
            {"item": "舊屋拆除與廢棄物結案", "dept": "環保局", "method": "線上", "timing": "【拆除後】", "docs": "1. 結案申報書", "critical": "⚠️ B5/B8 未結案，無法進行放樣", "details": "拆除完成後需解除列管。", "demo_only": True, "done": False, "note": ""}
        ],
        "stage_3": [ 
            {"item": "導溝勘驗申報", "dept": "建管處", "method": "線上", "timing": "【施工前2日】", "docs": "1. 申請書\n2. 照片", "critical": "", "details": "", "demo_only": False, "done": False, "note": ""}
        ],
        "stage_4": [ 
             {"item": "地界複丈/路心樁復原", "dept": "地政事務所", "method": "臨櫃", "timing": "【拆除後】", "docs": "1. 複丈申請書", "critical": "", "details": "", "demo_only": True, "done": False, "note": ""},
            {"item": "放樣勘驗申報", "dept": "建管處", "method": "線上", "timing": "【結構施工前】", "docs": "⚠️ 確認 NS 勘驗文件備齊", "critical": "", "details": "需將測量成果、鋼筋保證書等掃描上傳。檔名 Ex: NS0100...pdf", "demo_only": False, "done": False, "note": ""}
        ]
    }

# --- 6. 初始化 ---
if "sop_data" not in st.session_state:
    st.session_state.sop_data = get_initial_sop()

list_start, list_plan, list_ns = get_all_checklists()
all_checklists_codes = [c[0] for c in list_start + list_plan + list_ns]

# 確保所有 code 都在字典裡
if "nw_status" not in st.session_state:
    st.session_state.nw_status = {code: False for code in all_checklists_codes}
else:
    for code in all_checklists_codes:
        if code not in st.session_state.nw_status:
            st.session_state.nw_status[code] = False

# 強制更新 SOP 內容
st.session_state.sop_data = get_initial_sop()
data = st.session_state.sop_data

# --- 7. Callback ---
def toggle_status(stage_key, index):
    st.session_state.sop_data[stage_key][index]['done'] = not st.session_state.sop_data[stage_key][index]['done']

def toggle_nw(code):
    st.session_state.nw_status[code] = not st.session_state.nw_status[code]

# --- 8. 渲染函數 ---
def render_stage_detailed(stage_key, is_locked=False):
    stage_items = data[stage_key]
    if is_locked: st.markdown('<div class="locked-stage">🔒 請先完成上一階段</div>', unsafe_allow_html=True)

    for i, item in enumerate(stage_items):
        if item.get("demo_only") and not is_demo_project: continue
        with st.container():
            col1, col2 = st.columns([0.5, 9.5])
            with col1:
                # 解決 Duplicate ID 的關鍵：加上 key_suffix (stage_key)
                st.checkbox("", value=item['done'], key=f"chk_{stage_key}_{i}", on_change=toggle_status, args=(stage_key, i), disabled=is_locked)
            with col2:
                method = item.get('method', '現場')
                method_tag = f'<span class="tag-online">🔵 線上</span>' if method == "線上" else f'<span class="tag-paper">🟤 {method}</span>'
                demo_tag = '<span class="tag-demo">🏗️ 拆除專項</span>' if item.get("demo_only") else ""
                
                title_html = f"**{item['item']}** {method_tag} {demo_tag} <span style='color:#666; font-size:0.9em'>(🏢 {item['dept']})</span>"
                if item['done']: st.markdown(f"<span style='color:#2E7D32; font-weight:bold;'>✅ {item['item']}</span>", unsafe_allow_html=True)
                else: st.markdown(title_html, unsafe_allow_html=True)
                
                if item.get("critical"): st.markdown(f"<div class='critical-info'>{item['critical']}</div>", unsafe_allow_html=True)

                with st.expander("🔽 詳細指引與備註", expanded=False):
                    st.markdown(f"**🕒 時機：** {item['timing']}")
                    st.markdown(f"**📄 文件：**\n{item['docs']}")
                    if item['details']: st.markdown(f"<div class='info-box'>💡 <b>指引：</b><br>{item['details']}</div>", unsafe_allow_html=True)
                    st.text_input("備註", value=item['note'], key=f"note_{stage_key}_{i}")
        st.divider()

def render_checklist(checklist_data, title, tab_name):
    with st.expander(f"📑 {title} (點擊展開檢查)", expanded=False):
        st.markdown(f'<div class="nw-header">請確認 PDF 檔案已備齊並完成用印/掃描：</div>', unsafe_allow_html=True)
        for code, name, note, demo_only in checklist_data:
            if demo_only and not is_demo_project: continue
            c1, c2, c3 = st.columns([0.5, 4, 5.5])
            
            # [關鍵修正] 使用 tab_name 作為 key 的一部分，避免重複 ID 錯誤
            # (例如 NW0500 在開工和計畫都有，加上後綴區分)
            is_checked = st.session_state.nw_status.get(code, False)
            with c1: st.checkbox("", value=is_checked, key=f"chk_{code}_{tab_name}", on_change=toggle_nw, args=(code,))
            with c2: 
                color_style = "color:#2E7D32; font-weight:bold;" if is_checked else ""
                st.markdown(f"<span style='{color_style}'>{code} {name}</span>", unsafe_allow_html=True)
            with c3: st.caption(f"🖊️ {note}")

# --- 9. 主流程 ---
s0_done = all(item['done'] for item in data['stage_0'])
permit_unlocked = s0_done

tabs = st.tabs(["0.建照領取", "1.開工申報(NW)", "2.施工計畫(NW)", "3.導溝勘驗", "4.放樣勘驗(NS)"])

with tabs[0]:
    st.subheader("🔑 階段零：建照領取")
    render_stage_detailed("stage_0", is_locked=False)

with tabs[1]:
    st.subheader("📋 階段一：開工申報 (含NW開工文件)")
    if not permit_unlocked: st.markdown('<div class="locked-stage">🔒 請先完成建照領取</div>', unsafe_allow_html=True)
    else:
        render_checklist(list_start, "NW 開工文件準備檢查表", "start")
        st.markdown("---")
        st.markdown("### ✅ 正式申報流程")
        render_stage_detailed("stage_1", is_locked=False)

with tabs[2]:
    st.subheader("📘 階段二：施工計畫 (含NW計畫文件)")
    if not permit_unlocked: st.markdown('<div class="locked-stage">🔒 請先完成開工申報</div>', unsafe_allow_html=True)
    else:
        render_checklist(list_plan, "NW 施工計畫文件準備檢查表", "plan")
        st.markdown("---")
        render_stage_detailed("stage_2", is_locked=False)

with tabs[3]:
    st.subheader("🚧 階段三：導溝勘驗")
    render_stage_detailed("stage_3", is_locked=not permit_unlocked)

with tabs[4]:
    st.subheader("📐 階段四：放樣勘驗 (含NS勘驗文件)")
    if not permit_unlocked: st.markdown('<div class="locked-stage">🔒 請先完成施工計畫</div>', unsafe_allow_html=True)
    else:
        render_checklist(list_ns, "NS 放樣勘驗文件準備檢查表", "survey")
        st.markdown("---")
        render_stage_detailed("stage_4", is_locked=False)

# --- 10. Excel 下載 ---
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
    pd.DataFrame(all_rows).to_excel(writer, index=False, sheet_name='SOP流程')
    
    all_checklists = []
    for lst, category in [(list_start, "開工NW"), (list_plan, "計畫NW"), (list_ns, "放樣NS")]:
        for code, name, note, demo_only in lst:
            if demo_only and not is_demo_project: continue
            status = "完成" if st.session_state.nw_status.get(code, False) else "未完成"
            all_checklists.append({"類別": category, "編號": code, "名稱": name, "備註": note, "狀態": status})
    pd.DataFrame(all_checklists).to_excel(writer, index=False, sheet_name='文件檢查表')

st.download_button("📥 下載完整 Excel", buffer.getvalue(), f"SOP_Full_{date.today()}.xlsx", "application/vnd.ms-excel")