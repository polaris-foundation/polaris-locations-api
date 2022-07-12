from typing import Any, Dict, List, Optional

from flask import Blueprint, Response, jsonify
from flask_batteries_included.helpers.security import protected_route
from flask_batteries_included.helpers.security.endpoint_security import (
    and_,
    or_,
    scopes_present,
)

from ..helpers.security import get_clinician_locations, ods_code_is_none
from . import controller

locations_blueprint = Blueprint("locations_api", __name__)


@locations_blueprint.route("/dhos/v1/location", methods=["POST"])
@protected_route(
    or_(
        scopes_present(required_scopes="write:gdm_location"),
        scopes_present(required_scopes="write:send_location"),
        scopes_present(required_scopes="write:location"),
    )
)
def create_location(location_details: Dict[str, Any]) -> Response:
    """
    ---
    post:
      summary: Create location
      description: Create a new location using the details provided in the request body.
      tags: [location]
      requestBody:
        description: Location details
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/LocationRequest'
              x-body-name: location_details
      responses:
        '200':
          description: New location
          content:
            application/json:
              schema: LocationResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    response: Dict = controller.create_location(location_details=location_details)
    return jsonify(response)


@locations_blueprint.route("/dhos/v1/location/bulk", methods=["POST"])
@protected_route(
    or_(
        scopes_present(required_scopes="write:gdm_location"),
        scopes_present(required_scopes="write:send_location"),
        scopes_present(required_scopes="write:location"),
    )
)
def create_many_locations(location_list: List[Dict[str, Any]]) -> Response:
    """
    ---
    post:
      summary: Create location
      description: Create a new location using the details provided in the request body.
      tags: [location]
      requestBody:
        description: Location details
        required: true
        content:
          application/json:
            schema:
              type: array
              items:
                $ref: '#/components/schemas/LocationRequest'
              x-body-name: location_list
      responses:
        '200':
          description: New location
          content:
            application/json:
              schema:
                type: object
                properties:
                    created:
                        type: integer
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    response: Dict = controller.create_many_locations(location_list=location_list)
    return jsonify(response)


@locations_blueprint.route("/dhos/v1/location/<location_id>", methods=["PATCH"])
@protected_route(
    or_(
        scopes_present(required_scopes="write:gdm_location"),
        scopes_present(required_scopes="write:send_location"),
        scopes_present(required_scopes="write:location"),
    )
)
def update_location(location_id: str, location_details: Dict[str, Any]) -> Response:
    """
    ---
    patch:
      summary: Update location
      description: Update the location with the provided UUID using the details in the request body.
      tags: [location]
      parameters:
        - name: location_id
          in: path
          required: true
          description: Location UUID
          schema:
            type: string
            example: bba65af9-88d3-459b-8c09-c359873828f7
      requestBody:
        description: Location update
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/LocationUpdateRequest'
              x-body-name: location_details
      responses:
        '200':
          description: Updated location
          content:
            application/json:
              schema: LocationResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    response: Dict = controller.update_location(
        location_uuid=location_id, update_details=location_details
    )
    return jsonify(response)


@locations_blueprint.route("/dhos/v1/location/search", methods=["GET"])
@protected_route(
    and_(
        or_(
            scopes_present("read:send_location"),
            scopes_present("read:gdm_location"),
            scopes_present("read:gdm_location_all"),
            scopes_present("read:location_all"),
        ),
        or_(ods_code_is_none, scopes_present("read:location_by_ods")),
    )
)
def search_locations(
    ods_code: Optional[str] = None,
    location_types: Optional[List[str]] = None,
    active: Optional[bool] = None,
    product_name: Optional[List[str]] = None,
    children: bool = False,
    compact: bool = False,
) -> Response:
    """
    ---
    get:
      summary: Get all locations
      description: Get all locations using the filters in the request parameters.
      tags: [location]
      parameters:
        - name: ods_code
          in: query
          required: false
          description: An ODS code to filter by
          schema:
            type: string
            example: ABC-123
        - name: location_types
          in: query
          required: false
          description: A pipe-delimited list of location type SNOMED codes to filter results by
          style: pipeDelimited
          schema:
            type: array
            nullable: true
            items:
                type: string
                enum: ["22232009", "D0000009", "225746001", "225730009", "229772003", "723231000000104"]
            example: 225746001|22232009
        - name: active
          in: query
          required: false
          description: An active status to filter by
          schema:
            type: boolean
            example: true
            nullable: true
        - name: children
          in: query
          required: false
          description: Whether to include child location UUIDs in the response
          schema:
            type: boolean
            default: false
        - name: product_name
          in: query
          required: false
          description: One or more product names to filter on (comma separated or repeated parameter)
          schema:
            type: array
            items:
                type: string
                minLength: 1
            example: GDM
        - name: compact
          in: query
          required: false
          description: Whether to return results in compact form
          schema:
            type: boolean
            default: false
        - in: header
          name: X-Location-Ids
          description: List of location UUIDs, only used for clinicians
          schema:
            type: string
            example: '09db61d2-2ad9-4878-beee-1225b720c205,5d68b104-38cb-48fe-a814-00ac1387ef17'
          required: false
      responses:
        '200':
          description: List of locations
          content:
            application/json:
              schema:
                type: object
                additionalProperties:
                  $ref: '#/components/schemas/LocationResponse'
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    location_uuids: Optional[List[str]] = get_clinician_locations()
    locations: List[Dict] = controller.location_search(
        ods_code=ods_code,
        location_types=location_types,
        location_uuids=location_uuids,
        product_name=product_name,
        active=active,
        compact=compact,
        children=children,
    )

    locations_map: Dict[str, Optional[Dict]] = (
        dict.fromkeys(location_uuids) if location_uuids else {}
    )
    locations_map.update({loc["uuid"]: loc for loc in locations})
    return jsonify(locations_map)


