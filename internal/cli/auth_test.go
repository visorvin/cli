// Copyright 2026 Visor. Licensed under Apache-2.0. See LICENSE.

package cli

import (
	"strings"
	"testing"

	"github.com/spf13/cobra"
	"github.com/visorvin/cli/internal/config"
)

func TestReadTokenForSetTokenFromStdinTrimsWhitespace(t *testing.T) {
	cmd := &cobra.Command{}
	cmd.SetIn(strings.NewReader("  test-token\n"))

	got, err := readTokenForSetToken(cmd, true)
	if err != nil {
		t.Fatalf("readTokenForSetToken returned error: %v", err)
	}
	if got != "test-token" {
		t.Fatalf("token = %q, want test-token", got)
	}
}

func TestReadTokenForSetTokenFromStdinRejectsEmptyInput(t *testing.T) {
	cmd := &cobra.Command{}
	cmd.SetIn(strings.NewReader(" \n\t"))

	_, err := readTokenForSetToken(cmd, true)
	if err == nil || !strings.Contains(err.Error(), "no token provided") {
		t.Fatalf("expected empty-token error, got %v", err)
	}
}

func TestAuthSetTokenRejectsPositionalToken(t *testing.T) {
	cmd := newAuthSetTokenCmd(&rootFlags{})
	err := cmd.Args(cmd, []string{"secret-token"})
	if err == nil {
		t.Fatal("expected positional token to be rejected")
	}
	if strings.Contains(err.Error(), "secret-token") {
		t.Fatalf("error leaked token: %v", err)
	}
	if !strings.Contains(err.Error(), "--stdin") {
		t.Fatalf("error should point users to --stdin, got %v", err)
	}
}

func TestAuthSetTokenStdinSavesConfig(t *testing.T) {
	configPath := t.TempDir() + "/config.toml"
	cmd := newAuthSetTokenCmd(&rootFlags{configPath: configPath})
	cmd.SetIn(strings.NewReader("test-token\n"))
	cmd.SetArgs([]string{"--stdin"})

	if err := cmd.Execute(); err != nil {
		t.Fatalf("auth set-token --stdin failed: %v", err)
	}

	cfg, err := config.Load(configPath)
	if err != nil {
		t.Fatalf("loading config: %v", err)
	}
	if cfg.AccessToken != "test-token" {
		t.Fatalf("saved access token = %q, want test-token", cfg.AccessToken)
	}
}

func TestAuthSetTokenStdinNormalizesBearerPrefix(t *testing.T) {
	configPath := t.TempDir() + "/config.toml"
	cmd := newAuthSetTokenCmd(&rootFlags{configPath: configPath})
	cmd.SetIn(strings.NewReader("Bearer test-token\n"))
	cmd.SetArgs([]string{"--stdin"})

	if err := cmd.Execute(); err != nil {
		t.Fatalf("auth set-token --stdin failed: %v", err)
	}

	cfg, err := config.Load(configPath)
	if err != nil {
		t.Fatalf("loading config: %v", err)
	}
	if cfg.AccessToken != "test-token" {
		t.Fatalf("saved access token = %q, want test-token", cfg.AccessToken)
	}
	if got := cfg.AuthHeader(); got != "Bearer test-token" {
		t.Fatalf("AuthHeader() = %q, want %q", got, "Bearer test-token")
	}
}

func TestAuthSetTokenClearsLegacyAPIKey(t *testing.T) {
	configPath := t.TempDir() + "/config.toml"
	cfg := &config.Config{
		Path:        configPath,
		BaseURL:     "https://api.visor.vin",
		VisorApiKey: "old-token",
	}
	if err := cfg.SaveTokens("", "", "", "", cfg.TokenExpiry); err != nil {
		t.Fatalf("saving initial config: %v", err)
	}

	cmd := newAuthSetTokenCmd(&rootFlags{configPath: configPath})
	cmd.SetIn(strings.NewReader("new-token\n"))
	cmd.SetArgs([]string{"--stdin"})

	if err := cmd.Execute(); err != nil {
		t.Fatalf("auth set-token --stdin failed: %v", err)
	}

	loaded, err := config.Load(configPath)
	if err != nil {
		t.Fatalf("loading config: %v", err)
	}
	if loaded.VisorApiKey != "" {
		t.Fatalf("legacy api key = %q, want empty", loaded.VisorApiKey)
	}
	if got := loaded.AuthHeader(); got != "Bearer new-token" {
		t.Fatalf("AuthHeader() = %q, want %q", got, "Bearer new-token")
	}
}
