import io
import csv
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def _get_val(obj: Any, key: str, default: Any = "") -> Any:
    """Helper to safely extract attribute from either a dict or an ORM model."""
    if isinstance(obj, dict):
        val = obj.get(key)
        return val if val is not None else default
    val = getattr(obj, key, None)
    return val if val is not None else default

class ExportService:
    """
    Generates downloadable CSV, PDF, and JSON file attachments
    with complete headers, professional styling, and streaming buffers.
    """

    @staticmethod
    def _get_timestamp_str() -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @classmethod
    def export_records_json(cls, records: List[Any], report_name: str) -> str:
        """Export ORM rows using their actual mapped columns."""
        def clean(value: Any) -> Any:
            if hasattr(value, "isoformat"):
                return value.isoformat()
            if hasattr(value, "as_tuple"):  # Decimal
                return str(value)
            return value

        rows = [{column.name: clean(getattr(row, column.name))
                 for column in row.__table__.columns} for row in records]
        return json.dumps({"report": report_name, "generated_at": datetime.now(timezone.utc).isoformat(),
                           "record_count": len(rows), "records": rows}, indent=2)

    @classmethod
    def export_records_csv(cls, records: List[Any]) -> io.StringIO:
        output = io.StringIO()
        columns = list(records[0].__table__.columns) if records else []
        writer = csv.writer(output)
        writer.writerow([column.name for column in columns])
        for row in records:
            writer.writerow([_get_val(row, column.name) for column in columns])
        output.seek(0)
        return output

    @classmethod
    def export_records_pdf(cls, records: List[Any], report_name: str) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
        styles = getSampleStyleSheet()
        columns = list(records[0].__table__.columns) if records else []
        selected = columns[:8]
        table_data = [[column.name for column in selected]]
        table_data.extend([[str(_get_val(row, column.name, ""))[:48] for column in selected]
                           for row in records[:500]])
        if not selected:
            table_data = [["No records"]]
        table = Table(table_data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CBD5E1")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
        ]))
        doc.build([Paragraph(report_name, styles["Title"]),
                   Paragraph(f"Generated {datetime.now(timezone.utc).isoformat()} | {len(records)} records (up to 500 shown)", styles["Normal"]),
                   Spacer(1, 12), table])
        buffer.seek(0)
        return buffer

    # ==================== ASSETS EXPORTS ====================

    @classmethod
    def export_assets_csv(cls, assets: List[Any]) -> io.StringIO:
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        writer.writerow([
            "Asset ID", "Serial Number", "Type Code", "Type Name", "Status",
            "Current Location", "Owner", "Current Custodian", "Purchase Date",
            "Acquisition Cost ($)", "Deposit Amount ($)", "Days Outstanding",
            "Overdue Status", "Last Event Timestamp"
        ])

        for a in assets:
            asset_id = _get_val(a, "asset_id")
            serial = _get_val(a, "serial_number")
            type_code = _get_val(a, "type_code") or (a.asset_type.type_code if hasattr(a, "asset_type") and a.asset_type else "")
            type_name = _get_val(a, "type_name") or (a.asset_type.type_name if hasattr(a, "asset_type") and a.asset_type else "")
            status = _get_val(a, "asset_status")
            owner_name = _get_val(a, "owner_name") or (a.owner.owner_name if hasattr(a, "owner") and a.owner else "")
            custodian_name = _get_val(a, "current_custodian_name") or (a.current_custodian.owner_name if hasattr(a, "current_custodian") and a.current_custodian else "")
            loc_name = _get_val(a, "current_location_name") or (a.current_location.location_name if hasattr(a, "current_location") and a.current_location else "In Transit")
            purchase_date = str(_get_val(a, "purchase_date", ""))
            acq_cost = float(_get_val(a, "acquisition_cost", 0.0))
            dep_amt = float(_get_val(a, "deposit_amount", 0.0))
            days_out = _get_val(a, "days_outstanding", 0)
            is_overdue = "YES" if _get_val(a, "is_overdue", False) else "NO"
            last_ev = str(_get_val(a, "last_event_at", ""))

            writer.writerow([
                asset_id, serial, type_code, type_name, status,
                loc_name, owner_name, custodian_name, purchase_date,
                f"{acq_cost:.2f}", f"{dep_amt:.2f}", days_out,
                is_overdue, last_ev
            ])

        output.seek(0)
        return output

    @classmethod
    def export_assets_json(cls, assets: List[Any]) -> str:
        data = []
        for a in assets:
            asset_id = _get_val(a, "asset_id")
            serial = _get_val(a, "serial_number")
            type_code = _get_val(a, "type_code") or (a.asset_type.type_code if hasattr(a, "asset_type") and a.asset_type else None)
            type_name = _get_val(a, "type_name") or (a.asset_type.type_name if hasattr(a, "asset_type") and a.asset_type else None)
            status = _get_val(a, "asset_status")
            owner_name = _get_val(a, "owner_name") or (a.owner.owner_name if hasattr(a, "owner") and a.owner else None)
            loc_name = _get_val(a, "current_location_name") or (a.current_location.location_name if hasattr(a, "current_location") and a.current_location else None)
            purchase_date = str(_get_val(a, "purchase_date", ""))
            acq_cost = float(_get_val(a, "acquisition_cost", 0.0))
            dep_amt = float(_get_val(a, "deposit_amount", 0.0))
            days_out = _get_val(a, "days_outstanding", 0)
            is_overdue = bool(_get_val(a, "is_overdue", False))
            last_ev = str(_get_val(a, "last_event_at", ""))

            data.append({
                "asset_id": asset_id,
                "serial_number": serial,
                "type_code": type_code,
                "type_name": type_name,
                "asset_status": status,
                "current_location": loc_name,
                "owner": owner_name,
                "purchase_date": purchase_date,
                "acquisition_cost": acq_cost,
                "deposit_amount": dep_amt,
                "days_outstanding": days_out,
                "is_overdue": is_overdue,
                "last_event_at": last_ev
            })
        return json.dumps({
            "report": "ReturnFlow Asset Registry",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "record_count": len(data),
            "assets": data
        }, indent=2)

    @classmethod
    def export_assets_pdf(cls, assets: List[Any], filter_desc: str = "All Records") -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=18,
            textColor=colors.HexColor('#0F172A'),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.HexColor('#64748B'),
            spaceAfter=14
        )

        elements = [
            Paragraph("<b>ReturnFlow Enterprise &mdash; Reusable Asset Inventory Report</b>", title_style),
            Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Scope: {filter_desc} | Total Assets: {len(assets):,}", subtitle_style),
            Spacer(1, 10)
        ]

        table_data = [
            ["Asset ID", "Type", "Status", "Current Location", "Owner", "Days Out", "Deposit ($)", "Last Event"]
        ]

        # Take up to 250 items to keep PDF responsive and formatted
        for a in assets[:250]:
            asset_id = str(_get_val(a, "asset_id"))
            type_name = str(_get_val(a, "type_name") or (a.asset_type.type_name if hasattr(a, "asset_type") and a.asset_type else "Asset"))
            status = str(_get_val(a, "asset_status"))
            loc_name = str(_get_val(a, "current_location_name") or (a.current_location.location_name if hasattr(a, "current_location") and a.current_location else "-"))
            owner_name = str(_get_val(a, "owner_name") or (a.owner.owner_name if hasattr(a, "owner") and a.owner else "-"))
            last_ev = str(_get_val(a, "last_event_at", "-"))
            if "T" in last_ev:
                last_ev = last_ev.split("T")[0]
            days_out = str(_get_val(a, "days_outstanding", 0))
            dep_amt = float(_get_val(a, "deposit_amount", 0.0))

            table_data.append([
                asset_id,
                type_name[:14],
                status,
                loc_name[:18],
                owner_name[:18],
                days_out,
                f"${dep_amt:.2f}",
                last_ev[:10]
            ])

        t = Table(table_data, colWidths=[80, 80, 75, 120, 120, 60, 70, 75])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 7),
            ('TOPPADDING', (0, 0), (-1, 0), 7),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#1E293B')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (5, 0), (6, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ]))

        elements.append(t)
        doc.build(elements)
        buffer.seek(0)
        return buffer

    # ==================== FINANCIAL LEDGER EXPORTS ====================

    @classmethod
    def export_financial_csv(cls, records: List[Any]) -> io.StringIO:
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["Entry ID", "Asset ID", "Transaction Type", "Amount ($)", "Status", "Date", "Reference"])

        for r in records:
            ledger_id = _get_val(r, "ledger_id")
            asset_id = _get_val(r, "asset_id")
            tx_type = _get_val(r, "transaction_type")
            amt = float(_get_val(r, "transaction_amount", _get_val(r, "amount", 0.0)))
            status = _get_val(r, "status", "POSTED")
            tx_date = _get_val(r, "transaction_date", "")
            date_str = tx_date.strftime("%Y-%m-%d %H:%M:%S") if hasattr(tx_date, "strftime") else str(tx_date)
            ref = _get_val(r, "transaction_reference", _get_val(r, "reference_number", ""))

            writer.writerow([
                ledger_id, asset_id, tx_type, f"{amt:.2f}",
                status, date_str, ref
            ])
        output.seek(0)
        return output

    @classmethod
    def export_financial_pdf(cls, records: List[Any]) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('FinTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=18, textColor=colors.HexColor('#0F172A'))
        sub_style = ParagraphStyle('FinSub', parent=styles['Normal'], fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#64748B'))

        elements = [
            Paragraph("<b>ReturnFlow Enterprise &mdash; Financial Ledger & Deposit Reconciliation</b>", title_style),
            Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Entries: {len(records):,}", sub_style),
            Spacer(1, 12)
        ]

        table_data = [["Entry ID", "Asset ID", "Type", "Amount ($)", "Status", "Transaction Date", "Reference"]]
        for r in records[:250]:
            ledger_id = str(_get_val(r, "ledger_id"))
            asset_id = str(_get_val(r, "asset_id"))
            tx_type = str(_get_val(r, "transaction_type"))
            amt = float(_get_val(r, "transaction_amount", _get_val(r, "amount", 0.0)))
            status = str(_get_val(r, "status", "POSTED"))
            tx_date = _get_val(r, "transaction_date", "-")
            date_str = tx_date.strftime("%Y-%m-%d") if hasattr(tx_date, "strftime") else str(tx_date)[:10]
            ref = str(_get_val(r, "transaction_reference", _get_val(r, "reference_number", "-")))

            table_data.append([
                ledger_id, asset_id, tx_type, f"${amt:.2f}",
                status, date_str, ref[:16]
            ])

        t = Table(table_data, colWidths=[80, 95, 130, 85, 85, 105, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1D4ED8')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('ALIGN', (3, 0), (3, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t)
        doc.build(elements)
        buffer.seek(0)
        return buffer

    # ==================== INSPECTIONS EXPORTS ====================

    @classmethod
    def export_inspections_csv(cls, inspections: List[Any]) -> io.StringIO:
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["Inspection ID", "Asset ID", "Condition Status", "Damage Severity", "Requires Repair", "Inspection Date", "Notes"])
        for i in inspections:
            insp_id = _get_val(i, "inspection_id")
            asset_id = _get_val(i, "asset_id")
            condition = _get_val(i, "condition_status")
            severity = _get_val(i, "damage_severity", "NONE")
            req_repair = "YES" if _get_val(i, "requires_repair", False) else "NO"
            i_date = _get_val(i, "inspection_date", "")
            date_str = i_date.strftime("%Y-%m-%d %H:%M:%S") if hasattr(i_date, "strftime") else str(i_date)
            notes = _get_val(i, "inspection_notes", "")

            writer.writerow([insp_id, asset_id, condition, severity, req_repair, date_str, notes])
        output.seek(0)
        return output

    @classmethod
    def export_inspections_pdf(cls, inspections: List[Any]) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('InspTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, textColor=colors.HexColor('#0F172A'))
        elements = [
            Paragraph("<b>ReturnFlow &mdash; Quality Inspections Report</b>", title_style),
            Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total Records: {len(inspections):,}", styles['Normal']),
            Spacer(1, 10)
        ]

        data = [["Inspection ID", "Asset ID", "Condition", "Severity", "Repair Needed", "Date"]]
        for i in inspections[:250]:
            insp_id = str(_get_val(i, "inspection_id"))
            asset_id = str(_get_val(i, "asset_id"))
            condition = str(_get_val(i, "condition_status"))
            severity = str(_get_val(i, "damage_severity", "NONE"))
            req_repair = "YES" if _get_val(i, "requires_repair", False) else "NO"
            i_date = _get_val(i, "inspection_date", "-")
            date_str = i_date.strftime("%Y-%m-%d") if hasattr(i_date, "strftime") else str(i_date)[:10]

            data.append([insp_id, asset_id, condition, severity, req_repair, date_str])

        t = Table(data, colWidths=[95, 95, 80, 80, 90, 90])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563EB')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t)
        doc.build(elements)
        buffer.seek(0)
        return buffer

    # ==================== ANOMALIES EXPORTS ====================

    @classmethod
    def export_anomalies_csv(cls, anomalies: List[Any]) -> io.StringIO:
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(["Issue ID", "Scenario Code", "Asset ID", "Severity", "Description", "Recommended Action", "Detection Timestamp"])
        for a in anomalies:
            issue_id = _get_val(a, "issue_id")
            scenario = _get_val(a, "issue_type", _get_val(a, "scenario_code", ""))
            asset_id = _get_val(a, "affected_asset_id", _get_val(a, "asset_id", "-"))
            severity = _get_val(a, "severity")
            desc = _get_val(a, "description")
            action = _get_val(a, "expected_decision", _get_val(a, "recommended_action", ""))
            d_time = _get_val(a, "detected_at", _get_val(a, "created_at", ""))
            time_str = d_time.strftime("%Y-%m-%d %H:%M:%S") if hasattr(d_time, "strftime") else str(d_time)

            writer.writerow([issue_id, scenario, asset_id, severity, desc, action, time_str])
        output.seek(0)
        return output

    @classmethod
    def export_anomalies_pdf(cls, anomalies: List[Any], metrics: Optional[Dict[str, Any]] = None) -> io.BytesIO:
        from app.config import settings
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(letter),
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'AnomTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            leading=20,
            textColor=colors.HexColor('#991B1B')
        )
        meta_style = ParagraphStyle(
            'AnomMeta',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=11,
            textColor=colors.HexColor('#64748B')
        )
        section_style = ParagraphStyle(
            'AnomSection',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#0F172A')
        )
        body_style = ParagraphStyle(
            'AnomBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor('#1E293B')
        )
        body_bold = ParagraphStyle(
            'AnomBodyBold',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor('#1E293B')
        )

        elements = []
        m = metrics or {}

        # 1. REPORT HEADER
        gen_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        seed_val = getattr(settings, "RANDOM_SEED", 20261022)
        ref_date_val = getattr(settings, "REFERENCE_DATE", "2026-10-22")
        elements.append(Paragraph("<b>ReturnFlow Enterprise &mdash; Anomaly Detection & Audit Report</b>", title_style))
        elements.append(Paragraph(
            f"<b>Report Generated:</b> {gen_time} UTC &nbsp;|&nbsp; "
            f"<b>Dataset Seed:</b> {seed_val} &nbsp;|&nbsp; "
            f"<b>Reporting Scope / Reference Date:</b> {ref_date_val} &nbsp;|&nbsp; "
            f"<b>Audit Status:</b> {'EVALUATED' if m else 'NOT EVALUATED'}",
            meta_style
        ))
        elements.append(Spacer(1, 10))

        # 2. EXECUTIVE SUMMARY SCORECARD
        elements.append(Paragraph("<b>1. Detection Performance & Invariant Evaluation Scorecard</b>", section_style))
        elements.append(Spacer(1, 4))

        tot_inj = m.get("total_injected", 0)
        tot_det = m.get("total_detected", len(anomalies))
        tp = m.get("true_positives", 0)
        fp = m.get("false_positives", 0)
        fn = m.get("false_negatives", 0)
        precision = m.get("precision_pct")
        recall = m.get("recall_pct")
        tn = m.get("true_negatives")
        fpr = m.get("false_positive_rate_pct")
        f1 = m.get("f1_score_pct")
        detected_by_type = m.get("detected_by_type", {})
        injected_by_type = m.get("injected_by_type", {})

        def scenario_row(code, kind, title, rule):
            expected = int(injected_by_type.get(kind, 0))
            found = int(detected_by_type.get(kind, 0))
            rate = f"{found / expected * 100:.1f}%" if expected else "Unavailable"
            return [code, title, f"{found} / {expected}", rate, rule]

        summary_data = [
            ["Metric", "Value", "Metric", "Value", "Audit Status", "Result"],
            [
                "Total Injected Invariants", f"{tot_inj}",
                "True Positives (TP)", f"{tp}",
                "Detection Precision", f"{precision:.1f}%" if precision is not None else "Unavailable"
            ],
            [
                "Total Detected Invariants", f"{tot_det}",
                "False Positives (FP)", f"{fp}",
                "Detection Recall", f"{recall:.1f}%" if recall is not None else "Unavailable"
            ],
            [
                "Verified Ground Truth", f"{tp}/{tot_inj}",
                "False Negatives (FN)", f"{fn}",
                "Invariant Compliance", "Evaluation available" if m else "Not evaluated"
            ],
            [
                "Labelled Negatives", str(tn) if tn is not None else "Unavailable",
                "False Positive Rate", f"{fpr:.1f}%" if fpr is not None else "Unavailable",
                "F1 Score", f"{f1:.1f}%" if f1 is not None else "Unavailable"
            ],
        ]
        sum_table = Table(summary_data, colWidths=[130, 90, 120, 90, 140, 160])
        sum_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ]))
        elements.append(sum_table)
        elements.append(Spacer(1, 10))

        # 3. 5 REQUIRED ANOMALY CATEGORIES BREAKDOWN
        elements.append(Paragraph("<b>2. Invariant Scenario Categories & Rule Breakdown</b>", section_style))
        elements.append(Spacer(1, 4))

        scenarios_data = [
            ["Scenario Code", "Category Name", "Detected", "Rate", "Policy Enforcement Rule"],
            scenario_row("SIMULTANEOUS_LOCATIONS", "SIMULTANEOUS_LOCATIONS", "Simultaneous Custody", "Asset cannot be concurrently active in two locations."),
            scenario_row("RETURN_BEFORE_DISPATCH", "RETURN_BEFORE_DISPATCH", "Return Before Dispatch", "A return must follow its dispatch in event time."),
            scenario_row("DUPLICATE_REFUND", "DUPLICATE_REFUND", "Duplicate Refund", "A deposit must not be refunded more than once."),
            scenario_row("REPAIR_WITHOUT_INSPECTION", "REPAIR_WITHOUT_INSPECTION", "Repair Without Inspection", "A completed repair requires an originating inspection."),
            scenario_row("MISSING_CUSTODY_ACTOR", "MISSING_CUSTODY_ACTOR", "Missing Custody Actor", "Custody movements require an actor.")
        ]
        scen_table = Table(scenarios_data, colWidths=[150, 140, 60, 60, 320])
        scen_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#991B1B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7.5),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#FECACA')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FEF2F2')]),
            ('TOPPADDING', (0, 0), (-1, -1), 3.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3.5),
            ('ALIGN', (2, 0), (3, -1), 'CENTER'),
        ]))
        elements.append(scen_table)
        elements.append(Spacer(1, 10))

        # 4. DETAILED ANOMALY AUDIT RECORDS TABLE
        elements.append(Paragraph(f"<b>3. Detailed Audit Log ({len(anomalies)} Records)</b>", section_style))
        elements.append(Spacer(1, 4))

        detail_data = [[
            Paragraph("<b>Issue ID</b>", body_bold),
            Paragraph("<b>Scenario</b>", body_bold),
            Paragraph("<b>Asset ID</b>", body_bold),
            Paragraph("<b>Severity</b>", body_bold),
            Paragraph("<b>Description</b>", body_bold),
            Paragraph("<b>Recommended Action</b>", body_bold),
            Paragraph("<b>Detected At</b>", body_bold),
        ]]

        if anomalies:
            for a in anomalies[:100]:
                issue_id = str(_get_val(a, "issue_id"))
                scenario = str(_get_val(a, "issue_type", _get_val(a, "scenario_code", ""))).replace("SCENARIO_", "")
                asset_id = str(_get_val(a, "affected_asset_id", _get_val(a, "asset_id", "-")))
                severity = str(_get_val(a, "severity", "CRITICAL"))
                desc = str(_get_val(a, "description"))
                action = str(_get_val(a, "expected_decision", _get_val(a, "recommended_action", "")))
                d_time = _get_val(a, "detected_at", _get_val(a, "created_at", "-"))
                time_str = d_time.strftime("%Y-%m-%d %H:%M") if hasattr(d_time, "strftime") else str(d_time)[:16]

                detail_data.append([
                    Paragraph(issue_id, body_bold),
                    Paragraph(scenario[:24], body_style),
                    Paragraph(asset_id, body_style),
                    Paragraph(f"<b>{severity}</b>", body_style),
                    Paragraph(desc, body_style),
                    Paragraph(action, body_style),
                    Paragraph(time_str, body_style),
                ])
        else:
            detail_data.append([
                Paragraph("INFO", body_bold),
                Paragraph("ALL_CLEAR", body_style),
                Paragraph("-", body_style),
                Paragraph("LOW", body_style),
                Paragraph("No invariant violations detected in current audit scan.", body_style),
                Paragraph("Maintain continuous monitoring.", body_style),
                Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M"), body_style),
            ])

        detail_table = Table(detail_data, colWidths=[70, 110, 75, 55, 210, 120, 80])
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#DC2626')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#FCA5A5')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FFF5F5')]),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(detail_table)

        doc.build(elements)
        buffer.seek(0)
        return buffer
