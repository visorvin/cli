#!/usr/bin/env python3
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
auth = root / "internal/cli/auth.go"
helpers = root / "internal/cli/helpers.go"

s = auth.read_text()
for imp in ['"io"', '"strings"']:
    if imp not in s:
        s = s.replace('import (\n\t"fmt"\n', f'import (\n\t"fmt"\n\t{imp}\n', 1)
if '"golang.org/x/term"' not in s:
    s = s.replace('\t"github.com/spf13/cobra"\n', '\t"github.com/spf13/cobra"\n\t"golang.org/x/term"\n', 1)

s = s.replace('fmt.Fprintf(w, "  visor auth set-token <token>\\n")', 'fmt.Fprintf(w, "  visor auth set-token        # secure prompt\\n")\n\t\t\t\tfmt.Fprintf(w, "  printf \'%%s\' \\\"$VISOR_API_KEY\\\" | visor auth set-token --stdin\\n")')

new_block = r'''func newAuthSetTokenCmd(flags *rootFlags) *cobra.Command {
	var readFromStdin bool
	cmd := &cobra.Command{
		Use:   "set-token",
		Short: "Save an API token to the config file",
		Example: `  visor auth set-token
  printf '%s' "$VISOR_API_KEY" | visor auth set-token --stdin`,
		Args: func(cmd *cobra.Command, args []string) error {
			if len(args) == 0 {
				return nil
			}
			return fmt.Errorf("do not pass tokens as command arguments; use 'visor auth set-token' for a secure prompt or pipe the token to 'visor auth set-token --stdin'")
		},
		RunE: func(cmd *cobra.Command, args []string) error {
			token, err := readTokenForSetToken(cmd, readFromStdin)
			if err != nil {
				return err
			}

			cfg, err := config.Load(flags.configPath)
			if err != nil {
				return configErr(err)
			}

			// Clear any legacy auth_header so AuthHeader() falls through to
			// the newly-saved credential. Without this, a pre-existing
			// auth_header value (common after regenerate) shadows the saved
			// token and set-token silently has no effect.
			cfg.AuthHeaderVal = ""
			if err := cfg.SaveTokens("", "", token, "", cfg.TokenExpiry); err != nil {
				return configErr(fmt.Errorf("saving token: %w", err))
			}

			// JSON envelope: {saved, config_path}.
			if flags.asJSON {
				return printJSONFiltered(cmd.OutOrStdout(), map[string]any{
					"saved":       true,
					"config_path": cfg.Path,
				}, flags)
			}
			fmt.Fprintf(cmd.OutOrStdout(), "Token saved to %s\n", cfg.Path)
			return nil
		},
	}
	cmd.Flags().BoolVar(&readFromStdin, "stdin", false, "Read the API token from stdin instead of prompting")
	return cmd
}

func readTokenForSetToken(cmd *cobra.Command, readFromStdin bool) (string, error) {
	if readFromStdin {
		data, err := io.ReadAll(cmd.InOrStdin())
		if err != nil {
			return "", fmt.Errorf("reading token from stdin: %w", err)
		}
		token := strings.TrimSpace(string(data))
		if token == "" {
			return "", fmt.Errorf("no token provided on stdin")
		}
		return token, nil
	}

	if !term.IsTerminal(int(os.Stdin.Fd())) {
		return "", fmt.Errorf("refusing to read token from non-terminal without --stdin; pipe the token to 'visor auth set-token --stdin'")
	}

	fmt.Fprint(cmd.ErrOrStderr(), "Visor API token: ")
	data, err := term.ReadPassword(int(os.Stdin.Fd()))
	fmt.Fprintln(cmd.ErrOrStderr())
	if err != nil {
		return "", fmt.Errorf("reading token: %w", err)
	}
	token := strings.TrimSpace(string(data))
	if token == "" {
		return "", fmt.Errorf("no token provided")
	}
	return token, nil
}

'''
s, n = re.subn(r'func newAuthSetTokenCmd\(flags \*rootFlags\) \*cobra\.Command \{.*?\n\}\n\nfunc newAuthLogoutCmd', lambda _m: new_block + 'func newAuthLogoutCmd', s, flags=re.S)
if n != 1:
    raise SystemExit('could not replace auth set-token block')
auth.write_text(s)

h = helpers.read_text()
http_401 = r'''case strings.Contains(msg, "HTTP 401"):
		return authErr(fmt.Errorf("%w\nhint: check your token. Pipe it with: printf '%%s' \"$VISOR_API_KEY\" | visor auth set-token --stdin"+
			"\n      or: export VISOR_API_KEY=<your-token>"+
			"\n      Run 'visor doctor' to check auth status.", err))
	case strings.Contains(msg, "HTTP 403"):'''
h, n = re.subn(r'case strings\.Contains\(msg, "HTTP 401"\):.*?\n\tcase strings\.Contains\(msg, "HTTP 403"\):', lambda _m: http_401, h, flags=re.S)
if n != 1:
    h = h.replace('Set it with: visor auth set-token <token>', 'Pipe it with: printf \'%%s\' \\"$VISOR_API_KEY\\" | visor auth set-token --stdin')
    h = h.replace('Set it with: visor auth set-token --stdin', 'Pipe it with: printf \'%%s\' \\"$VISOR_API_KEY\\" | visor auth set-token --stdin')
helpers.write_text(h)
