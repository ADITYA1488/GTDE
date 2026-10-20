
from src.ieee33_electrical_data import (
    BASE_KV,
    MAIN_BRANCHES,
    TIE_BRANCHES,
    BUS_LOADS,
)


def test_electrical_data_dimensions():
    assert BASE_KV == 12.66
    assert len(MAIN_BRANCHES) == 32
    assert len(TIE_BRANCHES) == 5
    assert len(BUS_LOADS) == 33


def test_branch_impedances_are_positive():
    for branch in MAIN_BRANCHES + TIE_BRANCHES:
        _, _, resistance, reactance = branch
        assert resistance > 0
        assert reactance > 0


def test_loads_are_nonnegative():
    assert all(
        p_kw >= 0 and q_kvar >= 0
        for p_kw, q_kvar in BUS_LOADS.values()
    )
