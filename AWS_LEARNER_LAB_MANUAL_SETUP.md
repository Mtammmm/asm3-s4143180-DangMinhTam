# Hướng dẫn thiết lập thủ công CSV Insight trên AWS Learner Lab

Tài liệu này hướng dẫn cấu hình AWS CLI, Docker và tạo thủ công toàn bộ tài nguyên AWS cho backend CSV Insight. Quy trình này **không sử dụng AWS SAM hoặc CloudFormation** và không import `infrastructure/template.yaml`.

## 1. Kiến trúc cần triển khai

```text
Frontend
   |
   v
API Gateway (HTTP API)
   |
   v
Lambda: csv-insight-api
   |---------------------> DynamoDB
   |---------------------> S3

S3 upload bucket
   |
   v
Lambda: csv-insight-upload-event
   |
   v
ECS Fargate task: csv-insight-processor
   |---------------------> S3
   |---------------------> DynamoDB
```

Các tài nguyên được sử dụng:

- AWS IAM `LabRole` có sẵn trong Learner Lab.
- Hai bảng DynamoDB.
- Hai S3 bucket.
- Một ECR repository.
- Một ECS Fargate cluster và task definition.
- Hai Lambda function.
- Một API Gateway HTTP API.
- CloudWatch Logs.

Tất cả tài nguyên phải được tạo trong cùng một region. Tài liệu này sử dụng:

```text
us-east-1
```

## 2. Khởi động AWS Learner Lab

1. Đăng nhập AWS Academy.
2. Mở khóa học có Learner Lab.
3. Chọn **Learner Lab**.
4. Nhấn **Start Lab**.
5. Chờ biểu tượng AWS chuyển sang màu xanh.
6. Nhấn **AWS** để mở AWS Management Console.

Không đóng phiên Learner Lab khi đang cấu hình. Tài nguyên thường được giữ lại giữa các phiên, nhưng credentials sẽ hết hạn khi phiên lab kết thúc.

## 3. Cấu hình AWS CLI

### 3.1 Kiểm tra AWS CLI

Mở PowerShell và chạy:

```powershell
aws --version
```

Nếu lệnh không tồn tại, cài **AWS CLI version 2** từ trang chính thức của AWS rồi mở lại PowerShell.

### 3.2 Lấy temporary credentials

Trong trang Learner Lab:

1. Chọn **AWS Details**.
2. Chọn **Show** bên cạnh mục **AWS CLI**.
3. Sao chép toàn bộ ba giá trị:
   - `aws_access_key_id`
   - `aws_secret_access_key`
   - `aws_session_token`

Mở file credentials:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.aws"
notepad "$env:USERPROFILE\.aws\credentials"
```

Thêm nội dung do Learner Lab cung cấp và đặt tên profile là `learner-lab`:

```ini
[learner-lab]
aws_access_key_id=REPLACE_WITH_ACCESS_KEY
aws_secret_access_key=REPLACE_WITH_SECRET_KEY
aws_session_token=REPLACE_WITH_SESSION_TOKEN
```

Không đưa các giá trị thật vào source code, `.env`, ảnh chụp màn hình hoặc Git.

Thiết lập region và output format:

```powershell
aws configure set region us-east-1 --profile learner-lab
aws configure set output json --profile learner-lab
```

Kiểm tra đăng nhập:

```powershell
aws sts get-caller-identity --profile learner-lab
```

Kết quả hợp lệ phải chứa `Account` và `Arn`. Nếu xuất hiện `ExpiredToken`, khởi động lại lab và cập nhật lại cả ba credential.

Có thể đặt profile cho phiên PowerShell hiện tại:

```powershell
$env:AWS_PROFILE = "learner-lab"
$env:AWS_REGION = "us-east-1"
```

## 4. Cài đặt và kiểm tra Docker

Processor của dự án chạy bằng ECS Fargate, vì vậy cần Docker để build và push image lên ECR. Docker cũng được dùng để tạo Lambda package tương thích Linux.

1. Cài Docker Desktop cho Windows.
2. Bật WSL 2 backend nếu Docker Desktop yêu cầu.
3. Khởi động Docker Desktop.
4. Chờ Docker Engine chạy hoàn tất.

Kiểm tra:

```powershell
docker --version
docker info
```

Nếu `docker info` báo không kết nối được daemon, mở Docker Desktop và chờ đến khi trạng thái là **Running**.

## 5. Quy ước tên tài nguyên

S3 bucket name phải duy nhất trên toàn AWS. Thay `s4143180` nếu tên đã được sử dụng.

| Tài nguyên | Tên đề xuất |
| --- | --- |
| Users table | `CsvInsightUsers` |
| Datasets table | `CsvInsightDatasets` |
| Upload bucket | `csv-insight-upload-s4143180` |
| Avatar bucket | `csv-insight-avatar-s4143180` |
| ECR repository | `csv-insight-processor` |
| ECS cluster | `csv-insight-cluster` |
| ECS task family | `csv-insight-processor` |
| Security group | `csv-insight-processor-sg` |
| API Lambda | `csv-insight-api` |
| Upload-event Lambda | `csv-insight-upload-event` |
| HTTP API | `csv-insight-api` |

Nếu dùng tên khác, phải thay đúng tên đó trong tất cả environment variable liên quan.

## 6. Xác nhận LabRole, VPC và subnet

Learner Lab cung cấp sẵn IAM role tên `LabRole`. Không tạo role mới nếu tài khoản lab không cho phép.

Lấy ARN của role:

```powershell
aws iam get-role `
  --role-name LabRole `
  --query "Role.Arn" `
  --output text `
  --profile learner-lab
