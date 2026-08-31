"""Threshold values used by the rule-based detectors.

Every number here comes from published work rather than intuition, because the
thesis has to defend each one. Two sources are used:

* Lanza, M. & Marinescu, R. (2006), *Object-Oriented Metrics in Practice*:
  the statistical thresholds derived from a corpus of 45 Java and C++ systems,
  and the detection strategies built on them.
* Fowler, M. (2018), *Refactoring*, 2nd ed.: the qualitative descriptions
  that motivate the size-based rules.

Keeping them in one module (rather than inline in the detectors) means the
sensitivity analysis in the Results chapter can sweep them programmatically.
"""

from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------
# Lanza & Marinescu's generic quantifiers, p. 16.
# These are the vocabulary the detection strategies are written in.
# ---------------------------------------------------------------------
FEW = 5
MANY = 10
SHORT_MEMORY_CAP = 7  # the "magical number seven" bound on working memory
ONE_THIRD = 1.0 / 3.0

# Statistical thresholds for Java systems, derived in the same work (p. 17).
HIGH_WMC = 31
VERY_HIGH_WMC = 47
HIGH_NOM = 20
HIGH_CLASS_LOC = 200
HIGH_METHOD_LOC = 70


@dataclass(frozen=True)
class Thresholds:
    """One tunable configuration of the rule-based detectors.

    Instances are frozen so that a sweep over several configurations cannot
    accidentally mutate the baseline it is being compared against.
    """

    # --- God Class ---------------------------------------------------
    god_class_wmc: float = VERY_HIGH_WMC
    god_class_tcc: float = ONE_THIRD
    god_class_atfd: float = FEW

    # --- Data Class ---------------------------------------------------
    data_class_woc: float = ONE_THIRD
    data_class_public_members: float = FEW
    data_class_wmc_low: float = HIGH_WMC
    data_class_public_members_many: float = MANY
    data_class_wmc_high: float = VERY_HIGH_WMC

    # --- Feature Envy -------------------------------------------------
    feature_envy_atfd: float = FEW
    feature_envy_laa: float = ONE_THIRD
    feature_envy_fdp: float = FEW

    # --- Long Method / Brain Method -----------------------------------
    long_method_loc: float = 30
    brain_method_loc: float = HIGH_METHOD_LOC / 2
    brain_method_cc: float = 4
    brain_method_nesting: float = 3
    brain_method_noav: float = MANY

    # --- Long Parameter List ------------------------------------------
    long_parameter_list_np: float = FEW

    # --- Deep Nesting --------------------------------------------------
    deep_nesting: float = 3

    # --- Large Class ---------------------------------------------------
    large_class_loc: float = HIGH_CLASS_LOC
    large_class_nom: float = HIGH_NOM

    # --- Severity (VD-06) ----------------------------------------------
    # These three have no published source, and saying so is the point. The
    # detection thresholds above are Lanza & Marinescu's; these are ours, chosen
    # to turn measured excess into the MLCQ scale. VD-06 recorded that they must
    # be swept rather than trusted, which is only possible with them here: while
    # they sat inline in `base.py` no sweep could reach them.
    #
    # They do not change whether a detector fires, only how severe it calls what
    # it found, so their sweep is scored against agreement with the reviewers'
    # severity and not against MCC.
    excess_cap: float = 5.0
    severity_major: float = 1.5
    severity_critical: float = 2.5


DEFAULT = Thresholds()
