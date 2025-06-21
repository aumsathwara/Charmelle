import asyncio
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from apscheduler.schedulers.blocking import BlockingScheduler
from pathlib import Path
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

BASE = Path(__file__).resolve().parent
sched = BlockingScheduler(timezone="UTC")

def run_command(command, cwd):
    """Runs a command and logs its output."""
    process = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in iter(process.stdout.readline, ''):
        logging.info(line.strip())
    process.stdout.close()
    return_code = process.wait()
    if return_code:
        logging.error(f"Command '{' '.join(command)}' failed with return code {return_code}")

@sched.scheduled_job("cron", hour="*/3")
def delta_crawl():
    logging.info("Starting delta crawl job...")
    for spider in ("sephora", "ulta", "dermstore", "moidaus", "yesstyle"):
        logging.info(f"Running spider: {spider}")
        run_command(["scrapy", "crawl", spider], cwd=str(BASE / "crawler"))
    logging.info("Delta crawl job finished.")

@sched.scheduled_job("cron", hour="*", minute=10)
def run_etl():
    logging.info("Starting ETL and view refresh job...")
    python_exe = sys.executable
    run_command([python_exe, "etl/load_to_db.py"], cwd=str(BASE))
    run_command([python_exe, "etl/refresh_view.py"], cwd=str(BASE))
    logging.info("ETL and view refresh job finished.")

if __name__ == "__main__":
    logging.info("Starting a single run of all spiders and ETL process...")
    # For demonstration, run jobs once on startup
    delta_crawl()
    run_etl()
    logging.info("Single run finished.")
    # To run as a continuous scheduled service, uncomment the following lines:
    # logging.info("Starting scheduler...")
    # sched.start() 