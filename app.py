import streamlit as st
import requests
import pandas as pd
import json

# -----------------------------------------------------------------------------
# CẤU HÌNH TRANG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Soi Cầu Pro: Vị Trí & Giải",
    page_icon="💎",
    layout="wide"
)

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    div.stButton > button {width: 100%; height: 3em; font-weight: bold;}
    /* Ẩn index bảng */
    thead tr th:first-child {display:none}
    tbody th {display:none}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. DỮ LIỆU & CẤU TRÚC
# -----------------------------------------------------------------------------
API_URL = "https://www.kqxs88.live/api/front/open/lottery/history/list/game?limitNum=30&gameCode=miba"

# Cấu trúc XSMB chuẩn
XSMB_STRUCTURE = [
    ("GĐB", 1, 5), ("G1", 1, 5), ("G2", 2, 5), ("G3", 6, 5),
    ("G4", 4, 4), ("G5", 6, 4), ("G6", 3, 3), ("G7", 4, 2)
]

# Định nghĩa Bộ Đề
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
# 2. HÀM XỬ LÝ DATA
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

def create_position_map():
    mapping = []
    for p, c, l in XSMB_STRUCTURE:
        for i in range(1, c+1):
            for j in range(1, l+1): mapping.append(f"{p}.{i}.{j}")
    return mapping

def get_prize_map_indices():
    """
    Map vị trí cắt chuỗi cho từng giải.
    QUAN TRỌNG: Bỏ GĐB ra khỏi map này.
    """
    mapping = {}
    current = 0
    for p_name, count, length in XSMB_STRUCTURE:
        for i in range(1, count + 1):
            start, end = current, current + length
            # Chỉ thêm vào nếu không phải GĐB
            if p_name != "GĐB":
                key = f"{p_name}" if count == 1 else f"{p_name}.{i}"
                mapping[key] = (start, end)
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
            "de_rev": de[::-1],
            "de_set": get_set_name(de),
            "body": full
        })
    return processed_days

# -----------------------------------------------------------------------------
# 3. THUẬT TOÁN TÌM CẦU
# -----------------------------------------------------------------------------

# === A. SOI VỊ TRÍ (LOGIC CŨ: Body[i] + Body[j]) ===
def calculate_streak_pos(days_data, idx1, idx2, mode, allow_rev):
    streak = 0
    for day in days_data:
        val = day['body'][idx1] + day['body'][idx2]
        match = False
        if mode == "straight":
            if val == day['de']: match = True
            elif allow_rev and val == day['de_rev']: match = True
        else: # set
            if get_set_name(val) == day['de_set']: match = True
        
        if match: streak += 1
        else: break
    return streak

def find_position_bridges(days_data, mode="straight", allow_rev=False, min_streak=3):
    if not days_data: return []
    day0 = days_data[0]
    body = day0['body']
    candidates = []
    
    # Lọc ứng viên ngày đầu
    for i in range(len(body)):
        for j in range(len(body)):
            if i == j: continue
            val = body[i] + body[j]
            match = False
            if mode == "straight":
                if val == day0['de']: match = True
                elif allow_rev and val == day0['de_rev']: match = True
            else:
                if get_set_name(val) == day0['de_set']: match = True
            if match: candidates.append((i, j))
            
    # Check Streak
    finals = []
    for (i, j) in candidates:
        stk = calculate_streak_pos(days_data, i, j, mode, allow_rev)
        if stk >= min_streak:
            finals.append({"idx1": i, "idx2": j, "streak": stk})
            
    finals.sort(key=lambda x: x['streak'], reverse=True)
    return finals

# === B. SOI GIẢI / NHỊ HỢP (LOGIC MỚI: Giải chứa số) ===
def check_containment(prize_str, target_de, mode="straight"):
    digits = set(prize_str)
    if mode == "straight":
        # Phải chứa cả 2 số của Đề (VD: Đề 38 -> Giải phải có 3 và 8)
        return (target_de[0] in digits) and (target_de[1] in digits)
    else: # set
        # Phải chứa bất kỳ cặp nào trong bộ
        nums = BO_DE_DICT.get(get_set_name(target_de), [])
        for n in nums:
            if (n[0] in digits) and (n[1] in digits): return True
        return False

def find_prize_bridges(days_data, mode="straight", min_streak=3):
    prize_map = get_prize_map_indices() # Map này đã loại bỏ GĐB
    results = []
    
    for p_name, (s, e) in prize_map.items():
        streak = 0
        for day in days_data:
            p_str = day['body'][s:e]
            if check_containment(p_str, day['de'], mode): 
                streak += 1
            else: 
                break
        
        if streak >= min_streak:
            results.append({
                "prize": p_name, 
                "streak": streak,
                "today_val": days_data[0]['body'][s:e]
            })
            
    results.sort(key=lambda x: x['streak'], reverse=True)
    return results

