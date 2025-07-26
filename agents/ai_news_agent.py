#main.py

#Imports and .env loading
import feedparser, os, yagmail
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

# Load .env only if it exists (for local runs)
if os.path.exists(".env"):
    load_dotenv()

# Secrets will come from GitHub Actions in production

# Module2: Ingest News - This script fetches the latest articles from Wired's AI section RSS feed
def fetch_articles():
    feed = feedparser.parse("https://www.wired.com/feed/tag/ai/latest/rss")
    articles = []
    for entry in feed.entries:
        summary = entry.get("summary", "") or entry.get("description", "")
        articles.append({
            'title': entry.title,
            'link': entry.link,
            'summary': summary # May be empty; will scrape later if needed
        })
    return articles

#Module2b: Scrape Full Article
def scrape_article(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'} #User-Agent: string that identifies your browser. Setting it value to fake browser ID, and not be flagged as bot
        # 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36' #more detailed and convincing modern browser signature
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        paragraphs = soup.find_all('p')
        full_text = ' '.join(p.get_text() for p in paragraphs)
        return full_text.strip()[:2000] # Truncate long content
    except Exception as e:
        print(f"⚠️ Failed to scrape article: {url}")
        return ""
    
#Module3: Clean and Filter - This script cleans the fetched articles and filters them based on relevance to AI
KEYWORDS= ["open source", "LLM", "multi-agent", "AI", "artificial intelligence", "machine learning", "deep learning", "OpenAI","chatbot", "perplexity", "GPT", "Generative AI", "AI agent", "AI assistant", "AI tools", "AI applications", "AI research", "AI development", "AI ethics", "AI safety"]
def is_relevant(text):
    return any(kw.lower() in text.lower() for kw in KEYWORDS)

def clean(text):
    return text.replace('\n', ' ').strip()

#Module4: Summrize with GPT - This script uses OpenAI's GPT 4 model to summarize the articles
# openai.api_key = os.getenv("OPENAI_API_KEY") - this is old syntax for old version
client = OpenAI() # new syntax for new version
def summarize_text(text):
    prompt = f"""Summarise this AI article in 2-3 short bullet points. Make it human-readable and insightful:\n\n{text}"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7           
    )
    return response.choices[0].message.content

#Module5: Save Output to a File - This script saves the summarized articles to a text file
def save_summaries(summaries):
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"AI_News_Summary_{date_str}.txt"
    with open(filename, 'w') as f:
        for title, summary, link in summaries:
            f.write(f"### {title}\n")
            f.write(f"{summary}\n")
            f.write(f"🔗 Read more: {link}\n\n") #Clean clickable link
    return filename

#Module5b: Return HTML() version
def generate_html_summaries(summaries):
    html = "<h2>📰 Your Daily AI News Summary</h2><ul>"
    for title, summary, link in summaries:
        html += f"<li><strong>{title}</strong><br>{summary}<br><a href='{link}'>🔗 Read more</a><br><br><br</li>"
    html += "</ul>"
    return html

#Module6: Send Email with Attachment - This script sends the summary file via email
def send_email(filename, summary_html):
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASSWORD")
    email_recipients = os.getenv("EMAIL_RECIPIENTS", "").split(",")
    # Strip any spaces and ignore empty entries
    email_recipients = [e.strip() for e in email_recipients if e.strip()]

    yag = yagmail.SMTP(user=email_user, password=email_pass)

    subject = "Your Daily AI News Summary"
    body = "Hey! Here's your AI news digest for today. See attached."

    yag.send(to=email_user,
             bcc=email_recipients,
             subject=subject,
             contents=[summary_html],
             attachments=filename
    )
#confirmation log
#print(f"📧 Sent summary to (bcc): {', '.join(email_recipients)}")
    
#Module7: Orchestrate and Automate
#pull everything together into a signle run_agent() function
def run_agent():
    articles = fetch_articles()
    summaries = []

    for article in articles:
        raw_text = article['summary'] or scrape_article(article['link']) #short-circuit evaluation, shortcut for if-else
        text = clean(raw_text)

        if is_relevant(text):
            summary = summarize_text(text)
            summaries.append((article['title'], summary, article['link']))

    # If no summaries were generated, we can skip sending an email. If emailing, send both - html and txt versions
    if summaries:
        summary_html = generate_html_summaries(summaries)
        filename = save_summaries(summaries)
        send_email(filename, summary_html)