```

Output thực tế:

```text
arn:aws:iam::912595911783:role/LabRole
```

Lấy default VPC:

```powershell
aws ec2 describe-vpcs `
  --filters "Name=is-default,Values=true" `
  --query "Vpcs[0].VpcId" `
  --output text `
  --profile learner-lab
```

Output thực tế:

```text
vpc-06c930686c784c547
```

Lấy subnet của default VPC:

```powershell
aws ec2 describe-subnets `
  --filters "Name=vpc-id,Values=vpc-06c930686c784c547" `
  --query "Subnets[].{SubnetId:SubnetId,AZ:AvailabilityZone,PublicIp:MapPublicIpOnLaunch}" `
  --output table `
  --profile learner-lab
```

Output thực tế:

| Availability Zone | Subnet ID | Public IP tự động |
| --- | --- | --- |
| `us-east-1a` | `subnet-0b2c69518884a37cd` | Có |
| `us-east-1b` | `subnet-0ce8958375d7d2083` | Có |
| `us-east-1c` | `subnet-080445287756a736e` | Có |
| `us-east-1d` | `subnet-02ea8117eb1dddbbe` | Có |
| `us-east-1e` | `subnet-054d101f1c34b5588` | Có |
| `us-east-1f` | `subnet-0a2e6905031a7a60f` | Có |

Ba subnet đề xuất cho ECS Fargate, thuộc ba Availability Zone khác nhau:

```text
subnet-0b2c69518884a37cd
subnet-0ce8958375d7d2083
subnet-080445287756a736e
```

Giá trị dùng cho environment variable `ECS_SUBNETS`:

```text
subnet-0b2c69518884a37cd,subnet-0ce8958375d7d2083,subnet-080445287756a736e
```

Các subnet trên sử dụng route mặc định qua Internet Gateway `igw-04d3a361abae04e65`, phù hợp để chạy Fargate với **Assign public IP** được bật.

Ghi lại:

- LabRole ARN: `arn:aws:iam::912595911783:role/LabRole`.
- Default VPC ID: `vpc-06c930686c784c547`.
- ECS subnet IDs: `subnet-0b2c69518884a37cd,subnet-0ce8958375d7d2083,subnet-080445287756a736e`.

## 7. Tạo DynamoDB tables

### 7.1 Tạo bảng người dùng

Trong AWS Console, mở **DynamoDB → Tables → Create table**:

- Table name: `CsvInsightUsers`
- Partition key: `userId`
- Data type: String
- Table settings: Customize settings hoặc giữ mặc định.
- Read/write capacity mode: On-demand.

Sau khi bảng ở trạng thái **Active**:

1. Mở bảng `CsvInsightUsers`.
2. Chọn tab **Indexes**.
3. Chọn **Create index**.
4. Partition key: `email`, kiểu String.
5. Index name: `email-index`.
6. Attribute projections: All.
7. Chọn **Create index**.

Chờ index chuyển sang trạng thái **Active**.

### 7.2 Tạo bảng dataset

Mở **DynamoDB → Tables → Create table**:

- Table name: `CsvInsightDatasets`
- Partition key: `userId`, kiểu String.
- Sort key: `datasetId`, kiểu String.
- Read/write capacity mode: On-demand.

Chờ bảng ở trạng thái **Active**.

## 8. Tạo S3 buckets

Mở **S3 → Create bucket** và tạo bucket upload:

- Bucket name: `csv-insight-upload-s4143180`
- AWS Region: `us-east-1`
- Object Ownership: ACLs disabled.
- Block all public access: bật.
- Bucket versioning: có thể tắt để tiết kiệm tài nguyên lab.

Tạo bucket avatar tương tự:

```text
csv-insight-avatar-s4143180
```

### 8.1 Cấu hình CORS

Với từng bucket, mở **Permissions → Cross-origin resource sharing (CORS) → Edit** và nhập:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "PUT"],
    "AllowedOrigins": ["http://localhost:5500"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 900
  }
]
```

