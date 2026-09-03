import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from app.core.exceptions import database_error
from app.core import auth
from app.db.session import get_db

router = APIRouter()


@router.get("/kpis/history")
async def get_kpi_history(
    days: int = Query(30, ge=7, le=90),
    current_user: dict = Depends(auth.get_current_user_with_scope("DEPARTMENT_HEAD")),
    db=Depends(get_db),
):
    """Historical KPI trend (TASK-016): last N days from the daily KPI mart
    for 30/60/90-day charts (N must be a multiple the UI can bucket)."""
    try:
        rows = await db.fetch(
            "SELECT report_date, alert_rate, false_positive_rate, str_conversion_rate, "
            "first_review_sla_rate, case_cycle_time_days "
            "FROM mart.daily_aml_kpi "
            "WHERE report_date >= CURRENT_DATE - ($1 || ' days')::interval "
            "ORDER BY report_date ASC",
            str(days),
        )
    except Exception as e:
        raise database_error("reports.kpi_history", e)
    series = []
    for row in rows:
        item = dict(row)
        item["report_date"] = item["report_date"].isoformat()
        series.append(item)
    return {"days": days, "series": series}


@router.get("/kpis/export.csv", response_class=PlainTextResponse)
async def export_kpi_csv(
    days: int = Query(90, ge=7, le=365),
    current_user: dict = Depends(auth.get_current_user_with_scope("DEPARTMENT_HEAD")),
    db=Depends(get_db),
):
    """CSV export of the daily KPI mart (TASK-016)."""
    try:
        rows = await db.fetch(
            "SELECT * FROM mart.daily_aml_kpi "
            "WHERE report_date >= CURRENT_DATE - ($1 || ' days')::interval "
            "ORDER BY report_date ASC",
            str(days),
        )
    except Exception as e:
        raise database_error("reports.kpi_export", e)
    if not rows:
        return "report_date,no_data\n"
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(rows[0].keys())
    for row in rows:
        writer.writerow([getattr(row, k) for k in row.keys()])
    return buffer.getvalue()

@router.get("/monthly")
async def get_monthly_report(
    current_user: dict = Depends(auth.get_current_user_with_scope("DEPARTMENT_HEAD")),
    db=Depends(get_db)
):
    """
    Generate KPIs and Case Management metrics for the Department Head dashboard.
    """
    try:
        # Aggregated Status Counts
        status_rows = await db.fetch("SELECT status, COUNT(*) FROM app.alerts GROUP BY status")
        status_counts = {row['status']: row['count'] for row in status_rows}
        
        # Senior Investigator Approvals (Checkers)
        checker_rows = await db.fetch(
            """
            SELECT u.username, COUNT(c.case_id) as case_count
            FROM app.cases c
            JOIN app.app_users u ON c.approver_id = u.user_id
            WHERE c.status = 'closed'
            GROUP BY u.username
            """
        )
        checker_metrics = [{"investigator": row['username'], "approved_cases": row['case_count']} for row in checker_rows]
        
        return {
            "status_metrics": status_counts,
            "checker_metrics": checker_metrics
        }
    except Exception as e:
        raise database_error("reports.monthly", e)

@router.get("/kpis")
async def get_daily_kpis(
    current_user: dict = Depends(auth.get_current_user_with_scope("DEPARTMENT_HEAD")),
    db=Depends(get_db)
):
    """
    Retrieve the latest Daily AML KPIs from the datamart for the Governance MIS dashboard.
    """
    try:
        query = "SELECT * FROM mart.daily_aml_kpi ORDER BY report_date DESC LIMIT 1"
        row = await db.fetchrow(query)
        if not row:
            # Return empty or placeholder if ETL hasn't run yet
            return {"status": "no_data"}
        
        # Convert record to dict, standardizing dates as strings if necessary
        data = dict(row)
        if 'report_date' in data and data['report_date']:
            data['report_date'] = data['report_date'].isoformat()
        if 'updated_at' in data and data['updated_at']:
            data['updated_at'] = data['updated_at'].isoformat()
            
        return data
    except Exception as e:
        raise database_error("reports.kpis", e)
