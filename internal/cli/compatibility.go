// Copyright 2026 visor. Licensed under Apache-2.0. See LICENSE.

package cli

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/visorvin/cli/internal/client"
)

const (
	compatibilityPath      = "/cli/compatibility"
	githubLatestReleaseURL = "https://api.github.com/repos/visorvin/cli/releases/latest"
	defaultUpdateURL       = "https://github.com/visorvin/cli/releases/latest"
	defaultUpdateCommand   = `BIN_DIR="$HOME/.local/bin" sh -c 'curl -fsSL https://raw.githubusercontent.com/visorvin/cli/main/install.sh | sh'`
)

type cliCompatibilityResponse struct {
	SchemaVersion           string  `json:"schema_version,omitempty"`
	Client                  string  `json:"client,omitempty"`
	Status                  string  `json:"status,omitempty"`
	InstalledVersion        string  `json:"installed_version,omitempty"`
	VersionRecognized       bool    `json:"version_recognized"`
	MinimumSupportedVersion *string `json:"minimum_supported_version,omitempty"`
	ReasonCode              *string `json:"reason_code,omitempty"`
	Message                 *string `json:"message,omitempty"`
	UpdateURL               string  `json:"update_url,omitempty"`
	UpdateCommand           string  `json:"update_command,omitempty"`
}

type releaseFreshnessReport struct {
	Status           string `json:"status"`
	InstalledVersion string `json:"installed_version"`
	LatestVersion    string `json:"latest_version,omitempty"`
	ReleaseURL       string `json:"release_url,omitempty"`
	Error            string `json:"error,omitempty"`
}

var fetchLatestCLIRelease = fetchLatestCLIReleaseFromGitHub

func checkCLICompatibility(ctx context.Context, c *client.Client) (cliCompatibilityResponse, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, strings.TrimRight(c.BaseURL, "/")+compatibilityPath, nil)
	if err != nil {
		return cliCompatibilityResponse{}, err
	}
	for k, v := range c.Telemetry {
		if v != "" {
			req.Header.Set(k, v)
		}
	}
	if c.UserAgent != "" {
		req.Header.Set("User-Agent", c.UserAgent)
	}

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return cliCompatibilityResponse{}, err
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if err != nil {
		return cliCompatibilityResponse{}, err
	}
	if resp.StatusCode >= 400 {
		return cliCompatibilityResponse{}, fmt.Errorf("HTTP %d: %s", resp.StatusCode, truncate(string(body), 300))
	}
	var out cliCompatibilityResponse
	if err := json.Unmarshal(body, &out); err != nil {
		return cliCompatibilityResponse{}, fmt.Errorf("malformed response: %w", err)
	}
	if out.Status != "supported" && out.Status != "unsupported" {
		return cliCompatibilityResponse{}, fmt.Errorf("malformed response: unknown status %q", out.Status)
	}
	if out.InstalledVersion == "" {
		out.InstalledVersion = version
	}
	if out.UpdateURL == "" {
		out.UpdateURL = defaultUpdateURL
	}
	if out.UpdateCommand == "" {
		out.UpdateCommand = defaultUpdateCommand
	}
	return out, nil
}

func fetchLatestCLIReleaseFromGitHub(ctx context.Context, httpClient *http.Client) (string, string, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, githubLatestReleaseURL, nil)
	if err != nil {
		return "", "", err
	}
	req.Header.Set("Accept", "application/vnd.github+json")
	req.Header.Set("User-Agent", "visor-cli/"+version)
	resp, err := httpClient.Do(req)
	if err != nil {
		return "", "", err
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	if err != nil {
		return "", "", err
	}
	if resp.StatusCode >= 400 {
		return "", "", fmt.Errorf("HTTP %d: %s", resp.StatusCode, truncate(string(body), 300))
	}
	var release struct {
		TagName string `json:"tag_name"`
		Name    string `json:"name"`
		HTMLURL string `json:"html_url"`
	}
	if err := json.Unmarshal(body, &release); err != nil {
		return "", "", fmt.Errorf("malformed response: %w", err)
	}
	latest := release.TagName
	if latest == "" {
		latest = release.Name
	}
	latest = normalizeVersion(latest)
	if latest == "" {
		return "", "", fmt.Errorf("malformed response: missing release version")
	}
	if release.HTMLURL == "" {
		release.HTMLURL = defaultUpdateURL
	}
	return latest, release.HTMLURL, nil
}