Khi frontend đã được host, thêm URL frontend vào `AllowedOrigins`, ví dụ:

```json
"AllowedOrigins": [
  "http://localhost:5500",
  "https://frontend.example.com"
]
```

Không tắt Block Public Access. Frontend upload và tải file thông qua presigned URL.

### 8.2 Lifecycle rule tùy chọn

Trong upload bucket, mở **Management → Create lifecycle rule**:

- Rule name: `delete-temporary-files`
- Scope: Limit the scope using one or more filters.
- Prefix: `temporary/`
- Expire current versions after: 7 days.

## 9. Tạo ECR repository và push processor image

### 9.1 Tạo repository

Mở **Elastic Container Registry → Private registry → Repositories → Create repository**:

- Visibility: Private.
- Repository name: `csv-insight-processor`.
- Tag immutability: Mutable.
- Scan on push: Enabled.

### 9.2 Build và push image

Từ thư mục gốc của project, chạy:

```powershell
$profile = "learner-lab"
$region = "us-east-1"
$accountId = aws sts get-caller-identity `
  --query Account `
  --output text `
  --profile $profile

$registry = "$accountId.dkr.ecr.$region.amazonaws.com"
$image = "$registry/csv-insight-processor:latest"

aws ecr get-login-password `
  --region $region `
  --profile $profile |
  docker login `
    --username AWS `
    --password-stdin $registry

docker build `
  -t csv-insight-processor `
  backend/processor

