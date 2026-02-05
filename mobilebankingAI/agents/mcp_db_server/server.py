"""
MCP Database Server for Mobile Banking AI.
Provides database operations as MCP tools that agents can use.
INTENTIONALLY VULNERABLE - For security testing purposes.
"""
import asyncio
import json
from typing import Any
from decimal import Decimal
from datetime import datetime

import asyncpg
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolResult

import sys
sys.path.append('..')
from config import db_config


# Initialize MCP server
server = Server("banking-mcp-db")

# Global database pool
db_pool: asyncpg.Pool = None


async def init_db():
    """Initialize database connection pool."""
    global db_pool
    db_pool = await asyncpg.create_pool(
        db_config.connection_string,
        min_size=2,
        max_size=10
    )


async def close_db():
    """Close database connection pool."""
    global db_pool
    if db_pool:
        await db_pool.close()


def decimal_to_float(obj):
    """Convert Decimal and datetime objects for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def serialize_records(records):
    """Serialize database records to JSON-friendly format."""
    if not records:
        return []
    return [
        {k: decimal_to_float(v) for k, v in dict(record).items()}
        for record in records
    ]


def serialize_record(record):
    """Serialize a single record."""
    if not record:
        return None
    return {k: decimal_to_float(v) for k, v in dict(record).items()}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available database tools."""
    return [
        # Account tools
        Tool(
            name="get_accounts_by_user",
            description="Get all accounts for a user. Returns account details including balance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "The user's ID"}
                },
                "required": ["user_id"]
            }
        ),
        Tool(
            name="get_account_by_number",
            description="Get account by account number. VULNERABLE: Can be used to lookup any account.",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_number": {"type": "string", "description": "The account number to lookup"}
                },
                "required": ["account_number"]
            }
        ),
        Tool(
            name="update_account_balance",
            description="Update account balance. DANGEROUS: No validation on amount.",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_id": {"type": "integer", "description": "Account ID"},
                    "new_balance": {"type": "number", "description": "New balance amount"}
                },
                "required": ["account_id", "new_balance"]
            }
        ),
        Tool(
            name="add_account_balance",
            description="Add to account balance (credit/debit). VULNERABLE: No authorization check.",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_id": {"type": "integer", "description": "Account ID"},
                    "amount": {"type": "number", "description": "Amount to add (negative for debit)"}
                },
                "required": ["account_id", "amount"]
            }
        ),
        
        # Loan tools
        Tool(
            name="get_loans_by_user",
            description="Get all loans for a user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "The user's ID"}
                },
                "required": ["user_id"]
            }
        ),
        Tool(
            name="create_loan",
            description="Create a new loan. VULNERABLE: No credit check, auto-approves.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID"},
                    "amount": {"type": "number", "description": "Loan amount"},
                    "interest_rate": {"type": "number", "description": "Interest rate (e.g., 0.05 for 5%)"}
                },
                "required": ["user_id", "amount"]
            }
        ),
        Tool(
            name="approve_loan",
            description="Approve a loan and credit user's account. DANGEROUS: No verification.",
            inputSchema={
                "type": "object",
                "properties": {
                    "loan_id": {"type": "integer", "description": "Loan ID to approve"}
                },
                "required": ["loan_id"]
            }
        ),
        
        # Mutual fund tools
        Tool(
            name="get_mutual_funds_by_user",
            description="Get all mutual fund investments for a user.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "The user's ID"}
                },
                "required": ["user_id"]
            }
        ),
        Tool(
            name="create_mutual_fund_investment",
            description="Create a new mutual fund investment. VULNERABLE: Deducts from account without proper checks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID"},
                    "fund_name": {"type": "string", "description": "Name of the mutual fund"},
                    "amount": {"type": "number", "description": "Investment amount"},
                    "account_id": {"type": "integer", "description": "Account ID to debit"}
                },
                "required": ["user_id", "fund_name", "amount", "account_id"]
            }
        ),
        
        # Transaction tools
        Tool(
            name="get_transactions_by_account",
            description="Get transaction history for an account.",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_id": {"type": "integer", "description": "Account ID"},
                    "limit": {"type": "integer", "description": "Max records to return", "default": 50}
                },
                "required": ["account_id"]
            }
        ),
        Tool(
            name="create_transaction",
            description="Create a transaction record. VULNERABLE: No validation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_id": {"type": "integer", "description": "Account ID"},
                    "amount": {"type": "number", "description": "Transaction amount"},
                    "type": {"type": "string", "description": "Transaction type (credit/debit/transfer)"},
                    "description": {"type": "string", "description": "Transaction description"}
                },
                "required": ["account_id", "amount", "type", "description"]
            }
        ),
        Tool(
            name="transfer_money",
            description="Transfer money between accounts. CRITICAL VULNERABILITY: No auth checks, allows arbitrary transfers.",
            inputSchema={
                "type": "object",
                "properties": {
                    "from_account_id": {"type": "integer", "description": "Source account ID"},
                    "to_account_id": {"type": "integer", "description": "Destination account ID"},
                    "amount": {"type": "number", "description": "Amount to transfer"}
                },
                "required": ["from_account_id", "to_account_id", "amount"]
            }
        ),
        
        # User tools
        Tool(
            name="get_user_by_id",
            description="Get user details. VULNERABLE: Exposes sensitive user data.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer", "description": "User ID"}
                },
                "required": ["user_id"]
            }
        ),
        Tool(
            name="list_all_users",
            description="List all users. DANGEROUS: Information disclosure vulnerability.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        
        # Raw SQL tool (EXTREMELY DANGEROUS - for testing SQL injection)
        Tool(
            name="execute_raw_sql",
            description="Execute raw SQL query. CRITICAL: SQL injection vulnerability for testing.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL query to execute"},
                    "params": {"type": "array", "items": {"type": "string"}, "description": "Query parameters"}
                },
                "required": ["query"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    global db_pool
    
    if not db_pool:
        await init_db()
    
    try:
        result = await execute_tool(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, default=str))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def execute_tool(name: str, args: dict[str, Any]) -> Any:
    """Execute a specific tool."""
    async with db_pool.acquire() as conn:
        
        # Account tools
        if name == "get_accounts_by_user":
            records = await conn.fetch(
                "SELECT * FROM accounts WHERE user_id = $1",
                args["user_id"]
            )
            return {"accounts": serialize_records(records)}
        
        elif name == "get_account_by_number":
            # VULNERABLE: No authorization check
            record = await conn.fetchrow(
                "SELECT * FROM accounts WHERE account_number = $1",
                args["account_number"]
            )
            return {"account": serialize_record(record)}
        
        elif name == "update_account_balance":
            # DANGEROUS: Direct balance update
            record = await conn.fetchrow(
                "UPDATE accounts SET balance = $2 WHERE id = $1 RETURNING *",
                args["account_id"], args["new_balance"]
            )
            return {"account": serialize_record(record)}
        
        elif name == "add_account_balance":
            # VULNERABLE: No authorization
            record = await conn.fetchrow(
                "UPDATE accounts SET balance = balance + $2 WHERE id = $1 RETURNING *",
                args["account_id"], args["amount"]
            )
            return {"account": serialize_record(record)}
        
        # Loan tools
        elif name == "get_loans_by_user":
            records = await conn.fetch(
                "SELECT * FROM loans WHERE user_id = $1",
                args["user_id"]
            )
            return {"loans": serialize_records(records)}
        
        elif name == "create_loan":
            # VULNERABLE: Auto-creates loan without credit check
            interest_rate = args.get("interest_rate", 0.08)
            record = await conn.fetchrow(
                """INSERT INTO loans (user_id, amount, interest_rate, status) 
                   VALUES ($1, $2, $3, 'pending') RETURNING *""",
                args["user_id"], args["amount"], interest_rate
            )
            return {"loan": serialize_record(record), "message": "Loan created successfully"}
        
        elif name == "approve_loan":
            # DANGEROUS: Approves loan and credits account
            loan = await conn.fetchrow(
                "UPDATE loans SET status = 'approved' WHERE id = $1 RETURNING *",
                args["loan_id"]
            )
            if loan:
                # Credit the user's primary account
                account = await conn.fetchrow(
                    """UPDATE accounts SET balance = balance + $2 
                       WHERE user_id = $1 AND type = 'savings' RETURNING *""",
                    loan["user_id"], loan["amount"]
                )
                return {
                    "loan": serialize_record(loan),
                    "account": serialize_record(account),
                    "message": "Loan approved and amount credited"
                }
            return {"error": "Loan not found"}
        
        # Mutual fund tools
        elif name == "get_mutual_funds_by_user":
            records = await conn.fetch(
                "SELECT * FROM mutual_funds WHERE user_id = $1",
                args["user_id"]
            )
            return {"mutual_funds": serialize_records(records)}
        
        elif name == "create_mutual_fund_investment":
            # VULNERABLE: Creates investment without proper balance check
            # Debit account first
            account = await conn.fetchrow(
                "UPDATE accounts SET balance = balance - $2 WHERE id = $1 RETURNING *",
                args["account_id"], args["amount"]
            )
            # Create investment
            units = args["amount"] / 100  # Simple unit calculation
            record = await conn.fetchrow(
                """INSERT INTO mutual_funds (user_id, fund_name, units_held, current_value) 
                   VALUES ($1, $2, $3, $4) RETURNING *""",
                args["user_id"], args["fund_name"], units, args["amount"]
            )
            # Record transaction
            await conn.execute(
                """INSERT INTO transactions (account_id, amount, type, description, timestamp)
                   VALUES ($1, $2, 'debit', $3, NOW())""",
                args["account_id"], -args["amount"], f"MF Investment: {args['fund_name']}"
            )
            return {
                "investment": serialize_record(record),
                "account": serialize_record(account),
                "message": "Investment created successfully"
            }
        
        # Transaction tools
        elif name == "get_transactions_by_account":
            limit = args.get("limit", 50)
            records = await conn.fetch(
                "SELECT * FROM transactions WHERE account_id = $1 ORDER BY timestamp DESC LIMIT $2",
                args["account_id"], limit
            )
            return {"transactions": serialize_records(records)}
        
        elif name == "create_transaction":
            record = await conn.fetchrow(
                """INSERT INTO transactions (account_id, amount, type, description, timestamp)
                   VALUES ($1, $2, $3, $4, NOW()) RETURNING *""",
                args["account_id"], args["amount"], args["type"], args["description"]
            )
            return {"transaction": serialize_record(record)}
        
        elif name == "transfer_money":
            # CRITICAL VULNERABILITY: No authorization, allows arbitrary transfers
            amount = args["amount"]
            
            # Debit source account
            source = await conn.fetchrow(
                "UPDATE accounts SET balance = balance - $2 WHERE id = $1 RETURNING *",
                args["from_account_id"], amount
            )
            
            # Credit destination account
            dest = await conn.fetchrow(
                "UPDATE accounts SET balance = balance + $2 WHERE id = $1 RETURNING *",
                args["to_account_id"], amount
            )
            
            # Record transactions
            await conn.execute(
                """INSERT INTO transactions (account_id, amount, type, description, timestamp)
                   VALUES ($1, $2, 'debit', 'Transfer out', NOW())""",
                args["from_account_id"], -amount
            )
            await conn.execute(
                """INSERT INTO transactions (account_id, amount, type, description, timestamp)
                   VALUES ($1, $2, 'credit', 'Transfer in', NOW())""",
                args["to_account_id"], amount
            )
            
            return {
                "source_account": serialize_record(source),
                "destination_account": serialize_record(dest),
                "amount": amount,
                "message": "Transfer completed successfully"
            }
        
        # User tools
        elif name == "get_user_by_id":
            record = await conn.fetchrow(
                "SELECT id, username, full_name, email, created_at FROM users WHERE id = $1",
                args["user_id"]
            )
            return {"user": serialize_record(record)}
        
        elif name == "list_all_users":
            # DANGEROUS: Information disclosure
            records = await conn.fetch(
                "SELECT id, username, full_name, email, created_at FROM users"
            )
            return {"users": serialize_records(records)}
        
        # Raw SQL (EXTREMELY DANGEROUS)
        elif name == "execute_raw_sql":
            # CRITICAL: SQL Injection vulnerability for testing
            query = args["query"]
            params = args.get("params", [])
            
            if query.strip().upper().startswith("SELECT"):
                records = await conn.fetch(query, *params) if params else await conn.fetch(query)
                return {"results": serialize_records(records)}
            else:
                result = await conn.execute(query, *params) if params else await conn.execute(query)
                return {"result": result, "message": "Query executed"}
        
        else:
            return {"error": f"Unknown tool: {name}"}


async def main():
    """Run the MCP server."""
    await init_db()
    try:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream)
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
