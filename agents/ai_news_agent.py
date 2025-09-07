#main.py

#Imports and .env loading
import feedparser, os, yagmail
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
from bs4 import BeautifulSoup
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Load .env only if it exists (for local runs)
if os.path.exists(".env"):
    load_dotenv()
elif not (os.getenv("OPENAI_API_KEY") and os.getenv("EMAIL_USER") and os.getenv("EMAIL_PASSWORD") and os.getenv("EMAIL_RECIPIENTS")):
    print("❌ No .env found and required environment variables are missing. Exiting.")
    sys.exit(1)  # Cancel run if neither available

# Secrets will come from GitHub Actions in production

# Module2: Ingest News - This script fetches the latest articles from Wired's AI section RSS feed
def fetch_articles():
    # rss_feeds = ["https://www.wired.com/feed/tag/ai/latest/rss","https://techcrunch.com/tag/artificial-intelligence/feed/","https://www.theverge.com/rss/ai-artificial-intelligence",
                # "https://www.zdnet.com/topic/ai/rss.xml","https://www.engadget.com/rss.xml","https://arstechnica.com/feed/"]
    rss_feeds = ["https://www.wired.com/feed/tag/ai/latest/rss"]
    articles = []
    for url in rss_feeds:
        feed = feedparser.parse(url)
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
KEYWORDS= ["open source", "LLM", "multi-agent", "AI", "artificial intelligence", "machine learning", "deep learning", "OpenAI","chatbot", 
           "perplexity", "GPT", "Generative AI", "AI agent", "AI assistant", "AI tools", "AI applications", "AI research", "AI development",
             "AI ethics", "AI safety", "anthropic", "copilot", "gemini", "openai", "grok"]
def is_relevant(text): #pick articles only with these keywords. reducing inupts to LLM and save cost
    return any(kw.lower() in text.lower() for kw in KEYWORDS)

def clean(text):
    return text.replace('\n', ' ').strip()

#Module4: Summrize with GPT - This script uses OpenAI's GPT 4 model to summarize the articles
# openai.api_key = os.getenv("OPENAI_API_KEY") - this is old syntax for old version
client = OpenAI() # new syntax for new version
def summarize_and_score(text): #GPT rating and summarization
    system_prompt = (
        "You are an analyst scoring and summarizing news for AI professionals. Be concise, consistent, and only use the provided text. "
        "5 - Critical: landmark lawsuits, copyright/ethics precedents, major infra or model breakthroughs, regulations/standards, widely adopted platform shifts, research overturning assumptions."
        "4 - High: infra constraints like chips/energy, major vendor/legal moves, market shifts, strong OSS/regional models with adoption."
        "3 - Medium: sector case studies, infra/renewables stories, significant product updates showing industry trends."
        "2 - Low: niche/speculative, limited-scope use cases, small-scale deployments, think-pieces with minor practitioner relevance."
        "1 - Minimal: celebrity, hype, spiritual/speculative claims with no material impact."
        "Output should include only rating (int 1-5) and bullets (array of 2-3 short strings). "
    )

    prompt = f"""Rate the following news for its importance to AI professionals (scale 1-5). Prefer practical impact over hype. Use this rubric:
    If score is at least 3/5, summarise this AI article in 2-3 short bullet points. Make it human-readable and insightful.:\n\n{text}"""
        # "Include rating only once, not with bullets:\n\n{text}"""
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": system_prompt},{"role": "user", "content": prompt}],
        temperature=0.7           
    )
    full = response.choices[0].message.content #full response from GPT
    lines = full.strip().split('\n')

    # Extract score (looks for any line containing "rating")
    score = 3  # default
    for line in lines:
        if "rating" in line.lower():
            try:
                score = int(line.split(":")[-1].split("/")[0].strip())
            except:
                pass
            break

    # Remove any line that contains 'rating' or 'rated' so it never leaks into output
    summary_lines = [line for line in lines if not any(t in line.lower() for t in ("rating", "rated"))]
    summary = "\n".join(summary_lines).strip()

    return summary, score

#Module 4b: Semantic Grouping
def get_embedding(text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small"
    )
    return np.array(response.data[0].embedding)

def group_similar_articles(articles, threshold=0.75):
    grouped = []
    used = set()
    embeddings = [get_embedding(article['title']) for article in articles]
    for i, a in enumerate(articles):
        if i in used:
            continue
        group = [a]
        used.add(i)
        for j in range(i+1, len(articles)):
            if j in used:
                continue
            sim = cosine_similarity([embeddings[i]], [embeddings[j]])[0][0]
            if sim > threshold:
                group.append(articles[j])
                used.add(j)
        grouped.append(group)
    return grouped

#Module5: Save Output to a File - This script saves the summarized articles to a text file
def save_summaries(summaries):
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"AI_News_Summary_{date_str}.txt"
    with open(filename, 'w') as f:
        for title, summary, link, score in summaries:
            f.write(f"### {title}\n")
            f.write(f"{summary}\n")
            f.write(f"🔗 Read more: {link}\n\n") #Clean clickable link
    return filename

#Module5b: Return HTML() version
def generate_html_summaries(summaries):
    html = "<h2>📰 Your Daily AI News Summary</h2><ul>"
    for title, summary, link, score in summaries:
        html += f"<li><strong>{title} </strong><br>{summary}<br><a href='{link}'>🔗 Read more</a><br><br><br></li>"
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
    # filtered = [a for a in articles if is_relevant(a['summary'] or scrape_article(a['link']))]
    filtered = [a for a in articles if is_relevant(a['summary'])]
    grouped = group_similar_articles(filtered)
    final_summaries = []

    for group in grouped:
        combined_text = "\n".join(clean(a['summary'] or scrape_Article(a['link'])) for a in group)
        summary, score = summarize_and_score(combined_text)
        if score >= 3 and summary.strip():
            title = group[0]['title']
            links = ", ".join([a['link'] for a in group])
            final_summaries.append((title, summary, links, score))

    final_summaries.sort(key=lambda x: x[3], reverse=True) #sort by score, highest first

    if len(final_summaries) == 0:
        print("No relevant articles found today. Skipping email.")
        return
    
    #Send up to 21 relevant articles, however many available
    top_articles = final_summaries[:21]
    
    summary_html = generate_html_summaries(top_articles)
    filename = save_summaries(top_articles)
    send_email(filename, summary_html)
