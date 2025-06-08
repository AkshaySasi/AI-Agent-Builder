 ## AI Agent Builder

A Flask-based web application for creating and testing AI agents that perform specific tasks based on user prompts. The app supports three tasks: summarizing tweets and posting them, scraping Hacker News headlines and emailing them, and summarizing PDFs with file monitoring.

# Project Structure

main.py: Flask server handling agent creation, scheduling, and file uploads.
agents.py: Defines a simple agent executor to process prompts and invoke tools without an LLM dependency.
tools.py: Contains tools for interacting with the X API, scraping web pages, sending emails, and summarizing PDFs.
static/index.html: Frontend UI for interacting with the app.
requirements.txt: Lists all Python dependencies.
uploads/: Directory for storing uploaded PDFs.
agent_builder.log: Log file for debugging and monitoring.

# Setup Instructions

Prerequisites

Python 3.8 or higher
A virtual environment 
API credentials for X, OpenAI, and Gmail SMTP (optional for Google Custom Search)

# Installation

Clone the Repository or Create Project Directory

Create a directory named ai_agent_builder and place all provided files in it.


Set Up a Virtual Environment

On Windows:python -m venv venv
.\venv\Scripts\activate


On macOS/Linux:python3 -m venv venv
source venv/bin/activate




# Install Dependencies

Ensure requirements.txt is in the project directory, then run:pip install -r requirements.txt




# Configure Environment Variables

Create a .env file in the project root with the following:TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret
OPENAI_API_KEY=your_openai_api_key
SMTP_EMAIL=your_gmail_address
SMTP_PASSWORD=your_gmail_app_password
GOOGLE_API_KEY=your_google_api_key
GOOGLE_CSE_ID=your_google_cse_id
PORT=5000


