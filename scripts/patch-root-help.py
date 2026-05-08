#!/usr/bin/env python3
"""Reapply Visor curated root help after Printing Press regeneration."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_HELP_GO = '// Copyright 2026 Visor. Licensed under Apache-2.0. See LICENSE.\n\npackage cli\n\nimport (\n\t"fmt"\n\t"io"\n\n\t"github.com/spf13/cobra"\n)\n\nfunc printRootHelp(w io.Writer) {\n\tfmt.Fprint(w, `__     ___\n\\ \\   / (_)___  ___  _ __\n \\ \\ / /| / __|/ _ \\| \'__|\n  \\ V / | \\__ \\ (_) | |\n   \\_/  |_|___/\\___/|_|\n\nVisor CLI — read-only vehicle listings, VIN, dealer, and facet search.\n\nUsage:\n  visor [command]\n\nCore Commands:\n  listings      Search and fetch vehicle listings\n  vins          Look up VIN records\n  dealers       Search and fetch dealers\n  facets        Get listing filter facets\n  doctor        Check auth and connectivity\n  auth          Manage API credentials\n\nAgent Commands:\n  agent-context Emit CLI metadata for agents\n  which         Find the command for a task\n\nOther Commands:\n  completion    Generate shell completion\n  version       Print version\n  help          Help about any command\n\nCommon Flags:\n      --agent          JSON + compact + non-interactive mode\n      --json           Output JSON\n      --select string  Select output fields, e.g. vin,price,miles\n      --config string  Config file path\n  -h, --help           help for visor\n  -v, --version        version for visor\n\nRun "visor help advanced" for advanced flags and local-cache commands.\n`)\n}\n\nfunc newAdvancedHelpCmd(rootCmd *cobra.Command) *cobra.Command {\n\tcmd := &cobra.Command{\n\t\tUse:    "advanced",\n\t\tShort:  "Show advanced commands and flags",\n\t\tHidden: true,\n\t\tRun: func(cmd *cobra.Command, args []string) {\n\t\t\tprintAdvancedHelp(cmd.OutOrStdout(), rootCmd)\n\t\t},\n\t}\n\tcmd.SetHelpFunc(func(cmd *cobra.Command, args []string) {\n\t\tprintAdvancedHelp(cmd.OutOrStdout(), rootCmd)\n\t})\n\treturn cmd\n}\n\nfunc printAdvancedHelp(w io.Writer, rootCmd *cobra.Command) {\n\tfmt.Fprint(w, `Advanced Visor CLI commands and flags.\n\nLocal Cache Commands:\n  sync          Sync API data to local SQLite for offline search\n  search        Full-text search across synced data or live API\n  profile       Named sets of flags saved for reuse\n  workflow      Compound local/archive workflows\n\nDeveloper Commands:\n  api           Browse generated API endpoint metadata\n  feedback      Record local CLI feedback\n  import        Import JSONL records through API write paths\n\nAdvanced Flags:\n      --compact              Return compact JSON fields\n      --csv                  Output CSV\n      --data-source string   auto, live, or local data source\n      --deliver string       Route output to stdout, file:<path>, or webhook:<url>\n      --dry-run              Show request without sending\n      --human-friendly       Enable colored output and rich formatting\n      --idempotent           Treat already-existing create results as a successful no-op\n      --no-cache             Bypass response cache\n      --no-color             Disable colored output\n      --no-input             Disable interactive prompts\n      --plain                Output plain tab-separated text\n      --profile string       Apply values from a saved profile\n      --quiet                Suppress normal output\n      --rate-limit float     Max requests per second\n      --timeout duration     Request timeout\n      --yes                  Skip confirmation prompts\n\nRun "visor <command> --help" for command-specific flags.\n`)\n}\n'


def main() -> None:
    help_path = ROOT / "internal/cli/root_help.go"
    help_path.write_text(ROOT_HELP_GO)

    root_go = ROOT / "internal/cli/root.go"
    text = root_go.read_text()
    text = text.replace(
        'Long: `Manage visor resources via the visor API.\n\nAdd --agent to any command for JSON output + non-interactive mode.\nRun \'visor doctor\' to verify auth and connectivity.`,',
        'Long: `Visor CLI — read-only vehicle listings, VIN, dealer, and facet search.\n\nAdd --agent to any command for JSON output + non-interactive mode.\nRun \'visor doctor\' to verify auth and connectivity.`,',
    )
    hook = '''\tdefaultHelpFunc := rootCmd.HelpFunc()\n\trootCmd.SetHelpFunc(func(cmd *cobra.Command, args []string) {\n\t\tif cmd == rootCmd {\n\t\t\tprintRootHelp(cmd.OutOrStdout())\n\t\t\treturn\n\t\t}\n\t\tdefaultHelpFunc(cmd, args)\n\t})\n'''
    if 'printRootHelp(cmd.OutOrStdout())' not in text:
        text = text.replace('\trootCmd.SetVersionTemplate("visor {{ .Version }}\\n")\n', '\trootCmd.SetVersionTemplate("visor {{ .Version }}\\n")\n' + hook)
    if 'newAdvancedHelpCmd(rootCmd)' not in text:
        text = text.replace('\trootCmd.AddCommand(newVersionCliCmd())\n', '\trootCmd.AddCommand(newVersionCliCmd())\n\trootCmd.AddCommand(newAdvancedHelpCmd(rootCmd))\n')
    root_go.write_text(text)


if __name__ == "__main__":
    main()
