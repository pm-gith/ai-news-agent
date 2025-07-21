# AI News Summarizer Agent

This is a personal-project Python agent that fetches AI-related news from RSS feeds, filters relevant topics based on keywords, summarizes articles using OpenAI's GPT models, and emails daily digest.

## Features

- Pulls articles from RSS feeds (e.g. Wired). Can be repurposed for other news
- Filters relevant AI topics based on custom keywords
- Cleans and optionally scrapes full article text
- Summarizes articles using GPT (OpenAI API). Default GPT 3.5
- Sends daily email with bullet summaries and article link
- Modular & extensible codebase
- `.env.example` provided

## Project Structure
```
ai-news-agent/
├── agents/
│   └── ai\_news\_agent.py      # Core logic of the agent. Update inputs on this file to repurpose agent for other news outlets
├── shared/
│   └── common\_utils.py        # Shared helper functions (empty for now)
├── main.py                     # Scheduler and agent trigger
├── .env                        # Your secret keys (DO NOT COMMIT)
├── .env.example                # Sample template for your .env
├── .gitignore                  # Files to ignore (like .env, venv)
└── README.md                   # You're reading this
```

## Getting Started

1. Clone the repo:

   bash
   git clone https://github.com/pm-gith/ai-news-agent.git
   cd ai-news-agent

2. Create virtual environment:

   bash
   python -m venv venv
   source venv/bin/activate

3. Install Dependencies
   pip install <package>
   ## Dependencies/packages
   ```
    Python 3.8+
    openai, feedparser, beautifulsoup4, bs4, yagmail, schedule, time, python-dotenv, requests
    ```

3. Create your `.env` file at the root of your project, from the example:
    ```
    EMAIL_USER=your@email.com
    EMAIL_PASSWORD=your_email_password
    EMAIL_RECIPIENTS=comma,separated,list
    OPENAI_API_KEY=your_openai_key
    ```
    
    Never commit your .env file - it is already ignored via .gitignore

4. Run the Agent Manually, or let it run automatically on a daily schedule as configured

    python main.py
    
    Scheduler - The `main.py` script uses the `schedule` library to run the agent daily at 9 AM. You can edit the time as needed.



## License
This project is licensed under Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)

You are free to:
- Share — copy and redistribute the material in any medium or format
- Adapt — remix, transform, and build upon the material

Under the following terms:
- Attribution — You must give appropriate credit.
- NonCommercial — You may not use the material for commercial purposes.

No warranties are given. The license may not give you all of the permissions necessary for your intended use.

Contributing
Contributions, issues, and feature requests are welcome! Open a pull request or submit an issue to improve this project.

Author
Created by Prachi Mishra. For questions or collaboration, feel free to reach out.