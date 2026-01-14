import streamlit as st
import pandas as pd
import io
import hashlib
from datetime import date

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="建案行政SOP系統 (V11.0)",
    page_icon="🏗️",
    layout="wide"
)

# --- 2. 🛡️ 版本控制 (V11.0) ---
CURRENT_VERSION = 11.0

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
    .tag-struct { background-color: #e1bee7; color: #4a148c; padding: 2px 8px; border-radius: 4px; font-size: 0.8em; font-weight: bold; border: 1px solid #ce93d8; }
    .critical-info {
        color: #d32f2f; font-size: 0.9em; font-weight: bold; margin-left: 25px; margin-bottom: 5px;
        background-color: #ffebee; padding: 2px 8px; border-radius: 4px; display: inline-block;
    }
    .info-box { background-color: #f8f9fa; padding: 10px; border-radius: 5px; border-left: 5px solid #6c757d; font-size: 0.9em; margin-bottom: 5px; }
    .nw-header { background-color: #e8f5e9; padding: 10px; border-radius: 5px; border: 1px solid #c8e6c9; margin-bottom: 10px; font-weight: bold; color: #2e7d32; }
    .check-header { background-color: #fff3e0; padding: 10px; border-radius: 5px; border: 1px solid #ffe0b2; margin-bottom: 10px; font-weight: bold; color: #e65100; }
    div[data-testid="stExpander"] { margin-top: -5px; }
</style>
""", unsafe_allow_html=True)

st.title(f"🏗️ 建案行政SOP系統 (Ver {CURRENT_VERSION})")
st.caption("修復：勾選狀態同步問題、確保解鎖邏輯穩定")

# --- 3. 輔助函數：產生唯一 Key ---
def generate_key(stage, item_name):
    # 產生一個固定的 hash key，確保即使重新整理，只要項目名稱不變，key 就不變
    raw_str = f"{stage}_{item_name}"
    return hashlib.md5(raw_str.encode()).hexdigest()[:10]

# --- 4. 側邊欄：參數輸入 ---
with st.sidebar:
    st.header("⚙️ 專案參數設定")
    project_type = st.radio("案件類型", ["素地新建案", "拆除併建造執照案"])
    is_demo_project = (project_type == "拆除併建造執照案")
    
    st.divider()
    
    st.subheader("📏 工程與結構規模")
    total_area = st.number_input("總樓地板面積 (m²)", value=0, step=100)
    base_area = st.number_input("基地/施工面積 (m²)", value=0, step=100)
    duration_month = st.number_input("預計工期 (月)", value=12, step=1)
    
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        building_height = st.number_input("建築高度 (m)", value=0.0, step=1.0)
        floors_above = st.number_input("地上層數", value=0, step=1)
    with col_h2:
        excavation_depth = st.number_input("開挖深度 (m)", value=0.0, step=0.5)
        floors_below = st.number_input("地下層數", value=0, step=1)
        
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        span_rc = st.number_input("RC最大跨距(m)", value=0.0, step=0.5)
    with col_s2:
        span_sc = st.number_input("鋼骨最大跨距(m)", value=0.0, step=0.5)
        
    is_geo_sensitive = st.checkbox("位於地質敏感區", value=False)
    is_slope_land = st.checkbox("位於山坡地", value=False)
    is_manual_struct_review = st.checkbox("建照列管結構外審", value=False)

    # 判讀邏輯
    pollution_value = base_area * duration_month
    is_water_plan_needed = pollution_value >= 4600
    is_traffic_plan_needed = total_area > 10000
    
    is_struct_review_needed = (
        building_height > 50 or 
        floors_above > 15 or 
        excavation_depth > 12 or 
        floors_below > 3 or 
        span_rc > 12 or 
        span_sc > 35 or
        is_slope_land or
        is_manual_struct_review or
        (is_geo_sensitive and (excavation_depth > 7 or floors_below > 1))
    )
    is_demo_review_needed = is_demo_project and floors_above > 10
    
    st.divider()
    if st.button("🔄 強制重置系統"):
        st.session_state.clear()
        st.rerun()

# --- 5. 核心 SOP 資料庫 (每次刷新都根據參數生成最新結構) ---
def get_current_sop_data():
    water_msg = f"⚠️ 數值 {pollution_value} (達4600門檻) 需辦理" if is_water_plan_needed else "✅ 免辦理"
    traffic_msg = "⚠️ 強制辦理 (面積>10000m²)" if is_traffic_plan_needed else ""
    struct_msg = "⚠️ 符合外審條件 (高度/深度/跨距)：需辦理細部設計審查" if is_struct_review_needed else ""
    demo_msg = "⚠️ 拆除規模>10層：需辦理拆除計畫外審" if is_demo_review_needed else ""

    raw_data = {
        "stage_0": [ 
            {"item": "建築執照申請作業", "dept": "建築師/建管處", "method": "線上", "timing": "【掛號階段】", "docs": "1. 申請書電子檔\n2. 書圖文件", "critical": "", "details": "透過無紙化審查系統上傳。", "demo_only": False, "struct_only": False},
            {"item": "領取建造執照", "dept": "建管處", "method": "臨櫃", "timing": "【校對完成後】", "docs": "1. 規費收據", "critical": "", "details": "繳納規費後領取紙本執照。", "demo_only": False, "struct_only": False}
        ],
        "stage_1": [ 
            {"item": "空氣污染防制費申報", "dept": "環保局", "method": "線上", "timing": "【開工前】", "docs": "1. 合約書影本\n2. 建照影本", "critical": "⚠️ 首期申報：山坡地案需附詳細合約明細", "details": "**臺北市營建工程空污費網路申報系統**\n1. 註冊帳號\n2. 上傳文件\n3. 下載繳款書\n4. 繳款\n(面積>500m²需列管B8)", "demo_only": False, "struct_only": False},
            {"item": "建照科行政驗收抽查", "dept": "建管處", "method": "臨櫃", "timing": "【開工申報前】", "docs": "1. 抽查紀錄表\n2. 缺失改善報告", "critical": "⚠️ 關鍵門檻：缺失修正後，方得辦理開工", "details": "單一拆照或拆併建照案必辦。", "demo_only": True, "struct_only": False},
            {"item": "撤管防空避難設備", "dept": "警察分局", "method": "紙本", "timing": "【開工前】", "docs": "1. 函知公文", "critical": "", "details": "取得掛件收文戳章。", "demo_only": True, "struct_only": False},
            {"item": "開工前置-逕流廢水削減計畫", "dept": "環保局", "method": "線上", "timing": "【開工前】", "docs": "1. 削減計畫書", "critical": water_msg, "details": "門檻：面積 × 工期 >= 4600", "demo_only": False, "struct_only": False},
            {"item": "拆除計畫外審", "dept": "相關公會", "method": "會議", "timing": "【開工前】", "docs": "1. 拆除計畫書\n2. 審查核備函", "critical": demo_msg, "details": "地上10層以上建築物拆除必辦。", "demo_only": True, "struct_only": False},
            {"item": "開工申報 (正式掛號)", "dept": "建管處", "method": "線上", "timing": "【建照後6個月內】", "docs": "⚠️ 確認 NW 開工文件備齊", "critical": "⚠️ 線上掛號後 1 日內需親送正本核對", "details": "需使用 HICOS 憑證元件。核對無誤以系統送出日為準。", "demo_only": False, "struct_only": False}
        ],
        "stage_2": [ 
            {"item": "結構外審-細部設計審查", "dept": "結構外審公會", "method": "會議", "timing": "【施工計畫/放樣前】", "docs": "1. 細部結構配筋圖\n2. 無需變更設計切結書\n3. 核備公函", "critical": struct_msg, "details": "需完成細部設計審查並取得建照科核備，方可進行施工計畫及放樣。", "demo_only": False, "struct_only": True},
            {"item": "施工計畫說明會 (外審)", "dept": "相關公會", "method": "會議", "timing": "【計畫核定前】", "docs": "1. 施工計畫書\n2. 簡報", "critical": struct_msg, "details": "條件同結構外審 (深開挖、高樓層、大跨距等)。", "demo_only": False, "struct_only": False},
            {"item": "交通維持計畫", "dept": "交通局", "method": "紙本", "timing": "【施工計畫前】", "docs": "1. 交維計畫書", "critical": traffic_msg, "details": "樓地板面積>10000m²強制辦理。需配合施工大門、車行坡道。", "demo_only": False, "struct_only": False},
            {"item": "施工計畫書核備 (上傳)", "dept": "建管處", "method": "線上", "timing": "【放樣前】", "docs": "⚠️ 確認 NW 施工計畫文件備齊", "critical": "", "details": "**無紙化規定**：\n1. 掃描 A3/A4 格式 PDF。\n2. 配筋圖需至公會用印。\n3. 圖說檔案編號 NW4700~NW5000。", "demo_only": False, "struct_only": False},
            {"item": "舊屋拆除與廢棄物結案", "dept": "環保局", "method": "線上", "timing": "【拆除後】", "docs": "1. 結案申報書", "critical": "⚠️ B5/B8 未結案，無法進行放樣", "details": "拆除完成後需解除列管。", "demo_only": True, "struct_only": False}
        ],
        "stage_3": [ 
            {"item": "導溝勘驗申報", "dept": "建管處", "method": "線上", "timing": "【施工前2日】", "docs": "1. 申請書\n2. 照片", "critical": "", "details": "", "demo_only": False, "struct_only": False}
        ],
        "stage_4": [ 
            {"item": "放樣前置-用水/電/汙水核備", "dept": "自來水/台電/衛工", "method": "紙本", "timing": "【放樣前】", "docs": "1. 核備公函影本", "critical": "需承造人用印", "details": "免辦理條件：5樓/5戶/2000m²以下。", "demo_only": False, "struct_only": False},
            {"item": "地界複丈/路心樁復原", "dept": "地政事務所", "method": "臨櫃", "timing": "【拆除後】", "docs": "1. 複丈申請書", "critical": "", "details": "拆除後需重新確認地界。", "demo_only": True, "struct_only": False},
            {"item": "放樣勘驗申報", "dept": "建管處", "method": "線上", "timing": "【結構施工前】", "docs": "⚠️ 確認 NS 勘驗文件備齊", "critical": "⚠️ 現場不得先行施工", "details": "建管處網路核備後，需送建照正本及勘驗紙本至櫃台掛件。", "demo_only": False, "struct_only": False}
        ]
    }
    
    # [關鍵修正] 這裡不再依賴舊資料合併，而是直接從 session_state 的 Keys 讀取狀態
    # 這樣保證「介面顯示」與「邏輯判斷」一致
    for stage, items in raw_data.items():
        for item in items:
            key = generate_key(stage, item['item'])
            # 如果 session_state 裡有這個 key，就讀取它的值，否則預設 False
            item['done'] = st.session_state.get(f"chk_{key}", False)
            item['note'] = st.session_state.get(f"note_{key}", "")
            
    return raw_data

# --- 6. 定義文件與稽核清單 ---
def get_nw_checklists():
    # 這裡只定義靜態資料，狀態同樣由 session_state keys 管理
    return [
        ("NW0100", "開工", "建築工程開工申報書", "起造/建築/營造/技師/工地主任簽章", False),
        ("NW0500", "開工", "建築執照正本/影本", "需掃描正本", False),
        ("NW1000", "開工", "空氣污染防治費收據影本", "含核定單、營造廠大小章", False),
        ("NW1100", "開工", "逕流廢水削減計畫核備公函", "營造廠大小章 (達4600門檻者)", False),
        ("NW2400", "開工", "拆除施工計畫書", "依營建署格式 (拆除案)", True),
        
        ("NW3300", "計畫", "施工計畫書", "含防災應變、觀測系統、安全支撐", False),
        ("NW5000", "計畫", "配筋圖(A3)", "需至建築師公會用印", False),
        ("NW5300", "計畫", "交通維持計畫核准函", "達10000m²者必備", False),
        
        ("NS0100", "放樣", "建築工程勘驗申報書", "完整填註及用章", False),
        ("NS0900", "放樣", "勘驗現場照片", "建物立面、告示牌、綠美化、四向鋼筋", False),
        ("NS2100", "放樣", "放樣切結書", "起造/建築/承造/技師簽章", False)
    ]

def get_site_audit_list():
    return [
        ("現場告示牌", "拍照時人員不可遮擋資訊"),
        ("施工圍籬 (甲種)", "高度2.4m以上 (臨安全走廊3m)"),
        ("圍籬綠美化", "臨10m路需1/2面積綠化"),
        ("監視錄影系統", "需完整攝錄車牌，背景可辨識"),
        ("現況實測圖", "A1上色圖13份"),
        ("騎樓公告", "張貼騎樓打通/封閉公告")
    ]

# --- 7. 渲染 SOP 詳細清單 ---
def render_stage_detailed(stage_key, is_locked=False):
    data = get_current_sop_data() # 獲取最新狀態
    stage_items = data[stage_key]
    
    if is_locked: 
        st.markdown('<div class="locked-stage">🔒 請先完成上一階段</div>', unsafe_allow_html=True)
    
    for item in stage_items:
        # 顯示過濾
        if item.get("demo_only") and not is_demo_project: continue
        if item.get("demo_only") and item.get("critical") == "" and not is_demo_review_needed: continue
        if item.get("struct_only") and not is_struct_review_needed: continue

        with st.container():
            col1, col2 = st.columns([0.5, 9.5])
            
            # 產生唯一且穩定的 Key
            chk_key = f"chk_{generate_key(stage_key, item['item'])}"
            note_key = f"note_{generate_key(stage_key, item['item'])}"
            
            with col1:
                # [核心修正] 這裡直接創建 checkbox，不需要賦值，因為它的狀態由 key 自動管理
                # 當使用者點擊時，st.session_state[chk_key] 會自動更新
                # 我們只需要判斷是否需要 rerun
                prev_val = st.session_state.get(chk_key, False)
                curr_val = st.checkbox("", key=chk_key, disabled=is_locked)
                
                if curr_val != prev_val:
                    st.rerun() # 狀態改變，立即刷新以更新解鎖邏輯

            with col2:
                # 標題與樣式
                method = item.get('method', '現場')
                method_tag = f'<span class="tag-online">🔵 線上</span>' if method == "線上" else f'<span class="tag-paper">🟤 {method}</span>'
                tags = method_tag
                if item.get("demo_only"): tags += ' <span class="tag-demo">🏗️ 拆除</span>'
                if item.get("struct_only"): tags += ' <span class="tag-struct">🏢 結構外審</span>'
                
                title_html = f"**{item['item']}** {tags} <span style='color:#666; font-size:0.9em'>(🏢 {item['dept']})</span>"
                
                if curr_val: # 使用當前 checkbox 的值
                    st.markdown(f"<span style='color:#2E7D32; font-weight:bold;'>✅ {item['item']}</span>", unsafe_allow_html=True)
                else: 
                    st.markdown(title_html, unsafe_allow_html=True)
                
                if item.get("critical"): st.markdown(f"<div class='critical-info'>{item['critical']}</div>", unsafe_allow_html=True)

                with st.expander("🔽 詳細指引與備註", expanded=False):
                    st.markdown(f"**🕒 時機：** {item['timing']}")
                    st.markdown(f"**📄 文件：**\n{item['docs']}")
                    if item['details']: st.markdown(f"<div class='info-box'>💡 <b>指引：</b><br>{item['details']}</div>", unsafe_allow_html=True)
                    st.text_input("備註", key=note_key)
        st.divider()

# --- 8. 簡易檢查表渲染 ---
def render_checklist_simple(filter_type, title):
    with st.expander(f"📑 {title} (點擊展開)", expanded=False):
        st.markdown(f'<div class="nw-header">請確認 PDF 檔案已備齊並完成用印/掃描：</div>', unsafe_allow_html=True)
        checklist = get_nw_checklists()
        for code, cat, name, note, demo_only in checklist:
            if cat != filter_type: continue
            if demo_only and not is_demo_project: continue
            
            c1, c2, c3 = st.columns([0.5, 4, 5.5])
            chk_key = f"chk_nw_{code}"
            
            with c1: st.checkbox("", key=chk_key)
            is_checked = st.session_state.get(chk_key, False)
            
            with c2: 
                style = "color:#2E7D32; font-weight:bold;" if is_checked else ""
                st.markdown(f"<span style='{style}'>{code} {name}</span>", unsafe_allow_html=True)
            with c3: st.caption(f"🖊️ {note}")

def render_site_audit():
    st.markdown('<div class="check-header">📸 現場放樣勘驗自我稽核 (務必確認以免退件)</div>', unsafe_allow_html=True)
    audit_list = get_site_audit_list()
    for name, note in audit_list:
        c1, c2, c3 = st.columns([0.5, 4, 5.5])
        chk_key = f"chk_site_{name}"
        with c1: 
            if st.checkbox("", key=chk_key):
                st.rerun()
        is_checked = st.session_state.get(chk_key, False)
        
        with c2: st.markdown(f"**{name}**" if not is_checked else f"<span style='color:#2E7D32;font-weight:bold;'>{name}</span>", unsafe_allow_html=True)
        with c3: st.info(f"💡 {note}")
        st.divider()

# --- 9. 主流程 (解鎖邏輯) ---
def check_stage_complete(stage_key):
    data = get_current_sop_data()
    items = data[stage_key]
    for item in items:
        # 必須過濾掉不顯示的項目，否則永遠不會解鎖
        if item.get("demo_only") and not is_demo_project: continue
        if item.get("demo_only") and item.get("critical") == "" and not is_demo_review_needed: continue
        if item.get("struct_only") and not is_struct_review_needed: continue
        
        # 檢查對應的 key 是否為 True
        key = f"chk_{generate_key(stage_key, item['item'])}"
        if not st.session_state.get(key, False):
            return False
    return True

s0_done = check_stage_complete('stage_0')
s1_done = check_stage_complete('stage_1')
s2_done = check_stage_complete('stage_2')

tabs = st.tabs(["0.建照領取", "1.開工申報(NW)", "2.施工計畫(NW)", "3.導溝勘驗", "4.放樣勘驗(NS)"])

with tabs[0]:
    st.subheader("🔑 階段零：建照領取")
    render_stage_detailed("stage_0", is_locked=False)

with tabs[1]:
    st.subheader("📋 階段一：開工申報 (含NW開工文件)")
    if not s0_done: st.markdown('<div class="locked-stage">🔒 請先完成建照領取</div>', unsafe_allow_html=True)
    else:
        render_checklist_simple("開工", "NW 開工文件準備檢查表")
        st.markdown("---")
        render_stage_detailed("stage_1", is_locked=False)

with tabs[2]:
    st.subheader("📘 階段二：施工計畫 (含NW計畫文件)")
    if not (s0_done and s1_done): st.markdown('<div class="locked-stage">🔒 請先完成開工申報</div>', unsafe_allow_html=True)
    else:
        render_checklist_simple("計畫", "NW 施工計畫文件準備檢查表")
        st.markdown("---")
        render_stage_detailed("stage_2", is_locked=False)

with tabs[3]:
    st.subheader("🚧 階段三：導溝勘驗")
    render_stage_detailed("stage_3", is_locked=not (s0_done and s1_done and s2_done))

with tabs[4]:
    st.subheader("📐 階段四：放樣勘驗 (含NS勘驗文件)")
    if not (s0_done and s1_done and s2_done): st.markdown('<div class="locked-stage">🔒 請先完成施工計畫</div>', unsafe_allow_html=True)
    else:
        with st.expander("📸 現場放樣勘驗自我稽核 (現場準備)", expanded=True):
            render_site_audit()
        render_checklist_simple("放樣", "NS 放樣勘驗文件準備檢查表")
        st.markdown("---")
        render_stage_detailed("stage_4", is_locked=False)

# --- 10. Excel 下載 ---
st.write("---")
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    data = get_current_sop_data()
    all_rows = []
    for k, v in data.items():
        for item in v:
            # 匯出時過濾
            if item.get("demo_only") and not is_demo_project: continue
            if item.get("struct_only") and not is_struct_review_needed: continue
            
            key = f"chk_{generate_key(k, item['item'])}"
            item['done'] = st.session_state.get(key, False)
            item['note'] = st.session_state.get(f"note_{generate_key(k, item['item'])}", "")
            
            item_copy = item.copy()
            item_copy['階段代號'] = k
            all_rows.append(item_copy)
    
    if all_rows:
        pd.DataFrame(all_rows).to_excel(writer, index=False, sheet_name='SOP流程')
    
st.download_button("📥 下載完整 Excel", buffer.getvalue(), f"SOP_Full_V{CURRENT_VERSION}_{date.today()}.xlsx", "application/vnd.ms-excel")