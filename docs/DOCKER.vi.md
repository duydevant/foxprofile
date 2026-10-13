# Chạy FoxProfile bằng Docker

## Khởi động

Máy cần Docker Desktop đang chạy với Linux containers. Trong thư mục dự án:

```powershell
docker compose up -d --build
docker compose ps
```

Kiểm thử API, noVNC, MCP và hai browser thực (tạo rồi xóa profile thử riêng):

```powershell
docker compose exec foxprofile python deploy/docker-smoke.py
```

File `.env` đã được tạo cho máy hiện tại, có API token và mật khẩu VNC ngẫu nhiên.
Khi clone sang máy khác, copy `deploy/docker.env.example` thành `.env`, thay
`FOXPROFILE_API_TOKEN` bằng chuỗi ngẫu nhiên từ 24 ký tự trở lên và
`FOXPROFILE_VNC_PASSWORD` bằng mật khẩu đúng 8 ký tự.

- Web panel: http://localhost:8000 — nhập `FOXPROFILE_API_TOKEN` trong `.env`.
- Cửa sổ browser: http://localhost:6080/vnc.html — bấm Connect, nhập
  `FOXPROFILE_VNC_PASSWORD` trong `.env`.
- API docs: http://localhost:8000/docs — dùng Bearer token cho các API cần xác thực.
- MCP: http://localhost:8000/mcp — dùng cùng API token; nút Connect AI trong panel
  tạo cấu hình kết nối.

Camoufox, GeoIP và fingerprint-chromium được tải khi build image, theo
[hướng dẫn cài Camoufox](https://camoufox.com/python/installation/).
Lần build đầu cần Internet và có thể mất vài phút.
Các dependency Docker được cố định trong `deploy/requirements-docker.txt`;
Camoufox được cố định ở `156.0.1-beta.36`, Chrome ở phiên bản do dự án pin.

## Tính năng và cách sử dụng

Giao diện desktop Flet gốc và browser chạy trên desktop Linux 1920×1080
và được điều khiển trực tiếp qua noVNC. REST API và MCP dùng cùng các profile.
Đặt `FOXPROFILE_HEADLESS=false` để nhìn thấy cửa sổ; nếu đổi thành `true` hoặc
`virtual`, browser chạy ẩn và sẽ không xuất hiện trên desktop noVNC.

Container chạy Linux, vì vậy chọn OS **Linux** khi tạo Chrome profile.
Chrome vẫn là engine thử nghiệm theo dự án. Proxy được nhập riêng cho từng
profile; không có proxy thương mại hay tài khoản website được cấp sẵn.
Proxy chạy trên máy Windows phải dùng `host.docker.internal` thay vì `localhost`.
Giao diện desktop Linux xem qua noVNC. Mặc định `FOXPROFILE_MODE=desktop`;
đổi thành `server` trong `.env` nếu chỉ cần web panel, API và MCP.
Client desktop được cài sẵn theo [hướng dẫn Flet](https://flet.dev/docs/getting-started/installation/).

Container chạy bằng user thường. Compose cho phép các syscall cần cho sandbox
Chromium bằng `seccomp=unconfined`; không dùng privileged mode. Hai cổng mặc định
chỉ bind vào `127.0.0.1` của máy chủ. Nếu cần truy cập từ xa, dùng VPN hoặc
reverse proxy có HTTPS và xác thực.

## Dữ liệu, nhập và xuất

Named volume `foxprofile_foxprofile_data` giữ danh sách profile, cookie,
fingerprint, lịch sử tab và log qua các lần restart/rebuild.
Container không tự nhập dữ liệu từ bản chạy native có sẵn trên máy.

Thư mục `docker-data/exchange` trên máy được mount thành `/data/exchange`.
Khi xuất ZIP, dùng đường dẫn `/data/exchange` để nhận file trên máy Windows.
Khi nhập ZIP, copy file vào `docker-data/exchange` rồi nhập đường dẫn container,
ví dụ `/data/exchange/my-profile.zip`.

Nếu đổi cổng, sửa `FOXPROFILE_HTTP_PORT` hoặc `FOXPROFILE_NOVNC_PORT` trong `.env`
và chạy lại `docker compose up -d`. Cổng nội bộ API vẫn là 8000.

```powershell
# Xem log
docker compose logs --tail=100 -f
# Dừng (giữ dữ liệu)
docker compose down
# Chạy lại
docker compose up -d
# Cập nhật sau khi sửa code
docker compose up -d --build
```

`docker compose down -v` sẽ xóa volume và toàn bộ profile/cookie đã lưu.
Không dùng lệnh này nếu muốn giữ dữ liệu. File `.env` và `docker-data` được
git-ignore; `.env` cũng bị loại khỏi Docker build context.

## Kết quả kiểm tra cấu hình này

Ngày 2026-10-13: container `healthy`; 265 test chính và 198 test Chrome đã qua,
3 test được skip theo điều kiện của bộ test. Smoke test xác minh hai browser
thực, điều khiển trang, screenshot, cookie, fingerprint, ZIP export/import,
API authentication và MCP (28 tools). noVNC đã được kiểm tra kết nối WebSocket,
mật khẩu và ảnh desktop. Profile, cookie và fingerprint vẫn giữ nguyên sau
khi recreate container. Đã sửa lỗi ZIP export trên Linux do symlink lock browser.
