createdb:
	docker exec -ti postgres createdb --username=root --owner=root bank_account
dropdb:
	docker exec -ti postgres dropdb bank_account
postgres:
	docker run --name postgres -p 5432:5432 -e POSTGRES_USER=root -e POSTGRES_PASSWORD=secret -d postgres:12-alpine
migrateinit:
	migrate create -ext sql -dir db/migration -seq init_schema
migrateup:
	migrate -path db/migration -database "postgres://root:secret@localhost:5432/bank_account?sslmode=disable" -verbose up
migratedown:
	migrate -path db/migration -database "postgres://root:secret@localhost:5432/bank_account?sslmode=disable" -verbose down
removepg:
	docker kill postgres && docker rm postgres
sqlcgen:
	sqlc generate
gotest:
	go test -v -cover ./...
gobuild:
	go build -v ./...
start:
	go run main.go
.PHONY: postgres createdb dropdb migrateup migratedown removepg sqlcgen gotest gobuild start
