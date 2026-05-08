// Copyright 2026 Visor. Licensed under Apache-2.0. See LICENSE.

package cli

import (
	"fmt"
	"io"

	"github.com/spf13/cobra"
)

func printRootHelp(w io.Writer) {
	fmt.Fprint(w, `Visor CLI — read-only vehicle listings, VIN, dealer, and facet search.

Usage:
  visor [command]

Core Commands:
  listings      Search and fetch vehicle listings
  vins          Look up VIN records
  dealers       Search and fetch dealers
  facets        Get listing filter facets
  doctor        Check auth and connectivity
  auth          Manage API credentials

Agent Commands:
  agent-context Emit CLI metadata for agents
  which         Find the command for a task

Other Commands:
  completion    Generate shell completion
  version       Print version
  help          Help about any command

Common Flags:
      --agent          JSON + compact + non-interactive mode
      --json           Output JSON
      --select string  Select output fields, e.g. vin,price,miles
      --config string  Config file path
  -h, --help           help for visor
  -v, --version        version for visor

Run "visor help advanced" for advanced flags and local-cache commands.
`)
}

func newAdvancedHelpCmd(rootCmd *cobra.Command) *cobra.Command {
	cmd := &cobra.Command{
		Use:    "advanced",
		Short:  "Show advanced commands and flags",
		Hidden: true,
		Run: func(cmd *cobra.Command, args []string) {
			printAdvancedHelp(cmd.OutOrStdout(), rootCmd)
		},
	}
	cmd.SetHelpFunc(func(cmd *cobra.Command, args []string) {
		printAdvancedHelp(cmd.OutOrStdout(), rootCmd)
	})
	return cmd
}

func printAdvancedHelp(w io.Writer, rootCmd *cobra.Command) {
	fmt.Fprint(w, `Advanced Visor CLI commands and flags.

Local Cache Commands:
  sync          Sync API data to local SQLite for offline search
  search        Full-text search across synced data or live API
  profile       Named sets of flags saved for reuse
  workflow      Compound local/archive workflows

Developer Commands:
  api           Browse generated API endpoint metadata
  feedback      Record local CLI feedback
  import        Import JSONL records through API write paths

Advanced Flags:
      --compact              Return compact JSON fields
      --csv                  Output CSV
      --data-source string   auto, live, or local data source
      --deliver string       Route output to stdout, file:<path>, or webhook:<url>
      --dry-run              Show request without sending
      --human-friendly       Enable colored output and rich formatting
      --idempotent           Treat already-existing create results as a successful no-op
      --no-cache             Bypass response cache
      --no-color             Disable colored output
      --no-input             Disable interactive prompts
      --plain                Output plain tab-separated text
      --profile string       Apply values from a saved profile
      --quiet                Suppress normal output
      --rate-limit float     Max requests per second
      --timeout duration     Request timeout
      --yes                  Skip confirmation prompts

Run "visor <command> --help" for command-specific flags.
`)
}
