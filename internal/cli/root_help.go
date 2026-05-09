// Copyright 2026 Visor. Licensed under Apache-2.0. See LICENSE.

package cli

import (
	"fmt"
	"io"
	"sort"
	"strings"

	"github.com/spf13/cobra"
	"github.com/spf13/pflag"
)

func printRootHelp(w io.Writer) {
	fmt.Fprint(w, `__      ___ ___ ___  ___  ___
\ \    / /_ _/ __|/ _ \| _ \
 \ \  / / | |\__ \ (_) |   /
  \ \/ / |___|___/\___/|_|_\
   \__/   see the whole market

Visor CLI — read-only vehicle listings, VIN, dealer, and facet search.

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
      --markdown       Output Markdown
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

func installCleanHelp(rootCmd *cobra.Command) {
	var visit func(*cobra.Command)
	visit = func(cmd *cobra.Command) {
		if cmd == rootCmd {
			cmd.SetHelpFunc(func(cmd *cobra.Command, args []string) {
				printRootHelp(cmd.OutOrStdout())
			})
		} else if cmd.Name() != "advanced" {
			cmd.SetHelpFunc(func(cmd *cobra.Command, args []string) {
				printCleanCommandHelp(cmd.OutOrStdout(), cmd)
			})
		}
		for _, child := range cmd.Commands() {
			visit(child)
		}
	}
	visit(rootCmd)
}

func printCleanCommandHelp(w io.Writer, cmd *cobra.Command) {
	if strings.TrimSpace(cmd.Short) != "" {
		fmt.Fprintf(w, "%s\n\n", strings.TrimSpace(cmd.Short))
	}
	fmt.Fprintf(w, "Usage:\n  %s\n", cmd.UseLine())

	children := visibleChildren(cmd)
	if len(children) > 0 {
		fmt.Fprint(w, "\nCommands:\n")
		for _, child := range children {
			fmt.Fprintf(w, "  %-13s %s\n", child.Name(), cleanCommandShort(child))
		}
	}

	if example := strings.TrimSpace(cmd.Example); example != "" {
		fmt.Fprintf(w, "\nExamples:\n%s\n", example)
	}

	keyFlags, filterFlags := cleanLocalFlags(cmd)
	if len(keyFlags) > 0 {
		fmt.Fprint(w, "\nKey Flags:\n")
		printFlagList(w, keyFlags)
	}

	if len(filterFlags) > 0 {
		fmt.Fprint(w, "\nFilter Flags:\n")
		printFlagList(w, filterFlags)
	}

	outputFlags := cleanOutputFlags(cmd)
	if len(outputFlags) > 0 {
		fmt.Fprint(w, "\nOutput Flags:\n")
		printFlagList(w, outputFlags)
	}

	fmt.Fprintf(w, "\nRun \"visor help advanced\" for advanced flags and local-cache commands.\n")
	if len(children) > 0 {
		fmt.Fprintf(w, "Run \"visor %s [command] --help\" for command-specific help.\n", strings.TrimPrefix(cmd.CommandPath(), "visor "))
	}
}

func visibleChildren(cmd *cobra.Command) []*cobra.Command {
	children := make([]*cobra.Command, 0)
	for _, child := range cmd.Commands() {
		if child.Hidden || child.Name() == "help" {
			continue
		}
		children = append(children, child)
	}
	sort.Slice(children, func(i, j int) bool { return children[i].Name() < children[j].Name() })
	return children
}

func cleanCommandShort(cmd *cobra.Command) string {
	short := strings.TrimSpace(cmd.Short)
	if short == "" {
		return ""
	}
	replacements := map[string]string{
		"Returns active, sold, or historical snapshot listing summaries using stable snake_case fields. Unknown filters fail...":         "Search listing summaries",
		"Returns listing-centered detail by listing_id. Missing listings return 404 not_found_error.":                                    "Get listing detail",
		"Returns dealer detail for a stable dealer_id. Missing dealers return 404 not_found_error.":                                      "Get dealer detail",
		"Returns dealer summaries with stable snake_case fields.":                                                                        "Search dealer summaries",
		"Returns inventory listings for one dealer.":                                                                                     "List inventory for one dealer",
		"Shortcut for 'facets list'. Returns categorical facets, numeric range facets, and stats for the listing filter surface. Use...": "Get listing filter facets",
		"Returns categorical facets, numeric range facets, and stats for an explicit listing filter surface facet selection....":         "Get listing filter facets",
		"Returns the current or latest known record for a VIN. Missing VINs return 404 not_found_error.":                                 "Look up a VIN record",
	}
	if cleaned, ok := replacements[short]; ok {
		return cleaned
	}
	if len(short) > 86 {
		return strings.TrimSpace(short[:83]) + "..."
	}
	return short
}

func cleanLocalFlags(cmd *cobra.Command) ([]*pflag.Flag, []*pflag.Flag) {
	names := []string{
		"make", "model", "year", "trim", "state",
		"min-price", "max-price", "min-mileage", "max-mileage",
		"postal-code", "radius", "limit", "sort",
		"facets", "facet-value-limit", "inventory-type", "inventory-status", "all",
	}
	localFlagSet := cmd.LocalFlags()
	keyFlags := lookupVisibleFlags(localFlagSet, names)
	seen := map[string]bool{}
	for _, flag := range keyFlags {
		seen[flag.Name] = true
	}
	var filterFlags []*pflag.Flag
	localFlagSet.VisitAll(func(flag *pflag.Flag) {
		if flag.Hidden || seen[flag.Name] || flag.Name == "help" {
			return
		}
		filterFlags = append(filterFlags, flag)
	})
	sort.Slice(filterFlags, func(i, j int) bool { return filterFlags[i].Name < filterFlags[j].Name })
	return keyFlags, filterFlags
}

func cleanOutputFlags(cmd *cobra.Command) []*pflag.Flag {
	names := []string{"agent", "json", "markdown", "select", "config"}
	return lookupVisibleFlags(cmd.Root().PersistentFlags(), names)
}

func lookupVisibleFlags(flags *pflag.FlagSet, names []string) []*pflag.Flag {
	out := make([]*pflag.Flag, 0, len(names))
	for _, name := range names {
		flag := flags.Lookup(name)
		if flag == nil || flag.Hidden {
			continue
		}
		out = append(out, flag)
	}
	return out
}

func printFlagList(w io.Writer, flags []*pflag.Flag) {
	for _, flag := range flags {
		name := "--" + flag.Name
		if flag.Value.Type() != "bool" {
			name += " " + flag.Value.Type()
		}
		if flag.Shorthand != "" {
			name = "-" + flag.Shorthand + ", " + name
		}
		fmt.Fprintf(w, "  %-28s %s\n", name, cleanFlagUsage(flag))
	}
}

func cleanFlagUsage(flag *pflag.Flag) string {
	usage := map[string]string{
		"agent":             "JSON + compact + non-interactive mode",
		"json":              "Output JSON",
		"markdown":          "Output Markdown",
		"select":            "Select output fields, e.g. vin,price,miles",
		"config":            "Config file path",
		"make":              "Filter by make",
		"model":             "Filter by model",
		"year":              "Filter by model year",
		"trim":              "Filter by trim",
		"state":             "Filter by dealer state",
		"min-price":         "Minimum listed price",
		"max-price":         "Maximum listed price",
		"min-mileage":       "Minimum odometer mileage",
		"max-mileage":       "Maximum odometer mileage",
		"postal-code":       "Origin ZIP/postal code",
		"radius":            "Maximum distance from origin",
		"limit":             "Number of rows to return",
		"sort":              "Sort order, e.g. price or -price",
		"facets":            "Required facet names to return",
		"facet-value-limit": "Max values per categorical facet",
		"inventory-type":    "Inventory class, e.g. new or used",
		"inventory-status":  "Inventory mode, e.g. active or sold",
		"all":               "Fetch all pages",
	}
	if value, ok := usage[flag.Name]; ok {
		return value
	}
	return flag.Usage
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
      --markdown             Output Markdown
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
