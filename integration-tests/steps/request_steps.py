from typing import Dict, Generator, Tuple
from uuid import uuid4

from behave import given, step, when
from behave.runner import Context
from clients.locations_api_client import (
    location_search,
    patch_location,
    post_location,
    post_many_locations,
)
from helpers.jwt import get_system_token
from helpers.locations import (
    bay_factory,
    bed_factory,
    hospital_factory,
    organisation_factory,
    slugify,
    ward_factory,
)
from requests import Response


def _create_location(context: Context, location: Dict) -> None:
    name: str = location["display_name"]
    response: Response = post_location(location, jwt=get_system_token())
    context.create_location_response = response
    assert response.status_code == 200
    context.location_map[name] = response.json()["uuid"]


@given('a hospital called "(?P<name>[^"]*)" exists')
def hospital_exists(context: Context, name: str) -> None:
    _create_location(context, hospital_factory(name, ods_code="H1"))


@when('a ward "(?P<name>[^"]*)" is created in "(?P<hospital>[^"]*)"')
def ward_exists(context: Context, name: str, hospital: str) -> None:
    _create_location(
        context,
        ward_factory(name, ods_code="W1", parent=context.location_map[hospital]),
    )


@step('a bay "(?P<name>[^"]*)" is created in "(?P<ward>[^"]*)"')
def bay_exists(context: Context, name: str, ward: str) -> None:
    _create_location(
        context, bay_factory(name, ods_code="B1", parent=context.location_map[ward])
    )


@step('a bed "(?P<name>[^"]*)" is created in "(?P<bay>[^"]*)"')
def bed_exists(context: Context, name: str, bay: str) -> None:
    _create_location(
        context, bed_factory(name, ods_code="W1", parent=context.location_map[bay])
    )


@when("we fetch the location hierarchy")
def fetch_location_hierarchy(context: Context) -> None:
    response: Response = location_search(
        jwt=get_system_token(),
        location_types=["225746001", "22232009"],
        compact=True,
        children=True,
    )

    context.hierarchy = response.json()


def names(category: str, count: str) -> Generator[Tuple[str, int, str], None, None]:
    for c in range(int(count)):
        name = f"{category} {c+1}"
        ods_code = slugify(name)
        yield name, c + 1, ods_code


@given(
    """(?P<hospitals>\d+) hospitals each with (?P<wards>\d+) wards each with (?P<bays>\d+) bays and (?P<beds>\d+) beds exists"""
)
def bulk_create(
    context: Context, hospitals: str, wards: str, bays: str, beds: str
) -> None:
    context.hospital_count, context.ward_count, context.bay_count, context.bed_count = (
        int(hospitals),
        int(wards),
        int(bays),
        int(beds),
    )
    locations = []
    for hospital, hospital_index, hospital_ods_code in names("Hospital", hospitals):
        hospital_uuid = str(uuid4())
        locations.append(
            hospital_factory(hospital, ods_code=hospital_ods_code, uuid=hospital_uuid)
        )
        for ward, ward_index, ward_ods_code in names(f"H{hospital_index} Ward", wards):
            ward_uuid = str(uuid4())
            locations.append(
                ward_factory(
                    ward, ods_code=ward_ods_code, parent=hospital_uuid, uuid=ward_uuid
                )
            )
            for bay, bay_index, bay_ods_code in names(
                f"H{hospital_index}W{ward_index} Bay", bays
            ):
                bay_uuid = str(uuid4())
                locations.append(
                    bay_factory(
                        bay, ods_code=bay_ods_code, parent=ward_uuid, uuid=bay_uuid
                    )
                )
                for bed, bed_index, bed_ods_code in names(
                    f"H{hospital_index}W{ward_index}B{bay_index} Bed", beds
                ):
                    locations.append(
                        bed_factory(bed, ods_code=bed_ods_code, parent=bay_uuid)
                    )
    response: Response = post_many_locations(locations, jwt=get_system_token())
    context.create_location_response = response
    assert response.status_code == 200


@when(
    'the "(?P<name>[^"]*)" ward\'s default score system is updated to (?P<score_system>.*)'
)
def update_ward(context: Context, name: str, score_system: str) -> None:
    ward_uuid: str = context.location_map[name]
    update_details = {"score_system_default": score_system}
    response = patch_location(
        location_uuid=ward_uuid, update_details=update_details, jwt=get_system_token()
    )
    context.location_update_response = response


@step('an Organisation "(?P<name>[^"]*)" is created')
def create_organisation(context: Context, name: str) -> None:
    _create_location(context, organisation_factory(name))
