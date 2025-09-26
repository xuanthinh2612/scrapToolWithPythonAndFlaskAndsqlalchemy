import schedule
import time
import threading
from scraper.uniqlo_crawl import start_crawl_uniqlo

def run_scheduler():
    schedule.every(3).hours.do(start_crawl_uniqlo)

    while True:
        schedule.run_pending()
        time.sleep(1)

# Khi app Flask khởi động thì chạy thread cho scheduler
def start_scheduler():
    t = threading.Thread(target=run_scheduler)
    t.daemon = True
    t.start()
