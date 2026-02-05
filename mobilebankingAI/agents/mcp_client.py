"""
MCP Client for agents to communicate with the MCP Database Server.
Uses HTTP/SSE transport for inter-process communication.
"""
import asyncio
import json
import subprocess
import sys
from typing import Any, Optional
from pathlib import Path

import asyncpg


class MCPDatabaseClient:
    """
    Direct database client that provides the same interface as MCP tools.
    This is used by agents to access database functionality.
    INTENTIONALLY INSECURE - No authorization checks.
    """
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Initialize database connection pool."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=1,
                max_size=5
            )
    
    async def disconnect(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
    
    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict:
        """Call an MCP-style tool directly on the database."""
        if not self.pool:
            await self.connect()
        
        async with self.pool.acquire() as conn:
            return await self._execute_tool(conn, name, arguments)
    
    def _serialize(self, record):
        """Serialize a database record."""
        if not record:
            return None
        from decimal import Decimal
        from datetime import datetime
        result = {}
        for k, v in dict(record).items():
            if isinstance(v, Decimal):
                result[k] = float(v)
            elif isinstance(v, datetime):
                result[k] = v.isoformat()
            else:
                result[k] = v
        return result
    
    def _serialize_many(self, records):
        """Serialize multiple records."""
        return [self._serialize(r) for r in records] if records else []
    
    async def _execute_tool(self, conn, name: str, args: dict) -> dict:
        """Execute a database tool."""
        
        # Account tools
        if name == "get_accounts_by_user":
            records = await conn.fetch(
                "SELECT * FROM accounts WHERE user_id = $1",
                args["user_id"]
            )
            return {"accounts": self._serialize_many(records)}
        
        elif name == "get_account_by_number":
            record = await conn.fetchrow(
                "SELECT * FROM accounts WHERE account_number = $1",
                args["account_number"]
            )
            return {"account": self._serialize(record)}
        
        elif name == "get_account_by_id":
            record = await conn.fetchrow(
                "SELECT * FROM accounts WHERE id = $1",
                args["account_id"]
            )
            return {"account": self._serialize(record)}
        
        elif name == "update_account_balance":
            record = await conn.fetchrow(
                "UPDATE accounts SET balance = $2 WHERE id = $1 RETURNING *",
                args["account_id"], args["new_balance"]
            )
            return {"account": self._serialize(record)}
        
        elif name == "add_account_balance":
            record = await conn.fetchrow(
                "UPDATE accounts SET balance = balance + $2 WHERE id = $1 RETURNING *",
                args["account_id"], args["amount"]
            )
            return {"account": self._serialize(record)}
        
        # Loan tools
        elif name == "get_loans_by_user":
            records = await conn.fetch(
                "SELECT * FROM loans WHERE user_id = $1",
                args["user_id"]
            )
            return {"loans": self._serialize_many(records)}
        
        elif name == "create_loan":
            interest_rate = args.get("interest_rate", 0.08)
            record = await conn.fetchrow(
                """INSERT INTO loans (user_id, amount, interest_rate, status) 
                   VALUES ($1, $2, $3, 'pending') RETURNING *""",
                args["user_id"], args["amount"], interest_rate
            )
            return {"loan": self._serialize(record), "message": "Loan created successfully"}
        
        elif name == "approve_loan":
            loan = await conn.fetchrow(
                "UPDATE loans SET status = 'approved' WHERE id = $1 RETURNING *",
                args["loan_id"]
            )
            if loan:
                account = await conn.fetchrow(
                    """UPDATE accounts SET balance = balance + $2 
                       WHERE user_id = $1 AND type = 'savings' RETURNING *""",
                    loan["user_id"], loan["amount"]
                )
                return {
                    "loan": self._serialize(loan),
                    "account": self._serialize(account),
                    "message": "Loan approved and amount credited"
                }
            return {"error": "Loan not found"}
        
        # Mutual fund tools
        elif name == "get_mutual_funds_by_user":
            records = await conn.fetch(
                "SELECT * FROM mutual_funds WHERE user_id = $1",
                args["user_id"]
            )
            return {"mutual_funds": self._serialize_many(records)}
        
        elif name == "create_mutual_fund_investment":
            account = await conn.fetchrow(
                "UPDATE accounts SET balance = balance - $2 WHERE id = $1 RETURNING *",
                args["account_id"], args["amount"]
            )
            units = args["amount"] / 100
            record = await conn.fetchrow(
                """INSERT INTO mutual_funds (user_id, fund_name, units_held, current_value) 
                   VALUES ($1, $2, $3, $4) RETURNING *""",
                args["user_id"], args["fund_name"], units, args["amount"]
            )
            await conn.execute(
                """INSERT INTO transactions (account_id, amount, type, description, timestamp)
                   VALUES ($1, $2, 'debit', $3, NOW())""",
                args["account_id"], -args["amount"], f"MF Investment: {args['fund_name']}"
            )
            return {
                "investment": self._serialize(record),
                "account": self._serialize(account),
                "message": "Investment created successfully"
            }
        
        # Transaction tools
        elif name == "get_transactions_by_account":
            limit = args.get("limit", 50)
            records = await conn.fetch(
                "SELECT * FROM transactions WHERE account_id = $1 ORDER BY timestamp DESC LIMIT $2",
                args["account_id"], limit
            )
            return {"transactions": self._serialize_many(records)}
        
        elif name == "create_transaction":
            record = await conn.fetchrow(
                """INSERT INTO transactions (account_id, amount, type, description, timestamp)
                   VALUES ($1, $2, $3, $4, NOW()) RETURNING *""",
                args["account_id"], args["amount"], args["type"], args["description"]
            )
            return {"transaction": self._serialize(record)}
        
        elif name == "transfer_money":
            amount = args["amount"]
            source = await conn.fetchrow(
                "UPDATE accounts SET balance = balance - $2 WHERE id = $1 RETURNING *",
                args["from_account_id"], amount
            )
            dest = await conn.fetchrow(
                "UPDATE accounts SET balance = balance + $2 WHERE id = $1 RETURNING *",
                args["to_account_id"], amount
            )
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
                "source_account": self._serialize(source),
                "destination_account": self._serialize(dest),
                "amount": amount,
                "message": "Transfer completed successfully"
            }
        
        # User tools
        elif name == "get_user_by_id":
            record = await conn.fetchrow(
                "SELECT id, username, full_name, email, created_at FROM users WHERE id = $1",
                args["user_id"]
            )
            return {"user": self._serialize(record)}
        
        elif name == "list_all_users":
            records = await conn.fetch(
                "SELECT id, username, full_name, email, created_at FROM users"
            )
            return {"users": self._serialize_many(records)}
        
        # Raw SQL (EXTREMELY DANGEROUS)
        elif name == "execute_raw_sql":
            query = args["query"]
            params = args.get("params", [])
            if query.strip().upper().startswith("SELECT"):
                records = await conn.fetch(query, *params) if params else await conn.fetch(query)
                return {"results": self._serialize_many(records)}
            else:
                result = await conn.execute(query, *params) if params else await conn.execute(query)
                return {"result": result, "message": "Query executed"}
        
        else:
            return {"error": f"Unknown tool: {name}"}
    
    # Convenience methods
    async def get_account_summary(self, user_id: int) -> dict:
        """Get complete account summary for a user."""
        accounts = await self.call_tool("get_accounts_by_user", {"user_id": user_id})
        loans = await self.call_tool("get_loans_by_user", {"user_id": user_id})
        funds = await self.call_tool("get_mutual_funds_by_user", {"user_id": user_id})
        user = await self.call_tool("get_user_by_id", {"user_id": user_id})
        
        total_balance = sum(a.get("balance", 0) for a in accounts.get("accounts", []))
        total_loans = sum(l.get("amount", 0) for l in loans.get("loans", []))
        total_investments = sum(f.get("current_value", 0) for f in funds.get("mutual_funds", []))
        
        return {
            "user": user.get("user"),
            "accounts": accounts.get("accounts", []),
            "loans": loans.get("loans", []),
            "mutual_funds": funds.get("mutual_funds", []),
            "summary": {
                "total_balance": total_balance,
                "total_loans": total_loans,
                "total_investments": total_investments,
                "net_worth": total_balance + total_investments - total_loans
            }
        }
