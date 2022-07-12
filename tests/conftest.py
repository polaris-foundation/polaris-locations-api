import contextlib
import itertools
import json
import os
import re
import signal
import socket
import sys
import time
from datetime import datetime, timezone
from functools import partial
from typing import (
    Any,
    Callable,
    ContextManager,
    Dict,
    Generator,
    Iterator,
    List,
    NoReturn,
    Optional,
    Tuple,
    Type,
    Union,
)
from urllib.parse import urlparse

import draymed
import pytest
import sqlalchemy
from _pytest.config import Config
from flask import Flask, g
from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.sqldb import (
    database_connectivity_test,
    database_version_test,
    db,
)
from flask_sqlalchemy import SQLAlchemy
from marshmallow import RAISE, Schema
from mock import Mock
from pytest_mock import MockerFixture, MockFixture
from sqlalchemy.orm import Session

#####################################################
# Configuration to use database started by tox-docker
#####################################################
from dhos_locations_api.models.location import Location
from dhos_locations_api.models.location_product import LocationProduct

ods_counter = itertools.count(start=1000)


def pytest_configure(config: Config) -> None:
    for env_var, tox_var in [
        ("DATABASE_HOST", "POSTGRES_HOST"),
        ("DATABASE_PORT", "POSTGRES_5432_TCP_PORT"),
    ]:
        if tox_var in os.environ:
            os.environ[env_var] = os.environ[tox_var]

    import logging

    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.DEBUG if os.environ.get("SQLALCHEMY_ECHO") else logging.WARNING
    )


def pytest_report_header(config: Config) -> str:
    db_config = (
        f"{os.environ['DATABASE_HOST']}:{os.environ['DATABASE_PORT']}"
        if os.environ.get("DATABASE_PORT")
        else "Sqlite"
    )
    return f"SQL database: {db_config}"


def _wait_for_it(service: str, timeout: int = 30) -> None:
    url = urlparse(service, scheme="http")

    host = url.hostname
    port = url.port or (443 if url.scheme == "https" else 80)

    friendly_name = f"{host}:{port}"

    def _handle_timeout(signum: Any, frame: Any) -> NoReturn:
        print(f"timeout occurred after waiting {timeout} seconds for {friendly_name}")
        sys.exit(1)

    if timeout > 0:
        signal.signal(signal.SIGALRM, _handle_timeout)
        signal.alarm(timeout)
        print(f"waiting {timeout} seconds for {friendly_name}")
    else:
        print(f"waiting for {friendly_name} without a timeout")

    t1 = time.time()

    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s = sock.connect_ex((host, port))
            if s == 0:
                seconds = round(time.time() - t1)
                print(f"{friendly_name} is available after {seconds} seconds")
                break
        except socket.gaierror:
            pass
        finally:
            time.sleep(1)

    signal.alarm(0)


#########################################################
# End Configuration to use database started by tox-docker
#########################################################


@pytest.fixture(scope="session")
def session_app() -> Flask:
    import dhos_locations_api.app

    _wait_for_it(f"//{os.environ['DATABASE_HOST']}:{os.environ['DATABASE_PORT']}")

    app = dhos_locations_api.app.create_app(testing=True)
    with app.app_context():
        db.drop_all()
        db.create_all()

    return app


@pytest.fixture(scope="session")
def _db(session_app: Flask) -> SQLAlchemy:
    """
    Provide the transactional fixtures with access to the database via a Flask-SQLAlchemy
    database connection.
    """
    db = SQLAlchemy(app=session_app)

    return db


@pytest.fixture
def app(mocker: MockFixture, session_app: Flask) -> Flask:
    from flask_batteries_included.helpers.security import _ProtectedRoute

    def mock_claims(self: Any, verify: bool = True) -> Tuple:
        return g.jwt_claims, g.jwt_scopes

    mocker.patch.object(_ProtectedRoute, "_retrieve_jwt_claims", mock_claims)
    session_app.config["IGNORE_JWT_VALIDATION"] = False
    return session_app


@pytest.fixture
def app_context(app: Flask) -> Generator[None, None, None]:
    with app.app_context():
        yield


