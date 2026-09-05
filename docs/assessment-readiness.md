# Đối chiếu Assessment 3 — CSV Insight

Ngày kiểm tra: 05/09/2026. Nguồn: `E:/ASSESSMENT_3_S2-1.pdf`, 7 trang thực tế. Đây là checklist đánh giá, **không thay thế Solution Architecture Document dạng Word/PDF cần nộp**.

## Kết luận

Project phù hợp hướng đề và có triển khai code cho các nhóm dịch vụ yêu cầu. Chưa đủ bằng chứng để xác nhận sẵn sàng nộp: chưa thấy Solution Architecture Document, bộ hồ sơ ZIP đúng cấu trúc, và chưa kiểm chứng được toàn bộ hệ thống AWS đang chạy tự động.

API đang deploy trả HTTP 200 với `/health`. Đây chỉ là kiểm tra API còn phản hồi, không xác nhận DynamoDB, S3, ECS, Glue hoặc Athena hoạt động. Kiểm tra AWS bằng thông tin local bị chặn bởi `ExpiredToken`; không thay đổi AWS resources hay dữ liệu người dùng.

## Các nhóm dịch vụ bắt buộc (đề trang 3)

| Nhóm | Thành phần project | Bằng chứng hiện có | Còn cần xác nhận |
| --- | --- | --- | --- |
| Compute | Lambda API và Lambda nhận S3 event | `backend/api/lambda_handler.py`, `backend/functions/upload_event/handler.py`; API health thành công | Hai Lambda chạy đúng integration và trigger; hai function vẫn chỉ tính một loại Lambda |
| Containers | ECS Fargate CSV processor | Dockerfile, worker, lời gọi `ecs.run_task` tự động | Task được kích hoạt bởi thao tác upload trên UI và hoàn tất thành công |
| Storage | S3 dataset, preview, dữ liệu Athena, avatar | Presigned upload, đọc/ghi/xóa object trong code | Bucket, CORS, permissions và object thực tế; upload avatar chưa được test live |
| Networking and Content Delivery | API Gateway; CloudFront dự kiến phục vụ frontend | API Gateway URL đang trả health; frontend là static site | URL CloudFront, origin S3 và ứng dụng frontend đang public/hoạt động |
| Database | DynamoDB | Users/datasets stores; ownership; metadata updates | Tables, email-index và dữ liệu phát sinh qua UI |
| Analytics | Athena và Glue Data Catalog | API chạy Athena SQL; worker tự đăng ký Glue table | Query engine thực sự là Athena, có kết quả ngoài 100 dòng preview |

Theo cách tính loại dịch vụ ở trang 3, Lambda + API Gateway + ECS là 18 điểm thô; S3 + DynamoDB + CloudFront + Athena là thêm 12; Glue có thể thêm 3 nếu được chấp nhận là sử dụng độc lập, phù hợp và đầy đủ. **30–33 là phép đếm khả năng theo kiến trúc, không phải điểm đã đạt.** Rubric cột `Pts` dành 25 điểm cho phần dịch vụ. Không cộng lặp hai Lambda, nhiều bucket hay container với hạ tầng tự đi kèm. Không mặc định cộng ECR, IAM, SES, CloudWatch hoặc Fargate thành dịch vụ độc lập.

Mọi dịch vụ chỉ được tính đầy đủ nếu được client/code/dịch vụ khác gọi tự động và được giám khảo đánh giá phù hợp. Tạo tài nguyên ban đầu bằng Console/CLI không tự động vi phạm yêu cầu; chạy tay processor hay query Athena để thay cho luồng UI thì chưa đáp ứng.

## Giao diện, phân tích và ý tưởng

- Có giao diện HTML/CSS/JS, upload, preview dạng bảng, thống kê, thư viện và truy vấn. Đề cho phép bảng **và/hoặc** biểu đồ, nên không bắt buộc bổ sung chart chỉ để đáp ứng câu này.
- Có ý tưởng CSV analytics phù hợp nhóm Analytics. Cần trình bày rõ người dùng mục tiêu, giá trị, lý do chọn ECS cho xử lý file và giới hạn hiện tại (10 MB, tối đa 100 dòng kết quả hiển thị).
- Không thể xác nhận từ repo rằng ý tưởng đã được tutor duyệt hoặc có tái sử dụng Assessment 2 hay không. Đề cấm tái sử dụng ứng dụng Assessment 2.
- Third-party API được khuyến khích, không bắt buộc; tối đa hai loại được chấm theo rubric. Chưa thấy tích hợp third-party API và không cần thêm chỉ để đủ số lượng nếu hệ thống hiện tại đã phù hợp.
- Đề không nêu hashing password là tiêu chí riêng. Theo yêu cầu chủ project, mật khẩu vẫn giữ cách lưu hiện tại. README đã được sửa để mô tả đúng, không khẳng định có hashing.
- SES và IAM được đề ghi rõ không cho điểm. Reset password là cải thiện chức năng được yêu cầu trước đó, không phải yêu cầu riêng trong đề.

