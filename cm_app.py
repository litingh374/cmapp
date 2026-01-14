import streamlit as st
import pandas as pd
import io
import hashlib
from datetime import date

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="建案行政SOP系統 (V12.0 完整收錄版)",
    page_icon="🏗️",
    layout="wide"
)

# --- 2. 🛡️ 版本控制 (V12.0) ---
CURRENT_VERSION = 12.0

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

st.title(f"🏗️ 建案行政SOP系統 (Ver {CURRENT_VERSION})")
st.caption("完整收錄：開工NW全表、施工計畫NW全表、放樣NS全表 (含重複項目獨立檢核)")

# --- 3. 輔助函數 ---
def generate_key(stage, item_name):
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
        
    is_slope_land = st.checkbox("位於山坡地", value=False)

    # 判讀邏輯
    pollution_value = base_area * duration_month
    is_water_plan_needed = pollution_value >= 4600
    is_traffic_plan_needed = total_area > 10000
    
    is_struct_review_needed = (
        building_height > 50 or 
        floors_above > 15 or 
        excavation_depth > 12 or 
        floors_below > 3
    )
    is_demo_review_needed = is_demo_project and floors_above > 10
    
    st.divider()
    if st.button("🔄 強制重置系統"):
        st.session_state.clear()
        st.rerun()

# --- 5. 核心 SOP 資料庫 ---
def get_current_sop_data():
    water_msg = f"⚠️ 數值 {pollution_value} (達4600門檻) 需辦理" if is_water_plan_needed else "✅ 免辦理"
    traffic_msg = "⚠️ 強制辦理 (面積>10000m²)" if is_traffic_plan_needed else ""
    struct_msg = "⚠️ 符合外審條件：需辦理細部設計審查" if is_struct_review_needed else ""
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
            {"item": "開工申報 (正式掛號)", "dept": "建管處", "method": "線上", "timing": "【建照後6個月內】", "docs": "⚠️ 確認 NW 開工文件備齊 (下方清單)", "critical": "⚠️ 線上掛號後 1 日內需親送正本核對", "details": "需使用 HICOS 憑證元件。核對無誤以系統送出日為準。", "demo_only": False, "struct_only": False}
        ],
        "stage_2": [ 
            {"item": "結構外審-細部設計審查", "dept": "結構外審公會", "method": "會議", "timing": "【施工計畫/放樣前】", "docs": "1. 細部結構配筋圖\n2. 核備公函", "critical": struct_msg, "details": "需完成細部設計審查並取得建照科核備。", "demo_only": False, "struct_only": True},
            {"item": "施工計畫說明會 (外審)", "dept": "相關公會", "method": "會議", "timing": "【計畫核定前】", "docs": "1. 施工計畫書\n2. 簡報", "critical": struct_msg, "details": "條件同結構外審 (深開挖、高樓層、大跨距等)。", "demo_only": False, "struct_only": False},
            {"item": "交通維持計畫", "dept": "交通局", "method": "紙本", "timing": "【施工計畫前】", "docs": "1. 交維計畫書", "critical": traffic_msg, "details": "樓地板面積>10000m²強制辦理。", "demo_only": False, "struct_only": False},
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
    
    for stage, items in raw_data.items():
        for item in items:
            key = generate_key(stage, item['item'])
            item['done'] = st.session_state.get(f"chk_{key}", False)
            item['note'] = st.session_state.get(f"note_{key}", "")
            
    return raw_data

# --- 6. 定義完整文件清單 (收錄所有重複項目) ---
def get_all_checklists():
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
        ("NW3100", "開工展期文件", "", False),
        ("NW9900", "其他文件", "", False)
    ]
    
    # 2. 施工計畫 (NW0500...NW3200-NW9900)
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

    # 3. 放樣勘驗 (NS0100-NS9900)
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

# --- 6. 狀態初始化 ---
if "sop_data" not in st.session_state:
    st.session_state.sop_data = get_current_sop_data()

list_start, list_plan, list_ns = get_all_checklists()
all_checklists_codes = []
for lst, cat in [(list_start, "start"), (list_plan, "plan"), (list_ns, "ns")]:
    for code, _, _, _ in lst:
        all_checklists_codes.append(f"{code}_{cat}")

if "nw_status" not in st.session_state:
    st.session_state.nw_status = {key: False for key in all_checklists_codes}
else:
    for key in all_checklists_codes:
        if key not in st.session_state.nw_status:
            st.session_state.nw_status[key] = False

# 強制更新 SOP 內容 (讓參數計算生效)
st.session_state.sop_data = get_current_sop_data()
data = st.session_state.sop_data

# --- 7. Callback 函數 (修復解鎖問題) ---
def toggle_status(stage_key, index):
    pass # 直接由 checkbox 控制