docker tag csv-insight-processor:latest $image
docker push $image
```

Kiểm tra trong ECR repository phải thấy image tag `latest`.

## 10. Tạo CloudWatch log group

Mở **CloudWatch → Logs → Log groups → Create log group**:

- Log group name: `/ecs/csv-insight-processor`
- Retention: 7 days.

Lambda log group sẽ được AWS tạo tự động khi function chạy lần đầu.

## 11. Tạo security group cho ECS

Mở **EC2 → Network & Security → Security Groups → Create security group**:

- Security group name: `csv-insight-processor-sg`.
- Description: `Outbound access for CSV processor tasks`.
- VPC: default VPC đã xác định ở bước 6.
- Inbound rules: không cần rule.
- Outbound rules: All traffic đến `0.0.0.0/0`.

Ghi lại security group ID, ví dụ `sg-0123456789abcdef0`.
sg-00ddab535ca919eed
## 12. Tạo ECS Fargate cluster và task definition

### 12.1 Tạo cluster

Mở **ECS → Clusters → Create cluster**:

- Cluster name: `csv-insight-cluster`.
- Infrastructure: AWS Fargate.
- Không cần EC2 Auto Scaling Group.

### 12.2 Tạo task definition

Mở **ECS → Task definitions → Create new task definition**:

- Task definition family: `csv-insight-processor`.
- Launch type: AWS Fargate.
- Operating system/architecture: Linux/x86_64.
- Network mode: `awsvpc`.
- CPU: `0.25 vCPU` hoặc `256 CPU units`.
- Memory: `0.5 GB` hoặc `512 MiB`.
- Task role: `LabRole`.
- Task execution role: `LabRole`.

Thêm container:

- Name: `csv-processor`.
- Image URI: URI đầy đủ của image ECR có tag `latest`.
- Essential container: Yes.
- Port mappings: không cần.

Environment variable:

| Key | Value |
| --- | --- |
| `DATASETS_TABLE` | `CsvInsightDatasets` |
| `AWS_REGION` | `us-east-1` |

Logging:

- Log driver: `awslogs`.
- Log group: `/ecs/csv-insight-processor`.
- Region: `us-east-1`.
- Stream prefix: `processor`.

Không tạo ECS Service. Mỗi lần có CSV mới, Lambda chỉ chạy một Fargate task và task tự kết thúc sau khi xử lý xong.

## 13. Tạo Lambda nhận sự kiện upload S3

### 13.1 Tạo function

Mở **Lambda → Functions → Create function → Author from scratch**:

- Function name: `csv-insight-upload-event`.
- Runtime: Python 3.12.
- Architecture: x86_64.
- Permissions: Use an existing role.
- Existing role: `LabRole`.

Sau khi tạo:

- Memory: 256 MB.
- Timeout: 30 seconds.
- Handler: `handler.handler`.

File function nằm tại:

```text
backend/lambdas/s3_event_handler/handler.py
```

Function này chỉ dùng `boto3`, đã có trong Lambda Python runtime. Có thể copy toàn bộ nội dung file vào Lambda code editor và deploy.

### 13.2 Environment variables

Mở **Configuration → Environment variables → Edit**:

| Key | Value |
| --- | --- |
| `AWS_REGION` | `us-east-1` |
| `DATASETS_TABLE` | `CsvInsightDatasets` |
| `ECS_CLUSTER` | `csv-insight-cluster` |
| `PROCESSOR_TASK_DEFINITION` | `csv-insight-processor` |
| `ECS_SUBNETS` | `subnet-aaa,subnet-bbb` |
| `ECS_SECURITY_GROUP` | Security group ID từ bước 11 |

Không thêm khoảng trắng giữa các subnet trong `ECS_SUBNETS`.

### 13.3 Thêm S3 trigger

Trong trang Lambda function:

1. Chọn **Add trigger**.
2. Source: S3.
3. Bucket: upload bucket.
4. Event type: All object create events.
5. Prefix: `datasets/`.
6. Suffix: `.csv`.
7. Xác nhận recursive invocation warning.
8. Chọn **Add**.

S3 bucket và Lambda phải nằm trong cùng region.

## 14. Build deployment package cho Flask Lambda

Không cài dependency trực tiếp bằng Windows rồi zip, vì `argon2-cffi` có thành phần native và package Windows không tương thích với Lambda Linux.

Tại thư mục gốc project, chạy:

```powershell
New-Item `
  -ItemType Directory `
  -Force `
  backend\.lambda-package

docker run --rm `
  -v "${PWD}\backend:/var/task" `
  -w /var/task `
  --entrypoint pip `
  public.ecr.aws/lambda/python:3.12 `
  install `
    -r requirements.txt `
    -t .lambda-package

Copy-Item `
  backend\app `
  backend\.lambda-package\app `
  -Recurse `
  -Force

Copy-Item `
  backend\lambda_handler.py `
  backend\.lambda-package\lambda_handler.py `
  -Force

Compress-Archive `
  -Path backend\.lambda-package\* `
  -DestinationPath backend\flask-api.zip `
  -Force