@pytest.fixture
def uses_sql_database(_db: SQLAlchemy) -> None:
    LocationProduct.query.delete()
    Location.query.delete()
    _db.session.commit()
    _db.drop_all()
    _db.create_all()


@pytest.fixture
def jwt_user_type() -> str:
    "parametrize to 'clinician', 'patient', or None as appropriate"
    return "clinician"


@pytest.fixture
def clinician() -> str:
    """pytest-dhos:
    jwt_send_clinician_uuid/jwt_send_admin_uuid fixtures expect this for the uuid."""
    return generate_uuid()


@pytest.fixture
def gdm_clinician() -> str:
    """pytest-dhos:
    jwt_gdm_clinician_uuid/jwt_gdm_admin_uuid fixtures expect this for the uuid."""
    return generate_uuid()


@pytest.fixture
def jwt_scopes() -> Optional[Dict]:
    "parametrize to scopes required by a test"
    return None


@pytest.fixture
def jwt_extra_claims() -> Dict:
    return {"can_edit_spo2_scale": True}


@pytest.fixture
def mock_bearer_validation(mocker: MockerFixture) -> Mock:
    from jose import jwt

    mocked = mocker.patch.object(jwt, "get_unverified_claims")
    mocked.return_value = {
        "sub": "1234567890",
        "name": "John Doe",
        "iat": 1_516_239_022,
        "iss": "http://localhost/",
    }
    return mocked


class DBStatementCounter(object):
    def __init__(self, limit: int = None) -> None:
        self.clauses: List[sqlalchemy.sql.ClauseElement] = []
        self.limit = limit

    @property
    def count(self) -> int:
        return len(self.clauses)

    def callback(
        self,
        conn: sqlalchemy.engine.Connection,
        clauseelement: sqlalchemy.sql.ClauseElement,
        multiparams: List[Dict],
        params: Dict,
        execution_options: Optional[Dict],
    ) -> None:
        if isinstance(clauseelement, sqlalchemy.sql.elements.SavepointClause):
            return

        self.clauses.append(clauseelement)
        if self.limit:
            assert (
                len(self.clauses) <= self.limit
            ), f"Too many SQL statements (limit was {self.limit})"


@contextlib.contextmanager
def db_statement_counter(
    limit: int = None, session: Session = None
) -> Iterator[DBStatementCounter]:
    if session is None:
        session = db.session
    counter = DBStatementCounter(limit=limit)
    cb = counter.callback
    sqlalchemy.event.listen(db.engine, "before_execute", cb)
    try:
        yield counter
    finally:
        sqlalchemy.event.remove(db.engine, "before_execute", cb)


@pytest.fixture
def statement_counter() -> Callable[[Session], ContextManager[DBStatementCounter]]:
    return db_statement_counter


@pytest.fixture
def location_factory(uses_sql_database: None) -> Callable[..., str]:
    def location(
        display_name: str,
        ods_code: str = None,
        location_type: str = draymed.codes.code_from_name("ward", "location"),
        product_name: Union[str, List[str]] = "SEND",
        opened_date: datetime = None,
        parent: str = None,
        **kw: Any,
    ) -> Location:
        if ods_code is None:
            ods_code = f"ods-{next(ods_counter)}"

        if opened_date is None:
            opened_date = datetime.now(tz=timezone.utc)
        if isinstance(product_name, str):
            product_name = [product_name]

        loc: Location = Location.new(
            dh_products=[
                {
                    "product_name": p,
                    "opened_date": opened_date.isoformat(timespec="milliseconds"),
                }
                for p in product_name
            ],
            location_type=location_type,
            ods_code=ods_code,
            display_name=display_name,
            parent=parent,
            **kw,
        )
        db.session.commit()
        return loc.uuid

    return location


@pytest.fixture
def hospital_factory(location_factory: Callable[..., str]) -> Callable[..., str]:
    HOSPITAL_SNOMED: str = draymed.codes.code_from_name("hospital", "location")
    hospital = partial(location_factory, location_type=HOSPITAL_SNOMED)
    return hospital


@pytest.fixture
def ward_factory(location_factory: Callable[..., str]) -> Callable[..., str]:
    WARD_SNOMED: str = draymed.codes.code_from_name("ward", "location")
    ward = partial(location_factory, location_type=WARD_SNOMED)
    return ward


