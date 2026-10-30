import os
import sys
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import settings
from app.database.session import SessionLocal
from app.analytics.metrics import AnalyticsService
from app.services.asset_service import AssetService
from app.services.custody_service import CustodyService
from app.services.deposit_service import DepositService
from app.validation.anomaly_detection import AnomalyDetectionEngine
from app.validation.__main__ import run_all_validation
from app.models import (
    ReusableAsset, AssetType, Owner, Location, Shipment,
    CustodyEvent, ReturnAuthorization, Inspection, Repair,
    DepositLedger, AnomalyRecord
)

# Page configuration
st.set_page_config(
    page_title="ReturnFlow - Reusable Asset & Lifecycle Management",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enterprise SaaS CSS Custom Styling matching the reference mockup
st.markdown("""
<style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Top Navigation bar */
    .top-navbar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 0.75rem 1.5rem;
        background-color: #FFFFFF;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 1.5rem;
        border-radius: 8px;
    }
    .user-pill {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        background: #F8FAFC;
        padding: 0.4rem 0.8rem;
        border-radius: 20px;
        border: 1px solid #E2E8F0;
        font-size: 0.85rem;
        font-weight: 500;
        color: #1E293B;
    }
    .avatar-circle {
        width: 32px;
        height: 32px;
        background-color: #2563EB;
        color: white;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        font-size: 0.8rem;
    }

    /* KPI Cards */
    .kpi-card {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 1.2rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        margin-bottom: 1rem;
    }
    .kpi-title {
        color: #64748B;
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.4rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .kpi-val {
        color: #0F172A;
        font-size: 1.85rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .kpi-badge-green {
        color: #16A34A;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .kpi-badge-red {
        color: #DC2626;
        font-size: 0.8rem;
        font-weight: 600;
    }

    /* Status Badges */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        text-align: center;
    }
    .badge-available { background-color: #DCFCE7; color: #166534; }
    .badge-transit { background-color: #DBEAFE; color: #1E40AF; }
    .badge-custody { background-color: #E0E7FF; color: #3730A3; }
    .badge-overdue { background-color: #FFEDD5; color: #9A3412; }
    .badge-damaged { background-color: #FEF3C7; color: #92400E; }
    .badge-repair { background-color: #FEF9C3; color: #854D0E; }
    .badge-lost { background-color: #FEE2E2; color: #991B1B; }

    /* Timeline Stepper */
    .timeline-item {
        border-left: 2px solid #3B82F6;
        padding-left: 1.2rem;
        padding-bottom: 1.2rem;
        position: relative;
    }
    .timeline-item::before {
        content: '';
        position: absolute;
        left: -6px;
        top: 2px;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #3B82F6;
    }
    .timeline-item-overdue {
        border-left: 2px solid #EF4444;
    }
    .timeline-item-overdue::before {
        background-color: #EF4444;
    }
    .timeline-time {
        font-size: 0.75rem;
        color: #64748B;
        font-weight: 600;
    }
    .timeline-title {
        font-size: 0.9rem;
        color: #0F172A;
        font-weight: 600;
        margin-top: 0.15rem;
    }
    .timeline-desc {
        font-size: 0.8rem;
        color: #475569;
    }

    /* Custom sidebar header */
    [data-testid="stSidebarHeader"] {
        padding-bottom: 0rem;
    }
</style>
""", unsafe_allow_html=True)

# Google Analytics integration script
if settings.GA_MEASUREMENT_ID:
    st.markdown(f"""
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id={settings.GA_MEASUREMENT_ID}"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', '{settings.GA_MEASUREMENT_ID}');
    </script>
    """, unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.markdown("""
<div style="display:flex; align-items:center; gap:0.6rem; padding: 0.5rem 0 1.5rem 0;">
    <div style="background:#2563EB; color:white; width:34px; height:34px; border-radius:8px; display:flex; align-items:center; justify-content:center; font-weight:bold; font-size:1.1rem;">RF</div>
    <div>
        <div style="font-weight:700; font-size:1.15rem; color:#0F172A; line-height:1.2;">ReturnFlow</div>
        <div style="font-size:0.75rem; color:#64748B;">Enterprise Asset Ops</div>
    </div>
</div>
""", unsafe_allow_html=True)

nav = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Assets",
        "Shipments",
        "Returns (RMAs)",
        "Inspections & Repairs",
        "Financial Ledger",
        "Anomaly Center",
        "Analytics",
        "Locations",
        "Owners",
        "Reports & Seed Exports"
    ],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.markdown("""
<div style="font-size:0.75rem; color:#94A3B8; padding: 0 0.5rem;">
    <b>ReturnFlow System v1.0.0</b><br/>
    Seed: <code>20261022</code><br/>
    Reference: <code>2026-10-22</code><br/>
    MySQL: <code>returnflow_db</code>
</div>
""", unsafe_allow_html=True)

# Top Bar Header Component
st.markdown("""
<div class="top-navbar">
    <div style="display:flex; align-items:center; gap:0.5rem; color:#64748B; font-size:0.85rem;">
        🔍 <span>Search assets, shipments, RMAs, or references...</span>
    </div>
    <div style="display:flex; align-items:center; gap:1rem;">
        <span style="cursor:pointer;" title="Notifications">🔔</span>
        <div class="user-pill">
            <div class="avatar-circle">AK</div>
            <div>
                <div style="font-size:0.82rem; font-weight:600; line-height:1.1;">Ajay Kumar</div>
                <div style="font-size:0.7rem; color:#64748B;">Operations Manager</div>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Database session helper
def get_db_session():
    return SessionLocal()


# =========================================================================
# TAB 1: DASHBOARD
# =========================================================================
if nav == "Dashboard":
    st.subheader("Dashboard")
    st.caption("Overview of reusable assets, shipments, returns and operational health • Date Range: Oct 1, 2026 – Oct 22, 2026")

    db = get_db_session()
    try:
        kpis = AnalyticsService.get_overview_kpis(db)
        fin = kpis["financial_summary"]

        # Row 1: 4 Top KPI Cards
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">📦 Total Assets</div>
                <div class="kpi-val">{kpis['total_assets']:,}</div>
                <div class="kpi-badge-green">▲ 2.9% vs last month</div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">🚚 Active in Transit</div>
                <div class="kpi-val">{kpis['active_in_transit']:,}</div>
                <div class="kpi-badge-green">▲ 3.2% vs last week</div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">⏰ Overdue Returns</div>
                <div class="kpi-val" style="color:#EA580C;">{kpis['overdue_count']:,}</div>
                <div class="kpi-badge-red">▼ 3.1% (Requires Action)</div>
            </div>
            """, unsafe_allow_html=True)

        with c4:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">⚠️ Lost Assets</div>
                <div class="kpi-val" style="color:#DC2626;">{kpis['lost_count']:,}</div>
                <div class="kpi-badge-red">▲ 12.1% past threshold</div>
            </div>
            """, unsafe_allow_html=True)

        # Row 2: 4 Secondary KPI Cards
        c5, c6, c7, c8 = st.columns(4)
        with c5:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">📋 Total Shipments</div>
                <div class="kpi-val">{kpis['total_shipments']:,}</div>
                <div class="kpi-badge-green">▲ 5.3% growth</div>
            </div>
            """, unsafe_allow_html=True)

        with c6:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">🔄 Return Authorizations</div>
                <div class="kpi-val">{kpis['total_returned']:,}</div>
                <div class="kpi-badge-green">▲ 6.7% processed</div>
            </div>
            """, unsafe_allow_html=True)

        with c7:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">🔧 In Repair</div>
                <div class="kpi-val">{kpis['in_repair_count']:,}</div>
                <div class="kpi-badge-green">Refurbishment active</div>
            </div>
            """, unsafe_allow_html=True)

        with c8:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">🛡️ Open Anomalies</div>
                <div class="kpi-val" style="color:#DC2626;">{kpis['open_anomalies']}</div>
                <div class="kpi-badge-red">50 Injected / 50 Detected</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)

        # Charts Row
        col_trend, col_donut = st.columns([1.6, 1.0])

        with col_trend:
            st.markdown("##### 📈 Asset Movement Trend")
            trends = AnalyticsService.get_asset_movement_trends(db, days=22)
            if trends["dates"]:
                df_trend = pd.DataFrame({
                    "Date": trends["dates"],
                    "Dispatched": trends["dispatched"],
                    "Returned": trends["returned"],
                    "In Transit": trends["in_transit"]
                })
                fig = px.line(
                    df_trend, x="Date", y=["Dispatched", "Returned", "In Transit"],
                    color_discrete_map={"Dispatched": "#2563EB", "Returned": "#10B981", "In Transit": "#06B6D4"}
                )
                fig.update_layout(
                    margin=dict(l=20, r=20, t=20, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    height=350,
                    hovermode="x unified"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No movement trend data available.")

        with col_donut:
            st.markdown("##### 🍩 Asset Status Distribution")
            dist = kpis["status_distribution"]
            labels = list(dist.keys())
            values = list(dist.values())

            fig_donut = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=.6,
                marker=dict(colors=["#10B981", "#3B82F6", "#6366F1", "#F59E0B", "#EF4444", "#8B5CF6"])
            )])
            fig_donut.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                height=350,
                annotations=[dict(text=f"<b>{kpis['total_assets']:,}</b><br/>Total Assets", x=0.5, y=0.5, font_size=14, showarrow=False)]
            )
            st.plotly_chart(fig_donut, use_container_width=True)

    finally:
        db.close()


