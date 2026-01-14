import streamlit as st
import pandas as pd
import io
import hashlib
from datetime import date

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="建案行政SOP系統 (V17.0 詳細法規版)",
    page_icon="🏗️",
    layout="wide"
)

# --- 2. 🛡️ 版本控制 (V17.0) ---
CURRENT_VERSION = 17.0

if "data_version" not in st.session_state:
    st.session_state.clear()
    st.session_state.data_version = CURRENT_VERSION
elif st.session_state.data_version != CURRENT_VERSION:
    st.session_state.clear()
    st.session_state.data_version = CURRENT_VERSION
    st.rerun()

# --- 3. 初始化狀態 ---
special_flags = [
    "flag_slope", "flag_public", "flag_expired", 
    "flag_change", "flag_existing", "flag_demo_included"
]
for flag in special_flags:
    if flag not in st.session_state:
        st.session_state[flag] = False

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
    
    .special-context {
        background-color: #f3e5f5; 
        padding: 15px; 
        border-radius: 8px; 
        border: 1px solid #e1bee7;
        margin-bottom: 15px;
    }
    div[data-testid="stExpander"] { margin-top: -5px; }
</style>
""", unsafe_allow_html=True)

st.title(f"🏗️ 建案行政SOP系統 (Ver {CURRENT_VERSION})")
st.caption("更新：詳細收錄 B8 廢棄物列管時機 (四科) 與 逕流廢水 (二科/環評) 規定")

# --- 4. 輔助函數 ---
@st.cache_data
def generate_key_cached(stage, item_name):
    return f"{stage}_{item_name}".replace(" ", "_")

# --- 5. 側邊欄：參數輸入 ---
with st.sidebar:
    st.header("⚙️ 專案參數設定")
    project_type = st.radio("案件類型", ["素地新建案", "拆除併建造執照案"])
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
        (is_geo_sensitive and (excavation_depth > 7 or floors_below > 1))
    )
    is_demo_review_needed = is_demo_project and floors_above > 10
    
    st.divider()
    if st.button("🔄 強制重置系統"):
        st.session_state.clear()
        st.rerun()

# --- 6. 動態生成空污費詳細文字 (Helper) ---
def get_air_pollution_context():
    f_slope = st.session_state.flag_slope
    f_public = st.session_state.flag_public
    f_expired = st.session_state.flag_expired
    f_change = st.session_state.flag_change
    f_existing = st.session_state.flag_existing
    f_demo = st.session_state.flag_demo_included

    doc_details = []
    
    if f_slope:
        doc_details.append("★ **山坡地基地**：\n   需檢附合約之「封面、條款、甲乙方、總價金額、用印欄頁及工程項次明細表」等影本 (需全部業主用章)。")
    
    if f_public:
        doc_details.append("★ **工程契約型(公務)**：\n   1. 工程契約書影本 (含封面、契約價金之給付條款總價頁、甲乙雙人用印頁、工程總表及明細表、決標記錄影本)。\n   2. 業務主管機關之開工證明「正本」。\n   (均需用起造人大小章)。")
    else:
        doc_details.append("★ **一般案件**：\n   需檢附合約影本 (含封面、條款、甲乙方、總價金額、用印欄頁)。")
        
    if f_expired:
        doc_details.append("★ **領照逾6個月**：\n   應檢附「開工展期申請書」影本 (全部業主大小章)。")
        
    if f_change:
        doc_details.append("★ **變更過起造人/承造人**：\n   應檢附「變更申請書」影本 (全部業主大小章)。")
        
    if f_existing:
        doc_details.append("★ **基地已有建物(如學校)**：\n   請加附「建築執照申請書」及「建物概要表」影本 (全部業主大小章)。")
        
    if f_demo:
        doc_details.append("★ **屬建照列管拆照者**：\n   檢附「拆照影本」及「拆照空污費繳費單」影本 (全部業主大小章)。")

    return "\n\n".join(doc_details)

# --- 7. 核心 SOP 資料庫 ---
def get_current_sop_data():
    b8_msg = "⚠️ 需向環保局四科辦理 B8 列管 (面積>500m² 或 經費>500萬)" if is_b8_needed else ""
    water_msg = f"⚠️ 數值 {pollution_value} (達4600) 需向環保局二科辦理" if is_water_plan_needed else "✅ 免辦理"
    traffic_msg = "⚠️ 強制辦理 (面積>10000m²)" if is_traffic_plan_needed else ""
    struct_msg = "⚠️ 符合外審條件：需辦理細部設計審查" if is_struct_review_needed else ""
    demo_msg = "⚠️ 拆除規模>10層：需辦理拆除計畫外審" if is_demo_review_needed else ""

    raw_data = {
        "stage_0": [ 
            {"item": "建築執照申請作業", "dept": "建築師/建管處", "method": "線上", "timing": "【掛號階段】", "docs": "1. 申請書電子檔\n2. 書圖文件", "critical": "", "details": "透過無紙化審查系統上傳。", "demo_only": False, "struct_only": False},
            {"item": "領取建造執照", "dept": "建管處", "method": "臨櫃", "timing": "【校對完成後】", "docs": "1. 規費收據", "critical": "", "details": "繳納規費後領取紙本執照。", "demo_only": False, "struct_only": False}
        ],
        "stage_1": [ 
            {
                "item": "空氣污染防制費申報", 
                "dept": "環保局(空噪科)", 
                "method": "線上", 
                "timing": "【開工前】", 
                "docs": "基本：申報書、建照影本 (點開下方檢核表看詳情)", 
                "critical": b8_msg, 
                "details": f"""
                **1. 營建混合物 (B8) 運送清理計畫：**
                * **門檻**：工程面積 > 500 $m^2$ 或 合約經費 > 500 萬元。
                * **承辦單位**：市府環保局 (**第四科**)。
                * **申報時機**：
                    * **拆照/拆併建案**：於「開工申辦時」列管。
                    * **一般建照案**：於「放樣勘驗時」列管。
                * **結算**：均於「使照核發時」列管結算。
                
                **2. 作業指引：**
                請承造人依環保局 (第四科) 函件要求依程序辦理。
                """, 
                "demo_only": False, "struct_only": False
            },
            {"item": "建照科行政驗收抽查", "dept": "建管處", "method": "臨櫃", "timing": "【開工申報前】", "docs": "1. 抽查紀錄表\n2. 缺失改善報告", "critical": "⚠️ 關鍵門檻：缺失修正後，方得辦理開工", "details": "單一拆照或拆併建照案必辦。", "demo_only": True, "struct_only": False},
            {"item": "撤管防空避難設備", "dept": "警察分局", "method": "紙本", "timing": "【開工前】", "docs": "1. 函知公文", "critical": "", "details": "取得掛件收文戳章。", "demo_only": True, "struct_only": False},
            {
                "item": "開工前置-逕流廢水削減計畫", 
                "dept": "環保局(二科)", 
                "method": "線上", 
                "timing": "【開工前】", 
                "docs": "1. 削減計畫書\n2. 沉沙池圖說", 
                "critical": water_msg, 
                "details": """
                **1. 辦理標準：**
                凡施工面積 ($m^2$) × 施工工期 (月) ≥ 4600 者均需辦理。
                
                **2. 承辦單位：**
                市府環保局 (**第二科**)。
                
                **3. 注意事項：**
                * 須於申報開工前取得核准公函，方得辦理開工作業。
                * **雜項執照**：非屬上列要求，可免辦本計畫審查。
                * **環評基地**：應送「環評報告審查公會」辦理審查，經公會核備後再轉環保局簽核。
                """, 
                "demo_only": False, "struct_only": False
            },
            {"item": "拆除計畫外審", "dept": "相關公會", "method": "會議", "timing": "【開工前】", "docs": "1. 拆除計畫書\n2. 審查核備函", "critical": demo_msg, "details": "地上10層以上建築物拆除必辦。", "demo_only": True, "struct_only": False},
            {"item": "開工申報 (正式掛號)", "dept": "建管處", "method": "線上", "timing": "【建照後6個月內】", "docs": "⚠️ 確認 NW 開工文件備齊", "critical": "⚠️ 線上掛號後 1 日內需親送正本核對", "details": "需使用 HICOS 憑證元件。核對無誤以系統送出日為準。", "demo_only": False, "struct_only": False}
        ],
        "stage_2": [ 
            {"item": "結構外審-細部設計審查", "dept": "結構外審公會", "method": "會議", "timing": "【施工計畫/放樣前】", "docs": "1. 細部結構配筋圖\n2. 核備公函", "critical": struct_msg, "details": "需完成細部設計審查並取得建照科核備。", "demo_only": False, "struct_only": True},
            {"item": "施工計畫說明會 (外審)", "dept": "相關公會", "method": "會議", "timing": "【計畫核定前】", "docs": "1. 施工計畫書\n2. 簡報", "critical": struct_msg, "details": "條件同結構外審 (深開挖、高樓層、大跨距等)。", "demo_only": False, "struct_only": False},
            {"item": "交通維持計畫", "dept": "交通局", "method": "紙本", "timing": "【施工計畫前】", "docs": "1. 交維計畫書", "critical": traffic_msg, "details": "樓地板面積>10000m²強制辦理。", "demo_only": False, "struct_only": False},
            {"item": "施工計畫書核備 (上傳)", "dept": "建管處", "method": "線上", "timing": "【放樣前】", "docs": "⚠️ 確認 NW 施工計畫文件備齊", "critical": "", "details": "**無紙化規定**：\n1. 掃描 A3(圖說)/A4 格式 PDF。\n2. 配筋圖需至公會用印。\n3. 圖說檔案編號 NW4700~NW5000。", "demo_only": False, "struct_only": False},
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
    return raw_data

# --- 8. 完整文件清單 (快取優化) ---
@st.cache_data
def get_all_checklists_cached():
    # 1. 開工申報 (NW0100-NW9900)
    list_start = [
        ("NW0100", "建築工程開工申報書", "起造/建築/營造/技師/工地主任簽章", False),
        ("NW0200", "起造人名冊", "各起造人用起造章", False),
        ("NW0300", "承造人名冊", "", False),
        ("NW0400", "監造人名冊", "", False),
        ("NW0500", "建築執照正本/影本", "需掃描正本", False),
        ("NW0600", "建築執照申請書", "", False),
        ("NW0700", "建築工程開工查報表", "", False),
        ("NW0800", "工地現場照片", "彩色PDF", False),
        ("NW0900", "基地位置圖", "A4大小、營造廠大小章", False),
        ("NW1000", "空氣污染防治費收據影本", "含核定單、營造廠大小章", False),
        ("NW1100", "逕流廢水削減計畫核備公函", "營造廠大小章 (達4600門檻者)", False),
        ("NW1200", "建照列管事項辦理證明", "", False),
        ("NW1300", "施工計畫備查資料表", "營造廠大小章", False),
        ("NW1400", "施工計劃書簽章負責表", "", False),
        ("NW1500", "營造業承攬手冊(登記證書)", "浮貼負責人及技師照片之簽名影本", False),
        ("NW1600", "營造業承攬手冊(負責人簽章)", "彩色影印", False),
        ("NW1700", "營造業承攬手冊(專任工程人員簽章)", "彩色影印", False),
        ("NW1800", "專任工程人員公會會員證", "當年度正本", False),
        ("NW1900", "工地主任(會員證)", "營造廠大小章", False),
        ("NW2000", "工地主任(執業證)", "營造廠大小章", False),
        ("NW2100", "監造建築師(會員證)", "當年度正本", False),
        ("NW2200", "監造建築師(執業證)", "", False),
        ("NW2300", "鄰房現況鑑定報告/切結書", "拆照案強制鑑定 / 素地可切結", False), 
        ("NW2400", "拆除施工計畫書", "依營建署格式", True), 
        ("NW2500", "監拆報告書", "建築師用章", True), 
        ("NW2600", "拆除剩餘資源備查公文(B5)", "都發局核准函", True), 
        ("NW2700", "拆除廢棄物清理計畫備查公文(B8)", "環保局核准函", True),
        ("NW2800", "拆除施工計畫說明會文件", "地上10樓以上拆除", True),
        ("NW2900", "塔式起重機自主檢查表", "無則附切結書", False),
        ("NW3000", "未使用塔式起重機具切結書", "", False),
        ("NW3100", "開工展期文件", "若領照逾6個月", False),
        ("NW9900", "其他文件", "", False)
    ]
    
    # 2. 施工計畫
    list_plan = [
        ("NW0500", "建築執照", "掃描正本", False),
        ("NW1300", "施工計畫備查資料表", "建管處網站下載", False),
        ("NW1400", "施工計畫書簽章負責表", "起造/建築/營造/技師簽章", False),
        ("NW1500", "營造業承攬手冊(登記證書)", "", False),
        ("NW1600", "營造業承攬手冊(負責人簽章)", "", False),
        ("NW3200", "施工計畫書申請備案報告表", "承造人蓋章", False),
        ("NW3300", "施工計畫書", "含防災應變、觀測系統、安全支撐", False),
        ("NW3400", "工程告示牌設計圖", "起造/建築/營造用章", False),
        ("NW3500", "工地主任證書/勞保", "無則免", False),
        ("NW3600", "勞安人員證書/勞保", "營造廠蓋章", False),
        ("NW3700", "申報勘驗順序表", "承造/技師/監造簽章確認 (逆打需加附開口示意)", False),
        ("NW3800", "預定施工進度表", "建築師/承造人蓋章", False),
        ("NW3900", "公共管線查線函", "五大管線回函 (5樓/2000m²以下免附)", False),
        ("NW4000", "緊急應變計畫", "含緊急聯絡名冊", False),
        ("NW4100", "工程保險", "山坡地案件", False),
        ("NW4200", "工程材料品質管理計畫", "併檢附結構材料強度圖說", False),
        ("NW4300", "運送憑證應辦事項及聯單管制", "", False),
        ("NW4400", "空氣品質惡化營建工地防制措施", "", False),
        ("NW4500", "建照工程專業工項施作情形表", "", False),
        ("NW4600", "特定施工項目技術士表", "", False),
        ("NW4700", "鷹架/圍籬/大門大樣圖", "建築師/營造廠/技師用章", False),
        ("NW4800", "平面安全設施配置圖", "繪於建照核准圖", False),
        ("NW4900", "四向立面安全設施配置圖", "繪於建照核准圖(含鷹架/護網/帆布)", False),
        ("NW5000", "配筋圖", "需至建築師公會用印 (A3圖說)", False),
        ("NW5100", "圍籬綠美化圖說", "含維護及回收計畫 (臨10M路需綠化)", False),
        ("NW5200", "臨時借用道路說明書", "含告示牌/通知單", False),
        ("NW5300", "交通維持計畫核准函", "達10000m²者必備", False),
        ("NW5400", "施工計畫說明會審查函", "達外審標準者必備", False),
        ("NW5500", "塔式起重機審查核可函", "勞檢處/交通局核准", False),
        ("NW5600", "山坡地開工許可證", "山坡地案", False),
        ("NW5700", "觀測系統平面圖及應變計畫", "開挖深達1.5m者必備", False),
        ("NW5800", "安全支撐及擋土措施圖說", "開挖深達1.5m者必備", False),
        ("NW5900", "施工構台應力分析", "開挖面積>500m²者必備", False),
        ("NW6000", "模板支撐應力檢討", "跨距>12m或淨高>3.5m", False),
        ("NW6100", "現有巷道封閉改道計畫核准", "", False),
        ("NW6200", "逾期罰款繳款單據", "", False),
        ("NW9900", "其他文件", "建築線指示圖、複丈成果圖、鑽探報告", False)
    ]
    
    # 3. 放樣勘驗
    list_ns = [
        ("NS0100", "建築工程勘驗申報書", "完整填註及用章", False),
        ("NS0200", "建築執照存根", "含變更設計", False),
        ("NS0300", "勘驗順序表", "確認目前進度", False),
        ("NS0400", "必需勘驗部分申報表", "", False),
        ("NS0500", "建築物監造報告表", "110/10/01起廢止", False),
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
        ("NS1600", "碎石粒料級配酸鹼值檢測", "", False),
        ("NS1601", "爐碴(石)檢測報告書", "", False),
        ("NS1700", "鋼筋抗拉強度試驗報告", "", False),
        ("NS1800", "鋼筋材料品管查核報告表", "", False),
        ("NS1900", "混凝土抗壓強度試驗報告", "", False),
        ("NS2000", "混凝土配合比例設計計算表", "", False),
        ("NS2100", "放樣切結書", "起造/建築/承造/技師簽章", False),
        ("NS2200", "公會抽查紀錄表", "二樓版/十樓版", False),
        ("NS2300", "縮短工期安全無虞切結書", "", False),
        ("NS2400", "紅火蟻清查紀錄表", "每月第1次申報檢附", False),
        ("NS2500", "剩餘資源備查函", "處理計畫/完成報告", False),
        ("NS2600", "專業工項施作情形表", "", False),
        ("NS2700", "流出抑制設施審查函", "", False),
        ("NS2800", "自來水設備審查函", "", False),
        ("NS2900", "電力/避雷核可文件", "", False),
        ("NS3000", "候選綠建築證書", "簽證圖說一致", False),
        ("NS3100", "消防設備審查核准函", "", False),
        ("NS3200", "執照注意事項列管文件", "", False),
        ("NS3300", "施工日誌", "前一日日誌(技師/主任簽章)", False),
        ("NS9900", "勘驗相關文件-其他", "", False)
    ]
    return list_start, list_plan, list_ns

@st.cache_data
def get_site_audit_list_cached():
    return [
        ("現場告示牌", "拍照時人員不可遮擋資訊"),
        ("施工圍籬 (甲種)", "高度2.4m以上 (臨安全走廊3m)"),
        ("圍籬綠美化", "臨10m路需1/2面積綠化"),
        ("監視錄影系統", "需完整攝錄車牌，背景可辨識"),
        ("現況實測圖", "A1上色圖13份"),
        ("騎樓公告", "張貼騎樓打通/封閉公告")
    ]

# --- 9. 狀態初始化與同步 ---
# 取得靜態資料 (Cached)
list_start, list_plan, list_ns = get_all_checklists_cached()
site_list = get_site_audit_list_cached()

# 取得動態資料
sop_data = get_current_sop_data()

# 初始化 Checklist 狀態
for lst, cat in [(list_start, "start"), (list_plan, "plan"), (list_ns, "ns")]:
    for code, _, _, _ in lst:
        key = f"chk_{code}_{cat}"
        if key not in st.session_state:
            st.session_state[key] = False

# 初始化現場稽核狀態
for item in site_list:
    key = f"chk_site_{item[0]}"
    if key not in st.session_state:
        st.session_state[key] = False

# 初始化 SOP 項目狀態 (確保 key 存在)
for stage, items in sop_data.items():
    for item in items:
        chk_key = f"chk_{generate_key_cached(stage, item['item'])}"
        if chk_key not in st.session_state:
            st.session_state[chk_key] = False
        if f"note_{chk_key[4:]}" not in st.session_state:
            st.session_state[f"note_{chk_key[4:]}"] = ""

# --- 10. 渲染函數 (移除手動 Rerun，依賴原生綁定) ---
def render_stage_detailed(stage_key, is_locked=False):
    stage_items = sop_data[stage_key]
    
    if is_locked: 
        st.markdown('<div class="locked-stage">🔒 請先完成上一階段</div>', unsafe_allow_html=True)
    
    for item in stage_items:
        if item.get("demo_only") and not is_demo_project: continue
        if item.get("demo_only") and item.get("critical") == "" and not is_demo_review_needed: continue
        if item.get("struct_only") and not is_struct_review_needed: continue

        with st.container():
            col1, col2 = st.columns([0.5, 9.5])
            chk_key = f"chk_{generate_key_cached(stage_key, item['item'])}"
            note_key = f"note_{generate_key_cached(stage_key, item['item'])}"
            
            with col1:
                # [核心修正] 使用 key 綁定，不手動 rerun，避免兩次刷新造成的 lag
                st.checkbox("", key=chk_key, disabled=is_locked)
                is_checked = st.session_state[chk_key]

            with col2:
                method = item.get('method', '現場')
                method_tag = f'<span class="tag-online">🔵 線上</span>' if method == "線上" else f'<span class="tag-paper">🟤 {method}</span>'
                demo_tag = '<span class="tag-demo">🏗️ 拆除</span>' if item.get("demo_only") else ""
                
                title_html = f"**{item['item']}** {method_tag} {demo_tag} <span style='color:#666; font-size:0.9em'>(🏢 {item['dept']})</span>"
                
                if is_checked: 
                    st.markdown(f"<span style='color:#2E7D32; font-weight:bold;'>✅ {item['item']}</span>", unsafe_allow_html=True)
                else: 
                    st.markdown(title_html, unsafe_allow_html=True)
                
                if item.get("critical"): st.markdown(f"<div class='critical-info'>{item['critical']}</div>", unsafe_allow_html=True)

                # 空污費特殊區塊
                if item['item'] == "空氣污染防制費申報":
                    with st.expander("🔽 詳細指引與檢核 (含特殊案件勾選)", expanded=False):
                        st.markdown("""
                        <div class='special-context'>
                        <b>🚩 特殊案件條件勾選 (系統將自動更新下方清單)：</b><br>
                        """, unsafe_allow_html=True)
                        
                        # [優化] 改用 key 綁定，移除 st.rerun() 以減少卡頓
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
                        
                        st.markdown(f"**🕒 時機：** {item['timing']}")
                        st.markdown("---")
                        st.markdown(f"**📄 自動產生應備文件清單：**\n\n{dynamic_details}")
                        st.markdown("---")
                        st.markdown(f"**💡 作業指引：**\n臺北市營建工程空污費網路申報系統 (02-27208889 #7252)\n1.註冊 -> 2.申報 -> 3.繳款")
                        
                        # 固定顯示 B8 與 逕流廢水資訊
                        st.markdown(f"**⚠️ B8 營建混合物 (四科)：**\n{item['details'].split('**⚠️ B8')[1] if '**⚠️ B8' in item['details'] else '詳見上方說明'}")
                        
                        st.text_input("備註", key=note_key)
                
                # 逕流廢水特殊區塊 (顯示詳細法規)
                elif "逕流廢水" in item['item']:
                     with st.expander("🔽 詳細指引與備註", expanded=False):
                        st.markdown(f"**🕒 時機：** {item['timing']}")
                        st.markdown(f"**📄 文件：**\n{item['docs']}")
                        st.markdown(f"""
                        **💡 作業指引 (環保局二科)：**
                        {item['details']}
                        """)
                        st.text_input("備註", key=note_key)

                else:
                    with st.expander("🔽 詳細指引與備註", expanded=False):
                        st.markdown(f"**🕒 時機：** {item['timing']}")
                        st.markdown(f"**📄 文件：**\n{item['docs']}")
                        if item['details']: st.markdown(f"<div class='info-box'>💡 <b>指引：</b><br>{item['details']}</div>", unsafe_allow_html=True)
                        st.text_input("備註", key=note_key)
        st.divider()

def render_checklist(checklist_data, title, tab_name):
    with st.expander(f"📑 {title} (點擊展開)", expanded=False):
        st.markdown(f'<div class="nw-header">請確認 PDF 檔案已備齊並完成用印/掃描：</div>', unsafe_allow_html=True)
        for code, name, note, demo_only in checklist_data:
            if demo_only and not is_demo_project: continue
            c1, c2, c3 = st.columns([0.5, 4, 5.5])
            
            unique_id = f"{code}_{tab_name}"
            chk_key = f"chk_{unique_id}"
            
            # 使用原生 key 綁定
            st.checkbox("", key=chk_key)
            is_checked = st.session_state[chk_key]

            with c2: 
                style = "color:#2E7D32; font-weight:bold;" if is_checked else ""
                st.markdown(f"<span style='{style}'>{code} {name}</span>", unsafe_allow_html=True)
            with c3: st.caption(f"🖊️ {note}")

def render_site_audit():
    st.markdown('<div class="check-header">📸 現場放樣勘驗自我稽核 (務必確認以免退件)</div>', unsafe_allow_html=True)
    audit_list = get_site_audit_list_cached()
    for name, note in audit_list:
        c1, c2, c3 = st.columns([0.5, 4, 5.5])
        chk_key = f"chk_site_{name}"
        
        st.checkbox("", key=chk_key)
        is_checked = st.session_state[chk_key]
        
        with c2: st.markdown(f"**{name}**" if not is_checked else f"<span style='color:#2E7D32;font-weight:bold;'>{name}</span>", unsafe_allow_html=True)
        with c3: st.info(f"💡 {note}")
        st.divider()

# --- 12. 主流程 (解鎖邏輯) ---
def check_stage_complete(stage_key):
    items = sop_data[stage_key]
    for item in items:
        if item.get("demo_only") and not is_demo_project: continue
        if item.get("demo_only") and item.get("critical") == "" and not is_demo_review_needed: continue
        if item.get("struct_only") and not is_struct_review_needed: continue
        
        key = f"chk_{generate_key_cached(stage_key, item['item'])}"
        if not st.session_state.get(key, False):
            return False
    return True

# 計算解鎖狀態 (Streamlit 會自動在每次 Rerun 時重新計算這裡)
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
        render_checklist(list_start, "NW 開工文件準備檢查表", "start")
        st.markdown("---")
        st.markdown("### ✅ 正式申報流程")
        render_stage_detailed("stage_1", is_locked=False)

with tabs[2]:
    st.subheader("📘 階段二：施工計畫 (含NW計畫文件)")
    if not (s0_done and s1_done): st.markdown('<div class="locked-stage">🔒 請先完成開工申報</div>', unsafe_allow_html=True)
    else:
        render_checklist(list_plan, "NW 施工計畫文件準備檢查表", "plan")
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
        render_checklist(list_ns, "NS 放樣勘驗文件準備檢查表", "survey")
        st.markdown("---")
        render_stage_detailed("stage_4", is_locked=False)

# --- 13. Excel 下載 ---
st.write("---")
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    all_rows = []
    for k, v in sop_data.items():
        for item in v:
            if item.get("demo_only") and not is_demo_project: continue
            
            key = f"chk_{generate_key_cached(k, item['item'])}"
            item['done'] = st.session_state.get(key, False)
            item['note'] = st.session_state.get(f"note_{generate_key_cached(k, item['item'])}", "")
            
            item_copy = item.copy()
            item_copy['階段代號'] = k
            all_rows.append(item_copy)
    
    if all_rows:
        pd.DataFrame(all_rows).to_excel(writer, index=False, sheet_name='SOP流程')
    
    check_rows = []
    for lst, cat in [(list_start, "start"), (list_plan, "plan"), (list_ns, "ns")]:
        for code, name, note, demo_only in lst:
            if demo_only and not is_demo_project: continue
            status = "完成" if st.session_state.get(f"chk_{code}_{cat}", False) else "未完成"
            check_rows.append({"階段": cat, "編號": code, "名稱": name, "備註": note, "狀態": status})
            
    if check_rows:
        pd.DataFrame(check_rows).to_excel(writer, index=False, sheet_name='文件檢查表')

st.download_button("📥 下載完整 Excel", buffer.getvalue(), f"SOP_Full_V{CURRENT_VERSION}_{date.today()}.xlsx", "application/vnd.ms-excel")