from datetime import datetime, timezone
from typing import Callable, Dict, List

import draymed
import pytest
from flask.testing import FlaskClient
from flask_batteries_included.helpers import generate_uuid
from mock import Mock
from pytest_mock import MockerFixture

from dhos_locations_api.blueprint_api import controller as location_controller

WARD_SNOMED: str = draymed.codes.code_from_name("ward", "location")


@pytest.mark.usefixtures("app", "mock_bearer_validation")
class TestLocationsApi:
    @pytest.fixture
    def location_request(self) -> Dict:
        return {
            "dh_products": [
                {
                    "product_name": "GDM",
                    "opened_date": datetime.now(tz=timezone.utc).isoformat(
                        timespec="milliseconds"
                    ),
                }
            ],
            "location_type": WARD_SNOMED,
            "ods_code": "12345",
            "display_name": "Location Name",
        }

    def test_post_location_success(
        self,
        client: FlaskClient,
        mocker: MockerFixture,
        location_request: Dict,
        jwt_gdm_admin_uuid: str,
    ) -> None:
        mock_create: Mock = mocker.patch.object(
            location_controller,
            "create_location",
            return_value={"uuid": generate_uuid()},
        )
        response = client.post(
            "/dhos/v1/location",
            json=location_request,
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json is not None
        assert "uuid" in response.json
        mock_create.assert_called_with(location_details=location_request)

    @pytest.mark.parametrize(
        "missing_field", ["dh_products", "location_type", "display_name"]
    )
    def test_post_location_invalid_400(
        self, client: FlaskClient, location_request: Dict, missing_field: str
    ) -> None:
        del location_request[missing_field]
        response = client.post(
            "/dhos/v1/location",
            json=location_request,
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 400

    def test_post_location_extra_field_400(
        self,
        client: FlaskClient,
        location_request: Dict,
        jwt_gdm_admin_uuid: str,
    ) -> None:
        location_request["extra"] = "field"
        response = client.post(
            "/dhos/v1/location",
            json=location_request,
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 400

    def test_post_location_bulk_success(
        self,
        client: FlaskClient,
        mocker: MockerFixture,
        location_request: Dict,
        jwt_gdm_admin_uuid: str,
    ) -> None:
        mock_create: Mock = mocker.patch.object(
            location_controller,
            "create_many_locations",
            return_value={"created": 1},
        )
        response = client.post(
            "/dhos/v1/location/bulk",
            json=[location_request],
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json == {"created": 1}
        mock_create.assert_called_with(location_list=[location_request])

    @pytest.mark.parametrize(
        "missing_field", ["dh_products", "location_type", "display_name"]
    )
    def test_post_location_bulk_invalid_400(
        self, client: FlaskClient, location_request: Dict, missing_field: str
    ) -> None:
        del location_request[missing_field]
        response = client.post(
            "/dhos/v1/location/bulk",
            json=[location_request],
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 400

    def test_post_location_bulk_extra_field_400(
        self,
        client: FlaskClient,
        location_request: Dict,
        jwt_gdm_admin_uuid: str,
    ) -> None:
        location_request["extra"] = "field"
        response = client.post(
            "/dhos/v1/location/bulk",
            json=[location_request],
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 400

    def test_patch_location(
        self, client: FlaskClient, mocker: MockerFixture, jwt_gdm_admin_uuid: str
    ) -> None:
        mock_create: Mock = mocker.patch.object(
            location_controller,
            "update_location",
            return_value={"uuid": generate_uuid()},
        )
        location_update = {
            "location_type": WARD_SNOMED,
            "display_name": "John Radcliffe Hospital",
            "parent_location": generate_uuid(),
            "children": [generate_uuid()],
            "ods_code": "12345",
        }
        location_uuid: str = generate_uuid()
        response = client.patch(
            f"/dhos/v1/location/{location_uuid}",
            json=location_update,
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json is not None
        assert "uuid" in response.json
        mock_create.assert_called_with(
            location_uuid=location_uuid, update_details=location_update
        )

    def test_get_locations_gdm(
        self,
        client: FlaskClient,
        mocker: MockerFixture,
        jwt_gdm_admin_uuid: str,
    ) -> None:
        dummy_uuid = generate_uuid()
        mock_get: Mock = mocker.patch.object(
            location_controller,
            "location_search",
            return_value=[{"uuid": dummy_uuid}],
        )
        response = client.get(
            f"/dhos/v1/location/search?product_name=GDM&active=true&compact=true&location_types={WARD_SNOMED}",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json == {dummy_uuid: {"uuid": dummy_uuid}}
        mock_get.assert_called_with(
            ods_code=None,
            location_types=[WARD_SNOMED],
            location_uuids=None,
            product_name=["GDM"],
            active=True,
            compact=True,
            children=False,
        )

    def test_get_locations_send(
        self, client: FlaskClient, mocker: MockerFixture, jwt_send_clinician_uuid: str
    ) -> None:
        dummy_uuid = generate_uuid()
        mock_get: Mock = mocker.patch.object(
            location_controller,
            "location_search",
            return_value=[{"uuid": dummy_uuid}],
        )
        response = client.get(
            f"/dhos/v1/location/search?product_name=SEND&active=true&compact=false&location_types"
            f"={WARD_SNOMED}|22232009&children=true",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json == {dummy_uuid: {"uuid": dummy_uuid}}
        mock_get.assert_called_with(
            ods_code=None,
            location_types=[WARD_SNOMED, "22232009"],
            location_uuids=None,
            product_name=["SEND"],
            active=True,
            compact=False,
            children=True,
        )

    def test_get_locations_all(
        self,
        client: FlaskClient,
        mocker: MockerFixture,
        jwt_system: str,
    ) -> None:
        send_location_uuid: str = generate_uuid()
        gdm_location_uuid: str = generate_uuid()
        common_location_uuid: str = generate_uuid()
        mock_get: Mock = mocker.patch.object(
            location_controller,
            "location_search",
            return_value=[
                {"uuid": send_location_uuid},
                {"uuid": gdm_location_uuid},
                {
                    "uuid": common_location_uuid,
                    "dh_products": [{"product_name": "SEND"}, {"product_name": "GDM"}],
                },
            ],
        )
        response = client.get(
            f"/dhos/v1/location/search?active=null&product_name=SEND&product_name=GDM",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json == {
            send_location_uuid: {"uuid": send_location_uuid},
            gdm_location_uuid: {"uuid": gdm_location_uuid},
            common_location_uuid: {
                "uuid": common_location_uuid,
                "dh_products": [{"product_name": "SEND"}, {"product_name": "GDM"}],
            },
        }
        mock_get.assert_called_with(
            ods_code=None,
            location_types=None,
            location_uuids=None,
            product_name=["SEND", "GDM"],
            active=None,
            compact=False,
            children=False,
        )

    def test_get_locations_all_gdm_only(
        self,
        client: FlaskClient,
        mocker: MockerFixture,
        jwt_system: str,
    ) -> None:
        gdm_location_uuid: str = generate_uuid()
        common_location_uuid: str = generate_uuid()
        mock_get: Mock = mocker.patch.object(
            location_controller,
            "location_search",
            return_value=[
                {"uuid": gdm_location_uuid},
                {
                    "uuid": common_location_uuid,
                    "dh_products": [{"product_name": "GDM"}],
                },
            ],
        )
        response = client.get(
            f"/dhos/v1/location/search?active=null&product_name=GDM",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json == {
            gdm_location_uuid: {"uuid": gdm_location_uuid},
            common_location_uuid: {
                "uuid": common_location_uuid,
                "dh_products": [{"product_name": "GDM"}],
            },
        }
        mock_get.assert_called_with(
            ods_code=None,
            location_types=None,
            location_uuids=None,
            product_name=["GDM"],
            active=None,
            compact=False,
            children=False,
        )

    def test_get_locations_all_send_only(
        self,
        client: FlaskClient,
        mocker: MockerFixture,
        jwt_system: str,
    ) -> None:
        send_location_uuid: str = generate_uuid()
        common_location_uuid: str = generate_uuid()
        mock_get: Mock = mocker.patch.object(
            location_controller,
            "location_search",
            return_value=[
                {"uuid": send_location_uuid},
                {
                    "uuid": common_location_uuid,
                    "dh_products": [{"product_name": "SEND"}],
                },
            ],
        )
        response = client.get(
            f"/dhos/v1/location/search?active=null&product_name=SEND",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json == {
            send_location_uuid: {"uuid": send_location_uuid},
            common_location_uuid: {
                "uuid": common_location_uuid,
                "dh_products": [{"product_name": "SEND"}],
            },
        }
        mock_get.assert_called_with(
            ods_code=None,
            location_types=None,
            location_uuids=None,
            product_name=["SEND"],
            active=None,
            compact=False,
            children=False,
        )

    @pytest.mark.parametrize(
        "jwt_scopes,expected_success",
        [
            (["read:send_location", "read:location_by_ods"], True),
            (["read:send_location"], False),
        ],
    )
    def test_get_locations_ods_code(
        self,
        client: FlaskClient,
        mocker: MockerFixture,
        jwt_send_clinician_uuid: str,
        expected_success: bool,
    ) -> None:
        dummy_uuid = generate_uuid()
        mock_get: Mock = mocker.patch.object(
            location_controller,
            "location_search",
            return_value=[{"uuid": dummy_uuid}],
        )
        response = client.get(
            f"/dhos/v1/location/search?ods_code=12345abcde&active=null",
            headers={"Authorization": "Bearer TOKEN"},
        )
        if expected_success:
            assert response.status_code == 200
            assert response.json is not None
            assert response.json == {dummy_uuid: {"uuid": dummy_uuid}}
            mock_get.assert_called_with(
                ods_code="12345abcde",
                location_types=None,
                location_uuids=None,
                product_name=None,
                children=False,
                active=None,
                compact=False,
            )
        else:
            assert response.status_code == 403
            assert mock_get.call_count == 0

    def test_get_location_by_uuid(
        self,
        client: FlaskClient,
        mocker: MockerFixture,
        jwt_gdm_admin_uuid: str,
    ) -> None:
        location_uuid: str = generate_uuid()
        mock_get: Mock = mocker.patch.object(
            location_controller,
            "get_location_by_uuid",
            return_value={"uuid": location_uuid},
        )
        response = client.get(
            f"/dhos/v1/location/{location_uuid}?children=true",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["uuid"] == location_uuid
        mock_get.assert_called_with(location_uuid=location_uuid, children=True)

    def test_get_location_by_uuid_and_type(
        self, client: FlaskClient, mocker: MockerFixture, jwt_system: str
    ) -> None:
        location_uuid: str = generate_uuid()
        mock_get: Mock = mocker.patch.object(
            location_controller,
            "get_location_by_type",
            return_value={"uuid": location_uuid},
        )
        response = client.get(
            f"/dhos/v1/location/{location_uuid}?return_parent_of_type={WARD_SNOMED}",
            headers={"Authorization": "Bearer TOKEN"},
        )
        assert response.status_code == 200
        assert response.json is not None
        assert response.json["uuid"] == location_uuid
        mock_get.assert_called_with(
            location_uuid=location_uuid, location_type=WARD_SNOMED
        )

    @pytest.mark.parametrize(
        "method,endpoint",
        [("post", "/dhos/v1/location"), ("patch", "/dhos/v1/location/12345")],
    )
    def test_post_endpoints_missing_body(
        self, client: FlaskClient, method: str, endpoint: str
    ) -> None:
        method_callable: Callable = getattr(client, method)
        response = method_callable(endpoint, headers={"Authorization": "Bearer TOKEN"})
        assert response.status_code == 400

    @pytest.mark.parametrize(
        "qs,called_with",
        [
            (
                "compact=true&children=true",
                {
                    "compact": True,
                    "children": True,
                },
            ),
            (
                "",
                {},
            ),
            (
                "ods_code=4444&location_types=225746001|225730009",
                {"ods_code": "4444", "location_types": ["225746001", "225730009"]},
            ),
            (
                "ods_code=4444&location_types=225746001|225730009&active=false&product_name=SEND",
                {
                    "ods_code": "4444",
                    "location_types": ["225746001", "225730009"],
                    "active": False,
                    "product_name": ["SEND"],
                },
            ),
        ],
        ids=["compact-and-children", "no-args", "ods-and-types", "ods-type-product"],
    )
    def test_post_search_locations(
        self,
        client: FlaskClient,
        mocker: MockerFixture,
        jwt_system: str,
        qs: str,
        called_with: Dict,
    ) -> None:
        location_uuids: List[str] = [generate_uuid() for _ in range(5)]
        expected = {
            "ods_code": None,
            "location_types": None,
            "product_name": None,
            "active": None,
            "children": False,
            "compact": False,
            "location_uuids": location_uuids,
        }
        expected.update(called_with)
        mock_get: Mock = mocker.patch.object(
            location_controller,
            "location_search",
            return_value=[{"uuid": u} for u in location_uuids[:4]],
        )
        response = client.post(
            f"/dhos/v1/location/search?{qs}",
            headers={"Authorization": "Bearer TOKEN"},
            json=location_uuids,
        )
        assert response.status_code == 200
        assert response.json is not None
        assert len(response.json.keys()) == 5
        # One of the locations was not found, check it's still in the response.
        assert response.json[location_uuids[-1]] is None
        mock_get.assert_called_with(**expected)

    @pytest.mark.parametrize(
        "qs,called_with",
        [
            (
                "compact=true&children=true",
                {
                    "compact": True,
                    "children": True,
                },
            ),
            (
                "",
                {},
            ),
            (
                "ods_code=4444&location_types=225746001|225730009",
                {"ods_code": "4444", "location_types": ["225746001", "225730009"]},
            ),
            (
                "ods_code=4444&location_types=225746001|225730009&active=true&product_name=SEND",
                {
                    "ods_code": "4444",
                    "location_types": ["225746001", "225730009"],
                    "active": True,
                    "product_name": ["SEND"],
                },
            ),
        ],
    )
    @pytest.mark.parametrize(
        "jwt_scopes", [["read:gdm_location", "read:location_by_ods"]]
    )
    def test_get_search_locations(
        self,
        client: FlaskClient,
        mocker: MockerFixture,
        jwt_system: str,
        qs: str,
        called_with: Dict,
    ) -> None:
        location_uuids: List[str] = [generate_uuid() for _ in range(5)]
        expected = {
            "ods_code": None,
            "location_types": None,
            "product_name": None,
            "active": None,
            "children": False,
            "compact": False,
            "location_uuids": location_uuids,
        }
        expected.update(called_with)
        mock_get: Mock = mocker.patch.object(
            location_controller,
            "location_search",
            return_value=[{"uuid": u} for u in location_uuids[:4]],
        )
        response = client.get(
            f"/dhos/v1/location/search?{qs}",
            headers={
                "Authorization": "Bearer TOKEN",
                "X-Location-Ids": ",".join(location_uuids),
            },
        )
        assert response.status_code == 200
        assert response.json is not None
        assert len(response.json.keys()) == 5
        # One of the locations was not found, check it's still in the response.
        assert response.json[location_uuids[-1]] is None
        mock_get.assert_called_with(**expected)

    @pytest.mark.parametrize(
        "qs,expected_status",
        [
            ("compact=42", 400),
            ("compact=true", 200),
            ("product_name=", 400),
            ("location_types=999999999", 400),
            ("ods_code=4444&location_types=225746001|225730009", 403),
            ("ods_code=4444&product_name=GDM", 403),
        ],
    )
    @pytest.mark.parametrize("method", ["get", "post"])
    @pytest.mark.parametrize("jwt_scopes", [["read:gdm_location"]])
    def test_search_locations_validation(
        self,
        client: FlaskClient,
        jwt_system: str,
        qs: str,
        method: str,
        expected_status: int,
    ) -> None:
        response = getattr(client, method)(
            f"/dhos/v1/location/search?{qs}",
            headers={
                "Authorization": "Bearer TOKEN",
            },
        )
        assert response.status_code == expected_status
