# CSV Insight frontend

Frontend MVP viết bằng HTML, CSS và JavaScript thuần.

## Chạy cục bộ

Mở `index.html` trực tiếp trong trình duyệt hoặc chạy static server:

```bash
python -m http.server 5500 --directory frontend
```

Sau đó truy cập `http://localhost:5500`.

## Tích hợp Flask sau này

Hiện tại CSV được đọc trong trình duyệt để giao diện có thể hoạt động độc lập. Khi backend sẵn sàng, thay phần `FileReader` trong `handleFile()` bằng `fetch()` gửi `FormData` đến endpoint Flask, ví dụ `POST /api/upload`.
