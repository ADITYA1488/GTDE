import networkx as nx
import opendssdirect as dss


def evaluate_power_flow(
    net, closed_ties=None, opened_branches=None, faulted_branches=None
):
    closed_ties = set(closed_ties or [])
    opened_branches = set(opened_branches or [])
    faulted_branches = set(faulted_branches or [])

    graph = net.build_graph(
        closed_ties, opened_branches, faulted_branches
    )

    if not nx.is_forest(graph):
        return {"converged": False, "error": "Topology contains a cycle."}

    if net.source_bus not in graph:
        return {"converged": False, "error": "Source bus missing."}

    supplied = net.supplied_buses(graph)
    unsupplied = sum(
        float(bus.get("load_kw", 0))
        for bus_id, bus in net.buses.items()
        if bus_id not in supplied
    )

    try:
        dss.Basic.ClearAll()
        dss.Text.Command(
            "New Circuit.FeederDemo basekv=12.47 pu=1.0 "
            f"phases=3 bus1=bus{net.source_bus}"
        )

        for branch in net.branches:
            bid = branch.branch_id

            if bid in faulted_branches or bid in opened_branches:
                continue
            if not branch.normally_closed and bid not in closed_ties:
                continue

            r = max(float(branch.resistance_ohm), 1e-5)
            x = max(r * 0.5, 1e-5)

            dss.Text.Command(
                f"New Line.{bid} bus1=bus{branch.u} bus2=bus{branch.v} "
                f"phases=3 length=1 units=km "
                f"r1={r} x1={x} r0={r} x0={x}"
            )

        for bus_id, bus in net.buses.items():
            kw = float(bus.get("load_kw", 0))
            if kw <= 0 or bus_id not in supplied:
                continue

            dss.Text.Command(
                f"New Load.Load{bus_id} bus1=bus{bus_id} "
                f"phases=3 conn=wye kv=12.47 kw={kw} pf=0.95 model=1"
            )

        dss.Text.Command("Set VoltageBases=[12.47]")
        dss.Text.Command("CalcVoltageBases")
        dss.Text.Command("Solve")

        if not dss.Solution.Converged():
            return {
                "converged": False,
                "error": "OpenDSS did not converge.",
                "unsupplied_load_kw": unsupplied,
            }

        voltages = {}
        for name in dss.Circuit.AllBusNames():
            dss.Circuit.SetActiveBus(name)
            values = dss.Bus.puVmagAngle()[::2]
            if values:
                voltages[name] = {
                    "min_pu": float(min(values)),
                    "max_pu": float(max(values)),
                }

        losses = dss.Circuit.Losses()
        all_min = [v["min_pu"] for v in voltages.values()]
        all_max = [v["max_pu"] for v in voltages.values()]

        return {
            "converged": True,
            "real_losses_kw": float(losses[0]) / 1000,
            "reactive_losses_kvar": float(losses[1]) / 1000,
            "minimum_bus_voltage_pu": min(all_min) if all_min else None,
            "maximum_bus_voltage_pu": max(all_max) if all_max else None,
            "bus_voltages": voltages,
            "unsupplied_load_kw": unsupplied,
            "model": "Synthetic assumptions; not a calibrated feeder.",
        }

    except Exception as exc:
        return {
            "converged": False,
            "error": f"{type(exc).__name__}: {exc}",
            "unsupplied_load_kw": unsupplied,
        }