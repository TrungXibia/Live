import streamlit as st
import requests
import pandas as pd
import json

# -----------------------------------------------------------------------------
# CẤU HÌNH TRANG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Super Soi Cầu XSMB - Bộ Đề & Chạy Thông",
    page_icon="🔥",
    layout="wide"
)

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    div[data-testid="stExpander"] {border: 1px solid #e6e6e6; border-radius: 5px;}
    .success-box {padding: 10px; background-color: #d4edda; color: #155724; border-radius: 5px; margin-bottom: 10px;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH, API & MAPPING
# -----------------------------------------------------------------------------
API_URL = "https://www.kqxs88.live/api/front/open/lottery/history/list/game?limitNum=10&gameCode=miba"

XSMB_STRUCTURE = [
    ("G1", 1, 5), ("G2", 2, 5), ("G3", 6, 5),
    ("G4", 4, 4), ("G5", 6, 4), ("G6", 3, 3), ("G7", 4, 2)
]

# ĐỊNH NGHĨA 15 BỘ ĐỀ CƠ BẢN (Toàn bộ là string)
BO_DE_DICT = {
    "00": ["00", "55", "05", "50"],
    "11": ["11", "66", "16", "61"],
    "22": ["22", "77", "27", "72"],
    "33": ["33", "88", "38", "83"],
    "44": ["44", "99", "49", "94"],
    "01": ["01", "10", "06", "60", "51", "15", "56", "65"],
    "02": ["02", "20", "07", "70", "52", "25", "57", "75"],
    "03": ["03", "30", "08", "80", "53", "35", "58", "85"],
    "04": ["04", "40", "09", "90", "54", "45", "59", "95"],
    "12": ["12", "21", "17", "71", "62", "26", "67", "76"],
    "13": ["13", "31", "18", "81", "63", "36", "68", "86"],
    "14": ["14", "41", "19", "91", "64", "46", "69", "96"],
    "23": ["23", "32", "28", "82", "73", "37", "78", "87"],
    "24": ["24", "42", "29", "92", "74", "47", "79", "97"],
    "34": ["34", "43", "39", "93", "84", "48", "89", "98"]
}

# Tạo bảng tra cứu ngược (Số -> Tên bộ)
NUMBER_TO_SET_MAP = {}
for set_name, numbers in BO_DE_DICT.items():
    for num in numbers:
        NUMBER_TO_SET_MAP[str(num)] = set_name

# -----------------------------------------------------------------------------
# 2. HÀM XỬ LÝ DỮ LIỆU (CORE)
# -----------------------------------------------------------------------------

@st.cache_data(ttl=60)
def fetch_lottery_data():
    """Lấy dữ liệu từ API, xử lý cấu trúc t -> issueList"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(API_URL, headers=headers, timeout=10)
        data = response.json()

        if 't' in data and isinstance(data['t'], dict) and 'issueList' in data['t']:
            return data['t']['issueList']
        return None
    except Exception:
        return None

def parse_detail_to_107_chars(detail_str):
    """Chuyển chuỗi detail JSON thành chuỗi 107 ký tự"""
    try:
        if not detail_str: return ""
        raw_groups = json.loads(detail_str)
        full_str = ""
        for group in raw_groups:
            full_str += group.replace(",", "").strip()
        return full_str
    except:
        return ""

def create_position_map():
    mapping = []
    for prize_name, count, length in XSMB_STRUCTURE:
        for c in range(1, count + 1):
            for l in range(1, length + 1):
                mapping.append(f"{prize_name}.{c}.{l}")
    return mapping

def get_set_name(number_str):
    """Lấy tên bộ đề của một số (Ví dụ: '60' -> '01')"""
    return NUMBER_TO_SET_MAP.get(str(number_str), "Unknown")

def process_days_data(raw_list, num_days):
    """
    Xử lý dữ liệu thô của N ngày.
    """
    processed_days = []
    pos_map = create_position_map()

    # Duyệt qua N ngày (raw_list[0] là mới nhất)
    limit = min(num_days, len(raw_list))
    for i in range(limit):
        record = raw_list[i]
        
        # SỬA LỖI TẠI ĐÂY: Dùng biến full_str thống nhất
        full_str = parse_detail_to_107_chars(record.get('detail', ''))
        
        if len(full_str) != 107:
            continue 
            
        target = full_str[3:5] # GĐB 4-5
        body = full_str[5:]
        
        processed_days.append({
            "index": i, # 0 = Mới nhất
            "issue": record.get('turnNum'),
            "target": target,
            "target_set": get_set_name(target),
            "body": body
        })
        
    return processed_days, pos_map

# -----------------------------------------------------------------------------
# 3. THUẬT TOÁN TÌM CẦU (LOGIC CHÍNH)
# -----------------------------------------------------------------------------

def find_streak_bridges(days_data, mode="straight"):
    """
    Tìm các cặp vị trí chạy thông qua tất cả các ngày.
    """
    if not days_data:
        return []

    # Bước 1: Tìm tất cả các cặp đúng của NGÀY MỚI NHẤT (Day 0)
    candidate_pairs = []
    day0 = days_data[0]
    body = day0['body']
    
    for i in range(len(body)):
        for j in range(len(body)):
            if i == j: continue
            
            pair_val = body[i] + body[j]
            
            is_match = False
            if mode == "straight":
                if pair_val == day0['target']: is_match = True
            else: # mode == "set"
                if get_set_name(pair_val) == day0['target_set']: is_match = True
            
            if is_match:
                candidate_pairs.append((i, j))

    # Bước 2: Duyệt ngược về các ngày quá khứ để lọc
    final_pairs = []
    
    for (i, j) in candidate_pairs:
        streak_ok = True
        
        for k in range(1, len(days_data)):
            day_k = days_data[k]
            body_k = day_k['body']
            pair_val_k = body_k[i] + body_k[j]
            
            if mode == "straight":
                if pair_val_k != day_k['target']:
                    streak_ok = False
                    break
            else: # mode == "set"
                if get_set_name(pair_val_k) != day_k['target_set']:
                    streak_ok = False
                    break
        
        if streak_ok:
            final_pairs.append((i, j))
            
    return final_pairs

# -----------------------------------------------------------------------------
# 4. GIAO DIỆN NGƯỜI DÙNG
# -----------------------------------------------------------------------------

def main():
    st.title("🔥 Super Soi Cầu XSMB: Chạy Thông & Bộ Đề")
    st.markdown("Dữ liệu từ: **kqxs88.live**")
    
    # --- SIDEBAR CẤU HÌNH ---
    with st.sidebar:
        st.header("⚙️ Cấu Hình Soi Cầu")
        
        scan_days = st.slider("Số ngày chạy thông (Streak)", min_value=2, max_value=5, value=2, 
                              help="Tìm cầu đúng liên tiếp trong bao nhiêu ngày gần nhất?")
        
        scan_mode = st.radio("Phương pháp soi", ["Soi Thẳng (Bạch thủ)", "Soi Bộ Đề (Bóng/Hệ)"], index=0)
        
        mode_key = "straight" if "Thẳng" in scan_mode else "set"
        
        st.info("""
        **Giải thích:**
        - **Soi Thẳng:** Tổng 2 vị trí = Chính xác 2 số cuối GĐB.
        - **Soi Bộ Đề:** Tổng 2 vị trí thuộc cùng BỘ với GĐB. (Rộng hơn, dễ tìm cầu dài ngày).
        """)
        
        if st.button("🚀 QUÉT CẦU NGAY", type="primary"):
            st.session_state['run_scan'] = True

    # --- LOGIC HIỂN THỊ ---
    
    # Lấy dữ liệu API
    raw_list = fetch_lottery_data()
    
    if not raw_list:
        st.error("Không kết nối được API hoặc dữ liệu trả về lỗi.")
        return

    # Xử lý dữ liệu đầu vào
    processed_days, pos_map = process_days_data(raw_list, scan_days)
    
    if len(processed_days) < scan_days:
        st.warning(f"Dữ liệu API chỉ có {len(processed_days)} ngày, không đủ để soi {scan_days} ngày.")
        return

    # Hiển thị thông tin các ngày được soi
    st.subheader(f"📅 Dữ liệu {scan_days} ngày gần nhất được dùng để soi")
    cols = st.columns(scan_days)
    for idx, day in enumerate(processed_days):
        with cols[idx]:
            st.markdown(f"**{day['issue']}**")
            st.code(f"GĐB: ...{day['target']}", language="text")
            if mode_key == "set":
                set_name = day['target_set']
                if set_name != "Unknown":
                    st.caption(f"Thuộc Bộ: {set_name}")
                else:
                    st.caption("Không thuộc bộ nào")

    # Chỉ chạy khi bấm nút
    if st.session_state.get('run_scan'):
        with st.spinner(f"Đang quét hàng ngàn cặp vị trí..."):
            
            # GỌI HÀM TÌM CẦU
            winning_pairs = find_streak_bridges(processed_days, mode=mode_key)
            
            st.divider()
            st.header(f"💎 KẾT QUẢ: Tìm thấy {len(winning_pairs)} cầu chạy thông {scan_days} ngày")
            
            if winning_pairs:
                # Tạo bảng kết quả chi tiết
                results_data = []
                for (i, j) in winning_pairs:
                    row = {
                        "Vị trí 1": f"{pos_map[i]}",
                        "Vị trí 2": f"{pos_map[j]}",
                    }
                    
                    # Thêm cột giá trị cho từng ngày
                    for day in processed_days:
                        val = day['body'][i] + day['body'][j]
                        if mode_key == "set":
                            # Nếu soi bộ, hiển thị: "85 (Bộ 03)"
                            val_display = f"{val} ({get_set_name(val)})"
                        else:
                            val_display = val
                            
                        row[f"Ngày {day['issue']}"] = val_display
                        
                    results_data.append(row)
                
                # Hiển thị bảng
                st.dataframe(pd.DataFrame(results_data), use_container_width=True)
                
                st.success("✅ Các vị trí trên đều cho kết quả đúng (hoặc cùng bộ) liên tiếp các ngày qua.")
            else:
                st.warning(f"Không tìm thấy cầu nào thỏa mãn điều kiện chạy thông {scan_days} ngày. Hãy thử giảm số ngày hoặc chuyển sang chế độ 'Soi Bộ Đề'.")

    # --- PHẦN TRA CỨU BỘ ĐỀ (PHỤ TRỢ) ---
    with st.expander("📖 Tra cứu nhanh các Bộ Đề"):
        col_a, col_b, col_c = st.columns(3)
        sets = list(BO_DE_DICT.items())
        chunk_size = (len(sets) // 3) + 1
        
        for i, col in enumerate([col_a, col_b, col_c]):
            sub_sets = sets[i*chunk_size : (i+1)*chunk_size]
            with col:
                for name, nums in sub_sets:
                    st.text(f"Bộ {name}: {', '.join(map(str, nums))}")

if __name__ == "__main__":
    main()
