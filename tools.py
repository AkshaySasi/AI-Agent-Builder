import os
import logging
import smtplib
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import tweepy
import PyPDF2
from io import BytesIO

load_dotenv()
logging.basicConfig(filename='agent_builder.log', level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def scrape_headlines(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        headlines = []
        for item in soup.find_all('tr', class_='athing')[:5]:
            title = item.find('span', class_='titleline')
            if title and title.a:
                headlines.append(title.a.text.strip())
        if not headlines:
            return "No headlines found."
        return '\n'.join([f"{i+1}. {headline}" for i, headline in enumerate(headlines)])
    except Exception as e:
        logger.error(f"Error scraping headlines from {url}: {str(e)}")
        return f"Error scraping headlines: {str(e)}"

def send_email(recipient, subject, body):
    smtp_email = os.getenv('SMTP_EMAIL')
    smtp_password = os.getenv('SMTP_PASSWORD')
    
    if not smtp_email or not smtp_password:
        logger.info(f"SMTP credentials not provided. Mocking email to {recipient}")
        return f"Email sent to {recipient} with subject '{subject}' (mock)"
    
    try:
        msg = MIMEMultipart()
        msg['From'] = smtp_email
        msg['To'] = recipient
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(smtp_email, smtp_password)
            server.send_message(msg)
        logger.info(f"Email sent to {recipient} with subject '{subject}'")
        return f"Email sent to {recipient} with subject '{subject}'"
    except Exception as e:
        logger.error(f"Error sending email to {recipient}: {str(e)}")
        return f"Error sending email: {str(e)}"

def scrape_tweets(username):
    try:
        # Load Twitter API credentials
        consumer_key = os.getenv('TWITTER_CONSUMER_KEY')
        consumer_secret = os.getenv('TWITTER_CONSUMER_SECRET')
        access_token = os.getenv('TWITTER_ACCESS_TOKEN')
        access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')

        if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
            logger.error("Twitter API credentials missing")
            return {"output": "Error: Twitter API credentials missing"}

        # Authenticate with Twitter API v1.1 using tweepy
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        api = tweepy.API(auth)

        # Remove leading '@' if present
        username = username.lstrip('@')
        logger.info(f"Scraping tweets for {username}")

        # Fetch the user's recent tweets (up to 5)
        tweets = api.user_timeline(screen_name=username, count=5, tweet_mode="extended")
        if not tweets:
            logger.info(f"No tweets found for {username}")
            return {"output": f"No tweets found for {username}"}

        # Extract tweet text
        tweet_texts = []
        for i, tweet in enumerate(tweets, 1):
            # Handle retweets and full text
            if hasattr(tweet, 'retweeted_status'):
                text = f"RT @{tweet.retweeted_status.user.screen_name}: {tweet.retweeted_status.full_text}"
            else:
                text = tweet.full_text
            tweet_texts.append(f"{i}. {text}")
        result = '\n'.join(tweet_texts)
        logger.info(f"Successfully scraped tweets for {username}: {result}")
        return {"output": result}
    except Exception as e:
        logger.error(f"Error scraping tweets for {username}: {str(e)}")
        return {"output": f"Error scraping tweets: {str(e)}"}

def summarize_pdf(file_path):
    try:
        logger.info(f"Reading PDF from {file_path}")
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ''
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + ' '

        if not text.strip():
            logger.warning(f"No text extracted from PDF at {file_path}")
            return {"output": "Error: No text could be extracted from the PDF"}

        # Simple summarization: Take the first 100 words (or less if the text is shorter)
        words = text.split()
        summary_length = min(100, len(words))
        summary = ' '.join(words[:summary_length])
        if len(words) > summary_length:
            summary += "..."
        logger.info(f"Generated summary for PDF at {file_path}: {summary}")
        return {"output": f"Summary of PDF at {file_path}:\n{summary}"}
    except Exception as e:
        logger.error(f"Error summarizing PDF at {file_path}: {str(e)}")
        return {"output": f"Error summarizing PDF: {str(e)}"}

available_tools = {
    "scrape_headlines": lambda input: {"output": scrape_headlines(input.get("url", ""))},
    "send_email": lambda input: {"output": send_email(
        input.get("recipient", ""),
        input.get("subject", ""),
        input.get("body", "")
    )},
    "scrape_tweets": lambda input: scrape_tweets(input.get("username", "")),
    "summarize_pdf": lambda input: summarize_pdf(input.get("file_path", ""))
}
