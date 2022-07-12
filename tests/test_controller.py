import collections
from datetime import date, datetime
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Type

import draymed
import pytest
from flask import Flask
from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.helpers.error_handler import DuplicateResourceException
from pytest_mock import MockFixture

from dhos_locations_api.blueprint_api import controller as location_controller
from dhos_locations_api.models.api_spec import LocationResponse
from dhos_locations_api.models.location import Location

WARD_LOCATION_TYPE = draymed.codes.code_from_name("ward", category="location")
BAY_LOCATION_TYPE = draymed.codes.code_from_name("bay", category="location")
BED_LOCATION_TYPE = draymed.codes.code_from_name("bed", category="location")
HOSPITAL_LOCATION_TYPE = draymed.codes.code_from_name("hospital", category="location")

SendLocations = collections.namedtuple(
    "SendLocations", ["bed", "bay", "ward", "hospital"]
)


@pytest.mark.usefixtures("app")
class TestLocationController:
    @pytest.fixture
    def send_locations(
        self,
        hospital_factory: Callable,
        ward_factory: Callable,
        bay_factory: Callable,
        bed_factory: Callable,
        send_hospital_uuid: str,
    ) -> SendLocations:
        hospital_uuid: str = hospital_factory(
            ods_code="Hospital-1",
            parent=None,
            product_name="SEND",
            active=True,
            address_line_1="Barts ave",
            display_name="St Barts Hospital",
        )
        ward_uuid: str = ward_factory(
            ods_code="WARD-1",
            parent=hospital_uuid,
            product_name="SEND",
            active=True,
            display_name="The Ward",
            score_system_default="meows",
        )

        bay_uuid: str = bay_factory(
            ods_code="The Bay",
            parent=ward_uuid,
            product_name="SEND",
            active=True,
            display_name="Bay-1",
        )
        bed_uuid: str = bed_factory(
            ods_code="Bed-2",
            parent=bay_uuid,
            product_name="SEND",
            active=True,
            display_name="The Bed",
        )
        hospital_data: Dict = location_controller.get_location_by_uuid(hospital_uuid)
        ward_data: Dict = location_controller.get_location_by_uuid(ward_uuid)
        bay_data: Dict = location_controller.get_location_by_uuid(bay_uuid)
        bed_data: Dict = location_controller.get_location_by_uuid(bed_uuid)
        return SendLocations(bed_data, bay_data, ward_data, hospital_data)

    @pytest.fixture
    def multiple_locations(
        self,
        send_hospital_uuid: str,
        gdm_hospital_uuid: str,
        ward_factory: Callable,
        bay_factory: Callable,
    ) -> Generator[Dict, None, None]:
        uuids: Dict = {
            "SEND": {True: {send_hospital_uuid}, False: set()},
            "GDM": {True: {gdm_hospital_uuid}, False: set()},
        }

        for ward_index in range(7):
            ward_active = (ward_index % 3) != 0
            ward_uuid = ward_factory(
                address_line_1="Address",
                postcode="",
                country="",
                ods_code=f"Ward-{ward_index}",
                parent=send_hospital_uuid,
                display_name=f"{ward_index} Ward",
                product_name=["SEND", "GDM"],
                active=ward_active,
            )
            uuids["SEND"][ward_active].add(ward_uuid)
            uuids["GDM"][ward_active].add(ward_uuid)

            for bay_index in range(2):
                bay_active = ward_active and (bay_index % 2) == 0
                bay_uuid = bay_factory(
                    address_line_1="Address",
                    postcode="",
                    country="",
                    ods_code=f"Bay-{bay_index}.{ward_index}",
                    parent=ward_uuid,
                    display_name=f"{bay_index} Bay, {ward_index} Ward",
                    product_name=["SEND", "GDM"]
                    if ward_index == 0 and bay_index == 0
                    else ["SEND"],
                    active=bay_active,
                )
                uuids["SEND"][bay_active].add(bay_uuid)

        for product in uuids:
            uuids[product][None] = uuids[product][True].union(uuids[product][False])

        yield uuids

    def test_create_location(
        self, any_uuid: str, any_datetime: datetime, any_string: str
    ) -> None:
        data = {
            "dh_products": [
                {
                    "product_name": "FOO",
                    "opened_date": "2020-11-12T12:00:00.000+00:00",
                }
            ],
            "location_type": "1234",
            "ods_code": "ODS999",
            "display_name": "An Hospital",
            "parent": None,
        }
        expected: Dict[str, Any] = {
            "active": True,
            "address_line_1": None,
            "address_line_2": None,
            "address_line_3": None,
            "address_line_4": None,
            "country": None,
            "created": any_datetime,
            "created_by": any_string,
            "dh_products": [
                {
                    "product_name": "FOO",
                    "opened_date": date(2020, 11, 12),
                    "closed_date": None,
                    "created": any_datetime,
                    "uuid": any_uuid,
                }
            ],
            "display_name": "An Hospital",
            "locality": None,
            "location_type": "1234",
            "modified": any_datetime,
            "modified_by": any_string,
            "ods_code": "ODS999",
            "parent": None,
            "postcode": None,
            "region": None,
            "uuid": any_uuid,
        }
        response = location_controller.create_location(data)

        assert response == expected

    def test_create_with_parent(
        self,
        any_uuid: str,
        any_datetime: datetime,
        any_string: str,
        send_locations: SendLocations,
    ) -> None:
        hospital_uuid = send_locations.hospital["uuid"]
        data = {
            "dh_products": [
                {
                    "product_name": "SEND",
                    "opened_date": "2020-11-12T12:00:00.000+00:00",
                }
            ],
            "location_type": "1234",
            "ods_code": "ODS999",
            "parent_ods_code": "Hospital-1",
            "display_name": "Another ward",
        }
        expected: Dict[str, Any] = {
            "active": True,
            "address_line_1": None,
            "address_line_2": None,
            "address_line_3": None,
            "address_line_4": None,
            "country": None,
            "created": any_datetime,
            "created_by": any_string,
            "dh_products": [
                {
                    "product_name": "SEND",
                    "opened_date": date(2020, 11, 12),
                    "closed_date": None,
                    "created": any_datetime,
                    "uuid": any_uuid,
                }
            ],
            "display_name": "Another ward",
            "locality": None,
            "location_type": "1234",
            "modified": any_datetime,
            "modified_by": any_string,
            "ods_code": "ODS999",
            "parent": {
                "uuid": hospital_uuid,
                "ods_code": "Hospital-1",
                "parent": None,
                "display_name": "St Barts Hospital",
                "location_type": "22232009",
            },
            "postcode": None,
            "region": None,
            "uuid": any_uuid,
        }
        response = location_controller.create_location(data)

        assert response == expected

    def test_create_with_parent_and_default_score(
        self,
        any_uuid: str,
        any_datetime: datetime,
        any_string: str,
        send_locations: SendLocations,
    ) -> None:
        hospital_uuid = send_locations.hospital["uuid"]
        ward_uuid = send_locations.ward["uuid"]
        data = {
            "dh_products": [
                {
                    "product_name": "SEND",
                    "opened_date": "2020-11-12T12:00:00.000+00:00",
                }
            ],
            "location_type": "1234",
            "ods_code": "ODS999",
            "parent_ods_code": "WARD-1",
            "display_name": "Somewhere",
        }
        expected: Dict[str, Any] = {
            "active": True,
            "address_line_1": None,
            "address_line_2": None,
            "address_line_3": None,
            "address_line_4": None,
            "country": None,
            "created": any_datetime,
            "created_by": any_string,
            "dh_products": [
                {
                    "product_name": "SEND",
                    "opened_date": date(2020, 11, 12),
                    "closed_date": None,
                    "created": any_datetime,
                    "uuid": any_uuid,
                }
            ],
            "display_name": "Somewhere",
            "locality": None,
            "location_type": "1234",
            "modified": any_datetime,
            "modified_by": any_string,
            "ods_code": "ODS999",
            "parent": {
                "uuid": ward_uuid,
                "ods_code": "WARD-1",
                "display_name": "The Ward",
                "location_type": "225746001",
                "score_system_default": "meows",
                "parent": {
                    "uuid": hospital_uuid,
                    "ods_code": "Hospital-1",
                    "parent": None,
                    "display_name": "St Barts Hospital",
                    "location_type": "22232009",
                },
            },
            "postcode": None,
            "region": None,
            "uuid": any_uuid,
        }
        response = location_controller.create_location(data)

        assert response == expected

    def test_unknown_parent_ods_code(
        self,
        hospital_factory: Callable,
        send_locations: SendLocations,
    ) -> None:
        data = {
            "dh_products": [
                {
                    "product_name": "FOO",
                    "opened_date": "2020-11-12T12:00:00.000+00:00",
                }
            ],
            "location_type": "1234",
            "ods_code": "A111",
            "parent_ods_code": "Foo-Bar",
            "display_name": "An Hospital",
        }
        with pytest.raises(ValueError) as excinfo:
            location_controller.create_location(data)

        assert str(excinfo.value) == f"Parent location with ods_code Foo-Bar not found"

    def test_duplicate_ods_code(self, hospital_factory: Callable) -> None:
        data = {
            "dh_products": [
                {
                    "product_name": "FOO",
                    "opened_date": "2020-11-12T12:00:00.000+00:00",
                }
            ],
            "location_type": "1234",
            "ods_code": "A111",
            "display_name": "An Hospital",
            "parent": None,
        }
        location_controller.create_location(data)

        data["display_name"] = "Another hospital"
        with pytest.raises(DuplicateResourceException) as excinfo:
            location_controller.create_location(data)

        assert str(excinfo.value) == "location with ods code 'A111' already exists"

    def test_create_many(
        self,
        any_uuid: str,
        any_datetime: datetime,
        any_string: str,
    ) -> None:
        HOSPITAL_SNOMED: str = draymed.codes.code_from_name("hospital", "location")
        WARD_SNOMED: str = draymed.codes.code_from_name("ward", "location")
        BAY_SNOMED: str = draymed.codes.code_from_name("bay", "location")
        products = [
            {
                "product_name": "SEND",
                "opened_date": "2020-11-12T12:00:00.000+00:00",
            }
        ]
        data: List[Dict] = [
            {
                "dh_products": products,
                "location_type": HOSPITAL_SNOMED,
                "ods_code": "HOSP-1",
                "parent_ods_code": None,
                "display_name": "Hospital 1",
            },
            {
                "dh_products": products,
                "location_type": WARD_SNOMED,
                "ods_code": "W-1",
                "parent_ods_code": "HOSP-1",
                "display_name": "Some ward",
            },
            {
                "dh_products": products,
                "location_type": BAY_SNOMED,
                "ods_code": "W-1-B-1",
                "parent_ods_code": "W-1",
                "display_name": "The bay",
            },
        ]
        expected: Dict[str, Any] = {"created": 3}
        response = location_controller.create_many_locations(data)

        assert response == expected

    def test_create_many_duplicate_ods(
        self,
        any_uuid: str,
        any_datetime: datetime,
        any_string: str,
    ) -> None:
        HOSPITAL_SNOMED: str = draymed.codes.code_from_name("hospital", "location")
        WARD_SNOMED: str = draymed.codes.code_from_name("ward", "location")
        BAY_SNOMED: str = draymed.codes.code_from_name("bay", "location")
        products = [
            {
                "product_name": "SEND",
                "opened_date": "2020-11-12T12:00:00.000+00:00",
            }
        ]
        data: List[Dict] = [
            {
                "dh_products": products,
                "location_type": HOSPITAL_SNOMED,
                "ods_code": "HOSP-1",
                "parent_ods_code": None,
                "display_name": "Hospital 1",
            },
            {
                "dh_products": products,
                "location_type": WARD_SNOMED,
                "ods_code": "W-1",
                "parent_ods_code": "HOSP-1",
                "display_name": "Some ward",
            },
            {
                "dh_products": products,
                "location_type": BAY_SNOMED,
                "ods_code": "W-1-B-1",
                "parent_ods_code": "W-1",
                "display_name": "The bay",
            },
            {
                "dh_products": products,
                "location_type": BAY_SNOMED,
                "ods_code": "W-1-B-1",
                "parent_ods_code": "W-1",
                "display_name": "The bay duplicated",
            },
        ]
        with pytest.raises(DuplicateResourceException) as excinfo:
            location_controller.create_many_locations(data)

        assert str(excinfo.value) == "duplicate ods_code creating locations"

    def test_post_location_all_fields(
        self, any_uuid: str, any_datetime: datetime, any_string: str
    ) -> None:
        uuid = generate_uuid()
        data = {
            "active": True,
            "address_line_1": "Address",
            "address_line_2": None,
            "address_line_3": None,
            "address_line_4": None,
            "country": "",
            "created": "2020-12-14T15:11:08Z",
            "created_by": "dhos-robot",
            "display_name": "Another ward",
            "locality": None,
            "location_type": "225746001",
            "modified": "2020-12-14T15:11:11Z",
            "modified_by": "dhos-robot",
            "ods_code": "L20",
            "parent": None,
            "postcode": "",
            "region": None,
            "uuid": uuid,
        }
        expected: Dict[str, Any] = {
            "active": True,
            "address_line_1": "Address",
            "address_line_2": None,
            "address_line_3": None,
            "address_line_4": None,
            "country": "",
            "created": datetime(2020, 12, 14, 15, 11, 8),
            "created_by": "dhos-robot",
            "display_name": "Another ward",
            "locality": None,
            "location_type": "225746001",
            "modified": datetime(2020, 12, 14, 15, 11, 11),
            "modified_by": "dhos-robot",
            "ods_code": "ODS999",
            "parent": None,
            "postcode": "",
            "region": None,
            "uuid": uuid,
        }
        location_controller.create_location(data)

    @pytest.mark.parametrize(
        ["location_type", "expected"],
        [
            (HOSPITAL_LOCATION_TYPE, "St Barts Hospital"),
            (WARD_LOCATION_TYPE, "The Ward"),
            (BAY_LOCATION_TYPE, "Bay-1"),
        ],
    )
    def test_get_parent_location(
        self,
        send_locations: SendLocations,
        location_type: str,
        expected: str,
        statement_counter: Any,
    ) -> None:
        location_data: Dict = send_locations.bed
        with statement_counter() as counter:
            parent: Optional[Location] = location_controller._get_parent_location(
                location_data["uuid"], location_type
            )
        assert parent and parent.display_name == expected
        assert counter.count == 1

    @pytest.mark.parametrize(
        ["location_type", "expected", "sql_count"],
        [
            (BED_LOCATION_TYPE, "The Bed", 4),
            (BAY_LOCATION_TYPE, "Bay-1", 3),
            (WARD_LOCATION_TYPE, "The Ward", 2),
            (HOSPITAL_LOCATION_TYPE, "St Barts Hospital", 1),
        ],
    )
    def test_get_location_type_by_id(
        self,
        send_locations: SendLocations,
        statement_counter: Any,
        location_type: str,
        expected: str,
        sql_count: int,
    ) -> None:
        location_uuid = send_locations.bed["uuid"]
        with statement_counter() as counter:
            response = location_controller.get_location_by_type(
                location_uuid, location_type
            )
        assert response["display_name"] == expected
        if sql_count > 1:
            assert isinstance(response["parent"], dict)

        assert counter.count == sql_count, [str(cl) for cl in counter.clauses]

    @pytest.mark.parametrize(
        ["location_type", "exception"],
        [
            ("999999999", ValueError),  # Error as location type does not exist
            (
                BED_LOCATION_TYPE,
                ValueError,
            ),  # Error as bay location object has no bed parent
        ],
    )
    def test_get_location_type_by_id_raises_error(
        self,
        send_locations: SendLocations,
        location_type: str,
        exception: Type[Exception],
    ) -> None:
        location_uuid: str = send_locations.bay["uuid"]
        with pytest.raises(exception):
            location_controller.get_location_by_type(location_uuid, location_type)

    def test_get_by_id_with_children(
        self, send_locations: SendLocations, statement_counter: Callable
    ) -> None:
        bed_uuid = send_locations.bed["uuid"]
        bay_uuid = send_locations.bay["uuid"]
        ward_uuid = send_locations.ward["uuid"]
        hospital_uuid = send_locations.hospital["uuid"]

        with statement_counter(limit=2) as counter:
            response = location_controller.get_location_by_uuid(
                hospital_uuid, children=True
            )
        assert set(response["children"]) == {bed_uuid, bay_uuid, ward_uuid}

    @pytest.mark.parametrize(
        "compact,want_children,expected",
        [(False, False, True), (True, False, False), (True, True, False)],
    )
    def test_locations_by_id(
        self,
        send_locations: SendLocations,
        statement_counter: Callable,
        compact: bool,
        want_children: bool,
        expected: bool,
    ) -> None:
        ward_uuid = send_locations.ward["uuid"]
        bay_uuid = send_locations.bay["uuid"]

        with statement_counter() as counter:
            result = location_controller.get_locations_by_uuids(
                location_uuids=[ward_uuid, bay_uuid],
                product_name="SEND",
                active=True,
                compact=compact,
                children=want_children,
            )
        assert len(result) == 2
        assert set(r["uuid"] for r in result) == {bay_uuid, ward_uuid}
        assert all([("dh_products" in r) is expected for r in result])
        assert all([("children" in r) is want_children for r in result])

    def test_locations_by_uuids_children(
        self, send_locations: SendLocations, statement_counter: Callable
    ) -> None:
        bed_uuid = send_locations.bed["uuid"]
        bay_uuid = send_locations.bay["uuid"]
        ward_uuid = send_locations.ward["uuid"]
        hospital_uuid = send_locations.hospital["uuid"]

        with statement_counter(limit=2) as counter:
            response = location_controller.get_locations_by_uuids(
                location_uuids=[bed_uuid, ward_uuid, hospital_uuid],
                children=True,
                product_name="SEND",
            )

        assert set(r["uuid"] for r in response) == {bed_uuid, ward_uuid, hospital_uuid}
        assert {r["uuid"]: set(r["children"]) for r in response} == {
            bed_uuid: set(),
            ward_uuid: {bed_uuid, bay_uuid},
            hospital_uuid: {bed_uuid, bay_uuid, ward_uuid},
        }

    def test_gdm_locations_all(
        self,
        location_factory: Callable,
        jwt_gdm_admin_uuid: str,
        mocker: MockFixture,
        assert_valid_schema: Callable[..., None],
    ) -> None:
        location_factory(
            display_name="ignore me!", active=True, product_name="FOO", ods_code="FOO-1"
        )
        location_uuid: str = location_factory(
            display_name="location 1", active=True, product_name="GDM", ods_code="GDM-1"
        )
        result: List[Dict] = location_controller.location_search(product_name="GDM")
        assert len(result) == 1, [r["display_name"] for r in result]
        assert result[0]["uuid"] == location_uuid
        assert_valid_schema(LocationResponse, result, many=True)

    def test_gdm_locations_from_clinician(
        self,
        jwt_gdm_clinician_uuid: str,
        gdm_hospital_uuid: str,
        mocker: MockFixture,
        assert_valid_schema: Callable[..., None],
    ) -> None:
        result: List[Dict] = location_controller.location_search(
            product_name="GDM",
            location_uuids=[gdm_hospital_uuid],
        )
        assert [r["uuid"] for r in result] == [gdm_hospital_uuid]
        assert_valid_schema(LocationResponse, result, many=True)

    def test_ignore_gdm_locations_not_from_clinician(
        self,
        location_factory: Any,
        jwt_gdm_clinician_uuid: str,
        gdm_hospital_uuid: str,
        mocker: MockFixture,
        assert_valid_schema: Callable[..., None],
    ) -> None:
        location2_uuid = location_factory(
            display_name="GDM location 2",
            active=True,
            product_name="GDM",
            ods_code="GDM-2",
        )
        result: List[Dict] = location_controller.location_search(
            product_name="GDM",
            location_uuids=[gdm_hospital_uuid],
        )
        assert [r["uuid"] for r in result] == [gdm_hospital_uuid]
        assert_valid_schema(LocationResponse, result, many=True)

    def test_get_locations_matching_ods_code(
        self, send_locations: SendLocations
    ) -> None:
        result = location_controller.location_search(ods_code="WARD-1")
        assert len(result) == 1
        assert result[0]["display_name"] == "The Ward"

    @pytest.mark.parametrize(
        "ods_code,product_name,result_count",
        [
            ("WARD-1", None, 1),
            ("WARD-1", "SEND", 1),
            ("WARD-1", "GDM", 0),
        ],
    )
    def test_get_locations_matching_ods_code_and_single_product(
        self,
        send_locations: SendLocations,
        ods_code: str,
        product_name: Optional[str],
        result_count: int,
    ) -> None:
        result = location_controller.location_search(
            ods_code="WARD-1", product_name=product_name
        )
        assert len(result) == result_count
        if result_count == 1:
            assert result[0]["display_name"] == "The Ward"

    @pytest.mark.parametrize(
        "ods_code,product_name",
        [
            ("Ward-0", None),
            ("Ward-0", "SEND"),
            ("Ward-0", "GDM"),
        ],
    )
    def test_get_locations_matching_ods_code_and_multi_product(
        self, multiple_locations: Dict, ods_code: str, product_name: Optional[str]
    ) -> None:
        result = location_controller.location_search(
            ods_code=ods_code, product_name=product_name
        )
        assert len(result) == 1
        assert result[0]["display_name"] == "0 Ward"

    @pytest.mark.parametrize(
        "ods_code,product_name,expected_count",
        [
            ("Ward-0", "SEND", 2),
            ("Ward-0", "GDM", 1),
        ],
    )
    def test_get_locations_matching_ods_code_and_multi_product_with_child_locations(
        self,
        multiple_locations: Dict,
        ods_code: str,
        product_name: Optional[str],
        expected_count: int,
    ) -> None:
        result = location_controller.location_search(
            ods_code=ods_code, product_name=product_name, children=True, compact=False
        )
        assert len(result) == 1
        assert len(result[0]["dh_products"]) == 2
        assert result[0]["display_name"] == "0 Ward"

        # "0 Ward" has 2 child locations active on SEND and 1 child location active on GDM.
        assert len(result[0]["children"]) == expected_count

    def test_get_location_with_no_children_matching_ods_code(
        self, send_hospital_uuid: str
    ) -> None:
        result = location_controller.location_search(
            ods_code="Frideswide", children=True
        )
        assert len(result) == 1
        assert result[0]["display_name"] == "St Frideswide Hospital"
        assert result[0]["children"] == []

    def test_get_gdm_locations_only_send_locations(
        self,
        send_locations: SendLocations,
        jwt_gdm_admin_uuid: str,
        assert_valid_schema: Callable[..., None],
    ) -> None:
        result = location_controller.location_search(product_name="GDM")
        assert len(result) == 0
        assert_valid_schema(LocationResponse, result, many=True)

    @pytest.mark.parametrize(
        "active,compact", [(True, True), (False, True), (None, True), (True, False)]
    )
    def test_get_locations_nested(
        self,
        app: Flask,
        jwt_send_clinician_uuid: str,
        send_hospital_uuid: str,
        multiple_locations: Dict,
        active: bool,
        compact: bool,
        assert_valid_schema: Callable[..., None],
    ) -> None:
        expected_uuids: Set[str] = multiple_locations["SEND"][active]
        locations = location_controller.location_search(
            product_name="SEND", active=active, location_types=None, compact=compact
        )
        assert set(l["uuid"] for l in locations) == expected_uuids

        for l in locations:
            if l["location_type"] == BAY_LOCATION_TYPE:
                # Each Bay has a chain of parents two deep
                assert l["parent"]["parent"]["uuid"] == send_hospital_uuid
            elif l["location_type"] == WARD_LOCATION_TYPE:
                # Each Ward has a parent chain one deep
                assert l["parent"]["uuid"] == send_hospital_uuid
            else:
                # and the base location has no parent
                assert l["uuid"] == send_hospital_uuid
                assert not l["parent"]

        assert_valid_schema(LocationResponse, locations, many=True)

    def test_update_location_parents(
        self, jwt_send_admin_uuid: str, ward_uuids: List[str], send_hospital_uuid: str
    ) -> None:
        new_parent_uuid: str = ward_uuids.pop()
        for uuid in ward_uuids:
            # Set parent
            result = location_controller.update_location(
                location_uuid=uuid,
                update_details={"parent_location": new_parent_uuid},
            )
            assert result["parent"]["uuid"] == new_parent_uuid
            # Change parent
            result = location_controller.update_location(
                location_uuid=uuid,
                update_details={"parent_location": send_hospital_uuid},
            )
            assert result["parent"]["uuid"] == send_hospital_uuid
            # Remove parent
            result = location_controller.update_location(
                location_uuid=uuid,
                update_details={"parent_location": None},
            )
            assert result["parent"] is None

    def test_update_location_ods_code_not_unique(
        self, jwt_send_admin_uuid: str, location_factory: Callable
    ) -> None:
        location1 = location_factory("location1", ods_code="ods-location1")
        location_factory("location2", ods_code="ods-location2")
        with pytest.raises(DuplicateResourceException):
            location_controller.update_location(
                location_uuid=location1, update_details={"ods_code": "ods-location2"}
            )

    def test_update_location_ods_code_to_same(
        self, jwt_send_admin_uuid: str, location_factory: Callable
    ) -> None:
        location1 = location_factory("location1", ods_code="location1")
        result = location_controller.update_location(
            location_uuid=location1, update_details={"ods_code": "location1"}
        )
        assert result["ods_code"] == "location1"

    def test_cannot_duplicate_product_on_update(
        self, jwt_gdm_admin_uuid: str, location_factory: Callable
    ) -> None:
        location1_uuid: str = location_factory("Eastleigh", product_name="GDM")
        location: Dict = {
            "dh_products": [
                {
                    "product_name": "GDM",
                    "opened_date": date(2000, 1, 1),
                }
            ],
        }
        with pytest.raises(ValueError):
            result = location_controller.update_location(
                location_uuid=location1_uuid, update_details=location
            )

    def test_cannot_rename_to_duplicate_product(
        self, jwt_gdm_admin_uuid: str, location_factory: Callable
    ) -> None:
        location1_uuid: str = location_factory("Eastleigh", product_name=["GDM", "FOO"])
        original_location = location_controller.get_location_by_uuid(location1_uuid)
        for prod in original_location["dh_products"]:
            if prod["product_name"] == "FOO":
                prod_uuid = prod["uuid"]
                break
        else:
            assert False, "Cannot find expected product"

        location: Dict = {
            "dh_products": [
                {
                    "uuid": prod_uuid,
                    "product_name": "GDM",
                    "opened_date": date(2000, 1, 1),
                }
            ],
        }
        with pytest.raises(ValueError):
            result = location_controller.update_location(
                location_uuid=location1_uuid, update_details=location
            )

    def test_update_location_fields(
        self, jwt_gdm_admin_uuid: str, location_factory: Callable
    ) -> None:
        location1_uuid: str = location_factory("Eastleigh", product_name="GDM")
        original_location = location_controller.get_location_by_uuid(location1_uuid)

        location: Dict = {
            "address_line_1": "Address",
            "postcode": "",
            "country": "",
            "location_type": "",
            "ods_code": "location1a",
            "display_name": "Theme Hospital",
            "dh_products": [
                {
                    "uuid": original_location["dh_products"][0]["uuid"],
                    "product_name": "GDM",
                    "opened_date": date(2000, 1, 1),
                }
            ],
        }
        result = location_controller.update_location(
            location_uuid=location1_uuid, update_details=location
        )
        for k in location:
            if isinstance(location[k], (str, date)):
                assert result[k] == location[k]
            elif isinstance(location[k], list):
                for sk in location[k][0]:
                    assert result[k][0][sk] == location[k][0][sk]

    def test_get_send_locations_showing_no_children(
        self,
        jwt_send_clinician_uuid: str,
        send_hospital_uuid: str,
        assert_valid_schema: Callable[..., None],
    ) -> None:
        result = location_controller.location_search(children=True)
        assert len(result) == 1
        assert result[0]["children"] == []
        assert_valid_schema(LocationResponse, result, many=True)

    def test_get_send_locations_with_children(
        self,
        jwt_send_clinician_uuid: str,
        send_locations: SendLocations,
        assert_valid_schema: Callable[..., None],
    ) -> None:
        ward_uuid = send_locations.ward["uuid"]
        hospital_uuid = send_locations.hospital["uuid"]

        locations = location_controller.location_search(children=True)
        for location in locations:
            assert "children" in location
            if location["uuid"] == hospital_uuid:
                assert ward_uuid in location["children"]
        assert_valid_schema(LocationResponse, locations, many=True)

    def test_get_locations_by_uuids(
        self,
        send_locations: SendLocations,
        assert_valid_schema: Callable[..., None],
    ) -> None:
        bed_uuid = send_locations.bed["uuid"]
        ward_uuid = send_locations.ward["uuid"]
        hospital_uuid = send_locations.hospital["uuid"]

        locations = location_controller.get_locations_by_uuids(
            [bed_uuid, ward_uuid, hospital_uuid], compact=True, children=True
        )
        for location in locations:
            assert "children" in location
        assert_valid_schema(LocationResponse, locations, many=True)

    def test_location_score_system_default(
        self, jwt_send_admin_uuid: str, location_factory: Callable
    ) -> None:
        location_uuid: str = location_factory("Maternity Ward", product_name="SEND")
        location_1: Dict = location_controller.get_location_by_uuid(location_uuid)
        assert "score_system_default" not in location_1
        location_2 = location_controller.update_location(
            location_uuid=location_1["uuid"],
            update_details={"score_system_default": "meows"},
        )
        assert location_2.get("score_system_default") == "meows"

    def test_location_score_system_default_hierarchy(
        self, jwt_send_admin_uuid: str, send_locations: SendLocations
    ) -> None:
        ward_uuid = send_locations.ward["uuid"]
        hospital_uuid = send_locations.hospital["uuid"]
        location_controller.update_location(
            location_uuid=hospital_uuid,
            update_details={"score_system_default": "meows"},
        )
        matching_locations = location_controller.location_search(
            location_uuids=[ward_uuid], product_name="SEND"
        )
        assert len(matching_locations) == 1
        assert matching_locations[0]["parent"]["score_system_default"] == "meows"
