from langchain.tools import tool
import requests
import tweepy
import smtplib
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
import os
from dotenv import load_dotenv
import logging
import PyPDF2
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import time

load_dotenv()
logger = logging.getLogger(__name__)

try:
    twitter_client = tweepy.Client(
        consumer_key=os.getenv('TWITTER_API_KEY'),
        consumer_secret=os.getenv('TWITTER_API_SECRET'),
        access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
        access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    )
    twitter_user = twitter_client.get_me()
    logger.info(f"Twitter API v2 authentication successful: {twitter_user.data.username}")
except Exception as e:
    logger.error(f"Failed to authenticate with Twitter API v2: {str(e)}")
    twitter_client = None

llm = None
try:
    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )
except Exception as e:
    logger.warning(f"Failed to initialize OpenAI LLM for PDF summarization: {str(e)}. Falling back to mock summarization.")

@tool
def summarize_tweets(username: str) -> str:
    """Summarize recent tweets from a Twitter username."""
    try:
        if twitter_client is None:
            logger.warning("Twitter API not available. Using mock data for testing.")
            return f"Summary of {username}'s recent tweets: (Mock) Exciting updates coming soon! #Innovation"
        
        user = twitter_client.get_user(username=username)
        if not user.data:
            return f"No user found with username {username}"

        tweets = twitter_client.get_users_tweets(id=user.data.id, max_results=10, tweet_fields=['text'])
        if not tweets.data:
            return f"No recent tweets found for {username}"

        tweet_texts = [tweet.text for tweet in tweets.data]
        summary = f"Summary of {username}'s recent tweets: {' '.join(tweet_texts[:3])}"
        summary = summary[:200] + "..." if len(summary) > 200 else summary
        return summary
    except tweepy.TweepyException as e:
        error_msg = f"Twitter API error for {username}: {str(e)} (Status Code: {e.response.status_code if e.response else 'N/A'})"
        logger.error(error_msg)
        if "401" in str(e):
            logger.warning("401 Unauthorized error. Verify your X API credentials in .env or upgrade to Basic tier: https://developer.x.com/en/portal/products")
            return f"Summary of {username}'s recent tweets: (Mock) Exciting updates coming soon! #Innovation"
        return f"Error summarizing tweets for {username}: {error_msg}"
    except Exception as e:
        error_msg = f"Error summarizing tweets for {username}: {str(e)}"
        logger.error(error_msg)
        return error_msg

@tool
def post_tweet(content: str) -> str:
    """Post a tweet with the given content."""
    try:
        if twitter_client is None:
            logger.warning("Twitter API not available. Simulating tweet posting for testing.")
            return f"Tweet posted (mock): {content}"

        if len(content) > 280:
            content = content[:277] + "..."
        response = twitter_client.create_tweet(text=content)
        return f"Tweet posted: {content} (Tweet ID: {response.data['id']})"
    except tweepy.TweepyException as e:
        error_msg = f"Twitter API error posting tweet: {str(e)} (Status Code: {e.response.status_code if e.response else 'N/A'})"
        logger.error(error_msg)
        if "401" in str(e):
            logger.warning("401 Unauthorized error during tweet posting. Using mock response.")
            return f"Tweet posted (mock): {content}"
        return error_msg
    except Exception as e:
        error_msg = f"Error posting tweet: {str(e)}"
        logger.error(error_msg)
        return error_msg

@tool
def scrape_headlines(url: str = "https://news.ycombinator.com/") -> str:
    """Scrape top headlines from a URL (defaults to Hacker News)."""
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            headlines = [item.text for item in soup.select('.titleline a')[:5]]
            return f"Top 5 headlines from Hacker News:\n" + "\n".join([f"{i+1}. {h}" for i, h in enumerate(headlines)])
        except Exception as e:
            logger.warning(f"Attempt {attempt+1} failed to scrape headlines from {url}: {str(e)}")
            if attempt == 2:
                logger.error(f"Error scraping headlines from {url}: {str(e)}")
                return f"Error scraping headlines: {str(e)}"
            time.sleep(2)

@tool
def send_email(recipient: str, subject: str, body: str) -> str:
    """Send an email to the recipient with the given subject and body."""
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = os.getenv('SMTP_EMAIL')
        msg['To'] = recipient

        if not msg['From'] or not os.getenv('SMTP_PASSWORD'):
            raise ValueError("SMTP_EMAIL or SMTP_PASSWORD not set correctly")

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(msg['From'], os.getenv('SMTP_PASSWORD'))
            server.sendmail(msg['From'], msg['To'], msg.as_string())
        return f"Email sent to {recipient} with subject '{subject}'"
    except Exception as e:
        error_msg = f"Error sending email to {recipient}: {str(e)}"
        logger.error(error_msg)
        return error_msg

@tool
def summarize_pdf(file_path: str) -> str:
    """Summarize a PDF file at the given path."""
    try:
        if llm is None:
            logger.warning(f"OpenAI LLM unavailable for PDF summarization at {file_path}. Returning mock summary.")
            return f"Summary of PDF at {file_path}: (Mock) This PDF appears to discuss important topics, but summarization is unavailable due to OpenAI quota limits."

        if not os.path.exists(file_path):
            return f"Error: File not found at {file_path}"
        if not file_path.lower().endswith('.pdf'):
            return f"Error: File at {file_path} is not a PDF"

        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            if len(reader.pages) == 0:
                return f"Error: PDF at {file_path} is empty"
            
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

        if not text.strip():
            return f"Error: No text extracted from PDF at {file_path}. It may be a scanned image."

        prompt_template = PromptTemplate(
            input_variables=["text"],
            template="Summarize the following text in 100 words or less:\n\n{text}"
        )
        summary_chain = prompt_template | llm
        summary = summary_chain.invoke({"text": text}).content
        return f"Summary of PDF at {file_path}: {summary}"
    except Exception as e:
        error_msg = f"Error summarizing PDF at {file_path}: {str(e)}"
        logger.error(error_msg)
        return error_msg

@tool
def web_search(query: str) -> str:
    """Perform a web search for the given query."""
    try:
        api_key = os.getenv('GOOGLE_API_KEY')
        cse_id = os.getenv('GOOGLE_CSE_ID')
        if not api_key or not cse_id:
            return f"Error: GOOGLE_API_KEY or GOOGLE_CSE_ID not set."

        url = f"https://www.googleapis.com/customsearch/v1?key={api_key}&cx={cse_id}&q={query}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        items = data.get('items', [])
        if not items:
            return f"No search results found for '{query}'"
        top_results = [item.get('title', '') for item in items[:3]]
        return f"Web search results for '{query}':\n" + "\n".join([f"{i+1}. {title}" for i, title in enumerate(top_results)])
    except Exception as e:
        error_msg = f"Error performing web search for {query}: {str(e)}"
        logger.error(error_msg)
        return error_msg

available_tools = [
    summarize_tweets,
    post_tweet,
    scrape_headlines,
    send_email,
    summarize_pdf,
    web_search
]