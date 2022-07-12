from typing import Optional

from environs import Env
from flask import Flask


class Configuration:
    env = Env()
    DHOS_RULES_ENGINE_URL: str = env.str(
        "DHOS_RULES_ENGINE_URL", "http://localhost:3000"
    )
    MOCK_TRUSTOMER_CONFIG: Optional[str] = env.str("MOCK_TRUSTOMER_CONFIG", None)


def init_config(app: Flask) -> None:
    app.config.from_object(Configuration)
