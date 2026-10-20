"""Record types and how to tell them apart from an ID.

IDs follow the naming scheme CAT-/AN- (material) -> -C001 (coating) ->
-SLP-001 / -CC01 / MLP-0001 (cells).
"""

def detect_record_type(record_id: str) -> str:
    """Record type from an ID: 'material', 'coating', 'slp', 'coincell', 'mlp' or None."""
    rid = record_id.upper()
    if "-SLP-" in rid:
        return "slp"
    if "MLP-" in rid:
        return "mlp"
    if "-CC" in rid:
        return "coincell"
    if "-C0" in rid or "-C1" in rid:
        return "coating"
    if rid.startswith("CAT") or rid.startswith("AN"):
        return "material"
    return None


CELL_TYPES = ("slp", "coincell", "mlp")
