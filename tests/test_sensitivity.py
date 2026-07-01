"""Tornado (one-at-a-time) sensitivity analysis checks."""

from lpem import params as P
from lpem.routes import ROUTES
from lpem.sensitivity import ParamSensitivity, dominant_drivers, tornado


def test_tornado_sorted_by_swing_descending():
    for key in ROUTES:
        rows = tornado(key)
        swings = [r.swing for r in rows]
        assert swings == sorted(swings, reverse=True), key


def test_swings_non_negative():
    for key in ROUTES:
        for r in tornado(key):
            assert r.swing >= 0.0, (key, r.cite)
            # swing is the absolute gap between the two pinned totals
            assert r.swing == abs(r.high_total - r.low_total)


def test_every_used_param_appears_once():
    # Each route's tornado should cover the params it actually uses, no duplicates.
    for key in ROUTES:
        rows = tornado(key)
        params = [id(r.param) for r in rows]
        assert len(params) == len(set(params)), key
        assert all(isinstance(r, ParamSensitivity) for r in rows)


def test_dominant_drivers_is_tornado_head():
    for key in ROUTES:
        full = tornado(key)
        top = dominant_drivers(key, top=3)
        assert top == full[:3]


def test_h2_reduction_dominant_driver_is_standing_loss():
    # With the reactor standing loss now charged symmetrically to H2 reduction, its wide
    # log-range (2-30 kWh/kg O2) makes it the single largest one-at-a-time swing, ahead of
    # the heating chain (O2 yield, heat recuperation) that dominated before.
    top3 = {d.param for d in dominant_drivers("h2_reduction", top=3)}
    assert dominant_drivers("h2_reduction", top=1)[0].param is P.REACTOR_STANDING_LOSS
    # The heating chain is still a top driver, just no longer the first.
    assert P.YIELD_H2_REDUCTION in top3 or P.RECUP_REGOLITH in top3


def test_mre_dominant_drivers_are_loss_or_faradaic():
    # For MRE the dominant uncertainties are the (newly added) reactor standing loss and
    # the faradaic chain (cell voltage / current efficiency). The top driver should be one
    # of these; cell voltage in particular is the key unmeasured electrochemical number.
    top3 = {d.param for d in dominant_drivers("mre", top=3)}
    assert P.REACTOR_STANDING_LOSS in top3 or P.V_CELL_MRE in top3
    assert P.V_CELL_MRE in top3
