from agents.ai_news_agent import run_agent
import schedule
import time

#automate
schedule.every().day.at("15:53").do(run_agent)

while True:
    schedule.run_pending()
    time.sleep(10)