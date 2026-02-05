DB_NAME=mobilebanking
DB_URL=postgres://root:secret@localhost:5432/$(DB_NAME)?sslmode=disable

# Database commands
postgres:
	docker run --name postgres -p 5432:5432 -e POSTGRES_USER=root -e POSTGRES_PASSWORD=secret -d postgres:12-alpine

createdb:
	docker exec -ti postgres createdb --username=root --owner=root $(DB_NAME)

dropdb:
	docker exec -ti postgres dropdb $(DB_NAME)

removepg:
	docker kill postgres && docker rm postgres

# Migration commands
migrateinit:
	migrate create -ext sql -dir backend/db/migration -seq init_schema

migrateup:
	migrate -path backend/db/migration -database "$(DB_URL)" -verbose up

migratedown:
	migrate -path backend/db/migration -database "$(DB_URL)" -verbose down

# SQL generation
sqlcgen:
	sqlc generate

# Go backend commands
gotest:
	go test -v -cover ./...

gobuild:
	go build -v ./...

backend:
	cd backend && go run main.go

# Python agents commands
agents-install:
	cd agents && pip install -r requirements.txt

agents-start:
	cd agents && bash run_agents.sh

agent-summary:
	cd agents/account_summary_agent && python main.py

agent-transfer:
	cd agents/transfer_agent && python main.py

agent-loan:
	cd agents/loan_agent && python main.py

agent-invest:
	cd agents/investment_agent && python main.py

# Frontend commands
frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

# Seed database with test data
seed:
	docker exec -i postgres psql -U root -d $(DB_NAME) < db/seed.sql

# Run everything
start-all: 
	@echo "Starting all services..."
	@echo "1. Start PostgreSQL: make postgres"
	@echo "2. Create database: make createdb"
	@echo "3. Run migrations: make migrateup"
	@echo "4. Seed data: make seed"
	@echo "5. Start agents (in separate terminal): make agents-start"
	@echo "6. Start backend (in separate terminal): make backend"
	@echo "7. Start frontend (in separate terminal): make frontend-dev"

# Help
help:
	@echo "Mobile Banking AI - Available Commands"
	@echo ""
	@echo "Database:"
	@echo "  postgres      - Start PostgreSQL container"
	@echo "  createdb      - Create the database"
	@echo "  dropdb        - Drop the database"
	@echo "  migrateup     - Run migrations"
	@echo "  migratedown   - Rollback migrations"
	@echo "  seed          - Seed test data"
	@echo ""
	@echo "Backend:"
	@echo "  backend       - Start Go backend server"
	@echo "  gobuild       - Build Go code"
	@echo "  gotest        - Run Go tests"
	@echo ""
	@echo "Agents:"
	@echo "  agents-install - Install Python dependencies"
	@echo "  agents-start   - Start all Python agents"
	@echo "  agent-summary  - Start only summary agent"
	@echo "  agent-transfer - Start only transfer agent"
	@echo "  agent-loan     - Start only loan agent"
	@echo "  agent-invest   - Start only investment agent"
	@echo ""
	@echo "Frontend:"
	@echo "  frontend-install - Install npm dependencies"
	@echo "  frontend-dev     - Start dev server"
	@echo "  frontend-build   - Build for production"

.PHONY: postgres createdb dropdb migrateup migratedown removepg sqlcgen gotest gobuild backend agents-install agents-start agent-summary agent-transfer agent-loan agent-invest frontend-install frontend-dev frontend-build seed start-all help
