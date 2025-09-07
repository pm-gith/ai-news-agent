#main.py

#Imports and .env loading
import feedparser, os, yagmail
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
from bs4 import BeautifulSoup
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import re, json
from datetime import datetime
from urllib.parse import urlparse

PUBLISHER_MAP = {
    "wired.com": "Wired",
    "www.wired.com": "Wired",
    "techcrunch.com": "TechCrunch",
    "www.techcrunch.com": "TechCrunch",
    "theverge.com": "The Verge",
    "www.theverge.com": "The Verge",
    "zdnet.com": "ZDNET",
    "www.zdnet.com": "ZDNET",
    "engadget.com": "Engadget",
    "www.engadget.com": "Engadget",
    "arstechnica.com": "Ars Technica",
    "www.arstechnica.com": "Ars Technica",
}

def pretty_source(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    if netloc in PUBLISHER_MAP:
        return PUBLISHER_MAP[netloc]
    # Fallback: strip www and TLD, capitalize first chunk
    base = netloc.replace("www.", "")
    main = base.split(".")[0]
    return main.capitalize()

def format_sources_md(sources):  # [(label, url)]
    if not sources:
        return ""
    return "Read more at " + ", ".join(f"[{label}]({url})" for label, url in sources)

def format_sources_html(sources):  # [(label, url)]
    if not sources:
        return ""
    return "Read more at " + ", ".join(f"<a href='{url}'>{label}</a>" for label, url in sources)

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
    rss_feeds = ["https://www.wired.com/feed/tag/ai/latest/rss","https://techcrunch.com/tag/artificial-intelligence/feed/","https://www.theverge.com/rss/ai-artificial-intelligence","https://www.zdnet.com/topic/ai/rss.xml","https://www.zdnet.com/topic/ai/rss.xml","https://arstechnica.com/feed/"]
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

def summarize_article(text: str) -> str:
    """Return a 2-3 bullet summary. No ratings, no meta commentary."""
    system_prompt = (
        "You are a crisp editor for AI professionals. "
        "Summarize using 2-3 short bullets. No rating, no preface, no conclusion. "
        "Only use information present in the text."
        )


    user_prompt = (
        "Summarize this article in 2-3 short bullets for AI professionals."
        "Make it human-readable and insightful. \n\n" + text
        )


    resp = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        )


    summary = resp.choices[0].message.content.strip()
    lines = [ln for ln in summary.split("\n") if not re.search(r"rating|rated|/5\\b", ln, flags=re.I)]
    return "\n".join(lines).strip()

# def summarize_and_score(text): #GPT rating and summarization
#     system_prompt = (
#         "You are an analyst scoring and summarizing news for AI professionals. Be concise, consistent, and only use the provided text. "
#         "5 - Critical: landmark lawsuits, copyright/ethics precedents, major infra or model breakthroughs, regulations/standards, widely adopted platform shifts, research overturning assumptions."
#         "4 - High: infra constraints like chips/energy, major vendor/legal moves, market shifts, strong OSS/regional models with adoption."
#         "3 - Medium: sector case studies, infra/renewables stories, significant product updates showing industry trends."
#         "2 - Low: niche/speculative, limited-scope use cases, small-scale deployments, think-pieces with minor practitioner relevance."
#         "1 - Minimal: celebrity, hype, spiritual/speculative claims with no material impact."
#         "Output should include only rating (int 1-5) and bullets (array of 2-3 short strings). "
#     )

#     prompt = f"""Rate the following news for its importance to AI professionals (scale 1-5). Prefer practical impact over hype. Use this rubric:
#     If score is at least 3/5, summarise this AI article in 2-3 short bullet points. Make it human-readable and insightful.:\n\n{text}"""
#         # "Include rating only once, not with bullets:\n\n{text}"""
    
#     response = client.chat.completions.create(
#         model="gpt-3.5-turbo",
#         messages=[{"role": "system", "content": system_prompt},{"role": "user", "content": prompt}],
#         temperature=0.7           
#     )
#     full = response.choices[0].message.content #full response from GPT
#     lines = full.strip().split('\n')

#     # Extract score (looks for any line containing "rating")
#     score = 3  # default
#     for line in lines:
#         if "rating" in line.lower():
#             try:
#                 score = int(line.split(":")[-1].split("/")[0].strip())
#             except:
#                 pass
#             break

#     # Remove any line that contains 'rating' or 'rated' so it never leaks into output
#     summary_lines = [line for line in lines if not any(t in line.lower() for t in ("rating", "rated"))]
#     summary = "\n".join(summary_lines).strip()

