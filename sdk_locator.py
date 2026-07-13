"""Make the external ``taphome_sdk`` package importable during development.

In production the package is installed from PyPI (listed in ``manifest.json``
requirements once published). During development a local checkout of
https://github.com/martindybal/taphome-sdk takes precedence instead, so SDK
changes are picked up without publishing a release. Search order:

1. the directory in the ``TAPHOME_SDK_PATH`` environment variable,
2. a ``taphome-sdk`` repository cloned next to this one, e.g. both
   repositories checked out side by side in ``d:\\repos``.

Importing this module performs the ``sys.path`` setup, so it must stay the
first import of the integration package. This module will not be part of the
Home Assistant Core submission — Core installs requirements from PyPI only.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sys

_LOGGER = logging.getLogger(__name__)


def _ensure_taphome_sdk() -> None:
    """Prepend a local taphome-sdk checkout to ``sys.path`` when one exists."""
    candidates = []

    env_path = os.environ.get("TAPHOME_SDK_PATH")
    if env_path:
        candidates.append(Path(env_path))

    # resolve() follows symlinks, so this also works when
    # custom_components/taphome is a symlink into the repository clone.
    repo_root = Path(__file__).resolve().parent
    candidates.append(repo_root.parent / "taphome-sdk" / "src")

    for candidate in candidates:
        if (candidate / "taphome_sdk" / "__init__.py").is_file():
            path = str(candidate)
            if path not in sys.path:
                sys.path.insert(0, path)
                _LOGGER.info("Loading taphome_sdk from local checkout: %s", path)
            return


_ensure_taphome_sdk()
