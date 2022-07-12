from typing import Dict, Iterable, List, Optional, Tuple, Union

from flask_batteries_included.helpers.error_handler import (
    DuplicateResourceException,
    EntityNotFoundException,
)
from flask_batteries_included.sqldb import db
from sqlalchemy import and_, bindparam, func, literal_column, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query, aliased, joinedload
from sqlalchemy.sql.functions import coalesce
from sqlalchemy.sql.selectable import CTE

from dhos_locations_api.models.location import Location
from dhos_locations_api.models.location_product import LocationProduct


def create_location(location_details: Dict) -> Dict:
    loc = Location.new(**location_details)
    ods_code = loc.ods_code
    _safe_commit(ods_code)
    return loc.to_dict(include_parents=True)


def create_many_locations(location_list: List[Dict]) -> Dict:
    try:
        for details in location_list:
            Location.new(**details)

        db.session.commit()
    except IntegrityError as e:
        err_msg = str(e)
        if 'unique constraint "ix_location_ods_code"' in err_msg:
            raise DuplicateResourceException(
                "duplicate ods_code creating locations"
            ) from e
        raise
    return {"created": len(location_list)}


def _safe_commit(ods_code: str) -> None:
    try:
        db.session.commit()
    except IntegrityError as e:
        err_msg = str(e)
        if 'unique constraint "ix_location_ods_code"' in err_msg:
            raise DuplicateResourceException(
                f"location with ods code '{ods_code}' already exists"
            ) from e
        raise


def update_location(location_uuid: str, update_details: Dict) -> Dict:
    location: Location = Location.query.get(location_uuid)
    location.update(**update_details)
    _safe_commit(location.ods_code)
    return location.to_dict(include_parents=True)


def get_locations_by_uuids(
    location_uuids: List[str] = None,
    product_name: Optional[str] = None,
    active: Optional[bool] = True,
    compact: bool = True,
    children: bool = False,
) -> List[Dict]:
    return location_search(
        location_uuids=location_uuids,
        product_name=product_name,
        active=active,
        compact=compact,
        children=children,
    )


def location_search(
    location_uuids: List[str] = None,
    product_name: Union[str, List[str]] = None,
    active: Optional[bool] = None,
    ods_code: str = None,
    location_types: Optional[List[str]] = None,
    compact: bool = True,
    children: bool = False,
) -> List[Dict]:
    if isinstance(product_name, list) and len(product_name) == 1:
        product_name = product_name[0]

    if children:
        query = query_child_uuids(location_uuids, product_name)
    else:
        query = Location.query.add_columns(literal_column("NULL").label("children"))

    if product_name:
        query = query.join(
            LocationProduct,
            and_(
                LocationProduct.location_uuid == Location.uuid,
                LocationProduct.product_name.in_(
                    bindparam("product_name", expanding=True)
                )
                if isinstance(product_name, list)
                else LocationProduct.product_name == bindparam("product_name"),
            ),
        )
    elif not compact:
        query = query.options(joinedload(Location.dh_products))

    params = {
        "location_types": location_types,
        "location_uuids": location_uuids,
        "product_name": product_name,
        "active": active,
        "ods_code": ods_code,
    }

    uuid_filter = (
        True
        if location_uuids is None
        else Location.uuid.in_(bindparam("location_uuids", expanding=True))
    )

    query = query.filter(
        uuid_filter,
        Location.active == bindparam("active") if active is not None else True,
        Location.ods_code == bindparam("ods_code") if ods_code else True,
        Location.location_type.in_(bindparam("location_types", expanding=True))
        if location_types is not None
        else True,
    )

    result: Iterable[Tuple[Location, Optional[List[str]]]] = query.params(**params)
    locations = [
        location.to_dict(compact=compact, child_location_uuids=child_uuids)
        for location, child_uuids in result
    ]
    fixup_parents(locations)
    return locations


