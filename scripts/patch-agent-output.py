#!/usr/bin/env python3
"""Reapply Visor agent-output fixes after Printing Press regeneration."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPERS_BLOCK = '// filterFields keeps only the specified fields (comma-separated) from JSON objects/arrays.\n// Supports dotted paths like "events.shortName" to descend into nested structures.\n// Arrays are traversed element-wise: "events.shortName" keeps shortName on each event.\nfunc filterFields(data json.RawMessage, fields string) json.RawMessage {\n\tfiltered, err := filterFieldsValidated(data, fields)\n\tif err != nil {\n\t\treturn filterFieldsRec(data, parseSelectPaths(fields))\n\t}\n\treturn filtered\n}\n\nfunc filterFieldsValidated(data json.RawMessage, fields string) (json.RawMessage, error) {\n\tpaths := expandRowRelativeSelectPaths(data, parseSelectPaths(fields))\n\tif len(paths) == 0 {\n\t\treturn data, nil\n\t}\n\tinvalid := make([]string, 0)\n\tfor _, p := range paths {\n\t\tif !selectPathExists(data, p) {\n\t\t\tinvalid = append(invalid, strings.Join(p, "."))\n\t\t}\n\t}\n\tif len(invalid) > 0 {\n\t\tvalid := validSelectPaths(data, 80)\n\t\tmsg := fmt.Sprintf("unknown selected field(s): %s", strings.Join(invalid, ", "))\n\t\tif len(valid) > 0 {\n\t\t\tmsg += "; valid fields include: " + strings.Join(valid, ", ")\n\t\t}\n\t\treturn nil, usageErr(fmt.Errorf(msg))\n\t}\n\treturn filterFieldsRec(data, paths), nil\n}\n\nfunc expandRowRelativeSelectPaths(data json.RawMessage, paths [][]string) [][]string {\n\tif len(paths) == 0 || !selectPathExists(data, []string{"results", "data"}) {\n\t\treturn paths\n\t}\n\texpanded := make([][]string, 0, len(paths))\n\tfor _, p := range paths {\n\t\tif len(p) == 0 || selectPathExists(data, p) {\n\t\t\texpanded = append(expanded, p)\n\t\t\tcontinue\n\t\t}\n\t\tcandidate := append([]string{"results", "data"}, p...)\n\t\tif selectPathExists(data, candidate) {\n\t\t\texpanded = append(expanded, candidate)\n\t\t\tcontinue\n\t\t}\n\t\texpanded = append(expanded, p)\n\t}\n\treturn expanded\n}\n\nfunc parseSelectPaths(fields string) [][]string {\n\tvar paths [][]string\n\tfor _, f := range strings.Split(fields, ",") {\n\t\tf = strings.TrimSpace(f)\n\t\tif f == "" {\n\t\t\tcontinue\n\t\t}\n\t\tparts := strings.Split(f, ".")\n\t\tfor i := range parts {\n\t\t\tparts[i] = strings.ToLower(strings.TrimSpace(parts[i]))\n\t\t}\n\t\tpaths = append(paths, parts)\n\t}\n\treturn paths\n}\n\nfunc selectPathExists(data json.RawMessage, path []string) bool {\n\tif len(path) == 0 {\n\t\treturn true\n\t}\n\tvar arr []json.RawMessage\n\tif err := json.Unmarshal(data, &arr); err == nil {\n\t\tif len(arr) == 0 {\n\t\t\treturn true\n\t\t}\n\t\tfor _, el := range arr {\n\t\t\tif selectPathExists(el, path) {\n\t\t\t\treturn true\n\t\t\t}\n\t\t}\n\t\treturn false\n\t}\n\tvar obj map[string]json.RawMessage\n\tif err := json.Unmarshal(data, &obj); err != nil {\n\t\treturn false\n\t}\n\tfor k, v := range obj {\n\t\tif selectSegmentMatches(k, path[0]) {\n\t\t\treturn selectPathExists(v, path[1:])\n\t\t}\n\t}\n\treturn false\n}\n\nfunc validSelectPaths(data json.RawMessage, limit int) []string {\n\tseen := map[string]bool{}\n\tvar out []string\n\tvar walk func(json.RawMessage, []string)\n\twalk = func(raw json.RawMessage, prefix []string) {\n\t\tif len(out) >= limit {\n\t\t\treturn\n\t\t}\n\t\tvar arr []json.RawMessage\n\t\tif err := json.Unmarshal(raw, &arr); err == nil {\n\t\t\tif len(arr) > 0 {\n\t\t\t\twalk(arr[0], prefix)\n\t\t\t}\n\t\t\treturn\n\t\t}\n\t\tvar obj map[string]json.RawMessage\n\t\tif err := json.Unmarshal(raw, &obj); err == nil {\n\t\t\tkeys := make([]string, 0, len(obj))\n\t\t\tfor k := range obj {\n\t\t\t\tkeys = append(keys, k)\n\t\t\t}\n\t\t\tsort.Strings(keys)\n\t\t\tfor _, k := range keys {\n\t\t\t\tif len(out) >= limit {\n\t\t\t\t\treturn\n\t\t\t\t}\n\t\t\t\tp := append(append([]string{}, prefix...), k)\n\t\t\t\tvar childObj map[string]json.RawMessage\n\t\t\t\tvar childArr []json.RawMessage\n\t\t\t\tif err := json.Unmarshal(obj[k], &childObj); err == nil {\n\t\t\t\t\twalk(obj[k], p)\n\t\t\t\t\tcontinue\n\t\t\t\t}\n\t\t\t\tif err := json.Unmarshal(obj[k], &childArr); err == nil && len(childArr) > 0 {\n\t\t\t\t\twalk(childArr[0], p)\n\t\t\t\t\tcontinue\n\t\t\t\t}\n\t\t\t\tpath := strings.Join(p, ".")\n\t\t\t\tif !seen[path] {\n\t\t\t\t\tseen[path] = true\n\t\t\t\t\tout = append(out, path)\n\t\t\t\t}\n\t\t\t}\n\t\t}\n\t}\n\twalk(data, nil)\n\treturn out\n}\n\n// filterFieldsRec applies path filters to a JSON value. Each path is a list of\n// lowercase segments; arrays descend element-wise.\nfunc filterFieldsRec(data json.RawMessage, paths [][]string) json.RawMessage {\n\tvar arr []json.RawMessage\n\tif err := json.Unmarshal(data, &arr); err == nil {\n\t\tout := make([]json.RawMessage, len(arr))\n\t\tfor i, el := range arr {\n\t\t\tout[i] = filterFieldsRec(el, paths)\n\t\t}\n\t\tresult, _ := json.Marshal(out)\n\t\treturn result\n\t}\n\n\tvar obj map[string]json.RawMessage\n\tif err := json.Unmarshal(data, &obj); err == nil {\n\t\tkeepWhole := map[string]bool{}\n\t\tsubPaths := map[string][][]string{}\n\t\tfor _, p := range paths {\n\t\t\tif len(p) == 0 {\n\t\t\t\tcontinue\n\t\t\t}\n\t\t\thead := p[0]\n\t\t\tif len(p) == 1 {\n\t\t\t\tkeepWhole[head] = true\n\t\t\t} else {\n\t\t\t\tsubPaths[head] = append(subPaths[head], p[1:])\n\t\t\t}\n\t\t}\n\t\tfiltered := map[string]json.RawMessage{}\n\t\tfor k, v := range obj {\n\t\t\tmatched := matchSelectSegment(k, keepWhole, subPaths)\n\t\t\tif matched == "" {\n\t\t\t\tcontinue\n\t\t\t}\n\t\t\tif keepWhole[matched] {\n\t\t\t\tfiltered[k] = v\n\t\t\t\tcontinue\n\t\t\t}\n\t\t\tif subs := subPaths[matched]; subs != nil {\n\t\t\t\tfiltered[k] = filterFieldsRec(v, subs)\n\t\t\t}\n\t\t}\n\t\tresult, _ := json.Marshal(filtered)\n\t\treturn result\n\t}\n\n\treturn data\n}\n\n// matchSelectSegment returns the matching lowercase segment, or "" if no match.\n// Supports direct case-insensitive match and camelCase→kebab-case conversion.\nfunc matchSelectSegment(fieldName string, keepWhole map[string]bool, subPaths map[string][][]string) string {\n\tfor candidate := range keepWhole {\n\t\tif selectSegmentMatches(fieldName, candidate) {\n\t\t\treturn candidate\n\t\t}\n\t}\n\tfor candidate := range subPaths {\n\t\tif selectSegmentMatches(fieldName, candidate) {\n\t\t\treturn candidate\n\t\t}\n\t}\n\treturn ""\n}\n\nfunc selectSegmentMatches(fieldName, requested string) bool {\n\tlower := strings.ToLower(fieldName)\n\tif requested == lower {\n\t\treturn true\n\t}\n\tkebab := camelToKebab(fieldName)\n\tif requested == kebab {\n\t\treturn true\n\t}\n\tsnake := strings.ReplaceAll(kebab, "-", "_")\n\treturn requested == snake\n}\n\n// camelToKebab converts "orderDate" or "orderdate" to "order-date" by splitting on\n// uppercase boundaries. For already-lowercase input, splits on known word boundaries.\nfunc camelToKebab(s string) string {\n\tvar b strings.Builder\n\trunes := []rune(s)\n\tfor i, r := range runes {\n\t\tif i > 0 && unicode.IsUpper(r) && unicode.IsLower(runes[i-1]) {\n\t\t\tb.WriteByte(\'-\')\n\t\t}\n\t\tb.WriteRune(unicode.ToLower(r))\n\t}\n\treturn b.String()\n}\n\n// printOutputWithFlags routes output through the right format based on flags.\nfunc printOutputWithFlags(w io.Writer, data json.RawMessage, flags *rootFlags) error {\n\t// --select wins over --compact when both are set: an explicit field list\n\t// is the user\'s authoritative request, so compacting must not strip those\n\t// fields before --select can pick them.\n\tif flags.selectFields != "" {\n\t\tfiltered, err := filterFieldsValidated(data, flags.selectFields)\n\t\tif err != nil {\n\t\t\treturn err\n\t\t}\n\t\tdata = filtered\n\t} else if flags.compact {\n\t\tdata = compactFields(data)\n\t}\n\t// --quiet: suppress all output, exit code communicates result\n\tif flags.quiet {\n\t\treturn nil\n\t}\n\t// --csv: render as CSV\n\tif flags.csv {\n\t\treturn printCSV(w, data)\n\t}\n\treturn printOutput(w, data, flags.asJSON)\n}\n\n// extractResponseData unwraps common API response envelopes for display.\n// Many APIs return {"status":"success","data":[...]} instead of a bare array.\n// This extracts the inner data for output helpers (filterFields, compactFields,\n// printAutoTable) that expect arrays or flat objects.\n//\n// Only unwraps when a "status" field is present and indicates success — this\n// avoids false positives on APIs where "data" is a regular field (e.g., Stripe\n// returns {"data":[...],"has_more":true} where "data" is the list, not an\n// envelope wrapper).\nfunc extractResponseData(data json.RawMessage) json.RawMessage {\n\tvar envelope struct {\n\t\tStatus string          `json:"status"`\n\t\tData   json.RawMessage `json:"data"`\n\t}\n\tif err := json.Unmarshal(data, &envelope); err != nil {\n\t\treturn data\n\t}\n\tif envelope.Data == nil || envelope.Status == "" {\n\t\treturn data // No status field = not an envelope, might be regular "data" field\n\t}\n\tswitch envelope.Status {\n\tcase "success", "ok", "OK", "Success":\n\t\treturn envelope.Data\n\tdefault:\n\t\treturn data\n\t}\n}\n\n// compactFields keeps only the most important fields for agent consumption.\n// For arrays: allowlist of high-gravity fields (no descriptions/photos).\n// For single objects: blocklist that strips known-verbose fields.\nfunc compactFields(data json.RawMessage) json.RawMessage {\n\tvar obj map[string]any\n\tif err := json.Unmarshal(data, &obj); err == nil {\n\t\tif results, ok := obj["results"]; ok {\n\t\t\tif raw, err := json.Marshal(results); err == nil {\n\t\t\t\tobj["results"] = rawJSONToAny(compactFields(json.RawMessage(raw)))\n\t\t\t}\n\t\t\tresult, _ := json.Marshal(obj)\n\t\t\treturn result\n\t\t}\n\t\tif dataVal, ok := obj["data"]; ok {\n\t\t\tif raw, err := json.Marshal(dataVal); err == nil {\n\t\t\t\tobj["data"] = rawJSONToAny(compactFields(json.RawMessage(raw)))\n\t\t\t}\n\t\t\tresult, _ := json.Marshal(compactObjectMap(obj))\n\t\t\treturn result\n\t\t}\n\t\treturn compactObjectFields(obj)\n\t}\n\n\tvar items []map[string]any\n\tif err := json.Unmarshal(data, &items); err == nil {\n\t\treturn compactListFields(items)\n\t}\n\n\treturn data\n}\n\nfunc rawJSONToAny(raw json.RawMessage) any {\n\tvar v any\n\tif err := json.Unmarshal(raw, &v); err != nil {\n\t\treturn string(raw)\n\t}\n\treturn v\n}\n\n// compactListFields keeps high-gravity fields for array responses, including\n// Visor listing fields agents need to rank and cite vehicles.\nfunc compactListFields(items []map[string]any) json.RawMessage {\n\tkeepFields := map[string]bool{\n\t\t"id": true, "name": true, "title": true, "identifier": true,\n\t\t"status": true, "state": true, "type": true, "priority": true,\n\t\t"url": true, "email": true, "key": true,\n\t\t"created_at": true, "updated_at": true, "createdAt": true, "updatedAt": true,\n\t\t"listing_id": true, "vin": true, "year": true, "make": true, "model": true,\n\t\t"trim": true, "version": true, "price": true, "msrp": true, "miles": true,\n\t\t"dealer_id": true, "dealer_name": true, "city": true, "postal_code": true,\n\t\t"inventory_type": true, "inventory_status": true, "vdp_url": true,\n\t\t"days_on_market": true, "distance": true, "exterior_color": true,\n\t\t"interior_color": true,\n\t}\n\n\tfiltered := make([]map[string]any, 0, len(items))\n\tfor _, item := range items {\n\t\tcompact := map[string]any{}\n\t\tfor k, v := range item {\n\t\t\tif keepFields[k] {\n\t\t\t\tcompact[k] = v\n\t\t\t}\n\t\t}\n\t\tfiltered = append(filtered, compact)\n\t}\n\tresult, _ := json.Marshal(filtered)\n\treturn result\n}\n\n// compactObjectFields strips known-verbose fields from single-object responses.\n// Uses a blocklist so it works across all API domains.\nfunc compactObjectFields(obj map[string]any) json.RawMessage {\n\tresult, _ := json.Marshal(compactObjectMap(obj))\n\treturn result\n}\n\nfunc compactObjectMap(obj map[string]any) map[string]any {\n\tstripFields := map[string]bool{\n\t\t"description": true, "body": true, "content": true,\n\t\t"comments": true, "attachments": true, "html": true, "markdown": true,\n\t\t"photo_urls": true, "photos": true, "images": true,\n\t}\n\n\tcompact := map[string]any{}\n\tfor k, v := range obj {\n\t\tif !stripFields[k] {\n\t\t\tcompact[k] = v\n\t\t}\n\t}\n\treturn compact\n}\n\n'

HELPERS_BLOCK = HELPERS_BLOCK.replace(
    '\t// --csv: render as CSV\n\tif flags.csv {\n\t\treturn printCSV(w, data)\n\t}\n\treturn printOutput(w, data, flags.asJSON)\n',
    '\t// --csv: render as CSV\n\tif flags.csv {\n\t\treturn printCSV(w, data)\n\t}\n\t// --markdown: render as Markdown for transcript-friendly output\n\tif flags.markdown {\n\t\treturn printMarkdown(w, data)\n\t}\n\treturn printOutput(w, data, flags.asJSON)\n',
)

MARKDOWN_HELPERS = r'''
// printMarkdown renders JSON objects and arrays as Markdown tables.
func printMarkdown(w io.Writer, data json.RawMessage) error {
	if title, items, ok := markdownEnvelopeRows(data); ok {
		if err := printMarkdownHeading(w, title); err != nil {
			return err
		}
		if err := printMarkdownTable(w, items); err != nil {
			return err
		}
		if meta, ok := markdownEnvelopeMeta(data); ok && len(meta) > 0 {
			fmt.Fprintln(w)
			if err := printMarkdownHeading(w, "Meta"); err != nil {
				return err
			}
			return printMarkdownObject(w, meta)
		}
		return nil
	}

	var items []map[string]any
	if err := json.Unmarshal(data, &items); err == nil {
		return printMarkdownTable(w, items)
	}

	var obj map[string]any
	if err := json.Unmarshal(data, &obj); err == nil {
		return printMarkdownObject(w, obj)
	}

	fmt.Fprintln(w, "```")
	fmt.Fprintln(w, string(data))
	fmt.Fprintln(w, "```")
	return nil
}

func markdownEnvelopeRows(data json.RawMessage) (string, []map[string]any, bool) {
	var envelope struct {
		Results struct {
			Data json.RawMessage `json:"data"`
		} `json:"results"`
		Data json.RawMessage `json:"data"`
	}
	if err := json.Unmarshal(data, &envelope); err != nil {
		return "", nil, false
	}
	raw := envelope.Results.Data
	title := "Results"
	if raw == nil {
		raw = envelope.Data
		title = "Data"
	}
	if raw == nil {
		return "", nil, false
	}
	var items []map[string]any
	if err := json.Unmarshal(raw, &items); err != nil {
		return "", nil, false
	}
	return title, items, true
}

func markdownEnvelopeMeta(data json.RawMessage) (map[string]any, bool) {
	var envelope struct {
		Meta map[string]any `json:"meta"`
	}
	if err := json.Unmarshal(data, &envelope); err != nil || envelope.Meta == nil {
		return nil, false
	}
	return envelope.Meta, true
}

func printMarkdownHeading(w io.Writer, title string) error {
	_, err := fmt.Fprintf(w, "## %s\n\n", title)
	return err
}

func printMarkdownTable(w io.Writer, items []map[string]any) error {
	if len(items) == 0 {
		_, err := fmt.Fprintln(w, "_No results._")
		return err
	}
	headers := markdownHeaders(items)
	fmt.Fprintf(w, "| %s |\n", strings.Join(headers, " | "))
	separators := make([]string, len(headers))
	for i := range separators {
		separators[i] = "---"
	}
	fmt.Fprintf(w, "| %s |\n", strings.Join(separators, " | "))
	for _, item := range items {
		row := make([]string, len(headers))
		for i, h := range headers {
			row[i] = escapeMarkdownTableCell(formatCellValue(item[h]))
		}
		fmt.Fprintf(w, "| %s |\n", strings.Join(row, " | "))
	}
	return nil
}

func printMarkdownObject(w io.Writer, obj map[string]any) error {
	if len(obj) == 0 {
		_, err := fmt.Fprintln(w, "_No fields._")
		return err
	}
	headers := prioritizeAllHeaders(obj)
	fmt.Fprintln(w, "| Field | Value |")
	fmt.Fprintln(w, "| --- | --- |")
	for _, h := range headers {
		fmt.Fprintf(w, "| %s | %s |\n", escapeMarkdownTableCell(h), escapeMarkdownTableCell(formatCellValue(obj[h])))
	}
	return nil
}

func markdownHeaders(items []map[string]any) []string {
	seen := map[string]bool{}
	headers := make([]string, 0)
	preferred := []string{
		"id", "listing_id", "vin", "year", "make", "model", "trim", "version",
		"price", "msrp", "miles", "dealer_id", "dealer_name", "city", "state",
		"postal_code", "inventory_type", "inventory_status", "vdp_url",
		"days_on_market", "distance", "exterior_color", "interior_color",
		"name", "title", "status", "type", "url", "created_at", "updated_at",
	}
	for _, h := range preferred {
		for _, item := range items {
			if _, ok := item[h]; ok && !seen[h] {
				seen[h] = true
				headers = append(headers, h)
				break
			}
		}
	}
	extra := make([]string, 0)
	for _, item := range items {
		for h := range item {
			if !seen[h] {
				seen[h] = true
				extra = append(extra, h)
			}
		}
	}
	sort.Strings(extra)
	headers = append(headers, extra...)
	return headers
}

func escapeMarkdownTableCell(s string) string {
	s = strings.ReplaceAll(s, "\\", "\\\\")
	s = strings.ReplaceAll(s, "|", "\\|")
	s = strings.ReplaceAll(s, "\r\n", "<br>")
	s = strings.ReplaceAll(s, "\n", "<br>")
	return s
}

'''

MARKDOWN_HELPERS = (ROOT / "scripts/markdown_helpers.go.txt").read_text()


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
    path = ROOT / "internal/cli/helpers.go"
    text = path.read_text()
    if "type markdownEnvelope struct" in text:
        start = text.index("type markdownEnvelope struct")
        end = text.index("// printOutput auto-detects arrays", start)
        text = text[:start] + MARKDOWN_HELPERS + text[end:]
    elif "func printMarkdown(" not in text:
        text = text.replace(
            "// printOutput auto-detects arrays and renders as tables, or prints raw JSON for objects.\n",
            MARKDOWN_HELPERS + "// printOutput auto-detects arrays and renders as tables, or prints raw JSON for objects.\n",
        )
    text = text.replace(
        "// - --json/--csv/--compact/--agent: machine format → JSON",
        "// - --json/--csv/--markdown/--compact/--agent: explicit output format",
    )
    text = text.replace(
        "if flags.asJSON || flags.csv || flags.compact || flags.quiet || flags.plain {",
        "if flags.asJSON || flags.csv || flags.markdown || flags.compact || flags.quiet || flags.plain {",
    )
    if '`json:"query,omitempty"`' not in text:
        text = text.replace(
            '\tFreshness    any        `json:"freshness,omitempty"`     // optional machine-owned freshness metadata for covered command paths\n',
            '\tFreshness    any        `json:"freshness,omitempty"`     // optional machine-owned freshness metadata for covered command paths\n\tQuery        any        `json:"query,omitempty"`         // cleaned request query params for agent envelopes\n',
        )
    text = text.replace(
        """	if prov.Freshness != nil {
		meta["freshness"] = prov.Freshness
	}
	var results any = json.RawMessage(data)
