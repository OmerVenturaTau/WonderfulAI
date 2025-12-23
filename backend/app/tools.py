import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .db import query_all, query_one, exec_sql

logger = logging.getLogger("wonderful.tools")


def _like(q: str) -> str:
    return f"%{q.strip()}%"


def _fuzzy_medication_candidates(name: str) -> List[Dict[str, Any]]:
    """
    Best-effort fuzzy search for medications using PostgreSQL pg_trgm similarity.

    This lets the agent recover from minor typos (e.g., "iburprofen" -> "ibuprofen").
    If the pg_trgm extension or similarity function is unavailable, this quietly
    falls back to an empty list so we don't break the flow.
    """
    try:
        # Attempt fuzzy matching; may fail if pg_trgm extension is missing
        # NOTE: requires: CREATE EXTENSION IF NOT EXISTS pg_trgm;
        rows = query_all(
            """
            SELECT
                med_id,
                brand_name,
                generic_name,
                GREATEST(
                    similarity(LOWER(brand_name), LOWER(%s)),
                    similarity(LOWER(generic_name), LOWER(%s))
                ) AS score
            FROM medications
            WHERE
                similarity(LOWER(brand_name), LOWER(%s)) > 0.3
                OR similarity(LOWER(generic_name), LOWER(%s)) > 0.3
            ORDER BY score DESC
            LIMIT 5
            """,
            (name, name, name, name),
        )
    except Exception as e:
        # If pg_trgm isn't available or any error occurs, just return no fuzzy candidates.
        logger.exception("Fuzzy medication candidate lookup failed for name=%r", name)
        return []

    return [
        {
            "med_id": r["med_id"],
            "brand": r["brand_name"],
            "generic": r["generic_name"],
            "score": float(r.get("score", 0.0)),
        }
        for r in rows
    ]


def get_medication_by_name(name: str) -> Dict[str, Any]:
    """Search medications by brand name, generic name, or active ingredient. Returns English data only."""
    rows = query_all(
        """
        SELECT * FROM medications
        WHERE brand_name ILIKE %s OR generic_name ILIKE %s OR active_ingredients ILIKE %s
        """,
        (_like(name), _like(name), _like(name))
    )

    if not rows:
        # No direct matches found; try fuzzy candidates to recover from typos.
        fuzzy = _fuzzy_medication_candidates(name)
        if fuzzy:
            return {
                "found": False,
                "ambiguous": True,
                "fuzzy": True,
                "input_name": name,
                "candidates": fuzzy,
            }

        # If no fuzzy hits, surface alternatives sharing the active ingredient substring.
        cand = query_all(
            "SELECT brand_name, generic_name FROM medications WHERE active_ingredients LIKE %s",
            (_like(name),)
        )
        return {
            "found": False,
            "candidates": [f"{c['brand_name']} ({c['generic_name']})" for c in cand],
            "input_name": name,
        }

    if len(rows) > 1:
        # Multiple matches → ask caller to disambiguate
        return {
            "found": False,
            "ambiguous": True,
            "candidates": [
                {
                    "med_id": r["med_id"],
                    "brand": r["brand_name"],
                    "generic": r["generic_name"],
                } for r in rows[:5]
            ],
        }

    # At this point, rows should have exactly 1 element (checked above)
    if not rows:
        return {"found": False, "error": "Unexpected empty result"}
    
    r = rows[0]
    # Handle potential None values safely
    active_ingredients = r.get("active_ingredients") or ""
    active_ingredients_list = active_ingredients.split(", ") if active_ingredients else []
    
    return {
        "found": True,
        "med": {
            "med_id": r["med_id"],
            "brand_name": r["brand_name"],
            "generic_name": r["generic_name"],
            "active_ingredients": active_ingredients_list,
            "form": r["form"],
            "strength": r["strength"],
            "rx_required": bool(r["rx_required"]),
            "standard_directions": r.get("standard_directions") or "",
            "warnings": [r.get("warnings")] if r.get("warnings") else [],
            "contraindications": [r.get("contraindications")] if r.get("contraindications") else [],
            "source": "Synthetic internal pharmacy catalog"
        }
    }