func checkReleaseFreshness(ctx context.Context, httpClient *http.Client, installed string) releaseFreshnessReport {
	report := releaseFreshnessReport{
		Status:           "unknown",
		InstalledVersion: installed,
		ReleaseURL:       defaultUpdateURL,
	}
	latest, url, err := fetchLatestCLIRelease(ctx, httpClient)
	if err != nil {
		report.Error = err.Error()
		return report
	}
	report.LatestVersion = latest
	report.ReleaseURL = url
	cmp, ok := compareVersions(installed, latest)
	if !ok {
		report.Error = fmt.Sprintf("could not compare installed version %q with latest version %q", installed, latest)
		return report
	}
	if cmp < 0 {
		report.Status = "outdated"
	} else {
		report.Status = "current"
	}
	return report
}

func normalizeVersion(v string) string {
	v = strings.TrimSpace(v)
	v = strings.TrimPrefix(v, "visor ")
	v = strings.TrimPrefix(v, "v")
	if i := strings.IndexAny(v, " \t\r\n"); i >= 0 {
		v = v[:i]
	}
	if i := strings.IndexAny(v, "+-"); i >= 0 {
		v = v[:i]
	}
	return v
}

// compareVersions compares dotted numeric versions. It returns -1 when a < b,
// 0 when equal, 1 when a > b, and ok=false when either side is not numeric.
func compareVersions(a, b string) (int, bool) {
	ap := strings.Split(normalizeVersion(a), ".")
	bp := strings.Split(normalizeVersion(b), ".")
	if len(ap) == 0 || len(bp) == 0 || ap[0] == "" || bp[0] == "" {
		return 0, false
	}
	max := len(ap)
	if len(bp) > max {
		max = len(bp)
	}
	for i := 0; i < max; i++ {
		ai, bi := 0, 0
		var err error
		if i < len(ap) {
			ai, err = strconv.Atoi(ap[i])
			if err != nil {
				return 0, false
			}
		}
		if i < len(bp) {
			bi, err = strconv.Atoi(bp[i])
			if err != nil {
				return 0, false
			}
		}
		switch {
		case ai < bi:
			return -1, true
		case ai > bi:
			return 1, true
		}
	}
	return 0, true
}

func compatibilityDetailsMap(resp cliCompatibilityResponse) map[string]any {
	out := map[string]any{
		"schema_version":     resp.SchemaVersion,
		"client":             resp.Client,
		"status":             resp.Status,
		"installed_version":  resp.InstalledVersion,
		"version_recognized": resp.VersionRecognized,
		"update_url":         resp.UpdateURL,
		"update_command":     resp.UpdateCommand,
	}
	if resp.MinimumSupportedVersion != nil {
		out["minimum_supported_version"] = *resp.MinimumSupportedVersion
	} else {
		out["minimum_supported_version"] = nil
	}
	if resp.ReasonCode != nil {
		out["reason_code"] = *resp.ReasonCode
	} else {
		out["reason_code"] = nil
	}
	if resp.Message != nil {
		out["message"] = *resp.Message
	} else {
		out["message"] = nil
	}
	return out
}

func renderUnsupportedCompatibility(w io.Writer, details map[string]any) {
	for _, key := range []string{"message", "installed_version", "minimum_supported_version", "reason_code", "update_command"} {
		v, ok := details[key]
		if !ok || v == nil || fmt.Sprintf("%v", v) == "" {
			continue
		}
		fmt.Fprintf(w, "    %s: %v\n", key, v)
	}
}

