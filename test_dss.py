
import opendssdirect as dss

dss.Basic.ClearAll()

def run(command):
    dss.Text.Command(command)
    error = dss.Error.Number()
    if error:
        raise RuntimeError(f"{command}\n{dss.Error.Description()}")

run("New Circuit.TestFeeder bus1=SourceBus basekV=12.66 pu=1.0 phases=3")
run("New Line.L1 bus1=SourceBus.1.2.3 bus2=LoadBus.1.2.3 phases=3 r1=0.1 x1=0.1 length=1 units=km")
run("New Load.Load1 bus1=LoadBus.1.2.3 phases=3 conn=wye model=1 kV=12.66 kW=100 kvar=50")
run("Set VoltageBases=[12.66]")
run("CalcVoltageBases")
run("Set Mode=Snapshot")

dss.Solution.Solve()

print("Circuit:", dss.Circuit.Name())
print("Converged:", dss.Solution.Converged())
print("Buses:", dss.Circuit.AllBusNames())
print("Total power (W, var):", dss.Circuit.TotalPower())
print("Losses (W, var):", dss.Circuit.Losses())

dss.Circuit.SetActiveBus("LoadBus")
print("Load bus voltage (pu, magnitude/angle):", dss.Bus.puVmagAngle())
