# VRPTW Research v2 — Research prototype

## Mục tiêu
Thực nghiệm bài toán định tuyến xe có cửa sổ thời gian (VRPTW) với các baseline Greedy nearest-neighbor, Clarke–Wright Savings có kiểm tra khả thi và OR-Tools Guided Local Search. **Đây là prototype nghiên cứu, không phải ứng dụng giao hàng thực tế và không khẳng định tối ưu toàn cục.**

## Cài đặt Windows (PowerShell)
```powershell
cd VRPTW_Research_v2
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```
Nếu PowerShell chặn activate, dùng `.venv\Scripts\python.exe` thay `python` trong lệnh.

## Chạy ví dụ 8 khách
```powershell
python src/experiment.py --input data/sample.csv --vehicles 3 --capacity 80 --travel-scale 3 --seconds 10 --output outputs/demo.json
```
Dữ liệu này là **giả lập**, khoảng cách Euclid theo đơn vị tọa độ, không phải km thực tế. `--travel-scale 3` có nghĩa 3 phút trên một đơn vị khoảng cách. `data/example.csv` là dữ liệu giả lập lớn hơn, có 20 khách để so sánh ba thuật toán.

## Mở giao diện trực quan
Để mở nhanh trên Windows, bấm đúp `Start_VRPTW.bat` ở thư mục dự án. File này tự kiểm tra Python 3.9+ và OR-Tools trước khi mở launcher; nếu thiếu thành phần, nó sẽ chỉ rõ hướng dẫn cài đặt. Cài đặt lần đầu trong PowerShell bằng:
```powershell
py -3 -m pip install -r requirements.txt
```
Hoặc chạy trực tiếp launcher từ PowerShell:
```powershell
py -3 src/launcher.py
```
Trong giao diện, chọn file CSV hoặc Solomon `.txt`, chỉnh thông số rồi nhấn **Chạy so sánh**. Launcher hiển thị bảng trạng thái/khoảng cách/thời gian cho Greedy, Clarke–Wright và OR-Tools, chi tiết tuyến, và sơ đồ tuyến đường; kết quả được lưu ở `outputs/launcher/`. Với Solomon, số xe và tải trọng được lấy từ header file.

## Dataset Solomon chính thức
Tải bộ Solomon VRPTW từ nguồn học thuật: https://www.sintef.no/projectweb/top/vrptw/solomon-benchmark/ (trang thông tin benchmark và liên kết dữ liệu). Đặt các file instance `.txt` như `C101.txt`, `R101.txt`, `RC101.txt` vào `data/solomon/`. Không được đổi format gốc. File `data/examples/solomon_format_example.txt` chỉ để kiểm thử parser, KHÔNG phải Solomon chính thức.

```powershell
python src/experiment.py --input data/solomon/C101.txt --seconds 30 --output outputs/C101.json
python src/batch.py --dataset-dir data/solomon --seconds 30 --repeats 1 --output-dir outputs/batch
python src/plot_results.py --csv outputs/batch/summary.csv --output outputs/batch/distance.png
```
`batch.py` tự lấy số xe và tải trọng từ header Solomon. Dùng `--limit 25` chỉ để kiểm tra nhanh, không báo cáo là kết quả full instance.

## Ý nghĩa file
- `src/experiment.py`: đọc CSV/Solomon, tạo ma trận, các baseline Greedy và Clarke–Wright, OR-Tools, kiểm tra độc lập lời giải và lưu JSON.
- `src/batch.py`: chạy nhiều instance, xuất `summary.csv` (mỗi hàng = 1 thuật toán trên 1 instance/lần lặp).
- `src/plot_results.py`: biểu đồ khoảng cách trên những lần chạy hợp lệ; không coi lỗi là quãng đường 0.
- `tests/`: kiểm tra parser, tính khả thi, trường hợp sai ràng buộc.
- `src/legacy_solver.py`: mã gốc để đối chiếu.
- `Bao_cao_nghien_cuu_VRPTW.docx`: phân tích và kế hoạch nghiên cứu.

## Giới hạn / lưu ý khoa học
1. Greedy không tìm được lời giải KHÔNG chứng minh instance vô nghiệm.
2. OR-Tools có thể không tìm được lời giải trong time limit; đó KHÔNG chứng minh vô nghiệm.
3. `seed` lưu metadata để hỗ trợ quản lý thực nghiệm, **chưa cấu hình seed cho OR-Tools Routing**; không dùng để tuyên bố thực nghiệm ngẫu nhiên có kiểm soát.
4. Mục tiêu OR-Tools hiện là tối thiểu tổng khoảng cách; không ưu tiên tối thiểu số xe. Khi so sánh best-known solutions (thường tối ưu theo số xe trước), cần điều chỉnh hàm mục tiêu và quy tắc đo khoảng cách.
5. Ma trận khoảng cách là Euclid; thời gian đi được làm tròn lên thành số nguyên. Kiểm tra đúng chuẩn đánh giá của bộ Solomon được chọn trước khi đối chiếu bảng chuẩn.
6. `repeats` không tạo seed khác nhau trong OR-Tools hiện tại; dùng để kiểm tra độ ổn định môi trường, không phải thí nghiệm nhiều seed độc lập.
7. Không có traffic, đường thực tế, nhiều kho, tải xe hỗn hợp hoặc tái tối ưu trực tuyến.
8. Nếu không cài OR-Tools, chương trình ghi `dependency_missing`, không giả mạo kết quả.

## Kế hoạch đề xuất
Tuần 1: đọc 5–8 bài báo và định nghĩa VRPTW. Tuần 2: dữ liệu Solomon, parser và kiểm thử. Tuần 3: baseline và kiểm chứng. Tuần 4: chạy toàn bộ nhóm C/R/RC và lập bảng. Tuần 5: phân tích khoảng trống nghiên cứu và chọn cải tiến. Tuần 6: báo cáo và slide.
