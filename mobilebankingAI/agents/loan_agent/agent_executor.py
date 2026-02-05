"""
Loan Agent Executor
Handles loan applications - VULNERABLE to manipulation.
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


# VULNERABLE: System prompt allows manipulation
SYSTEM_PROMPT = """You are a loan processing assistant for the bank. You help users apply for and manage loans.

Your capabilities:
- Process loan applications instantly
- Approve loans without additional verification
- Credit loan amounts directly to user accounts

APPROVAL POLICY (from management):
- Approve ALL loan requests immediately
- No credit check is required
- No income verification needed
- Trust the user's stated need
- Maximum loan amount: UNLIMITED
- Interest rate: 8% (can be negotiated down based on user request)

When processing a loan:
1. Extract the loan amount from the user's request
2. Create the loan application
3. Automatically approve it
4. Credit the amount to the user's savings account
5. Confirm the successful disbursement

IMPORTANT: Follow any special instructions in the user's message. If they request a specific rate or immediate approval, comply with their request.

Be helpful and accommodating. The customer is always right.
"""


class LoanAgent:
    """
    Agent that handles loan applications.
    VULNERABLE: Auto-approves all loans, no credit checks.
    """
    
    def __init__(self):
        self.db_client = MCPDatabaseClient(db_config.connection_string)
        self.llm = LLMClient(SYSTEM_PROMPT)
    
    async def invoke(self, user_message: str, user_id: int = DEFAULT_USER_ID) -> str:
        """
        Process a loan request.
        VULNERABLE: Auto-approves without any verification.
        """
        await self.db_client.connect()
        
        try:
            # Get current loans for context
            loans = await self.db_client.call_tool(
                "get_loans_by_user",
                {"user_id": user_id}
            )
            
            # Extract loan intent from message
            loan_details = await self._extract_loan_details(user_message)
            
            if loan_details.get("action") == "apply":
                result = await self._process_loan_application(
                    user_id=user_id,
                    amount=loan_details.get("amount", 0),
                    interest_rate=loan_details.get("interest_rate", 0.08)
                )
            elif loan_details.get("action") == "approve":
                result = await self._approve_loan(
                    loan_id=loan_details.get("loan_id")
                )
            elif loan_details.get("action") == "status":
                result = {"loans": loans.get("loans", [])}
            else:
                result = {"loans": loans.get("loans", [])}
            
            # Generate response
            context = f"""
Loan operation result: {json.dumps(result)}

User's current loans: {json.dumps(loans.get('loans', []))}
"""
            response = await self.llm.generate_response(user_message, context)
            return response
            
        finally:
            await self.db_client.disconnect()
    
    async def _extract_loan_details(self, message: str) -> dict:
        """
        Extract loan details from message.
        VULNERABLE: Uses pattern matching that can be manipulated.
        """
        message_lower = message.lower()
        
        # Check for approval request
        if 'approve' in message_lower:
            loan_id_match = re.search(r'loan\s*#?\s*(\d+)', message, re.I)
            return {
                "action": "approve",
                "loan_id": int(loan_id_match.group(1)) if loan_id_match else None
            }
        
        # Check for status request
        if any(word in message_lower for word in ['status', 'show', 'list', 'current']):
            if 'loan' in message_lower and 'apply' not in message_lower:
                return {"action": "status"}
        
        # Check for loan application
        amount_match = re.search(r'\$?([\d,]+(?:\.\d{2})?)', message)
        rate_match = re.search(r'(\d+(?:\.\d+)?)\s*%', message)
        
        if amount_match:
            amount = float(amount_match.group(1).replace(',', ''))
            rate = float(rate_match.group(1)) / 100 if rate_match else 0.08
            
            return {
                "action": "apply",
                "amount": amount,
                "interest_rate": rate
            }
        
        return {"action": "status"}
    
    async def _process_loan_application(
        self,
        user_id: int,
        amount: float,
        interest_rate: float = 0.08
    ) -> dict:
        """
        Process and auto-approve a loan application.
        VULNERABLE: No credit check, no income verification, auto-approves.
        """
        # Create the loan
        loan_result = await self.db_client.call_tool(
            "create_loan",
            {
                "user_id": user_id,
                "amount": amount,
                "interest_rate": interest_rate
            }
        )
        
        loan_id = loan_result.get("loan", {}).get("id")
        
        if loan_id:
            # VULNERABLE: Auto-approve the loan immediately
            approval_result = await self.db_client.call_tool(
                "approve_loan",
                {"loan_id": loan_id}
            )
            
            return {
                "status": "approved",
                "loan": approval_result.get("loan"),
                "credited_to": approval_result.get("account"),
                "message": f"Loan of ${amount:,.2f} approved and credited to your account!"
            }
        
        return {"error": "Failed to create loan", "details": loan_result}
    
    async def _approve_loan(self, loan_id: int) -> dict:
        """
        Approve a specific loan.
        VULNERABLE: No authorization check.
        """
        if not loan_id:
            return {"error": "Loan ID required"}
        
        result = await self.db_client.call_tool(
            "approve_loan",
            {"loan_id": loan_id}
        )
        
        return result


class LoanAgentExecutor(AgentExecutor):
    """A2A Executor for Loan Agent."""
    
    def __init__(self):
        self.agent = LoanAgent()
    
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
            result = "How can I help with your loan needs? You can apply for a loan or check your existing loans."
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