""",
        """	if prov.Freshness != nil {
		meta["freshness"] = prov.Freshness
	}
	if prov.Query != nil {
		meta["query"] = prov.Query
	}
	var results any = json.RawMessage(data)
""",
    )
    text = text.replace(
        'if len(paths) == 0 || !selectPathExists(data, []string{"results", "data"}) {',
        'if len(paths) == 0 || (!selectPathExists(data, []string{"results", "data"}) && !selectPathExists(data, []string{"data"})) {',
    )
    text = text.replace(
        """		candidate := append([]string{"results", "data"}, p...)
		if selectPathExists(data, candidate) {
			expanded = append(expanded, candidate)
			continue
		}
		expanded = append(expanded, p)
""",
        """		candidate := append([]string{"results", "data"}, p...)
		if selectPathExists(data, candidate) {
			expanded = append(expanded, candidate)
			continue
		}
		candidate = append([]string{"data"}, p...)
		if selectPathExists(data, candidate) {
			expanded = append(expanded, candidate)
			continue
		}
		expanded = append(expanded, p)
""",
    )
    text = text.replace(
        """// printOutputWithFlags routes output through the right format based on flags.
func printOutputWithFlags(w io.Writer, data json.RawMessage, flags *rootFlags) error {
	// --select wins over --compact when both are set: an explicit field list
	// is the user's authoritative request, so compacting must not strip those
	// fields before --select can pick them.
	if flags.selectFields != "" {
		filtered, err := filterFieldsValidated(data, flags.selectFields)
		if err != nil {
			return err
		}
		data = filtered
	} else if flags.compact {
		data = compactFields(data)
	}
	// --quiet: suppress all output, exit code communicates result
	if flags.quiet {
		return nil
	}
	// --csv: render as CSV
	if flags.csv {
		return printCSV(w, data)
	}
	// --markdown: render as Markdown for transcript-friendly output
	if flags.markdown {
		return printMarkdown(w, data)
	}
	return printOutput(w, data, flags.asJSON)
}
""",
        """// printOutputWithFlags routes output through the right format based on flags.
