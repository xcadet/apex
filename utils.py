import hashlib
import json

from models import ExperimentConfig


def generate_config_sha1(config: ExperimentConfig) -> str:
    """Generate a deterministic SHA1 hash from an ExperimentConfig.

    Serializes the config to a canonical JSON string (sorted keys, no extra
    whitespace) and returns its SHA1 hex digest.  Two configs that are
    semantically identical will always produce the same hash, so the SHA1
    can be used to uniquely identify and recover an experiment.
    """
    canonical = json.dumps(config.model_dump(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()
