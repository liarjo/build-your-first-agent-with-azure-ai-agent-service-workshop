import os
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import Agent, BingGroundingTool, CodeInterpreterTool
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_agentchat.ui import Console

# Initialize logging
import logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Constants
API_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME")
PROJECT_CONNECTION_STRING = os.environ["PROJECT_CONNECTION_STRING"]
BING_CONNECTION_NAME = os.getenv("BING_CONNECTION_NAME")
TEMPERATURE = 0.1

# Initialize project client
project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=PROJECT_CONNECTION_STRING,
)

class autoGenResearchTeam:
    async def create_az_model_client() ->AzureOpenAIChatCompletionClient:
        """Create an agent team with tools."""
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )
        az_model_client_parallel = AzureOpenAIChatCompletionClient(
            azure_deployment="gpt-4o",
            api_version="2024-05-01-preview",
            model="gpt-4o",
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
            azure_ad_token_provider=token_provider,
        )
        return az_model_client_parallel
    
    #Strat coding here
  