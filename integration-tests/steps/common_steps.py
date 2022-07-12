import time

from behave import given, step, when
from behave.runner import Context
from helpers.jwt import get_system_token


@given("a valid JWT")
def get_system_jwt(context: Context) -> None:
    if not hasattr(context, "system_jwt"):
        context.system_jwt = get_system_token()


@step("it took less than (?P<max_time>\d+(?:.\d*)?) second(?:s)? to complete")
def it_took_less_than(context: Context, max_time: str) -> None:
    limit = float(max_time)

    end_time = time.time()
    assert (
        end_time - context.start_time < limit
    ), f"Max time for test exceeded {max_time} seconds"


@when("timing this step")
def timing_step(context: Context) -> None:
    context.start_time = time.time()
