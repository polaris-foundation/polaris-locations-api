from typing import Any, Dict, Generator

from behave import step, then
from behave.runner import Context
from requests import Response


def _flatten_parents(location: Dict) -> Generator[Dict, None, None]:
    while location["parent"]:
        yield location["parent"]
        location = location["parent"]


@then("the location creation response is correct")
def response_is_correct(context: Context) -> None:
    assert context.create_location_response.status_code == 200
    returned: Dict = context.create_location_response.json()
    assert isinstance(returned, Dict)


@then('location "(?P<child>[^"]*)" has parents "(?P<parents>[^"]*)"')
def check_location_parents(context: Context, child: str, parents: str) -> None:
    parent_uuids = [
        context.location_map[parent.strip()] for parent in parents.split(",")
    ]

    returned = context.create_location_response.json()

    assert [parent["uuid"] for parent in _flatten_parents(returned)] == parent_uuids


@step("we received all of the expected locations")
def check_location_hierarchy(context: Context) -> None:
    hierarchy: Dict[str, Dict[str, Any]] = context.hierarchy
    assert len(hierarchy) == context.hospital_count * (context.ward_count + 1)
    for location in hierarchy.values():
        location_type = location["location_type"]
        assert location_type in ["225746001", "22232009"]
        if location_type == "22232009":
            # Hospital
            assert location["parent"] is None
            assert len(location["children"]) == context.ward_count * (
                context.bay_count * (context.bed_count + 1) + 1
            )
        else:
            # Ward
            parent = hierarchy[location["parent"]["uuid"]]
            assert location["parent"] == {
                k: parent[k]
                for k in ("uuid", "parent", "location_type", "ods_code", "display_name")
            }
            assert len(location["children"]) == context.bay_count * (
                context.bed_count + 1
            )


@then(
    "the resulting location has the expected default score system of (?P<score_system>.*)"
)
def check_location_update_response(context: Context, score_system: str) -> None:
    response: Response = context.location_update_response
    assert response.status_code == 200
    assert response.json()["score_system_default"] == score_system