def toggle_nw(key):
    st.session_state.nw_status[key] = not st.session_state.nw_status[key]

# --- 8. 渲染函數 ---
def render_stage_detailed(stage_key, is_locked=False):
    stage_items = data[stage_key]
    if is_locked: 
        st.markdown('<div class="locked-stage">🔒 請先完成上一階段</div>', unsafe_allow_html=True)
    
    for i, item in enumerate(stage_items):
        if item.get("demo_only") and not is_demo_project: continue
        if item.get("demo_only") and item.get("critical") == "" and not is_demo_review_needed: continue
        if item.get("struct_only") and not is_struct_review_needed: continue

        with st.container():
            col1, col2 = st.columns([0.5, 9.5])
            chk_key = f"chk_{generate_key(stage_key, item['item'])}"
            note_key = f"note_{generate_key(stage_key, item['item'])}"
            
            with col1:
                # [關鍵] 狀態改變觸發 Rerun，確保解鎖
                if st.checkbox("", value=item['done'], key=chk_key, disabled=is_locked):
                    if not item['done']:
                        item['done'] = True
                        st.rerun()
                else:
                    if item['done']:
                        item['done'] = False
                        st.rerun()

            with col2:
                method = item.get('method', '現場')
                method_tag = f'<span class="tag-online">🔵 線上</span>' if method == "線上" else f'<span class="tag-paper">🟤 {method}</span>'
                demo_tag = '<span class="tag-demo">🏗️ 拆除</span>' if item.get("demo_only") else ""
                
                title_html = f"**{item['item']}** {method_tag} {demo_tag} <span style='color:#666; font-size:0.9em'>(🏢 {item['dept']})</span>"
                if item['done']: 
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

def render_checklist(checklist_data, title, tab_name):
    with st.expander(f"📑 {title} (點擊展開)", expanded=False):
        st.markdown(f'<div class="nw-header">請確認 PDF 檔案已備齊並完成用印/掃描：</div>', unsafe_allow_html=True)
        for code, name, note, demo_only in checklist_data:
            if demo_only and not is_demo_project: continue
            c1, c2, c3 = st.columns([0.5, 4, 5.5])
            
            # 使用唯一 key (code + tab_name)
            unique_id = f"{code}_{tab_name}"
            is_checked = st.session_state.nw_status.get(unique_id, False)
            
            # Checkbox
            new_checked = st.checkbox("", value=is_checked, key=f"chk_{unique_id}")
            if new_checked != is_checked:
                st.session_state.nw_status[unique_id] = new_checked
                st.rerun()

            with c2: 
                style = "color:#2E7D32; font-weight:bold;" if is_checked else ""
                st.markdown(f"<span style='{style}'>{code} {name}</span>", unsafe_allow_html=True)
            with c3: st.caption(f"🖊️ {note}")

# --- 9. 主流程 ---
def check_stage_complete(stage_key):
    data = get_current_sop_data()
    items = data[stage_key]
    for item in items:
        if item.get("demo_only") and not is_demo_project: continue
        if item.get("demo_only") and item.get("critical") == "" and not is_demo_review_needed: continue
        if item.get("struct_only") and not is_struct_review_needed: continue
        
        # 檢查 session_state 中的狀態
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
        render_checklist(list_start, "NW 開工文件準備檢查表", "start")
        st.markdown("---")
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
        render_checklist(list_ns, "NS 放樣勘驗文件準備檢查表", "ns")
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
            if item.get("demo_only") and not is_demo_project: continue
            
            key = f"chk_{generate_key(k, item['item'])}"
            item['done'] = st.session_state.get(key, False)
            item['note'] = st.session_state.get(f"note_{generate_key(k, item['item'])}", "")
            
            item_copy = item.copy()
            item_copy['階段代號'] = k
            all_rows.append(item_copy)
    
    if all_rows:
        pd.DataFrame(all_rows).to_excel(writer, index=False, sheet_name='SOP流程')
    
    # Checklist 匯出
    check_rows = []
    for lst, cat in [(list_start, "start"), (list_plan, "plan"), (list_ns, "ns")]:
        for code, name, note, demo_only in lst:
            if demo_only and not is_demo_project: continue
            status = "完成" if st.session_state.nw_status.get(f"{code}_{cat}", False) else "未完成"
            check_rows.append({"階段": cat, "編號": code, "名稱": name, "備註": note, "狀態": status})
            
    if check_rows:
        pd.DataFrame(check_rows).to_excel(writer, index=False, sheet_name='文件檢查表')

st.download_button("📥 下載完整 Excel", buffer.getvalue(), f"SOP_Full_V{CURRENT_VERSION}_{date.today()}.xlsx", "application/vnd.ms-excel")