@locations_blueprint.route("/dhos/v1/location/search", methods=["POST"])
@protected_route(
    and_(
        or_(
            scopes_present("read:send_location"),
            scopes_present("read:gdm_location"),
            scopes_present("read:gdm_location_all"),
            scopes_present("read:location_all"),
        ),
        or_(ods_code_is_none, scopes_present("read:location_by_ods")),
    )
)
def post_search_locations(
    ods_code: Optional[str] = None,
    location_types: Optional[List[str]] = None,
    active: Optional[bool] = None,
    product_name: Optional[List[str]] = None,
    children: bool = False,
    compact: bool = False,
    location_uuids: List[str] = None,
) -> Response:
    """
    ---
    post:
      summary: Search locations by UUID
      description: Search for a list of locations using the UUIDs provided in the request body.
      tags: [location]
      parameters:
        - name: ods_code
          in: query
          required: false
          description: An ODS code to filter by
          schema:
            type: string
            example: ABC-123
        - name: location_types
          in: query
          required: false
          description: A pipe-delimited list of location type SNOMED codes to filter results by
          style: pipeDelimited
          schema:
            type: array
            nullable: true
            items:
                type: string
                enum: ["22232009", "D0000009", "225746001", "225730009", "229772003", "723231000000104"]
            example: 225746001|22232009
        - name: active
          in: query
          required: false
          description: An active status to filter by
          schema:
            type: boolean
            nullable: true
        - name: children
          in: query
          required: false
          description: Whether to include child location UUIDs in the response
          schema:
            type: boolean
            default: false
        - name: compact
          in: query
          required: false
          description: Whether to return results in compact form
          schema:
            type: boolean
            default: false
        - name: product_name
          in: query
          required: false
          description: One or more product names to filter on (comma separated or repeated parameter)
          schema:
            type: array
            items:
                type: string
                minLength: 1
            example: GDM
      requestBody:
        description: Location UUIDs
        required: true
        content:
          application/json:
            schema:
              type: array
              nullable: true
              items:
                type: string
                example: afd60502-da9e-4253-b6ee-f7ba97e82b93
              x-body-name: location_uuids
      responses:
        '200':
          description: List of locations
          content:
            application/json:
              schema:
                type: object
                additionalProperties:
                  $ref: '#/components/schemas/LocationResponse'
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    locations: List[Dict] = controller.location_search(
        ods_code=ods_code,
        location_types=location_types,
        location_uuids=location_uuids,
        product_name=product_name,
        active=active,
        compact=compact,
        children=children,
    )
    locations_map: Dict[str, Optional[Dict]] = (
        dict.fromkeys(location_uuids) if location_uuids else {}
    )
    locations_map.update({loc["uuid"]: loc for loc in locations})
    return jsonify(locations_map)


@locations_blueprint.route("/dhos/v1/location/<location_id>", methods=["GET"])
@protected_route(
    or_(
        scopes_present(required_scopes="read:send_location"),
        scopes_present(required_scopes="read:gdm_location_all"),
        scopes_present(required_scopes="read:gdm_location"),
        scopes_present(required_scopes="read:location_all"),
    )
)
def get_location_by_uuid(
    location_id: str,
    return_parent_of_type: Optional[str] = None,
    children: bool = False,
) -> Response:
    """
    ---
    get:
      summary: Get location by UUID
      description: >-
        Get the location with the provided UUID. The 'return_parent_of_type' query parameter can
        be used to instead get the parent location of a specific type, for example the ward
        parent of a bed's location UUID.
      tags: [location]
      parameters:
        - name: location_id
          in: path
          required: true
          description: Location UUID
          schema:
            type: string
            example: bba65af9-88d3-459b-8c09-c359873828f7
        - name: return_parent_of_type
          in: query
          required: false
          description: >-
            SNOMED code of a location type. If the requested location does not match this location
            type, the endpoint will search through its parent locations and respond with the first
            matching parent location of the requested type.
          schema:
            type: string
            example: "225746001"
        - name: children
          in: query
          required: false
          description: Whether to include child location UUIDs in the response
          schema:
            type: boolean
            default: false
      responses:
        '200':
          description: Requested location
          content:
            application/json:
              schema: LocationResponse
        default:
          description: >-
            Error, e.g. 400 Bad Request, 503 Service Unavailable
          content:
            application/json:
              schema: Error
    """
    if return_parent_of_type is not None:
        response_by_type: Dict = controller.get_location_by_type(
            location_uuid=location_id, location_type=return_parent_of_type
        )
        return jsonify(response_by_type)
    else:
        response_by_id: Dict = controller.get_location_by_uuid(
            location_uuid=location_id, children=children
        )
        return jsonify(response_by_id)
