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

func TestFilterFieldsValidatedAcceptsRowRelativeListFields(t *testing.T) {
	input := json.RawMessage(`{
		"meta":{"source":"live"},
		"results":{"data":[{"id":"listing-1","vin":"1FA","year":2018,"price":19995,"miles":81234,"photo_urls":["https://example.test/photo.jpg"]}]}
	}`)

	got, err := filterFieldsValidated(input, "id,vin,year,price,miles")
	if err != nil {
		t.Fatalf("filterFieldsValidated returned error: %v", err)
	}

	var out map[string]any
	if err := json.Unmarshal(got, &out); err != nil {
		t.Fatalf("unmarshal output: %v", err)
	}
	row := out["results"].(map[string]any)["data"].([]any)[0].(map[string]any)
	for _, want := range []string{"id", "vin", "year", "price", "miles"} {
		if _, ok := row[want]; !ok {
			t.Fatalf("row-relative select missing %s: %#v", want, row)
		}
	}
	if _, ok := row["photo_urls"]; ok {
		t.Fatalf("row-relative select should not include unselected photo_urls: %#v", row)
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

func TestPrintOutputWithFlagsRendersMarkdownEnvelope(t *testing.T) {
	var buf bytes.Buffer
	flags := &rootFlags{markdown: true, compact: true}
	input := json.RawMessage(`{
		"meta":{"source":"live"},
		"results":{"data":[{"vin":"1FA","year":2018,"make":"ford","model":"mustang","price":19995,"miles":81234,"vdp_url":"https://example.test/car","photo_urls":["https://example.test/photo.jpg"]}]}
	}`)

	if err := printOutputWithFlags(&buf, input, flags); err != nil {
		t.Fatalf("printOutputWithFlags returned error: %v", err)
	}
	out := buf.String()
	for _, want := range []string{"## Listings", "_1 result._", "| vin | year | make | model | price | miles | vdp_url |", "| 1FA | 2018 | ford | mustang | 19995 | 81234 | [link](https://example.test/car) |", "## Meta", "| source | live |"} {
		if !strings.Contains(out, want) {
			t.Fatalf("markdown output missing %q:\n%s", want, out)
		}
	}
	if strings.Contains(out, "photo_urls") {
		t.Fatalf("markdown compact output should omit photo_urls:\n%s", out)
	}
}

func TestPrintMarkdownRendersDirectResultsArray(t *testing.T) {
	var buf bytes.Buffer
	input := json.RawMessage(`{
		"meta":{"source":"local","resource_type":"listings"},
		"results":[{"vin":"1FA","year":2018,"make":"ford","model":"mustang","price":19995,"miles":81234,"vdp_url":"https://example.test/car"}]
	}`)

	if err := printMarkdown(&buf, input); err != nil {
		t.Fatalf("printMarkdown returned error: %v", err)
	}
	out := buf.String()
	for _, want := range []string{"## Listings", "| vin | year | make | model | price | miles | vdp_url |", "## Meta", "| resource_type | listings |"} {
		if !strings.Contains(out, want) {
			t.Fatalf("markdown output missing %q:\n%s", want, out)
		}
	}
}

func TestPrintMarkdownRendersFacetSections(t *testing.T) {
	var buf bytes.Buffer
	input := json.RawMessage(`{
		"meta":{"source":"live"},
		"results":{"facets":{"make":[{"value":"ford","count":12},{"value":"toyota","count":8}],"year":[{"value":2024,"count":4}]},"stats":{"total":20,"min_price":10000,"max_price":30000}}
	}`)

	if err := printMarkdown(&buf, input); err != nil {
		t.Fatalf("printMarkdown returned error: %v", err)
	}
	out := buf.String()
	for _, want := range []string{"## Facets", "### Stats", "| total | 20 |", "### Facet Values", "#### Make", "| value | count |", "| ford | 12 |", "#### Year"} {
		if !strings.Contains(out, want) {
			t.Fatalf("facet markdown output missing %q:\n%s", want, out)
		}
	}
}

func TestPrintMarkdownRendersNestedVehicleDetail(t *testing.T) {
	var buf bytes.Buffer
	input := json.RawMessage(`{
		"meta":{"source":"live"},
		"results":{"vin":"1FA","status":"active","latest_listing":{"vin":"1FA","year":2018,"make":"ford","model":"mustang","price":19995,"miles":81234,"vdp_url":"https://example.test/car"},"build":{"trim":"GT","fuel_type":"gas"}}
	}`)

	if err := printMarkdown(&buf, input); err != nil {
		t.Fatalf("printMarkdown returned error: %v", err)
	}
	out := buf.String()
	for _, want := range []string{"## Vehicle", "### Summary", "| vin | 1FA |", "### Vehicle", "| vin | 1FA |", "| vdp_url | [link](https://example.test/car) |", "### Build", "| trim | GT |", "| fuel_type | gas |"} {
		if !strings.Contains(out, want) {
			t.Fatalf("nested markdown output missing %q:\n%s", want, out)
		}
	}
}
