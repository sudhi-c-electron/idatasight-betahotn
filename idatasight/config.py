"""App configuration flags."""

import os

# When True, state falls back to the wireframe's demo content whenever the
# backend dispatch returns nothing (which is always, until the TAOpy actors
# land in phase 2). Set IDATASIGHT_DEMO=0 to see the real empty states.
DEMO_MODE = os.environ.get("IDATASIGHT_DEMO", "1") != "0"
