#!/usr/bin/env python3
"""Reapply Visor agent-output fixes after Printing Press regeneration."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPERS_BLOCK = '// filterFields keeps only the specified fields (comma-separated) from JSON objects/arrays.\n// Supports dotted paths like "events.shortName" to descend into nested structures.\n// Arrays are traversed element-wise: "events.shortName" keeps shortName on each event.\nfunc filterFields(data json.RawMessage, fields string) json.RawMessage {\n\tfiltered, err := filterFieldsValidated(data, fields)\n\tif err != nil {\n\t\treturn filterFieldsRec(data, parseSelectPaths(fields))\n\t}\n\treturn filtered\n}\n\nfunc filterFieldsValidated(data json.RawMessage, fields string) (json.RawMessage, error) {\n\tpaths := parseSelectPaths(fields)\n\tif len(paths) == 0 {\n\t\treturn data, nil\n\t}\n\tinvalid := make([]string, 0)\n\tfor _, p := range paths {\n\t\tif !selectPathExists(data, p) {\n\t\t\tinvalid = append(invalid, strings.Join(p, "."))\n\t\t}\n\t}\n\tif len(invalid) > 0 {\n\t\tvalid := validSelectPaths(data, 80)\n\t\tmsg := fmt.Sprintf("unknown selected field(s): %s", strings.Join(invalid, ", "))\n\t\tif len(valid) > 0 {\n\t\t\tmsg += "; valid fields include: " + strings.Join(valid, ", ")\n\t\t}\n\t\treturn nil, usageErr(fmt.Errorf(msg))\n\t}\n\treturn filterFieldsRec(data, paths), nil\n}\n\nfunc parseSelectPaths(fields string) [][]string {\n\tvar paths [][]string\n\tfor _, f := range strings.Split(fields, ",") {\n\t\tf = strings.TrimSpace(f)\n\t\tif f == "" {\n\t\t\tcontinue\n\t\t}\n\t\tparts := strings.Split(f, ".")\n\t\tfor i := range parts {\n\t\t\tparts[i] = strings.ToLower(strings.TrimSpace(parts[i]))\n\t\t}\n\t\tpaths = append(paths, parts)\n\t}\n\treturn paths\n}\n\nfunc selectPathExists(data json.RawMessage, path []string) bool {\n\tif len(path) == 0 {\n\t\treturn true\n\t}\n\tvar arr []json.RawMessage\n\tif err := json.Unmarshal(data, &arr); err == nil {\n\t\tif len(arr) == 0 {\n\t\t\treturn true\n\t\t}\n\t\tfor _, el := range arr {\n\t\t\tif selectPathExists(el, path) {\n\t\t\t\treturn true\n\t\t\t}\n\t\t}\n\t\treturn false\n\t}\n\tvar obj map[string]json.RawMessage\n\tif err := json.Unmarshal(data, &obj); err != nil {\n\t\treturn false\n\t}\n\tfor k, v := range obj {\n\t\tif selectSegmentMatches(k, path[0]) {\n\t\t\treturn selectPathExists(v, path[1:])\n\t\t}\n\t}\n\treturn false\n}\n\nfunc validSelectPaths(data json.RawMessage, limit int) []string {\n\tseen := map[string]bool{}\n\tvar out []string\n\tvar walk func(json.RawMessage, []string)\n\twalk = func(raw json.RawMessage, prefix []string) {\n\t\tif len(out) >= limit {\n\t\t\treturn\n\t\t}\n\t\tvar arr []json.RawMessage\n\t\tif err := json.Unmarshal(raw, &arr); err == nil {\n\t\t\tif len(arr) > 0 {\n\t\t\t\twalk(arr[0], prefix)\n\t\t\t}\n\t\t\treturn\n\t\t}\n\t\tvar obj map[string]json.RawMessage\n\t\tif err := json.Unmarshal(raw, &obj); err == nil {\n\t\t\tkeys := make([]string, 0, len(obj))\n\t\t\tfor k := range obj {\n\t\t\t\tkeys = append(keys, k)\n\t\t\t}\n\t\t\tsort.Strings(keys)\n\t\t\tfor _, k := range keys {\n\t\t\t\tif len(out) >= limit {\n\t\t\t\t\treturn\n\t\t\t\t}\n\t\t\t\tp := append(append([]string{}, prefix...), k)\n\t\t\t\tvar childObj map[string]json.RawMessage\n\t\t\t\tvar childArr []json.RawMessage\n\t\t\t\tif err := json.Unmarshal(obj[k], &childObj); err == nil {\n\t\t\t\t\twalk(obj[k], p)\n\t\t\t\t\tcontinue\n\t\t\t\t}\n\t\t\t\tif err := json.Unmarshal(obj[k], &childArr); err == nil && len(childArr) > 0 {\n\t\t\t\t\twalk(childArr[0], p)\n\t\t\t\t\tcontinue\n\t\t\t\t}\n\t\t\t\tpath := strings.Join(p, ".")\n\t\t\t\tif !seen[path] {\n\t\t\t\t\tseen[path] = true\n\t\t\t\t\tout = append(out, path)\n\t\t\t\t}\n\t\t\t}\n\t\t}\n\t}\n\twalk(data, nil)\n\treturn out\n}\n\n// filterFieldsRec applies path filters to a JSON value. Each path is a list of\n// lowercase segments; arrays descend element-wise.\nfunc filterFieldsRec(data json.RawMessage, paths [][]string) json.RawMessage {\n\tvar arr []json.RawMessage\n\tif err := json.Unmarshal(data, &arr); err == nil {\n\t\tout := make([]json.RawMessage, len(arr))\n\t\tfor i, el := range arr {\n\t\t\tout[i] = filterFieldsRec(el, paths)\n\t\t}\n\t\tresult, _ := json.Marshal(out)\n\t\treturn result\n\t}\n\n\tvar obj map[string]json.RawMessage\n\tif err := json.Unmarshal(data, &obj); err == nil {\n\t\tkeepWhole := map[string]bool{}\n\t\tsubPaths := map[string][][]string{}\n\t\tfor _, p := range paths {\n\t\t\tif len(p) == 0 {\n\t\t\t\tcontinue\n\t\t\t}\n\t\t\thead := p[0]\n\t\t\tif len(p) == 1 {\n\t\t\t\tkeepWhole[head] = true\n\t\t\t} else {\n\t\t\t\tsubPaths[head] = append(subPaths[head], p[1:])\n\t\t\t}\n\t\t}\n\t\tfiltered := map[string]json.RawMessage{}\n\t\tfor k, v := range obj {\n\t\t\tmatched := matchSelectSegment(k, keepWhole, subPaths)\n\t\t\tif matched == "" {\n\t\t\t\tcontinue\n\t\t\t}\n\t\t\tif keepWhole[matched] {\n\t\t\t\tfiltered[k] = v\n\t\t\t\tcontinue\n\t\t\t}\n\t\t\tif subs := subPaths[matched]; subs != nil {\n\t\t\t\tfiltered[k] = filterFieldsRec(v, subs)\n\t\t\t}\n\t\t}\n\t\tresult, _ := json.Marshal(filtered)\n\t\treturn result\n\t}\n\n\treturn data\n}\n\n// matchSelectSegment returns the matching lowercase segment, or "" if no match.\n// Supports direct case-insensitive match and camelCase→kebab-case conversion.\nfunc matchSelectSegment(fieldName string, keepWhole map[string]bool, subPaths map[string][][]string) string {\n\tfor candidate := range keepWhole {\n\t\tif selectSegmentMatches(fieldName, candidate) {\n\t\t\treturn candidate\n\t\t}\n\t}\n\tfor candidate := range subPaths {\n\t\tif selectSegmentMatches(fieldName, candidate) {\n\t\t\treturn candidate\n\t\t}\n\t}\n\treturn ""\n}\n\nfunc selectSegmentMatches(fieldName, requested string) bool {\n\tlower := strings.ToLower(fieldName)\n\tif requested == lower {\n\t\treturn true\n\t}\n\tkebab := camelToKebab(fieldName)\n\tif requested == kebab {\n\t\treturn true\n\t}\n\tsnake := strings.ReplaceAll(kebab, "-", "_")\n\treturn requested == snake\n}\n\n// camelToKebab converts "orderDate" or "orderdate" to "order-date" by splitting on\n// uppercase boundaries. For already-lowercase input, splits on known word boundaries.\nfunc camelToKebab(s string) string {\n\tvar b strings.Builder\n\trunes := []rune(s)\n\tfor i, r := range runes {\n\t\tif i > 0 && unicode.IsUpper(r) && unicode.IsLower(runes[i-1]) {\n\t\t\tb.WriteByte(\'-\')\n\t\t}\n\t\tb.WriteRune(unicode.ToLower(r))\n\t}\n\treturn b.String()\n}\n\n// printOutputWithFlags routes output through the right format based on flags.\nfunc printOutputWithFlags(w io.Writer, data json.RawMessage, flags *rootFlags) error {\n\t// --select wins over --compact when both are set: an explicit field list\n\t// is the user\'s authoritative request, so compacting must not strip those\n\t// fields before --select can pick them.\n\tif flags.selectFields != "" {\n\t\tfiltered, err := filterFieldsValidated(data, flags.selectFields)\n\t\tif err != nil {\n\t\t\treturn err\n\t\t}\n\t\tdata = filtered\n\t} else if flags.compact {\n\t\tdata = compactFields(data)\n\t}\n\t// --quiet: suppress all output, exit code communicates result\n\tif flags.quiet {\n\t\treturn nil\n\t}\n\t// --csv: render as CSV\n\tif flags.csv {\n\t\treturn printCSV(w, data)\n\t}\n\treturn printOutput(w, data, flags.asJSON)\n}\n\n// extractResponseData unwraps common API response envelopes for display.\n// Many APIs return {"status":"success","data":[...]} instead of a bare array.\n// This extracts the inner data for output helpers (filterFields, compactFields,\n// printAutoTable) that expect arrays or flat objects.\n//\n// Only unwraps when a "status" field is present and indicates success — this\n// avoids false positives on APIs where "data" is a regular field (e.g., Stripe\n// returns {"data":[...],"has_more":true} where "data" is the list, not an\n// envelope wrapper).\nfunc extractResponseData(data json.RawMessage) json.RawMessage {\n\tvar envelope struct {\n\t\tStatus string          `json:"status"`\n\t\tData   json.RawMessage `json:"data"`\n\t}\n\tif err := json.Unmarshal(data, &envelope); err != nil {\n\t\treturn data\n\t}\n\tif envelope.Data == nil || envelope.Status == "" {\n\t\treturn data // No status field = not an envelope, might be regular "data" field\n\t}\n\tswitch envelope.Status {\n\tcase "success", "ok", "OK", "Success":\n\t\treturn envelope.Data\n\tdefault:\n\t\treturn data\n\t}\n}\n\n// compactFields keeps only the most important fields for agent consumption.\n// For arrays: allowlist of high-gravity fields (no descriptions/photos).\n// For single objects: blocklist that strips known-verbose fields.\nfunc compactFields(data json.RawMessage) json.RawMessage {\n\tvar obj map[string]any\n\tif err := json.Unmarshal(data, &obj); err == nil {\n\t\tif results, ok := obj["results"]; ok {\n\t\t\tif raw, err := json.Marshal(results); err == nil {\n\t\t\t\tobj["results"] = rawJSONToAny(compactFields(json.RawMessage(raw)))\n\t\t\t}\n\t\t\tresult, _ := json.Marshal(obj)\n\t\t\treturn result\n\t\t}\n\t\tif dataVal, ok := obj["data"]; ok {\n\t\t\tif raw, err := json.Marshal(dataVal); err == nil {\n\t\t\t\tobj["data"] = rawJSONToAny(compactFields(json.RawMessage(raw)))\n\t\t\t}\n\t\t\tresult, _ := json.Marshal(compactObjectMap(obj))\n\t\t\treturn result\n\t\t}\n\t\treturn compactObjectFields(obj)\n\t}\n\n\tvar items []map[string]any\n\tif err := json.Unmarshal(data, &items); err == nil {\n\t\treturn compactListFields(items)\n\t}\n\n\treturn data\n}\n\nfunc rawJSONToAny(raw json.RawMessage) any {\n\tvar v any\n\tif err := json.Unmarshal(raw, &v); err != nil {\n\t\treturn string(raw)\n\t}\n\treturn v\n}\n\n// compactListFields keeps high-gravity fields for array responses, including\n// Visor listing fields agents need to rank and cite vehicles.\nfunc compactListFields(items []map[string]any) json.RawMessage {\n\tkeepFields := map[string]bool{\n\t\t"id": true, "name": true, "title": true, "identifier": true,\n\t\t"status": true, "state": true, "type": true, "priority": true,\n\t\t"url": true, "email": true, "key": true,\n\t\t"created_at": true, "updated_at": true, "createdAt": true, "updatedAt": true,\n\t\t"listing_id": true, "vin": true, "year": true, "make": true, "model": true,\n\t\t"trim": true, "version": true, "price": true, "msrp": true, "miles": true,\n\t\t"dealer_id": true, "dealer_name": true, "city": true, "postal_code": true,\n\t\t"inventory_type": true, "inventory_status": true, "vdp_url": true,\n\t\t"days_on_market": true, "distance": true, "exterior_color": true,\n\t\t"interior_color": true,\n\t}\n\n\tfiltered := make([]map[string]any, 0, len(items))\n\tfor _, item := range items {\n\t\tcompact := map[string]any{}\n\t\tfor k, v := range item {\n\t\t\tif keepFields[k] {\n\t\t\t\tcompact[k] = v\n\t\t\t}\n\t\t}\n\t\tfiltered = append(filtered, compact)\n\t}\n\tresult, _ := json.Marshal(filtered)\n\treturn result\n}\n\n// compactObjectFields strips known-verbose fields from single-object responses.\n// Uses a blocklist so it works across all API domains.\nfunc compactObjectFields(obj map[string]any) json.RawMessage {\n\tresult, _ := json.Marshal(compactObjectMap(obj))\n\treturn result\n}\n\nfunc compactObjectMap(obj map[string]any) map[string]any {\n\tstripFields := map[string]bool{\n\t\t"description": true, "body": true, "content": true,\n\t\t"comments": true, "attachments": true, "html": true, "markdown": true,\n\t\t"photo_urls": true, "photos": true, "images": true,\n\t}\n\n\tcompact := map[string]any{}\n\tfor k, v := range obj {\n\t\tif !stripFields[k] {\n\t\t\tcompact[k] = v\n\t\t}\n\t}\n\treturn compact\n}\n\n'


def replace_between(path: Path, start_marker: str, end_marker: str, replacement: str) -> None:
    text = path.read_text()
    start = text.index(start_marker)
    end = text.index(end_marker, start)
    path.write_text(text[:start] + replacement + text[end:])


def patch_helpers() -> None:
    replace_between(
        ROOT / "internal/cli/helpers.go",
        "// filterFields keeps only the specified fields",
        "// printCSV renders JSON arrays as CSV with header row.",
        HELPERS_BLOCK,
    )


def patch_endpoint_branches() -> None:
    old = """			// For JSON output, wrap with provenance envelope before passing through flags.
			// --select wins over --compact when both are set; --compact only runs when
			// no explicit fields were requested.
			if flags.asJSON || !isTerminal(cmd.OutOrStdout()) {
				filtered := data
				if flags.selectFields != "" {
					filtered = filterFields(filtered, flags.selectFields)
				} else if flags.compact {
					filtered = compactFields(filtered)
				}
				wrapped, wrapErr := wrapWithProvenance(filtered, prov)
				if wrapErr != nil {
					return wrapErr
				}
				return printOutput(cmd.OutOrStdout(), wrapped, true)
			}
