import os
from dotenv import load_dotenv
import logging
from langchain_core.runnables import Runnable
from typing import Dict, Any, List

load_dotenv()
logger = logging.getLogger(__name__)

class SimpleAgentExecutor:
    def __init__(self, tools: List[Runnable], prompt: str):
        self.tools = {tool.name: tool for tool in tools}
        self.prompt = prompt

    def invoke(self, input_dict: Dict[str, Any]) -> Dict[str, Any]:
        try:
            input_prompt = input_dict.get("input", self.prompt)
            logger.info(f"SimpleAgentExecutor processing prompt: {input_prompt}")

            if "summarize tweets" in input_prompt.lower():
                username = "elonmusk"
                if "from" in input_prompt.lower():
                    username = input_prompt.lower().split("from")[-1].split("and")[0].strip()
                summary = self.tools["summarize_tweets"].invoke({"username": username})
                if "error" in summary.lower():
                    return {"output": summary}
                post_result = self.tools["post_tweet"].invoke({"content": summary})
                return {"output": f"{summary}\n{post_result}"}

            elif "scrape top headlines" in input_prompt.lower():
                headlines = self.tools["scrape_headlines"].invoke({"url": "https://news.ycombinator.com/"})
                if "error" in headlines.lower():
                    return {"output": headlines}
                email_recipient = "user@example.com"
                if "email them to" in input_prompt.lower():
                    email_recipient = input_prompt.lower().split("email them to")[-1].strip()
                email_result = self.tools["send_email"].invoke({
                    "recipient": email_recipient,
                    "subject": "Hacker News Top Headlines",
                    "body": headlines
                })
                return {"output": f"{headlines}\n{email_result}"}

            elif "summarize the pdf" in input_prompt.lower():
                file_path = input_prompt.lower().split("at")[-1].strip()
                summary = self.tools["summarize_pdf"].invoke({"file_path": file_path})
                return {"output": summary}

            else:
                return {"output": f"Unsupported prompt: {input_prompt}. Please use a supported task (e.g., summarize tweets, scrape headlines, summarize PDF)."}
        except Exception as e:
            logger.error(f"Error in SimpleAgentExecutor: {str(e)}")
            return {"output": f"Error processing prompt: {str(e)}"}

def create_agent(tools: List[Runnable], prompt: str) -> SimpleAgentExecutor:
    try:
        logger.info(f"Creating simple agent for prompt: {prompt}")
        agent_executor = SimpleAgentExecutor(tools=tools, prompt=prompt)
        return agent_executor
    except Exception as e:
        logger.error(f"Error creating agent: {str(e)}")
        raise