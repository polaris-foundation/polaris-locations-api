import draymed
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from flask_batteries_included.helpers.apispec import (
    FlaskBatteriesPlugin,
    Identifier,
    initialise_apispec,
    openapi_schema,
)
from marshmallow import EXCLUDE, Schema, fields, validate

PRODUCT_UUID_DESCRIPTION = "UUID of the product the encounter is associated with"

dhos_locations_api_spec: APISpec = APISpec(
    version="1.0.0",
    openapi_version="3.0.3",
    title="DHOS Locations API",
    info={
        "description": "A service for storing information about locations (Hospitals, Wards, Bays and Beds)"
    },
    plugins=[FlaskPlugin(), MarshmallowPlugin(), FlaskBatteriesPlugin()],
)

initialise_apispec(dhos_locations_api_spec)


class LocationProductRequest(Schema):
    class Meta:
        ordered = True

    product_name = fields.String(
        required=True, metadata={"description": "The product name", "example": "GDM"}
    )
    opened_date = fields.Date(
        required=True,
        metadata={
            "description": "ISO8601 date for when product was opened for the location",
            "example": "2020-01-01",
        },
    )
    closed_date = fields.Date(
        required=False,
        allow_none=True,
        metadata={
            "description": "ISO8601 date for when product was closed for the location",
            "example": "2020-05-01",
        },
    )


class LocationProductResponse(Identifier, LocationProductRequest):
    class Meta:
        ordered = True


class LocationCommonOptionalFields(Schema):
    class Meta:
        ordered = True

    active = fields.Boolean(
        required=False,
        allow_none=True,
        metadata={
            "description": "Whether the location is active",
            "example": True,
        },
    )
    address_line_1 = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "description": "First line of location address",
            "example": "21 Spring Lane",
        },
    )
    address_line_2 = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "description": "Second line of location address",
            "example": "Villageville",
        },
    )
    address_line_3 = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "description": "Third line of location address",
            "example": "Townton",
        },
    )
    address_line_4 = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "description": "Fourth line of location address",
            "example": "Cityland",
        },
    )
    postcode = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "description": "Location address postcode",
            "example": "OX1 1AA",
        },
    )
    country = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "description": "Location address country",
            "example": "United Kingdom",
        },
    )
    locality = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "description": "Location address locality",
            "example": "Oxfordshire",
        },
    )
    region = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "description": "Location address region",
            "example": "South East",
        },
    )
    score_system_default = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "description": "Default early warning score system for this location",
        },
        validate=validate.OneOf(["news2", "meows"]),
    )


class LocationCommonRequiredFields(Schema):
    class Meta:
        ordered = True

    location_type = fields.String(
        required=True,
        metadata={
            "description": "Location type code",
            "example": draymed.codes.code_from_name(
                name="hospital", category="location"
            ),
        },
    )
    ods_code = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "description": "ODS code used by the EPR to refer to the location",
            "example": "JW1-34",
        },
    )
    display_name = fields.String(
        required=True,
        metadata={
            "description": "Name used to display the location in product UIs",
            "example": "John Radcliffe Hospital",
        },
    )


@openapi_schema(dhos_locations_api_spec)
class LocationRequest(LocationCommonOptionalFields, LocationCommonRequiredFields):
    class Meta:
        description = "Location request"
        unknown = EXCLUDE
        ordered = True

    dh_products = fields.List(
        fields.Nested(LocationProductRequest),
        required=True,
        metadata={
            "description": "Products with which location should be associated",
        },
    )

    parent = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "description": "Parent location UUID",
            "example": "eb42ee95-6aa6-46b7-9c3e-0e96526747a6",
        },
    )

    parent_ods_code = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "description": "ODS code used by EPR to refer to the location's parent",
            "example": "ABC-123",
        },
    )


class ParentResponse(LocationCommonRequiredFields):
    class Meta:
        description = "Parent location subset of fields"
        unknown = EXCLUDE
        ordered = True

    uuid = fields.String(
        required=True,
        metadata={
            "description": "Universally unique identifier for object",
            "example": "2c4f1d24-2952-4d4e-b1d1-3637e33cc161",
        },
    )
    parent = fields.Nested(
        lambda: ParentResponse(),
        required=False,
        allow_none=True,
        metadata={"example": None},
    )
    score_system_default = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "description": "Default early warning score system for this location",
        },
        validate=validate.OneOf(["news2", "meows"]),
    )


@openapi_schema(dhos_locations_api_spec)
class LocationResponse(
    Identifier, LocationCommonOptionalFields, LocationCommonRequiredFields
):
    class Meta:
        description = "Location response"
        unknown = EXCLUDE
        ordered = True

    dh_products = fields.List(
        fields.Nested(LocationProductResponse),
        required=False,
        metadata={
            "description": "Products with which location is associated",
        },
    )

    parent = fields.Nested(
        ParentResponse,
        required=False,
        allow_none=True,
        metadata={
            "description": "Parent location",
            "example": {
                "uuid": "9d85305e-7a6c-4a37-82a2-21787994ce79",
                "location_type": "22232009",
                "ods_code": "AAA-111",
                "display_name": "Amber Hospital",
            },
        },
    )

    children = fields.List(
        fields.String(),
        required=False,
        metadata={
            "description": "UUIDs of child locations associated with this location",
        },
    )


@openapi_schema(dhos_locations_api_spec)
class LocationUpdateRequest(LocationCommonOptionalFields):
    class Meta:
        description = "Location update request"
        unknown = EXCLUDE
        ordered = True

    location_type = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "description": "Location type code",
            "example": draymed.codes.code_from_name(
                name="hospital", category="location"
            ),
        },
    )

    parent_location = fields.String(
        required=False,
        allow_none=True,
        metadata={
            "description": "Parent location UUID",
            "example": "eb42ee95-6aa6-46b7-9c3e-0e96526747a6",
        },
    )

    dh_products = fields.List(
        fields.Nested(LocationProductRequest),
        required=False,
        allow_none=True,
        metadata={
            "description": "Products with which location should be associated",
        },
    )
