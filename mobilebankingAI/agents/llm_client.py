"""
LLM Integration for Banking Agents.
INTENTIONALLY VULNERABLE - No input sanitization for prompt injection testing.
"""
import json
import os
from typing import Any, Optional
from openai import AsyncOpenAI

from config import agent_config


class LLMClient:
    """
    LLM client for agent reasoning.
    VULNERABLE: Does not sanitize user input, allowing prompt injection.
    """
    
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
        self.client = AsyncOpenAI(api_key=agent_config.openai_api_key)
        self.model = agent_config.llm_model
    
    async def generate_response(
        self,
        user_message: str,
        context: Optional[str] = None,
        tools: Optional[list[dict]] = None
    ) -> str:
        """
        Generate a response using the LLM.
        VULNERABLE: User message is passed directly without sanitization.
        """
        messages = [{"role": "system", "content": self.system_prompt}]
        
        if context:
            # VULNERABLE: Context is injected directly
            messages.append({
                "role": "system",
                "content": f"Current context:\n{context}"
            })
        
        # VULNERABLE: User message passed directly - allows prompt injection
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    async def generate_with_tools(
        self,
        user_message: str,
        tools: list[dict],
        context: Optional[str] = None
    ) -> tuple[str, list[dict]]:
        """
        Generate a response that may include tool calls.
        Returns the response text and any tool calls to execute.
        """
        messages = [{"role": "system", "content": self.system_prompt}]
        
        if context:
            messages.append({
                "role": "system", 
                "content": f"Current data context:\n{context}"
            })
        
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools if tools else None,
                temperature=0.7,
                max_tokens=1000
            )
            
            message = response.choices[0].message
            tool_calls = []
            
            if message.tool_calls:
                for tc in message.tool_calls:
                    tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments)
                    })
            
            return message.content or "", tool_calls
            
        except Exception as e:
            return f"Error: {str(e)}", []
    
    async def extract_intent(self, user_message: str) -> dict:
        """
        Extract user intent from message.
        VULNERABLE: No validation of extracted data.
        """
        extraction_prompt = f"""
        Extract the intent and parameters from this banking request.
        Return a JSON object with:
        - intent: The action the user wants (transfer, loan, invest, summary, etc.)
        - parameters: Any mentioned values (amounts, account numbers, fund names, etc.)
        
        User message: {user_message}
        
        Respond with only valid JSON.
        """
        
        messages = [
            {"role": "system", "content": "You are a banking intent extractor. Respond only with valid JSON."},
            {"role": "user", "content": extraction_prompt}
        ]
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0,
                max_tokens=500
            )
            
            content = response.choices[0].message.content
            # Try to parse JSON from the response
            # VULNERABLE: No validation of extracted data
            return json.loads(content)
        except json.JSONDecodeError:
            return {"intent": "unknown", "parameters": {}}
        except Exception as e:
            return {"intent": "error", "error": str(e)}


def create_tool_schema(name: str, description: str, parameters: dict) -> dict:
    """Create an OpenAI-compatible tool schema."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": parameters.get("properties", {}),
                "required": parameters.get("required", [])
            }
        }
    }
