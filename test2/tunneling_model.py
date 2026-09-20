"""Physical constants shared by Calibration and gap-current calculations."""
from math import sqrt

ELECTRON_MASS_KG = 9.1093837e-31
ELEMENTARY_CHARGE_C = 1.602176634e-19
HBAR_J_S = 1.054571817e-34
WORK_FUNCTION_EV = 5.3


def barrier_decay_per_nm():
    """Return kappa for a rectangular barrier in nm^-1."""
    phi_j = WORK_FUNCTION_EV * ELEMENTARY_CHARGE_C
    return sqrt(2 * ELECTRON_MASS_KG * phi_j) / HBAR_J_S * 1e-9


def current_decay_per_nm():
    """Return 2*kappa because current is proportional to exp(-2*kappa*d)."""
    return 2 * barrier_decay_per_nm()
