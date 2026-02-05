package config

import (
	"os"
	"strconv"
)

type Config struct {
	Port                 int    `mapstructure:"PORT"`
	Host                 string `mapstructure:"HOST"`
	DBUser               string `mapstructure:"DB_USER"`
	DBPass               string `mapstructure:"DB_PASS"`
	DBHost               string `mapstructure:"DB_HOST"`
	DBPort               int    `mapstructure:"DB_PORT"`
	SummaryAgentCardUrl  string `mapstructure:"SUMMARY_AGENT_CARD_URL"`
	TransferAgentCardUrl string `mapstructure:"TRANSFER_AGENT_CARD_URL"`
	LoadAgentCardUrl     string `mapstructure:"LOAD_AGENT_CARD_URL"`
	InvestAgentCardUrl   string `mapstructure:"INVEST_AGENT_CARD_URL"`
}

func LoadConfig() (*Config, error) {
	config := &Config{
		Port:                 getEnvInt("PORT", 8080),
		Host:                 getEnv("HOST", "0.0.0.0"),
		DBUser:               getEnv("DB_USER", "root"),
		DBPass:               getEnv("DB_PASS", "secret"),
		DBHost:               getEnv("DB_HOST", "localhost"),
		DBPort:               getEnvInt("DB_PORT", 5432),
		SummaryAgentCardUrl:  getEnv("SUMMARY_AGENT_CARD_URL", "http://localhost:9001"),
		TransferAgentCardUrl: getEnv("TRANSFER_AGENT_CARD_URL", "http://localhost:9002"),
		LoadAgentCardUrl:     getEnv("LOAD_AGENT_CARD_URL", "http://localhost:9003"),
		InvestAgentCardUrl:   getEnv("INVEST_AGENT_CARD_URL", "http://localhost:9004"),
	}
	return config, nil
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intVal, err := strconv.Atoi(value); err == nil {
			return intVal
		}
	}
	return defaultValue
}
