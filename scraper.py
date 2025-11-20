import easyocr
import numpy as np
from PIL import Image
import cv2
import re

# Khởi tạo OCR
reader = easyocr.Reader(['vi', 'en'], gpu=False) # Thêm tiếng Việt để đọc chữ "Giải"

def clean_text_ocr(text):
    """Chuẩn hóa text để so sánh: viết thường, bỏ dấu, bỏ chấm"""
    # Ví dụ: "G.ĐB" -> "gdb", "Giải ĐB" -> "giaidb"
    text = text.lower()
    text = text.replace(".", "").replace(" ", "").replace(",", "")
    # Map ký tự tiếng việt cơ bản nếu OCR đọc lỗi
    text = text.replace("đ", "d")
    return text

def extract_numbers_from_image(image_file):
    """
    1. Đọc toàn bộ chữ trong ảnh.
    2. Tìm từ khóa 'gdb', 'giaidb', 'dacbiet'.
    3. Chỉ lấy các số xuất hiện SAU từ khóa đó.
    """
    try:
        # Xử lý ảnh
        image = Image.open(image_file)
        img = np.array(image)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        
        # Tăng tương phản
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # Đọc toàn bộ (cả chữ và số)
        raw_results = reader.readtext(gray, detail=0, paragraph=False)
        
        # Mốc bắt đầu (Mặc định là 0 nếu không tìm thấy chữ GĐB)
        start_index = 0
        found_anchor = False
        
        # Các từ khóa nhận diện giải đặc biệt
        keywords = ['gdb', 'giaidb', 'dacbiet', 'giai0', 'db']
        
        for i, text in enumerate(raw_results):
            cleaned = clean_text_ocr(text)
            # Kiểm tra xem text có chứa từ khóa không
            if any(kw in cleaned for kw in keywords):
                start_index = i
                found_anchor = True
                # Gặp GĐB cái là dừng tìm, đánh dấu mốc tại đây
                break 
        
        # Lọc số từ mốc trở đi
        candidates = []
        
        # Duyệt từ start_index + 1 (Bỏ qua chính chữ GĐB)
        scan_list = raw_results[start_index:] if found_anchor else raw_results
        
        for text in scan_list:
            # Xử lý text: Xóa khoảng trắng, dấu chấm (nếu số tiền 10.000)
            t = text.replace(" ", "").replace(".", "").replace(",", "").strip()
            
            # Chỉ lấy nếu là số
            if t.isdigit():
                # QUY TẮC ĐỘ DÀI XSMB: 2, 3, 4, 5 chữ số
                if len(t) in [2, 3, 4, 5]:
                    candidates.append(t)
            else:
                # Trường hợp OCR đọc nhầm số 0 thành chữ O, hoặc dính ký tự lạ
                # Cố gắng lọc
                digits_only = "".join(filter(str.isdigit, t))
                if len(digits_only) >= 2 and len(digits_only) <= 5:
                    # Kiểm tra tỷ lệ số (tránh lấy mã 7RS -> 7)
                    # Nếu chuỗi gốc dài mà chỉ có 1-2 số thì bỏ (VD: 'Thứ 5' -> 5)
                    if len(digits_only) == len(t): # Sạch sẽ
                        candidates.append(digits_only)

        return candidates, found_anchor

    except Exception as e:
        return [f"Lỗi: {str(e)}"], False

def map_numbers_to_107_str(numbers_list):
    """
    Ghép 27 số đầu tiên vào chuỗi 107 ký tự.
    """
    PRIZE_COUNTS = [1, 1, 2, 6, 4, 6, 3, 4] # GĐB -> G7
    PRIZE_LENGTHS = [5, 5, 5, 5, 4, 4, 3, 2]
    
    full_str = ""
    current_idx = 0
    
    for count, length in zip(PRIZE_COUNTS, PRIZE_LENGTHS):
        for _ in range(count):
            if current_idx < len(numbers_list):
                val = numbers_list[current_idx]
                if len(val) == length: full_str += val
                elif len(val) > length: full_str += val[-length:]
                else: full_str += val.rjust(length, '?')
            else:
                full_str += "?" * length
            current_idx += 1
    return full_str
