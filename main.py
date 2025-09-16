from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from datetime import date, datetime
import shutil
import os

app = FastAPI(title="File Upload App")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ROOT_DIR = Path("files")
ROOT_DIR.mkdir(exist_ok=True)


def build_storage_path(d: date) -> Path:
    """Return directory path for a given date (year/month/day)."""
    return ROOT_DIR / str(d.year) / f"{d.month:02d}" / f"{d.day:02d}"


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(..., description="CSV file to upload"),
    file_date: date = Form(default_factory=date.today, description="Date for file"),
):
    """
    Upload a CSV file for a given date.  
    File will be stored in files/YYYY/MM/DD/.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are allowed")

    storage_path = build_storage_path(file_date)
    storage_path.mkdir(parents=True, exist_ok=True)

    destination = storage_path / file.filename

    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return JSONResponse(
        content={"data": {"message": f"File saved at {destination}"}},
        status_code=201,
    )


@app.get("/files/dates")
async def list_dates():
    """
    Return all dates (YYYY-MM-DD) that have at least one file.
    """
    dates = []
    for year_dir in ROOT_DIR.iterdir():
        if year_dir.is_dir():
            for month_dir in year_dir.iterdir():
                for day_dir in month_dir.iterdir():
                    if any(day_dir.iterdir()):  # has files
                        try:
                            d = date(
                                int(year_dir.name),
                                int(month_dir.name),
                                int(day_dir.name),
                            )
                            dates.append(d.isoformat())
                        except ValueError:
                            continue
    return {"data": {"dates": sorted(dates)}}


@app.get("/files/{file_date}")
async def get_files_by_date(file_date: str):
    """
    List all files for a given date (format: YYYY-MM-DD).
    """
    try:
        d = datetime.strptime(file_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")

    storage_path = build_storage_path(d)
    if not storage_path.exists():
        return {"data": {"files": []}}

    files = [f.name for f in storage_path.iterdir() if f.is_file()]
    return {"data": {"files": files}}


@app.get("/download/{file_date}/{filename}")
async def download_file(file_date: str, filename: str):
    """
    Download a specific file for a given date.
    """
    try:
        d = datetime.strptime(file_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")

    file_path = build_storage_path(d) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, filename=filename)
