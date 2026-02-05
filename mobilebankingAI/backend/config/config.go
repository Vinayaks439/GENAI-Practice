package config

import "github.com/spf13/viper"

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
	var config *Config
	viper.AutomaticEnv()
	viper.AddConfigPath("app")
	viper.SetConfigName("env")
	if err := viper.ReadInConfig(); err != nil {
		return config, err
	}
	err := viper.Unmarshal(&config)
	return config, err
}