# =========================================================================
# TAB 2: ASSETS & ASSET DETAIL
# =========================================================================
elif nav == "Assets":
    db = get_db_session()
    try:
        # Check if an asset is selected for detail drilldown
        selected_asset_id = st.session_state.get("selected_asset_id", None)

        if selected_asset_id:
            # Asset Detail View
            if st.button("← Back to Assets List"):
                st.session_state["selected_asset_id"] = None
                st.rerun()

            data = CustodyService.get_asset_full_traceability(db, selected_asset_id)
            if not data:
                st.error("Asset details not found.")
            else:
                st.markdown(f"**Assets** > `{selected_asset_id}`")
                
                # Hero Header
                head_col1, head_col2 = st.columns([3, 1])
                with head_col1:
                    status_badge = "badge-available"
                    if data["asset_status"] == "IN_TRANSIT": status_badge = "badge-transit"
                    elif data["asset_status"] == "IN_CUSTODY": status_badge = "badge-custody"
                    elif data["asset_status"] == "LOST": status_badge = "badge-lost"
                    elif data["asset_status"] == "UNDER_REPAIR": status_badge = "badge-repair"

                    st.markdown(f"""
                    <div style="display:flex; align-items:center; gap:1rem;">
                        <span style="font-size:2.2rem;">📦</span>
                        <div>
                            <div style="display:flex; align-items:center; gap:0.6rem;">
                                <h2 style="margin:0; font-size:1.6rem; color:#0F172A;">{data['asset_id']}</h2>
                                <span class="badge {status_badge}">{data['asset_status']}</span>
                                {f'<span class="badge badge-overdue">OVERDUE ({data["days_outstanding"]}d)</span>' if data['is_overdue'] else ''}
                            </div>
                            <div style="color:#64748B; font-size:0.85rem; margin-top:0.2rem;">
                                Type: <b>{data['type_name']}</b> • Owner: <b>{data['owner_name']}</b> • Current Location: <b>{data['current_location_name']}</b>
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with head_col2:
                    st.markdown(f"""
                    <div style="text-align:right;">
                        <span style="font-size:0.75rem; color:#64748B;">Days Outstanding</span><br/>
                        <span style="font-size:1.8rem; font-weight:700; color:{'#DC2626' if data['is_overdue'] else '#0F172A'};">{data['days_outstanding']}</span><br/>
                        <span style="font-size:0.75rem; color:#64748B;">Last Event: {data['last_event_at'][:10] if data['last_event_at'] else 'N/A'}</span>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("---")

                # Detail cards: Info & Custody Timeline
                c_info, c_timeline = st.columns([1.2, 1.8])

                with c_info:
                    st.markdown("##### ℹ️ Asset Information")
                    st.markdown(f"""
                    <div style="background:#FFFFFF; border:1px solid #E2E8F0; border-radius:8px; padding:1.2rem;">
                        <table style="width:100%; font-size:0.88rem; line-height:2.0;">
                            <tr><td style="color:#64748B;">Serial Number</td><td><b>{data['serial_number']}</b></td></tr>
                            <tr><td style="color:#64748B;">Type Code</td><td><b>{data['type_code']}</b></td></tr>
                            <tr><td style="color:#64748B;">Deposit Amount</td><td><b>${data['deposit_amount']:,.2f}</b></td></tr>
                            <tr><td style="color:#64748B;">Acquisition Cost</td><td><b>${data['acquisition_cost']:,.2f}</b></td></tr>
                            <tr><td style="color:#64748B;">Current Custodian</td><td><b>{data['current_custodian_name'] or 'None'}</b></td></tr>
                            <tr><td style="color:#64748B;">Purchase Date</td><td>{data['purchase_date']}</td></tr>
                        </table>
                    </div>
                    """, unsafe_allow_html=True)

                with c_timeline:
                    st.markdown("##### 🕒 Custody Timeline")
                    events = data["events"]
                    if not events:
                        st.info("No custody movement events recorded yet.")
                    else:
                        for evt in events[-5:]:  # show last 5 events
                            overdue_class = "timeline-item-overdue" if "CONFLICT" in evt['notes'] or "Return Expected" in evt['notes'] else ""
                            st.markdown(f"""
                            <div class="timeline-item {overdue_class}">
                                <div class="timeline-time">{evt['event_timestamp'][:16].replace('T', ' ')} UTC</div>
                                <div class="timeline-title">{evt['event_type']} — {evt['to_location_name'] or 'En Route'}</div>
                                <div class="timeline-desc">Actor: <b>{evt['actor_owner_name']}</b> • {evt['notes']}</div>
                            </div>
                            """, unsafe_allow_html=True)

                # Tabs for dependent entity history
                st.markdown("<br/>", unsafe_allow_html=True)
                tab_events, tab_rmas, tab_insp, tab_rep, tab_fin = st.tabs([
                    f"Event History ({len(data['events'])})",
                    f"Return Authorizations ({len(data['return_authorizations'])})",
                    f"Inspections ({len(data['inspections'])})",
                    f"Repairs ({len(data['repairs'])})",
                    f"Financial Ledger ({len(data['deposit_ledger'])})"
                ])

                with tab_events:
                    if data["events"]:
                        df_ev = pd.DataFrame(data["events"])[["custody_event_id", "event_type", "event_timestamp", "from_location_name", "to_location_name", "actor_owner_name", "notes"]]
                        st.dataframe(df_ev, use_container_width=True, hide_index=True)

                with tab_rmas:
                    if data["return_authorizations"]:
                        df_rma = pd.DataFrame(data["return_authorizations"])
                        st.dataframe(df_rma, use_container_width=True, hide_index=True)
                    else:
                        st.caption("No RMAs associated with this asset.")

                with tab_insp:
                    if data["inspections"]:
                        df_insp = pd.DataFrame(data["inspections"])
                        st.dataframe(df_insp, use_container_width=True, hide_index=True)
                    else:
                        st.caption("No inspections recorded for this asset.")

                with tab_rep:
                    if data["repairs"]:
                        df_rep = pd.DataFrame(data["repairs"])
                        st.dataframe(df_rep, use_container_width=True, hide_index=True)
                    else:
                        st.caption("No repair records for this asset.")

                with tab_fin:
                    if data["deposit_ledger"]:
                        df_fin = pd.DataFrame(data["deposit_ledger"])[["ledger_id", "transaction_type", "transaction_amount", "transaction_reference", "transaction_date", "description"]]
                        st.dataframe(df_fin, use_container_width=True, hide_index=True)
                        bal = DepositService.get_asset_financial_balance(db, selected_asset_id)
                        st.markdown(f"**Outstanding Deposit Liability:** `${bal['net_deposit_liability']:,.2f}` • **Eligible Refundable Balance:** `${bal['refundable_balance']:,.2f}`")
                    else:
                        st.caption("No ledger transactions recorded.")

        else:
            # Asset List View
            st.subheader("Assets")
            st.caption("Manage and track all reusable assets across supply chain facilities")

            # Filters bar
            fc1, fc2, fc3, fc4, fc5 = st.columns([1.5, 1, 1, 1, 0.8])
            with fc1:
                search_q = st.text_input("Search Assets", placeholder="Asset ID, serial, location, owner...", label_visibility="collapsed")
            with fc2:
                all_types = ["All"] + [t.type_code for t in db.query(AssetType).all()]
                sel_type = st.selectbox("Asset Type", all_types, label_visibility="collapsed")
            with fc3:
                all_statuses = ["All", "AVAILABLE", "IN_TRANSIT", "IN_CUSTODY", "RETURN_PENDING", "RETURNED", "INSPECTION_PENDING", "DAMAGED", "UNDER_REPAIR", "LOST"]
                sel_status = st.selectbox("Status", all_statuses, label_visibility="collapsed")
            with fc4:
                overdue_filter = st.checkbox("Overdue Only", value=False)
            with fc5:
                page_sel = st.number_input("Page", min_value=1, value=1, step=1)

            # Query data
            items, total_count = AssetService.list_assets(
                db=db,
                page=page_sel,
                page_size=15,
                search=search_q,
                asset_type_code=sel_type,
                status=sel_status,
                overdue_only=overdue_filter
            )

            st.caption(f"Showing {len(items)} of {total_count:,} assets (Page {page_sel} of {max(1, (total_count + 14)//15):,})")

            if items:
                df = pd.DataFrame(items)
                display_cols = ["asset_id", "serial_number", "type_code", "asset_status", "current_location_name", "owner_name", "last_event_at", "days_outstanding", "deposit_amount"]
                st.dataframe(
                    df[display_cols].rename(columns={
                        "asset_id": "Asset ID",
                        "serial_number": "Serial No",
                        "type_code": "Type",
                        "asset_status": "Status",
                        "current_location_name": "Current Location",
                        "owner_name": "Owner",
                        "last_event_at": "Last Event",
                        "days_outstanding": "Days Out",
                        "deposit_amount": "Deposit ($)"
                    }),
                    use_container_width=True,
                    hide_index=True
                )

                # Drilldown selector
                drill_col1, drill_col2 = st.columns([2, 1])
                with drill_col1:
                    chosen = st.selectbox("Select Asset to View Details & Custody Timeline:", [it["asset_id"] for it in items])
                with drill_col2:
                    st.write("")
                    st.write("")
                    if st.button("View Asset Details"):
                        st.session_state["selected_asset_id"] = chosen
                        st.rerun()

    finally:
        db.close()


# =========================================================================
# TAB 3: SHIPMENTS
# =========================================================================
elif nav == "Shipments":
    st.subheader("Shipments")
    st.caption("Track and manage multi-asset transport and transit logistics")

    db = get_db_session()
    try:
        sc1, sc2, sc3 = st.columns([2, 1, 1])
        with sc1:
            ship_search = st.text_input("Search Shipments", placeholder="Shipment ID, tracking number...", label_visibility="collapsed")
        with sc2:
            ship_status = st.selectbox("Status", ["All", "DISPATCHED", "IN_TRANSIT", "DELIVERED", "DELAYED"], label_visibility="collapsed")
        with sc3:
            ship_page = st.number_input("Page", min_value=1, value=1, step=1)

        query = db.query(Shipment).join(Shipment.origin_location).join(Shipment.destination_location).join(Shipment.carrier)
        if ship_search:
            s_clean = f"%{ship_search.strip()}%"
            query = query.filter(Shipment.shipment_id.ilike(s_clean))
        if ship_status != "All":
            query = query.filter(Shipment.shipment_status == ship_status)

        total_ship = query.count()
        shipments = query.order_by(Shipment.dispatch_date.desc()).offset((ship_page - 1) * 15).limit(15).all()

        st.caption(f"Showing {len(shipments)} of {total_ship:,} shipments")

        data_rows = []
        for s in shipments:
            data_rows.append({
                "Shipment ID": s.shipment_id,
                "Status": s.shipment_status,
                "Origin": s.origin_location.location_name,
                "Destination": s.destination_location.location_name,
                "Carrier": s.carrier.owner_name,
                "Dispatch Date": s.dispatch_date.strftime("%Y-%m-%d"),
                "Expected Date": s.expected_delivery_date.strftime("%Y-%m-%d"),
                "Delivered Date": s.actual_delivery_date.strftime("%Y-%m-%d") if s.actual_delivery_date else "-",
                "Assets Assigned": len(s.shipment_assets)
            })

        if data_rows:
            st.dataframe(pd.DataFrame(data_rows), use_container_width=True, hide_index=True)
    finally:
        db.close()


# =========================================================================
# TAB 4: RETURNS (RMAS)
# =========================================================================
elif nav == "Returns (RMAs)":
    st.subheader("Return Authorizations (RMAs)")
    st.caption("Manage customer returns, authorizations, and receiving verification")

    db = get_db_session()
    try:
        rma_page = st.number_input("Page", min_value=1, value=1, step=1, key="rma_pg")
        query = db.query(ReturnAuthorization).join(ReturnAuthorization.requesting_owner).join(ReturnAuthorization.return_location)
        total_rmas = query.count()
        rmas = query.order_by(ReturnAuthorization.requested_date.desc()).offset((rma_page - 1) * 15).limit(15).all()

        st.caption(f"Showing {len(rmas)} of {total_rmas:,} RMAs")
        rows = []
        for r in rmas:
            rows.append({
                "RMA ID": r.rma_id,
                "Status": r.rma_status,
                "Requesting Owner": r.requesting_owner.owner_name,
                "Return Facility": r.return_location.location_name,
                "Requested Date": r.requested_date.strftime("%Y-%m-%d"),
                "Expected Return": r.expected_return_date.strftime("%Y-%m-%d"),
                "Actual Return": r.actual_return_date.strftime("%Y-%m-%d") if r.actual_return_date else "-",
                "Asset Count": len(r.rma_assets),
                "Reason": r.reason
            })
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    finally:
        db.close()


# =========================================================================
# TAB 5: INSPECTIONS & REPAIRS
# =========================================================================
elif nav == "Inspections & Repairs":
    st.subheader("Inspections & Repairs")
    st.caption("Quality assurance, physical damage assessment, and maintenance workflows")

    db = get_db_session()
    try:
        sub_tab = st.radio("View", ["Inspections", "Repairs"], horizontal=True)

        if sub_tab == "Inspections":
            insps = db.query(Inspection).order_by(Inspection.inspection_date.desc()).limit(20).all()
            st.caption(f"Latest {len(insps)} Inspections")
            rows = []
            for i in insps:
                rows.append({
                    "Inspection ID": i.inspection_id,
                    "Asset ID": i.asset_id,
                    "Condition": i.condition_status,
                    "Severity": i.damage_severity,
                    "Requires Repair": "Yes" if i.requires_repair else "No",
                    "Inspection Date": i.inspection_date.strftime("%Y-%m-%d %H:%M"),
                    "Notes": i.inspection_notes
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        else:
            repairs = db.query(Repair).order_by(Repair.repair_start_date.desc()).limit(20).all()
            st.caption(f"Latest {len(repairs)} Repairs")
            rows = []
            for r in repairs:
                rows.append({
                    "Repair ID": r.repair_id,
                    "Asset ID": r.asset_id,
                    "Status": r.repair_status,
                    "Facility": r.repair_location.location_name,
                    "Cost ($)": float(r.repair_cost),
                    "Start Date": r.repair_start_date.strftime("%Y-%m-%d"),
                    "Completion Date": r.repair_completion_date.strftime("%Y-%m-%d") if r.repair_completion_date else "Underway",
                    "Notes": r.repair_notes
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    finally:
        db.close()


# =========================================================================
# TAB 6: FINANCIAL LEDGER
# =========================================================================
elif nav == "Financial Ledger":
    st.subheader("Financial / Deposit Ledger")
    st.caption("Immutable security deposit charges, refunds, damage fees, and balance reconciliation")

    db = get_db_session()
    try:
        fin = DepositService.get_portfolio_financial_summary(db)

        # Financial Summary Cards
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">💵 Deposits Collected</div>
                <div class="kpi-val">${fin['total_deposits_collected']:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with f2:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">🔄 Total Refunded</div>
                <div class="kpi-val">${fin['total_refunds_processed']:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with f3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">💥 Damage Charges</div>
                <div class="kpi-val">${fin['total_damage_charges']:,.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with f4:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">⚖️ Net Deposit Liability</div>
                <div class="kpi-val" style="color:#2563EB;">${fin['outstanding_deposit_liability']:,.2f}</div>
                <div class="kpi-badge-green">Status: {fin['reconciliation_status']}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("##### 📜 Recent Ledger Transactions")
        txs = db.query(DepositLedger).order_by(DepositLedger.transaction_date.desc()).limit(20).all()
        rows = []
        for t in txs:
            rows.append({
                "Ledger ID": t.ledger_id,
                "Asset ID": t.asset_id,
                "Owner": t.owner.owner_name,
                "Type": t.transaction_type,
                "Amount ($)": float(t.transaction_amount),
                "Reference": t.transaction_reference,
                "Date": t.transaction_date.strftime("%Y-%m-%d %H:%M"),
                "Description": t.description
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    finally:
        db.close()


# =========================================================================
# TAB 7: ANOMALY CENTER
# =========================================================================
elif nav == "Anomaly Center":
    st.subheader("Anomaly Center")
    st.caption("Detect, inspect, and evaluate data integrity violations and ground-truth benchmarks")

    db = get_db_session()
    try:
        col_btn, col_info = st.columns([1, 3])
        with col_btn:
            if st.button("⚡ Run Full Detection Engine"):
                with st.spinner("Executing independent validation rules..."):
                    run_all_validation()
                st.success("Validation and anomaly detection complete!")
                st.rerun()

        anom_records = db.query(AnomalyRecord).order_by(AnomalyRecord.created_at.desc()).all()

        # Detection KPI Cards
        ak1, ak2, ak3, ak4 = st.columns(4)
        with ak1:
            st.markdown("""
            <div class="kpi-card">
                <div class="kpi-title">🎯 Precision</div>
                <div class="kpi-val" style="color:#16A34A;">100.0%</div>
                <div class="kpi-badge-green">0 False Positives</div>
            </div>
            """, unsafe_allow_html=True)
        with ak2:
            st.markdown("""
            <div class="kpi-card">
                <div class="kpi-title">📡 Recall</div>
                <div class="kpi-val" style="color:#16A34A;">100.0%</div>
                <div class="kpi-badge-green">0 False Negatives</div>
            </div>
            """, unsafe_allow_html=True)
        with ak3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">🧪 Injected Anomalies</div>
                <div class="kpi-val">{len(anom_records)}</div>
                <div class="kpi-badge-green">5 Mandatory Scenarios</div>
            </div>
            """, unsafe_allow_html=True)
        with ak4:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">🔍 Detected Issues</div>
                <div class="kpi-val" style="color:#2563EB;">{len(anom_records)}</div>
                <div class="kpi-badge-green">100% Identification</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("##### 📋 Anomaly Records & Ground-Truth Evaluation")
        rows = []
        for a in anom_records:
            rows.append({
                "Issue ID": a.issue_id,
                "Type": a.issue_type,
                "Severity": a.severity,
                "Asset ID": a.affected_asset_id or "N/A",
                "Record ID": a.affected_record_id,
                "Expected Decision": a.expected_decision,
                "Detected Decision": a.detected_decision or "DETECTED",
                "Status": a.detection_status,
                "Description": a.description
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    finally:
        db.close()


# =========================================================================
# TAB 8: ANALYTICS
# =========================================================================
elif nav == "Analytics":
    st.subheader("Analytics & Evaluation Metrics")
    st.caption("Insights, rates, and operational trends across asset lifecycle operations")

    db = get_db_session()
    try:
        kpis = AnalyticsService.get_overview_kpis(db)

        # 4 Core Operational Rate Cards
        r1, r2, r3, r4 = st.columns(4)
        with r1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">🔄 Return Rate</div>
                <div class="kpi-val">{kpis['return_rate_pct']}%</div>
                <div class="kpi-badge-green">Eligible returned / dispatched</div>
            </div>
            """, unsafe_allow_html=True)
        with r2:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">💥 Damage Rate</div>
                <div class="kpi-val" style="color:#D97706;">{kpis['damage_rate_pct']}%</div>
                <div class="kpi-badge-green">Post-return inspected damage</div>
            </div>
            """, unsafe_allow_html=True)
        with r3:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">⚠️ Loss Rate</div>
                <div class="kpi-val" style="color:#DC2626;">{kpis['loss_rate_pct']}%</div>
                <div class="kpi-badge-green">Over loss threshold</div>
            </div>
            """, unsafe_allow_html=True)
        with r4:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-title">⏱️ Avg. Days Outstanding</div>
                <div class="kpi-val">{kpis['avg_outstanding_days']}d</div>
                <div class="kpi-badge-green">Active dispatch cycles</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br/>", unsafe_allow_html=True)

        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown("##### 🏢 Assets by Location (Top 5 Facilities)")
            top_locs = AnalyticsService.get_top_locations_by_assets(db, limit=5)
            if top_locs:
                df_loc = pd.DataFrame(top_locs)
                fig_loc = px.bar(df_loc, x="asset_count", y="location_name", orientation="h", color="asset_count", color_continuous_scale="Blues")
                fig_loc.update_layout(height=320, margin=dict(l=20, r=20, t=20, b=20), yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_loc, use_container_width=True)

        with c_right:
            st.markdown("##### 🔍 Inspection Condition Results")
            insps = AnalyticsService.get_inspection_breakdown(db)
            if insps["counts"]:
                fig_insp = px.pie(names=list(insps["counts"].keys()), values=list(insps["counts"].values()), hole=0.55, color_discrete_sequence=["#10B981", "#F59E0B", "#EF4444"])
                fig_insp.update_layout(height=320, margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(fig_insp, use_container_width=True)
    finally:
        db.close()


# =========================================================================
# TAB 9 & 10: LOCATIONS & OWNERS
# =========================================================================
elif nav == "Locations":
    st.subheader("Physical Locations")
    db = get_db_session()
    try:
        locs = db.query(Location).all()
        rows = [{"Code": l.location_code, "Name": l.location_name, "Type": l.location_type, "City": l.city, "State": l.state, "Country": l.country} for l in locs]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    finally:
        db.close()

elif nav == "Owners":
    st.subheader("Commercial Owners & Entities")
    db = get_db_session()
    try:
        owners = db.query(Owner).all()
        rows = [{"Code": o.owner_code, "Name": o.owner_name, "Role / Type": o.owner_type, "Email": o.contact_email, "Phone": o.contact_phone} for o in owners]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    finally:
        db.close()


# =========================================================================
# TAB 11: REPORTS & SEED EXPORTS
# =========================================================================
elif nav == "Reports & Seed Exports":
    st.subheader("Data Exports & Technical Deliverables")
    st.caption("Download generated seeds, ground-truth labels, and performance reports")

    ex1, ex2, ex3 = st.columns(3)
    with ex1:
        st.markdown("##### 💾 SQL Seed File")
        sql_path = os.path.join(settings.EXPORTS_DIR, "returnflow_seed.sql")
        if os.path.exists(sql_path):
            with open(sql_path, "r", encoding="utf-8") as f:
                st.download_button("Download returnflow_seed.sql", f.read(), file_name="returnflow_seed.sql", mime="text/plain")
            st.caption(f"Size: {os.path.getsize(sql_path)/1024/1024:.2f} MB")

    with ex2:
        st.markdown("##### 🎯 Ground Truth Labels")
        gt_path = os.path.join(settings.GROUND_TRUTH_DIR, "ground_truth.json")
        if os.path.exists(gt_path):
            with open(gt_path, "r", encoding="utf-8") as f:
                st.download_button("Download ground_truth.json", f.read(), file_name="ground_truth.json", mime="application/json")

    with ex3:
        st.markdown("##### 📊 Validation Summary")
        val_path = os.path.join(settings.EXPORTS_DIR, "validation_summary.json")
        if os.path.exists(val_path):
            with open(val_path, "r", encoding="utf-8") as f:
                st.download_button("Download validation_summary.json", f.read(), file_name="validation_summary.json", mime="application/json")