func renderOutdatedFreshness(w io.Writer, report releaseFreshnessReport) {
	if report.LatestVersion == "" {
		return
	}
	fmt.Fprintf(w, "    installed_version: %s\n", report.InstalledVersion)
	fmt.Fprintf(w, "    latest_version: %s\n", report.LatestVersion)
	fmt.Fprintf(w, "    update_url: %s\n", report.ReleaseURL)
	fmt.Fprintf(w, "    update_command: %s\n", defaultUpdateCommand)
}

func compatibilityFromAPIErrorBody(body string) (cliCompatibilityResponse, bool) {
	var envelope struct {
		Error struct {
			Code                    string  `json:"code"`
			Message                 string  `json:"message"`
			InstalledVersion        string  `json:"installed_version"`
			MinimumSupportedVersion *string `json:"minimum_supported_version"`
			ReasonCode              *string `json:"reason_code"`
			UpdateURL               string  `json:"update_url"`
			UpdateCommand           string  `json:"update_command"`
		} `json:"error"`
		Code                    string  `json:"code"`
		Message                 string  `json:"message"`
		InstalledVersion        string  `json:"installed_version"`
		MinimumSupportedVersion *string `json:"minimum_supported_version"`
		ReasonCode              *string `json:"reason_code"`
		UpdateURL               string  `json:"update_url"`
		UpdateCommand           string  `json:"update_command"`
	}
	if err := json.Unmarshal([]byte(body), &envelope); err != nil {
		return cliCompatibilityResponse{}, false
	}
	code := envelope.Error.Code
	if code == "" {
		code = envelope.Code
	}
	if code != "unsupported_cli_version" {
		return cliCompatibilityResponse{}, false
	}
	message := envelope.Error.Message
	if message == "" {
		message = envelope.Message
	}
	reason := envelope.Error.ReasonCode
	if reason == nil {
		reason = envelope.ReasonCode
	}
	minimum := envelope.Error.MinimumSupportedVersion
	if minimum == nil {
		minimum = envelope.MinimumSupportedVersion
	}
	updateURL := envelope.Error.UpdateURL
	if updateURL == "" {
		updateURL = envelope.UpdateURL
	}
	if updateURL == "" {
		updateURL = defaultUpdateURL
	}
	updateCommand := envelope.Error.UpdateCommand
	if updateCommand == "" {
		updateCommand = envelope.UpdateCommand
	}
	if updateCommand == "" {
		updateCommand = defaultUpdateCommand
	}
	installed := envelope.Error.InstalledVersion
	if installed == "" {
		installed = envelope.InstalledVersion
	}
	if installed == "" {
		installed = version
	}
	var messagePtr *string
	if message != "" {
		messagePtr = &message
	}
	return cliCompatibilityResponse{
		Status:                  "unsupported",
		InstalledVersion:        installed,
		MinimumSupportedVersion: minimum,
		ReasonCode:              reason,
		Message:                 messagePtr,
		UpdateURL:               updateURL,
		UpdateCommand:           updateCommand,
	}, true
}

func formatUnsupportedCLIError(details cliCompatibilityResponse) string {
	lines := []string{"unsupported CLI version"}
	if details.Message != nil && *details.Message != "" {
		lines[0] = *details.Message
	}
	lines = append(lines, "installed_version: "+details.InstalledVersion)
	if details.MinimumSupportedVersion != nil && *details.MinimumSupportedVersion != "" {
		lines = append(lines, "minimum_supported_version: "+*details.MinimumSupportedVersion)
	}
	if details.ReasonCode != nil && *details.ReasonCode != "" {
		lines = append(lines, "reason_code: "+*details.ReasonCode)
	}
	lines = append(lines, "update_command: "+details.UpdateCommand)
	return strings.Join(lines, "\n")
}

func githubReleaseHTTPClient() *http.Client {
	return &http.Client{Timeout: 5 * time.Second}
}
