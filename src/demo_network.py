from .network import Branch, DistributionNetwork


def build_demo_network():
    buses = {
        1: {"name": "Substation", "load_kw": 0},
        2: {"name": "Residential North", "load_kw": 100},
        3: {"name": "Commercial", "load_kw": 120},
        4: {"name": "Industrial", "load_kw": 80},
        5: {"name": "Residential South", "load_kw": 150},
        6: {"name": "Mixed Load", "load_kw": 90},
    }

    branches = [
        Branch("L12", 1, 2, True, True, 0.20),
        Branch("L23", 2, 3, True, True, 0.25),
        Branch("L34", 3, 4, True, True, 0.30),
        Branch("L45", 4, 5, True, True, 0.35),
        Branch("L56", 5, 6, True, True, 0.25),
        Branch("T25", 2, 5, False, True, 0.40),
        Branch("T36", 3, 6, False, True, 0.38),
        Branch("T46", 4, 6, False, True, 0.32),
    ]

    return DistributionNetwork(buses, branches, source_bus=1)