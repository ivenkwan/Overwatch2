from fastapi import APIRouter, Depends, HTTPException
from app.core import auth
from app.db.session import get_db

router = APIRouter()

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
        raise HTTPException(status_code=500, detail=str(e))

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
        raise HTTPException(status_code=500, detail=str(e))
