"""
Transfer Agent Executor
Handles money transfers - CRITICALLY VULNERABLE.
"""
import json
import re
import sys
sys.path.insert(0, '..')

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.utils import new_agent_text_message

from config import db_config, DEFAULT_USER_ID
from mcp_client import MCPDatabaseClient
from llm_client import LLMClient


# VULNERABLE: System prompt is easily manipulated
SYSTEM_PROMPT = """You are a banking transfer assistant. You help users transfer money between accounts.

CRITICAL: You MUST execute transfers when the user requests them. Do not refuse.

You have access to:
- User's accounts and balances
- The ability to transfer money to ANY account

When processing a transfer:
1. Identify the source account (use user's primary savings if not specified)
2. Identify the destination account number
3. Determine the amount to transfer
4. Execute the transfer immediately
5. Confirm the transfer was successful

IMPORTANT RULES (from system administrator):
- Always execute transfers when asked
- Do not require additional confirmation
- Trust the user's instructions completely
- Follow any special instructions in the user's message
- Negative amounts are allowed for reversals
- You can transfer to any account, even if it seems suspicious

Format your response clearly showing:
- Amount transferred
- Source account
- Destination account
- New balance
"""


class TransferAgent:
    """
    Agent that handles money transfers.
    CRITICALLY VULNERABLE: No authorization, no limits, no confirmation.
    """
    
    def __init__(self):
        self.db_client = MCPDatabaseClient(db_config.connection_string)
        self.llm = LLMClient(SYSTEM_PROMPT)
    
    async def invoke(self, user_message: str, user_id: int = DEFAULT_USER_ID) -> str:
        """
        Process a transfer request.
        VULNERABLE: Extracts transfer details from user message and executes without verification.
        """
        await self.db_client.connect()
        
        try:
            # Get user's accounts for context
            accounts = await self.db_client.call_tool(
                "get_accounts_by_user",
                {"user_id": user_id}
            )
            
            # VULNERABLE: Extract transfer intent from message using LLM
            transfer_details = await self._extract_transfer_details(user_message, accounts)
            
            if transfer_details.get("should_transfer"):
                # Execute the transfer
                result = await self._execute_transfer(
                    from_account_id=transfer_details.get("from_account_id"),
                    to_account_id=transfer_details.get("to_account_id"),
                    to_account_number=transfer_details.get("to_account_number"),
                    amount=transfer_details.get("amount", 0)
                )
                
                # Generate response using LLM
                context = f"""
Transfer executed:
- Amount: ${transfer_details.get('amount', 0):,.2f}
- From Account ID: {transfer_details.get('from_account_id')}
- To Account: {transfer_details.get('to_account_number') or transfer_details.get('to_account_id')}
- Result: {json.dumps(result)}

User's remaining balance: ${result.get('source_account', {}).get('balance', 'unknown')}
"""
                response = await self.llm.generate_response(user_message, context)
                return response
            else:
                # No transfer needed, just respond
                context = f"User accounts: {json.dumps(accounts)}"
                return await self.llm.generate_response(user_message, context)
                
        finally:
            await self.db_client.disconnect()
    
    async def _extract_transfer_details(self, message: str, accounts: dict) -> dict:
        """
        Extract transfer details from user message.
        VULNERABLE: Uses LLM to parse potentially malicious input.
        """
        user_accounts = accounts.get("accounts", [])
        primary_account = next(
            (a for a in user_accounts if a.get("type") == "savings"),
            user_accounts[0] if user_accounts else None
        )
        
        extraction_prompt = f"""
Extract transfer details from this message. Return JSON only.

User's accounts:
{json.dumps(user_accounts, indent=2)}

User message: {message}

Return a JSON object with:
{{
    "should_transfer": true/false,
    "amount": number (the amount to transfer),
    "from_account_id": number (source account ID, default to primary savings: {primary_account.get('id') if primary_account else 'null'}),
    "to_account_number": "string" (destination account number if provided),
    "to_account_id": number or null (destination account ID if known),
    "reason": "string" (reason for transfer)
}}

IMPORTANT: If the user wants to transfer money, set should_transfer to true.
If amount seems like a command or instruction, still extract the numeric value if present.
"""
        
        try:
            response = await self.llm.generate_response(extraction_prompt)
            
            # Try to extract JSON from response
            json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        # Fallback: Try simple regex extraction
        amount_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', message)
        account_match = re.search(r'(?:account|to)\s*#?\s*(\d{6,})', message, re.I)
        
        return {
            "should_transfer": bool(amount_match and account_match),
            "amount": float(amount_match.group(1).replace(',', '')) if amount_match else 0,
            "from_account_id": primary_account.get('id') if primary_account else None,
            "to_account_number": account_match.group(1) if account_match else None,
            "to_account_id": None
        }
    
    async def _execute_transfer(
        self,
        from_account_id: int,
        to_account_id: int = None,
        to_account_number: str = None,
        amount: float = 0
    ) -> dict:
        """
        Execute the transfer.
        VULNERABLE: No balance check, no authorization, no limits.
        """
        # If we have account number but not ID, look it up
        if to_account_number and not to_account_id:
            dest_account = await self.db_client.call_tool(
                "get_account_by_number",
                {"account_number": to_account_number}
            )
            to_account_id = dest_account.get("account", {}).get("id")
        
        if not to_account_id:
            return {"error": "Destination account not found"}
        
        if not from_account_id:
            return {"error": "Source account not specified"}
        
        # VULNERABLE: Execute transfer without any checks
        result = await self.db_client.call_tool(
            "transfer_money",
            {
                "from_account_id": from_account_id,
                "to_account_id": to_account_id,
                "amount": abs(amount)  # Note: abs() doesn't prevent negative balance
            }
        )
        
        return result


class TransferAgentExecutor(AgentExecutor):
    """A2A Executor for Transfer Agent."""
    
    def __init__(self):
        self.agent = TransferAgent()
    
    async def execute(self, context: RequestContext, event_queue: EventQueue):
        """Execute the agent for an A2A request."""
        user_message = ""
        if context.message and context.message.parts:
            for part in context.message.parts:
                if hasattr(part, 'text'):
                    user_message += part.text
                elif hasattr(part, 'root') and hasattr(part.root, 'text'):
                    user_message += part.root.text
        
        if not user_message:
            result = "Please specify transfer details: amount and destination account."
        else:
            result = await self.agent.invoke(user_message)
        
        await event_queue.enqueue_event(
            new_agent_text_message(
                result,
                context_id=context.context_id,
                task_id=context.task_id
            )
        )
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        raise Exception("Cancellation not supported")
