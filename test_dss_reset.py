from opendssdirect import dss

dss.Text.Command("Clear")
dss.Text.Command(
    "New Circuit.ResetTest bus1=SourceBus phases=3 basekV=12.66 pu=1"
)
dss.Text.Command(
    "New Capacitor.Support bus1=SourceBus.1.2.3 "
    "phases=3 conn=wye kV=12.66 kvar=900"
)

print("First capacitor creation: OK")

dss.Text.Command("Clear")
dss.Text.Command(
    "New Circuit.ResetTest2 bus1=SourceBus phases=3 basekV=12.66 pu=1"
)
dss.Text.Command(
    "New Capacitor.Support bus1=SourceBus.1.2.3 "
    "phases=3 conn=wye kV=12.66 kvar=900"
)

print("Second capacitor creation after Clear: OK")