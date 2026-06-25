import scraper.dns_resolver
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import os
from typing import Optional

from generate_pdf import create_job_pdf

app = FastAPI(title="Govt Job Scraper API")

# Add CORS middleware if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the static web_ui directory at the root
# We will mount it after defining the API endpoints so that /api routes take precedence.

class CoreScraperRequest(BaseModel):
    org: Optional[str] = None
    watch_mode: bool = False
    interval: int = 30

class ScaleScraperRequest(BaseModel):
    limit: int = 20
    offset: int = 0

# Global variable to store running process info
running_process = None
LOG_FILE = "scraper_output.txt"

def run_scraper_process(cmd: list):
    global running_process
    # Terminate any existing running process
    if running_process is not None and running_process.poll() is None:
        try:
            running_process.terminate()
            running_process.wait(timeout=5)
        except Exception:
            running_process.kill()
    
    # Ensure log file exists or is cleared
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"--- Starting Scraper Task ---\nCommand: {' '.join(cmd)}\n")

    # Start new process and redirect stdout and stderr to the log file
    running_process = subprocess.Popen(
        cmd, 
        stdout=open(LOG_FILE, "a", encoding="utf-8"),
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        cwd=os.path.dirname(os.path.abspath(__file__))
    )

@app.post("/api/run_core")
def run_core(req: CoreScraperRequest, background_tasks: BackgroundTasks):
    import sys
    cmd = [sys.executable, "-u", "-m", "scraper.main"]
    if req.org:
        cmd.extend(["--org", req.org])
    if req.watch_mode:
        cmd.extend(["--watch", "--interval", str(req.interval)])
    
    background_tasks.add_task(run_scraper_process, cmd)
    return {"message": "Core scraper started", "command": " ".join(cmd)}

@app.post("/api/run_scale")
def run_scale(req: ScaleScraperRequest, background_tasks: BackgroundTasks):
    import sys
    cmd = [sys.executable, "-u", "run_all_orgs.py", "--limit", str(req.limit), "--offset", str(req.offset)]
    
    background_tasks.add_task(run_scraper_process, cmd)
    return {"message": "Scale scraper started", "command": " ".join(cmd)}

@app.get("/api/logs")
def get_logs():
    if not os.path.exists(LOG_FILE):
        return JSONResponse(content={"logs": "No logs available yet."})
    
    try:
        # Get the last 100 lines or read all if small
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # return last 100 lines to avoid massive payloads
            return JSONResponse(content={"logs": "".join(lines[-100:])})
    except Exception as e:
        return JSONResponse(content={"logs": f"Error reading logs: {str(e)}"})

@app.get("/api/download_pdf")
def download_pdf():
    pdf_path = "jobs_report.pdf"
    json_path = "scraped_jobs.json"
    
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="No scraped jobs found to generate PDF.")
        
    try:
        create_job_pdf(json_path=json_path, output_path=pdf_path)
        return FileResponse(
            path=pdf_path, 
            filename="Govt_Job_Scraper_Report.pdf", 
            media_type='application/pdf'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")

# Mount the static files (this MUST come after API routes)
app.mount("/", StaticFiles(directory="web_ui", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="127.0.0.1", port=8000, reload=True)
