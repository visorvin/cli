// Copyright 2026 visor. Licensed under Apache-2.0. See LICENSE.

package client

import (
	"io"
	"net/http"
	"strings"
	"testing"
	"time"

	"github.com/visorvin/cli/internal/config"
)

type roundTripFunc func(*http.Request) (*http.Response, error)

func (f roundTripFunc) RoundTrip(req *http.Request) (*http.Response, error) {
	return f(req)
}

func TestClientSendsUserAgentAndTelemetryHeaders(t *testing.T) {
	var gotUserAgent string
	var gotClient string
	var gotVersion string
	var gotContext string

	c := New(&config.Config{BaseURL: "https://api.example.test"}, 5*time.Second, 0)
	c.HTTPClient = &http.Client{Transport: roundTripFunc(func(r *http.Request) (*http.Response, error) {
		gotUserAgent = r.Header.Get("User-Agent")
		gotClient = r.Header.Get("X-Visor-Client")
		gotVersion = r.Header.Get("X-Visor-CLI-Version")
		gotContext = r.Header.Get("X-Visor-CLI-Context")
		return &http.Response{
			StatusCode: 200,
			Body:       io.NopCloser(strings.NewReader(`{"ok":true}`)),
			Header:     http.Header{},
		}, nil
	})}
	c.UserAgent = "visor-cli/1.2.3"
	c.NoCache = true
	c.Telemetry = map[string]string{
		"X-Visor-Client":      "cli",
		"X-Visor-CLI-Version": "1.2.3",
		"X-Visor-CLI-Context": "agent,markdown",
	}

	if _, err := c.Get("/v1/listings", nil); err != nil {
		t.Fatalf("GET failed: %v", err)
	}

	if gotUserAgent != "visor-cli/1.2.3" {
		t.Fatalf("User-Agent = %q, want %q", gotUserAgent, "visor-cli/1.2.3")
	}
	if gotClient != "cli" {
		t.Fatalf("X-Visor-Client = %q, want %q", gotClient, "cli")
	}
	if gotVersion != "1.2.3" {
		t.Fatalf("X-Visor-CLI-Version = %q, want %q", gotVersion, "1.2.3")
	}
	if gotContext != "agent,markdown" {
		t.Fatalf("X-Visor-CLI-Context = %q, want %q", gotContext, "agent,markdown")
	}
}
