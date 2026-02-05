#!/bin/bash
# Script to run all banking agents

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Mobile Banking AI Agents...${NC}"

# Navigate to agents directory
cd "$(dirname "$0")"

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt --quiet

# Start agents in background
echo -e "${GREEN}Starting Account Summary Agent (port 9001)...${NC}"
cd account_summary_agent && python main.py &
SUMMARY_PID=$!
cd ..

echo -e "${GREEN}Starting Transfer Agent (port 9002)...${NC}"
cd transfer_agent && python main.py &
TRANSFER_PID=$!
cd ..

echo -e "${GREEN}Starting Loan Agent (port 9003)...${NC}"
cd loan_agent && python main.py &
LOAN_PID=$!
cd ..

echo -e "${GREEN}Starting Investment Agent (port 9004)...${NC}"
cd investment_agent && python main.py &
INVEST_PID=$!
cd ..

echo -e "${GREEN}All agents started!${NC}"
echo "Account Summary Agent PID: $SUMMARY_PID"
echo "Transfer Agent PID: $TRANSFER_PID"
echo "Loan Agent PID: $LOAN_PID"
echo "Investment Agent PID: $INVEST_PID"

# Trap to clean up on exit
cleanup() {
    echo -e "${YELLOW}Stopping all agents...${NC}"
    kill $SUMMARY_PID $TRANSFER_PID $LOAN_PID $INVEST_PID 2>/dev/null
    echo -e "${GREEN}All agents stopped.${NC}"
}

trap cleanup EXIT

# Wait for all background processes
wait
