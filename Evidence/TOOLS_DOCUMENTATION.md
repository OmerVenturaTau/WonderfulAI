# Wonderful Pharmacy Agent – Tool Documentation

This document summarizes the available backend tools/functions exposed to the agent. Each section covers purpose, inputs, output schema, error handling, and fallback behavior. The code also knows how to handle generic fallbacks, like connection problems etc...
It will tell the user a problem occurred (the tools will show it in red and as an exception).

## get_medication_by_name
- **Purpose**: Fetch detailed medication info by brand/generic name or active ingredient; performs fuzzy matching for typos.
- **Inputs**: `name` (string, required) – brand, generic, or active ingredient (any language).
- **Output**:  
  - `found` (bool)  
  - If `found=true`: `med` (object) with `med_id` (string), `brand_name` (string), `generic_name` (string), `active_ingredients` (list[string]), `form` (string), `strength` (string), `rx_required` (bool), `standard_directions` (string), `warnings` (list[string]), `contraindications` (list[string]), `source` (string).  
  - If ambiguous: `ambiguous` (bool), `candidates` (list[{`med_id`, `brand`, `generic`}]).  
  - If fuzzy only: `ambiguous` (bool), `fuzzy` (bool), `input_name` (string), `candidates` (list[{`med_id`, `brand`, `generic`, `score`(float)}]).  
  - If not found: `candidates` (list[string]) of nearby active-ingredient matches, `input_name` (string).  
  - Possible `error` (string) on unexpected empty result.
- **Errors**: Returns structured objects; no exceptions. Unexpected edge returns `{"found": false, "error": "Unexpected empty result"}`.
- **Fallbacks**: Fuzzy search via pg_trgm; if unavailable or no rows, returns empty candidates. Falls back to active-ingredient substring search to suggest alternatives.

## list_medications
- **Purpose**: List or search medications; efficient alternative to multiple `get_medication_by_name` calls.
- **Inputs**: `search_term` (string, optional), `limit` (int, optional, default 20).
- **Output**: `count` (int), `medications` (list[{`med_id`, `brand_name`, `generic_name`, `active_ingredients`, `form`, `strength`, `rx_required`(bool)}]).
- **Errors**: None; returns empty list when no results.
- **Fallbacks**: If no `search_term`, lists all up to `limit`.

## search_users
- **Purpose**: Find users for downstream prescription flows.
- **Inputs**: Any of `name` (string), `email` (string), `phone` (string), `user_id` (string); at least one required.
- **Output**: `count` (int), `users` (list[{`user_id`, `full_name`, `phone`, `email`, `preferred_language`}]).
- **Errors**: If no inputs, returns `{"error": "At least one search parameter (name, email, phone, or user_id) must be provided"}`.
- **Fallbacks**: None beyond returning zero matches.

## check_stock_availability
- **Purpose**: Check inventory for a medication at a specific store.
- **Inputs**: `med_id` (string, required), `store_id` (string, required).
- **Output**: `med_id` (string), `store_id` (string), `quantity` (int), `status` ("in_stock" | "out_of_stock"), `last_updated` (timestamp).
- **Errors**: If no inventory row, returns `{"error": "NOT_FOUND", "med_id": ..., "store_id": ...}`.
- **Fallbacks**: None. I believe the answers are enough to handle all scenarios.

## list_user_prescriptions
- **Purpose**: List all prescriptions for a user.
- **Inputs**: `user_id` (string, required).
- **Output**: `user_id` (string), `prescriptions` (list[{`prescription_id`, `med_id`, `med_name`, `directions`, `refills_remaining`, `expires_at`, `rx_required`(bool)}]).
- **Errors**: None; empty list when no prescriptions.
- **Fallbacks**: None. The code handle problems that are not included in the above scenarios, and the above cover all scenarios.

## query_medications_flexible
- **Purpose**: Multi-filter medication search.
- **Inputs** (all optional): `brand_name` (string), `generic_name` (string), `active_ingredient` (string), `form` (string), `strength` (string), `rx_required` (bool), `limit` (int, default 20).
- **Output**: `count` (int), `medications` (list with same fields as `list_medications` plus `rx_required` as bool).
- **Errors**: None.
- **Fallbacks**: With no filters, returns all medications up to `limit`.