#     return summary, score

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
        for title, summary, sources, score in summaries:
            f.write(f"### {title}\n")
            f.write(f"{summary}\n")
            if sources:
                links_md = ", ".join(f"[{label}]({url})" for label, url in sources)
                f.write(f"🔗 Read more at {links_md}\n\n")
            else:
                f.write("\n")
    return filename




def generate_html_summaries(summaries):
    html = "<h2>📰 Your Daily AI News Summary</h2><ul>"
    for title, summary, sources, score in summaries:
        links_html = (
            "Read more at " + ", ".join(f"<a href=\"{url}\">{label}</a>" for label, url in sources)
        ) if sources else ""
        html += (
            f"<li><strong>{title}</strong><br>"
            f"{summary}<br>"
            f"{links_html}<br><br><br></li>"
        )
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
    


def score_articles_batch(items):
    chunks = []
    for i, it in enumerate(items, start=1):
        title = it.get("title", "").strip()
        text = (it.get("text", "") or "").strip()
        if len(text) > 800:
            text = text[:800]
            chunks.append(f"{i}. Title: {title}\nText:\n{text}")


    system_prompt = (
        "You are an analyst scoring news for AI professionals. Be decisive and consistent. "
        "Prefer practical impact over hype. Rate each item 1–5 using this scale: "
        "5 - Critical: landmark lawsuits, copyright/ethics precedents, major infra or model breakthroughs, regulations/standards, widely adopted platform shifts, research overturning assumptions."
        "4 - High: infra constraints like chips/energy, major vendor/legal moves, market shifts, strong OSS/regional models with adoption."
        "3 - Medium: sector case studies, infra/renewables stories, significant product updates showing industry trends."
        "2 - Low: niche/speculative, gambling, limited-scope use cases, small-scale deployments, think-pieces with minor practitioner relevance."
        "1 - Minimal: celebrity, hype, spiritual/speculative claims with no material impact."
        "Return ONLY compact JSON mapping index to rating, e.g. {\"scores\": {\"1\": 4, \"2\": 3}}."
        )


    user_prompt = (
        "Rate each item (1–5). Respond ONLY with JSON as {\"scores\": {\"<index>\": <int>}}. "
        "No prose, no explanations.\n\n" + "\n\n".join(chunks)
        )


    resp = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        )


    raw = resp.choices[0].message.content.strip()
    try:
        start = raw.find("{")
        end = raw.rfind("}")
        payload = raw[start:end+1] if (start != -1 and end != -1) else raw
        data = json.loads(payload)
        scores_map = data.get("scores", data)
    except Exception:
        return [3 for _ in items]


    out = []
    for i in range(1, len(items) + 1):
        val = scores_map.get(str(i)) if isinstance(scores_map, dict) else None
        try:
            out.append(int(val))
        except Exception:
            out.append(3)
    return out

#Module7: Orchestrate and Automate
#pull everything together into a signle run_agent() function
def run_agent():
    articles = fetch_articles()
    filtered = [a for a in articles if is_relevant(a['summary'])]
    grouped = group_similar_articles(filtered)
    groups = []
    for group in grouped:
        combined_text = "\n".join(clean(a['summary'] or scrape_article(a['link'])) for a in group)
        seen = set()
        sources = []
        for a in group:
            url = a['link']
            domain = urlparse(url).netloc.lower().replace("www.", "")
            if domain not in seen:
                sources.append((pretty_source(url), url))
                seen.add(domain)
        groups.append({
            "title": group[0]['title'],
            "text": combined_text,
            "sources": sources,
        })
    
    if not groups:
        print("No articles after prefiltering.")
        return


    scores = score_articles_batch([{ "title": g["title"], "text": g["text"] } for g in groups])
    for g, s in zip(groups, scores):
        g["score"] = s


    eligible = [g for g in groups if g["score"] >= 3]
    eligible.sort(key=lambda g: g["score"], reverse=True)
    top_n = eligible[:21]

    final_summaries = []
    for g in top_n:
        summary = summarize_article(g["text"])
        if summary.strip():
            final_summaries.append((g["title"], summary, g["sources"], g["score"]))

    if not final_summaries:
        print("No relevant articles scored high enough. Skipping email.")
        return

    summary_html = generate_html_summaries(final_summaries)
    filename = save_summaries(final_summaries)
    send_email(filename, summary_html)