def fixup_parents(locations: List[Dict]) -> None:
    """The parent list in a location is a possibly nested list of parent locations.
    As there are comparatively few parent locations it makes sense to fetch them in a separate query
    instead of complicating the main location search.
    """
    parent_uuids = {location["parent"] for location in locations if location["parent"]}

    query: Query = db.session.query(
        Location.uuid,
        Location.parent_id,
        Location.location_type,
        Location.ods_code,
        Location.display_name,
        Location.score_system_default,
    ).filter(Location.uuid.in_(bindparam("parent_uuids", expanding=True)))

    parent_query: CTE = query.cte(name="locations", recursive=True)
    child_alias = aliased(parent_query, name="c")
    location_alias = aliased(Location, name="l")
    q2 = db.session.query(
        child_alias.c.parent_id,
        location_alias.parent_id,
        location_alias.location_type,
        location_alias.ods_code,
        location_alias.display_name,
        location_alias.score_system_default,
    ).filter(child_alias.c.parent_id == location_alias.uuid)

    parent_query = parent_query.union_all(q2)
    parent_maps: Dict[str, Dict] = {
        uuid: {
            "uuid": uuid,
            "parent": parent,
            "location_type": location_type,
            "ods_code": ods_code,
            "display_name": display_name,
            "score_system_default": score_system_default,
        }
        for uuid, parent, location_type, ods_code, display_name, score_system_default in db.session.query(
            parent_query.params({"parent_uuids": list(parent_uuids)})
        )
    }
    # Parents can have parents, convert parent uuids to parent dicts.
    for location in parent_maps.values():
        parent_uuid = location["parent"]
        if parent_uuid:
            location["parent"] = parent_maps[parent_uuid]
        # Remove the score_system_default if it's not set (to reduce clutter)
        if location["score_system_default"] is None:
            del location["score_system_default"]

    # Now fix up the original locations.
    for location in locations:
        parent_uuid = location["parent"]
        if parent_uuid:
            location["parent"] = parent_maps[parent_uuid]


def query_child_uuids(
    location_uuids: Optional[List[str]], product_name: Union[str, List[str], None]
) -> Query:
    query: Query = db.session.query(Location.parent_id, Location.uuid)
    if location_uuids is not None:
        query = query.filter(
            Location.parent_id.in_(bindparam("location_uuids", expanding=True))
        )
    if product_name:
        query = query.join(
            LocationProduct,
            and_(
                LocationProduct.location_uuid == Location.uuid,
                LocationProduct.product_name.in_(
                    bindparam("product_name", expanding=True)
                )
                if isinstance(product_name, list)
                else LocationProduct.product_name == bindparam("product_name"),
            ),
        )
    child_locations: CTE = query.cte(name="child_locations", recursive=True)
    parent_alias = aliased(child_locations, name="p")
    location_alias = aliased(Location, name="l")

    q2 = db.session.query(
        parent_alias.c.parent_id,
        location_alias.uuid,
    ).filter(location_alias.parent_id == parent_alias.c.uuid)

    if product_name:
        q2 = q2.join(
            LocationProduct,
            and_(
                LocationProduct.location_uuid == location_alias.uuid,
                LocationProduct.product_name.in_(
                    bindparam("product_name", expanding=True)
                )
                if isinstance(product_name, list)
                else LocationProduct.product_name == bindparam("product_name"),
            ),
        )
    child_locations = child_locations.union_all(q2)
    c2: CTE = (
        db.session.query(
            child_locations.c.parent_id,
            func.array_agg(child_locations.c.uuid).label("children"),
        )
        .order_by(child_locations.c.parent_id)
        .group_by(child_locations.c.parent_id)
        .cte(name="c2")
    )
    query = db.session.query(Location, coalesce(c2.c.children, [])).outerjoin(
        c2, Location.uuid == c2.c.parent_id
    )
    return query


def get_location_by_uuid(
    location_uuid: str, children: bool = False, compact: bool = False
) -> Dict:
    locations = location_search(
        location_uuids=[location_uuid], children=children, compact=compact
    )
    if locations:
        return locations[0]
    raise EntityNotFoundException(f"Location {location_uuid} not found")


def _get_parent_location(location_uuid: str, location_type: str) -> Optional[Location]:
    parent_locations: CTE = (
        db.session.query(Location.uuid, Location.parent_id, Location.location_type)
        .filter(Location.uuid == location_uuid)
        .cte(name="parent_locations", recursive=True)
    )
    child_alias = aliased(parent_locations, name="c")
    location_alias = aliased(Location, name="l")
    parent_locations = parent_locations.union_all(
        db.session.query(
            location_alias.uuid,
            location_alias.parent_id,
            location_alias.location_type,
        ).filter(location_alias.uuid == child_alias.c.parent_id)
    )

    p2: CTE = (
        db.session.query(parent_locations)
        .filter(parent_locations.c.location_type == location_type)
        .cte(name="p2")
    )

    query = Location.query.options(joinedload(Location.dh_products)).filter(
        Location.uuid.in_(select([p2.c.uuid]))
    )
    result = query.first()
    return result


def get_location_by_type(location_uuid: str, location_type: str) -> Dict:
    location: Optional[Location] = _get_parent_location(
        location_uuid=location_uuid, location_type=location_type
    )
    if not location:
        raise ValueError(
            f"This location has no parent location of type {location_type}"
        )
    location_dict: Dict = location.to_dict(include_parents=True)
    return location_dict
