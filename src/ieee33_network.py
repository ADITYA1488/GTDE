from src.network import Branch, DistributionNetwork


def build_ieee33_network():
    # Standard IEEE 33-bus benchmark active loads (kW).
    # Bus 1 is the source bus.
    loads_kw = {
        1: 0,
        2: 100, 3: 90, 4: 120, 5: 60, 6: 60,
        7: 200, 8: 200, 9: 60, 10: 60, 11: 45,
        12: 60, 13: 60, 14: 120, 15: 60, 16: 60,
        17: 60, 18: 90, 19: 90, 20: 90, 21: 90,
        22: 90, 23: 90, 24: 420, 25: 420, 26: 60,
        27: 60, 28: 60, 29: 120, 30: 200, 31: 150,
        32: 210, 33: 60,
    }

    buses = {
        bus_id: {
            "name": f"Bus {bus_id}",
            "load_kw": load_kw,
        }
        for bus_id, load_kw in loads_kw.items()
    }

    # Normally closed sectionalizing branches.
    main_edges = [
        (1, 2), (2, 3), (3, 4), (4, 5),
        (5, 6), (6, 7), (7, 8), (8, 9),
        (9, 10), (10, 11), (11, 12), (12, 13),
        (13, 14), (14, 15), (15, 16), (16, 17),
        (17, 18), (2, 19), (19, 20), (20, 21),
        (21, 22), (3, 23), (23, 24), (24, 25),
        (6, 26), (26, 27), (27, 28), (28, 29),
        (29, 30), (30, 31), (31, 32), (32, 33),
    ]

    # Normally open tie branches.
    tie_edges = [
        (8, 21), (9, 15), (12, 22),
        (18, 33), (25, 29),
    ]

    branches = []

    for index, (u, v) in enumerate(main_edges, start=1):
        branches.append(
            Branch(
                branch_id=f"L{index:02d}",
                u=u,
                v=v,
                normally_closed=True,
                switchable=True,
            )
        )

    for index, (u, v) in enumerate(tie_edges, start=33):
        branches.append(
            Branch(
                branch_id=f"T{index}",
                u=u,
                v=v,
                normally_closed=False,
                switchable=True,
            )
        )

    return DistributionNetwork(
        buses=buses,
        branches=branches,
        source_bus=1,
    )