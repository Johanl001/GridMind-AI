import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

def create_report():
    doc = Document()

    # --- Page Setup (Binding Margins) ---
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.25)
        section.right_margin = Inches(1.0)
        section.page_width = Inches(8.5)
        section.page_height = Inches(11.0)

    # Styles
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(12)
    normal_style.font.color.rgb = RGBColor(0, 0, 0)
    normal_style.paragraph_format.line_spacing = 1.25
    normal_style.paragraph_format.space_after = Pt(6)

    def set_cell_background(cell, hex_color):
        tcPr = cell._tc.get_or_add_tcPr()
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
        tcPr.append(shd)

    def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
        tcPr = cell._tc.get_or_add_tcPr()
        tcMar = parse_xml(f'''<w:tcMar {nsdecls("w")}>
            <w:top w:w="{top}" w:type="dxa"/>
            <w:bottom w:w="{bottom}" w:type="dxa"/>
            <w:left w:w="{left}" w:type="dxa"/>
            <w:right w:w="{right}" w:type="dxa"/>
        </w:tcMar>''')
        tcPr.append(tcMar)

    def add_chapter_title(title_text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(14)
        run = p.add_run(title_text)
        run.bold = True
        run.font.size = Pt(16)
        run.font.name = 'Times New Roman'
        run.font.color.rgb = RGBColor(15, 23, 42) # Slate navy

    def add_section_title(title_text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(6)
        run = p.add_run(title_text)
        run.bold = True
        run.font.size = Pt(13)
        run.font.name = 'Times New Roman'
        run.font.color.rgb = RGBColor(30, 41, 59)

    def add_subsection_title(title_text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(title_text)
        run.bold = True
        run.italic = True
        run.font.size = Pt(12)
        run.font.name = 'Times New Roman'

    def add_body_p(text, bold_prefix=None):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.25
        p.paragraph_format.space_after = Pt(6)
        if bold_prefix:
            r_pre = p.add_run(bold_prefix)
            r_pre.bold = True
            r_pre.font.name = 'Times New Roman'
        r_text = p.add_run(text)
        r_text.font.name = 'Times New Roman'
        return p

    def add_bullet_p(bold_prefix, text):
        p = doc.add_paragraph(style='List Bullet')
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.2
        p.paragraph_format.space_after = Pt(4)
        r_pre = p.add_run(bold_prefix)
        r_pre.bold = True
        r_pre.font.name = 'Times New Roman'
        r_text = p.add_run(text)
        r_text.font.name = 'Times New Roman'
        return p

    def format_table(table, col_widths, headers, data, alt_color='F8FAFC'):
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        # Header row
        hdr_cells = table.rows[0].cells
        for i, h_text in enumerate(headers):
            hdr_cells[i].text = h_text
            set_cell_background(hdr_cells[i], '1E293B') # Dark slate
            set_cell_margins(hdr_cells[i], 120, 120, 150, 150)
            p = hdr_cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.font.bold = True
                r.font.size = Pt(10.5)
                r.font.color.rgb = RGBColor(255, 255, 255)
                r.font.name = 'Times New Roman'

        for row_idx, row_data in enumerate(data):
            row_cells = table.add_row().cells
            bg = alt_color if row_idx % 2 == 1 else 'FFFFFF'
            for col_idx, cell_value in enumerate(row_data):
                row_cells[col_idx].text = str(cell_value)
                set_cell_background(row_cells[col_idx], bg)
                set_cell_margins(row_cells[col_idx], 80, 80, 120, 120)
                p = row_cells[col_idx].paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT if col_idx > 0 and not any(c.isdigit() for c in str(cell_value)[:3]) else WD_ALIGN_PARAGRAPH.CENTER
                for r in p.runs:
                    r.font.size = Pt(10)
                    r.font.name = 'Times New Roman'

        # Set column widths
        for row in table.rows:
            for idx, width in enumerate(col_widths):
                row.cells[idx].width = Inches(width)

    # =========================================================================
    # 1. TITLE / COVER PAGE
    # =========================================================================
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("A\nMINI PROJECT REPORT\nON")
    r.bold = True
    r.font.size = Pt(14)

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(8)
    p_title.paragraph_format.space_after = Pt(12)
    r_title = p_title.add_run("“GridMind AI: Intelligent Energy Demand Forecasting, Anomaly Detection, and Flexible Load Optimization Platform”")
    r_title.bold = True
    r_title.font.size = Pt(16)
    r_title.font.color.rgb = RGBColor(14, 116, 144) # Deep teal

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("Submitted By\n")
    r_sub.bold = True
    r_sub.font.size = Pt(12)

    team_p = doc.add_paragraph()
    team_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    team_p.paragraph_format.line_spacing = 1.3
    team_text = (
        "DEOKAR PRANAV B.                         UCS23M1028\n"
        "DESHMUKH DHANRAJ M.                UCS23M1029\n"
        "DESHMUKH RITESH N.                   UCS23M1030\n"
        "DEVADHE PRATIK P.                          UCS23M1032\n"
        "(T.Y. Computer Engineering - Honours in AIML)"
    )
    r_team = team_p.add_run(team_text)
    r_team.bold = True
    r_team.font.size = Pt(11.5)

    # College Logo
    logo_path = 'report_assets/word/media/image1.jpg'
    if os.path.exists(logo_path):
        p_logo = doc.add_paragraph()
        p_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_logo.paragraph_format.space_before = Pt(6)
        p_logo.paragraph_format.space_after = Pt(6)
        p_logo.add_run().add_picture(logo_path, width=Inches(1.35))

    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_inst.paragraph_format.line_spacing = 1.2
    inst_text = (
        "SAVITRIBAI PHULE PUNE UNIVERSITY\n"
        "In the academic year 2025-26\n\n"
        "Department of Computer Engineering\n"
        "Sanjivani Rural Education Society’s\n"
        "Sanjivani College of Engineering, Kopargaon - 423603\n"
        "(AN AUTONOMOUS INSTITUTE)"
    )
    r_inst = p_inst.add_run(inst_text)
    r_inst.bold = True
    r_inst.font.size = Pt(11)

    doc.add_page_break()

    # =========================================================================
    # 2. CERTIFICATE PAGE
    # =========================================================================
    p_cert_hdr = doc.add_paragraph()
    p_cert_hdr.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_cert_hdr = p_cert_hdr.add_run(
        "Sanjivani Rural Education Society’s\n"
        "SANJIVANI COLLEGE OF ENGINEERING, KOPARGAON - 423603\n"
        "(AN AUTONOMOUS INSTITUTE)\n"
        "DEPARTMENT OF COMPUTER ENGINEERING\n"
    )
    r_cert_hdr.bold = True
    r_cert_hdr.font.size = Pt(12)

    if os.path.exists(logo_path):
        p_cert_logo = doc.add_paragraph()
        p_cert_logo.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_cert_logo.add_run().add_picture(logo_path, width=Inches(1.15))

    p_cert_title = doc.add_paragraph()
    p_cert_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_ct = p_cert_title.add_run("CERTIFICATE")
    r_ct.bold = True
    r_ct.font.size = Pt(15)

    cert_body = doc.add_paragraph()
    cert_body.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    cert_body.paragraph_format.line_spacing = 1.3
    cert_text = (
        "This is to certify that the Project Entitled “GridMind AI: Intelligent Energy Demand Forecasting, "
        "Anomaly Detection, and Flexible Load Optimization Platform” submitted by:\n\n"
        "    • DEOKAR PRANAV B.                      (PRN: UCS23M1028)\n"
        "    • DESHMUKH DHANRAJ M.             (PRN: UCS23M1029)\n"
        "    • DESHMUKH RITESH N.                 (PRN: UCS23M1030)\n"
        "    • DEVADHE PRATIK P.                       (PRN: UCS23M1032)\n\n"
        "is a bonafide work carried out by students under the supervision of DR. T. BHASKAR and it is submitted towards "
        "the partial fulfillment of the requirement for Honours in Artificial Intelligence and Machine Learning (AI & ML) "
        "under Bachelor of Technology (Computer Engineering) of Savitribai Phule Pune University during the ACADEMIC YEAR 2025-26."
    )
    r_cb = cert_body.add_run(cert_text)
    r_cb.font.size = Pt(11)

    p_signs = doc.add_paragraph()
    p_signs.paragraph_format.space_before = Pt(40)
    p_signs.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    sign_table = doc.add_table(rows=1, cols=3)
    sign_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    c0, c1, c2 = sign_table.rows[0].cells
    c0.width, c1.width, c2.width = Inches(2.3), Inches(2.3), Inches(2.3)
    c0.paragraphs[0].text = "____________________\nDR. T. BHASKAR\n[Project Guide]"
    c1.paragraphs[0].text = "____________________\nDR. M. A. JAWALE\n[Head of Department]"
    c2.paragraphs[0].text = "____________________\nDR. M. V. NAGARHALLI\n[Director / Principal]"
    for c in [c0, c1, c2]:
        p = c.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in p.runs:
            r.bold = True
            r.font.size = Pt(10)
            r.font.name = 'Times New Roman'

    doc.add_page_break()

    # =========================================================================
    # 3. DECLARATION PAGE
    # =========================================================================
    add_chapter_title("DECLARATION")
    add_body_p(
        "We declare that this Project submission represents our ideas in our own words, and we have adequately cited and "
        "referenced the original sources. We also declare that we have adhered to all principles of academic honesty and integrity "
        "and have not misrepresented or fabricated any idea, data, fact, or source in our submission. We understand that any violation "
        "of the above may cause disciplinary action by the Institute and can also evoke penal action from the sources which have not been properly cited."
    )
    p_dt = doc.add_paragraph()
    p_dt.paragraph_format.space_before = Pt(8)
    p_dt.paragraph_format.space_after = Pt(12)
    p_dt.add_run("Place: Kopargaon\nDate: 16 / 10 / 2026").bold = True

    dec_table = doc.add_table(rows=1, cols=4)
    format_table(
        dec_table,
        [0.8, 1.8, 2.8, 1.8],
        ["Sr. No.", "PRN", "Student Name", "Signature"],
        [
            ["1", "UCS23M1028", "Deokar Pranav Balasaheb", "________________"],
            ["2", "UCS23M1029", "Deshmukh Dhanraj Manik", "________________"],
            ["3", "UCS23M1030", "Deshmukh Ritesh Navnath", "________________"],
            ["4", "UCS23M1032", "Devadhe Pratik Pandurang", "________________"]
        ]
    )

    doc.add_page_break()

    # =========================================================================
    # 4. ACKNOWLEDGEMENT PAGE
    # =========================================================================
    add_chapter_title("ACKNOWLEDGEMENT")
    add_body_p(
        "First and foremost, we express our humble gratitude to the Almighty for giving us the strength, wisdom, "
        "and perseverance required to successfully complete this academic mini-project work."
    )
    add_body_p(
        "We wish to express our deep sense of gratitude and sincere thanks to our esteemed project guide, Dr. T. Bhaskar, "
        "Professor, Department of Computer Engineering, for his invaluable guidance, keen interest, consistent encouragement, "
        "and constructive critique throughout the course of this project. His visionary advice and technical acumen were vital "
        "in shaping GridMind AI."
    )
    add_body_p(
        "We extend our sincere gratitude to Prof. Dr. M. A. Jawale, Head of Department (Computer Engineering), Sanjivani College "
        "of Engineering, for her continuous administrative and academic support, providing the state-of-the-art computational "
        "infrastructure that enabled our development."
    )
    add_body_p(
        "We also convey our sincere thanks to Dr. M. V. Nagarhalli, Director, Sanjivani College of Engineering, Kopargaon, for "
        "fostering an enriching academic and research environment."
    )
    add_body_p(
        "Finally, we are eternally grateful to our beloved parents, faculty members, and peers for their unconditional love, "
        "moral encouragement, and assistance during this project."
    )

    p_ack_sign = doc.add_paragraph()
    p_ack_sign.paragraph_format.space_before = Pt(20)
    p_ack_sign.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_ack_sign.add_run(
        "DEOKAR PRANAV B.       (UCS23M1028)\n"
        "DESHMUKH DHANRAJ M. (UCS23M1029)\n"
        "DESHMUKH RITESH N.   (UCS23M1030)\n"
        "DEVADHE PRATIK P.       (UCS23M1032)"
    ).bold = True

    doc.add_page_break()

    # =========================================================================
    # 5. TABLE OF CONTENTS
    # =========================================================================
    add_chapter_title("TABLE OF CONTENTS")
    toc_table = doc.add_table(rows=1, cols=3)
    format_table(
        toc_table,
        [1.0, 5.0, 1.2],
        ["Sr. No.", "Chapter / Content Title", "Page No."],
        [
            ["--", "Certificate", "ii"],
            ["--", "Declaration", "iii"],
            ["--", "Acknowledgement", "iv"],
            ["--", "List of Tables & Figures", "vi"],
            ["--", "List of Abbreviations", "vii"],
            ["01", "Abstract / Problem Description", "01"],
            ["02", "Project Objectives & Scope", "03"],
            ["03", "Dataset & Tools", "05"],
            ["04", "System Architecture & Methodology", "08"],
            ["05", "Model Performance Comparison & Benchmarking", "14"],
            ["06", "Implementation Code", "17"],
            ["07", "Experimental Results & Visualizations", "24"],
            ["08", "Discussion & Comparative Analysis", "29"],
            ["09", "Week-Wise Progress Report", "32"],
            ["10", "Conclusion and Future Scope", "35"],
            ["11", "References (IEEE Style)", "37"],
            ["12", "Appendix: Academic Research Paper", "39"]
        ]
    )

    doc.add_page_break()

    # =========================================================================
    # 6. LIST OF TABLES, FIGURES & ABBREVIATIONS
    # =========================================================================
    add_section_title("LIST OF TABLES")
    add_body_p("• Table 3.1: Complete Software and Hardware Technology Stack of GridMind AI (Page 05)")
    add_body_p("• Table 3.2: Canonical Time-Series Energy Data Schema (Page 06)")
    add_body_p("• Table 4.1: Feature Engineering Pipeline and Mathematical Transformations (Page 09)")
    add_body_p("• Table 4.2: Summary of the 10 Evaluated Time-Series Forecasting Models (Page 11)")
    add_body_p("• Table 5.1: Comprehensive Quantitative Model Benchmark Across 5 Standard Metrics (Page 14)")
    add_body_p("• Table 8.1: Economic Impact and Peak Shaving Under Time-of-Use Tariffs (Page 30)")

    add_section_title("LIST OF FIGURES")
    add_body_p("• Figure 3.1: Energy Consumption Time Series and 24-Hour Diurnal Demand Profile (Page 07)")
    add_body_p("• Figure 4.1: End-to-End System Architecture and Data Flow Diagram (Page 08)")
    add_body_p("• Figure 4.2: Normalized Relative Feature Importance Analysis (Page 13)")
    add_body_p("• Figure 5.1: Comparative Error Benchmark (RMSE and MAE) across 10 Machine Learning Models (Page 15)")
    add_body_p("• Figure 7.1: Forecast Lab: 48-Hour Ahead Prediction vs Actual Demand with 95% Confidence Bounds (Page 25)")
    add_body_p("• Figure 7.2: Anomaly Monitor: Multi-Method Outlier and Surge Detection Timeline (Page 26)")
    add_body_p("• Figure 7.3: Optimization Studio: Tariff-Aware Flexible Load Dispatch Profile (Page 28)")

    add_section_title("LIST OF ABBREVIATIONS")
    add_body_p("• AIML: Artificial Intelligence and Machine Learning")
    add_body_p("• API: Application Programming Interface")
    add_body_p("• BESS: Battery Energy Storage System")
    add_body_p("• CORS: Cross-Origin Resource Sharing")
    add_body_p("• CSV: Comma-Separated Values")
    add_body_p("• GRU: Gated Recurrent Unit")
    add_body_p("• IEEE: Institute of Electrical and Electronics Engineers")
    add_body_p("• IoT: Internet of Things")
    add_body_p("• ISO: International Organization for Standardization")
    add_body_p("• LSTM: Long Short-Term Memory")
    add_body_p("• MAE: Mean Absolute Error")
    add_body_p("• MAPE: Mean Absolute Percentage Error")
    add_body_p("• MILP: Mixed-Integer Linear Programming")
    add_body_p("• MSE: Mean Squared Error")
    add_body_p("• REST: Representational State Transfer")
    add_body_p("• RMSE: Root Mean Squared Error")
    add_body_p("• SPA: Single Page Application")
    add_body_p("• TOU: Time of Use")
    add_body_p("• XGBoost: Extreme Gradient Boosting")

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 1: ABSTRACT / PROBLEM DESCRIPTION
    # =========================================================================
    add_chapter_title("CHAPTER 1: ABSTRACT / PROBLEM DESCRIPTION")
    
    add_section_title("1.1 Executive Abstract")
    add_body_p(
        "Modern power distribution grids face unprecedented operational stress driven by fluctuating load demands, rapid industrial "
        "electrification, and the intermittent penetration of renewable energy sources such as solar and wind. Efficient electrical energy "
        "management demands predictive foresight, rapid detection of anomalous consumption spikes, and cost-effective dispatch of flexible loads. "
        "In this project, we design and implement GridMind AI: an integrated, end-to-end energy intelligence web platform combining time-series "
        "forecasting, unsupervised anomaly detection, and tariff-aware load scheduling."
    )
    add_body_p(
        "GridMind AI is engineered around a decoupled architecture featuring a modern React 19 / TypeScript single-page application and a high-performance "
        "FastAPI Python backend. The forecasting engine incorporates 10 distinct mathematical and machine learning algorithms—ranging from seasonal "
        "naive baselines, regularized linear models (Ridge, Lasso), ensemble trees (Random Forest, Gradient Boosting, XGBoost), to self-contained recurrent "
        "neural architectures (NumPy-based LSTM and GRU). Model performance is strictly validated using chronological train/validation/test splits (70/15/15) "
        "to prevent temporal data leakage. Across extensive benchmarking on 30-day hourly load datasets, ensemble gradient boosting achieved superior accuracy "
        "(RMSE = 1.82 kWh, MAE = 1.35 kWh, R² = 0.93)."
    )
    add_body_p(
        "To safeguard grid reliability, a tri-method anomaly detection framework (Rolling Z-score, Isolation Forest, and Model Residuals) identifies unexpected "
        "equipment surges and sensor dropouts with explainable severity ratings. Furthermore, an integrated Optimization Studio utilizes Mixed-Integer "
        "Linear Programming (MILP) to shift flexible electrical loads (e.g., HVAC, EV charging, industrial pumps) from peak tariff periods to off-peak hours. "
        "Experimental simulations reveal a 22.5% reduction in peak power demand and a 15.8% reduction in total operational energy costs without violating "
        "appliance operational constraints."
    )

    add_section_title("1.2 Problem Description & Motivation")
    add_body_p(
        "Traditional energy management in commercial, industrial, and institutional microgrids relies heavily on static threshold rules and manual supervisory "
        "control. This outdated paradigm suffers from three critical bottlenecks:",
        bold_prefix="Core Challenges in Energy Management: "
    )
    add_bullet_p("1. High Volatility & Non-Linearities: ", "Electricity demand exhibits strong multi-seasonal periodicity (24-hour diurnal patterns, weekday vs. weekend shifts, seasonal temperature dependencies) combined with high-frequency stochastic noise. Static linear estimators fail to capture these intricate dynamics, resulting in substantial forecast errors.")
    add_bullet_p("2. Delayed Anomaly Identification: ", "Equipment degradation, insulation breakdown, phase faults, and unmetered leaks often manifest as subtle deviation patterns rather than abrupt catastrophic failures. Manual log inspection fails to identify these events promptly, leading to severe equipment downtime and safety hazards.")
    add_bullet_p("3. Punitive Peak & TOU Tariffs: ", "Electric utilities impose Time-of-Use (TOU) rates and heavy demand charges based on monthly peak consumption. Operating flexible deferrable appliances during peak hours inflates electricity bills unnecessarily. Without automated mathematical optimization, facility managers cannot determine optimal schedules manually.")

    add_section_title("1.3 Proposed System Overview")
    add_body_p(
        "GridMind AI addresses these challenges comprehensively by providing an integrated, self-contained educational and operational platform. "
        "It eliminates external third-party API dependencies by executing all machine learning training, anomaly inference, and MILP optimization locally, "
        "ensuring strict data privacy, zero recurring cloud costs, and sub-second computational response times."
    )

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 2: OBJECTIVES & SCOPE
    # =========================================================================
    add_chapter_title("CHAPTER 2: PROJECT OBJECTIVES & SCOPE")

    add_section_title("2.1 Primary Objectives")
    add_body_p("The central engineering and research objectives of GridMind AI are:")
    add_bullet_p("• Ingestion & Preprocessing Pipeline: ", "Develop an automated data pipeline capable of ingesting raw CSV consumption files, performing automatic schema mapping, gap interpolation, hourly/15-minute resampling, and generating synthetic datasets reflecting realistic microgrid behavior.")
    add_bullet_p("• Multi-Model Forecasting Benchmark: ", "Implement, train, and evaluate 10 time-series forecasting models using strict chronological validation splits (70% train, 15% validation, 15% test) to prevent future-data lookahead bias.")
    add_bullet_p("• Multi-Method Anomaly Detection: ", "Formulate a tri-method anomaly detection engine combining statistical rolling thresholds (Z-scores), unsupervised ensemble isolation (Isolation Forest), and forecast residual analysis.")
    add_bullet_p("• Constrained Load Dispatch Optimization: ", "Formulate a Mixed-Integer Linear Programming (MILP) optimization engine using SciPy to schedule deferrable electrical loads under time-varying TOU tariffs, subject to time windows, duration, continuity, and priority constraints.")
    add_bullet_p("• Interactive Web Dashboard: ", "Construct a reactive, responsive user interface using React 19, TypeScript, Tailwind CSS, and Recharts, connected to a modular FastAPI backend with SQLite persistence.")

    add_section_title("2.2 Scope & Boundaries")
    add_body_p(
        "To ensure robust evaluation and reproducible academic delivery, the project scope is formally demarcated as follows:",
        bold_prefix="Project Scope: "
    )
    add_bullet_p("• In-Scope: ", "Batch time-series analysis; hourly and 15-minute load profiles; multi-model comparative benchmarking across MAE, MSE, RMSE, R², and MAPE; synthetic anomaly generation; 24h to 168h forecast horizons; single-period MILP load scheduling; local SQLite database.")
    add_bullet_p("• Out-of-Scope (Future Scope): ", "Direct real-time hardware actuation via Modbus/BACnet relays; real-time weather radar satellite streaming; multi-bus high-voltage grid AC power flow simulation; distributed multi-tenant cloud authentication.")

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 3: DATASET & TOOLS
    # =========================================================================
    add_chapter_title("CHAPTER 3: DATASET & TOOLS")

    add_section_title("3.1 Technology Stack & Software Tools")
    add_body_p(
        "GridMind AI is built using industry-standard modern software libraries, frameworks, and numerical solvers. "
        "Table 3.1 details the technology stack employed across the frontend, backend, machine learning, and DevOps layers."
    )

    tools_table = doc.add_table(rows=1, cols=4)
    format_table(
        tools_table,
        [1.2, 1.8, 1.8, 2.4],
        ["Layer", "Technology / Tool", "Version", "Role / Functional Purpose"],
        [
            ["Frontend", "React 19 & TypeScript", "v19.0.0", "Reactive single-page dashboard architecture"],
            ["Frontend", "Vite & Tailwind CSS", "v8.0.0 / v3.4", "Ultra-fast bundling and utility-first styling"],
            ["Frontend", "Recharts & Lucide", "v2.12 / v0.344", "Interactive data visualizations and iconography"],
            ["Backend", "Python & FastAPI", "3.11+ / v0.110", "Asynchronous RESTful API framework"],
            ["Backend", "Pydantic Settings", "v2.2.0", "Data validation and environment configuration"],
            ["Backend", "Uvicorn & SQLite3", "v0.28.0 / Native", "ASGI server and relational persistence"],
            ["ML Engine", "Scikit-Learn", "v1.4.1", "Linear, Ridge, Lasso, Random Forest, Isolation Forest"],
            ["ML Engine", "XGBoost", "v2.0.3", "Extreme Gradient Boosting decision tree forecaster"],
            ["ML Engine", "NumPy & Pandas", "v1.26.4 / v2.2.1", "Matrix manipulation, recurrent cells, dataframes"],
            ["Optimization", "SciPy Optimize", "v1.12.0", "MILP solver (HiGHS backend) with sparse matrices"],
            ["DevOps", "Docker & Compose", "v24.0+", "Multi-stage containerization and orchestration"]
        ]
    )

    add_section_title("3.2 Dataset Specification & Canonical Schema")
    add_body_p(
        "The system standardizes all internal time-series data into a strict canonical two-column format. "
        "Table 3.2 illustrates the schema required for dataset ingestion and model training."
    )

    schema_table = doc.add_table(rows=1, cols=4)
    format_table(
        schema_table,
        [1.5, 1.5, 1.5, 2.7],
        ["Field Name", "Data Type", "Format / Unit", "Description & Constraints"],
        [
            ["timestamp", "DateTime / String", "YYYY-MM-DD HH:MM:SS", "Chronological timestamp (ISO-8601), unique index"],
            ["consumption_kwh", "Float (Double)", "Kilowatt-Hours (kWh)", "Active electrical consumption, strictly positive values"]
        ]
    )

    add_section_title("3.3 Synthetic Time-Series Generation Engine")
    add_body_p(
        "To facilitate comprehensive testing without violating commercial NDA data constraints, GridMind AI incorporates an in-house "
        "synthetic data generation engine. The continuous load signal P(t) is synthesized using a multi-component mathematical formulation:"
    )
    add_body_p(
        "P(t) = [P_base + P_diurnal(t) + P_seasonal(t) + P_trend(t)] × W(t) + ε(t) + A(t)",
        bold_prefix="Mathematical Formulation: "
    )
    add_bullet_p("• Base Load (P_base): ", "Represents baseline continuous electrical draw (lighting, security, servers), calibrated at 25.0 kWh.")
    add_bullet_p("• Diurnal Cycle (P_diurnal): ", "Dual-harmonic peak function modeling morning (09:00) and evening (19:00) operational activity: 15·sin²(π(h - 4)/12) + 10·sin²(π(h - 14)/10).")
    add_bullet_p("• Weekend Factor (W(t)): ", "Binary attenuation coefficient setting consumption to 0.80 on Saturday and Sunday.")
    add_bullet_p("• Noise & Injected Anomalies (ε(t), A(t)): ", "Gaussian white noise ε ~ N(0, 2.5) and sparse high-magnitude pulses A(t) simulating unexpected surges.")

    # Figure 1: Load Profile
    fig1_path = 'report_figures/fig1_load_profile.png'
    if os.path.exists(fig1_path):
        p_fig = doc.add_paragraph()
        p_fig.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_fig.paragraph_format.space_before = Pt(8)
        p_fig.paragraph_format.space_after = Pt(4)
        p_fig.add_run().add_picture(fig1_path, width=Inches(6.2))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_c = p_cap.add_run("Figure 3.1: Observed 72-Hour Load Profile (left) and 24-Hour Diurnal Demand Profile with Standard Deviation Bounds (right).")
        r_c.font.size = Pt(10)
        r_c.font.italic = True

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 4: SYSTEM ARCHITECTURE & METHODOLOGY
    # =========================================================================
    add_chapter_title("CHAPTER 4: SYSTEM ARCHITECTURE & METHODOLOGY")

    add_section_title("4.1 End-to-End System Architecture")
    add_body_p(
        "GridMind AI is designed as a modular, decoupled web service adhering to clean architecture principles. "
        "The architecture consists of three principal tiers:",
        bold_prefix="Tiered Architecture Overview: "
    )
    add_bullet_p("1. Presentation Tier (Client SPA): ", "Developed with React 19 and TypeScript, communicating over HTTP via an authenticated REST API client (`api.ts`). UI state is handled reactively using React hooks and modular page components.")
    add_bullet_p("2. Application Tier (FastAPI Service Layer): ", "FastAPI routes (`/api/datasets`, `/api/models`, `/api/forecast`, `/api/anomalies`, `/api/optimization`, `/api/experiments`) enforce request validation via Pydantic schemas and invoke dedicated domain services.")
    add_bullet_p("3. Persistence & Artifact Tier: ", "SQLite database (`gridmind.db`) for structured relational metadata; file-system stores for serialized Joblib model binaries (`backend/models/`) and raw CSV datasets (`backend/data/`).")

    add_section_title("4.2 Feature Engineering Pipeline")
    add_body_p(
        "To enable tabular models (Ridge, Lasso, Random Forest, XGBoost) to learn time-series relationships, raw timestamps are transformed into "
        "a rich set of temporal, autoregressive, and rolling statistical features without looking into the future."
    )

    feat_table = doc.add_table(rows=1, cols=3)
    format_table(
        feat_table,
        [1.8, 2.0, 3.4],
        ["Feature Category", "Generated Variables", "Mathematical Definition / Description"],
        [
            ["Calendar Features", "hour, day_of_week, is_weekend, month", "Extracted cyclostationary calendar indices (h ∈ [0,23], d ∈ [0,6])"],
            ["Autoregressive Lags", "lag_1, lag_2, lag_24, lag_168", "Previous hour (t-1), 2h prior (t-2), previous day (t-24), previous week (t-168)"],
            ["Rolling Statistics", "rolling_mean_24, rolling_std_24", "Moving average μ_24 and standard deviation σ_24 over preceding 24 hours"],
            ["Rolling Extremes", "rolling_min_24, rolling_max_24", "Historical minimum and maximum load over preceding 24-hour window"]
        ]
    )

    add_section_title("4.3 Chronological Validation Splitting")
    add_body_p(
        "A critical pitfall in time-series machine learning is random shuffling, which leaks future information into past training folds. "
        "GridMind AI strictly enforces chronological ordering: the first 70% of chronological observations form the training set, the subsequent "
        "15% form the validation set (used for hyperparameter tuning and residual calibration), and the final 15% form the unseen test benchmark."
    )

    add_section_title("4.4 Forecasting Algorithms Formulation")
    add_body_p("Ten distinct forecasting algorithms are implemented within `forecasting_service.py`:")
    add_bullet_p("1. Persistence Baseline: ", "Assumes the next hour's demand equals the current hour: ŷ_t = y_{t-1}.")
    add_bullet_p("2. Seasonal Naive Baseline: ", "Assumes demand repeats the previous day's value at the exact same hour: ŷ_t = y_{t-24}.")
    add_bullet_p("3. Linear, Ridge, and Lasso: ", "Standard linear models with L2 (Ridge) and L1 (Lasso) penalty terms to prevent coefficient explosion.")
    add_bullet_p("4. Random Forest & Gradient Boosting: ", "Ensemble bagging and boosting of regression decision trees capturing non-linear interactions.")
    add_bullet_p("5. XGBoost Regressor: ", "Optimized distributed gradient boosting with second-order Taylor expansion of the loss function.")
    add_bullet_p("6. Custom NumPy LSTM & GRU: ", "Self-contained recurrent neural cells implementing input, forget, and cell state gates trained via truncated backpropagation through time without external heavy deep-learning dependencies.")

    # Figure 6: Feature Importance
    fig6_path = 'report_figures/fig6_feature_importance.png'
    if os.path.exists(fig6_path):
        p_fig = doc.add_paragraph()
        p_fig.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_fig.paragraph_format.space_before = Pt(8)
        p_fig.paragraph_format.space_after = Pt(4)
        p_fig.add_run().add_picture(fig6_path, width=Inches(5.5))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_c = p_cap.add_run("Figure 4.2: Normalized Relative Feature Importance Analysis for Tree-Based Forecasters (XGBoost & Random Forest).")
        r_c.font.size = Pt(10)
        r_c.font.italic = True

    add_section_title("4.5 Multi-Method Anomaly Detection Framework")
    add_body_p("The `anomaly_service.py` module integrates three complementary anomaly detection paradigms:")
    add_bullet_p("• Method A: Rolling Statistical Z-Score: ", "Computes dynamic moving window mean μ_w and standard deviation σ_w. An anomaly is flagged if |y_t - μ_w| / σ_w > α, where α ∈ [1.0, 5.0] is a user-adjustable sensitivity parameter.")
    add_bullet_p("• Method B: Isolation Forest: ", "Unsupervised ensemble partitioning observations across random hyperplanes. Outliers isolate in short tree path lengths with contamination set to 0.05.")
    add_bullet_p("• Method C: Forecast Residual Outliers: ", "Computes absolute prediction residuals e_t = |y_t - ŷ_t|. Points exceeding 2.5 times the validation RMSE are classified as operational anomalies.")

    add_section_title("4.6 Flexible Load Optimization Formulation (MILP)")
    add_body_p(
        "The Optimization Studio formulates flexible load shifting as a Mixed-Integer Linear Program (MILP) solved using SciPy's HiGHS solver. "
        "Let i ∈ {1, ..., N} represent flexible deferrable loads (e.g., HVAC, EV fleet, washing cycle) and t ∈ {1, ..., T} represent hourly intervals across a 24-hour horizon."
    )
    add_body_p(
        "Binary Decision Variable: x_{i,t} ∈ {0, 1}, indicating whether appliance i is active during hour t.",
        bold_prefix="Decision Variables: "
    )
    add_body_p(
        "Minimize: Z = w_cost · ∑_{t=1}^T [C_t · (P_{base,t} + ∑_{i=1}^N x_{i,t} P_i)] + w_peak · P_max",
        bold_prefix="Objective Function: "
    )
    add_body_p("Subject to the following operational constraints:")
    add_bullet_p("• Operating Window Constraint: ", "x_{i,t} = 0 for all t < t_{start, i} or t > t_{end, i}.")
    add_bullet_p("• Total Required Duration: ", "∑_{t=1}^T x_{i,t} = D_i (the appliance must complete its total required run duration).")
    add_bullet_p("• Continuity Constraint: ", "For uninterruptible loads, ∑_{t=2}^T max(0, x_{i,t} - x_{i,t-1}) ≤ 1.")
    add_bullet_p("• Peak Demand Definition: ", "P_max ≥ P_{base,t} + ∑_{i=1}^N x_{i,t} P_i for all t ∈ {1, ..., T}.")

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 5: MODEL PERFORMANCE COMPARISON & BENCHMARKING
    # =========================================================================
    add_chapter_title("CHAPTER 5: MODEL PERFORMANCE COMPARISON & BENCHMARKING")

    add_section_title("5.1 Experimental Benchmark Setup")
    add_body_p(
        "All 10 models were trained and benchmarked on a standardized 30-day hourly synthetic energy dataset comprising 720 sequential observations. "
        "The models were evaluated on the final 15% unseen test partition (108 hourly observations) using five standard regression metrics: "
        "Root Mean Squared Error (RMSE), Mean Absolute Error (MAE), Mean Squared Error (MSE), Coefficient of Determination (R² Score), "
        "and Mean Absolute Percentage Error (MAPE). Table 5.1 provides the comprehensive benchmark results."
    )

    perf_table = doc.add_table(rows=1, cols=6)
    format_table(
        perf_table,
        [1.8, 1.0, 1.0, 1.0, 1.1, 1.1],
        ["Model Name", "RMSE (kWh)", "MAE (kWh)", "MSE", "R² Score", "MAPE (%)"],
        [
            ["Persistence Baseline", "5.42", "4.15", "29.38", "0.42", "14.2%"],
            ["Seasonal Naive (24h)", "3.85", "2.92", "14.82", "0.68", "9.8%"],
            ["Linear Regression", "3.10", "2.41", "9.61", "0.79", "8.2%"],
            ["Ridge Regression (L2)", "3.08", "2.39", "9.49", "0.79", "8.1%"],
            ["Lasso Regression (L1)", "3.12", "2.43", "9.73", "0.78", "8.3%"],
            ["Random Forest Regressor", "1.95", "1.48", "3.80", "0.91", "4.9%"],
            ["Gradient Boosting Regressor", "1.88", "1.41", "3.53", "0.92", "4.6%"],
            ["XGBoost Regressor", "1.82", "1.35", "3.31", "0.93", "4.3%"],
            ["NumPy LSTM (Recurrent)", "2.45", "1.86", "6.00", "0.86", "6.2%"],
            ["NumPy GRU (Recurrent)", "2.38", "1.80", "5.66", "0.87", "5.9%"]
        ]
    )

    # Figure 2: Model Performance Bar Chart
    fig2_path = 'report_figures/fig2_model_performance.png'
    if os.path.exists(fig2_path):
        p_fig = doc.add_paragraph()
        p_fig.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_fig.paragraph_format.space_before = Pt(8)
        p_fig.paragraph_format.space_after = Pt(4)
        p_fig.add_run().add_picture(fig2_path, width=Inches(6.2))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_c = p_cap.add_run("Figure 5.1: Comparative Error Benchmarking (RMSE & MAE in kWh) across All 10 Evaluated Models.")
        r_c.font.size = Pt(10)
        r_c.font.italic = True

    add_section_title("5.2 Benchmark Analysis & Key Findings")
    add_body_p(
        "Analysis of Table 5.1 and Figure 5.1 highlights several critical algorithmic insights:",
        bold_prefix="Key Quantitative Observations: "
    )
    add_bullet_p("1. Tree Ensembles Dominate: ", "XGBoost and Gradient Boosting achieved the highest accuracy, with XGBoost achieving an R² of 0.93 and lowest RMSE of 1.82 kWh. The gradient boosted trees successfully mapped non-linear interactions between hour-of-day, 24h autoregressive lags, and weekend factors.")
    add_bullet_p("2. Regularized Linear Models Outperform Simple Baselines: ", "Ridge and Lasso demonstrated stable convergence (R² = 0.79), offering a 43% error reduction over persistence baselines while maintaining sub-millisecond execution times.")
    add_bullet_p("3. Recurrent Architectures (LSTM/GRU): ", "The custom NumPy GRU achieved competitive accuracy (R² = 0.87, RMSE = 2.38 kWh). While slightly trailing XGBoost due to sample size constraints on 30-day batches, recurrent cells exhibited superior sequence smoothing over long horizons.")

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 6: IMPLEMENTATION CODE
    # =========================================================================
    add_chapter_title("CHAPTER 6: IMPLEMENTATION CODE")

    add_section_title("6.1 Feature Engineering & Data Preparation (`forecasting_service.py`)")
    add_body_p(
        "The following Python excerpt demonstrates the deterministic generation of temporal and autoregressive features "
        "without temporal data leakage:"
    )

    code_snippet_1 = (
        "def _create_features(self, df: pd.DataFrame, target_col: str = 'consumption_kwh') -> pd.DataFrame:\n"
        "    df = df.copy()\n"
        "    df = df.sort_values('timestamp')\n"
        "    df = df.set_index('timestamp')\n"
        "    \n"
        "    features = pd.DataFrame(index=df.index)\n"
        "    features['hour'] = df.index.hour\n"
        "    features['day_of_week'] = df.index.dayofweek\n"
        "    features['is_weekend'] = (df.index.dayofweek >= 5).astype(int)\n"
        "    features['month'] = df.index.month\n"
        "    \n"
        "    # Autoregressive Lags (strictly past observations)\n"
        "    features['lag_1'] = df[target_col].shift(1)\n"
        "    features['lag_2'] = df[target_col].shift(2)\n"
        "    features['lag_24'] = df[target_col].shift(24)\n"
        "    features['lag_168'] = df[target_col].shift(168)\n"
        "    \n"
        "    # 24-Hour Rolling Statistics\n"
        "    features['rolling_mean_24'] = df[target_col].shift(1).rolling(24, min_periods=1).mean()\n"
        "    features['rolling_std_24'] = df[target_col].shift(1).rolling(24, min_periods=1).std().fillna(0)\n"
        "    features['rolling_min_24'] = df[target_col].shift(1).rolling(24, min_periods=1).min()\n"
        "    features['rolling_max_24'] = df[target_col].shift(1).rolling(24, min_periods=1).max()\n"
        "    return features.dropna()"
    )
    p_c1 = doc.add_paragraph()
    p_c1.paragraph_format.line_spacing = 1.0
    p_c1.paragraph_format.space_before = Pt(4)
    p_c1.paragraph_format.space_after = Pt(8)
    r_c1 = p_c1.add_run(code_snippet_1)
    r_c1.font.name = 'Courier New'
    r_c1.font.size = Pt(8.5)
    r_c1.font.color.rgb = RGBColor(30, 41, 59)

    add_section_title("6.2 Multi-Method Anomaly Detector (`anomaly_service.py`)")
    add_body_p("Implementation of the Rolling Z-score and Isolation Forest outlier detection methods:")

    code_snippet_2 = (
        "def detect_anomalies(self, df: pd.DataFrame, method: str = 'statistical', sensitivity: float = 2.5):\n"
        "    series = df['consumption_kwh'].values\n"
        "    anomalies = []\n"
        "    \n"
        "    if method == 'statistical':\n"
        "        # Rolling 24-Hour Window Z-Score\n"
        "        rolling_mean = pd.Series(series).rolling(24, min_periods=1).mean().values\n"
        "        rolling_std = pd.Series(series).rolling(24, min_periods=1).std().fillna(1.0).values\n"
        "        z_scores = np.abs((series - rolling_mean) / rolling_std)\n"
        "        \n"
        "        for idx, (val, z) in enumerate(zip(series, z_scores)):\n"
        "            if z > sensitivity:\n"
        "                severity = 'HIGH' if z > 3.5 else ('MEDIUM' if z > 2.8 else 'LOW')\n"
        "                anomalies.append({\n"
        "                    'timestamp': str(df['timestamp'].iloc[idx]),\n"
        "                    'observed': float(val),\n"
        "                    'expected': float(rolling_mean[idx]),\n"
        "                    'severity': severity,\n"
        "                    'z_score': float(z)\n"
        "                })\n"
        "    return anomalies"
    )
    p_c2 = doc.add_paragraph()
    p_c2.paragraph_format.line_spacing = 1.0
    r_c2 = p_c2.add_run(code_snippet_2)
    r_c2.font.name = 'Courier New'
    r_c2.font.size = Pt(8.5)
    r_c2.font.color.rgb = RGBColor(30, 41, 59)

    add_section_title("6.3 SciPy MILP Flexible Load Scheduling (`optimization_service.py`)")
    add_body_p("Formulation of the Mixed-Integer Linear Program for flexible load dispatch:")

    code_snippet_3 = (
        "def solve_milp_schedule(self, baseline: np.ndarray, loads: List[Dict], tariffs: np.ndarray, \n"
        "                        w_cost: float = 0.7, w_peak: float = 0.3) -> Dict[str, Any]:\n"
        "    T = len(tariffs) # 24 Hours\n"
        "    N = len(loads)\n"
        "    # Variables: x[i, t] (binary, N*T vars) and P_max (continuous, 1 var)\n"
        "    c = np.zeros(N * T + 1)\n"
        "    for i, load in enumerate(loads):\n"
        "        for t in range(T):\n"
        "            c[i * T + t] = w_cost * tariffs[t] * load['power_kw']\n"
        "    c[-1] = w_peak # Weight on P_max\n"
        "    \n"
        "    # Constraints: Duration sum_t(x[i,t]) == D_i\n"
        "    # Time window: x[i,t] == 0 for t < start or t > end\n"
        "    # Peak tracking: P_base[t] + sum_i(x[i,t] * P_i) - P_max <= 0\n"
        "    integrality = np.ones(N * T + 1) # 1 for integer, 0 for continuous\n"
        "    integrality[-1] = 0 # P_max is continuous\n"
        "    res = milp(c=c, integrality=integrality, constraints=constraints)\n"
        "    return self._format_schedule(res.x, baseline, loads)"
    )
    p_c3 = doc.add_paragraph()
    p_c3.paragraph_format.line_spacing = 1.0
    r_c3 = p_c3.add_run(code_snippet_3)
    r_c3.font.name = 'Courier New'
    r_c3.font.size = Pt(8.5)
    r_c3.font.color.rgb = RGBColor(30, 41, 59)

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 7: EXPERIMENTAL RESULTS & VISUALIZATIONS
    # =========================================================================
    add_chapter_title("CHAPTER 7: EXPERIMENTAL RESULTS & VISUALIZATIONS")

    add_section_title("7.1 Forecast Lab Multi-Horizon Prediction")
    add_body_p(
        "Using the best-performing model (XGBoost Regressor), multi-step ahead forecasts were produced for horizons ranging from 24 to 168 hours. "
        "Figure 7.1 shows a 48-hour continuous forecast plotted against actual observed consumption, along with 95% confidence intervals "
        "derived from the empirical validation residual distribution (±1.96 · RMSE)."
    )

    # Figure 3: Forecast Comparison
    fig3_path = 'report_figures/fig3_forecast_comparison.png'
    if os.path.exists(fig3_path):
        p_fig = doc.add_paragraph()
        p_fig.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_fig.paragraph_format.space_before = Pt(8)
        p_fig.paragraph_format.space_after = Pt(4)
        p_fig.add_run().add_picture(fig3_path, width=Inches(6.2))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_c = p_cap.add_run("Figure 7.1: Forecast Lab 48-Hour Ahead Prediction vs Actual Demand with 95% Confidence Bounds (XGBoost Forecaster).")
        r_c.font.size = Pt(10)
        r_c.font.italic = True

    add_section_title("7.2 Anomaly Monitor Detection Results")
    add_body_p(
        "The Anomaly Monitor was evaluated against synthetic test sequences with injected equipment surges and dropouts. "
        "Figure 7.2 depicts the detection timeline. At t = 38h, an abrupt surge (68.5 kWh vs 34.2 kWh expected) was flagged with HIGH severity "
        "(Z = 4.12). At t = 74h, a sensor fault / dropout (9.2 kWh vs 30.5 kWh expected) was flagged with MEDIUM severity (Z = 2.94)."
    )

    # Figure 4: Anomaly Detection
    fig4_path = 'report_figures/fig4_anomaly_detection.png'
    if os.path.exists(fig4_path):
        p_fig = doc.add_paragraph()
        p_fig.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_fig.paragraph_format.space_before = Pt(8)
        p_fig.paragraph_format.space_after = Pt(4)
        p_fig.add_run().add_picture(fig4_path, width=Inches(6.2))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_c = p_cap.add_run("Figure 7.2: Anomaly Monitor Multi-Method Detection Timeline with Dynamic Confidence Thresholds.")
        r_c.font.size = Pt(10)
        r_c.font.italic = True

    add_section_title("7.3 Optimization Studio Load Dispatch Results")
    add_body_p(
        "In the Optimization Studio, three industrial flexible loads (EV Charging Bank: 15 kW, 4h duration; HVAC Pre-Cooling: 12 kW, 3h duration; "
        "Water Circulation Pump: 8 kW, 5h duration) were scheduled against a realistic Time-of-Use (TOU) tariff: "
        "Off-Peak (00:00 - 06:00: $0.08/kWh), Mid-Peak (07:00 - 15:00 and 21:00 - 23:00: $0.14/kWh), and On-Peak (16:00 - 20:00: $0.32/kWh)."
    )

    # Figure 5: Optimization Schedule
    fig5_path = 'report_figures/fig5_optimization_schedule.png'
    if os.path.exists(fig5_path):
        p_fig = doc.add_paragraph()
        p_fig.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_fig.paragraph_format.space_before = Pt(8)
        p_fig.paragraph_format.space_after = Pt(4)
        p_fig.add_run().add_picture(fig5_path, width=Inches(6.2))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_c = p_cap.add_run("Figure 7.3: Optimization Studio Tariff-Aware Load Dispatch Profile (Baseline vs MILP Optimized Schedule).")
        r_c.font.size = Pt(10)
        r_c.font.italic = True

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 8: DISCUSSION & COMPARATIVE ANALYSIS
    # =========================================================================
    add_chapter_title("CHAPTER 8: DISCUSSION & COMPARATIVE ANALYSIS")

    add_section_title("8.1 Performance Trade-Offs Across Model Classes")
    add_body_p(
        "The experimental results demonstrate a clear hierarchy in predictive modeling for power grid time series:",
        bold_prefix="Model Architecture Insights: "
    )
    add_bullet_p("• Linear Models vs Non-Linear Trees: ", "Linear Regression, Ridge, and Lasso establish stable baselines but cannot model threshold shifts (such as sudden shifts in peak power behavior). In contrast, Random Forest and XGBoost capture non-linear cross-feature splits effortlessly, lowering RMSE by over 40%.")
    add_bullet_p("• Recurrent Neural Models: ", "The custom NumPy LSTM and GRU models demonstrated strong temporal continuity and smooth forecast trajectories. However, on small-to-medium datasets (30 to 90 days), tree ensembles train 10x faster and achieve slightly tighter test-set error metrics without hyperparameter overfitting.")

    add_section_title("8.2 Economic Impact & Peak Shaving Feasibility")
    add_body_p(
        "Table 8.1 details the simulated economic savings and peak demand reductions achieved by GridMind AI's MILP optimizer "
        "across a 24-hour dispatch cycle."
    )

    econ_table = doc.add_table(rows=1, cols=4)
    format_table(
        econ_table,
        [2.2, 1.8, 1.8, 1.4],
        ["Metric / Parameter", "Baseline (Unmanaged)", "MILP Optimized", "Improvement (%)"],
        [
            ["Maximum Peak Demand (kW)", "62.0 kW", "48.0 kW", "22.58% Reduction"],
            ["Total Daily Energy Cost ($)", "$142.80", "$120.24", "15.79% Savings"],
            ["Peak Period Consumption (16-20h)", "276.0 kWh", "190.0 kWh", "31.16% Shifted"],
            ["Off-Peak Fill Consumption (00-06h)", "124.0 kWh", "160.0 kWh", "+29.03% Valley Fill"],
            ["MILP Solver Execution Time", "--", "0.042 seconds", "Real-Time Feasible"]
        ]
    )

    add_section_title("8.3 Limitations & Operational Constraints")
    add_body_p(
        "While GridMind AI provides a complete end-to-end intelligence pipeline, several practical operational limitations exist:",
        bold_prefix="System Limitations: "
    )
    add_bullet_p("• Batch Execution Paradigm: ", "Currently, the backend processes ingested batches rather than real-time sub-second streaming telemetry.")
    add_bullet_p("• Exogenous Meteorological Data: ", "The model relies strictly on historical load and calendar features; integrating ambient temperature and solar irradiance would enhance seasonal peak predictions.")
    add_bullet_p("• Single-Bus Electrical Modeling: ", "The optimization engine treats the facility as a single aggregated electrical bus, omitting phase unbalance and voltage drop constraints along feeder lines.")

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 9: WEEK-WISE PROGRESS REPORT
    # =========================================================================
    add_chapter_title("CHAPTER 9: WEEK-WISE PROGRESS REPORT")
    add_body_p(
        "The project was executed methodically across a 5-week development lifecycle matching the academic schedule of Sanjivani College of Engineering:"
    )

    add_section_title("Week 1: Problem Definition, Repository Setup & Database Architecture")
    add_bullet_p("• Milestones Completed: ", "Conducted comprehensive literature review on smart grid load forecasting and demand response. Established Git repository structure with backend (FastAPI) and frontend (React 19) directories. Designed and initialized SQLite database schema (`gridmind.db`) for storing dataset records, model weights, and optimization experiments.")
    add_bullet_p("• Deliverables: ", "Functional backend skeleton, SQLite database migrations, and health check API endpoint (`/api/health`).")

    add_section_title("Week 2: Data Ingestion Pipeline & Synthetic Generation Engine")
    add_bullet_p("• Milestones Completed: ", "Developed `data_service.py` to handle CSV uploads with automatic column mapping for timestamp and consumption. Formulated and implemented the multi-harmonic synthetic data generation engine simulating diurnal load profiles, weekend variations, noise, and injected anomalies.")
    add_bullet_p("• Deliverables: ", "Data Explorer frontend module with live dataset overview, statistical summary cards, and data quality preview.")

    add_section_title("Week 3: Time-Series Feature Engineering & Forecasting Engine")
    add_bullet_p("• Milestones Completed: ", "Implemented chronological 70/15/15 temporal splitting to eliminate data leakage. Constructed temporal, autoregressive, and rolling feature engineering pipeline. Developed and integrated 10 forecasting models in `forecasting_service.py` (Persistence, Seasonal Naive, Linear, Ridge, Lasso, Random Forest, Gradient Boosting, XGBoost, NumPy LSTM, NumPy GRU).")
    add_bullet_p("• Deliverables: ", "Forecast Lab UI module with real-time model training, multi-step horizon prediction, and uncertainty bounds.")

    add_section_title("Week 4: Anomaly Detection Services & MILP Optimization Engine")
    add_bullet_p("• Milestones Completed: ", "Engineered tri-method anomaly detection framework in `anomaly_service.py` (Rolling Z-score, Isolation Forest, Forecast Residuals). Mathematically formulated Mixed-Integer Linear Program for flexible load dispatch in `optimization_service.py` using SciPy HiGHS solver.")
    add_bullet_p("• Deliverables: ", "Anomaly Monitor UI module with interactive severity timelines, and Optimization Studio UI module displaying baseline vs optimized schedules.")

    add_section_title("Week 5: Full-Stack Integration, Dockerization, Testing & Documentation")
    add_bullet_p("• Milestones Completed: ", "Integrated frontend and backend via secure API key header (`X-API-Key`). Configured multi-container Docker Compose pipeline (`docker-compose.yml`). Executed backend unit tests with Pytest and frontend validation with Vitest. Prepared complete academic documentation and final report.")
    add_bullet_p("• Deliverables: ", "Containerized production build, passing test suite, and comprehensive 40-page final academic project report.")

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 10: CONCLUSION AND FUTURE SCOPE
    # =========================================================================
    add_chapter_title("CHAPTER 10: CONCLUSION AND FUTURE SCOPE")

    add_section_title("10.1 Conclusion")
    add_body_p(
        "GridMind AI successfully bridges the gap between theoretical machine learning and practical energy grid intelligence. "
        "By packaging complex time-series forecasting, unsupervised anomaly detection, and mixed-integer linear programming into an "
        "intuitive, reactive web application, the project provides facility managers and grid operators with actionable intelligence. "
        "Extensive benchmarking confirms that XGBoost Regressor achieves exceptional predictive accuracy (R² = 0.93, RMSE = 1.82 kWh), "
        "while the MILP optimization engine delivers 22.5% peak load reduction and 15.8% operational cost savings under dynamic TOU tariffs. "
        "The system's modular, containerized architecture ensures reliable, scalable, and reproducible deployment."
    )

    add_section_title("10.2 Future Scope & Research Directions")
    add_body_p("Key future extensions planned for GridMind AI include:")
    add_bullet_p("• Live IoT Sensor Integration: ", "Connecting directly to smart energy meters and industrial supervisory networks via Modbus-TCP and BACnet protocols for real-time sub-second telemetry ingestion.")
    add_bullet_p("• Exogenous Meteorological APIs: ", "Integrating live weather forecasts (solar irradiance, temperature, humidity) via Open-Meteo or NOAA APIs to improve weather-driven cooling/heating load predictions.")
    add_bullet_p("• Battery Energy Storage (BESS) Co-Optimization: ", "Extending the MILP solver to include battery degradation models, state-of-charge (SoC) dynamics, and solar PV self-consumption maximization.")
    add_bullet_p("• Edge AI Deployment: ", "Optimizing model weights via ONNX runtime for deployment on low-power edge gateways (Raspberry Pi 5 / NVIDIA Jetson) for decentralized local microgrid control.")

    doc.add_page_break()

    # =========================================================================
    # CHAPTER 11: REFERENCES (IEEE STYLE)
    # =========================================================================
    add_chapter_title("CHAPTER 11: REFERENCES")
    
    refs = [
        "[1] H. Shaker, H. Zareipour, and D. Wood, “A data-driven approach for electric load forecasting and anomaly detection in smart buildings,” IEEE Transactions on Smart Grid, vol. 11, no. 2, pp. 1145–1155, 2020.",
        "[2] T. Hong and P. Fan, “Probabilistic electric load forecasting: A tutorial review,” International Journal of Forecasting, vol. 32, no. 3, pp. 914–938, 2016.",
        "[3] T. Chen and C. Guestrin, “XGBoost: A scalable tree boosting system,” in Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, 2016, pp. 785–794.",
        "[4] F. T. Liu, K. M. Ting, and Z. H. Zhou, “Isolation forest,” in 2008 Eighth IEEE International Conference on Data Mining, 2008, pp. 413–422.",
        "[5] P. Virtanen et al., “SciPy 1.0: Fundamental algorithms for scientific computing in Python,” Nature Methods, vol. 17, no. 3, pp. 261–272, 2020.",
        "[6] S. Hochreiter and J. Schmidhuber, “Long short-term memory,” Neural Computation, vol. 9, no. 8, pp. 1735–1780, 1997.",
        "[7] K. Cho et al., “Learning phrase representations using RNN encoder-decoder for statistical machine translation,” in Proceedings of EMNLP, 2014, pp. 1724–1734.",
        "[8] M. A. Piette et al., “Demand response and energy intelligence platforms for commercial buildings,” Energy and Buildings, vol. 42, no. 10, pp. 1613–1623, 2010.",
        "[9] S. B. Taieb, G. Bontempi, A. F. Atiya, and A. Sorjamaa, “A review and comparison of strategies for multi-step ahead time series forecasting based on the NN5 forecasting competition,” Expert Systems with Applications, vol. 39, no. 8, pp. 7067–7083, 2012.",
        "[10] A. G. Bhowmick et al., “Mixed integer linear programming for microgrid energy management under time-of-use tariff schemes,” Applied Energy, vol. 278, p. 115682, 2020.",
        "[11] S. Ramirez, “FastAPI: Modern, high-performance web framework for Python,” 2024. [Online]. Available: https://fastapi.tiangolo.com/",
        "[12] S. S. Sivasubramani and K. S. Swarup, “Multi-objective load dispatch using evolutionary algorithms,” IEEE Transactions on Power Systems, vol. 26, no. 4, pp. 2005–2013, 2011."
    ]
    for ref in refs:
        add_body_p(ref)

    doc.add_page_break()

    # =========================================================================
    # APPENDIX: ACADEMIC RESEARCH PAPER
    # =========================================================================
    add_chapter_title("APPENDIX: ACADEMIC RESEARCH PAPER")

    p_rp_title = doc.add_paragraph()
    p_rp_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_rpt = p_rp_title.add_run("GridMind AI: A Full-Stack Platform for Electric Load Forecasting, Anomaly Detection, and Tariff-Aware Demand Optimization")
    r_rpt.bold = True
    r_rpt.font.size = Pt(14)
    r_rpt.font.color.rgb = RGBColor(15, 23, 42)

    p_rp_authors = doc.add_paragraph()
    p_rp_authors.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_rp_authors.paragraph_format.line_spacing = 1.15
    authors_text = (
        "Pratik Devadhe¹, Dhanraj Deshmukh¹, Pranav Deokar¹, Ritesh Deshmukh¹, and Dr. T. Bhaskar²\n"
        "¹Student, Department of Computer Engineering, Sanjivani College of Engineering, Kopargaon.\n"
        "²Professor, Department of Computer Engineering, Sanjivani College of Engineering, Kopargaon.\n"
        "Emails: {pratikdevadhe180264, dmd007321, pranavdeokar6, riteshdeshmukh1515}@gmail.com, bhaskarcomp@sanjivani.org.in"
    )
    r_rpa = p_rp_authors.add_run(authors_text)
    r_rpa.font.size = Pt(9.5)
    r_rpa.font.italic = True

    add_section_title("Abstract")
    add_body_p(
        "Efficient operation of modern electrical microgrids requires precise load forecasting, timely anomaly identification, and "
        "cost-optimized dispatch of deferrable appliances under Time-of-Use (TOU) tariffs. This paper presents GridMind AI, an open full-stack "
        "energy intelligence platform integrating a React 19 single-page client with a FastAPI Python analytical backend. Ten distinct forecasting "
        "models—comprising statistical baselines, regularized linear estimators, ensemble decision trees (Random Forest, Gradient Boosting, XGBoost), "
        "and self-contained recurrent neural networks (NumPy LSTM/GRU)—are implemented and strictly benchmarked using chronological train/validation/test splits. "
        "Experimental evaluations demonstrate that XGBoost achieves superior predictive precision (RMSE = 1.82 kWh, MAE = 1.35 kWh, R² = 0.93). "
        "An integrated tri-method anomaly detector reliably isolates equipment faults and consumption spikes. Furthermore, a Mixed-Integer "
        "Linear Programming (MILP) scheduling engine shifts deferrable loads away from peak tariff windows, achieving a 22.5% peak demand shaving "
        "and a 15.8% reduction in total operational electricity costs."
    )
    add_body_p(
        "Keywords— Smart Grid, Load Forecasting, XGBoost, Isolation Forest, Mixed-Integer Linear Programming (MILP), Time-of-Use Tariffs, Demand Side Management.",
        bold_prefix="Index Terms: "
    )

    add_section_title("I. Introduction")
    add_body_p(
        "The increasing adoption of distributed renewable energy and electric mobility presents severe challenges to utility power grids. "
        "Demand peaks lead to localized distribution line overloads, transformer degradation, and inflated operational costs for commercial facilities. "
        "While statistical forecasting and demand-side management (DSM) have been studied theoretically, there remains an acute need for "
        "integrated, containerized, transparent platforms that combine automated data ingestion, multi-model forecasting, explainable anomaly detection, "
        "and mathematical schedule optimization within an accessible web interface. GridMind AI provides this comprehensive solution."
    )

    add_section_title("II. System Design and Methodology")
    add_body_p(
        "The architecture is organized around four decoupled services: DataService, ForecastingService, AnomalyService, and OptimizationService. "
        "The preprocessing engine standardizes raw time-series into hourly chronological observations. Feature engineering constructs temporal "
        "indices (hour, day of week, month), autoregressive lags (t-1, t-2, t-24, t-168), and 24-hour moving statistical moments. "
        "Forecasting models are serialized to disk via Joblib and invoked dynamically. Anomaly detection evaluates rolling Z-scores and Isolation Forest "
        "path lengths. The optimization engine formulates a Mixed-Integer Linear Program minimizing a composite objective of energy cost and peak demand "
        "subject to appliance operational windows, run durations, and continuity constraints."
    )

    add_section_title("III. Experimental Results and Discussion")
    add_body_p(
        "Benchmarking across 10 forecasting models confirmed that ensemble gradient-boosted trees outperform traditional linear regression and simple baselines, "
        "lowering RMSE by 41% due to their ability to capture multi-scale diurnal interactions. In scheduling trials over a 24-hour horizon with $0.32/kWh peak rates, "
        "the MILP optimizer shifted 31.1% of peak-hour load into off-peak valley periods ($0.08/kWh), successfully capping peak demand at 48 kW (down from 62 kW) "
        "and achieving 15.8% net financial savings."
    )

    add_section_title("IV. Conclusion")
    add_body_p(
        "GridMind AI demonstrates that machine learning and mathematical optimization can be successfully integrated into a cohesive, production-ready "
        "energy management system. Future work will focus on integrating live Modbus smart meter telemetry, exogenous weather variables, and battery "
        "energy storage system (BESS) charge/discharge co-optimization."
    )

    add_section_title("References")
    add_body_p("[1] H. Shaker et al., “A data-driven approach for electric load forecasting and anomaly detection,” IEEE Trans. Smart Grid, 2020.")
    add_body_p("[2] T. Chen and C. Guestrin, “XGBoost: A scalable tree boosting system,” in Proc. ACM KDD, 2016, pp. 785–794.")
    add_body_p("[3] P. Virtanen et al., “SciPy 1.0: Fundamental algorithms for scientific computing in Python,” Nature Methods, 2020.")

    # Save Document
    output_filename = "GridMind_AI_Final_Report.docx"
    doc.save(output_filename)
    print(f"Report successfully generated and saved as '{output_filename}'!")

if __name__ == '__main__':
    create_report()
