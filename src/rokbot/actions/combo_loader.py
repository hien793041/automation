"""Load user-defined combos from config/combos.yaml."""

from pathlib import Path
from typing import Dict, List, Optional

import yaml
from loguru import logger


class ComboLoader:
    """Loads combo definitions from config/combos.yaml."""

    _cache: Optional[Dict[str, List[str]]] = None

    @classmethod
    def _load(cls) -> Dict[str, List[str]]:
        if cls._cache is not None:
            return cls._cache

        combos: Dict[str, List[str]] = {}
        path = Path("config/combos.yaml")
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if data and "combos" in data:
                    for name, action_list in data["combos"].items():
                        if isinstance(action_list, list):
                            combos[name] = [str(a) for a in action_list]
                        else:
                            logger.warning(f"Combo '{name}' is not a list — skipping")
            except Exception as e:
                logger.error(f"Failed to load combos.yaml: {e}")
        else:
            logger.debug("config/combos.yaml not found — no user combos loaded")

        cls._cache = combos
        return combos

    @classmethod
    def get_combo(cls, name: str) -> Optional[List[str]]:
        """Return the action sequence for a combo name, or None."""
        return cls._load().get(name)

    @classmethod
    def list_combos(cls) -> List[str]:
        """Return all defined combo names."""
        return list(cls._load().keys())

    @classmethod
    def invalidate_cache(cls) -> None:
        """Clear the cache so the next call re-reads the file."""
        cls._cache = None
