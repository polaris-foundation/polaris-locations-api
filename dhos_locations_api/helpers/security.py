from typing import Any, Dict, List, Optional

from flask import g, request
from she_logging import logger


def get_clinician_locations() -> Optional[List[str]]:
    if (
        "read:gdm_location" in g.jwt_scopes
        and not "read:gdm_location_all" in g.jwt_scopes
        and not "read:location_all" in g.jwt_scopes
    ):
        location_ids = request.headers.get("X-Location-Ids", "")
        if location_ids:
            filter_ids: List[str] = location_ids.split(",")
            logger.debug("Clinician locations %s", filter_ids)
            return filter_ids
        return []  # GDM clinician with no locations
    # No location restrictions
    return None


def ods_code_is_none(
    jwt_claims: Dict, claims_map: Dict, ods_code: Optional[str] = None, **kwargs: Any
) -> bool:
    return ods_code is None