func printOutputWithFlags(w io.Writer, data json.RawMessage, flags *rootFlags) error {
	if flags != nil && flags.agent {
		data = agentEnvelope(data)
	}
	// --select wins over --compact when both are set: an explicit field list
	// is the user's authoritative request, so compacting must not strip those
	// fields before --select can pick them.
	if flags != nil && flags.selectFields != "" {
		filtered, err := filterFieldsForOutput(data, flags.selectFields, flags)
		if err != nil {
			return err
		}
		data = filtered
	} else if flags != nil && flags.compact {
		data = compactFields(data)
	}
	// --quiet: suppress all output, exit code communicates result
	if flags != nil && flags.quiet {
		return nil
	}
	// --csv: render as CSV
	if flags != nil && flags.csv {
		return printCSV(w, data)
	}
	// --markdown: render as Markdown for transcript-friendly output
	if flags != nil && flags.markdown {
		return printMarkdown(w, data)
	}
	return printOutput(w, data, flags != nil && flags.asJSON)
}

func filterFieldsForOutput(data json.RawMessage, fields string, flags *rootFlags) (json.RawMessage, error) {
	if flags != nil && flags.agent {
		return filterAgentDataFields(data, fields)
	}
	return filterFieldsValidated(data, fields)
}

func filterAgentDataFields(data json.RawMessage, fields string) (json.RawMessage, error) {
	var obj map[string]json.RawMessage
	if json.Unmarshal(data, &obj) != nil {
		return filterFieldsValidated(data, fields)
	}
	dataRaw, ok := obj["data"]
	if !ok {
		return filterFieldsValidated(data, fields)
	}
	filtered, err := filterFieldsValidated(dataRaw, agentDataSelectFields(fields))
	if err != nil {
		return nil, err
	}
	obj["data"] = filtered
	return json.Marshal(obj)
}

