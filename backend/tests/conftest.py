"""Keep all automated tests isolated from a user's real Google account."""

import os


os.environ["AETHERBOT_TESTING"] = "1"