X API Credentials: Obtain from https://developer.x.com/en/portal. Requires Basic tier for get_users_tweets.
OpenAI API Key: Obtain from https://platform.openai.com. Currently limited by quota; mock responses used.
SMTP Credentials: Use a Gmail App Password (https://myaccount.google.com/security).
Google Custom Search (Optional): For the web_search tool, get from https://programmablesearchengine.google.com.


# Run the Application

Start the Flask server:python main.py


The server runs on http://127.0.0.1:5000 by default. Check agent_builder.log for startup confirmation:2025-06-08 20:15:00,123 [INFO] APScheduler started successfully
2025-06-08 20:15:00,456 [INFO] Starting Flask server on port 5000





# Running and Testing the App - Access the Web Interface

Open http://127.0.0.1:5000 in your browser.
The UI includes fields for uploading PDFs, entering an email, specifying a prompt, and setting a schedule interval.

# Test the Twitter Agent

Prompt: "Summarize tweets from elonmusk and post the summary to Twitter"
Interval: 5 minutes
Steps:
Enter the prompt in the "Enter Prompt" field.
Set the interval to 5.
Click "Generate Agent".


Expected Output (if X API credentials are valid):Agent created (ID: <uuid>).
Output: Summary of elonmusk's recent tweets: Starship launch planned next week! AI is accelerating human progress. #Tesla
Tweet posted: Summary of elonmusk's recent tweets: Starship launch... (Tweet ID: <id>)
Scheduled to run every 5 minutes.


Current Behavior (with invalid credentials):Agent created (ID: <uuid>).
Output: Summary of elonmusk's recent tweets: (Mock) Exciting updates coming soon! #Innovation
Tweet posted (mock): Summary of elonmusk's recent tweets: (Mock) Exciting updates coming soon! #Innovation
Scheduled to run every 5 minutes.


Verification:
Check agent_builder.log for scheduled runs every 5 minutes.
To fix the 401 Unauthorized error, verify your X API credentials in .env or upgrade to the Basic tier (https://developer.x.com/en/portal/products).



# Test the Hacker News Agent

Prompt: "Scrape top headlines from Hacker News and email them to "
Interval: 1440 minutes (1 day)
Steps:
Enter your email in the "Your Email" field (e.g., user@example.com).
Enter the prompt in the "Enter Prompt" field.
Set the interval to 1440.
Click "Generate Agent".


Expected Output:Agent created (ID: <uuid>).
Output: Top 5 headlines from Hacker News:
1. New AI Framework Released
2. Startup Raises $10M for Quantum Computing
3. Open-Source Tool Hits 1M Downloads
4. Cybersecurity Breach Exposes Data
5. Dev Conference Announces Dates
Email sent to user@example.com with subject 'Hacker News Top Headlines'
Scheduled to run every 1440 minutes.


Verification:
Check your email inbox for the headlines.
Check agent_builder.log for the next scheduled run (24 hours later).



# Test the PDF Summarization Chatbot

Prompt: "Summarize the PDF at uploads/.pdf"
Steps:
Click "Choose File", select a PDF (e.g., sample.pdf), and click "Upload PDF".
Note the file path (e.g., uploads/123e4567-e89b-12d3-a456-426614174000.pdf).
Enter the prompt with the file path in the "Enter Prompt" field.
Click "Generate Agent".
Add a new PDF (e.g., new.pdf) to the uploads/ directory to test file monitoring.


Current Output (due to OpenAI quota limit):Agent created (ID: <uuid>).
Output: Summary of PDF at uploads/123e4567-e89b-12d3-a456-426614174000.pdf: (Mock) This PDF appears to discuss important topics, but summarization is unavailable due to OpenAI quota limits.


File Monitoring Verification:
Check agent_builder.log for new PDF detection:2025-06-08 20:16:00,123 [INFO] New PDF detected: uploads/new.pdf
2025-06-08 20:16:01,456 [INFO] PDF summarization result for uploads/new.pdf: Summary of PDF at uploads/new.pdf: (Mock) ...


Click "Run Again" to see the latest summary.


Note: PDF summarization requires resolving the OpenAI quota issue (https://platform.openai.com/account/billing).

# Techniques Used

1. Flask Web Framework

Purpose: Handles HTTP requests, serves the frontend, and manages agent creation/running.
Implementation: main.py defines routes like /generate_agent, /run_agent/<agent_id>, and /upload_pdf.
Techniques:
Uses Flask-CORS to allow cross-origin requests.
Serves a static HTML file (index.html) as the frontend.
Handles JSON payloads and file uploads.



2. Agent Execution (agents.py)

Purpose: Processes user prompts and invokes appropriate tools.
Implementation:
SimpleAgentExecutor class parses prompts and directly calls tools without an LLM.
Supports three tasks by matching prompt patterns (e.g., "summarize tweets", "scrape top headlines").


Techniques:
Avoids LLM dependency to bypass OpenAI quota issues.
Uses string parsing to extract parameters (e.g., username, email recipient, file path).



3. Tools (tools.py)

Purpose: Defines reusable functions for specific tasks.
Implementation:
summarize_tweets: Uses Tweepy to fetch and summarize tweets from a user.
post_tweet: Posts summaries to Twitter.
scrape_headlines: Scrapes Hacker News using BeautifulSoup.
send_email: Sends emails via Gmail SMTP.
summarize_pdf: Extracts PDF text with PyPDF2 and summarizes using OpenAI (currently mocked).
web_search: Fallback tool using Google Custom Search (not used in current tasks).


Techniques:
Error handling with fallbacks (e.g., mock data for Twitter and PDF tasks).
Retry logic for web scraping (3 attempts).
Truncates tweet summaries to fit X API limits (280 characters).



4. Scheduling (main.py)

Purpose: Runs agents at specified intervals.
Implementation:
Uses APScheduler with BackgroundScheduler to schedule tasks.
Adds jobs with IntervalTrigger based on user-specified intervals.


Techniques:
Ensures single-instance execution with max_instances=1.
Logs scheduled runs for debugging.



5. File Monitoring (main.py)

Purpose: Detects new PDFs for summarization.
Implementation:
Uses watchdog to monitor the uploads/ directory.
PDFHandler class triggers summarization on new PDF files.


Techniques:
Delays processing (time.sleep(1)) to ensure file write completion.
Stores the latest summary for display.



6. Frontend (index.html)

Purpose: Provides a user interface for interacting with the app.
Implementation:
Simple HTML form with fields for PDF upload, email, prompt, and interval.
JavaScript handles API requests to the Flask backend.


Techniques:
Asynchronous fetch requests for agent creation and running.
Displays loading messages and errors for better user experience.
Adds a "Run Again" button dynamically for manual re-runs.


Hacker News Agent

Ensure SMTP_EMAIL and SMTP_PASSWORD are correct (use Gmail App Password).
Check email inbox/spam for the headlines.

PDF Summarization

Currently returns mock responses due to OpenAI quota limits.
Resolve by upgrading your OpenAI plan (https://platform.openai.com/account/billing).
Ensure PDFs contain extractable text (not scanned images).

# Deployment

For production, use Gunicorn:gunicorn -w 4 -b 0.0.0.0:5000 main:app

Ensure uploads/ has write permissions.
Monitor agent_builder.log for errors.