def list_medications(search_term: str = None, limit: int = 20) -> Dict[str, Any]:
    """
    List medications from the catalog. If search_term is provided, searches across brand name,
    generic name, and active ingredients. Use this to browse available medications or find
    medications when you're not sure of the exact name. More efficient than calling
    get_medication_by_name multiple times.
    """
    if search_term:
        # Search with fuzzy matching support
        search_pattern = _like(search_term)
        rows = query_all(
            """
            SELECT med_id, brand_name, generic_name, active_ingredients, form, strength, rx_required
            FROM medications
            WHERE brand_name ILIKE %s OR generic_name ILIKE %s OR active_ingredients ILIKE %s
            ORDER BY 
                CASE 
                    WHEN brand_name ILIKE %s THEN 1
                    WHEN generic_name ILIKE %s THEN 2
                    ELSE 3
                END,
                brand_name
            LIMIT %s
            """,
            (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, limit)
        )
    else:
        # List all medications
        rows = query_all(
            """
            SELECT med_id, brand_name, generic_name, active_ingredients, form, strength, rx_required
            FROM medications
            ORDER BY brand_name
            LIMIT %s
            """,
            (limit,)
        )
    
    return {
        "count": len(rows),
        "medications": [
            {
                "med_id": r["med_id"],
                "brand_name": r["brand_name"],
                "generic_name": r["generic_name"],
                "active_ingredients": r["active_ingredients"],
                "form": r["form"],
                "strength": r["strength"],
                "rx_required": bool(r["rx_required"]),
            }
            for r in rows
        ]
    }


def search_users(name: str = None, email: str = None, phone: str = None, user_id: str = None) -> Dict[str, Any]:
    """
    Search for users by name, email, phone, or user_id. At least one parameter must be provided.
    Use this to find a user when you need their user_id for prescription operations.
    """
    conditions = []
    params = []
    
    if user_id:
        conditions.append("user_id = %s")
        params.append(user_id)
    if name:
        conditions.append("full_name ILIKE %s")
        params.append(_like(name))
    if email:
        conditions.append("email ILIKE %s")
        params.append(_like(email))
    if phone:
        conditions.append("phone ILIKE %s")
        params.append(_like(phone))
    
    if not conditions:
        # Guard: require at least one selector
        return {"error": "At least one search parameter (name, email, phone, or user_id) must be provided"}
    
    where_clause = " OR ".join(conditions)
    rows = query_all(
        f"""
        SELECT user_id, full_name, phone, email, preferred_language
        FROM users
        WHERE {where_clause}
        ORDER BY full_name
        LIMIT 10
        """,
        tuple(params)
    )
    
    return {
        "count": len(rows),
        "users": [
            {
                "user_id": r["user_id"],
                "full_name": r["full_name"],
                "phone": r["phone"],
                "email": r["email"],
                "preferred_language": r["preferred_language"],
            }
            for r in rows
        ]
    }


def check_stock_availability(med_id: str, store_id: str) -> Dict[str, Any]:
    row = query_one(
        "SELECT quantity, last_updated FROM inventory WHERE med_id=%s AND store_id=%s",
        (med_id, store_id)
    )
    if not row:
        # No inventory record for this med + store
        return {"error": "NOT_FOUND", "med_id": med_id, "store_id": store_id}

    qty = int(row["quantity"])
    # Derive a simple status flag to avoid re-computing downstream
    status = "in_stock" if qty > 0 else "out_of_stock"
    return {
        "med_id": med_id,
        "store_id": store_id,
        "quantity": qty,
        "status": status,
        "last_updated": row["last_updated"],
    }

def list_user_prescriptions(user_id: str) -> Dict[str, Any]:
    """List all prescriptions for a user. Returns English data only."""
    rows = query_all(
        """
        SELECT p.*, m.brand_name, m.generic_name, m.rx_required
        FROM prescriptions p
        JOIN medications m ON m.med_id = p.med_id
        WHERE p.user_id=%s
        """,
        (user_id,)
    )
    return {
        "user_id": user_id,
        "prescriptions": [
            {
                "prescription_id": r["prescription_id"],
                "med_id": r["med_id"],
                "med_name": f"{r['brand_name']} ({r['generic_name']})",
                "directions": r["directions"],
                "refills_remaining": r["refills_remaining"],
                "expires_at": r["expires_at"],
                "rx_required": bool(r["rx_required"]),
            }
            for r in rows
        ]
    }

