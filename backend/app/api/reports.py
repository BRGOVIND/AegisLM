import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import Attack, Report, TestRun
from app.reports.generator import generate_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


class ReportRequest(BaseModel):
    model_name: str


class ReportResponse(BaseModel):
    id: int
    model_name: str
    generated_at: datetime
    report_data: dict

    model_config = {"from_attributes": True}


@router.post("", response_model=ReportResponse)
async def create_report(
    request: ReportRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TestRun)
        .options(selectinload(TestRun.attack))
        .where(TestRun.model_name == request.model_name)
    )
    test_runs = result.scalars().all()

    if not test_runs:
        raise HTTPException(
            status_code=400,
            detail="No test runs found for this model",
        )

    report_data = generate_report(request.model_name, test_runs)

    report = Report(
        model_name=request.model_name,
        report_data=report_data,
        generated_at=datetime.now(timezone.utc),
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    return report


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    model_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Report).order_by(Report.generated_at.desc())
    if model_name:
        query = query.where(Report.model_name == model_name)

    result = await db.execute(query)
    reports = result.scalars().all()
    return reports


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    return report


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()

    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    return Response(
        content=json.dumps(report.report_data, indent=2),
        media_type="application/json",
        headers={
            "Content-Disposition": f"attachment; filename=redforge-report-{report.model_name}-{report.id}.json"
        },
    )