## Tài liệu kiến trúc (đề trang 4, rubric trang 6–7: 10 điểm)

Chưa tìm thấy tài liệu Word/PDF tương ứng trong repository. README và hướng dẫn deploy không đủ thay thế toàn bộ tài liệu này.

| Mục bắt buộc | Tình trạng |
| --- | --- |
| Links: live frontend URL, repo, dataset public nếu có | Có git remote `https://github.com/Mtammmm/asm3-s4143180-DangMinhTam`; chưa có live frontend URL được kiểm chứng trong hồ sơ |
| Summary (0.5) | README có mô tả ngắn; cần đưa vào tài liệu chính |
| Introduction: motivation, high-level view, beneficiaries (1) | Chưa thấy phần hoàn chỉnh |
| Related work (1) | Chưa thấy so sánh sản phẩm/công trình tương tự kèm nguồn |
| System architecture diagrams (5) | Có sơ đồ text cơ bản trong hướng dẫn; thiếu bộ diagram đầy đủ cho từng thao tác UI, tương tác và chức năng các thành phần |
| System descriptions (1) | Có thông tin rải rác; cần giải thích lựa chọn và vai trò từng dịch vụ |
| Datasets/data structures/APIs (1) | Có API và response shape; cần mô tả keys/index/schema, trạng thái dataset, nguồn dữ liệu mẫu |
| References (0.5) | Chưa có danh mục IEEE đầy đủ cho toàn project; các nguồn AWS dùng cho sửa đổi mới đã được ghi trong code/deployment notes |

Không cần developer manual hoặc user manual theo đề trang 1. Nên dành thời gian cho tài liệu kiến trúc và sơ đồ, không chỉ kéo dài hướng dẫn cài đặt.

## Hồ sơ nộp (đề trang 4–5)

Chưa thấy bộ submission được đóng gói gồm:

- Solution Architecture Document `.docx` hoặc `.pdf`.
- `doc_images/`: tất cả hình dùng trong tài liệu.
- `code/`: source project; nếu source trên 5 MB thì `code.txt` chứa share link theo đề. Cần tính kích thước gói source sạch, không tính `.venv`, `.git`, cache hay credentials.
- `deploy/`: runnable/deployable files nếu có.
- `data/`: dữ liệu/SQL scripts nếu có; nếu trên 5 MB, dùng `data.txt` chứa link.
- ZIP cuối cùng và các link truy cập được với người chấm.

File `.env` hiện được gitignore, nhưng nếu zip thủ công toàn bộ thư mục thì vẫn có thể đưa vào gói nộp. Gói source phải được chọn lọc theo danh sách file cần thiết.

## Demo và điểm chưa thống nhất trong đề

- Trang 1 ghi hạn 23:59 ngày 12/09/2026 và yêu cầu kiểm tra Canvas cho cập nhật. Chưa kiểm tra Canvas.
- Bảng trang 2 ghi demo Week 13; phần Submission trang 5 lại yêu cầu hoàn tất demo Week 12. Cần lấy lịch Canvas/tutor làm xác nhận, không tự chọn một mốc.
- Demo khoảng 30 phút gồm giới thiệu, ứng dụng, tài liệu kiến trúc và Q&A; ứng dụng phải live.
- Rubric ghi `35~0 Pts` trong nội dung hàng dịch vụ nhưng cột `Pts` là 25. Tổng cột `Pts` là 2 + 3 + 25 + 10 = 40. Cần xác nhận cách chấm chính thức với tutor khi tính mục tiêu điểm.

## Kiểm chứng hiện tại và việc còn lại

- Backend: 27 tests pass tại thời điểm lập checklist; gồm unit/API tests và AWS integration **mô phỏng bằng Moto**. Không gọi dịch vụ AWS thật trong các test này.
- Frontend: cú pháp JavaScript đã được kiểm tra. Browser runtime không có trình duyệt khả dụng nên chưa kiểm thử tương tác/visual trực tiếp.
- API đã deploy: `/health` trả 200; phiên bản code live chưa được đối chiếu với các sửa đổi local.
- AWS account/resource inspection: chưa thực hiện được do temporary credentials hết hạn.
- Các sửa đổi local gồm JWT configuration, pipeline có điều kiện/idempotency, POST upload policy, dữ liệu Athena chuẩn hóa, preview S3, local upload hoàn chỉnh, reset UI và tài liệu. Chưa deploy.

Thứ tự ưu tiên trước khi nộp: (1) hoàn thiện Solution Architecture Document và hình; (2) refresh Learner Lab credentials, deploy đồng bộ API/worker/frontend và cấu hình integrations trong `reliability-deployment.md`; (3) demo upload → xử lý → query Athena → delete từ UI và lưu bằng chứng; (4) đóng ZIP đúng cấu trúc; (5) xác nhận lịch demo và điểm chưa thống nhất trên Canvas/tutor.
