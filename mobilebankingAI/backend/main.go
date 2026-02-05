/*
Copyright © 2026 NAME HERE <EMAIL ADDRESS>
*/
package main

import (
	"backend/config"
	db "backend/db/sqlc"
	"backend/pkg"
	"context"
	"fmt"
	"log/slog"
	"os"

	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v5/pgxpool"
)

func main() {
	logger := slog.New(slog.NewTextHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelInfo}))
	config, err := config.LoadConfig()
	if err != nil {
		logger.Error("Cannot load config", slog.String("error", err.Error()))
		os.Exit(1)
	}
	connStr := fmt.Sprintf("postgresql://%s:%s@%s:%d/mobilebanking", config.DBUser, config.DBPass, config.DBHost, config.DBPort)
	conn, err := pgxpool.New(context.Background(), connStr)
	if err != nil {
		logger.Error("Unable to connect to database", slog.String("error", err.Error()))
		os.Exit(1)
	}
	defer conn.Close()
	store := db.NewStore(conn)
	router := gin.New()
	// Initialize and start the server
	pkg.InitializeServer(store, config, router, logger)
}
