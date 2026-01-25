from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
import uvicorn
from agent_executor import GreetingAgentExecutor
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.apps import A2AStarletteApplication

def main():
    skill = AgentSkill(
        id="greeting_skill",
        name="greeting_skill",
        description="A skill that greets users based on their input.",
        tags=["greeting", "conversation"],
        examples=["Hello, how are you?", "Good morning!"],
    )
    
    agent_card = AgentCard(
        name="Greeting Agent",
        description="An agent that greets users warmly.",
        url="http://localhost:9999",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        skills=[skill],
        capabilities=AgentCapabilities()
    )
    
    request_handler = DefaultRequestHandler(
        agent_executor=GreetingAgentExecutor(),
        task_store=InMemoryTaskStore()
    )
    
    server = A2AStarletteApplication(
        http_handler=request_handler,
        agent_card=agent_card,
    )
    
    uvicorn.run(server.build(), host="0.0.0.0", port=9999)

if __name__ == "__main__":
    main()
    