from agents.ai_news_agent import run_agent
import schedule, time

##automate for local runs
# schedule.every().day.at("08:00").do(run_agent)
# while True:
#     schedule.run_pending()
#     time.sleep(30)

##run in git actions
if __name__ == "__main__":
    run_agent()   # Runs once (schedule sat in the yml file) and exits