"""Batch cleanup for a user-selected corner logo region on owned images.

Run with: streamlit run app.py
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import zipfile

import cv2
import numpy as np
import streamlit as st
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

st.set_page_config(page_title="Batch Logo Cleanup", page_icon="🧽", layout="wide")
st.title("🧽 Batch Logo Cleanup")
st.caption("Xử lý một vùng logo ở góc ảnh theo thiết lập chung, tải xuống từng ảnh hoặc tất cả dưới dạng ZIP. Ảnh được xử lý cục bộ tại nơi bạn chạy ứng dụng.")


def get_image(blob: bytes) -> Image.Image:
    img = Image.open(BytesIO(blob))
    img = ImageOps.exif_transpose(img)
    img.load()
    return img


def rectangle_for(
    size: tuple[int, int],
    corner: str,
    width_pct: float,
    height_pct: float,
    x_margin_pct: float,
    y_margin_pct: float,
) -> tuple[int, int, int, int]:
    w, h = size
    rw = max(1, round(w * width_pct / 100))
    rh = max(1, round(h * height_pct / 100))
    mx = round(w * x_margin_pct / 100)
    my = round(h * y_margin_pct / 100)

    if corner.endswith("phải"):
        x1 = w - mx - rw
    else:
        x1 = mx
    if corner.startswith("Dưới"):
        y1 = h - my - rh
    else:
        y1 = my
    x1 = min(max(0, x1), max(0, w - rw))
    y1 = min(max(0, y1), max(0, h - rh))
    return (x1, y1, x1 + rw, y1 + rh)


def clean_logo(img: Image.Image, region: tuple[int, int, int, int], radius: int, algorithm: str) -> Image.Image:
    # Inpaint RGB only; preserve any original alpha channel.
    rgba = img.convert("RGBA")
    arr = np.asarray(rgba)
    rgb = arr[:, :, :3].copy()
    alpha = arr[:, :, 3].copy()
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    mask = np.zeros(bgr.shape[:2], dtype=np.uint8)
    x1, y1, x2, y2 = region
    mask[y1:y2, x1:x2] = 255
    method = cv2.INPAINT_TELEA if algorithm == "Telea" else cv2.INPAINT_NS
    cleaned = cv2.inpaint(bgr, mask, float(radius), method)
    rgb_clean = cv2.cvtColor(cleaned, cv2.COLOR_BGR2RGB)
    output = np.dstack((rgb_clean, alpha))
    return Image.fromarray(output, "RGBA")


def encode_image(img: Image.Image, file_name: str) -> tuple[bytes, str, str]:
    suffix = Path(file_name).suffix.lower()
    buf = BytesIO()
    if suffix in {".jpg", ".jpeg"}:
        img.convert("RGB").save(buf, format="JPEG", quality=95, subsampling=0)
        return buf.getvalue(), "jpg", "image/jpeg"
    if suffix == ".webp":
        img.save(buf, format="WEBP", quality=95, method=4)
        return buf.getvalue(), "webp", "image/webp"
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue(), "png", "image/png"


files = st.file_uploader(
    "1. Thả nhiều ảnh vào đây (JPG / PNG / WEBP)",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
)

left, right = st.columns(2)
with left:
    corner = st.selectbox("2. Vị trí logo", ["Dưới phải", "Dưới trái", "Trên phải", "Trên trái"])
    width_pct = st.slider("Chiều rộng vùng cần xóa (% chiều rộng ảnh)", 1.0, 30.0, 7.0, 0.5)
    height_pct = st.slider("Chiều cao vùng cần xóa (% chiều cao ảnh)", 1.0, 30.0, 5.0, 0.5)
with right:
    x_margin_pct = st.slider("Cách mép ngang (%)", 0.0, 20.0, 1.0, 0.5)
    y_margin_pct = st.slider("Cách mép dọc (%)", 0.0, 20.0, 1.0, 0.5)
    algorithm = st.selectbox("Thuật toán làm đầy", ["Telea", "Navier–Stokes"], help="Telea thường phù hợp với nền tương đối đơn giản")
    radius = st.slider("Bán kính làm đầy (pixel)", 1, 15, 3)

if not files:
    st.info("Tải ảnh lên để xem trước vùng xóa và xử lý hàng loạt.")
    st.stop()

st.write(f"**Đã tải lên:** {len(files)} ảnh")

try:
    sample = get_image(files[0].getvalue())
    region = rectangle_for(sample.size, corner, width_pct, height_pct, x_margin_pct, y_margin_pct)
    with st.expander("3. Xem trước ảnh đầu tiên", expanded=True):
        original_preview = sample.convert("RGB")
        overlay = original_preview.copy()
        d = ImageDraw.Draw(overlay)
        d.rectangle(region, outline=(255, 45, 45), width=max(2, round(min(sample.size) / 300)))
        preview_clean = clean_logo(sample, region, radius, algorithm)
        c1, c2 = st.columns(2)
        c1.image(overlay, caption="Vùng đỏ sẽ được xử lý", use_container_width=True)
        c2.image(preview_clean, caption="Kết quả xem trước", use_container_width=True)
        st.caption("Mẹo: Điều chỉnh vùng đỏ vừa đủ bao hết logo. Vùng rộng quá có thể tạo vệt nhòe, nhất là trên họa tiết phức tạp.")
except (UnidentifiedImageError, OSError, ValueError) as exc:
    st.error(f"Không thể đọc ảnh đầu tiên: {exc}")
    st.stop()

if st.button("4. Xử lý tất cả ảnh", type="primary", use_container_width=True):
    output_zip = BytesIO()
    completed: list[tuple[str, bytes, str]] = []
    failed: list[str] = []
    progress = st.progress(0)
    status = st.empty()
    names_seen: dict[str, int] = {}

    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for i, f in enumerate(files, start=1):
            status.text(f"Đang xử lý {i}/{len(files)}: {f.name}")
            try:
                current = get_image(f.getvalue())
                box = rectangle_for(current.size, corner, width_pct, height_pct, x_margin_pct, y_margin_pct)
                result = clean_logo(current, box, radius, algorithm)
                payload, ext, mime = encode_image(result, f.name)
                stem = Path(f.name).stem
                base_name = f"{stem}_cleaned.{ext}"
                index = names_seen.get(base_name, 0)
                names_seen[base_name] = index + 1
                output_name = base_name if index == 0 else f"{stem}_cleaned_{index + 1}.{ext}"
                archive.writestr(output_name, payload)
                completed.append((output_name, payload, mime))
            except Exception as exc:
                failed.append(f"{f.name}: {exc}")
            progress.progress(i / len(files))
    status.empty()
    st.session_state["output_zip"] = output_zip.getvalue()
    st.session_state["completed"] = completed
    st.session_state["failed"] = failed

if "output_zip" in st.session_state:
    st.success(f"Đã xử lý {len(st.session_state['completed'])} ảnh thành công")
    st.download_button(
        "⬇️ Tải tất cả ảnh (ZIP)",
        data=st.session_state["output_zip"],
        file_name="batch_logo_cleaned.zip",
        mime="application/zip",
        type="primary",
        use_container_width=True,
    )
    with st.expander("Tải từng ảnh riêng lẻ"):
        for name, payload, mime in st.session_state["completed"]:
            st.download_button(f"⬇️ {name}", data=payload, file_name=name, mime=mime, key=f"download_{name}")
    if st.session_state["failed"]:
        st.warning("Một số ảnh không xử lý được:\n" + "\n".join(st.session_state["failed"]))

st.divider()
st.caption("Lưu ý: Công cụ thay thế pixel trong vùng bạn khoanh, không nhận diện logo bằng AI. Logo trên nền phức tạp có thể cần chỉnh thủ công. Công cụ không xác minh hoặc thay đổi dấu nguồn gốc vô hình như SynthID.")
