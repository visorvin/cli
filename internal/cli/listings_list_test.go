// Copyright 2026 visor. Licensed under Apache-2.0. See LICENSE.

package cli

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"
)

func TestListingsListSendsPublicOptionsPackagesAndInventoryTypeParams(t *testing.T) {
	var gotPath string
	var gotQuery url.Values

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotPath = r.URL.Path
		gotQuery = r.URL.Query()
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"data":[],"pagination":{"limit":2,"offset":0,"total":0},"meta":{}}`))
	}))
	defer srv.Close()

	t.Setenv("VISOR_BASE_URL", srv.URL)
	t.Setenv("VISOR_API_KEY", "test-token")

	cmd := RootCmd()
	var out bytes.Buffer
	var errOut bytes.Buffer
	cmd.SetOut(&out)
	cmd.SetErr(&errOut)
	cmd.SetArgs([]string{
		"listings", "list",
		"--data-source", "live",
		"--no-cache",
		"--json",
		"--make", "BMW",
		"--model", "X7",
		"--trim", "40i",
		"--inventory-type", "used",
		"--options-packages", "ZPP,ZPK",
		"--limit", "2",
		"--fields", "default,options_packages",
	})

	if err := cmd.Execute(); err != nil {
		t.Fatalf("listings list failed: %v\nstderr:\n%s", err, errOut.String())
	}
	if gotPath != "/v1/listings" {
		t.Fatalf("path = %q, want /v1/listings", gotPath)
	}
	for key, want := range map[string]string{
		"inventory_type":   "used",
		"options_packages": "ZPP,ZPK",
		"fields":           "default,options_packages",
		"limit":            "2",
	} {
		if got := gotQuery.Get(key); got != want {
			t.Fatalf("query %s = %q, want %q (full query: %#v)", key, got, want, gotQuery)
		}
	}
	for _, forbidden := range []string{"car_type", "option_codes", "options", "packages"} {
		if _, ok := gotQuery[forbidden]; ok {
			t.Fatalf("unexpected private/alternate query param %q present: %#v", forbidden, gotQuery)
		}
	}

	var envelope map[string]any
	if err := json.Unmarshal(out.Bytes(), &envelope); err != nil {
		t.Fatalf("output is not JSON: %v\n%s", err, out.String())
	}
}
