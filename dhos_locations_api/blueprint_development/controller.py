# -*- coding: utf-8 -*-
from typing import Sequence

from flask_batteries_included.sqldb import db
from she_logging.logging import logger

from dhos_locations_api.models.location import Location
from dhos_locations_api.models.location_product import LocationProduct

ALL_MODELS: Sequence[db.Model] = [LocationProduct, Location]


def reset_database() -> None:
    """Drops SQL data"""
    try:
        for model in ALL_MODELS:
            db.session.query(model).delete()
        db.session.commit()
    except Exception:
        logger.exception("Drop SQL data failed")
        db.session.rollback()
