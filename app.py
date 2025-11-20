import streamlit as st
import requests
import pandas as pd
import json

# -----------------------------------------------------------------------------
# CẤU HÌNH TRANG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Super Soi Cầu XSMB - Đảo & Bộ",
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

# ĐỊNH NGHĨA 15 BỘ ĐỀ
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

NUMBER_TO_SET_MAP = {}
for set_name, numbers in BO_DE_DICT.items():
    for num in numbers:
        NUMBER_TO_SET_MAP[str(num)] = set_name

# -----------------------------------------------------------------------------
# 2. HÀM XỬ LÝ DỮ LIỆU
# -----------------------------------------------------------------------------

@st.cache_data(ttl=60)
def fetch_lottery_data():
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
    return NUMBER_TO_SET_MAP.get(str(number_str), "Unknown")

def process_days_data(raw_list, num_days):
    processed_days = []
    pos_map = create_position_map()
    limit = min(num_days, len(raw_list))
    
    for i in range(limit):
        record = raw_list[i]
        full_str = parse_detail_to_107_chars(record.get('detail', ''))
        
        if len(full_str) != 107: continue 
            
        target = full_str[3:5] # GĐB 4-5
        body = full_str[5:]
        
        processed_days.append({
            "index": i,
            "issue": record.get('turnNum'),
            "target": target,
            "target_rev": target[::-1], # Lưu thêm số đảo
            "target_set": get_set_name(target),
            "body": body
        })
        
    return processed_days, pos_map

# -----------------------------------------------------------------------------
# 3. THUẬT TOÁN TÌM CẦU (UPDATE LOGIC ĐẢO)
# -----------------------------------------------------------------------------

def find_streak_bridges(days_data, mode="straight", allow_reverse=False):
    """
    Tìm cầu chạy thông.
    - allow_reverse: True nếu chấp nhận AB hoặc BA đều đúng (chỉ dùng cho Soi Thẳng).
    """
    if not days_data: return []

    # Bước 1: Lọc cặp ứng viên ở Ngày mới nhất (Day 0)
    candidate_pairs = []
    day0 = days_data[0]
    body = day0['body']
    
    for i in range(len(body)):
        for j in range(len(body)):
            if i == j: continue
            
            val = body[i] + body[j]
            is_match = False
            
            if mode == "straight":
                # Nếu soi thẳng: Đúng tuyệt đối HOẶC Đúng đảo (nếu bật option)
                if val == day0['target']:
                    is_match = True
                elif allow_reverse and val == day0['target_rev']:
                    is_match = True
            else: 
                # Soi bộ
                if get_set_name(val) == day0['target_set']:
                    is_match = True
            
            if is_match:
                candidate_pairs.append((i, j))

    # Bước 2: Kiểm tra ứng viên với các ngày quá khứ
    final_pairs = []
    
    for (i, j) in candidate_pairs:
        streak_ok = True
        
        for k in range(1, len(days_data)):
            day_k = days_data[k]
            body_k = day_k['body']
            val_k = body_k[i] + body_k[j]
            
            if mode == "straight":
                # Logic kiểm tra ngày cũ cũng phải áp dụng allow_reverse
                if allow_reverse:
                    if val_k != day_k['target'] and val_k != day_k['target_rev']:
                        streak_ok = False
                        break
                else:
                    if val_k != day_k['target']:
                        streak_ok = False
                        break
            else: # Soi bộ
                if get_set_name(val_k) != day_k['target_set']:
                    streak_ok = False
                    break
        
        if streak_ok:
            final_pairs.append((i, j))
            
    return final_pairs

# -----------------------------------------------------------------------------
# 4. GIAO DIỆN NGƯỜI DÙNG
# -----------------------------------------------------------------------------

def main():
    st.title("🔥 Soi Cầu XSMB: Thẳng (Đảo) & Bộ Đề")
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Cấu Hình")
        
        scan_days = st.slider("Số ngày chạy thông", 2, 5, 3)
        scan_mode = st.radio("Phương pháp", ["Soi Thẳng (Bạch thủ)", "Soi Bộ Đề (Hệ)"])
        
        mode_key = "straight" if "Thẳng" in scan_mode else "set"
        
        # Tùy chọn riêng cho Soi Thẳng
        allow_rev = False
        if mode_key == "straight":
            st.markdown("---")
            allow_rev = st.checkbox("✅ Chấp nhận đảo (AB-BA)", value=True, 
                                  help="Ví dụ: Cầu ra 54, Đề về 45 -> Vẫn tính là đúng.")
        
        if st.button("🚀 QUÉT CẦU NGAY", type="primary"):
            st.session_state['run_scan'] = True

    # --- MAIN CONTENT ---
    raw_list = fetch_lottery_data()
    if not raw_list:
        st.error("Lỗi API.")
        return

    processed_days, pos_map = process_days_data(raw_list, scan_days)
    
    if len(processed_days) < scan_days:
        st.warning("Không đủ dữ liệu ngày.")
        return

    # Hiển thị KQ các ngày
    st.subheader(f"📅 Kết quả {scan_days} ngày qua")
    cols = st.columns(scan_days)
    for idx, day in enumerate(processed_days):
        with cols[idx]:
            st.markdown(f"**{day['issue']}**")
            st.code(f"Đề: {day['target']}", language="text")
            if mode_key == "set":
                st.caption(f"Bộ: {day['target_set']}")

    if st.session_state.get('run_scan'):
        with st.spinner("Đang tính toán..."):
            
            # Gọi hàm tìm cầu với tham số đảo
            winning_pairs = find_streak_bridges(processed_days, mode=mode_key, allow_reverse=allow_rev)
            
            st.divider()
            st.header(f"💎 TÌM THẤY {len(winning_pairs)} CẦU THÔNG {scan_days} NGÀY")
            
            if winning_pairs:
                results_data = []
                for (i, j) in winning_pairs:
                    row = {
                        "Vị trí 1": f"{pos_map[i]}",
                        "Vị trí 2": f"{pos_map[j]}",
                    }
                    
                    for day in processed_days:
                        val = day['body'][i] + day['body'][j]
                        display_str = val
                        
                        # Logic hiển thị cho đẹp
                        if mode_key == "straight":
                            if val == day['target']:
                                display_str = f"{val} (Thẳng)"
                            elif val == day['target_rev']:
                                display_str = f"{val} (Đảo)"
                        else:
                            display_str = f"{val} (Bộ {get_set_name(val)})"
                            
                        row[f"Ngày {day['issue']}"] = display_str
                        
                    results_data.append(row)
                
                st.dataframe(pd.DataFrame(results_data), use_container_width=True)
            else:
                st.warning("Không tìm thấy cầu nào. Thử giảm số ngày hoặc chuyển chế độ.")

    with st.expander("📖 Tra cứu Bộ Đề"):
        col_a, col_b, col_c = st.columns(3)
        sets = list(BO_DE_DICT.items())
        chunk = (len(sets) // 3) + 1
        for i, col in enumerate([col_a, col_b, col_c]):
            with col:
                for n, nums in sets[i*chunk : (i+1)*chunk]:
                    st.text(f"Bộ {n}: {', '.join(map(str, nums))}")

if __name__ == "__main__":
    main()
