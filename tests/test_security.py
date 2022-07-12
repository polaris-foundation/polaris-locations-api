import pytest
from flask import g

from dhos_locations_api.helpers.security import get_clinician_locations


@pytest.mark.usefixtures("app", "mock_bearer_validation")
class TestSecurityApi:
    def test_get_clinician_locations_none(self) -> None:
        g.jwt_scopes = "read:gdm_location"
        assert [] == get_clinician_locations()

    def test_get_clinician_locations_empty(self) -> None:
        g.jwt_scopes = "read:gdm_location read:location_all"
        assert None == get_clinician_locations()
