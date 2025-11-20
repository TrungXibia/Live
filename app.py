import streamlit as st
import requests
import pandas as pd
import json

# -----------------------------------------------------------------------------
# CẤU HÌNH TRANG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Soi Cầu Pro: Nhị Hợp & Dàn Đề",
    page_icon="🎲",
    layout="wide"
)

st.markdown("""
<style>
    .stDataFrame {font-size: 14px;}
    /* Thu gọn bảng lịch sử */
    .compact-table {margin-bottom: 0px;}
    div.stButton > button {width: 100%; height: 3em; font-weight: bold;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 1. DỮ LIỆU & CẤU TRÚC
# -----------------------------------------------------------------------------
API_URL = "https://www.kqxs88.live/api/front/open/lottery/history/list/game?limitNum=30&gameCode=miba"

# Cấu trúc giải (Tên, Số lượng, Độ dài)
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

def get_prize_map_indices():
    """
    Map vị trí cắt chuỗi cho từng giải.
    Bỏ qua GĐB vì yêu cầu không xét GĐB.
    """
    mapping = {}
    current = 0
    for p_name, count, length in XSMB_STRUCTURE:
        for i in range(1, count + 1):
            # Tính toán vị trí start:end
            start, end = current, current + length
            
            # Chỉ thêm vào map nếu KHÔNG PHẢI LÀ GĐB
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
            "de_set": get_set_name(de),
            "body": full
        })
    return processed_days

# -----------------------------------------------------------------------------
# 3. LOGIC TÌM CẦU NHỊ HỢP (GHÉP TRONG GIẢI)
# -----------------------------------------------------------------------------

def check_containment_25_pairs(prize_str, target_de, mode="straight"):
    """
    Kiểm tra xem target_de có nằm trong dàn 25 số tạo ra từ prize_str không.
    Ghép thành 25 số tức là mọi chữ số ghép với mọi chữ số (bao gồm cả chính nó).
    -> Điều kiện: Chỉ cần Cả 2 chữ số của Đề đều xuất hiện trong prize_str là Đủ.
    """
    digits_in_prize = set(prize_str) # Tập hợp các chữ số có trong giải
    
    if mode == "straight":
        d1, d2 = target_de[0], target_de[1]
        # Ví dụ: Đề 38. Prize 12385. -> Có 3, Có 8 -> True
        # Ví dụ: Đề 33. Prize 12345. -> Có 3 -> True (vì ghép 3 với 3 được)
        return (d1 in digits_in_prize) and (d2 in digits_in_prize)
        
    else: # mode == "set" (Bộ)
        # Lấy tất cả các số trong bộ
        set_name = get_set_name(target_de)
        numbers_in_set = BO_DE_DICT.get(set_name, [])
        
        # Nếu tạo được BẤT KỲ số nào trong bộ -> True
        for num in numbers_in_set:
            d1, d2 = num[0], num[1]
            if (d1 in digits_in_prize) and (d2 in digits_in_prize):
                return True
        return False

def find_nhi_hop_streak(days_data, mode="straight"):
    """
    Quét tất cả các giải (trừ GĐB), tìm xem giải nào "chứa" đề liên tiếp.
    """
    prize_map = get_prize_map_indices()
    results = []
    
    # Duyệt từng giải: G1, G2.1, G2.2 ...
    for prize_name, (start, end) in prize_map.items():
        streak = 0
        
        # Duyệt ngược quá khứ (từ ngày 0 trở về trước)
        for i in range(len(days_data)):
            day = days_data[i]
            prize_str = day['body'][start:end]
            
            # Kiểm tra xem Giải này có tạo ra Đề ngày hôm đó không
            if check_containment_25_pairs(prize_str, day['de'], mode):
                streak += 1
            else:
                break # Gãy cầu -> dừng
        
        # Chỉ lấy cầu nào đang chạy (Streak >= 2 ngày cho uy tín)
        if streak >= 2:
            # Lấy dữ liệu ngày hôm nay để báo cáo
            today = days_data[0]
            today_prize_str = today['body'][start:end]
            
            results.append({
                "Giải": prize_name,
                "Streak": streak,
                "Dữ liệu hôm nay": today_prize_str,
                "Đề về hôm nay": today['de'] # Để đối chiếu
            })
            
    # Sắp xếp: Cầu dài nhất lên đầu
    results.sort(key=lambda x: x['Streak'], reverse=True)
    return results

# -----------------------------------------------------------------------------
# 4. GIAO DIỆN
# -----------------------------------------------------------------------------

def main():
    st.title("🔥 Soi Cầu Pro: Nhị Hợp (Ghép Trong)")
    
    # --- MENU CẤU HÌNH ---
    with st.container():
        c1, c2, c3 = st.columns([2, 1.5, 1.5])
        
        with c1:
            st.write("**Chế độ mặc định:** Nhị Hợp (Ghép trong giải)")
            st.caption("Tự động loại bỏ GĐB. Xét G1 -> G7.")
            
        with c2:
            is_set = st.checkbox("Soi theo Bộ Đề", value=False, help="Mở rộng điều kiện trúng")
            mode = "set" if is_set else "straight"
            
        with c3:
            btn = st.button("🚀 QUÉT CẦU", type="primary")

    st.divider()
    
    # --- FETCH DATA ---
    raw = fetch_lottery_data()
    if not raw: st.error("Lỗi API"); return
    days = process_days_data(raw)
    
    # --- 1. HIỂN THỊ LỊCH SỬ 5 NGÀY (THU GỌN 1 DÒNG) ---
    st.subheader("📅 Kết quả 5 ngày gần nhất")
    
    if len(days) >= 5:
        # Tạo DataFrame ngang
        history_data = []
        for i in range(5):
            d = days[i]
            history_data.append({
                "Ngày": d['issue'],
                "Đề": d['de'],
                "Bộ": d['de_set']
            })
        
        # Chuyển vị (Transpose) để hiện thành 1 bảng ngang gọn
        df_hist = pd.DataFrame(history_data)
        # Dùng st.dataframe với chiều cao thấp
        st.dataframe(df_hist.T, use_container_width=True)
    else:
        st.warning("Chưa đủ dữ liệu 5 ngày.")

    # --- 2. XỬ LÝ QUÉT ---
    if btn:
        st.write("---")
        st.subheader(f"🔎 DANH SÁCH CẦU NHỊ HỢP ĐANG CHẠY ({mode.upper()})")
        st.markdown("""
        *Quy tắc: Lấy các chữ số trong giải ghép vòng tròn (Nhị hợp). Nếu trong dàn số tạo ra có chứa số Đề -> Cầu chạy.*
        """)
        
        with st.spinner("Đang phân tích các giải..."):
            res = find_nhi_hop_streak(days, mode=mode)
            
        if res:
            # Hiển thị bảng kết quả
            final_data = []
            for item in res:
                # Tạo dàn số minh họa cho ngày hôm nay (Optional, để user dễ hiểu)
                # Nhưng user yêu cầu "xét xem đề có trong đó k thì báo có"
                # Ta hiển thị trạng thái "OK"
                
                final_data.append({
                    "Tên Giải": item['Giải'],
                    "Số ngày thông": f"{item['Streak']} ngày 🔥",
                    "Số liệu hôm nay": item['Dữ liệu hôm nay'],
                    "Ghép ra Đề?": f"Chứa {item['Đề về hôm nay']} ✅" 
                })
            
            st.dataframe(pd.DataFrame(final_data), use_container_width=True)
            
            # Gợi ý top 1
            top1 = res[0]
            st.success(f"💡 Cầu đẹp nhất: **{top1['Giải']}** đang chạy thông **{top1['Streak']} ngày**. Hãy chú ý giải này vào ngày mai!")
            
        else:
            st.warning("Hiện tại không có giải nào (G1-G7) chứa đề thông 2 ngày trở lên.")

if __name__ == "__main__":
    main()
