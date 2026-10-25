"""Shared model of the differential VTEAM crossbar.

A weight w is stored as a conductance pair (G+ on the column's blp line,
G- on its bln line), and the column output is

    I_out[c] = sum_i V_in[i] * (G+[i][c] - G-[i][c])

where V_in is the cell voltage (wordline minus the 300 mV virtual ground).
"""

# VTEAM parameters used in every cell (from the tb_array2x2_v4 netlist).
RON = 2e6     # ohm, x = 0
ROFF = 50e6   # ohm, x = 1

# Weight unit. The three programmed states sit on a x2 conductance ladder:
# xinit 0.0625 -> 5 MOhm (4*G0), 0.16667 -> 10 MOhm (2*G0), 0.375 -> 20 MOhm (1*G0).
G0 = 0.05e-6  # siemens

# Weight (in units of G0) -> (xinit for G+, xinit for G-).
# The x2 ladder of states gives seven evenly spaced weights; zero is a
# 20M/20M pair so both lines still carry a small, equal current.
WEIGHT_TO_PAIR = {
    +3: (0.0625, 0.375),
    +2: (0.0625, 0.16667),
    +1: (0.16667, 0.375),
    0: (0.375, 0.375),
    -1: (0.375, 0.16667),
    -2: (0.16667, 0.0625),
    -3: (0.375, 0.0625),
}


def resistance(xinit):
    """VTEAM resistance, linear in the state variable."""
    return RON + (ROFF - RON) * xinit


def conductance(xinit):
    return 1.0 / resistance(xinit)


def pair_for(weight):
    if weight not in WEIGHT_TO_PAIR:
        raise ValueError(f"weight {weight} not in -3..+3 (units of G0 = 0.05 uS)")
    return WEIGHT_TO_PAIR[weight]


def ideal_outputs(weights, v_in):
    """Ideal column currents in amps.

    weights: rows x columns, integers in -3..+3
    v_in:    one cell voltage per row, in volts
    """
    n_cols = len(weights[0])
    out = [0.0] * n_cols
    for row, v in zip(weights, v_in):
        for c, w in enumerate(row):
            xp, xn = pair_for(w)
            out[c] += v * (conductance(xp) - conductance(xn))
    return out


def parse_weights(text):
    """'2,-1;-1,3' -> [[2, -1], [-1, 3]]  (rows separated by ';')."""
    return [[int(w) for w in row.split(",")] for row in text.split(";")]