```

Trong file ZIP, `lambda_handler.py` và thư mục `app` phải nằm ngay ở root:

```text
flask-api.zip
├── lambda_handler.py
├── app/
├── flask/
├── argon2/
└── ...
```

Không zip thư mục `.lambda-package` thành một thư mục cha bên trong ZIP.

## 15. Tạo Flask API Lambda

Mở **Lambda → Functions → Create function → Author from scratch**:

- Function name: `csv-insight-api`.
- Runtime: Python 3.12.
- Architecture: x86_64.
- Permissions: Use an existing role.
- Existing role: `LabRole`.

Sau khi tạo:

1. Mở tab **Code**.
2. Chọn **Upload from → .zip file**.
3. Upload `backend/flask-api.zip`.
4. Chọn **Save**.

Cấu hình runtime:

- Handler: `lambda_handler.handler`.
- Memory: 512 MB.
- Timeout: 30 seconds.

### 15.1 Tạo JWT secret

Chạy trên máy local:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Giữ kín giá trị được tạo.

### 15.2 Environment variables

Mở **Configuration → Environment variables → Edit**:

| Key | Value |
| --- | --- |
| `STORAGE_BACKEND` | `aws` |
| `AWS_REGION` | `us-east-1` |
| `USERS_TABLE` | `CsvInsightUsers` |
| `DATASETS_TABLE` | `CsvInsightDatasets` |
| `UPLOAD_BUCKET` | Tên upload bucket thật |
| `AVATAR_BUCKET` | Tên avatar bucket thật |
| `JWT_SECRET` | Secret tối thiểu 32 ký tự |
| `JWT_TTL_SECONDS` | `3600` |
| `FRONTEND_ORIGINS` | `http://localhost:5500` |
| `EXPOSE_RESET_TOKEN` | `false` |

Không dùng giá trị JWT mặc định khi deploy thật.

## 16. Tạo API Gateway HTTP API

Mở **API Gateway → APIs → Create API → HTTP API → Build**:

- API name: `csv-insight-api`.
- Integration type: Lambda.
- Lambda function: `csv-insight-api`.
- Payload format version: 2.0.

Tạo routes:

```text
ANY /
ANY /{proxy+}
```

Tạo stage:

- Stage name: `$default`.
- Auto-deploy: Enabled.

### 16.1 CORS

Trong API Gateway, mở **CORS → Configure**:

- Access-Control-Allow-Origin: `http://localhost:5500`.
- Access-Control-Allow-Headers:
  - `Authorization`
  - `Content-Type`
- Access-Control-Allow-Methods:
  - `GET`
  - `POST`
  - `PATCH`
  - `DELETE`
  - `OPTIONS`

Lưu cấu hình. API Gateway sẽ tự thêm quyền invoke Lambda khi integration được tạo qua Console.

Ghi lại Invoke URL, ví dụ:

```text
https://abc123.execute-api.us-east-1.amazonaws.com
```

## 17. Kết nối frontend với API

Mở file:

```text
frontend/config.js
```

Thay URL local bằng API Gateway Invoke URL:

```javascript
window.CSV_INSIGHT_API_URL =
  "https://abc123.execute-api.us-east-1.amazonaws.com";
```

Nếu frontend vẫn chạy local, có thể phục vụ thư mục frontend bằng:

```powershell
python -m http.server 5500 --directory frontend
```

Sau đó mở:

```text
http://localhost:5500
```

## 18. Kiểm tra hệ thống

### 18.1 Health check

```powershell
$apiUrl = "https://abc123.execute-api.us-east-1.amazonaws.com"
Invoke-RestMethod -Uri "$apiUrl/health"
```

### 18.2 Đăng ký tài khoản

```powershell
$body = @{
  email = "demo@example.com"
  password = "DemoPassword123!"
  fullName = "Demo User"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "$apiUrl/auth/register" `
  -ContentType "application/json" `
  -Body $body
```

### 18.3 Kiểm tra luồng upload CSV

1. Đăng nhập từ frontend.
2. Tạo dataset.
3. Frontend nhận presigned S3 URL.
4. Frontend upload CSV trực tiếp lên S3.
5. S3 gọi `csv-insight-upload-event`.
6. Lambda đổi trạng thái dataset thành `processing`.
7. Lambda chạy một ECS Fargate task.
8. Processor đọc CSV và ghi `preview.json` vào S3.
9. Processor cập nhật trạng thái dataset thành `ready`.

## 19. Kiểm tra log và xử lý lỗi

### API trả về HTTP 500

Kiểm tra:

```text
CloudWatch → Log groups → /aws/lambda/csv-insight-api
```

Nguyên nhân thường gặp:

- Sai tên DynamoDB table.
- Sai tên S3 bucket.
- ZIP có sai cấu trúc thư mục.
- Dependency được build trên Windows thay vì Linux.
- `LabRole` thiếu quyền.

### API trả về CORS error

Kiểm tra cả hai nơi:

- API Gateway CORS.
- Environment variable `FRONTEND_ORIGINS` của Flask Lambda.

Origin phải khớp chính xác, bao gồm protocol và port.

