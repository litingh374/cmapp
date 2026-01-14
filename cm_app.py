import streamlit as st
import pandas as pd
import io
from datetime import date

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="建案行政SOP控管系統(內建指引版)",
    page_icon="🏗️",
    layout="wide"
)

# --- CSS 優化 ---
st.markdown("""
<style>
    .stProgress > div > div > div > div { background-color: #2E7D32; }
    .locked-stage { 
        padding: 15px; border-radius: 5px; background-color: #ffebee; 
        border: 1px solid #ffcdd2; color: #c62828; font-weight: bold; 
    }
    .info-box {
        background-color: #e3f2fd; padding: 10px; border-radius: 5px; border-left: 5px solid #2196f3;
        font-size: 0.9em; margin-bottom: 10px;
    }
    .warning-box {
        background-color: #fff3e0; padding: 10px; border-radius: 5px; border-left: 5px solid #ff9800;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)

st.title("🏗️ 建案開工至放樣 SOP 系統 (內建作業指引)")
st.markdown("### 特色：整合「辦理期限」、「承辦單位」與「注意事項」於單一介面")

# --- 2. 核心資料庫 (整合您的文件資訊) ---
def get_detailed_sop():
    return {
        "stage_0": [
            {
                "item": "建築師-建照執照領取",
                "dept": "建築師事務所",
                "timing": "【專案啟動】",
                "docs": "1. 建造執照正本\n2. 核准圖說",
                "details": "這是所有流程的起點。需確認建照號碼、起造人名稱無誤。取得建照後，方可進行後續空汙、廢棄物申報。",
                "done": False,
                "note": ""
            }
        ],
        "stage_1": [ # 對應：開工前置準備
            {
                "item": "空氣污染防制費 (首期) 申報",
                "dept": "環保局 (空噪科)",
                "timing": "【開工前】需完成申報並繳納",
                "docs": "1. 空汙費申報書\n2. 建照影本\n3. 工程合約書 (計算費率用)\n4. 營造業登記證",
                "details": "⚠️ 限制：未繳納空汙費者，環保局不予核定廢棄物處置計畫，亦無法申報開工。\n💡 費率依工期長短與工程類別計算。",
                "done": False,
                "note": ""
            },
            {
                "item": "營建工程廢棄物處理計畫書",
                "dept": "環保局 / 工務局",
                "timing": "【開工前】需取得核定函",
                "docs": "1. 廢棄物處置計畫書 (含計算書)\n2. 土資場收容同意書\n3. 清運合約書",
                "details": "⚠️ 限制：需先確認收容場所(土資場)有剩餘容量。計畫書需經核定後始得運土。",
                "done": False,
                "note": ""
            },
            {
                "item": "逕流廢水削減計畫",
                "dept": "環保局 (水保科)",
                "timing": "【開工前】需提送並核定",
                "docs": "1. 削減計畫書\n2. 沉沙池設置圖說",
                "details": "💡 重點：需規劃工區內的臨時排水路徑與沉沙池位置，避免泥水外流。",
                "done": False,
                "note": ""
            },
            {
                "item": "現況調查 (鄰房鑑定申請)",
                "dept": "建築師公會 / 土木技師公會",
                "timing": "【開工前 / 拆除前】",
                "docs": "1. 鑑定申請書\n2. 繳費證明\n3. 鄰房清冊",
                "details": "⚠️ 極重要：務必於「實際動工(或拆除)」前完成現況鑑定報告，作為日後損鄰爭議之依據。若開工後才做，鑑定報告效力會受質疑。",
                "done": False,
                "note": ""
            },
            {
                "item": "五大管線查詢",
                "dept": "台電、自來水、瓦斯、電信、汙水",
                "timing": "【規劃階段 / 開工前】",
                "docs": "1. 現況圖\n2. 建照地號清單",
                "details": "需確認基地內有無舊有管線需遷移，或基地外管線是否影響連續壁施工。",
                "done": False,
                "note": ""
            },
            {
                "item": "建管開工申報 (正式掛號)",
                "dept": "建管處 (施工科)",
                "timing": "【取得建照後 6 個月內】",
                "docs": "1. 開工申請書\n2. 承造/監造人證書\n3. 營造業公會會員證\n4. 營造綜合保險單\n5. 上述環保核定函",
                "details": "⚠️ 法規死線：建照發照後 6 個月內需開工 (可展延一次 3 個月)，逾期建照作廢。",
                "done": False,
                "note": ""
            }
        ],
        "stage_2": [ # 對應：施工計畫
            {
                "item": "施工計畫書 (含交通維持/防災)",
                "dept": "建管處 / 外審委員會",
                "timing": "【放樣勘驗前】需核定",
                "docs": "1. 施工計畫書 (多份)\n2. 簡報資料",
                "details": "⚠️ 特別限制：若位於山坡地或開挖深度超過規定(如地下室三層)，需進行「特殊結構外審」或「施工計畫外審」。\n💡 需召開施工前說明會 (里民說明會)。",
                "done": False,
                "note": ""
            },
            {
                "item": "職業安全衛生管理計畫",
                "dept": "勞動檢查處",
                "timing": "【開工前】",
                "docs": "1. 安衛計畫書\n2. 安衛人員證照\n3. 協議組織運作紀錄",
                "details": "依工程規模區分：危險性工作場所需丁類審查(丁審)。",
                "done": False,
                "note": ""
            }
        ],
        "stage_3": [ # 對應：導溝勘驗
            {
                "item": "導溝施工與單元劃分",
                "dept": "工地現場",
                "timing": "【連續壁施作前】",
                "docs": "1. 單元分割圖\n2. 自主檢查表",
                "details": "確認導溝位置是否正確，鋪面是否完成，作為連續壁挖掘之基準。",
                "done": False,
                "note": ""
            },
            {
                "item": "導溝勘驗申報",
                "dept": "建管處 / 勘驗公會",
                "timing": "【施工計畫核定後】",
                "docs": "1. 勘驗申請書\n2. 現場施工照片\n3. 監造建築師簽證",
                "details": "⚠️ 限制：需在施工計畫核定後，且相關防護設施(圍籬)完成後始得申報。",
                "done": False,
                "note": ""
            }
        ],
        "stage_4": [ # 對應：放樣勘驗
            {
                "item": "基地鑑界 (複丈)",
                "dept": "地政事務所",
                "timing": "【放樣前】",
                "docs": "1. 土地複丈申請書",
                "details": "⚠️ 務必確認：建築線指示圖與地政鑑界點位是否一致。若有差異需申請更正。",
                "done": False,
                "note": ""
            },
            {
                "item": "放樣勘驗申報",
                "dept": "建管處",
                "timing": "【一樓版灌漿前 / 基礎開挖前】",
                "docs": "1. 放樣勘驗報告書\n2. 測量成果圖\n3. 建築線指示圖核對",
                "details": "這是最重要的勘驗點。確認建築物座落位置、高程完全符合建照圖說。\n💡 完成此項後，才算是正式進入結構體施工階段。",
                "done": False,
                "note": ""
            }
        ]
    }

# 初始化資料
if "sop_data" not in st.session_state:
    st.session_state.sop_data = get_detailed_sop()

data = st.session_state.sop_data

# --- 3. 側邊欄 ---
with st.sidebar:
    st.header("📝 專案資訊")
    st.text_input("專案名稱", value="台北市中正區建案")
    
    # 全域狀態檢查
    permit_done = all(item['done'] for item in data['stage_0'])
    
    if permit_done:
        st.success("✅ 建照已領取")
    else:
        st.error("⛔ 建照尚未領取")

    if st.button("🔄 重置系統"):
        st.session_state.sop_data = get_detailed_sop()
        st.rerun()

# --- 4. 渲染函數 (含詳細摺疊選單) ---
def render_stage_detailed(stage_key, is_locked=False):
    stage_items = data[stage_key]
    
    if is_locked:
        st.markdown(f'<div class="locked-stage">⚠️ 此階段鎖定中：請先完成上一階段作業。</div>', unsafe_allow_html=True)

    for i, item in enumerate(stage_items):
        # 外框 Container
        with st.container():
            col1, col2 = st.columns([0.5, 9.5])
            
            # Checkbox
            with col1:
                checked = st.checkbox(
                    "", 
                    value=item['done'], 
                    key=f"{stage_key}_{i}", 
                    disabled=is_locked
                )
                data[stage_key][i]['done'] = checked
            
            # 內容區 (使用 Expander 摺疊詳細資訊)
            with col2:
                # 標題列：顯示項目名稱 + 承辦單位 (讓使用者一眼看到重點)
                title_text = f"**{item['item']}** All_right_{item['dept']}"
                if item['done']:
                    title_text = "✅ " + title_text
                
                with st.expander(title_text, expanded=False):
                    # 這裡就是您要的「詳細資訊」
                    st.markdown(f"<div class='info-box'><b>🕒 辦理期限/時機：</b>{item['timing']}</div>", unsafe_allow_html=True)
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**📄 應備文件：**")
                        st.text(item['docs']) # 使用 text 保持換行格式
                    with c2:
                        if item['details']:
                            st.markdown(f"<div class='warning-box'><b>⚠️ 注意事項/限制：</b><br>{item['details']}</div>", unsafe_allow_html=True)
                    
                    # 備註欄
                    data[stage_key][i]['note'] = st.text_input(
                        "我的筆記/追蹤單號", 
                        value=item['note'], 
                        key=f"note_{stage_key}_{i}",
                        placeholder="在此輸入公文文號或聯絡人...",
                        disabled=is_locked
                    )
        st.divider()

# --- 5. 主流程顯示 ---
# 進度條
current_stage = 0
total_stages = 5
if permit_done: current_stage += 1
if permit_done and all(i['done'] for i in data['stage_1']): current_stage += 1
if current_stage >= 2 and all(i['done'] for i in data['stage_2']): current_stage += 1
if current_stage >= 3 and all(i['done'] for i in data['stage_3']): current_stage += 1

st.progress(current_stage/total_stages, text=f"專案進度：Step {current_stage}")

# Tabs
tab0, tab1, tab2, tab3, tab4 = st.tabs([
    "0.建照領取", "1.開工申報準備", "2.施工計畫", "3.導溝勘驗", "4.放樣勘驗"
])

with tab0:
    st.subheader("🔑 階段零：建照領取")
    render_stage_detailed("stage_0")

with tab1:
    st.subheader("📋 階段一：開工申報準備 (含環保/現況)")
    is_locked = not permit_done
    render_stage_detailed("stage_1", is_locked)

with tab2:
    st.subheader("📘 階段二：施工計畫與勞安")
    is_locked = not (permit_done and all(i['done'] for i in data['stage_1']))
    # 註：這裡設定為必須完成「開工申報準備」才能跑計畫，若需彈性可調整
    render_stage_detailed("stage_2", is_locked)

with tab3:
    st.subheader("🚧 階段三：導溝勘驗")
    is_locked = not (all(i['done'] for i in data['stage_2']))
    render_stage_detailed("stage_3", is_locked)

with tab4:
    st.subheader("📐 階段四：放樣勘驗")
    is_locked = not (all(i['done'] for i in data['stage_3']))
    render_stage_detailed("stage_4", is_locked)

# --- 6. 匯出完整 Excel ---
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
    # 重新排列欄位順序
    cols = ["階段代號", "item", "dept", "timing", "docs", "details", "done", "note"]
    df_export = df_export[cols]
    df_export.columns = ["階段", "作業項目", "承辦單位", "辦理時限", "應備文件", "注意事項", "完成狀態", "筆記"]
    
    df_export.to_excel(writer, index=False, sheet_name='SOP詳表')
    
    # 調整 Excel 格式 (讓文字自動換行，方便閱讀)
    workbook = writer.book
    worksheet = writer.sheets['SOP詳表']
    wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})
    
    worksheet.set_column('B:B', 25, wrap_format) # 項目
    worksheet.set_column('C:C', 15, wrap_format) # 單位
    worksheet.set_column('E:E', 40, wrap_format) # 文件
    worksheet.set_column('F:F', 40, wrap_format) # 注意事項

st.download_button(
    label="📥 下載完整 SOP Excel (含作業指引)",
    data=buffer.getvalue(),
    file_name=f"建管SOP控管表_{date.today()}.xlsx",
    mime="application/vnd.ms-excel"
)