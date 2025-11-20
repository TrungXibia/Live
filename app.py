import streamlit as st
import requests
import pandas as pd
import json

# -----------------------------------------------------------------------------
# CẤU HÌNH TRANG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Soi Cầu Pro: Nhị Hợp Ghép Trong",
    page_icon="🎲",
    layout="wide"
)

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    div[data-testid="stExpander"] {border: 1px solid #e6e6e6; border-radius: 5px;}
    div.stButton > button {width: 100%; height: 3em; font-weight: bold;}
    .badge {
        background-color: #28a745; color: white; padding: 2px 8px; 
        border-radius: 4px; font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. DỮ LIỆU & CẤU TRÚC
# -----------------------------------------------------------------------------
API_URL = "https://www.kqxs88.live/api/front/open/lottery/history/list/game?limitNum=20&gameCode=miba"

# Cấu trúc giải để cắt chuỗi (Tên, Số lượng, Độ dài)
XSMB_STRUCTURE = [
    ("GĐB", 1, 5), ("G1", 1, 5), ("G2", 2, 5), ("G3", 6, 5),
    ("G4", 4, 4), ("G5", 6, 4), ("G6", 3, 3), ("G7", 4, 2)
]

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
NUMBER_TO_SET_MAP = {str(n): s for s, nums in BO_DE_DICT.items() for n in nums}

# -----------------------------------------------------------------------------
# 2. HÀM XỬ LÝ
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_lottery_data():
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(API_URL, headers=headers, timeout=10).json()
        return res.get('t', {}).get('issueList', [])
    except: return None

def parse_detail_to_107_chars(detail_str):
    try:
        return "".join([g.replace(",", "").strip() for g in json.loads(detail_str)]) if detail_str else ""
    except: return ""

def get_set_name(n): return NUMBER_TO_SET_MAP.get(str(n), "?")

def get_prize_map_indices():
    """
    Tạo map vị trí cắt chuỗi cho từng giải.
    Trả về: {'G1': (5, 10), 'G2.1': (10, 15)...}
    """
    mapping = {}
    current = 0
    # Lưu ý: XSMB 107 ký tự thực tế bắt đầu từ GĐB (5 số) -> G1 -> ...
    # Nhưng hàm parse của chúng ta trả về full chuỗi bao gồm cả GĐB ở đầu.
    
    # Cấu trúc API trả về thường là GĐB trước rồi đến các giải khác.
    # Ta cần map đúng thứ tự chuỗi 107 ký tự.
    # GĐB (5) -> G1 (5) -> G2 (10) -> ...
    
    for p_name, count, length in XSMB_STRUCTURE:
        for i in range(1, count + 1):
            key = f"{p_name}" if count == 1 else f"{p_name}.{i}"
            mapping[key] = (current, current + length)
            current += length
    return mapping

def process_days_data(raw_list):
    processed_days = []
    for i in range(len(raw_list)):
        record = raw_list[i]
        full = parse_detail_to_107_chars(record.get('detail', ''))
        if len(full) != 107: continue
        
        target_3cang = full[2:5]
        de = target_3cang[1:]
        
        processed_days.append({
            "index": i,
            "issue": record.get('turnNum'),
            "de": de,
            "de_set": get_set_name(de),
            "body": full # Chuỗi 107 ký tự
        })
    return processed_days

# -----------------------------------------------------------------------------
# 3. LOGIC TÌM CẦU "NHỊ HỢP GHÉP TRONG"
# -----------------------------------------------------------------------------

def check_containment(prize_str, target_de, mode="straight"):
    """
    Kiểm tra xem target_de có được tạo thành từ các chữ số của prize_str không.
    """
    # Tách giải thành list các chữ số. VD: "12345" -> ['1','2','3','4','5']
    digits = list(prize_str)
    
    if mode == "straight":
        # Cần tạo ra chính xác con đề (VD: 38)
        d1, d2 = target_de[0], target_de[1]
        # Logic: d1 phải có trong prize VÀ d2 phải có trong prize
        return (d1 in digits) and (d2 in digits)
        
    else: # mode == "set" (Bộ)
        # Lấy danh sách các số trong bộ đề (VD: Bộ 03 gồm 03,30,08,80...)
        set_name = get_set_name(target_de)
        numbers_in_set = BO_DE_DICT.get(set_name, [])
        
        # Nếu BẤT KỲ số nào trong bộ có thể ghép được từ prize -> True
        for num in numbers_in_set:
            d1, d2 = num[0], num[1]
            if (d1 in digits) and (d2 in digits):
                return True
        return False

def find_nhi_hop_containment(days_data, mode="straight", min_streak=2):
    """
    Quét tất cả các giải, tìm giải nào ghép ra đề liên tiếp N ngày.
    """
    prize_map = get_prize_map_indices()
    results = []
    
    for prize_name, (start, end) in prize_map.items():
        streak = 0
        
        # Duyệt từ ngày mới nhất (0) về quá khứ
        for i in range(len(days_data)):
            day = days_data[i]
            prize_str = day['body'][start:end]
            
            is_hit = check_containment(prize_str, day['de'], mode)
            
            if is_hit:
                streak += 1
            else:
                break # Đứt cầu
        
        if streak >= min_streak:
            # Lấy thông tin ngày hôm nay để hiển thị
            today = days_data[0]
            today_prize = today['body'][start:end]
            results.append({
                "Giải": prize_name,
                "Streak": streak,
                "Dữ liệu hôm nay": today_prize,
                "Đề về": today['de']
            })
            
    # Sắp xếp streak giảm dần
    results.sort(key=lambda x: x['Streak'], reverse=True)
    return results

# -----------------------------------------------------------------------------
# 4. GIAO DIỆN
# -----------------------------------------------------------------------------

def main():
    st.title("🔥 Soi Cầu: Nhị Hợp (Ghép Trong Giải)")
    
    # --- MENU TRÊN CÙNG ---
    with st.container():
        c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 1.5])
        
        with c1:
            scan_type = st.selectbox("Chế độ", ["Nhị Hợp (Ghép trong giải)", "Cầu Đề (Vị trí)"])
            
        with c2:
            min_strk = st.number_input("Min Streak", 2, 10, 3)
            
        with c3:
            is_set = st.checkbox("Soi theo Bộ", value=False, help="Mở rộng ra cả bộ đề")
            mode = "set" if is_set else "straight"
            
        with c4:
            st.write("")
            btn = st.button("🚀 QUÉT NGAY", type="primary")

    st.divider()
    
    # --- FETCH DATA ---
    raw = fetch_lottery_data()
    if not raw: st.error("Lỗi API"); return
    days = process_days_data(raw)
    
    # --- HIỂN THỊ KQ GẦN ĐÂY ---
    st.subheader("📅 Kết quả 5 ngày gần nhất")
    cols = st.columns(5)
    for i in range(min(5, len(days))):
        with cols[i]:
            st.info(f"{days[i]['issue']}")
            st.markdown(f"Đề: **{days[i]['de']}**")
            st.caption(f"Bộ: {days[i]['de_set']}")

    # --- XỬ LÝ ---
    if btn:
        st.write("---")
        
        if "Nhị Hợp" in scan_type:
            st.subheader(f"🔎 KẾT QUẢ NHỊ HỢP ({mode.upper()})")
            st.markdown("""
            **Cách hiểu:** Ví dụ Giải 1 là `12345`.
            - Nếu đề về `15` -> **Ăn** (vì có số 1 và 5).
            - Nếu đề về `33` -> **Ăn** (vì có số 3, chấp nhận ghép trùng).
            - Bảng dưới liệt kê các giải đã "ăn" liên tiếp nhiều ngày.
            """)
            
            with st.spinner("Đang phân tích từng giải..."):
                res = find_nhi_hop_containment(days, mode=mode, min_streak=min_strk)
                
            if res:
                # Format lại cho đẹp
                df = pd.DataFrame(res)
                # Thêm icon lửa vào streak
                df['Streak'] = df['Streak'].apply(lambda x: f"{x} ngày 🔥")
                st.dataframe(df, use_container_width=True)
            else:
                st.warning(f"Không có giải nào ghép ra đề thông {min_strk} ngày cả.")
                
        else:
            st.info("Vui lòng chọn chế độ 'Nhị Hợp' để trải nghiệm tính năng mới này.")

if __name__ == "__main__":
    main()
