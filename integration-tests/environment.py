from behave import use_step_matcher
from behave.model import Scenario
from behave.runner import Context
from clients.locations_api_client import drop_all_data
from helpers.jwt import get_system_token

use_step_matcher("re")


def before_scenario(context: Context, scenario: Scenario) -> None:
    drop_all_data(get_system_token())
    context.location_map = {}


def after_scenario(context: Context, scenario: Scenario) -> None:
    drop_all_data(get_system_token())
