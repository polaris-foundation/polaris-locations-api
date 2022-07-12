from typing import Any, Dict, List, Optional, Sequence

from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.sqldb import ModelIdentifier, db

from dhos_locations_api.models.address import AddressMixin
from dhos_locations_api.models.location_product import LocationProduct

_MARKER: Any = object()


class Location(ModelIdentifier, AddressMixin, db.Model):
    uuid = db.Column(
        db.String(length=36),
        unique=True,
        nullable=False,
        primary_key=True,
    )
    location_type = db.Column(db.String, nullable=True)
    ods_code = db.Column(db.String, nullable=True, unique=True, index=True)
    display_name = db.Column(db.String, nullable=False)
    active = db.Column(db.Boolean, default=True)
    parent_id = db.Column(db.String(length=36), db.ForeignKey("location.uuid"))
    score_system_default = db.Column(db.String, nullable=True)

    dh_products = db.relationship(
        "LocationProduct",
        primaryjoin="Location.uuid == LocationProduct.location_uuid",
        backref="location",
    )
    children = db.relationship(
        "Location", backref=db.backref("parent", remote_side=[uuid])
    )

    @property
    def created_by(self) -> str:
        return self.created_by_

    @created_by.setter
    def created_by(self, value: str) -> None:
        self.created_by_ = value

    @property
    def modified_by(self) -> str:
        return self.modified_by_

    @modified_by.setter
    def modified_by(self, value: str) -> None:
        self.modified_by_ = value

    @classmethod
    def new(
        cls,
        uuid: str = None,
        dh_products: Sequence[Dict] = (),
        parent: Optional[str] = None,
        parent_ods_code: Optional[str] = None,
        **kw: Any,
    ) -> "Location":
        if not uuid:
            uuid = generate_uuid()

        # If parent_ods_code field was provided in the request and is not None,
        # ensure it exists and add it to the parents list.
        if parent_ods_code:
            parent_obj = (
                Location.query.with_entities(Location.uuid)
                .filter(Location.ods_code == parent_ods_code)
                .first()
            )
            if parent_obj is None:
                raise ValueError(
                    f"Parent location with ods_code {parent_ods_code} not found"
                )

            if parent and parent_obj.uuid != parent:
                raise ValueError("Location may only have one parent")

            parent = parent_obj.uuid

        location = Location(
            uuid=uuid,
            parent_id=parent,
            **kw,
        )

        db.session.add(location)

        if dh_products:
            for prod in dh_products:
                LocationProduct.new(location_uuid=location.uuid, **prod)

        return location

    @classmethod
    def schema(cls) -> Dict:
        return {
            "optional": {
                "parent": str,
                "address_line_1": str,
                "address_line_2": str,
                "address_line_3": str,
                "address_line_4": str,
                "postcode": str,
                "country": str,
                "locality": str,
                "region": str,
                "active": bool,
                "parent_ods_code": str,
                "score_system_default": str,
            },
            "required": {
                "dh_products": [dict],
                "location_type": str,
                "ods_code": str,
                "display_name": str,
            },
            "updatable": {
                "parent_location": [str],
                "ods_code": str,
                "display_name": str,
                "address_line_1": str,
                "address_line_2": str,
                "address_line_3": str,
                "address_line_4": str,
                "postcode": str,
                "country": str,
                "location_type": str,
                "locality": str,
                "region": str,
                "dh_products": [dict],
                "active": bool,
                "score_system_default": str,
            },
        }

    def to_dict(
        self,
        compact: bool = False,
        child_location_uuids: Optional[List[str]] = None,
        include_parents: bool = False,
    ) -> Dict:
        compact_dict = self.to_compact_dict(
            child_location_uuids=child_location_uuids,
        )
        if compact:
            return compact_dict

        location: Dict[str, Any] = {
            "dh_products": [p.to_dict() for p in self.dh_products],
            **compact_dict,
            **self.pack_address(),
            **self.pack_identifier(),
        }

        if include_parents:
            current: Dict = location
            current["parent"] = None
            parent = self.parent
            while parent is not None:
                current["parent"] = {
                    "uuid": parent.uuid,
                    "parent": None,
                    "ods_code": parent.ods_code,
                    "display_name": parent.display_name,
                    "location_type": parent.location_type,
                }
                if parent.score_system_default:
                    current["parent"][
                        "score_system_default"
                    ] = parent.score_system_default

                current, parent = current["parent"], parent.parent

        return location

    def to_compact_dict(
        self,
        child_location_uuids: Optional[List[str]] = None,
    ) -> Dict:
        location = {
            "location_type": self.location_type,
            "ods_code": self.ods_code,
            "display_name": self.display_name,
            "active": self.active,
            "uuid": self.uuid,
            "parent": self.parent_id,
        }

        if child_location_uuids is not None:
            location["children"] = child_location_uuids

        if self.score_system_default:
            location["score_system_default"] = self.score_system_default

        return location

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.ods_code}:{self.display_name}>"

    def update(
        self,
        parent_location: Optional[List[str]] = _MARKER,
        dh_products: List[Dict] = None,
        **kw: Any,
    ) -> None:
        if parent_location is not _MARKER:
            if self.uuid == parent_location:
                raise ValueError("Location cannot have itself as a parent")

            self.parent_id = parent_location

        if dh_products:
            for product in dh_products:
                if isinstance(product, Dict):
                    if "uuid" in product:
                        LocationProduct.query.get(product["uuid"]).update(**product)
                    else:
                        if product.get("closed_date", None) is None:
                            if any(
                                p.product_name == product["product_name"]
                                and p.closed_date is None
                                for p in self.dh_products
                            ):
                                raise ValueError("Cannot add duplicate open product")
                        self.dh_products.append(LocationProduct.new(**product))
                else:
                    raise TypeError("Location.dh_products")

        for key, key_type in self.schema()["updatable"].items():
            if key in kw:
                value = kw[key]
                if not isinstance(value, key_type):
                    raise TypeError(f"LocationProduct.{key}")
                setattr(self, key, value)
