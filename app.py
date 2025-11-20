import streamlit as st
import requests
import pandas as pd

# -----------------------------------------------------------------------------
# CẤU HÌNH TRANG STREAMLIT
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Phân Tích XSMB - Cầu Tô Đỏ",
    page_icon="🎲",
    layout="wide"
)

# CSS tùy chỉnh để làm đẹp bảng
st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    .highlight-row {background-color: #d4edda !important;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH VÀ ĐỊNH NGHĨA CẤU TRÚC XSMB
# -----------------------------------------------------------------------------
API_URL = "https://www.kqxs88.live/api/front/open/lottery/history/list/game?limitNum=5&gameCode=miba"

XSMB_STRUCTURE = [
    ("G1", 1, 5), ("G2", 2, 5), ("G3", 6, 5),
    ("G4", 4, 4), ("G5", 6, 4), ("G6", 3, 3), ("G7", 4, 2)
]

# -----------------------------------------------------------------------------
# 2. HÀM XỬ LÝ LOGIC (Back-end)
# -----------------------------------------------------------------------------

@st.cache_data(ttl=600) # Cache dữ liệu trong 10 phút để tránh gọi API quá nhiều
def fetch_lottery_data():
    """Gọi API lấy dữ liệu xổ số"""
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list): return data
        elif 'data' in data:
             if isinstance(data['data'], list): return data['data']
             elif 'list' in data['data']: return data['data']['list']
        return data
    except Exception as e:
        st.error(f"Lỗi kết nối API: {e}")
        return []

def create_position_map():
    """Tạo danh sách mapping 102 vị trí"""
    mapping = []
    for prize_name, count, length in XSMB_STRUCTURE:
        for c in range(1, count + 1):
            for l in range(1, length + 1):
                mapping.append(f"{prize_name}.{c}.{l}")
    return mapping

def analyze_day(record, position_map):
    """Phân tích dữ liệu một ngày"""
    result_string = record.get('resultString', '')
    issue = record.get('issue', 'Unknown')
    open_time = record.get('openTime', 'N/A')

    if len(result_string) != 107:
        return None

    special_prize_full = result_string[0:5]
    target_tail = special_prize_full[3:5] # 2 số cuối (GĐB 4-5)
    body_string = result_string[5:] # 102 ký tự Body

    # Tìm cặp
    valid_pairs = []
    for i in range(len(body_string)):
        for j in range(len(body_string)):
            if i == j: continue
            if body_string[i] + body_string[j] == target_tail:
                valid_pairs.append((i, j))

    return {
        "issue": issue,
        "date": open_time,
        "gdb": special_prize_full,
        "target": target_tail,
        "body": body_string,
        "pairs": valid_pairs,
        "pair_set": set(valid_pairs)
    }

# -----------------------------------------------------------------------------
# 3. HÀM HIỂN THỊ GIAO DIỆN (Front-end)
# -----------------------------------------------------------------------------

def display_day_analysis(day_data, pos_map):
    """Hiển thị bảng phân tích cho 1 ngày"""
    st.subheader(f"📅 Kỳ: {day_data['issue']} ({day_data['date']})")
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Giải Đặc Biệt:** {day_data['gdb']}")
    with col2:
        st.warning(f"**Mục tiêu (Body[i] + Body[j]):** {day_data['target']}")

    # Tạo DataFrame hiển thị bảng vị trí
    hit_indices = {idx for pair in day_data['pairs'] for idx in pair}
    
    table_data = []
    body = day_data['body']
    
    for i in range(102):
        is_hit = "✔" if i in hit_indices else ""
        table_data.append({
            "Index": i,
            "Vị trí": pos_map[i],
            "Giá trị": body[i],
            "Trúng?": is_hit
        })
    
    df = pd.DataFrame(table_data)

    # Chia bảng thành 2 cột để dễ nhìn (0-50 và 51-101)
    c1, c2 = st.columns(2)
    with c1:
        st.text("Bảng Vị Trí (0 - 50)")
        st.dataframe(df.iloc[0:51], use_container_width=True, hide_index=True)
    with c2:
        st.text("Bảng Vị Trí (51 - 101)")
        st.dataframe(df.iloc[51:], use_container_width=True, hide_index=True)

    # Hiển thị danh sách cặp
    with st.expander(f"Xem chi tiết {len(day_data['pairs'])} cặp vị trí tạo nên {day_data['target']}"):
        if day_data['pairs']:
            pair_list = []
            for i, j in day_data['pairs']:
                pair_list.append(f"Index ({i}, {j}) | {pos_map[i]} + {pos_map[j]}")
            st.write(pair_list)
        else:
            st.write("Không có cặp nào.")

# -----------------------------------------------------------------------------
# 4. MAIN APP
# -----------------------------------------------------------------------------
def main():
    st.title("📊 XSMB: Phân Tích Cầu Tô Đỏ")
    st.markdown("Hệ thống tự động phân tích API, mapping vị trí và tìm giao thoa giữa 2 ngày.")

    # Nút tải dữ liệu
    if st.button("🚀 Tải dữ liệu mới nhất & Phân tích"):
        with st.spinner("Đang gọi API và xử lý..."):
            raw_data = fetch_lottery_data()
            pos_map = create_position_map()

            if not raw_data or len(raw_data) < 2:
                st.error("Không lấy được đủ dữ liệu từ API.")
                return

            # Lấy 2 ngày gần nhất
            day1 = analyze_day(raw_data[0], pos_map)
            day2 = analyze_day(raw_data[1], pos_map)

            if not day1 or not day2:
                st.error("Dữ liệu trả về bị lỗi cấu trúc.")
                return

            # TẠO TAB
            tab1, tab2, tab3 = st.tabs(["Ngày 1 (Mới nhất)", "Ngày 2 (Hôm trước)", "🔥 KẾT QUẢ TÔ ĐỎ"])

            with tab1:
                display_day_analysis(day1, pos_map)

            with tab2:
                display_day_analysis(day2, pos_map)

            with tab3:
                st.header("🔥 CÁC CẶP VỊ TRÍ TÔ ĐỎ (TRÙNG NHAU)")
                st.markdown(f"""
                - Ngày 1 Target: **{day1['target']}**
                - Ngày 2 Target: **{day2['target']}**
                - Quy tắc: Tìm cặp vị trí `(i, j)` sao cho đúng ở cả hai ngày.
                """)
                
                red_pairs = day1['pair_set'].intersection(day2['pair_set'])
                
                if red_pairs:
                    st.success(f"Tìm thấy {len(red_pairs)} cặp cầu chạy thông!")
                    
                    res_data = []
                    for (i, j) in red_pairs:
                        res_data.append({
                            "Cặp Index": f"({i}, {j})",
                            "Tên Vị Trí": f"{pos_map[i]} + {pos_map[j]}",
                            "Giá trị N1": int(day1['body'][i] + day1['body'][j]),
                            "Giá trị N2": int(day2['body'][i] + day2['body'][j])
                        })
                    
                    st.table(pd.DataFrame(res_data))
                else:
                    st.warning("KHÔNG TÌM THẤY CẶP TÔ ĐỎ NÀO (Cầu gãy).")

if __name__ == "__main__":
    main()
