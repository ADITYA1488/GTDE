from src.ieee33_network import build_ieee33_network
from src.restoration_powerflow import evaluate_ieee33_configuration

net = build_ieee33_network()

plans = [
    (["T35"], ["L08"]),
    (["T35"], ["L08", "L16"]),
    (["T35"], ["L08", "L17"]),
]

for ties, opened in plans:
    result = evaluate_ieee33_configuration(
        closed_ties=set(ties),
        opened_branches=set(opened),
        faulted_branches={"L15"},
        capacitor_bus=33,
        capacitor_kvar=1500,
    )
    print(
        f"ties={ties}, open={opened}, "
        f"converged={result.get('converged')}, "
        f"loss={result.get('real_losses_kw')}, "
        f"Vmin={result.get('min_voltage_pu')}, "
        f"energized_buses={result.get('energized_buses')}"
    )