func agentDataSelectFields(fields string) string {
	paths := parseSelectPaths(fields)
	out := make([]string, 0, len(paths))
	for _, p := range paths {
		if len(p) >= 2 && p[0] == "data" {
			p = p[1:]
		}
		if len(p) >= 3 && p[0] == "results" && p[1] == "data" {
			p = p[2:]
		}
		if len(p) == 0 {
			continue
		}
		out = append(out, strings.Join(p, "."))
	}
	return strings.Join(out, ",")
}

func agentEnvelope(data json.RawMessage) json.RawMessage {
	var obj map[string]json.RawMessage
	if json.Unmarshal(data, &obj) != nil {
		out, _ := json.Marshal(map[string]any{
			"data":            rawJSONToAny(data),
			"pagination":      map[string]any{},
			"query":           map[string]any{},
			"warnings":        []any{},
			"facets_used":     []any{},
			"total_available": nil,
		})
		return out
	}

	payload := data
	if results, ok := obj["results"]; ok {
		payload = results
	}
	payloadObj := map[string]json.RawMessage{}
	_ = json.Unmarshal(payload, &payloadObj)

	rows := payload
	if nestedData, ok := payloadObj["data"]; ok {
		rows = nestedData
	}
	pagination := json.RawMessage(`{}`)
	if raw, ok := payloadObj["pagination"]; ok {
		pagination = raw
	} else if raw, ok := payloadObj["meta"]; ok {
		pagination = raw
	}
	totalAvailable := any(nil)
	if pmap := map[string]json.RawMessage{}; json.Unmarshal(pagination, &pmap) == nil {
		if n, ok := intFromJSONFields(pmap, "total_available", "total", "total_count", "count"); ok {
			totalAvailable = n
		}
	}
	if totalAvailable == nil {
		var arr []json.RawMessage
		if json.Unmarshal(rows, &arr) == nil {
			totalAvailable = len(arr)
		}
	}

	envelope := map[string]any{
		"data":            rawJSONToAny(rows),
		"pagination":      rawJSONToAny(pagination),
		"query":           map[string]any{},
		"warnings":        []any{},
		"facets_used":     []any{},
		"total_available": totalAvailable,
	}
	if meta, ok := obj["meta"]; ok {
		metaAny := rawJSONToAny(meta)
		envelope["meta"] = metaAny
		if metaObj, ok := metaAny.(map[string]any); ok {
			if query, ok := metaObj["query"]; ok {
				envelope["query"] = query
				envelope["facets_used"] = facetsUsedFromQuery(query)
			}
		}
	}
	result, _ := json.Marshal(envelope)
	return result
}