## query_medications_with_stock
- **Purpose**: Combined medication search plus inventory across stores in one call.
- **Inputs** (all optional): `search_term` (string), `active_ingredient` (string), `form` (string), `rx_required` (bool), `store_ids` (list[string]), `in_stock_only` (bool, default false), `limit` (int, default 20).
- **Output**: `count` (int), `medications` (list[{`med_id`, `brand_name`, `generic_name`, `active_ingredients`, `form`, `strength`, `rx_required`(bool), `stock` (list[{`store_id`, `quantity`, `status`}])}]).
- **Errors**: None.
- **Fallbacks**: If no inventory for a med, `stock` is empty; if no `store_ids`, checks all stores.

## query_stock_multiple_stores
- **Purpose**: Stock lookup for a medication across multiple stores.
- **Inputs**: `med_id` (string, optional), `med_name` (string, optional), `store_ids` (list[string], optional), `in_stock_only` (bool, optional). At least `med_id` or `med_name` required.
- **Output**: `med_id` (string), `med_name` (string|null), `count` (int), `stock` (list[{`store_id`, `store_name`, `city`, `quantity`, `status`, `last_updated`}]).
- **Errors**:  
  - Missing identifier: `{"error": "MISSING_PARAMETER", "message": "Either med_id or med_name must be provided"}`.  
  - Unknown med_name: `{"error": "MEDICATION_NOT_FOUND", "med_name": ..., "message": "Medication not found in catalog"}`.
- **Fallbacks**: If `med_name` is provided, resolves to `med_id` via `get_medication_by_name`. If no stock rows, still returns `med_name` via medications table when available.

## list_stores
- **Purpose**: List store locations and IDs.
- **Inputs**: `city` (string, optional).
- **Output**: `count` (int), `stores` (list[{`store_id`, `name`, `city`}]).
- **Errors**: None.
- **Fallbacks**: Without `city`, lists all stores.

## query_prescriptions_flexible
- **Purpose**: Multi-filter prescription search (by user, med, expiration, refills).
- **Inputs** (all optional): `user_id` (string), `med_id` (string), `med_name` (string), `expiring_soon_days` (int), `has_refills` (bool), `limit` (int, default 50).
- **Output**: `count` (int), `prescriptions` (list[{`prescription_id`, `user_id`, `med_id`, `med_name`, `directions`, `refills_remaining`, `expires_at`, `status`("expired"|"no_refills"|"active"), `rx_required`(bool)}]).
- **Errors**: If `med_name` is provided but not found: `{"error": "MEDICATION_NOT_FOUND", "med_name": ..., "message": "Medication not found in catalog"}`.
- **Fallbacks**: `med_name` is resolved to `med_id` via `get_medication_by_name`; with no filters, returns all prescriptions up to `limit`.

## request_prescription_refill
- **Purpose**: Submit a refill request and decrement refills.
- **Inputs**: `user_id` (string, required), `prescription_id` (string, required).
- **Output** (success): `accepted` (bool true), `refill_request_id` (string), `status` ("submitted"), `eta_hours` (int).
- **Errors** (all return `accepted=false`): `NOT_FOUND`, `UNAUTHORIZED`, `NO_REFILLS`, `EXPIRED`.
- **Fallbacks**: Uses timestamp-based IDs to avoid collisions; no retries beyond error codes.

## get_tool_stats (analytics helper)
- **Purpose**: Return aggregated tool call counts from `tool_stats`.
- **Inputs**: None.
- **Output**: List of objects `{tool_name` (string), `call_count` (int)}`.
- **Errors**: None surfaced; relies on DB rows.
- **Fallbacks**: None.

## run_tool (dispatcher)
- **Purpose**: Map tool name to implementation, increment usage metrics, and execute with safe argument validation.
- **Inputs**: `name` (string), `args` (object for target tool).
- **Output**: Underlying tool response; on failure may return `{"error": "UNKNOWN_TOOL"|"MISSING_REQUIRED_ARGUMENT", ...}`.
- **Errors**:  
  - Unknown tool name → `UNKNOWN_TOOL`.  
  - Missing required args → `MISSING_REQUIRED_ARGUMENT` with message.  
  - Analytics increment errors are swallowed after logging.
- **Fallbacks**: Best-effort `_increment_tool_stat` (errors swallowed); otherwise delegates directly to tool functions.

