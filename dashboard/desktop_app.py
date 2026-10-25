"""GTDE native desktop UI. Run from repository root: python -m dashboard.desktop_app"""
import sys
import time
import traceback
from PySide6.QtCharts import (
    QChart,
    QChartView,
    QBarSeries,
    QBarSet,
    QBarCategoryAxis,
    QValueAxis,
)
import pandas as pd
import plotly.graph_objects as go
from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt, QUrl
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QProgressBar,
    QSpinBox, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)
try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
except ImportError as exc:
    raise SystemExit("Qt WebEngine missing. Run: python -m pip install PySide6-Addons") from exc

from src.ieee33_network import build_ieee33_network
from src.restoration_powerflow import evaluate_restoration_plans
from dashboard.verification import (
    candidate_summary,
    is_fully_verified,
    passes_electrical_checks,
)

STYLE = """
QMainWindow,QWidget{background:#171a21;color:#e8edf5;font-size:13px}
QGroupBox{border:1px solid #343b49;border-radius:8px;margin-top:10px;padding:12px;font-weight:600}
QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 5px}
QLabel#muted{color:#9ba7b8}
QLabel#metric{color:#facc15;font-size:22px;font-weight:700}
QComboBox,QSpinBox,QTableWidget{background:#222733;color:#e8edf5;border:1px solid #3a4352;border-radius:5px;padding:6px}
QPushButton{background:#eab308;color:#171a21;font-weight:700;border:0;border-radius:6px;padding:10px}
QPushButton:disabled{background:#596170;color:#c4cbd5}
QProgressBar{border:1px solid #3a4352;border-radius:5px;text-align:center}
QProgressBar::chunk{background:#eab308}
QHeaderView::section{background:#2a3040;color:#e8edf5;padding:6px;border:0}
"""


def feasible(r):
    return is_fully_verified(r)


class Worker(QObject):
    progress = Signal(int, str)
    done = Signal(object, float)
    failed = Signal(str)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings

    @Slot()
    def run(self):
        start = time.perf_counter()
        try:
            net = build_ieee33_network()

            def report(completed, total, result):
                pct = int(100 * completed / total) if total else 0
                msg = f"OpenDSS evaluations: {completed}/{total}" if total else "No graph-valid candidates."
                if result is not None:
                    msg += f" | converged: {result.converged}"
                self.progress.emit(pct, msg)

            results = evaluate_restoration_plans(
                net, faulted_branches={self.settings["fault"]},
                max_operations=self.settings["operations"], max_results=10,
                capacitor_bus=33 if self.settings["capacitor"] else None,
                capacitor_kvar=900 if self.settings["capacitor"] else 0,
                max_electrical_evaluations=self.settings["budget"],
                strategy=self.settings["strategy"], progress_callback=report,
            )
            self.done.emit(results, time.perf_counter() - start)
        except Exception:
            self.failed.emit(traceback.format_exc())


class Metric(QGroupBox):
    def __init__(self, title):
        super().__init__(title)
        layout = QVBoxLayout(self)
        self.value = QLabel("—")
        self.value.setObjectName("metric")
        self.note = QLabel("")
        self.note.setObjectName("muted")
        self.note.setWordWrap(True)
        layout.addWidget(self.value)
        layout.addWidget(self.note)


class GTDEWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GTDE | Feeder Restoration Engine")
        self.resize(1450, 900)
        self.results = []
        self.thread = None
        self.worker = None

        net = build_ieee33_network()
        branches = [b.branch_id for b in net.branches if b.normally_closed]

        base = QWidget()
        self.setCentralWidget(base)
        outer = QVBoxLayout(base)
        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel("⚡ GTDE — Feeder Restoration Engine")
        title.setStyleSheet("font-size:25px;font-weight:800;color:#facc15")
        sub = QLabel("IEEE 33-bus • Graph-based FLISR • OpenDSS validation")
        sub.setObjectName("muted")
        title_col.addWidget(title)
        title_col.addWidget(sub)
        header.addLayout(title_col)
        header.addStretch()
        self.status = QLabel("Ready")
        header.addWidget(self.status)
        outer.addLayout(header)

        split = QSplitter(Qt.Horizontal)
        outer.addWidget(split, 1)

        left = QWidget()
        left.setMaximumWidth(330)
        lv = QVBoxLayout(left)
        box = QGroupBox("Simulation settings")
        form = QFormLayout(box)
        self.fault = QComboBox()
        self.fault.addItems(branches)
        self.fault.setCurrentText("L10" if "L10" in branches else branches[0])
        self.strategy = QComboBox()
        self.strategy.addItems(["adaptive", "baseline"])
        self.operations = QSpinBox()
        self.operations.setRange(0, 5)
        self.operations.setValue(3)
        self.budget = QSpinBox()
        self.budget.setRange(1, 30)
        self.budget.setValue(10)
        self.capacitor = QCheckBox("Capacitor support: 900 kvar at bus 33")
        self.capacitor.setChecked(True)
        form.addRow("Faulted branch", self.fault)
        form.addRow("Search strategy", self.strategy)
        form.addRow("Maximum operations", self.operations)
        form.addRow("OpenDSS evaluation budget", self.budget)
        form.addRow("", self.capacitor)
        lv.addWidget(box)
        self.run_button = QPushButton("Run restoration")
        self.run_button.clicked.connect(self.start)
        lv.addWidget(self.run_button)
        self.progress = QProgressBar()
        lv.addWidget(self.progress)
        self.progress_text = QLabel("Choose settings and run.")
        self.progress_text.setObjectName("muted")
        self.progress_text.setWordWrap(True)
        lv.addWidget(self.progress_text)
        warning = QLabel("Thermal status remains UNASSESSED without verified branch ampacity ratings.")
        warning.setObjectName("muted")
        warning.setWordWrap(True)
        lv.addWidget(warning)
        lv.addStretch()
        split.addWidget(left)

        right = QWidget()
        rv = QVBoxLayout(right)
        cards = QHBoxLayout()
        self.m_feasible = Metric("Fully verified candidates")
        self.m_thermal_unassessed = Metric(
            "Electrical checks pass; thermal UNASSESSED"
        )
        self.m_load = Metric("Graph-connected load")
        self.m_voltage = Metric("Minimum voltage")
        self.m_loss = Metric("Real losses")
        for m in (
            self.m_feasible, self.m_thermal_unassessed,
            self.m_load, self.m_voltage, self.m_loss,
        ):
            cards.addWidget(m)
        rv.addLayout(cards)
        self.summary = QLabel("Run a restoration to inspect candidate plans.")
        self.summary.setWordWrap(True)
        rv.addWidget(self.summary)

        self.plot = QChartView()
        self.plot.setMinimumHeight(270)
        self.plot.setRenderHint(
            self.plot.renderHints()
        )
        rv.addWidget(self.plot, 1)

        self.table = QTableWidget(0, 16)
        self.table.setHorizontalHeaderLabels([
            "Rank", "Close ties", "Open branches", "Graph-connected kW",
            "Graph-connected %", "Operations", "Converged", "Voltage OK",
            "Graph consistent", "Electrical checks pass", "Fully verified",
            "Min V pu", "Max V pu", "Losses kW", "Thermal status",
            "Rejection reason",
        ])

        self.table.setAlternatingRowColors(True)
        rv.addWidget(self.table, 2)
        self.export = QPushButton("Export results CSV")
        self.export.setEnabled(False)
        self.export.clicked.connect(self.export_csv)
        rv.addWidget(self.export)
        split.addWidget(right)
        split.setSizes([330, 1080])
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        self.setStyleSheet(STYLE)
        self.show_chart(None)

    def start(self):
        if self.thread is not None and self.thread.isRunning():
            return
        settings = {
            "fault": self.fault.currentText(),
            "strategy": self.strategy.currentText(),
            "operations": self.operations.value(),
            "budget": self.budget.value(),
            "capacitor": self.capacitor.isChecked(),
        }
        self.run_button.setEnabled(False)
        self.export.setEnabled(False)
        self.progress.setValue(0)
        self.progress_text.setText("Starting search and OpenDSS…")
        self.status.setText("Running")
        self.thread = QThread(self)
        self.worker = Worker(settings)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.done.connect(self.on_done)
        self.worker.failed.connect(self.on_failed)
        self.worker.done.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.cleanup)
        self.thread.start()

    @Slot(int, str)
    def on_progress(self, pct, message):
        self.progress.setValue(pct)
        self.progress_text.setText(message)

    @Slot(object, float)
    def on_done(self, results, elapsed):
        self.results = list(results)
        summary = candidate_summary(self.results)
        verified = summary["fully_verified"]
        best = summary["selected"]
        self.m_feasible.value.setText(
            f"{len(verified)} / {len(self.results)}"
        )
        self.m_feasible.note.setText(
            "Requires convergence, voltage compliance, graph consistency, and thermal PASS"
        )
        self.m_thermal_unassessed.value.setText(
            f"{len(summary['thermal_unassessed'])} / {len(self.results)}"
        )
        self.m_thermal_unassessed.note.setText(
            "Passes convergence, voltage, and graph checks; thermal compliance is unassessed"
        )
        self.m_load.value.setText(f"{best.plan.restored_kw:,.1f} kW" if best else "None")
        self.m_load.note.setText(
            "Demand at source-connected buses; not necessarily voltage-compliant served load"
        )
        self.m_voltage.value.setText(f"{best.min_voltage_pu:.4f} pu" if best and best.min_voltage_pu is not None else "—")
        self.m_voltage.note.setText("Required: 0.95–1.05 pu")
        self.m_loss.value.setText(f"{best.real_losses_kw:.3f} kW" if best and best.real_losses_kw is not None else "—")
        self.m_loss.note.setText(f"Runtime: {elapsed:.2f} s")
        if best and summary["provisional"]:
            thermal_warning = (
                "Thermal compliance is unverified; do not treat this plan as fully validated."
                if best.thermal_status == "UNASSESSED"
                else f"Thermal status is {best.thermal_status}; do not treat this plan as fully validated."
            )
            self.summary.setText(
                f"Provisional recommendation (electrically feasible): close "
                f"{', '.join(best.plan.close_ties) or 'none'}; "
                f"open {', '.join(best.plan.open_branches) or 'none'}. "
                f"{thermal_warning}"
            )
        elif best:
            self.summary.setText(
                f"Fully verified candidate: close {', '.join(best.plan.close_ties) or 'none'}; "
                f"open {', '.join(best.plan.open_branches) or 'none'}."
            )
        else:
            self.summary.setText("No candidate passed all electrical checks. No recommendation is available.")
        self.table.setRowCount(len(self.results))
        for i, r in enumerate(self.results):

            values = [
                str(i + 1),
                ", ".join(r.plan.close_ties) or "—",
                ", ".join(r.plan.open_branches) or "—",
                f"{r.plan.restored_kw:.1f}",
                f"{r.plan.restoration_pct:.2f}%",
                str(r.plan.switching_operations),
                str(r.converged),
                str(r.voltage_feasible),
                str(r.graph_electrical_consistent),
                str(passes_electrical_checks(r)),
                str(feasible(r)),
                f"{r.min_voltage_pu:.4f}" if r.min_voltage_pu is not None else "—",
                f"{r.max_voltage_pu:.4f}" if r.max_voltage_pu is not None else "—",
                f"{r.real_losses_kw:.3f}" if r.real_losses_kw is not None else "—",
                r.thermal_status,
                r.rejection_reason or "—",
            ]

            for j, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, j, item)
        self.table.setWordWrap(False)
        self.table.setHorizontalScrollMode(
            self.table.ScrollMode.ScrollPerPixel
        )
        self.table.setVerticalScrollMode(
            self.table.ScrollMode.ScrollPerPixel
        )
        self.table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        self.table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        for column, width in {
            0: 55, 1: 110, 2: 130, 3: 100, 4: 105,
            5: 90, 6: 90, 7: 95, 8: 105, 9: 130,
            10: 105, 11: 90, 12: 90, 13: 100, 14: 150, 15: 240,
        }.items():
            self.table.setColumnWidth(column, width)
        self.show_chart(self.results)
        self.progress.setValue(100)
        self.progress_text.setText(
            f"Finished: {len(self.results)} candidates; "
            f"{len(verified)} fully verified; "
            f"{len(summary['thermal_unassessed'])} electrical pass / thermal unassessed."
        )
        self.status.setText(f"Completed in {elapsed:.2f}s")
        self.run_button.setEnabled(True)
        self.export.setEnabled(bool(self.results))

    @Slot(str)
    def on_failed(self, details):
        self.status.setText("Failed")
        self.progress_text.setText("Simulation failed; see error dialog.")
        QMessageBox.critical(self, "GTDE simulation failed", details[-4000:])
        self.run_button.setEnabled(True)

    @Slot()
    def cleanup(self):
        if self.worker:
            self.worker.deleteLater()
        if self.thread:
            self.thread.deleteLater()
        self.worker = None
        self.thread = None

    def show_chart(self, results):
        chart = QChart()
        chart.setTitle("Candidate electrical comparison")
        chart.setBackgroundBrush(Qt.GlobalColor.transparent)
        chart.setTitleBrush(Qt.GlobalColor.white)
        chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        chart.legend().hide()

        if results:
            bar_set = QBarSet("Real losses (kW)")
            bar_set.setColor(Qt.GlobalColor.green)

            categories = []

            for i, result in enumerate(results, start=1):
                # Qt Charts needs numeric values; use zero for missing losses.
                # The table remains the authoritative source for missing values.
                loss = result.real_losses_kw
                bar_set.append(float(loss) if loss is not None else 0.0)
                categories.append(f"#{i}")

            series = QBarSeries()
            series.append(bar_set)
            chart.addSeries(series)

            axis_x = QBarCategoryAxis()
            axis_x.append(categories)
            axis_x.setLabelsColor(Qt.GlobalColor.white)
            chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            series.attachAxis(axis_x)

            axis_y = QValueAxis()
            axis_y.setTitleText("Real losses (kW)")
            axis_y.setLabelsColor(Qt.GlobalColor.white)
            axis_y.setTitleBrush(Qt.GlobalColor.white)
            axis_y.setRange(
                0,
                max(
                    10.0,
                    max(
                        (r.real_losses_kw or 0.0 for r in results),
                        default=0.0,
                    ) * 1.15,
                ),
            )
            chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
            series.attachAxis(axis_y)

        else:
            chart.setTitle("Run restoration to view results")

        self.plot.setChart(chart)
        self.plot.setStyleSheet("background-color: #171a21;")
        self.plot.setBackgroundBrush(Qt.GlobalColor.transparent)

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export GTDE results", "gtde_restoration_results.csv", "CSV files (*.csv)")
        if not path:
            return
        rows = []
        for i, r in enumerate(self.results, 1):
            rows.append({
                "rank": i, "close_ties": ";".join(r.plan.close_ties),
                "open_branches": ";".join(r.plan.open_branches),
                # Legacy columns retained for exported-CSV compatibility.
                "restored_kw": r.plan.restored_kw,
                "restoration_pct": r.plan.restoration_pct,
                "graph_connected_load_kw": r.plan.restored_kw,
                "graph_connected_restoration_pct": r.plan.restoration_pct,
                "switching_operations": r.plan.switching_operations, "converged": r.converged,
                "voltage_feasible": r.voltage_feasible,
                "graph_electrical_consistent": r.graph_electrical_consistent,
                "electrical_checks_pass": passes_electrical_checks(r),
                "fully_verified": feasible(r),
                "min_voltage_pu": r.min_voltage_pu, "max_voltage_pu": r.max_voltage_pu,
                "real_losses_kw": r.real_losses_kw, "thermal_status": r.thermal_status,
                "rejection_reason": r.rejection_reason,
            })
        pd.DataFrame(rows).to_csv(path, index=False)
        self.status.setText(f"Exported {path}")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GTDE")
    window = GTDEWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