# -----------------------------------------------------------------------------
# 4. GIAO DIỆN CHÍNH
# -----------------------------------------------------------------------------

def main():
    st.title("🔥 Soi Cầu Pro: Vị Trí & Giải")
    
    # --- MENU ĐIỀU KHIỂN TRÊN CÙNG ---
    with st.container():
        c1, c2, c3, c4, c5 = st.columns([2, 1, 1.5, 1.2, 1.5])
        
        with c1:
            method = st.selectbox("🎯 PHƯƠNG PHÁP", [
                "1. Cầu Vị Trí (Ghép 2 index)", 
                "2. Cầu Giải (Nhị Hợp G1-G7)"
            ])
            
        with c2:
            min_strk = st.number_input("Min Streak", 2, 15, 3)
            
        with c3:
            is_set = st.checkbox("Soi theo Bộ Đề", value=False)
            mode = "set" if is_set else "straight"
            
        with c4:
            allow_rev = True
            if not is_set and "Vị Trí" in method:
                allow_rev = st.checkbox("Đảo (AB-BA)", value=True)
            else:
                st.write("")
                
        with c5:
            st.write("")
            btn = st.button("🚀 QUÉT NGAY", type="primary")

    st.divider()
    
    # --- LẤY DỮ LIỆU ---
    raw = fetch_lottery_data()
    if not raw: st.error("Lỗi kết nối API"); return
    
    days = process_days_data(raw)
    pos_map = create_position_map()
    
    # --- BẢNG LỊCH SỬ 5 NGÀY (GỌN 1 DÒNG) ---
    st.subheader("📅 Kết quả 5 ngày gần nhất")
    if len(days) >= 5:
        hist_data = []
        for i in range(5):
            hist_data.append({
                "Ngày": days[i]['issue'],
                "Đề": days[i]['de'],
                "Bộ": days[i]['de_set']
            })
        # Dùng bảng Transpose để hiện ngang
        st.dataframe(pd.DataFrame(hist_data).T, use_container_width=True)
    
    # --- THỰC HIỆN QUÉT ---
    if btn:
        st.write("---")
        
        # --- METHOD 1: CẦU VỊ TRÍ (Index A + Index B) ---
        if "Vị Trí" in method:
            st.subheader(f"🌐 KẾT QUẢ CẦU VỊ TRÍ ({mode.upper()})")
            
            with st.spinner("Đang quét 10.000 cặp vị trí..."):
                res = find_position_bridges(days, mode=mode, allow_rev=allow_rev, min_streak=min_strk)
            
            if res:
                # Hiển thị Top 50 cầu đẹp
                data_show = []
                for item in res[:50]:
                    idx1, idx2 = item['idx1'], item['idx2']
                    val_today = days[0]['body'][idx1] + days[0]['body'][idx2]
                    data_show.append({
                        "Vị trí 1": f"{pos_map[idx1]}",
                        "Vị trí 2": f"{pos_map[idx2]}",
                        "Thông": f"{item['streak']} ngày 🔥",
                        "Báo số": val_today
                    })
                st.dataframe(pd.DataFrame(data_show), use_container_width=True)
            else:
                st.warning(f"Không tìm thấy cầu vị trí nào thông {min_strk} ngày.")

        # --- METHOD 2: CẦU GIẢI / NHỊ HỢP (Ghép trong Giải) ---
        elif "Cầu Giải" in method:
            st.subheader(f"🔎 KẾT QUẢ CẦU GIẢI / NHỊ HỢP ({mode.upper()})")
            st.markdown("*Quy tắc: Xét G1-G7. Giải nào có chứa đủ các chữ số tạo thành Đề (hoặc Bộ Đề) thì tính là Cầu.*")
            
            with st.spinner("Đang phân tích các giải (Bỏ qua GĐB)..."):
                res = find_prize_bridges(days, mode=mode, min_streak=min_strk)
            
            if res:
                data_show = []
                for item in res:
                    data_show.append({
                        "Tên Giải": item['prize'],
                        "Thông": f"{item['streak']} ngày 🔥",
                        "Dữ liệu hôm nay": item['today_val'],
                        # Logic gợi ý cho ngày mai: Dựa vào dữ liệu hôm nay, user tự ghép
                        "Ghi chú": "Chứa số tạo Đề"
                    })
                st.dataframe(pd.DataFrame(data_show), use_container_width=True)
            else:
                st.warning(f"Không có giải nào (G1-G7) chứa đề thông {min_strk} ngày.")

if __name__ == "__main__":
    main()
