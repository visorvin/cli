// Copyright 2026 Visor. Licensed under Apache-2.0. See LICENSE.

package cli

import (
	"bytes"
	"encoding/json"
	"strings"
	"testing"
)

func TestFilterFieldsValidatedSelectsThroughProvenanceEnvelope(t *testing.T) {
	input := json.RawMessage(`{
		"meta":{"source":"live"},
		"results":{"data":[{"vin":"1FA","year":2018,"miles":81234,"vdp_url":"https://example.test/car","photo_urls":["https://example.test/photo.jpg"]}]}
	}`)

	got, err := filterFieldsValidated(input, "results.data.vin,results.data.miles,results.data.vdp_url")
	if err != nil {
		t.Fatalf("filterFieldsValidated returned error: %v", err)
	}

	var out map[string]any
	if err := json.Unmarshal(got, &out); err != nil {
		t.Fatalf("unmarshal output: %v", err)
	}
	results := out["results"].(map[string]any)
	rows := results["data"].([]any)
	row := rows[0].(map[string]any)
	if row["vin"] != "1FA" || row["miles"].(float64) != 81234 || row["vdp_url"] == nil {
		t.Fatalf("selected row missing expected fields: %#v", row)
	}
	if _, ok := row["photo_urls"]; ok {
		t.Fatalf("unexpected unselected photo_urls field: %#v", row)
	}
}

func TestFilterFieldsValidatedErrorsOnUnknownFieldWithValidExamples(t *testing.T) {
	input := json.RawMessage(`{"results":{"data":[{"vin":"1FA","miles":81234,"vdp_url":"https://example.test/car"}]}}`)

	_, err := filterFieldsValidated(input, "results.data.mileage,results.data.url")
	if err == nil {
		t.Fatal("expected unknown field error")
	}
	msg := err.Error()
	for _, want := range []string{"unknown selected field", "results.data.mileage", "results.data.url", "results.data.miles", "results.data.vdp_url"} {
		if !strings.Contains(msg, want) {
			t.Fatalf("error %q missing %q", msg, want)
		}
	}
}

func TestCompactFieldsKeepsUsefulListingRowsAndDropsPhotos(t *testing.T) {
	input := json.RawMessage(`{
		"meta":{"source":"live"},
		"results":{"data":[{"vin":"1FA","year":2018,"make":"ford","model":"mustang","price":19995,"miles":81234,"vdp_url":"https://example.test/car","photo_urls":["https://example.test/photo.jpg"],"engine":"verbose"}]}
	}`)

	got := compactFields(input)
	var out map[string]any
	if err := json.Unmarshal(got, &out); err != nil {
		t.Fatalf("unmarshal compact output: %v", err)
	}
	row := out["results"].(map[string]any)["data"].([]any)[0].(map[string]any)
	for _, want := range []string{"vin", "year", "make", "model", "price", "miles", "vdp_url"} {
		if _, ok := row[want]; !ok {
			t.Fatalf("compact listing row missing %s: %#v", want, row)
		}
	}
	if _, ok := row["photo_urls"]; ok {
		t.Fatalf("compact listing row should drop photo_urls: %#v", row)
	}
	if _, ok := row["engine"]; ok {
		t.Fatalf("compact listing row should drop non-allowlisted fields: %#v", row)
	}
}

func TestPrintOutputWithFlagsReturnsSelectValidationError(t *testing.T) {
	var buf bytes.Buffer
	flags := &rootFlags{asJSON: true, selectFields: "results.data.mileage"}
	input := json.RawMessage(`{"results":{"data":[{"vin":"1FA","miles":81234}]}}`)

	err := printOutputWithFlags(&buf, input, flags)
	if err == nil {
		t.Fatal("expected select validation error")
	}
	if !strings.Contains(err.Error(), "results.data.miles") {
		t.Fatalf("expected valid fields in error, got %v", err)
	}
	if buf.Len() != 0 {
		t.Fatalf("expected no output on validation error, got %q", buf.String())
	}
}
