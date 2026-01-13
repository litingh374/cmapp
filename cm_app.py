import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta

# --- 1. 網頁設定 ---
st.set_page_config(page_title="建管流程時間軸", page_icon="📅", layout="wide")

st.title("📅 建管作業流程時間軸 (Gantt Chart)")
st.markdown("請在下方表格**新增事項**與**日期**，系統將自動生成時間軸圖表。")

# --- 2. 定義資料結構 (一開始是空白的) ---
# 我們定義好欄位名稱，但裡面不放資料
if "tasks_df" not in st.session_state:
    st.session_state.tasks_df = pd.DataFrame(
        columns=["事項名稱", "開始日期", "結束日期", "作業階段", "進度(%)"]
    )

# --- 3. 資料輸入區 (可編輯表格) ---
with st.expander("📝 編輯流程與日期 (點擊展開/收合)", expanded=True):
    st.caption("💡 操作提示：點擊下方表格的最後一列 `+` 號可新增項目。日期請點兩下選擇。")
    
    # 設定欄位的格式 (Config)
    column_config = {
        "事項名稱": st.column_config.TextColumn(
            "作業項目", 
            help="例如：建照掛號、環保局空污費繳納...",
            required=True
        ),
        "開始日期": st.column_config.DateColumn(
            "開始日期",
            format="YYYY-MM-DD",
            required=True
        ),
        "結束日期": st.column_config.DateColumn(
            "結束日期",
            format="YYYY-MM-DD",
            required=True
        ),
        "作業階段": st.column_config.SelectboxColumn(
            "分類泳道",
            # 這裡依據您的圖片設定了三個主要分類
            options=[
                "1.建築師設計審查", 
                "2.建管作業流程 (黃色)", 
                "3.工地現場執行 (綠色)"
            ],
            required=True
        ),
        "進度(%)": st.column_config.NumberColumn(
            "完成度",
            min_value=0,
            max_value=100,
            step=10,
            format="%d %%"
        )
    }

    # 顯示可編輯表格
    edited_df = st.data_editor(
        st.session_state.tasks_df,
        column_config=column_config,
        num_rows="dynamic", # 允許使用者動態新增/刪除列
        use_container_width=True,
        hide_index=True,
        key="editor" # 給個 key 讓 streamlit 追蹤狀態
    )

# --- 4. 圖表生成區 ---
st.divider()
st.subheader("📊 專案時程視覺化")

# 檢查使用者是否有輸入資料
if not edited_df.empty:
    # 資料前處理：確保日期格式正確，並移除沒填日期的髒資料
    plot_df = edited_df.dropna(subset=["開始日期", "結束日期", "事項名稱"])
    
    if len(plot_df) > 0:
        # 計算工期天數 (顯示在圖表提示上)
        plot_df["工期"] = (pd.to_datetime(plot_df["結束日期"]) - pd.to_datetime(plot_df["開始日期"])).dt.days
        
        # 使用 Plotly 繪製甘特圖
        fig = px.timeline(
            plot_df, 
            x_start="開始日期", 
            x_end="結束日期", 
            y="事項名稱", 
            color="作業階段", # 不同階段顯示不同顏色
            hover_data=["工期", "進度(%)"], # 滑鼠移上去顯示的資訊
            title="建管行政與施工進度表",
            # 設定顏色對應 (模擬您圖片的色系)
            color_discrete_map={
                "1.建築師設計審查": "#FFA500", # 橘色
                "2.建管作業流程 (黃色)": "#FFD700", # 金黃色
                "3.工地現場執行 (綠色)": "#90EE90"  # 淺綠色
            }
        )

        # 圖表美化設定
        fig.update_yaxes(autorange="reversed") # 讓最早的項目排在最上面(或依表格順序)
        fig.update_layout(
            xaxis_title="日期",
            yaxis_title="作業項目",
            height=400 + (len(plot_df) * 30), # 自動調整高度，項目越多圖越高
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("ℹ️ 請在上方表格填寫完整的「名稱」與「起訖日期」才會顯示圖表。")
else:
    st.info("👆 目前表格是空白的，請開始新增您的第一筆建管作業資料！")

# --- 5. 存檔功能提示 ---
st.write("---")
# 下載按鈕 (簡單的 CSV 匯出)
if not edited_df.empty:
    csv = edited_df.to_csv(index=False).encode('utf-8-sig') # utf-8-sig 避免 Excel 中文亂碼
    st.download_button(
        label="📥 下載進度表 (CSV)",
        data=csv,
        file_name='construction_schedule.csv',
        mime='text/csv',
    )