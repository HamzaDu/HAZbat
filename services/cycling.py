from core.db import get_connection


# --- Voltage curves from cycling files ----------------------------------------
VOLTAGE_COLUMNS = ("Ewe/V", "Ecell/V", "<Ewe>/V")   # BioLogic names, first one found is used
MAX_POINTS_PER_CURVE = 400                          # keeps the JSON small for long files


def latest_cycling_file(record_id: str):
    """Path of the most recently uploaded .mpr file for a record (None if there isn't one)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT file_path FROM tbl_cycling_data WHERE record_id = %s ORDER BY uploaded_at DESC LIMIT 1",
        (record_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


def read_half_cycles(file_path: str):
    """Split a BioLogic file into half-cycles with their voltage curve.
    Returns [{"half_cycle", "is_charge", "capacity_mah": [...], "voltage_v": [...]}, ...];
    capacity restarts from 0 at the start of each half-cycle. Rests (< 0.01 mAh) are dropped."""
    from galvani import BioLogic
    data = BioLogic.MPRfile(file_path).data
    names = data.dtype.names if hasattr(data, "dtype") and data.dtype.names else list(data.keys())
    v_col = next((c for c in VOLTAGE_COLUMNS if c in names), None)
    if v_col is None:
        raise ValueError("No voltage column (Ewe/V) found in this file")

    halves = []
    for c in sorted(set(int(x) for x in data["half cycle"])):
        mask = data["half cycle"] == c
        q = data["Q charge/discharge/mA.h"][mask]
        v = data[v_col][mask]
        if len(q) < 2:
            continue
        delta = float(q[-1]) - float(q[0])
        if abs(delta) <= 0.01:
            continue  # rest / OCV segment
        # Keep at most MAX_POINTS_PER_CURVE points, always including the last one (end capacity)
        step = max(1, -(-len(q) // MAX_POINTS_PER_CURVE))  # ceiling division
        keep = list(range(0, len(q), step))
        if keep[-1] != len(q) - 1:
            keep.append(len(q) - 1)
        q0 = float(q[0])
        halves.append({
            "half_cycle": c,
            "is_charge": delta > 0,
            "capacity_mah": [round(abs(float(q[i]) - q0), 5) for i in keep],
            "voltage_v": [round(float(v[i]), 4) for i in keep],
        })
    return halves


def group_full_cycles(halves):
    """Pair each charge with the discharge after it: [{"cycle": 1, "charge": {...}, "discharge": {...}}, ...].
    A discharge with no charge before it (e.g. a cathode half cell) starts its own cycle."""
    cycles = []
    for h in halves:
        part = {"capacity_mah": h["capacity_mah"], "voltage_v": h["voltage_v"], "half_cycle": h["half_cycle"]}
        if h["is_charge"]:
            cycles.append({"charge": part})
        elif cycles and "discharge" not in cycles[-1]:
            cycles[-1]["discharge"] = part
        else:
            cycles.append({"discharge": part})
    for number, cycle in enumerate(cycles, start=1):
        cycle["cycle"] = number
    return cycles
