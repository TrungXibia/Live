import streamlit as st
import requests
import pandas as pd
import json
import itertools

# -----------------------------------------------------------------------------
# CẤU HÌNH TRANG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Super Soi Cầu: 3 Càng - Lô - Đề",
    page_icon="💎",
    layout="wide"
)

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    div[data-testid="stExpander"] {border: 1px solid #e6e6e6; border-radius: 5px;}
    .highlight {color: #d63384; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH API & DỮ LIỆU
# -----------------------------------------------------------------------------
API_URL = "https://www.kqxs88.live/api/front/open/lottery/history/list/game?limitNum=10&gameCode=miba"

XSMB_STRUCTURE = [
    ("G1", 1, 5), ("G2", 2, 5), ("G3", 6, 5),
    ("G4", 4, 4), ("G5", 6, 4), ("G6", 3, 3), ("G7", 4, 2)
]

# BỘ ĐỀ (Chỉ dùng cho 2 số)
BO_DE_DICT = {
    "00": ["00", "55", "05", "50"], "11": ["11", "66", "16", "61"],
    "22": ["22", "77", "27", "72"], "33": ["33", "88", "38", "83"],
    "44": ["44", "99", "49", "94"], "01": ["01", "10", "06", "60", "51", "15", "56", "65"],
    "02": ["02", "20", "07", "70", "52", "25", "57", "75"],
    "03": ["03", "30", "08", "80", "53", "35", "58", "85"],
    "04": ["04", "40", "09", "90", "54", "45", "59", "95"],
    "12": ["12", "21", "17", "71", "62", "26", "67", "76"],
    "13": ["13", "31", "18", 81, "63", "36", "68", "86"],
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
            
        target_2 = full_str[3:5] # GĐB 2 số cuối
        target_3 = full_str[2:5] # GĐB 3 số cuối (3 càng)
        body = full_str[5:]
        
        processed_days.append({
            "index": i,
            "issue": record.get('turnNum'),
            "target_2": target_2,
            "target_2_rev": target_2[::-1],
            "target_set": get_set_name(target_2),
            "target_3": target_3,
            "body": body
        })
        
    return processed_days, pos_map

# -----------------------------------------------------------------------------
# 3. THUẬT TOÁN TÌM CẦU (CORE LOGIC)
# -----------------------------------------------------------------------------

def find_bridges_2_positions(days_data, mode="straight", allow_rev=False):
    """Tìm cầu 2 vị trí (Bạch thủ / Bộ đề)"""
    if not days_data: return []
    
    day0 = days_data[0]
    body = day0['body']
    candidate_pairs = []
    
    # Lọc ứng viên ngày mới nhất
    for i in range(len(body)):
        for j in range(len(body)):
            if i == j: continue
            val = body[i] + body[j]
            
            is_match = False
            if mode == "straight":
                if val == day0['target_2']: is_match = True
                elif allow_rev and val == day0['target_2_rev']: is_match = True
            else: # mode set
                if get_set_name(val) == day0['target_set']: is_match = True
            
            if is_match:
                candidate_pairs.append((i, j))
    
    # Kiểm tra streak
    final_pairs = []
    for (i, j) in candidate_pairs:
        streak_ok = True
        for k in range(1, len(days_data)):
            day_k = days_data[k]
            body_k = day_k['body']
            val_k = body_k[i] + body_k[j]
            
            if mode == "straight":
                if allow_rev:
                    if val_k != day_k['target_2'] and val_k != day_k['target_2_rev']:
                        streak_ok = False; break
                else:
                    if val_k != day_k['target_2']:
                        streak_ok = False; break
            else:
                if get_set_name(val_k) != day_k['target_set']:
                    streak_ok = False; break
        
        if streak_ok: final_pairs.append((i, j))
            
    return final_pairs

def find_bridges_3_positions(days_data):
    """
    Tìm cầu 3 càng (3 vị trí ghép lại thành 3 số cuối GĐB).
    Thuật toán tối ưu: Không dùng 3 vòng lặp lồng nhau (O(N^3)).
    """
    if not days_data: return []
    
    day0 = days_data[0]
    target0 = day0['target_3'] # Ví dụ "589"
    body0 = day0['body']
    
    # 1. Tối ưu hóa việc tìm ứng viên ngày 0 bằng Map
    # Tìm tất cả vị trí của từng chữ số trong target
    # Ví dụ: target="589" -> positions_of_5, positions_of_8, positions_of_9
    
    pos_idx_0 = [i for i, char in enumerate(body0) if char == target0[0]]
    pos_idx_1 = [i for i, char in enumerate(body0) if char == target0[1]]
    pos_idx_2 = [i for i, char in enumerate(body0) if char == target0[2]]
    
    candidate_triplets = []
    
    # Tạo tổ hợp từ các vị trí tìm được (Cartesian product)
    for i in pos_idx_0:
        for j in pos_idx_1:
            if i == j: continue
            for k in pos_idx_2:
                if k == i or k == j: continue
                # Đây là tổ hợp tạo ra đúng 3 càng ngày 0
                candidate_triplets.append((i, j, k))
    
    # 2. Kiểm tra Streak các ngày cũ
    final_triplets = []
    
    for (i, j, k) in candidate_triplets:
        streak_ok = True
        for d in range(1, len(days_data)):
            day_d = days_data[d]
            # Giá trị ghép từ 3 vị trí này ở ngày quá khứ
            val_d = day_d['body'][i] + day_d['body'][j] + day_d['body'][k]
            
            # So sánh với 3 càng của ngày đó
            if val_d != day_d['target_3']:
                streak_ok = False
                break
        
        if streak_ok:
            final_triplets.append((i, j, k))
            
    return final_triplets

# -----------------------------------------------------------------------------
# 4. GIAO DIỆN NGƯỜI DÙNG
# -----------------------------------------------------------------------------

def main():
    st.title("💎 Super Soi Cầu: 3 Càng - Lô - Đề")
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.header("⚙️ Cấu Hình")
        
        scan_days = st.slider("Số ngày chạy thông", 2, 5, 3)
        
        # Thêm lựa chọn 3 Càng
        scan_mode = st.radio("Loại cầu", [
            "Soi Đề (2 số) - Thẳng",
            "Soi Đề (2 số) - Bộ",
            "Soi 3 Càng (3 số GĐB)"
        ])
        
        # Cấu hình phụ
        allow_rev = False
        if scan_mode == "Soi Đề (2 số) - Thẳng":
            st.caption("--- Tùy chọn ---")
            allow_rev = st.checkbox("Chấp nhận đảo (AB-BA)", value=True)
            
        if st.button("🚀 QUÉT CẦU NGAY", type="primary"):
            st.session_state['run_scan'] = True

    # --- DATA FETCHING ---
    raw_list = fetch_lottery_data()
    if not raw_list:
        st.error("Lỗi API.")
        return

    processed_days, pos_map = process_days_data(raw_list, scan_days)
    if len(processed_days) < scan_days:
        st.warning("Không đủ dữ liệu.")
        return

    # --- HIỂN THỊ KẾT QUẢ CÁC KỲ ---
    st.subheader(f"📅 Kết quả {scan_days} ngày qua")
    cols = st.columns(scan_days)
    for idx, day in enumerate(processed_days):
        with cols[idx]:
            st.markdown(f"**{day['issue']}**")
            if "3 Càng" in scan_mode:
                # Hiển thị 3 số
                st.code(f"3 Càng: {day['target_3']}", language="text")
            else:
                # Hiển thị 2 số
                st.code(f"Đề: {day['target_2']}", language="text")
                if "Bộ" in scan_mode:
                    st.caption(f"Bộ: {day['target_set']}")

    # --- XỬ LÝ QUÉT CẦU ---
    if st.session_state.get('run_scan'):
        
        st.divider()
        
        if "3 Càng" in scan_mode:
            # --- LOGIC 3 CÀNG ---
            with st.spinner("Đang quét thuật toán 3 càng (Siêu tốc)..."):
                results = find_bridges_3_positions(processed_days)
                
            st.header(f"🔥 TÌM THẤY {len(results)} CẦU 3 CÀNG THÔNG {scan_days} NGÀY")
            
            if results:
                df_data = []
                for (i, j, k) in results:
                    row = {
                        "Vị trí 1": f"{pos_map[i]}",
                        "Vị trí 2": f"{pos_map[j]}",
                        "Vị trí 3": f"{pos_map[k]}",
                    }
                    for day in processed_days:
                        val = day['body'][i] + day['body'][j] + day['body'][k]
                        row[f"Ngày {day['issue']}"] = val
                    df_data.append(row)
                
                st.dataframe(pd.DataFrame(df_data), use_container_width=True)
            else:
                st.warning("Không có cầu 3 càng nào chạy thông (Điều này rất bình thường vì xác suất 3 càng cực khó).")
                
        else:
            # --- LOGIC 2 SỐ (ĐỀ) ---
            mode_key = "set" if "Bộ" in scan_mode else "straight"
            
            with st.spinner("Đang quét cầu đề..."):
                results = find_bridges_2_positions(processed_days, mode=mode_key, allow_rev=allow_rev)
                
            st.header(f"🔥 TÌM THẤY {len(results)} CẦU ĐỀ THÔNG {scan_days} NGÀY")
            
            if results:
                df_data = []
                for (i, j) in results:
                    row = {
                        "Vị trí 1": f"{pos_map[i]}",
                        "Vị trí 2": f"{pos_map[j]}",
                    }
                    for day in processed_days:
                        val = day['body'][i] + day['body'][j]
                        
                        # Hiển thị đẹp
                        display_val = val
                        if mode_key == "straight":
                            if val == day['target_2']: display_val += " (Thẳng)"
                            elif val == day['target_2_rev']: display_val += " (Đảo)"
                        else:
                            display_val += f" (Bộ {get_set_name(val)})"
                            
                        row[f"Ngày {day['issue']}"] = display_val
                    df_data.append(row)
                
                st.dataframe(pd.DataFrame(df_data), use_container_width=True)
            else:
                st.warning("Không tìm thấy cầu nào.")

    # Tra cứu bộ đề (ẩn khi đang soi 3 càng)
    if "3 Càng" not in scan_mode:
        with st.expander("📖 Tra cứu Bộ Đề"):
            c1, c2, c3 = st.columns(3)
            sets = list(BO_DE_DICT.items())
            sz = (len(sets)//3) + 1
            for i, col in enumerate([c1, c2, c3]):
                with col:
                    for n, nums in sets[i*sz : (i+1)*sz]:
                        st.text(f"Bộ {n}: {', '.join(map(str, nums))}")

if __name__ == "__main__":
    main()