"""
    new = """			// For JSON output, wrap with provenance first so --select paths match
			// the documented envelope shape, e.g. results.data.vin.
			if flags.asJSON || !isTerminal(cmd.OutOrStdout()) {
				wrapped, wrapErr := wrapWithProvenance(data, prov)
				if wrapErr != nil {
					return wrapErr
				}
				return printOutputWithFlags(cmd.OutOrStdout(), wrapped, flags)
			}
"""
    for path in (ROOT / "internal/cli").glob("*.go"):
        text = path.read_text()
        if old in text:
            path.write_text(text.replace(old, new))


def patch_doctor() -> None:
    path = ROOT / "internal/cli/doctor.go"
    text = path.read_text()
    old_auth = """			// Check auth
			if cfg != nil {
				header := cfg.AuthHeader()
				if header == "" {
					report["auth"] = "not configured"
					report["auth_hint"] = "export VISOR_API_KEY=<your-key>"
				} else {
					report["auth"] = "configured"
					report["auth_source"] = cfg.AuthSource
				}
			}
"""
    new_auth = """			// Check auth
			authConfigured := false
			authSource := ""
			if cfg != nil {
				header := cfg.AuthHeader()
				if header == "" {
					report["auth"] = "not configured"
					report["auth_hint"] = "export VISOR_API_KEY=<your-key>"
				} else {
					authConfigured = true
					authSource = cfg.AuthSource
					report["auth"] = "configured"
					report["auth_source"] = cfg.AuthSource
				}
			}
"""
    old_env = """			switch {
			case len(authEnvRequiredMissing) > 0:
				report["env_vars"] = "ERROR missing required: " + strings.Join(authEnvRequiredMissing, ", ")
			case len(authEnvOptionalNames) > 1 && !authEnvOptionalSatisfied:
"""
    new_env = """			switch {
			case len(authEnvRequiredMissing) > 0 && authConfigured:
				if authSource == "" {
					authSource = "configured credentials"
				}
				report["env_vars"] = "INFO VISOR_API_KEY not set; using " + authSource
			case len(authEnvRequiredMissing) > 0:
				report["env_vars"] = "ERROR missing required: " + strings.Join(authEnvRequiredMissing, ", ")
			case len(authEnvOptionalNames) > 1 && !authEnvOptionalSatisfied:
"""
    if old_auth in text:
        text = text.replace(old_auth, new_auth)
    if old_env in text:
        text = text.replace(old_env, new_env)
    path.write_text(text)


def main() -> None:
    patch_helpers()
    patch_endpoint_branches()
    patch_doctor()


if __name__ == "__main__":
    main()
