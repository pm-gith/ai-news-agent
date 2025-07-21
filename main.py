from agents.ai_news_agent import run_agent
import schedule
import time

#automate
<<<<<<< HEAD
schedule.every().day.at("15:53").do(run_agent)
=======
schedule.every().day.at("16:51").do(run_agent)
>>>>>>> feature/clickable-links

while True:
    schedule.run_pending()
    time.sleep(10)