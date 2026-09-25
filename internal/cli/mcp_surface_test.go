// Copyright 2026 visor. Licensed under Apache-2.0. See LICENSE.

// External test package: internal/mcp imports internal/cli. Hand-owned tests
// live in internal/cli because regeneration replaces internal/mcp.
package cli_test

import (
	"testing"

	"github.com/mark3labs/mcp-go/server"
	mcptools "github.com/visorvin/cli/internal/mcp"
)

func TestVisorMCPExposesCurrentListingFilters(t *testing.T) {
	s := server.NewMCPServer("visor-mcp-test", "0", server.WithToolCapabilities(false))
	mcptools.RegisterTools(s)
	tools := s.ListTools()

	for _, name := range []string{"listings_list", "facets_list", "dealers_listings_dealers"} {
		tool, ok := tools[name]
		if !ok {
			t.Fatalf("visor-mcp is missing tool %q", name)
		}
		for _, param := range []string{
			"dealer_id", "option_slug", "exclude_option_slug", "model_code", "dealer_group_id",
			"exclude_dealer_id", "exclude_dealer_group_id", "listed_after",
		} {
			if _, ok := tool.Tool.InputSchema.Properties[param]; !ok {
				t.Errorf("visor-mcp tool %q is missing parameter %q", name, param)
			}
		}
	}

	for _, name := range []string{"tail", "analytics"} {
		if _, ok := tools[name]; ok {
			t.Errorf("visor-mcp must not expose generic generator tool %q", name)
		}
	}
}
