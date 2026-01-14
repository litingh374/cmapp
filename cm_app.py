import streamlit as st
import pandas as pd
import io
import hashlib
from datetime import date

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="建案行政SOP系統 (V20.0 結構重構版)",
    page_icon="🏗️",
    layout="wide"
)

# --- 2. 🛡️ 版本控制 (V20.0) ---
CURRENT_VERSION = 20.0

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
    .tag-online { background-color: #e3f2fd; color: #0d47a1; padding: 1px 6px; border-radius: 4px; font-size: 0.8em; font-weight: bold; border: 1px solid #90caf9; }
    .tag-paper { background-color: #efebe9; color: #5d4037; padding: 1px 6px; border-radius: 4px; font-size: 0.8em; font-weight: bold; border: 1px solid #bcaaa4; }
    .tag-demo { background-color: #ffcdd2; color: #b71c1c; padding: 1px 6px; border-radius: 4px; font-size: 0.8em; font-weight: bold; border: 1px solid #ef9a9a; }
    .tag-struct { background-color: #e1bee7; color: #4a148c; padding: 1px 6px; border-radius: 4px; font-size: 0.8em; font-weight: bold; border: 1px solid #ce93d8; }
    .critical-info {
        color: #d32f2f; font-size: 0.9em; font-weight: bold; margin-left: 25px; margin-bottom: 5px;
        background-color: #ffebee; padding: 2px 8px; border-radius: 4px; display: inline-block;
    }
    .info-box { background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 5px solid #6c757d; font-size: 0.9em; margin-bottom: 5px; }
    .nw-header { background-color: #e8f5e9; padding: 10px; border-radius: 5px; border: 1px solid #c8e6c9; margin-bottom: 10px; font-weight: bold; color: #2e7d32; }
    .check-header { background-color: #fff3e0; padding: 10px; border-radius: 5px; border: 1px solid #ffe0b2; margin-bottom: 10px; font-weight: bold; color: #e65100; }
    .special-context { background-color: #f3e5f5; padding: 15px; border-radius: 8px; border: 1px solid #e1bee7; margin-bottom: 15px; }
    div[data-testid="stExpander"] { margin-top: -5px; }
</style>
""", unsafe_allow_html=True)

st.title(f"🏗️ 建案行政SOP系統 (Ver {CURRENT_VERSION})")
st.caption("修復：素地案誤顯示拆除項目、無法解鎖問題")

# --- 3. 輔助函數 ---
def generate_key(stage, item_name):
    # 產生穩定唯一的 Key
    return hashlib.md5(f"{stage}_{item_name}".encode()).hexdigest()[:10]

# --- 4. 側邊欄：參數輸入 ---
with st.sidebar:
    st.header("⚙️ 專案參數設定")
    # [關鍵] 使用 key 綁定，確保 session_state 同步
    project_type = st.radio("案件類型", ["素地新建案", "拆除併建造執照案"], key="kp_project_type")
    is_demo_project = (project_type == "拆除併建造執照案")
    
    st.divider()
    
    st.subheader("📏 工程與結構規模")
    project_budget = st.number_input("工程合約經費 (萬元)", value=0, step=10, help="500萬以上需列管B8")
    base_area = st.number_input("基地/施工面積 (m²)", value=0, step=100)
    duration_month = st.number_input("預計工期 (月)", value=12, step=1)
    total_area = st.number_input("總樓地板面積 (m²)", value=0, step=100)
    
    with st.expander("詳細結構參數"):
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            building_height = st.number_input("建築高度 (m)", value=0.0)
            floors_above = st.number_input("地上層數", value=0)
        with col_h2:
            excavation_depth = st.number_input("開挖深度 (m)", value=0.0)
            floors_below = st.number_input("地下層數", value=0)
        span_rc = st.number_input("RC最大跨距(m)", value=0.0)
        
    is_geo_sensitive = st.checkbox("位於地質敏感區", value=False)
    is_slope_land_param = st.checkbox("位於山坡地 (結構外審判斷用)", value=False)

    # 邏輯判讀
    pollution_value = base_area * duration_month
    is_water_plan_needed = pollution_value >= 4600
    is_b8_needed = base_area >= 500 or project_budget >= 500
    
    is_traffic_plan_needed = total_area > 10000
    is_struct_review_needed = (
        building_height > 50 or 
        floors_above > 15 or 
        excavation_depth > 12 or 
        floors_below > 3 or 
        span_rc > 12 or
        is_slope_land_param or
        (is_geo_sensitive and (excavation_depth > 7 or floors_below > 1))
    )
    is_demo_review_needed = is_demo_project and floors_above > 10
    
    st.divider()
    if st.button("🔄 強制重置系統"):
        st.session_state.clear()
        st.rerun()

# --- 5. 初始化特殊狀態 Flag ---
special_flags = [
    "flag_slope", "flag_public", "flag_expired", 
    "flag_change", "flag_existing", "flag_demo_included",
    "flag_demo_dihua", "flag_demo_old", "flag_demo_done", "flag_demo_shelter"
]
for flag in special_flags:
    if flag not in st.session_state:
        st.session_state[flag] = False

# --- 6. Helper Functions (詳細文字) ---
def get_air_pollution_context():
    doc_details = []
    if st.session_state.flag_slope: doc_details.append("★ **山坡地基地**：\n   需檢附合約之「封面、條款、甲乙方、總價金額、用印欄頁及工程項次明細表」等影本 (需全部業主用章)。")
    if st.session_state.flag_public: doc_details.append("★ **工程契約型(公務)**：\n   1. 工程契約書影本 (含封面、契約價金之給付條款總價頁、甲乙雙人用印頁、工程總表及明細表、決標記錄影本)。\n   2. 業務主管機關之開工證明「正本」。(均需用起造人大小章)。")
    else: doc_details.append("★ **一般案件**：\n   需檢附合約影本 (含封面、條款、甲乙方、總價金額、用印欄頁)。")
    if st.session_state.flag_expired: doc_details.append("★ **領照逾6個月**：\n   應檢附「開工展期申請書」影本 (全部業主大小章)。")
    if st.session_state.flag_change: doc_details.append("★ **變更過起造人/承造人**：\n   應檢附「變更申請書」影本 (全部業主大小章)。")
    if st.session_state.flag_existing: doc_details.append("★ **基地已有建物**：\n   請加附「建築執照申請書」及「建物概要表」影本 (全部業主大小章)。")
    if st.session_state.flag_demo_included: doc_details.append("★ **屬建照列管拆照者**：\n   檢附「拆照影本」及「拆照空污費繳費單」影本 (全部業主大小章)。")
    return "\n\n".join(doc_details)

def get_demolition_context():
    notes = []
    notes.append("★ **鄰房鑑定**：需取得公會函件及結論報告。")
    if st.session_state.flag_demo_dihua: notes.append("   ⚠️ **迪化街區**：強制辦理現況鑑定。")
    if st.session_state.flag_demo_old: notes.append("   ⚠️ **老舊建物**：需增加安全及補強評估報告。")
    
    notes.append("★ **廢棄物處理 (B5/B8)**：")
    if st.session_state.flag_demo_done:
        notes.append("   ⚠️ **先行拆除完成**：若無 B5 土方，數量應修正為「0」。")
    else:
        notes.append("   1. **土石方 (B5)**：向「建管處施工科」申請。\n   2. **混合物 (B8)**：向「環保局」申辦審查。")
    
    notes.append(f"★ **逕流廢水 (二科)**：\n   拆除面積 × 工期 (月) ≥ 4600 者需辦理。")
    if st.session_state.flag_demo_shelter: notes.append("★ **防空避難**：\n   需函知警察分局辦理撤管。")
    return "\n\n".join(notes)

# --- 7. 核心 SOP 資料庫 (結構重構：依專案類型組裝) ---
def get_current_sop_data():
    # 警語
    b8_msg = "⚠️ 需辦理 B8 列管 (面積>500m² 或 經費>500萬)" if is_b8_needed else ""
    water_msg = f"⚠️ 數值 {pollution_value} (達4600) 需辦理" if is_water_plan_needed else "✅ 免辦理"
    traffic_msg = "⚠️ 強制辦理 (面積>10000m²)" if is_traffic_plan_needed else ""
    struct_msg = "⚠️ 符合外審條件：需辦理細部設計審查" if is_struct_review_needed else ""
    demo_msg = "⚠️ 拆除規模>10層：需辦理拆除計畫外審" if is_demo_review_needed else ""

    # --- 1. 定義基礎項目 (通用) ---
    s0 = [
        {"item": "建築執照申請作業", "dept": "建築師/建管處", "method": "線上", "timing": "【掛號階段】", "docs": "1. 申請書電子檔\n2. 書圖文件", "critical": "", "details": "透過無紙化審查系統上傳。"},
        {"item": "領取建造執照", "dept": "建管處", "method": "臨櫃", "timing": "【校對完成後】", "docs": "1. 規費收據", "critical": "", "details": "繳納規費後領取紙本執照。"}
    ]
    
    s1 = [
        {"item": "空氣污染防制費申報", "dept": "環保局(空噪科)", "method": "線上", "timing": "【開工前】", "docs": "基本：申報書、建照影本", "critical": b8_msg, "details": "DYNAMIC_AP_CONTENT"},
        {"item": "開工前置-逕流廢水削減計畫", "dept": "環保局(二科)", "method": "線上", "timing": "【開工前】", "docs": "1. 削減計畫書\n2. 沉沙池圖說", "critical": water_msg, "details": "辦理標準：面積 × 工期 ≥ 4600。\n環評基地需先經公會審查。"},
        {"item": "開工申報 (正式掛號)", "dept": "建管處", "method": "線上", "timing": "【建照後6個月內】", "docs": "⚠️ 確認 NW 開工文件備齊", "critical": "⚠️ 線上掛號後 1 日內需親送正本核對", "details": "需使用 HICOS 憑證元件。"}
    ]
    
    # --- 2. 定義拆除專用項目 ---
    s1_demo = [
        {"item": "拆除作業前置 (拆併建專用)", "dept": "相關單位", "method": "混合", "timing": "【開工前】", "docs": "鄰房鑑定、B5/B8核准函", "critical": "⚠️ 拆除案必辦", "details": "DYNAMIC_DEMO_CONTENT"},
        {"item": "建照科行政驗收抽查", "dept": "建管處", "method": "臨櫃", "timing": "【開工申報前】", "docs": "1. 抽查紀錄表", "critical": "⚠️ 關鍵門檻", "details": "單一拆照或拆併建照案必辦。"},
        {"item": "撤管防空避難設備", "dept": "警察分局", "method": "紙本", "timing": "【開工前】", "docs": "1. 函知公文", "critical": "", "details": "取得掛件收文戳章。"},
    ]
    if is_demo_review_needed:
        s1_demo.append({"item": "拆除計畫外審", "dept": "相關公會", "method": "會議", "timing": "【開工前】", "docs": "1. 拆除計畫書", "critical": demo_msg, "details": "地上10層以上拆除必辦。"})

    # --- 3. 組裝 Stage 1 (開工) ---
    # 如果是拆除案，將拆除項目插入到 "開工申報" 之前
    final_s1 = []
    if is_demo_project:
        # 順序：空污 -> 拆除前置 -> 行政驗收 -> 撤管 -> 廢水 -> (外審) -> 開工
        final_s1.append(s1[0]) # 空污
        final_s1.extend(s1_demo) # 拆除相關
        final_s1.append(s1[1]) # 廢水
        final_s1.append(s1[2]) # 開工
    else:
        # 素地案：空污 -> 廢水 -> 開工
        final_s1 = s1

    # --- 4. 施工計畫 ---
    s2 = []
    if is_struct_review_needed:
        s2.append({"item": "結構外審-細部設計審查", "dept": "結構公會", "method": "會議", "timing": "【放樣前】", "docs": "細部配筋圖、核備函", "critical": struct_msg, "details": "需取得建照科核備。"})
        s2.append({"item": "施工計畫說明會 (外審)", "dept": "相關公會", "method": "會議", "timing": "【核定前】", "docs": "施工計畫書、簡報", "critical": struct_msg, "details": "深開挖/高樓層/大跨距。"})
    
    if is_traffic_plan_needed:
        s2.append({"item": "交通維持計畫", "dept": "交通局", "method": "紙本", "timing": "【施工計畫前】", "docs": "交維計畫書", "critical": traffic_msg, "details": "樓地板>10000m²。"})
        
    s2.append({"item": "施工計畫書核備 (上傳)", "dept": "建管處", "method": "線上", "timing": "【放樣前】", "docs": "⚠️ 確認 NW 文件備齊", "critical": "", "details": "掃描 A3(圖說)/A4 PDF。配筋圖需公會用印。"})
    
    if is_demo_project:
        s2.append({"item": "舊屋拆除與廢棄物結案", "dept": "環保局", "method": "線上", "timing": "【拆除後】", "docs": "結案申報書", "critical": "⚠️ B5/B8 未結案，無法放樣", "details": "拆除完成後需解除列管。"})

    # --- 5. 導溝 & 放樣 ---
    s3 = [{"item": "導溝勘驗申報", "dept": "建管處", "method": "線上", "timing": "【施工前2日】", "docs": "申請書、照片", "critical": "", "details": ""}]
    
    s4 = [
        {"item": "放樣前置-用水/電/汙水核備", "dept": "自來水/台電", "method": "紙本", "timing": "【放樣前】", "docs": "核備公函", "critical": "", "details": "5樓/5戶/2000m²以下免辦。"},
        {"item": "放樣勘驗申報", "dept": "建管處", "method": "線上", "timing": "【結構施工前】", "docs": "⚠️ 確認 NS 文件備齊", "critical": "⚠️ 現場不得先行施工", "details": "網路核備後，送紙本掛件。"}
    ]
    if is_demo_project:
        # 拆除案在放樣前要加地界複丈
        s4.insert(1, {"item": "地界複丈/路心樁復原", "dept": "地政", "method": "臨櫃", "timing": "【拆除後】", "docs": "複丈申請書", "critical": "", "details": "拆除後重測地界。"})

    # 回傳組裝好的資料
    return {
        "stage_0": s0,
        "stage_1": final_s1,
        "stage_2": s2,
        "stage_3": s3,
        "stage_4": s4
    }

# --- 8. 狀態同步與初始化 ---
sop_data = get_current_sop_data() # 根據最新的 project_type 產生資料

# 初始化 Session State (Status Hydration)
for stage, items in sop_data.items():
    for item in items:
        # 使用 item 名稱作為 key，確保切換專案類型時，相同項目的狀態保留 (或重置，視需求)
        # 這裡我們希望相同項目保留，但不同專案類型的獨有項目互不干擾
        key = generate_key(stage, item['item'])
        chk_key = f"chk_{key}"
        note_key = f"note_{key}"
        
        # 確保 Key 存在，避免 KeyError
        if chk_key not in st.session_state:
            st.session_state[chk_key] = False
        
        # 將狀態寫入 data 用於顯示，但不依賴 data 存儲
        item['done'] = st.session_state[chk_key]
        item['note'] = st.session_state.get(note_key, "")

# 定義檢查表
def get_checklists():
    # 這裡放完整的清單，渲染時再過濾
    # (為了節省篇幅，這裡使用 V19.0 的完整清單)
    list_start = [
        ("NW0100", "開工", "建築工程開工申報書", "", False), ("NW0500", "開工", "建築執照正本", "", False),
        ("NW1000", "開工", "空污費收據", "", False), ("NW1100", "開工", "逕流廢水核備", "", False),
        ("NW2400", "開工", "拆除施工計畫書", "", True), ("NW2500", "開工", "監拆報告書", "", True),
        ("NW2600", "開工", "拆除B5備查", "", True), ("NW2700", "開工", "拆除B8備查", "", True),
        ("NW2900", "開工", "塔吊檢查表", "無則附切結", False)
    ]
    list_plan = [
        ("NW3300", "計畫", "施工計畫書", "", False), ("NW5000", "計畫", "配筋圖(A3)", "公會用印", False),
        ("NW5300", "計畫", "交維計畫核准", "1萬m²以上", False), ("NW5700", "計畫", "觀測系統", "深開挖", False)
    ]
    list_ns = [
        ("NS0100", "放樣", "勘驗申報書", "", False), ("NS0900", "放樣", "現場照片", "", False),
        ("NS1100", "放樣", "鋼筋保證書", "", False), ("NS2100", "放樣", "放樣切結書", "", False)
    ]
    return list_start, list_plan, list_ns

# 初始化檢查表狀態
chk_lists = get_checklists()
for lst in chk_lists:
    for code, cat, _, _, _ in lst:
        k = f"chk_{code}_{cat}"
        if k not in st.session_state: st.session_state[k] = False

# --- 9. 渲染函數 ---
def render_stage_detailed(stage_key, is_locked=False):
    stage_items = sop_data[stage_key] # 使用已過濾組裝好的資料
    
    if is_locked: 
        st.markdown('<div class="locked-stage">🔒 請先完成上一階段</div>', unsafe_allow_html=True)
    
    for item in stage_items:
        # 因為資料已經在 get_current_sop_data 篩選過，這裡不需要再判斷 demo_only
        # 直接渲染即可
        
        chk_key = f"chk_{generate_key(stage_key, item['item'])}"
        note_key = f"note_{generate_key(stage_key, item['item'])}"

        with st.container():
            col1, col2 = st.columns([0.5, 9.5])
            
            with col1:
                # 原生 checkbox，狀態直接綁定 session_state
                st.checkbox("", key=chk_key, disabled=is_locked)
                is_checked = st.session_state[chk_key]

            with col2:
                method = item.get('method', '現場')
                method_tag = f'<span class="tag-online">🔵 線上</span>' if method == "線上" else f'<span class="tag-paper">🟤 {method}</span>'
                
                title_html = f"**{item['item']}** {method_tag} <span style='color:#666; font-size:0.9em'>(🏢 {item['dept']})</span>"
                
                if is_checked: 
                    st.markdown(f"<span style='color:#2E7D32; font-weight:bold;'>✅ {item['item']}</span>", unsafe_allow_html=True)
                else: 
                    st.markdown(title_html, unsafe_allow_html=True)
                
                if item.get("critical"): st.markdown(f"<div class='critical-info'>{item['critical']}</div>", unsafe_allow_html=True)

                # 空污費詳細區塊
                if item['item'] == "空氣污染防制費申報":
                    with st.expander("🔽 詳細指引與檢核 (含特殊案件勾選)", expanded=False):
                        st.markdown("""<div class='special-context'><b>🚩 特殊案件條件勾選：</b>""", unsafe_allow_html=True)
                        c1, c2 = st.columns(2)
                        with c1:
                            st.checkbox("位於山坡地基地", key="flag_slope")
                            st.checkbox("屬工程契約型 (公務)", key="flag_public")
                            st.checkbox("領取建照逾 6 個月", key="flag_expired")
                        with c2:
                            st.checkbox("曾變更起造人/承造人", key="flag_change")
                            st.checkbox("基地已有建物 (如學校)", key="flag_existing")
                            st.checkbox("屬建照列管拆照者", key="flag_demo_included")
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        dynamic_details = get_air_pollution_context()
                        st.markdown(f"**📄 自動產生應備文件清單：**\n\n{dynamic_details}")
                        st.markdown("---")
                        st.markdown(f"**💡 作業指引：**\n臺北市營建工程空污費網路申報系統 (02-27208889 #7252)")
                        st.text_input("備註", key=note_key)
                
                elif item['item'] == "拆除作業前置 (拆併建專用)":
                    with st.expander("🔽 詳細指引與檢核 (拆除條件)", expanded=False):
                        st.markdown("""<div class='special-context'><b>🚩 拆除條件勾選：</b>""", unsafe_allow_html=True)
                        c1, c2 = st.columns(2)
                        with c1:
                            st.checkbox("屬大同區迪化街區", key="flag_demo_dihua")
                            st.checkbox("鄰房屬老舊建物", key="flag_demo_old")
                        with c2:
                            st.checkbox("先行拆除完成 (無B5土方)", key="flag_demo_done")
                            st.checkbox("舊建物有防空避難設備", key="flag_demo_shelter")
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        demo_details = get_demolition_context()
                        st.markdown(f"**📄 應備項目與注意事項：**\n\n{demo_details}")
                        st.text_input("備註", key=note_key)
                
                else:
                    with st.expander("🔽 詳細指引與備註", expanded=False):
                        st.markdown(f"**🕒 時機：** {item['timing']}")
                        st.markdown(f"**📄 文件：**\n{item['docs']}")
                        if item['details'] and "DYNAMIC" not in item['details']: 
                            st.markdown(f"<div class='info-box'>💡 <b>指引：</b><br>{item['details']}</div>", unsafe_allow_html=True)
                        st.text_input("備註", key=note_key)
        st.divider()

def render_checklist(checklist_data, title):
    with st.expander(f"📑 {title} (點擊展開)", expanded=False):
        for code, cat, name, note, demo_only in checklist_data:
            if demo_only and not is_demo_project: continue
            
            c1, c2, c3 = st.columns([0.5, 4, 5.5])
            key = f"chk_{code}_{cat}"
            st.checkbox("", key=key)
            is_checked = st.session_state[key]
            
            with c2: 
                style = "color:#2E7D32; font-weight:bold;" if is_checked else ""
                st.markdown(f"<span style='{style}'>{code} {name}</span>", unsafe_allow_html=True)
            with c3: st.caption(f"🖊️ {note}")

# --- 10. 解鎖邏輯 (Status Check) ---
def check_stage_complete(stage_key):
    items = sop_data[stage_key]
    for item in items:
        # 因為資料已經過濾過，我們只需要檢查清單內的所有項目是否完成
        key = f"chk_{generate_key(stage_key, item['item'])}"
        if not st.session_state.get(key, False):
            return False
    return True

s0_done = check_stage_complete('stage_0')
s1_done = check_stage_complete('stage_1')
s2_done = check_stage_complete('stage_2')

# --- 11. 主畫面 ---
tabs = st.tabs(["0.建照領取", "1.開工申報(NW)", "2.施工計畫(NW)", "3.導溝勘驗", "4.放樣勘驗(NS)"])

with tabs[0]:
    st.subheader("🔑 階段零：建照領取")
    render_stage_detailed("stage_0", is_locked=False)

with tabs[1]:
    st.subheader("📋 階段一：開工申報 (含NW開工文件)")
    if not s0_done: st.markdown('<div class="locked-stage">🔒 請先完成建照領取</div>', unsafe_allow_html=True)
    else:
        render_checklist(get_checklists()[0], "NW 開工文件準備檢查表") # List 0 is Start
        st.markdown("---")
        render_stage_detailed("stage_1", is_locked=False)

with tabs[2]:
    st.subheader("📘 階段二：施工計畫 (含NW計畫文件)")
    if not (s0_done and s1_done): st.markdown('<div class="locked-stage">🔒 請先完成開工申報</div>', unsafe_allow_html=True)
    else:
        render_checklist(get_checklists()[1], "NW 施工計畫文件準備檢查表") # List 1 is Plan
        st.markdown("---")
        render_stage_detailed("stage_2", is_locked=False)

with tabs[3]:
    st.subheader("🚧 階段三：導溝勘驗")
    render_stage_detailed("stage_3", is_locked=not (s0_done and s1_done and s2_done))

with tabs[4]:
    st.subheader("📐 階段四：放樣勘驗 (含NS勘驗文件)")
    if not (s0_done and s1_done and s2_done): st.markdown('<div class="locked-stage">🔒 請先完成施工計畫</div>', unsafe_allow_html=True)
    else:
        render_checklist(get_checklists()[2], "NS 放樣勘驗文件準備檢查表") # List 2 is NS
        st.markdown("---")
        render_stage_detailed("stage_4", is_locked=False)

# --- 12. Excel 下載 ---
st.write("---")
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    all_rows = []
    for k, v in sop_data.items():
        for item in v:
            key = f"chk_{generate_key(k, item['item'])}"
            item['done'] = st.session_state.get(key, False)
            item['note'] = st.session_state.get(f"note_{generate_key(k, item['item'])}", "")
            
            item_copy = item.copy()
            item_copy['階段代號'] = k
            all_rows.append(item_copy)
    
    if all_rows: pd.DataFrame(all_rows).to_excel(writer, index=False, sheet_name='SOP流程')
    
st.download_button("📥 下載完整 Excel", buffer.getvalue(), f"SOP_Full_V{CURRENT_VERSION}_{date.today()}.xlsx", "application/vnd.ms-excel")