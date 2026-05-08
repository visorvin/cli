---
name: visor
description: "Use the Visor CLI to query vehicle listings, facets, VIN detail, dealers, and dealer inventory. Trigger phrases: `search Visor listings`, `look up a VIN in Visor`, `get Visor facets`, `find Visor dealers`, `use Visor`, `run Visor`."
allowed-tools: "Bash"
---

# Visor CLI

Use `visor` for read-only access to the Visor Public API.

## Required Setup

Verify the binary and credentials before using API commands:

```bash
visor --version
visor doctor
```

Set `VISOR_API_KEY` in the environment or store it with:

```bash
printf '%s' "$VISOR_API_KEY" | visor auth set-token --stdin
```

## Commands

- `visor listings list` — search listing summaries.
- `visor listings get <listing_id>` — fetch listing detail.
- `visor facets` — fetch facet buckets and stats for listing filters.
- `visor vins <vin>` — fetch VIN detail.
- `visor dealers list` — search dealer summaries.
- `visor dealers get <dealer_id>` — fetch dealer detail.
- `visor dealers listings list <dealer_id>` — list inventory for a dealer.

## Agent Patterns

Use `--agent` for compact, automation-safe JSON. For listings, compact output keeps useful row fields and excludes `photo_urls`.

```bash
visor listings list --make ford --model mustang --max-price 20000 --limit 10 --agent

visor listings list --make ford --model mustang --max-price 20000 --limit 10 --agent \
  --select id,vin,year,price,miles,vdp_url

visor facets --make ford --model f-150 --facets year,trim,fuel_type --json \
  --select results.data.facets,results.data.stats

visor dealers list --state TX --make toyota --limit 10 --json \
  --select results.data.dealer_id,results.data.name,results.data.city,results.data.state

visor vins 3TMAZ5CN0PM207381 --json \
  --select results.data.vin,results.data.status,results.data.latest_listing.price,results.data.build
```

Responses use a provenance envelope. For standard list responses, `--select` accepts row-relative fields such as `id,vin,price,miles`; full paths under `results.data` also work. Listing fields use `miles` and `vdp_url`; guessed fields such as `mileage` or `url` return a validation error with valid field paths.

## Do Not Use For

Do not use this CLI for create, update, delete, purchase, booking, messaging, or any remote mutation. This CLI is read-only.