### Presigned upload bị AccessDenied

Kiểm tra:

- Upload bucket có đúng tên trong `UPLOAD_BUCKET`.
- `LabRole` có quyền `s3:PutObject`.
- S3 CORS cho phép `PUT` từ frontend origin.
- Content-Type gửi lúc upload khớp Content-Type dùng khi tạo presigned URL.

### S3 upload xong nhưng ECS không chạy

Kiểm tra log:

```text
CloudWatch → Log groups → /aws/lambda/csv-insight-upload-event
```

Sau đó kiểm tra:

- S3 trigger có prefix `datasets/` và suffix `.csv`.
- `ECS_CLUSTER` đúng tên cluster.
- `PROCESSOR_TASK_DEFINITION` đúng task family hoặc ARN.
- `ECS_SUBNETS` không chứa khoảng trắng.
- `ECS_SECURITY_GROUP` chứa security group ID, không phải tên.
- `LabRole` có `ecs:RunTask` và `iam:PassRole`.

### ECS task dừng ngay

Mở:

```text
ECS → Clusters → csv-insight-cluster → Tasks → Stopped
```

Xem `Stopped reason` và log tại:

```text
CloudWatch → Log groups → /ecs/csv-insight-processor
```

Kiểm tra thêm:

- Image ECR tồn tại với tag `latest`.
- Task execution role là `LabRole`.
- Fargate task được cấp public IP.
- Subnet có route `0.0.0.0/0` tới Internet Gateway.
- Security group cho phép outbound traffic.
- Environment variable `DATASETS_TABLE` đúng.

## 20. Cập nhật code sau này

### Cập nhật Flask Lambda

1. Xóa và build lại `backend/.lambda-package` nếu dependency thay đổi.
2. Tạo lại `backend/flask-api.zip`.
3. Upload ZIP mới vào Lambda `csv-insight-api`.
4. Chọn Deploy hoặc Save.

### Cập nhật processor

Build và push lại image:

```powershell
docker build -t csv-insight-processor backend/processor
docker tag csv-insight-processor:latest $image
docker push $image
```

Vì tag `latest` có thể bị ECS cache theo digest của task revision cũ, nên sau khi push:

1. Mở ECS task definition.
2. Chọn **Create new revision**.
3. Giữ nguyên cấu hình và image URI.
4. Tạo revision mới.
5. Nếu `PROCESSOR_TASK_DEFINITION` đang dùng ARN cụ thể, cập nhật Lambda sang revision mới. Nếu dùng family name, ECS sẽ lấy revision active mới nhất.

## 21. Kết thúc phiên Learner Lab an toàn

Khi hoàn tất:

1. Không xóa tài nguyên nếu còn cần cho lần sau.
2. Nhấn **End Lab** để ngừng phiên và tránh tiêu hao lab budget.
3. Lần sau chọn **Start Lab**.
4. Lấy credentials mới.
5. Thay cả ba giá trị trong profile `learner-lab`.
6. Chạy lại:

```powershell
aws sts get-caller-identity --profile learner-lab
```

Không cần tạo lại DynamoDB, S3, ECR, ECS, Lambda hoặc API Gateway nếu các tài nguyên vẫn còn.

## 22. Checklist hoàn thành

- [x] Learner Lab đang chạy.
- [x] AWS CLI profile `learner-lab` hoạt động.
- [x] Docker Desktop đang chạy.
- [x] `CsvInsightUsers` và `email-index` ở trạng thái Active.
- [x] `CsvInsightDatasets` ở trạng thái Active.
- [x] Upload bucket và avatar bucket đã có CORS.
- [x] Processor image đã được push lên ECR.
- [x] ECS cluster và task definition đã được tạo.
- [x] ECS security group cho phép outbound traffic.
- [ ] Upload-event Lambda đã có environment variables và S3 trigger.
- [ ] Flask Lambda đã được upload đúng Linux package.
- [ ] API Gateway có hai route `ANY`.
- [ ] Frontend đã dùng đúng Invoke URL.
- [ ] Health endpoint hoạt động.
- [ ] Có thể đăng ký và đăng nhập.
- [ ] Upload CSV tạo Fargate task.
- [ ] Dataset chuyển từ `processing` sang `ready`.
