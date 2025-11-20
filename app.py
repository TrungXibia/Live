import streamlit as st
import requests
import pandas as pd
import json

# -----------------------------------------------------------------------------
# CẤU HÌNH TRANG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Soi Cầu XSMB - KQXS88 Live",
    page_icon="🎲",
    layout="wide"
)

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    div[data-testid="stExpander"] {border: 1px solid #e6e6e6; border-radius: 5px;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH & MAPPING
# -----------------------------------------------------------------------------
API_URL = "https://www.kqxs88.live/api/front/open/lottery/history/list/game?limitNum=5&gameCode=miba"

# Cấu trúc chuẩn XSMB (Tổng 27 giải - 107 ký tự)
XSMB_STRUCTURE = [
    ("G1", 1, 5), ("G2", 2, 5), ("G3", 6, 5),
    ("G4", 4, 4), ("G5", 6, 4), ("G6", 3, 3), ("G7", 4, 2)
]

# -----------------------------------------------------------------------------
# 2. HÀM XỬ LÝ DỮ LIỆU (CORE)
# -----------------------------------------------------------------------------

@st.cache_data(ttl=60)
def fetch_lottery_data():
    """
    Gọi API và lấy list từ đường dẫn: root -> t -> issueList
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(API_URL, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        # --- ĐI THẲNG VÀO CẤU TRÚC JSON CỦA KQXS88 ---
        if 't' in data and isinstance(data['t'], dict):
            if 'issueList' in data['t'] and isinstance(data['t']['issueList'], list):
                return data['t']['issueList']

        st.error(f"Cấu trúc API thay đổi. Không tìm thấy 't' -> 'issueList'. Keys: {list(data.keys())}")
        return None

    except Exception as e:
        st.error(f"Lỗi kết nối API: {e}")
        return None

def parse_detail_to_107_chars(detail_str):
    """
    Chuyển chuỗi detail phức tạp thành chuỗi 107 ký tự liền mạch.
    Input mẫu: '["46433","89650","21573,12383", ...]'
    """
    try:
        if not detail_str: return ""
        
        # 1. Parse chuỗi JSON string thành List Python
        # Kết quả: ['46433', '89650', '21573,12383', ...]
        raw_groups = json.loads(detail_str)
        
        full_str = ""
        for group in raw_groups:
            # 2. Xóa dấu phẩy bên trong từng nhóm giải (Ví dụ giải 3: "21573,12383" -> "2157312383")
            clean_group = group.replace(",", "").strip()
            full_str += clean_group
            
        return full_str
    except Exception as e:
        # st.error(f"Lỗi parse detail: {e}")
        return ""

def create_position_map():
    mapping = []
    for prize_name, count, length in XSMB_STRUCTURE:
        for c in range(1, count + 1):
            for l in range(1, length + 1):
                mapping.append(f"{prize_name}.{c}.{l}")
    return mapping

def analyze_day(record, position_map):
    """Phân tích 1 ngày xổ số"""
    if not isinstance(record, dict):
        return None
    
    # Lấy thông tin cơ bản
    issue = record.get('turnNum', 'Unknown') # Ví dụ: "20/11/2025"
    detail_raw = record.get('detail', '')

    # --- QUAN TRỌNG: Xử lý chuỗi detail ---
    full_107_str = parse_detail_to_107_chars(detail_raw)
    
    # Kiểm tra độ dài chuẩn XSMB (107 ký tự)
    if len(full_107_str) != 107:
        # Nếu không đủ 107 ký tự, bỏ qua (có thể dữ liệu lỗi hoặc chưa quay xong)
        return None

    # Cắt chuỗi theo yêu cầu
    special_prize_full = full_107_str[0:5]     # GĐB (5 ký tự đầu)
    target_tail = special_prize_full[3:5]      # 2 số cuối GĐB (4-5) - MỤC TIÊU
    body_string = full_107_str[5:]             # 102 ký tự còn lại (G1 -> G7)

    # Thuật toán tìm cặp: Body[i] + Body[j] == Target
    valid_pairs = []
    for i in range(len(body_string)):
        for j in range(len(body_string)):
            if i == j: continue
            # So sánh chuỗi ghép
            if body_string[i] + body_string[j] == target_tail:
                valid_pairs.append((i, j))

    return {
        "issue": issue,
        "gdb": special_prize_full,
        "target": target_tail,
        "body": body_string,
        "pairs": valid_pairs,
        "pair_set": set(valid_pairs)
    }

# -----------------------------------------------------------------------------
# 3. GIAO DIỆN NGƯỜI DÙNG (STREAMLIT UI)
# -----------------------------------------------------------------------------

def display_day_analysis(day_data, pos_map, label):
    if not day_data:
        st.warning(f"{label}: Dữ liệu ngày này bị lỗi hoặc chưa có kết quả.")
        return

    st.subheader(f"{label} - Ngày: {day_data['issue']}")
    
    col1, col2 = st.columns(2)
    col1.info(f"Đặc Biệt: {day_data['gdb']}")
    col2.error(f"Mục Tiêu (Tâm Càng): {day_data['target']}")

    # Hiển thị bảng vị trí
    hit_indices = {idx for pair in day_data['pairs'] for idx in pair}
    table_data = []
    body = day_data['body']
    
    for i in range(102):
        is_hit = "✔" if i in hit_indices else ""
        table_data.append({
            "Index": i,
            "Vị trí": pos_map[i],
            "Số": body[i],
            "Trúng": is_hit
        })
    
    df = pd.DataFrame(table_data)
    
    # Chia 2 cột hiển thị bảng
    c1, c2 = st.columns(2)
    with c1:
        st.dataframe(df.iloc[0:51], use_container_width=True, hide_index=True, height=300)
    with c2:
        st.dataframe(df.iloc[51:], use_container_width=True, hide_index=True, height=300)

    # Expander xem danh sách cặp
    with st.expander(f"Chi tiết {len(day_data['pairs'])} cặp tạo nên {day_data['target']}"):
        if day_data['pairs']:
            # Format chuỗi hiển thị cho gọn
            text_lines = [f"({i}, {j}) : {pos_map[i]} + {pos_map[j]}" for i, j in day_data['pairs']]
            st.text("\n".join(text_lines))
        else:
            st.text("Không tìm thấy cặp nào.")

def main():
    st.title("🔍 XSMB: Phân Tích Cầu Tô Đỏ (API KQXS88)")
    
    if st.button("🚀 Tải & Phân Tích"):
        with st.spinner("Đang kết nối API & Bóc tách dữ liệu..."):
            # 1. Lấy dữ liệu
            raw_list = fetch_lottery_data()
            pos_map = create_position_map()
            
            if raw_list is None:
                return # Đã báo lỗi trong hàm fetch
            
            if len(raw_list) < 2:
                st.warning("Không đủ 2 ngày dữ liệu để so sánh.")
                return

            # 2. Phân tích 2 ngày gần nhất
            # raw_list[0]: Mới nhất
            # raw_list[1]: Hôm qua
            day1 = analyze_day(raw_list[0], pos_map)
            day2 = analyze_day(raw_list[1], pos_map)

            if not day1 or not day2:
                st.error("Lỗi cấu trúc dữ liệu bên trong (Detail string). Vui lòng kiểm tra log.")
                return

            # 3. Hiển thị Tabs
            tab1, tab2, tab3 = st.tabs(["📅 Mới Nhất", "📅 Hôm Trước", "🔥 CẦU TÔ ĐỎ"])

            with tab1:
                display_day_analysis(day1, pos_map, "Kỳ Mới Nhất")
            
            with tab2:
                display_day_analysis(day2, pos_map, "Kỳ Trước Đó")
            
            with tab3:
                st.header("🔥 KẾT QUẢ SO CẦU (TRÙNG 2 NGÀY)")
                
                # Tìm giao thoa (Intersection)
                red_pairs = day1['pair_set'].intersection(day2['pair_set'])
                
                st.markdown(f"""
                - Mục tiêu Ngày 1 ({day1['issue']}): **{day1['target']}**
                - Mục tiêu Ngày 2 ({day2['issue']}): **{day2['target']}**
                - Số lượng cặp trùng khớp: **{len(red_pairs)}**
                """)
                
                if red_pairs:
                    result_rows = []
                    for (i, j) in red_pairs:
                        val1 = day1['body'][i] + day1['body'][j]
                        val2 = day2['body'][i] + day2['body'][j]
                        
                        result_rows.append({
                            "Cặp Index": f"({i}, {j})",
                            "Tên Vị Trí": f"{pos_map[i]} - {pos_map[j]}",
                            "Giá trị N1": val1,
                            "Giá trị N2": val2
                        })
                    
                    st.table(pd.DataFrame(result_rows))
                else:
                    st.warning("Không tìm thấy cặp nào thông cầu (Cầu gãy).")

if __name__ == "__main__":
    main()
