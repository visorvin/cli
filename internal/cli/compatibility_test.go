// Copyright 2026 visor. Licensed under Apache-2.0. See LICENSE.

package cli

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/visorvin/cli/internal/client"
	"github.com/visorvin/cli/internal/config"
)

func TestCheckCLICompatibilityParsesResponseWithoutAuth(t *testing.T) {
	var gotAuth string
	var gotClient string
	var gotVersion string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != compatibilityPath {
			t.Fatalf("path = %q, want %q", r.URL.Path, compatibilityPath)
		}
		gotAuth = r.Header.Get("Authorization")
		gotClient = r.Header.Get("X-Visor-Client")
		gotVersion = r.Header.Get("X-Visor-CLI-Version")
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"schema_version":"1","client":"cli","status":"supported","installed_version":"1.0.13","version_recognized":true,"minimum_supported_version":"1.0.12","update_url":"https://github.com/visorvin/cli/releases/latest","update_command":"update now"}`))
	}))
	defer srv.Close()

	c := client.New(&config.Config{BaseURL: srv.URL, VisorApiKey: "secret"}, time.Second, 0)
	c.Telemetry = map[string]string{
		"X-Visor-Client":      "cli",
		"X-Visor-CLI-Version": version,
	}

	got, err := checkCLICompatibility(context.Background(), c)
	if err != nil {
		t.Fatalf("checkCLICompatibility returned error: %v", err)
	}
	if got.Status != "supported" || got.InstalledVersion != "1.0.13" {
		t.Fatalf("compatibility = %+v", got)
	}
	if gotAuth != "" {
		t.Fatalf("Authorization header = %q, want empty", gotAuth)
	}
	if gotClient != "cli" || gotVersion != version {
		t.Fatalf("telemetry headers = client %q version %q", gotClient, gotVersion)
	}
}

func TestDoctorJSONIncludesCompatibilityAndFreshness(t *testing.T) {
	origFetch := fetchLatestCLIRelease
	fetchLatestCLIRelease = func(context.Context, *http.Client) (string, string, error) {
		return "1.0.20", "https://github.com/visorvin/cli/releases/tag/v1.0.20", nil
	}
	defer func() { fetchLatestCLIRelease = origFetch }()

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/":
			_, _ = w.Write([]byte(`{"ok":true}`))
		case compatibilityPath:
			w.Header().Set("Content-Type", "application/json")
			_, _ = w.Write([]byte(`{"schema_version":"1","client":"cli","status":"supported","installed_version":"1.0.13","version_recognized":true,"minimum_supported_version":"1.0.12","update_url":"https://github.com/visorvin/cli/releases/latest","update_command":"update now"}`))
		default:
			http.NotFound(w, r)
		}
	}))
	defer srv.Close()
	t.Setenv("VISOR_BASE_URL", srv.URL)
	t.Setenv("VISOR_API_KEY", "test-token")

	flags := &rootFlags{asJSON: true, configPath: t.TempDir() + "/config.toml", timeout: time.Second}
	cmd := newDoctorCmd(flags)
	var out bytes.Buffer
	cmd.SetOut(&out)
	if err := cmd.Execute(); err != nil {
		t.Fatalf("doctor failed: %v\n%s", err, out.String())
	}

	var report map[string]any
	if err := json.Unmarshal(out.Bytes(), &report); err != nil {
		t.Fatalf("doctor JSON did not parse: %v\n%s", err, out.String())
	}
	if report["api_compatibility"] != "supported" {
		t.Fatalf("api_compatibility = %v", report["api_compatibility"])
	}
	if report["release_freshness"] != "outdated" {
		t.Fatalf("release_freshness = %v", report["release_freshness"])
	}
	details, ok := report["release_freshness_details"].(map[string]any)
	if !ok || details["latest_version"] != "1.0.20" {
		t.Fatalf("release_freshness_details = %#v", report["release_freshness_details"])
	}
}

func TestReleaseFreshnessComparison(t *testing.T) {
	origFetch := fetchLatestCLIRelease
	defer func() { fetchLatestCLIRelease = origFetch }()

	tests := []struct {
		name      string
		installed string
		latest    string
		want      string
	}{
		{name: "current", installed: "1.0.13", latest: "v1.0.13", want: "current"},
		{name: "outdated", installed: "1.0.13", latest: "1.0.14", want: "outdated"},
		{name: "ahead", installed: "1.1.0", latest: "1.0.14", want: "current"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			fetchLatestCLIRelease = func(context.Context, *http.Client) (string, string, error) {
				return tt.latest, defaultUpdateURL, nil
			}
			got := checkReleaseFreshness(context.Background(), http.DefaultClient, tt.installed)
			if got.Status != tt.want {
				t.Fatalf("status = %q, want %q (%+v)", got.Status, tt.want, got)
			}
		})
	}
}

func TestUnsupportedCLIAPIErrorRendering(t *testing.T) {
	minimum := "1.0.12"
	reason := "minimum_version"
	body := `{"error":{"code":"unsupported_cli_version","message":"Please update Visor CLI.","installed_version":"1.0.11","minimum_supported_version":"1.0.12","reason_code":"minimum_version","update_command":"visor update"}}`
	err := classifyAPIError(&client.APIError{Method: "GET", Path: "/v1/listings", StatusCode: 400, Body: body}, &rootFlags{})
	if err == nil {
		t.Fatal("expected classified error")
	}
	for _, want := range []string{"Please update Visor CLI.", "installed_version: 1.0.11", "minimum_supported_version: " + minimum, "reason_code: " + reason, "update_command: visor update"} {
		if !strings.Contains(err.Error(), want) {
			t.Fatalf("error %q does not contain %q", err.Error(), want)
		}
	}
}

func TestCheckCLICompatibilityMalformedAndUnavailable(t *testing.T) {
	t.Run("malformed", func(t *testing.T) {
		srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			_, _ = w.Write([]byte(`{"status":"confused"}`))
		}))
		defer srv.Close()
		c := client.New(&config.Config{BaseURL: srv.URL}, time.Second, 0)
		_, err := checkCLICompatibility(context.Background(), c)
		if err == nil || !strings.Contains(err.Error(), "unknown status") {
			t.Fatalf("expected malformed status error, got %v", err)
		}
	})

	t.Run("unavailable", func(t *testing.T) {
		srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			http.Error(w, "no route", http.StatusNotFound)
		}))
		defer srv.Close()
		c := client.New(&config.Config{BaseURL: srv.URL}, time.Second, 0)
		_, err := checkCLICompatibility(context.Background(), c)
		if err == nil || !strings.Contains(err.Error(), "HTTP 404") {
			t.Fatalf("expected unavailable endpoint error, got %v", err)
		}
	})
}
