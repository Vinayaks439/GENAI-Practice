from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.utils import new_agent_text_message

from pydantic import BaseModel

class GreetingAgent(BaseModel):
    async def invoke(self) -> str:
        return "Hello, World!"


class GreetingAgentExecutor(AgentExecutor):
    def __init__(self):
        self.agent = GreetingAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        result = await self.agent.invoke()
        await event_queue.enqueue_event(
            new_agent_text_message(
                result,
                context_id=context.context_id,
                task_id=context.task_id
            )
        )
        
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        raise Exception("Cancellation not supported for GreetingAgentExecutor")