func facetsUsedFromQuery(query any) []string {
	queryObj, ok := query.(map[string]any)
	if !ok {
		return []string{}
	}
	raw, ok := queryObj["facets"]
	if !ok {
		return []string{}
	}
	facets, ok := raw.(string)
	if !ok {
		return []string{}
	}
	out := make([]string, 0)
	for _, facet := range strings.Split(facets, ",") {
		facet = strings.TrimSpace(facet)
		if facet != "" {
			out = append(out, facet)
		}
	}
	return out
}
""",
    )
    path.write_text(text)


def patch_offset_pagination() -> None:
    path = ROOT / "internal/cli/helpers.go"
    text = path.read_text()
    if '"strconv"' not in text:
        text = text.replace('\t"sort"\n', '\t"sort"\n\t"strconv"\n', 1)
    if "itemsBefore := len(allItems)" not in text:
        text = text.replace(
            """				// Try common data fields
				for _, field := range []string{"data", "items", "results", "messages", "members", "values"} {
					if arr, ok := obj[field]; ok {
						var nested []json.RawMessage
						if json.Unmarshal(arr, &nested) == nil {
							allItems = append(allItems, nested...)
							break
						}
					}
				}
""",
        """				itemsBefore := len(allItems)
				// Try common data fields
				for _, field := range []string{"data", "items", "results", "messages", "members", "values"} {
					if arr, ok := obj[field]; ok {
						var nested []json.RawMessage
						if json.Unmarshal(arr, &nested) == nil {
							allItems = append(allItems, nested...)
							break
						}
					}
				}
				itemsAdded := len(allItems) - itemsBefore
