from typing import Dict, List, Optional

import requests
from environs import Env
from requests import Response


def _get_base_url() -> str:
    return Env().str("DHOS_LOCATIONS_BASE_URL", "http://dhos-locations-api:5000")


def post_location(location_data: Dict, jwt: str) -> Response:
    return requests.post(
        f"{_get_base_url()}/dhos/v1/location",
        headers={"Authorization": f"Bearer {jwt}"},
        json=location_data,
        timeout=15,
    )


def patch_location(location_uuid: str, update_details: Dict, jwt: str) -> Response:
    return requests.patch(
        f"{_get_base_url()}/dhos/v1/location/{location_uuid}",
        headers={"Authorization": f"Bearer {jwt}"},
        json=update_details,
        timeout=15,
    )


def post_many_locations(location_list: List[Dict], jwt: str) -> Response:
    return requests.post(
        f"{_get_base_url()}/dhos/v1/location/bulk",
        headers={"Authorization": f"Bearer {jwt}"},
        json=location_list,
        timeout=150,
    )


def get_location_by_uuid(location_uuid: str, jwt: str) -> Response:
    return requests.get(
        f"{_get_base_url()}/dhos/v1/location/{location_uuid}",
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=15,
    )


def location_search(
    jwt: str,
    ods_code: Optional[str] = None,
    location_types: Optional[List[str]] = None,
    active: Optional[bool] = True,
    product_name: Optional[List[str]] = None,
    children: bool = False,
    compact: bool = True,
    location_uuids: List[str] = None,
) -> Response:
    if location_uuids is None:
        return requests.post(
            f"{_get_base_url()}/dhos/v1/location/search",
            params=dict(
                ods_code=ods_code,
                location_types="|".join(location_types) if location_types else None,
                active=active,
                product_name=product_name,
                children=children,
                compact=compact,
            ),
            json=location_uuids,
            headers={"Authorization": f"Bearer {jwt}"},
            timeout=15,
        )
    else:
        return requests.post(
            f"{_get_base_url()}/dhos/v1/location/search",
            params=dict(
                ods_code=ods_code,
                location_types=location_types,
                active=active,
                product_name=product_name,
                children=children,
                compact=compact,
                location_uuids=location_uuids,
            ),
            json=location_uuids,
            headers={"Authorization": f"Bearer {jwt}"},
            timeout=15,
        )


def drop_all_data(jwt: str) -> Response:
    response = requests.post(
        f"{_get_base_url()}/drop_data",
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=15,
    )
    assert response.status_code == 200
    return response
