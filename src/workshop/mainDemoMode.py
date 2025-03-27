import logging
import os


from azure.ai.projects.models import (
    Agent,
    AgentThread,
    BingGroundingTool,
    CodeInterpreterTool,
    FileSearchTool,
)

from dotenv import load_dotenv
from terminal_colors import TerminalColors as tc


logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

load_dotenv()

AGENT_NAME = "Contoso Sales Agent"
TENTS_DATA_SHEET_FILE = "datasheet/contoso-tents-datasheet.pdf"
API_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME")
PROJECT_CONNECTION_STRING = os.environ["PROJECT_CONNECTION_STRING"]
BING_CONNECTION_NAME = os.getenv("BING_CONNECTION_NAME")
MAX_COMPLETION_TOKENS = 4096
MAX_PROMPT_TOKENS = 10240
TEMPERATURE = 0.1
TOP_P = 0.1

from main import toolset
from main import sales_data
from main import utilities
from main import project_client
from main import functions

from main import post_message  # Import the function
from main import cleanup  # Import the function

INSTRUCTIONS_FILE_1 = "instructions/instructions_function_calling.txt"
INSTRUCTIONS_FILE_2 = "instructions/instructions_code_interpreter.txt"
INSTRUCTIONS_FILE_3 = "instructions/instructions_file_search.txt"
INSTRUCTIONS_FILE_4 = "instructions/instructions_bing_grounding.txt"

async def create_agent_config(agentType: int) -> dict:
    """
    Create the tools and configuration for the specified agent type.
    """
    # Map agent types to their respective tools and instructions
    agent_config = {
        1: {"tools": [functions], "instructions": INSTRUCTIONS_FILE_1},
        2: {"tools": [functions, CodeInterpreterTool()], "instructions": INSTRUCTIONS_FILE_2},
        3: {
            "tools": [functions, CodeInterpreterTool()],
            "instructions": INSTRUCTIONS_FILE_3,
            "vector_store": True,
        },
        4: {
            "tools": [functions, CodeInterpreterTool()],
            "instructions": INSTRUCTIONS_FILE_4,
            "vector_store": True,
            "bing_grounding": True,
        },
    }

    # Get the configuration for the specified agent type
    config = agent_config.get(agentType)
    if not config:
        raise ValueError(f"Invalid agent type: {agentType}")

    # Add tools to the toolset
    for tool in config["tools"]:
        toolset.add(tool)

    # Add vector store if required
    if config.get("vector_store"):
        vector_store = await utilities.create_vector_store(
            project_client,
            files=[TENTS_DATA_SHEET_FILE],
            vector_name_name="Contoso Product Information Vector Store",
        )
        file_search_tool = FileSearchTool(vector_store_ids=[vector_store.id])
        toolset.add(file_search_tool)

    # Add Bing grounding tool if required
    if config.get("bing_grounding"):
        bing_connection = await project_client.connections.get(connection_name=BING_CONNECTION_NAME)
        bing_grounding = BingGroundingTool(connection_id=bing_connection.id)
        toolset.add(bing_grounding)

    return config

async def initializeAgentWithTools(agentType: int) -> tuple[Agent, AgentThread]:
    """
    Initialize the agent with the appropriate tools and instructions based on the agent type.
    """
    # Create tools and configuration for the agent
    config = await create_agent_config(agentType)

    # Load and prepare instructions
    agentInstructions = config["instructions"]
    env = os.getenv("ENVIRONMENT", "local")
    instructions_file_path = f"{'src/workshop/' if env == 'container' else ''}{agentInstructions}"
    with open(instructions_file_path, "r", encoding="utf-8", errors="ignore") as file:
        instructions = file.read()

    # Replace the placeholder with the database schema string
    await sales_data.connect()
    database_schema_string = await sales_data.get_database_info()
    instructions = instructions.replace("{database_schema_string}", database_schema_string)

    # Create the agent and thread
    try:
        print("Creating agent...")
        agent = await project_client.agents.create_agent(
            model=API_DEPLOYMENT_NAME,
            name=AGENT_NAME,
            instructions=instructions,
            toolset=toolset,
            temperature=TEMPERATURE,
            headers={"x-ms-enable-preview": "true"},
        )
        print(f"Created agent, ID: {agent.id}")

        print("Creating thread...")
        thread = await project_client.agents.create_thread()
        print(f"Created thread, ID: {thread.id}")

        return agent, thread

    except Exception as e:
        logger.error("An error occurred initializing the agent: %s", str(e))
        logger.error("Please ensure you've enabled an instructions file.")
        raise

async def agentFunctionCallTool_old() -> None:

    agent, thread = await initializeAgentWithTools(4)

    while True:
        # Get user input prompt in the terminal using a pretty shade of green
        print("\n")
        prompt = input(f"{tc.GREEN}Enter your query (type exit to finish): {tc.RESET}")
        if prompt.lower() == "exit":
            break
        if not prompt:
            continue
        await post_message(agent=agent, thread_id=thread.id, content=prompt, thread=thread)

    await cleanup(agent, thread)

async def agentFunctionCallTool() -> None:
    while True:
        # Ask the user to select the agent type
        print("\nSelect the type of agent you want to use:")
        print("1: Basic Agent")
        print("2: Agent with Code Interpreter")
        print("3: Agent with File Search and Vector Store")
        print("4: Agent with Bing Grounding and Vector Store")
        print("Type 'exit' to quit.")
        
        agent_type_input = input(f"{tc.GREEN}Enter your choice (1-4): {tc.RESET}")
        if agent_type_input.lower() == "exit":
            break
        
        try:
            agent_type = int(agent_type_input)
            if agent_type not in [1, 2, 3, 4]:
                print(f"{tc.RED}Invalid choice. Please select a valid option (1-4).{tc.RESET}")
                continue
        except ValueError:
            print(f"{tc.RED}Invalid input. Please enter a number between 1 and 4.{tc.RESET}")
            continue

        # Initialize the agent with the selected type
        agent, thread = await initializeAgentWithTools(agent_type)

        # Existing loop to handle user queries
        while True:
            print("\n")
            prompt = input(f"{tc.GREEN}Enter your query (type 'back' to choose another agent or 'exit' to finish): {tc.RESET}")
            if prompt.lower() == "exit":
                await cleanup(agent, thread)
                return 
            if prompt.lower() == "back":
                break
            if not prompt:
                continue
            await post_message(agent=agent, thread_id=thread.id, content=prompt, thread=thread)

        # Cleanup after exiting the inner loop
        await cleanup(agent, thread)
   