def query_medications_flexible(
    brand_name: Optional[str] = None,
    generic_name: Optional[str] = None,
    active_ingredient: Optional[str] = None,
    form: Optional[str] = None,
    strength: Optional[str] = None,
    rx_required: Optional[bool] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Flexible medication query with multiple optional filters.
    All parameters are optional - combine as needed for complex queries.
    Returns medications matching ALL specified criteria.
    """
    conditions = []
    params = []
    
    if brand_name:
        conditions.append("brand_name ILIKE %s")
        params.append(_like(brand_name))
    if generic_name:
        conditions.append("generic_name ILIKE %s")
        params.append(_like(generic_name))
    if active_ingredient:
        conditions.append("active_ingredients ILIKE %s")
        params.append(_like(active_ingredient))
    if form:
        conditions.append("form ILIKE %s")
        params.append(_like(form))
    if strength:
        conditions.append("strength ILIKE %s")
        params.append(_like(strength))
    if rx_required is not None:
        conditions.append("rx_required = %s")
        params.append(1 if rx_required else 0)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    sql = f"""
        SELECT med_id, brand_name, generic_name, active_ingredients, form, strength, rx_required
        FROM medications
        WHERE {where_clause}
        ORDER BY brand_name
        LIMIT %s
    """
    params.append(limit)
    
    rows = query_all(sql, tuple(params))
    
    return {
        "count": len(rows),
        "medications": [
            {
                "med_id": r["med_id"],
                "brand_name": r["brand_name"],
                "generic_name": r["generic_name"],
                "active_ingredients": r["active_ingredients"],
                "form": r["form"],
                "strength": r["strength"],
                "rx_required": bool(r["rx_required"]),
            }
            for r in rows
        ]
    }


def query_medications_with_stock(
    search_term: Optional[str] = None,
    active_ingredient: Optional[str] = None,
    form: Optional[str] = None,
    rx_required: Optional[bool] = None,
    store_ids: Optional[List[str]] = None,
    in_stock_only: bool = False,
    limit: int = 20
) -> Dict[str, Any]:
    """
    Query medications with optional stock filtering across one or more stores.
    Combines medication search with inventory checks in a single efficient query.
    Use this when you need to find medications AND check their availability.
    """
    med_conditions = []
    params = []
    
    if search_term:
        pattern = _like(search_term)
        med_conditions.append(
            "(brand_name ILIKE %s OR generic_name ILIKE %s OR active_ingredients ILIKE %s)"
        )
        params.extend([pattern, pattern, pattern])
    
    if active_ingredient:
        med_conditions.append("m.active_ingredients ILIKE %s")
        params.append(_like(active_ingredient))
    
    if form:
        med_conditions.append("m.form ILIKE %s")
        params.append(_like(form))
    
    if rx_required is not None:
        med_conditions.append("m.rx_required = %s")
        params.append(1 if rx_required else 0)
    
    med_where = " AND ".join(med_conditions) if med_conditions else "1=1"
    
    # Build stock filtering
    if store_ids:
        store_placeholders = ",".join(["%s"] * len(store_ids))
        store_filter = f" AND i.store_id IN ({store_placeholders})"
        params.extend(store_ids)
        if in_stock_only:
            stock_filter = " AND i.quantity > 0"
        else:
            stock_filter = ""
    else:
        store_filter = ""
        stock_filter = ""
    
    sql = f"""
        SELECT DISTINCT
            m.med_id,
            m.brand_name,
            m.generic_name,
            m.active_ingredients,
            m.form,
            m.strength,
            m.rx_required,
            COALESCE(i.store_id, 'N/A') as store_id,
            COALESCE(i.quantity, 0) as quantity,
            CASE WHEN i.quantity > 0 THEN 'in_stock' ELSE 'out_of_stock' END as stock_status
        FROM medications m
        LEFT JOIN inventory i ON m.med_id = i.med_id {store_filter}
        WHERE {med_where} {stock_filter}
        ORDER BY m.brand_name, store_id
        LIMIT %s
    """
    params.append(limit)
    
    rows = query_all(sql, tuple(params))
    
    # Group by medication and aggregate stock info
    meds = {}
    for row in rows:
        med_id = row["med_id"]
        if med_id not in meds:
            meds[med_id] = {
                "med_id": med_id,
                "brand_name": row["brand_name"],
                "generic_name": row["generic_name"],
                "active_ingredients": row["active_ingredients"],
                "form": row["form"],
                "strength": row["strength"],
                "rx_required": bool(row["rx_required"]),
                "stock": []
            }
        if row["store_id"] != "N/A":
            meds[med_id]["stock"].append({
                "store_id": row["store_id"],
                "quantity": row["quantity"],
                "status": row["stock_status"]
            })
    
    return {
        "count": len(meds),
        "medications": list(meds.values())
    }


def query_stock_multiple_stores(
    med_id: Optional[str] = None,
    med_name: Optional[str] = None,
    store_ids: Optional[List[str]] = None,
    in_stock_only: bool = False
) -> Dict[str, Any]:
    """
    Check stock availability for a medication across multiple stores in a single query.
    Can search by med_id or medication name. If store_ids not provided, checks all stores.
    """
    # If med_name provided, first get med_id
    if med_name and not med_id:
        med_result = get_medication_by_name(med_name)
        if not med_result.get("found"):
            # Explicitly signal when the provided name cannot be resolved
            return {
                "error": "MEDICATION_NOT_FOUND",
                "med_name": med_name,
                "message": "Medication not found in catalog"
            }
        med_id = med_result["med"]["med_id"]
    
    if not med_id:
        # Ensure at least one identifier is provided
        return {"error": "MISSING_PARAMETER", "message": "Either med_id or med_name must be provided"}
    
    conditions = ["i.med_id = %s"]
    params = [med_id]
    
    if store_ids:
        store_placeholders = ",".join(["%s"] * len(store_ids))
        conditions.append(f"i.store_id IN ({store_placeholders})")
        params.extend(store_ids)
    
    if in_stock_only:
        conditions.append("i.quantity > 0")
    
    where_clause = " AND ".join(conditions)
    
    sql = f"""
        SELECT 
            i.store_id,
            s.name as store_name,
            s.city,
            i.med_id,
            m.brand_name,
            m.generic_name,
            i.quantity,
            CASE WHEN i.quantity > 0 THEN 'in_stock' ELSE 'out_of_stock' END as status,
            i.last_updated
        FROM inventory i
        JOIN medications m ON i.med_id = m.med_id
        LEFT JOIN stores s ON i.store_id = s.store_id
        WHERE {where_clause}
        ORDER BY s.city, s.name
    """
    
    rows = query_all(sql, tuple(params))
    
    # Get medication name if we have results
    med_name = None
    if rows and len(rows) > 0:
        # Safe to access rows[0] since we checked rows is not empty
        brand = rows[0].get('brand_name', '')
        generic = rows[0].get('generic_name', '')
        if brand and generic:
            med_name = f"{brand} ({generic})"
    
    if not med_name and med_id:
        # If no stock found but med_id exists, get name from medications table
        med_row = query_one("SELECT brand_name, generic_name FROM medications WHERE med_id = %s", (med_id,))
        if med_row:
            med_name = f"{med_row['brand_name']} ({med_row['generic_name']})"
    
    return {
        "med_id": med_id,
        "med_name": med_name,
        "count": len(rows),
        "stock": [
            {
                "store_id": r["store_id"],
                "store_name": r["store_name"],
                "city": r["city"],
                "quantity": r["quantity"],
                "status": r["status"],
                "last_updated": r["last_updated"]
            }
            for r in rows
        ]
    }


def list_stores(city: Optional[str] = None) -> Dict[str, Any]:
    """
    List available pharmacy store locations.
    Use this to find store_ids when customers ask about specific locations.
    """
    if city:
        rows = query_all(
            "SELECT store_id, name, city FROM stores WHERE city ILIKE %s ORDER BY name",
            (_like(city),)
        )
    else:
        rows = query_all(
            "SELECT store_id, name, city FROM stores ORDER BY city, name",
            ()
        )
    
    return {
        "count": len(rows),
        "stores": [
            {
                "store_id": r["store_id"],
                "name": r["name"],
                "city": r["city"]
            }
            for r in rows
        ]
    }


def query_prescriptions_flexible(
    user_id: Optional[str] = None,
    med_id: Optional[str] = None,
    med_name: Optional[str] = None,
    expiring_soon_days: Optional[int] = None,
    has_refills: Optional[bool] = None,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Flexible prescription query with multiple optional filters.
    Can search by user, medication, expiration status, and refill availability.
    """
    conditions = []
    params = []
    
    if user_id:
        conditions.append("p.user_id = %s")
        params.append(user_id)
    
    if med_id:
        conditions.append("p.med_id = %s")
        params.append(med_id)
    elif med_name:
        # First get med_id from name
        med_result = get_medication_by_name(med_name)
        if med_result.get("found"):
            conditions.append("p.med_id = %s")
            params.append(med_result["med"]["med_id"])
        else:
            return {
                "error": "MEDICATION_NOT_FOUND",
                "med_name": med_name,
                "message": "Medication not found in catalog"
            }
    
    if expiring_soon_days is not None:
        # Use MAKE_INTERVAL for proper parameter binding with INTERVAL
        conditions.append("CAST(p.expires_at AS DATE) <= CURRENT_DATE + MAKE_INTERVAL(days => %s)")
        params.append(expiring_soon_days)
        conditions.append("CAST(p.expires_at AS DATE) >= CURRENT_DATE")
    
    if has_refills is not None:
        if has_refills:
            conditions.append("p.refills_remaining > 0")
        else:
            conditions.append("p.refills_remaining <= 0")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    sql = f"""
        SELECT 
            p.prescription_id,
            p.user_id,
            p.med_id,
            m.brand_name,
            m.generic_name,
            m.rx_required,
            p.directions,
            p.refills_remaining,
            p.expires_at,
            CASE 
                WHEN CAST(p.expires_at AS DATE) < CURRENT_DATE THEN 'expired'
                WHEN p.refills_remaining <= 0 THEN 'no_refills'
                ELSE 'active'
            END as status
        FROM prescriptions p
        JOIN medications m ON p.med_id = m.med_id
        WHERE {where_clause}
        ORDER BY CAST(p.expires_at AS DATE), p.user_id
        LIMIT %s
    """
    params.append(limit)
    
    rows = query_all(sql, tuple(params))
    
    return {
        "count": len(rows),
        "prescriptions": [
            {
                "prescription_id": r["prescription_id"],
                "user_id": r["user_id"],
                "med_id": r["med_id"],
                "med_name": f"{r['brand_name']} ({r['generic_name']})",
                "directions": r["directions"],
                "refills_remaining": r["refills_remaining"],
                "expires_at": r["expires_at"],
                "status": r["status"],
                "rx_required": bool(r["rx_required"])
            }
            for r in rows
        ]
    }


def request_prescription_refill(user_id: str, prescription_id: str) -> Dict[str, Any]:
    rx = query_one("SELECT * FROM prescriptions WHERE prescription_id=%s", (prescription_id,))
    if not rx:
        return {"accepted": False, "error": "NOT_FOUND"}

    if rx["user_id"] != user_id:
        return {"accepted": False, "error": "UNAUTHORIZED"}

    if int(rx["refills_remaining"]) <= 0:
        return {"accepted": False, "error": "NO_REFILLS"}

    if rx["expires_at"] < datetime.utcnow().date().isoformat():
        return {"accepted": False, "error": "EXPIRED"}

    # Generate unique refill request ID with timestamp to avoid collisions
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')[:-3]  # Include milliseconds
    rrid = f"RR-{timestamp}-{prescription_id}"
    exec_sql(
        "INSERT INTO refill_requests VALUES (%s,%s,%s,%s,%s)",
        (rrid, prescription_id, user_id, "submitted", datetime.utcnow().isoformat() + "Z")
    )
    exec_sql(
        "UPDATE prescriptions SET refills_remaining = refills_remaining - 1 WHERE prescription_id=%s",
        (prescription_id,)
    )
    return {"accepted": True, "refill_request_id": rrid, "status": "submitted", "eta_hours": 4}


def _increment_tool_stat(tool_name: str) -> None:
    """
    Increment call counter for a tool in the tool_stats table.

    This is best-effort only: failures should not break the main flow.
    """
    try:
        exec_sql(
            """
            INSERT INTO tool_stats (tool_name, call_count)
            VALUES (%s, 1)
            ON CONFLICT (tool_name)
            DO UPDATE SET call_count = tool_stats.call_count + 1
            """,
            (tool_name,),
        )
    except Exception as e:
        # Swallow errors so analytics never impact the user experience,
        # but do log them for observability.
        logger.exception("Failed to increment tool_stats for tool=%r", tool_name)
        return


def get_tool_stats() -> List[Dict[str, Any]]:
    """
    Return aggregated tool usage statistics.

    Shape:
      [
        {"tool_name": "get_medication_by_name", "call_count": 42},
        ...
      ]
    """
    rows = query_all(
        "SELECT tool_name, call_count FROM tool_stats ORDER BY call_count DESC",
        (),
    )
    return [{"tool_name": r["tool_name"], "call_count": int(r["call_count"])} for r in rows]

TOOL_SPECS = [
    {
        "type": "function",
        "name": "get_medication_by_name",
        "description": "Fetch detailed medication information from the pharmacy catalog by brand/generic name or active ingredient. This tool automatically performs fuzzy matching to handle typos and misspellings (e.g., 'iburprofen' will find 'ibuprofen'). If no exact match is found, it will suggest similar medications. Use this when you need full details about a specific medication. Returns data in English. CRITICAL: Only medications in the database will be returned. If 'found': false is returned, the medication does not exist in the catalog and you must NOT provide information about it from general knowledge. Instead, use list_medications to find alternatives.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Medication name (brand, generic, or active ingredient) - can be in any language. The tool handles typos automatically, so you can use this even if the spelling might be slightly off."}
            },
            "required": ["name"]
        },
    },
    {
        "type": "function",
        "name": "list_medications",
        "description": "List or search medications from the catalog. Use this to browse available medications or find medications when you're unsure of the exact name, or when a requested medication is not found and you need to suggest alternatives. More efficient than calling get_medication_by_name multiple times. Returns a list of medications with basic info (med_id, brand_name, generic_name, form, strength, rx_required). Use get_medication_by_name if you need full details about a specific medication. CRITICAL: Only medications in the database will be returned. Always use this tool when a medication is not found to search for alternatives.",
        "parameters": {
            "type": "object",
            "properties": {
                "search_term": {"type": "string", "description": "Optional search term to filter medications by brand name, generic name, or active ingredients. If not provided, returns all medications up to the limit."},
                "limit": {"type": "integer", "description": "Maximum number of medications to return (default: 20, max recommended: 50)"}
            },
            "required": []
        },
    },
    {
        "type": "function",
        "name": "search_users",
        "description": "Search for users by name, email, phone, or user_id. Use this to find a user when you need their user_id for prescription operations (like listing prescriptions or requesting refills). At least one search parameter must be provided.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Search by user's full name (partial match supported)"},
                "email": {"type": "string", "description": "Search by user's email address (partial match supported)"},
                "phone": {"type": "string", "description": "Search by user's phone number (partial match supported)"},
                "user_id": {"type": "string", "description": "Search by exact user_id"}
            },
            "required": []
        },
    },
    {
        "type": "function",
        "name": "check_stock_availability",
        "description": "Check inventory quantity for a medication in a specific store.",
        "parameters": {
            "type": "object",
            "properties": {
                "med_id": {"type": "string"},
                "store_id": {"type": "string"}
            },
            "required": ["med_id", "store_id"]
        },
    },
    {
        "type": "function",
        "name": "list_user_prescriptions",
        "description": "List prescriptions for a user (for refill workflows). Returns data in English.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"}
            },
            "required": ["user_id"]
        },
    },
    {
        "type": "function",
        "name": "request_prescription_refill",
        "description": "Submit a refill request for a user's prescription.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "prescription_id": {"type": "string"},
            },
            "required": ["user_id", "prescription_id"]
        },
    },
    {
        "type": "function",
        "name": "query_medications_flexible",
        "description": "Flexible medication query with multiple optional filters. All parameters are optional - combine as needed. Use this for complex searches like 'find all tablets with paracetamol that don't require prescription'. More powerful than list_medications when you need to filter by multiple criteria. Returns medications matching ALL specified criteria.",
        "parameters": {
            "type": "object",
            "properties": {
                "brand_name": {"type": "string", "description": "Filter by brand name (partial match)"},
                "generic_name": {"type": "string", "description": "Filter by generic name (partial match)"},
                "active_ingredient": {"type": "string", "description": "Filter by active ingredient (partial match)"},
                "form": {"type": "string", "description": "Filter by form (e.g., 'tablet', 'liquid', 'capsule')"},
                "strength": {"type": "string", "description": "Filter by strength (e.g., '200 mg', '500 mg')"},
                "rx_required": {"type": "boolean", "description": "Filter by prescription requirement (true = requires prescription, false = over-the-counter)"},
                "limit": {"type": "integer", "description": "Maximum number of results (default: 20, max recommended: 50)"}
            },
            "required": []
        },
    },
    {
        "type": "function",
        "name": "query_medications_with_stock",
        "description": "Query medications with optional stock filtering across one or more stores. Combines medication search with inventory checks in a single efficient query. Use this when you need to find medications AND check their availability. Much more efficient than calling get_medication_by_name and check_stock_availability separately.",
        "parameters": {
            "type": "object",
            "properties": {
                "search_term": {"type": "string", "description": "Search term for brand name, generic name, or active ingredients"},
                "active_ingredient": {"type": "string", "description": "Filter by active ingredient"},
                "form": {"type": "string", "description": "Filter by form (e.g., 'tablet')"},
                "rx_required": {"type": "boolean", "description": "Filter by prescription requirement"},
                "store_ids": {"type": "array", "items": {"type": "string"}, "description": "List of store IDs to check (e.g., ['STORE_TLV_01', 'STORE_JLM_01']). If not provided, checks all stores."},
                "in_stock_only": {"type": "boolean", "description": "If true, only return medications that are in stock at the specified stores"},
                "limit": {"type": "integer", "description": "Maximum number of medications to return (default: 20)"}
            },
            "required": []
        },
    },
    {
        "type": "function",
        "name": "query_stock_multiple_stores",
        "description": "Check stock availability for a medication across multiple stores in a single query. Use this instead of calling check_stock_availability multiple times. Can search by med_id or medication name.",
        "parameters": {
            "type": "object",
            "properties": {
                "med_id": {"type": "string", "description": "Medication ID (use this if you know it)"},
                "med_name": {"type": "string", "description": "Medication name (brand or generic) - will look up med_id automatically"},
                "store_ids": {"type": "array", "items": {"type": "string"}, "description": "List of store IDs to check. If not provided, checks all stores."},
                "in_stock_only": {"type": "boolean", "description": "If true, only return stores where medication is in stock"}
            },
            "required": []
        },
    },
    {
        "type": "function",
        "name": "list_stores",
        "description": "List available pharmacy store locations. Use this to find store_ids when customers ask about specific cities or locations. Returns store_id, name, and city for each store.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "Optional: Filter stores by city name (e.g., 'Tel Aviv', 'Jerusalem')"}
            },
            "required": []
        },
    },
    {
        "type": "function",
        "name": "query_prescriptions_flexible",
        "description": "Flexible prescription query with multiple optional filters. Can search by user, medication, expiration status, and refill availability. Use this for complex queries like 'find all prescriptions expiring in the next 7 days' or 'find prescriptions for a specific medication across all users'.",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "Filter by user ID"},
                "med_id": {"type": "string", "description": "Filter by medication ID"},
                "med_name": {"type": "string", "description": "Filter by medication name (will look up med_id)"},
                "expiring_soon_days": {"type": "integer", "description": "Find prescriptions expiring within this many days (e.g., 7 for next week)"},
                "has_refills": {"type": "boolean", "description": "Filter by refill availability (true = has refills remaining, false = no refills)"},
                "limit": {"type": "integer", "description": "Maximum number of results (default: 50)"}
            },
            "required": []
        },
    },
]

