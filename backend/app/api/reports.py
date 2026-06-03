import os

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.models.reports import ReportGenerateRequest, ReportItem, ReportsResponse
from app.services.report_service import report_service

router = APIRouter()


@router.get("/reports", response_model=ReportsResponse)
def list_reports():
    """List previously generated PDF reports (newest first)."""
    items = report_service.list_reports()
    return ReportsResponse(total=len(items), reports=items)


@router.post("/reports/generate", response_model=ReportItem, status_code=status.HTTP_201_CREATED)
def generate_report(req: ReportGenerateRequest):
    """Render and persist a PDF for the given window."""
    try:
        return report_service.generate(
            region=req.region,
            period=req.period,
            periodicity=req.periodicity,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/reports/{report_id}/download")
def download_report(report_id: str):
    """Stream the PDF file with the original filename."""
    try:
        path = report_service.get_path(report_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Report file is missing on disk")

    # Pull the friendly filename from the index entry.
    item = next((r for r in report_service.list_reports() if r.id == report_id), None)
    filename = item.file_name if item else f"{report_id}.pdf"
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=filename,
    )


@router.delete("/reports/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(report_id: str):
    """Delete the PDF file and its index entry."""
    try:
        report_service.delete(report_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")