""",
            1,
        )
    if "nextOffsetFromEnvelope(obj, clean, itemsAdded)" not in text:
        text = text.replace(
            """				// Check has_more
				if hasMoreField != "" {
					if moreRaw, ok := obj[hasMoreField]; ok {
						var more bool
						if json.Unmarshal(moreRaw, &more) == nil && more {
							continue
						}
					}
				}
""",
        """				// Check has_more
				if hasMoreField != "" {
					if moreRaw, ok := obj[hasMoreField]; ok {
						var more bool
						if json.Unmarshal(moreRaw, &more) == nil && more {
							continue
						}
					}
				}

				if nextOffset, ok := nextOffsetFromEnvelope(obj, clean, itemsAdded); ok {
					clean["offset"] = fmt.Sprintf("%d", nextOffset)
					continue
				}
""",
            1,
        )
    marker = "// printJSONFiltered marshals a Go-typed value through the same output\n"
    if "func nextOffsetFromEnvelope" not in text:
        text = text.replace(
            marker,
            """func nextOffsetFromEnvelope(obj map[string]json.RawMessage, params map[string]string, itemsAdded int) (int, bool) {
	if itemsAdded <= 0 {
		return 0, false
	}
	paginationRaw, ok := obj["pagination"]
	if !ok {
		if metaRaw, hasMeta := obj["meta"]; hasMeta {
			paginationRaw = metaRaw
		}
	}
	if len(paginationRaw) == 0 {
		return 0, false
	}
	var pagination map[string]json.RawMessage
	if json.Unmarshal(paginationRaw, &pagination) != nil {
		return 0, false
	}
	total, hasTotal := intFromJSONFields(pagination, "total", "total_available", "total_count", "count")
	limit, hasLimit := intFromJSONFields(pagination, "limit", "page_size", "per_page")
	offset, hasOffset := intFromJSONFields(pagination, "offset", "skip")
	if !hasOffset {
		offset, _ = atoiDefault(params["offset"], 0)
	}
	if !hasLimit {
		limit, _ = atoiDefault(params["limit"], itemsAdded)
	}
	if limit <= 0 {
		limit = itemsAdded
	}
	next := offset + limit
	if itemsAdded < limit {
		return 0, false
	}
	if hasTotal && next >= total {
		return 0, false
	}
	return next, true
}

