import requests
from bs4 import BeautifulSoup
import time

# Cấu trúc chuẩn XSMB để mapping
XSMB_STRUCTURE = [
    ("GĐB", 1, 5), ("G1", 1, 5), ("G2", 2, 5), ("G3", 6, 5),
    ("G4", 4, 4), ("G5", 6, 4), ("G6", 3, 3), ("G7", 4, 2)
]

def get_live_xsmb_minhngoc():
    """
    Truy cập minhngoc.net.vn lấy dữ liệu trực tiếp.
    Trả về: (full_string_107_chars, filled_length)
    """
    url = "https://www.minhngoc.net.vn/xo-so-truc-tiep/mien-bac.html"
    
    # Headers giả lập Chrome Windows mới nhất để tránh bị chặn
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }

    try:
        # Thêm tham số t để tránh cache phía server/proxy
        response = requests.get(f"{url}?t={int(time.time())}", headers=headers, timeout=8)
        
        if response.status_code != 200:
            return None, f"HTTP Error {response.status_code}"

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 1. Tìm bảng kết quả
        # Minh Ngọc thường dùng id="noidung" -> div.box_kqxs
        box = soup.find('div', class_='box_kqxs')
        if not box:
            return None, "Không tìm thấy bảng kết quả (HTML thay đổi?)"

        # 2. Bóc tách từng giải
        prizes_data = {}
        
        # Map tên class trong HTML của Minh Ngọc
        class_map = {
            "GĐB": "giaiDb", # Lưu ý: chữ D viết hoa
            "G1": "giai1", "G2": "giai2", "G3": "giai3",
            "G4": "giai4", "G5": "giai5", "G6": "giai6", "G7": "giai7"
        }
        
        for my_name, mn_class in class_map.items():
            # Tìm ô chứa giải (td)
            cell = box.find('td', class_=mn_class)
            nums = []
            
            if cell:
                # Giải nhiều số (G3, G4...) thường nằm trong thẻ <div> con
                divs = cell.find_all('div')
                if divs:
                    nums = [d.text.strip() for d in divs]
                else:
                    # Giải ít số (GĐB, G1) nằm trực tiếp trong <td>
                    text = cell.text.strip()
                    if text: nums = [text]
            
            # Lọc sạch chỉ lấy số
            clean_nums = []
            for n in nums:
                # Chỉ giữ lại ký tự số
                digits = "".join(filter(str.isdigit, n))
                if digits: clean_nums.append(digits)
                
            prizes_data[my_name] = clean_nums

        # 3. Ghép chuỗi 107 ký tự (Quan trọng nhất)
        full_str = ""
        
        for p_name, count, length in XSMB_STRUCTURE:
            current_nums = prizes_data.get(p_name, [])
            
            for i in range(count):
                if i < len(current_nums):
                    val = current_nums[i]
                    # Nếu số đang quay dở (chưa đủ ký tự), điền thêm '?' vào đuôi
                    # Ví dụ: Đang quay '12' cho giải 3 chữ số -> '12?'
                    if len(val) < length:
                        full_str += val.ljust(length, '?')
                    else:
                        full_str += val[:length] # Cắt đúng độ dài nếu thừa
                else:
                    # Chưa quay đến
                    full_str += "?" * length

        # Tính số lượng ký tự đã quay xong
        filled_len = 107 - full_str.count('?')
        
        return full_str, filled_len

    except Exception as e:
        return None, str(e)

# Test chạy thử khi gọi trực tiếp file này
if __name__ == "__main__":
    s, l = get_live_xsmb_minhngoc()
    print(f"Độ dài: {l}/107")
    print(f"Chuỗi: {s}")
