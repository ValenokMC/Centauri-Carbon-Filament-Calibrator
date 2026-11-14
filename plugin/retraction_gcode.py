"""Rewrite a sliced two-post tower with relative extrusion and wipe disabled."""
import math
import re
from collections import Counter


_MOVE = re.compile(r'^(G[01]\s+E)([-+]?(?:\d+(?:\.\d*)?|\.\d+))(?=\s|;|$)')


def rewrite_tower(gcode, stages, baseline):
    """Return a new G-code string and counts of completed pairs per stage."""
    if not stages or not math.isfinite(baseline) or baseline <= 0:
        raise ValueError('Invalid tower scale or baseline')
    if any(not math.isfinite(z) or not math.isfinite(length) or z <= 0 or length < 0
           for z, length in stages) or any(a[0] >= b[0] for a, b in zip(stages, stages[1:])):
        raise ValueError('Invalid tower scale')
    if ('; use_firmware_retraction = 0' not in gcode
            or '; use_relative_e_distances = 1' not in gcode
            or not re.search(r'^; (?:filament_)?wipe = 0\s*$', gcode, re.MULTILINE)
            or ';WIPE_START' in gcode):
        raise ValueError('Expected slicer retraction, relative extrusion, and no wipe')
    lines = gcode.splitlines(keepends=True)
    relative = False
    z = None
    pending = None
    counts = Counter()
    for i, line in enumerate(lines):
        code = line.partition(';')[0].strip()
        if code in ('M82', 'M83'):
            relative = code == 'M83'
        if line.startswith(';Z:'):
            z = float(line[3:])
        if z is None or not code:
            continue
        if code in ('M82', 'G90', 'G91') or code.startswith(('G92', 'T')):
            if pending is not None:
                raise ValueError('Motion mode or tool changed during a retraction')
            if code in ('M82', 'G90', 'G91'):
                raise ValueError('Unexpected positioning mode inside the tower')
        move = _MOVE.match(code) if re.fullmatch(r'G[01]\s+E[-+.\d]+(?:\s+F[-+.\d]+)?', code) else None
        if move is None:
            if re.match(r'G[0123]\s', code):
                extrusion = re.search(r'\bE([-+]?(?:\d+(?:\.\d*)?|\.\d+))', code)
                if extrusion and (pending is not None or float(extrusion[1]) < 0):
                    raise ValueError('Unexpected combined extrusion move')
            continue
        amount = float(move[2])
        if not relative or not math.isclose(abs(amount), baseline, abs_tol=0.0001):
            raise ValueError('Unexpected extrusion-only move inside the tower')
        if amount < 0 and pending is None:
            stage = next((j for j, (limit, _) in enumerate(stages) if z <= limit + 1e-6), None)
            pending = (i, stage)
        elif amount > 0 and pending is not None:
            start, stage = pending
            pending = None
            if stage is not None:
                length = stages[stage][1]
                for index, value in ((start, -length), (i, length)):
                    lines[index] = _MOVE.sub(lambda m: m[1] + f'{value:g}', lines[index], count=1)
                counts[stage] += 1
        else:
            raise ValueError('Unexpected retraction/recovery order')
    # Orca may leave the final parking retraction unmatched. Keep it as sliced.
    if any(not counts[i] for i in range(len(stages))):
        raise ValueError('At least one tower stage has no verified retraction pair')
    return ''.join(lines), counts
