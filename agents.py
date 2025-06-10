import logging
import re

logging.basicConfig(filename='agent_builder.log', level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class SimpleAgentExecutor:
    def __init__(self, tools, prompt):
        self.tools = tools
        self.prompt = prompt
        # Determine the agent type based on the prompt
        prompt_lower = prompt.lower()
        if "summarize the pdf" in prompt_lower or "summarize pdf" in prompt_lower:
            self.agent_type = "pdf_summarization"
        elif "elon musk" in prompt_lower and ("tweets" in prompt_lower or "summary" in prompt_lower):
            self.agent_type = "twitter_summarization"
        elif "scrape top headlines" in prompt_lower:
            self.agent_type = "hacker_news"
        else:
            self.agent_type = "unknown"

    def invoke(self, input_data):
        prompt = input_data.get("input", self.prompt).lower()
        logger.info(f"SimpleAgentExecutor (type: {self.agent_type}) processing prompt: {prompt}")

        if self.agent_type == "hacker_news" or "scrape top headlines" in prompt:
            headlines = self.tools["scrape_headlines"]({"url": "https://news.ycombinator.com/"})
            if "error" in headlines["output"].lower():
                return {"output": f"Failed to scrape headlines: {headlines['output']}"}
            email_recipient = "user@example.com"
            if "email them to" in prompt:
                email_part = prompt.split("email them to")[-1].strip()
                email_recipient = email_part.split()[0] if email_part else email_recipient
            email_result = self.tools["send_email"]({
                "recipient": email_recipient,
                "subject": "Hacker News Top Headlines",
                "body": f"Top 5 headlines from Hacker News:\n{headlines['output']}"
            })
            return {"output": f"Top 5 headlines from Hacker News:\n{headlines['output']}\n{email_result['output']}"}

        elif self.agent_type == "twitter_summarization" or ("elon musk" in prompt and ("tweets" in prompt or "summary" in prompt)):
            tweets = self.tools["scrape_tweets"]({"username": "@elonmusk"})
            if "error" in tweets["output"].lower():
                return {"output": f"Failed to scrape tweets: {tweets['output']}"}
            tweet_text = tweets["output"].lower()
            topics = []
            if "tesla" in tweet_text:
                topics.append("Tesla")
            if "spacex" in tweet_text:
                topics.append("SpaceX")
            if "mars" in tweet_text:
                topics.append("Mars exploration")
            if "ai" in tweet_text:
                topics.append("AI")
            if not topics:
                topics.append("various topics")
            summary = f"Summary of Elon Musk's tweets:\n- Discussed {', '.join(topics)}."
            logger.info(f"Posting summary of Elon Musk's tweets: {summary}")
            return {"output": f"Elon Musk's tweets:\n{tweets['output']}\n{summary}\nPosted summary to log."}

        elif self.agent_type == "pdf_summarization" and ("summarize the pdf" in prompt or "summarize pdf" in prompt):
            file_path = None
            for word in prompt.split():
                if word.endswith(".pdf"):
                    file_path = word
                    break
            if not file_path:
                return {"output": "Error: PDF file path not found in prompt. Please upload a PDF and try again."}
            summary = self.tools["summarize_pdf"]({"file_path": file_path})
            return {"output": summary["output"]}

        else:
            return {"output": "Prompt not recognized. Try asking about Hacker News headlines, Elon Musk's tweets, or PDF summarization."}

def create_agent(tools, prompt):
    logger.info(f"Creating simple agent for prompt: {prompt}")
    return SimpleAgentExecutor(tools, prompt)