func intFromJSONFields(obj map[string]json.RawMessage, names ...string) (int, bool) {
	for _, name := range names {
		raw, ok := obj[name]
		if !ok {
			continue
		}
		var n int
		if json.Unmarshal(raw, &n) == nil {
			return n, true
		}
		var f float64
		if json.Unmarshal(raw, &f) == nil {
			return int(f), true
		}
		var s string
		if json.Unmarshal(raw, &s) == nil {
			if parsed, err := atoiDefault(s, 0); err == nil {
				return parsed, true
			}
		}
	}
	return 0, false
}

func atoiDefault(s string, fallback int) (int, error) {
	if strings.TrimSpace(s) == "" {
		return fallback, nil
	}
	n, err := strconv.Atoi(strings.TrimSpace(s))
	if err != nil {
		return fallback, err
	}
	return n, nil
}

""" + marker,
            1,
        )
    path.write_text(text)


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
			if flags.asJSON || flags.markdown || !isTerminal(cmd.OutOrStdout()) {
				wrapped, wrapErr := wrapWithProvenance(data, prov)
				if wrapErr != nil {
					return wrapErr
				}
				return printOutputWithFlags(cmd.OutOrStdout(), wrapped, flags)
			}
"""
    current_generated = """			// For JSON output, wrap with provenance envelope. --select wins over
			// --compact when both are set; --compact only runs when no explicit
			// fields were requested.
			if flags.asJSON || flags.markdown || !isTerminal(cmd.OutOrStdout()) {
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
				return printOutputWithFlags(cmd.OutOrStdout(), wrapped, flags)
			}
"""
    for path in (ROOT / "internal/cli").glob("*.go"):
        text = path.read_text()
        if old in text:
            text = text.replace(old, new)
        if current_generated in text:
            text = text.replace(current_generated, new)
        text = text.replace(
            "if flags.asJSON || !isTerminal(cmd.OutOrStdout()) {",
            "if flags.asJSON || flags.markdown || !isTerminal(cmd.OutOrStdout()) {",
        )
        text = text.replace(
            "jsonMode := flags.asJSON || !isTerminal(cmd.OutOrStdout())",
            "jsonMode := flags.asJSON || flags.markdown || !isTerminal(cmd.OutOrStdout())",
        )
        text = text.replace(
            "return printOutput(cmd.OutOrStdout(), wrapped, true)",
            "return printOutputWithFlags(cmd.OutOrStdout(), wrapped, flags)",
        )
        path.write_text(text)


