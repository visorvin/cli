// Copyright 2026 visor. Licensed under Apache-2.0. See LICENSE.

package cli

import (
	"strings"
	"testing"
)

func TestTelemetryHeadersIncludeCoarseCLIContext(t *testing.T) {
	flags := &rootFlags{
		agent:    true,
		asJSON:   true,
		compact:  true,
		markdown: true,
		noCache:  true,
	}

	headers := flags.telemetryHeaders()

	if headers["X-Visor-Client"] != "cli" {
		t.Fatalf("X-Visor-Client = %q, want cli", headers["X-Visor-Client"])
	}
	if headers["X-Visor-CLI-Version"] != version {
		t.Fatalf("X-Visor-CLI-Version = %q, want %q", headers["X-Visor-CLI-Version"], version)
	}
	context := headers["X-Visor-CLI-Context"]
	for _, want := range []string{"agent", "compact", "json", "markdown", "no-cache"} {
		if !strings.Contains(context, want) {
			t.Fatalf("X-Visor-CLI-Context = %q, want it to include %q", context, want)
		}
	}
	if strings.Contains(context, "select") || strings.Contains(context, "profile") {
		t.Fatalf("X-Visor-CLI-Context = %q, should not include user-specific flags", context)
	}
}
