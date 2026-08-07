"""App configuration flags."""

import os

# When True, state falls back to the wireframe's demo content whenever the
# backend dispatch returns nothing (which is always, until the TAOpy actors
# land in phase 2). Set IDATASIGHT_DEMO=0 to see the real empty states.
DEMO_MODE = os.environ.get("IDATASIGHT_DEMO", "1") != "0"

# The analyst whose memory this session reads and writes — beliefs are
# remembered per-user in the EverOS storage root (EVEROS_ROOT, ~/.everos by
# default), so two analysts can hold different beliefs over the same data.
USER = os.environ.get("IDATASIGHT_USER", "sudhi")
