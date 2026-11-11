# Batch Logo Cleanup — app chạy cục bộ

App cho phép tải nhiều ảnh JPG/PNG/WEBP, chọn vùng logo ở một trong bốn góc, xem trước, inpaint vùng đã chọn, rồi tải từng ảnh hoặc ZIP.

## Cài đặt (Windows)

1. Cài Python 3.10 trở lên từ python.org và bật **Add Python to PATH**.
2. Mở Terminal/PowerShell trong thư mục chứa file `app.py`.
3. Chạy:

   ```powershell
   py -m pip install -r requirements.txt
   py -m streamlit run app.py
   ```

4. Truy cập địa chỉ được Streamlit hiện trên Terminal, thường là `http://localhost:8501`.

## Sử dụng

1. Thả nhiều ảnh vào app.
2. Chọn góc chứa logo (mặc định dưới phải).
3. Điều chỉnh kích thước và khoảng cách đến mép để khung đỏ bao đủ logo.
4. Kiểm tra ảnh xem trước rồi nhấn **Xử lý tất cả ảnh**.
5. Tải ZIP hoặc tải từng tệp riêng.

## Giới hạn

- Đây là phương pháp **inpainting theo vùng** (không phải nhận diện logo tự động).
- Nền chi tiết, chữ hoặc họa tiết phía sau vùng logo có thể không khôi phục chính xác.
- Không thay đổi hoặc đánh giá được dấu nguồn gốc ảnh vô hình như SynthID.
- Dùng cho ảnh bạn có quyền chỉnh sửa.
