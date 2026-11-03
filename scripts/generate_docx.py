"""
Script sinh file Word (.docx) chuẩn để tải lên Google Docs cho Smart Hydroponics Farm.
Định dạng chuyên nghiệp: Tiêu đề lớn, Bảng biểu màu sắc, Danh sách kiểm tra Điều 7.2 Thể lệ.
"""

import os
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tcPr.append(shd)

def create_document():
    doc = Document()

    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # 1. TIÊU ĐỀ CHÍNH
    title_p = doc.add_paragraph()
    title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = title_p.add_run("BÁO CÁO ĐẶC TẢ CHI TIẾT DỰ ÁN\nSMART HYDROPONICS REAL-TIME OPERATIONS")
    run_title.font.name = "Arial"
    run_title.font.size = Pt(22)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(0, 104, 74) # Forest Green

    sub_p = doc.add_paragraph()
    sub_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = sub_p.add_run("Cuộc thi: MongoDB User Group Vietnam Hackathon 2026 (MongoDB × Datadog)\nChủ đề: Real-time Operations • Lĩnh vực: Nông nghiệp Đô thị Thông minh (AgriTech & ESG)")
    run_sub.font.name = "Arial"
    run_sub.font.size = Pt(11)
    run_sub.font.italic = True
    run_sub.font.color.rgb = RGBColor(100, 116, 139)

    doc.add_paragraph()

    # 2. PHẦN 1: MỤC ĐÍCH & BỐI CẢNH
    h1 = doc.add_heading("1. Mục đích Dự án & Bối cảnh Thực tế", level=1)
    h1.runs[0].font.color.rgb = RGBColor(0, 104, 74)

    p = doc.add_paragraph(
        "Mô hình trồng rau thủy canh hồi lưu (NFT / Vertical Farming) tại các đô thị đang phát triển mạnh mẽ nhằm cung cấp rau sạch tự cung tự cấp. "
        "Tuy nhiên, hai rủi ro sinh hóa thường xuyên xảy ra nhưng rất khó phát hiện kịp thời:"
    )
    p.runs[0].font.size = Pt(10.5)

    bullets = [
        ("Tắc nghẽn rễ & cặn đường ống hồi lưu: ", "Rễ xà lách phát triển quá rậm rạp làm nghẹt ống dẫn dinh dưỡng. Lưu lượng tuần hoàn tụt dốc, nước trong bồn rễ cạn kiệt chỉ sau vài giờ."),
        ("Kiềm hóa dung dịch & Khóa dinh dưỡng (Nutrient Lockout): ", "Nước ngừng tuần hoàn khiến nồng độ pH vọt lên trên 8.0, rễ cây bị cháy và không thể hấp thụ khoáng chất, dẫn đến mất trắng giàn rau tiền triệu.")
    ]
    for b_title, b_desc in bullets:
        bp = doc.add_paragraph(style='List Bullet')
        r1 = bp.add_run(b_title)
        r1.font.bold = True
        r2 = bp.add_run(b_desc)

    p_goal = doc.add_paragraph(
        "Mục tiêu cốt lõi của dự án là xây dựng hệ sinh thái IoT thông minh giúp: "
        "(1) Tự động phát hiện nghẹt ống và kiềm hóa pH trước khi cây héo, "
        "(2) Điều tra chính xác nguyên nhân qua dữ liệu đa chiều Datadog & MongoDB Window Functions, và "
        "(3) Tự động kích hoạt van xả ngược áp lực cao và bơm pH-Down đưa hệ thống về trạng thái lý tưởng."
    )
    p_goal.runs[0].font.italic = True

    # 3. PHẦN 2: CHỨC NĂNG CHI TIẾT
    h2 = doc.add_heading("2. Các Chức năng Chi tiết của Hệ thống", level=1)
    h2.runs[0].font.color.rgb = RGBColor(0, 104, 74)

    features = [
        ("Thu thập Telemetry Thủy canh Tốc độ Cao (Batch Ingestion)",
         "Cảm biến tại các giàn định kỳ gửi gói dữ liệu mỗi 2 giây gồm: độ pH, nồng độ EC (ppm), lưu lượng bơm (LPM), mực nước bồn chứa (%), nhiệt độ nước (°C). "
         "Backend tiếp nhận và ghi hàng loạt bằng lệnh insert_many(ordered=False) vào MongoDB Time Series."),
        ("Phát hiện Sự cố Tức thời (Real-time Anomaly Detection)",
         "Hệ thống liên tục kiểm tra ngưỡng an toàn: Nếu lưu lượng bơm < 1.0 LPM hoặc pH > 7.6, hệ thống tự động gắn cờ sự cố, bắn Log lỗi [FARM_ALERT] và gửi Event khẩn cấp sang Datadog."),
        ("Bảng điều khiển Vận hành Nông trại (Fleet Operations Dashboard)",
         "Cung cấp 2 màn hình quan sát: (1) Datadog Dashboard đo lường độ trễ p95, throughput và phân bố pH; (2) Web UI tích hợp tại localhost:8000 hiển thị thẻ trực quan 3 giàn thủy canh và biểu đồ đa trục real-time."),
        ("Phân tích Xu hướng Bằng MongoDB Window Functions",
         "Sử dụng toán tử $setWindowFields tính toán Moving Average (trung bình trượt) 5 mẫu gần nhất của lưu lượng nước và độ pH, giúp bắt sớm xu hướng nghẹt rễ cây."),
        ("Cơ chế Phản ứng & Khắc phục Sự cố (Incident Mitigation API)",
         "Endpoint /api/incident/respond cho phép kích hoạt chu trình xả ngược áp lực cao (Reverse Pulse Flush) và châm pH-Down, lưu nhật ký khắc phục vào MongoDB collection 'incidents' và phục hồi trạng thái trên Datadog.")
    ]
    for ft_title, ft_desc in features:
        fp = doc.add_paragraph(style='List Bullet')
        r1 = fp.add_run(ft_title + ": ")
        r1.font.bold = True
        r2 = fp.add_run(ft_desc)

    # 4. PHẦN 3: KIẾN TRÚC KỸ THUẬT & CÁCH THỨC THỰC HIỆN
    h3 = doc.add_heading("3. Kiến trúc Kỹ thuật & Triển khai", level=1)
    h3.runs[0].font.color.rgb = RGBColor(0, 104, 74)

    table = doc.add_table(rows=1, cols=3)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Thành phần"
    hdr_cells[1].text = "Công nghệ / Nền tảng"
    hdr_cells[2].text = "Vai trò & Kỹ thuật áp dụng"
    for cell in hdr_cells:
        set_cell_background(cell, "001E2B")
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)

    tech_stack = [
        ("Operational Database", "MongoDB Atlas (Free M0)", "Time Series Collection 'hydroponic_telemetry' (granularity: seconds), TTL Index 7 ngày (expireAfterSeconds: 604800), Aggregation Pipeline ($match, $dateTrunc, $setWindowFields)."),
        ("Observability Platform", "Datadog Cloud", "Dashboard thời gian thực (LPM, pH, EC), Log Management Injection (trace_id), APM Distributed Tracing, Alert Monitors."),
        ("Backend Ingestion API", "Python 3.12, FastAPI, ddtrace", "Xử lý batch bất đồng bộ, middleware CORS, tích hợp Datadog REST API v1/v2."),
        ("AgriTech Edge Simulation", "Python Requests Simulator", "Mô phỏng dữ liệu ngẫu nhiên của 3 giàn thủy canh, hỗ trợ cờ --fault và --resolve phục vụ demo.")
    ]
    for comp, tech, role in tech_stack:
        row_cells = table.add_row().cells
        row_cells[0].text = comp
        row_cells[1].text = tech
        row_cells[2].text = role
        set_cell_background(row_cells[0], "F1F5F9")

    doc.add_paragraph()

    # 5. PHẦN 4: HƯỚNG DẪN KẾT NỐI VÀ CHẠY
    h4 = doc.add_heading("4. Hướng dẫn Kết nối & Các Bước Thực thi", level=1)
    h4.runs[0].font.color.rgb = RGBColor(0, 104, 74)

    steps = [
        ("Bước 1: Cấu hình biến môi trường (.env)",
         "Tạo file .env tại thư mục gốc với MONGODB_URI (từ cụm Atlas) và DD_API_KEY (từ Datadog Organization Settings)."),
        ("Bước 2: Cài đặt thư viện Python",
         "Chạy: pip install -r backend/requirements.txt để cài FastAPI, PyMongo, Pydantic, ddtrace, requests."),
        ("Bước 3: Khởi tạo Cụm MongoDB Time Series",
         "Chạy lệnh: python scripts/setup_mongo.py để tự động tạo collection hydroponic_telemetry, thiết lập TTL 7 ngày và khởi tạo dữ liệu mẫu."),
        ("Bước 4: Kiểm tra kết nối Datadog",
         "Chạy lệnh: python scripts/test_datadog.py để bắn 1 metric và 1 event thử nghiệm lên Event Stream của Datadog."),
        ("Bước 5: Khởi động Backend & Simulator",
         "Khởi động API: cd backend && uvicorn app.main:app --reload\nKhởi động Simulator: python simulator/sensor_simulator.py"),
        ("Bước 6: Trình diễn Kịch bản Sự cố (Detect -> Investigate -> Respond)",
         "Gây lỗi: python scripts/trigger_incident.py --fault (Lưu lượng tụt về 0.3 LPM, pH vọt 8.2, Datadog nổ Alert đỏ)\nKhắc phục: python scripts/trigger_incident.py --resolve (Xả ngược, lưu lượng phục hồi 4.5 LPM, pH về 6.1, Datadog chuyển xanh).")
    ]
    for s_title, s_desc in steps:
        p_step = doc.add_paragraph()
        r1 = p_step.add_run(s_title + "\n")
        r1.font.bold = True
        r2 = p_step.add_run(s_desc)
        r2.font.color.rgb = RGBColor(51, 65, 85)

    # 6. PHẦN 5: BẢNG CHECKLIST NỘP BÀI THEO ĐIỀU 7.2
    h5 = doc.add_heading("5. Bảng Checklist Hồ sơ Nộp bài (Điều 7.2 Thể lệ)", level=1)
    h5.runs[0].font.color.rgb = RGBColor(0, 104, 74)

    chk_table = doc.add_table(rows=1, cols=3)
    chk_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_hdr = chk_table.rows[0].cells
    c_hdr[0].text = "Hạng mục Hồ sơ"
    c_hdr[1].text = "Vị trí trong Repository"
    c_hdr[2].text = "Trạng thái"
    for cell in c_hdr:
        set_cell_background(cell, "001E2B")
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.color.rgb = RGBColor(255, 255, 255)

    checklist_items = [
        ("Tên dự án & Mô tả bài toán", "README.md (Mục 1)", "Đã hoàn thành"),
        ("Thông tin đội thi", "README.md (Mục 2)", "Cần điền tên đội & email"),
        ("Kiến trúc giải pháp", "docs/ARCHITECTURE.md", "Đã hoàn thành (kèm sơ đồ)"),
        ("Kiến trúc dữ liệu MongoDB", "docs/MONGODB_MODEL.md", "Đã hoàn thành (Time Series & Aggregation)"),
        ("Kiến trúc Observability Datadog", "docs/DATADOG_SETUP.md", "Đã hoàn thành (Dashboard & Monitors)"),
        ("Mã nguồn & Hướng dẫn cài đặt", "README.md & thư mục backend/, simulator/", "Đã hoàn thành"),
        ("MVP chạy được / Demo trực quan", "localhost:8000 (Web UI Dashboard)", "Đã hoàn thành"),
        ("Kịch bản sự cố thực tế", "docs/INCIDENT_SCENARIO.md", "Đã hoàn thành (Kịch bản 3 phút)"),
        ("Slide thuyết trình chung kết", "docs/PRESENTATION_SLIDES.md", "Đã hoàn thành (8 slide chi tiết)"),
        ("Video demo (3 phút)", "Link YouTube / Google Drive", "Bạn quay theo kịch bản có sẵn")
    ]
    for item, loc, stat in checklist_items:
        row = chk_table.add_row().cells
        row[0].text = item
        row[1].text = loc
        row[2].text = stat
        if stat == "Đã hoàn thành":
            set_cell_background(row[2], "DCFCE7")

    output_path = "F:/Project nghịch linh tinh/mug-hackathon-2026-iot/docs/Smart_Hydroponics_Realtime_Operations_Full_Spec.docx"
    doc.save(output_path)
    print("Document created successfully at docs/Smart_Hydroponics_Realtime_Operations_Full_Spec.docx")

if __name__ == "__main__":
    create_document()
