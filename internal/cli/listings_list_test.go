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

// runAgainstStubAPI executes the CLI against a stub Visor API and returns the
// request path and query it sent, plus stdout.
func runAgainstStubAPI(t *testing.T, args ...string) (string, url.Values, []byte) {
	t.Helper()
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
	cmd.SetArgs(append([]string{"--data-source", "live", "--no-cache", "--json"}, args...))

	if err := cmd.Execute(); err != nil {
		t.Fatalf("%v failed: %v\nstderr:\n%s", args, err, errOut.String())
	}
	return gotPath, gotQuery, out.Bytes()
}

func assertQuery(t *testing.T, got url.Values, want map[string]string) {
	t.Helper()
	for key, value := range want {
		if got.Get(key) != value {
			t.Fatalf("query %s = %q, want %q (full query: %#v)", key, got.Get(key), value, got)
		}
	}
}

func TestListingsListSendsPublicOptionsPackagesAndInventoryTypeParams(t *testing.T) {
	path, query, out := runAgainstStubAPI(t,
		"listings", "list",
		"--make", "BMW",
		"--model", "X7",
		"--trim", "40i",
		"--inventory-type", "used",
		"--options-packages", "ZPP,ZPK",
		"--limit", "2",
		"--fields", "default,options_packages",
	)

	if path != "/v1/listings" {
		t.Fatalf("path = %q, want /v1/listings", path)
	}
	assertQuery(t, query, map[string]string{
		"inventory_type":   "used",
		"options_packages": "ZPP,ZPK",
		"fields":           "default,options_packages",
		"limit":            "2",
	})
	for _, forbidden := range []string{"car_type", "option_codes", "options", "packages"} {
		if _, ok := query[forbidden]; ok {
			t.Fatalf("unexpected private/alternate query param %q present: %#v", forbidden, query)
		}
	}

	var envelope map[string]any
	if err := json.Unmarshal(out, &envelope); err != nil {
		t.Fatalf("output is not JSON: %v\n%s", err, out)
	}
}

func TestListingsListSendsOpenSpecOptionDealerGroupAndListedAtParams(t *testing.T) {
	_, query, _ := runAgainstStubAPI(t,
		"listings", "list",
		"--option-slug", "premium-package",
		"--exclude-option-slug", "tow-package",
		"--model-code", "ZNKAA",
		"--dealer-group-id", "dg:autonation",
		"--exclude-dealer-id", "550e8400-e29b-41d4-a716-446655440000",
		"--exclude-dealer-group-id", "dg:lithia",
		"--listed-after", "2026-09-01T00:00:00Z",
		"--sort", "-listed_at",
	)

	assertQuery(t, query, map[string]string{
		"option_slug":             "premium-package",
		"exclude_option_slug":     "tow-package",
		"model_code":              "ZNKAA",
		"dealer_group_id":         "dg:autonation",
		"exclude_dealer_id":       "550e8400-e29b-41d4-a716-446655440000",
		"exclude_dealer_group_id": "dg:lithia",
		"listed_after":            "2026-09-01T00:00:00Z",
		"sort":                    "-listed_at",
	})
	if _, ok := query["options_packages"]; ok {
		t.Fatalf("option_slug must not be sent as options_packages: %#v", query)
	}
}

func TestDealerInventorySendsDealerInPathOnly(t *testing.T) {
	const dealerID = "550e8400-e29b-41d4-a716-446655440000"
	path, query, _ := runAgainstStubAPI(t,
		"dealers", "listings", "list", dealerID,
		"--option-slug", "premium-package",
	)

	if path != "/v1/dealers/"+dealerID+"/listings" {
		t.Fatalf("path = %q, want dealer inventory path", path)
	}
	if _, ok := query["dealer_id"]; ok {
		t.Fatalf("dealer inventory must not repeat dealer_id as a query param: %#v", query)
	}
	assertQuery(t, query, map[string]string{"option_slug": "premium-package"})
}
