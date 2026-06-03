// Copyright 2026 Visor. Licensed under Apache-2.0. See LICENSE.

package config

import "testing"

func TestAuthHeaderNormalizesBearerTokenFromAPIKey(t *testing.T) {
	cfg := &Config{VisorApiKey: " Bearer test-token "}

	if got := cfg.AuthHeader(); got != "Bearer test-token" {
		t.Fatalf("AuthHeader() = %q, want %q", got, "Bearer test-token")
	}
}

func TestAuthHeaderNormalizesBearerTokenFromAccessToken(t *testing.T) {
	cfg := &Config{AccessToken: " Bearer test-token "}

	if got := cfg.AuthHeader(); got != "Bearer test-token" {
		t.Fatalf("AuthHeader() = %q, want %q", got, "Bearer test-token")
	}
}

func TestClearTokensClearsAllStoredAuthMaterial(t *testing.T) {
	cfg := &Config{
		Path:          t.TempDir() + "/config.toml",
		BaseURL:       "https://api.visor.vin",
		AuthHeaderVal: "Bearer header-token",
		VisorApiKey:   "api-key-token",
		AccessToken:   "access-token",
		RefreshToken:  "refresh-token",
	}

	if err := cfg.ClearTokens(); err != nil {
		t.Fatalf("ClearTokens() failed: %v", err)
	}

	loaded, err := Load(cfg.Path)
	if err != nil {
		t.Fatalf("Load() failed: %v", err)
	}
	if got := loaded.AuthHeader(); got != "" {
		t.Fatalf("AuthHeader() after ClearTokens = %q, want empty", got)
	}
}

func TestAuthHeaderPreservesConfigAPIKeySource(t *testing.T) {
	cfg := &Config{VisorApiKey: "test-token", AuthSource: "config"}

	if got := cfg.AuthHeader(); got != "Bearer test-token" {
		t.Fatalf("AuthHeader() = %q, want %q", got, "Bearer test-token")
	}
	if cfg.AuthSource != "config" {
		t.Fatalf("AuthSource = %q, want config", cfg.AuthSource)
	}
}
