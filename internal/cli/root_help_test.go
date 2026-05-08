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
		`__      ___ ___ ___`,
		"see the whole market",
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

func TestSubcommandHelpHidesGlobalFlagWall(t *testing.T) {
	cmd := RootCmd()
	var out bytes.Buffer
	cmd.SetOut(&out)
	cmd.SetErr(&out)
	cmd.SetArgs([]string{"listings", "--help"})

	if err := cmd.Execute(); err != nil {
		t.Fatalf("listings help failed: %v", err)
	}
	got := out.String()
	for _, want := range []string{
		"Commands:",
		"list",
		"get",
		"Run \"visor help advanced\"",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("listings help missing %q:\n%s", want, got)
		}
	}
	for _, clutter := range []string{"Global Flags:", "--deliver string", "--rate-limit float", "--data-source string"} {
		if strings.Contains(got, clutter) {
			t.Fatalf("listings help includes clutter %q:\n%s", clutter, got)
		}
	}
}

func TestEndpointHelpShowsCuratedFlagsOnly(t *testing.T) {
	cmd := RootCmd()
	var out bytes.Buffer
	cmd.SetOut(&out)
	cmd.SetErr(&out)
	cmd.SetArgs([]string{"listings", "list", "--help"})

	if err := cmd.Execute(); err != nil {
		t.Fatalf("listings list help failed: %v", err)
	}
	got := out.String()
	for _, want := range []string{
		"Key Flags:",
		"--make string",
		"--max-price string",
		"Output Flags:",
		"--agent",
		"--select string",
	} {
		if !strings.Contains(got, want) {
			t.Fatalf("listings list help missing %q:\n%s", want, got)
		}
	}
	for _, clutter := range []string{"Global Flags:", "--exclude-assembly-country", "--deliver string", "--rate-limit float"} {
		if strings.Contains(got, clutter) {
			t.Fatalf("listings list help includes clutter %q:\n%s", clutter, got)
		}
	}
}