def run_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    # Map tool name to implementation
    tool_map = {
        "get_medication_by_name": get_medication_by_name,
        "list_medications": list_medications,
        "search_users": search_users,
        "check_stock_availability": check_stock_availability,
        "list_user_prescriptions": list_user_prescriptions,
        "request_prescription_refill": request_prescription_refill,
        "query_medications_flexible": query_medications_flexible,
        "query_medications_with_stock": query_medications_with_stock,
        "query_stock_multiple_stores": query_stock_multiple_stores,
        "list_stores": list_stores,
        "query_prescriptions_flexible": query_prescriptions_flexible,
    }

    func = tool_map.get(name)
    if not func:
        return {"error": "UNKNOWN_TOOL", "tool": name}

    # Best-effort tracking of tool usage; never let analytics break the main flow
    try:
        _increment_tool_stat(name)
    except Exception as e:
        # Should be unreachable because _increment_tool_stat already swallows,
        # but double-guard + logging to keep tool execution safe and observable.
        logger.exception("Unexpected error while incrementing tool_stats for tool=%r", name)

    # Execute the tool function with error handling
    try:
        return func(**args)
    except TypeError as e:
        # Handle missing required arguments
        error_msg = str(e)
        if "missing" in error_msg and "required" in error_msg:
            return {
                "error": "MISSING_REQUIRED_ARGUMENT",
                "message": error_msg,
                "tool": name
            }
        # Re-raise other TypeErrors
        raise
