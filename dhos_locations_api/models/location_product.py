from datetime import date, datetime
from typing import Any, Dict, Union

from flask_batteries_included.helpers import generate_uuid
from flask_batteries_included.sqldb import ModelIdentifier, db
from sqlalchemy import func


class LocationProduct(ModelIdentifier, db.Model):
    uuid = db.Column(
        db.String(length=36),
        unique=True,
        nullable=False,
        primary_key=True,
    )
    product_name = db.Column(db.String, nullable=False)
    opened_date = db.Column(
        db.Date(),
        unique=False,
        nullable=False,
        default=func.now(),
    )
    closed_date = db.Column(
        db.Date(),
        unique=False,
        nullable=True,
    )
    location_uuid = db.Column(db.String(length=36), db.ForeignKey("location.uuid"))
    closed_reason = db.Column(db.String)
    closed_reason_other = db.Column(db.String)

    @classmethod
    def new(cls, uuid: str = None, **kw: Any) -> "LocationProduct":
        if not uuid:
            uuid = generate_uuid()

        product = LocationProduct(uuid=uuid, **kw)
        db.session.add(product)
        return product

    @classmethod
    def schema(cls) -> Dict[str, Dict[str, type]]:
        return {
            "optional": {
                "closed_date": date,
                "closed_reason": str,
                "closed_reason_other": str,
            },
            "required": {"product_name": str, "opened_date": date},
            "updatable": {
                "product_name": str,
                "opened_date": date,
                "closed_date": date,
                "closed_reason": str,
                "closed_reason_other": str,
            },
        }

    def to_compact_dict(self) -> Dict[str, Union[str, datetime, None]]:
        return {
            "product_name": self.product_name,
            "opened_date": self.opened_date,
            "closed_date": self.closed_date,
            "created": self.created,
            "uuid": self.uuid,
        }

    to_dict = to_compact_dict

    def update(self, product_name: str, **kw: Any) -> None:
        if product_name != self.product_name:
            for prod in self.location.dh_products:
                if (
                    prod is not self
                    and prod.product_name == product_name
                    and prod.closed_date is None
                ):
                    raise ValueError(f"Location is already active on {product_name}")
            self.product_name = product_name

        for key, key_type in self.schema()["updatable"].items():
            if key in kw:
                value = kw[key]
                if not isinstance(value, key_type):
                    raise TypeError(f"LocationProduct.{key}")
                setattr(self, key, value)

        db.session.add(self)