def patch_root_help() -> None:
    path = ROOT / "internal/cli/root.go"
    text = path.read_text()
    text = text.replace(
        "Comma-separated fields to include in output (e.g. --select id,name,status)",
        "Comma-separated output fields. List responses accept row fields like vin,price or full paths like results.data.vin",
    )
    path.write_text(text)


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


def patch_data_source() -> None:
    path = ROOT / "internal/cli/data_source.go"
    text = path.read_text()
    if "func attachQuery" not in text:
        text = text.replace(
            """func attachFreshness(prov DataProvenance, flags *rootFlags) DataProvenance {
	if flags != nil {
		prov.Freshness = flags.freshnessMeta
	}
	return prov
}

""",
            """func attachFreshness(prov DataProvenance, flags *rootFlags) DataProvenance {
	if flags != nil {
		prov.Freshness = flags.freshnessMeta
	}
	return prov
}

func attachQuery(prov DataProvenance, params map[string]string) DataProvenance {
	query := cleanQueryParams(params)
	if len(query) > 0 {
		prov.Query = query
	}
	return prov
}

func cleanQueryParams(params map[string]string) map[string]string {
	query := map[string]string{}
	for k, v := range params {
		if v != "" && v != "0" && v != "false" {
			query[k] = v
		}
	}
	return query
}

""",
        )
    text = text.replace("attachFreshness(prov, flags)", "attachFreshness(attachQuery(prov, params), flags)")
    text = text.replace('attachFreshness(DataProvenance{Source: "live"}, flags)', 'attachFreshness(attachQuery(DataProvenance{Source: "live"}, params), flags)')
    text = text.replace("attachFreshness(fallbackProv, flags)", "attachFreshness(attachQuery(fallbackProv, params), flags)")
    path.write_text(text)


def main() -> None:
    patch_helpers()
    patch_offset_pagination()
    patch_endpoint_branches()
    patch_root_help()
    patch_doctor()
    patch_data_source()


if __name__ == "__main__":
    main()
