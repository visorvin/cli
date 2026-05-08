// Copyright 2026 Visor. Licensed under Apache-2.0. See LICENSE.

package cli

import (
	"bytes"
	"strings"
	"testing"
)

func TestRootHelpIsCuratedForPublicSurface(t *testing.T) {
	cmd := RootCmd()
	var out bytes.Buffer
	cmd.SetOut(&out)
	cmd.SetErr(&out)
	cmd.SetArgs([]string{"--help"})

	if err := cmd.Execute(); err != nil {
		t.Fatalf("root help failed: %v", err)
	}
	got := out.String()
	for _, want := range []string{
		"Core Commands:",
		"listings      Search and fetch vehicle listings",
		"Common Flags:",
		"--select string  Select output fields, e.g. vin,price,miles",
		"visor help advanced",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("root help missing %q:\n%s", want, got)
		}
	}
	for _, clutter := range []string{"import        Import", "workflow      Compound", "--deliver string", "--rate-limit float"} {
		if strings.Contains(got, clutter) {
			t.Fatalf("root help includes advanced clutter %q:\n%s", clutter, got)
		}
	}
}

func TestAdvancedHelpShowsHiddenSurface(t *testing.T) {
	cmd := RootCmd()
	var out bytes.Buffer
	cmd.SetOut(&out)
	cmd.SetErr(&out)
	cmd.SetArgs([]string{"help", "advanced"})

	if err := cmd.Execute(); err != nil {
		t.Fatalf("advanced help failed: %v", err)
	}
	got := out.String()
	for _, want := range []string{
		"Advanced Visor CLI commands and flags.",
		"sync          Sync API data to local SQLite",
		"import        Import JSONL records",
		"--deliver string",
		"--rate-limit float",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("advanced help missing %q:\n%s", want, got)
		}
	}
}
