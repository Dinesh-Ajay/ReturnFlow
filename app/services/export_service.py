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
        writer.writerow(["Issue ID", "Scenario Code", "Asset ID", "Severity", "Description", "Recommended Action", "Detected Timestamp"])
        for a in anomalies:
            issue_id = _get_val(a, "issue_id")
            scenario = _get_val(a, "issue_type", _get_val(a, "scenario_code", ""))
            asset_id = _get_val(a, "asset_id")
            severity = _get_val(a, "severity")
            desc = _get_val(a, "description")
            action = _get_val(a, "recommended_action", _get_val(a, "expected_decision", ""))
            d_time = _get_val(a, "detected_timestamp", _get_val(a, "created_at", ""))
            time_str = d_time.strftime("%Y-%m-%d %H:%M:%S") if hasattr(d_time, "strftime") else str(d_time)

            writer.writerow([issue_id, scenario, asset_id, severity, desc, action, time_str])
        output.seek(0)
        return output

    @classmethod
    def export_anomalies_pdf(cls, anomalies: List[Any]) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle('AnomTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=16, textColor=colors.HexColor('#991B1B'))
        elements = [
            Paragraph("<b>ReturnFlow &mdash; Operational Invariant & Anomaly Audit Report</b>", title_style),
            Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total Verified Anomalies: {len(anomalies):,}", styles['Normal']),
            Spacer(1, 10)
        ]

        data = [["Issue ID", "Scenario", "Asset ID", "Severity", "Description", "Action"]]
        for a in anomalies[:250]:
            issue_id = str(_get_val(a, "issue_id"))
            scenario = str(_get_val(a, "issue_type", _get_val(a, "scenario_code", ""))).replace("SCENARIO_", "")
            asset_id = str(_get_val(a, "asset_id"))
            severity = str(_get_val(a, "severity"))
            desc = str(_get_val(a, "description"))[:40]
            action = str(_get_val(a, "recommended_action", _get_val(a, "expected_decision", "")))[:35]

            data.append([issue_id, scenario, asset_id, severity, desc, action])

        t = Table(data, colWidths=[75, 110, 80, 65, 180, 170])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#DC2626')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#FEF2F2')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#FCA5A5')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(t)
        doc.build(elements)
        buffer.seek(0)
        return buffer