@pytest.fixture
def bay_factory(location_factory: Callable[..., str]) -> Callable[..., str]:
    BAY_SNOMED: str = draymed.codes.code_from_name("bay", "location")
    bay = partial(location_factory, location_type=BAY_SNOMED)
    return bay


@pytest.fixture
def bed_factory(location_factory: Callable[..., str]) -> Callable[..., str]:
    BED_SNOMED: str = draymed.codes.code_from_name("bed", "location")
    bed = partial(location_factory, location_type=BED_SNOMED)
    return bed


@pytest.fixture
def send_hospital_uuid(hospital_factory: Callable[..., str]) -> str:
    return hospital_factory(
        ods_code="Frideswide",
        parent=None,
        product_name="SEND",
        active=True,
        address_line_1="Oxford ave",
        display_name="St Frideswide Hospital",
    )


@pytest.fixture
def gdm_hospital_uuid(hospital_factory: Callable[..., str]) -> str:
    return hospital_factory(
        ods_code="Edmund",
        parent=None,
        product_name="GDM",
        active=True,
        address_line_1="Abingdon Road",
        display_name="St Edmund Hospital",
    )


@pytest.fixture
def ward_uuids(ward_factory: Callable, send_hospital_uuid: str) -> List[str]:
    apple = ward_factory("Apple", parent=send_hospital_uuid)
    orange = ward_factory("Orange", parent=send_hospital_uuid)
    lemon = ward_factory("Lemon", parent=send_hospital_uuid)
    lime = ward_factory("Lime", parent=send_hospital_uuid)
    return [apple, orange, lemon, lime]


class _Anything:
    def __init__(
        self, _type: Optional[Type] = None, regex: Optional[str] = None
    ) -> None:
        self._type = _type
        self._pattern = regex

    def __eq__(self, other: Any) -> bool:
        # print(f"{self}=={repr(other)}")
        if self._type is not None:
            return isinstance(other, self._type)
        if self._pattern is not None and isinstance(other, str):
            return re.fullmatch(self._pattern, other) is not None
        return True

    def __repr__(self) -> str:
        if self._pattern:
            match = f" matching {self._pattern}"
        else:
            match = ""
        if self._type is not None:
            return f"<Any {str(self._type.__name__)}{match}>"
        else:
            return f"<Anything{match}>"


@pytest.fixture
def any() -> _Anything:
    return _Anything()


@pytest.fixture
def any_string() -> _Anything:
    return _Anything(str)


@pytest.fixture
def any_datetime() -> _Anything:
    return _Anything(datetime)


@pytest.fixture
def any_datetime_string() -> _Anything:
    return _Anything(str, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}.*")


@pytest.fixture
def any_date_string() -> _Anything:
    return _Anything(str, r"\d{4}-\d{2}-\d{2}")


@pytest.fixture
def any_name() -> _Anything:
    return _Anything(str, regex=r"\w+")


@pytest.fixture
def any_phone() -> _Anything:
    return _Anything(str, regex=r"[\d\(\)\-\+]+")


@pytest.fixture
def any_smartcard() -> _Anything:
    return _Anything(str, regex=r"\@\d+")


@pytest.fixture
def any_digits() -> _Anything:
    return _Anything(str, regex=r"\d+")


@pytest.fixture
def any_uuid() -> _Anything:
    return _Anything(
        str,
        regex=r"[[:xdigit:]]{8}-[[:xdigit:]]{4}-[[:xdigit:]]{4}-[[:xdigit:]]{4]-[[:xdigit:]]{12}",
    )


@pytest.fixture
def assert_valid_schema(
    app: Flask,
) -> Callable[[Type[Schema], Union[Dict, List], bool], None]:
    def verify_schema(
        schema: Type[Schema], value: Union[Dict, List], many: bool = False
    ) -> None:
        # Roundtrip through JSON to convert datetime values to strings.
        serialised = json.loads(json.dumps(value, cls=app.json_encoder))
        schema().load(serialised, many=many, unknown=RAISE)

    return verify_schema
