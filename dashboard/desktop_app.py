"""GTDE native desktop UI. Run from repository root: python -m dashboard.desktop_app"""
import sys
import time
import traceback
import json
import math
from PySide6.QtCharts import (
    QChart,
    QChartView,
    QBarSeries,
    QBarSet,
    QBarCategoryAxis,
    QValueAxis,
)
import pandas as pd
from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
from PySide6.QtGui import QBrush, QPen, QFont
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QProgressBar,
    QSpinBox, QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QGraphicsView, QGraphicsScene, QScrollArea, QGridLayout, QSizePolicy,
    QHeaderView,
    QPlainTextEdit,
)

from src.ieee33_network import build_ieee33_network
from dashboard.evaluation_runner import evaluate_restoration, compare_restoration_strategies
from dashboard.topology import topology_state, bus_positions, VIEWS, supported_faults
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


COMPARISON_METRICS = (
    ("Candidates evaluated", "Candidates returned", 0, ""),
    ("Electrically feasible candidates", "Electrically feasible candidates", 0, ""),
    ("Fully verified candidates", "Fully verified candidates", 0, ""),
    ("Graph-connected load", "Best graph-connected load (kW)", 1, " kW"),
    ("Minimum voltage", "Minimum voltage (pu)", 4, " p.u."),
    ("Real power losses", "Real losses (kW)", 2, " kW"),
    ("Switching operations", "Switching operations", 0, ""),
    ("Thermal verification", "Thermal status", None, ""),
)

COMPARISON_OUTCOME_KEYS = tuple(dict.fromkeys(
    key for _, key, _, _ in COMPARISON_METRICS
)) + ("Graph-connected restoration (%)",)


def format_comparison_value(value, precision=None, suffix=""):
    """Format comparison values without leaking null or nonfinite numbers."""
    if value is None:
        return "—"
    if precision is None:
        return str(value) if str(value).strip() else "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(number):
        return "—"
    if precision == 0:
        return f"{int(number)}"
    return f"{number:.{precision}f}{suffix}"


def _same_outcome_value(first, second):
    def missing(value):
        if value is None:
            return True
        try:
            return not math.isfinite(float(value))
        except (TypeError, ValueError):
            return False

    if missing(first) or missing(second):
        return missing(first) and missing(second)
    try:
        a, b = float(first), float(second)
        return math.isclose(a, b, rel_tol=0, abs_tol=1e-9)
    except (TypeError, ValueError):
        return first == second


def comparison_results_equal(rows):
    if len(rows) < 2:
        return False
    baseline, adaptive = rows[0], rows[1]
    return all(
        _same_outcome_value(baseline.get(key), adaptive.get(key))
        for key in COMPARISON_OUTCOME_KEYS
    )


def _metric_delta(first, second):
    try:
        a, b = float(first), float(second)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(a) or not math.isfinite(b):
        return None
    return b - a


def comparison_status_text(rows):
    if comparison_results_equal(rows):
        return "No measurable difference between strategies for this scenario."
    if len(rows) < 2:
        return "Comparison did not return both strategies."
    baseline, adaptive = rows[:2]
    changed = []
    for key in COMPARISON_OUTCOME_KEYS:
        if not _same_outcome_value(baseline.get(key), adaptive.get(key)):
            label = next((title for title, metric_key, *_ in COMPARISON_METRICS if metric_key == key), key)
            changed.append(label)
    return "Measured outcomes differ: " + ", ".join(dict.fromkeys(changed)) + "."


def comparison_delta_text(first, second, precision, suffix=""):
    if _same_outcome_value(first, second):
        if first is None or (isinstance(first, float) and not math.isfinite(first)):
            return "Unavailable in both strategies."
        return "Equal in both strategies."
    delta = _metric_delta(first, second)
    if delta is None:
        return "Delta unavailable (measurement missing)."
    delta_text = format_comparison_value(abs(delta), precision, suffix)
    sign = "+" if delta > 0 else "−" if delta < 0 else ""
    below_precision = " (difference is below displayed precision)" if delta != 0 and float(format_comparison_value(abs(delta), precision) or 0) == 0 else ""
    return f"Adaptive − Baseline: {sign}{delta_text}{below_precision}."


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
            results = evaluate_restoration(
                faulted_branches={self.settings["fault"]},
                max_operations=self.settings["operations"], max_results=10,
                capacitor_bus=33 if self.settings["capacitor"] else None,
                capacitor_kvar=900 if self.settings["capacitor"] else 0,
                max_electrical_evaluations=self.settings["budget"],
                strategy=self.settings["strategy"],
            )
            self.progress.emit(100, f"Evaluation complete: {len(results)} candidate(s).")
            self.done.emit(results, time.perf_counter() - start)
        except Exception:
            self.failed.emit(traceback.format_exc())


class CompareWorker(QObject):
    done = Signal(object, float)
    failed = Signal(str)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings

    @Slot()
    def run(self):
        started = time.perf_counter()
        try:
            self.done.emit(compare_restoration_strategies(**self.settings), time.perf_counter() - started)
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


class StrategyMetrics(QGroupBox):
    def __init__(self, strategy, parent=None):
        super().__init__(strategy, parent)
        form = QFormLayout(self)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.values = {}
        for title, key, precision, suffix in COMPARISON_METRICS:
            value = QLabel("—")
            value.setWordWrap(True)
            value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.values[key] = value
            form.addRow(title, value)

    def set_record(self, record):
        for _label, key, precision, suffix in COMPARISON_METRICS:
            self.values[key].setText(format_comparison_value(record.get(key), precision, suffix))


def _json_safe(value):
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


class StrategyComparisonPanel(QWidget):
    """Responsive, factual summary of the existing strategy comparison rows."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(0)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        self.status = QLabel("Run a strategy comparison to see measured outcomes.")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("font-size:16px;font-weight:700;color:#e8edf5")
        layout.addWidget(self.status)

        self.card_row = QGridLayout()
        self.card_row.setHorizontalSpacing(10)
        self.baseline_card = StrategyMetrics("Baseline")
        self.adaptive_card = StrategyMetrics("Adaptive")
        self.card_row.addWidget(self.baseline_card, 0, 0)
        self.card_row.addWidget(self.adaptive_card, 0, 1)
        layout.addLayout(self.card_row)

        self.differences = QGroupBox("Measured differences")
        diff_layout = QVBoxLayout(self.differences)
        self.delta_labels = {}
        for title, key, precision, suffix in (
            ("Graph-connected load", "Best graph-connected load (kW)", 1, " kW"),
            ("Real power losses", "Real losses (kW)", 2, " kW"),
            ("Minimum voltage", "Minimum voltage (pu)", 4, " p.u."),
            ("Switching operations", "Switching operations", 0, ""),
        ):
            row = QHBoxLayout()
            name = QLabel(title)
            name.setMinimumWidth(150)
            value = QLabel("—")
            value.setWordWrap(True)
            row.addWidget(name)
            row.addWidget(value, 1)
            diff_layout.addLayout(row)
            self.delta_labels[key] = (value, precision, suffix)
        self.load_note = QLabel("Graph-connected load does not necessarily mean voltage-compliant served load.")
        self.load_note.setObjectName("muted")
        self.load_note.setWordWrap(True)
        diff_layout.addWidget(self.load_note)
        layout.addWidget(self.differences)

        self.details = QGroupBox("Technical details")
        self.details.setCheckable(True)
        self.details.setChecked(False)
        details_layout = QVBoxLayout(self.details)
        self.raw_details = QPlainTextEdit()
        self.raw_details.setReadOnly(True)
        self.raw_details.setMaximumHeight(180)
        self.raw_details.setVisible(False)
        details_layout.addWidget(self.raw_details)
        self.details.toggled.connect(self.raw_details.setVisible)
        layout.addWidget(self.details)
        self.setVisible(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.width() < 760:
            self.card_row.addWidget(self.baseline_card, 0, 0)
            self.card_row.addWidget(self.adaptive_card, 1, 0)
        else:
            self.card_row.addWidget(self.baseline_card, 0, 0)
            self.card_row.addWidget(self.adaptive_card, 0, 1)

    def set_results(self, rows, elapsed=None):
        if len(rows) < 2:
            raise ValueError("Strategy comparison requires baseline and adaptive records.")
        self.records = list(rows)
        baseline, adaptive = self.records[:2]
        self.baseline_card.set_record(baseline)
        self.adaptive_card.set_record(adaptive)
        self.status.setText(comparison_status_text(self.records))

        for key, (label, precision, suffix) in self.delta_labels.items():
            first, second = baseline.get(key), adaptive.get(key)
            label.setText(comparison_delta_text(first, second, precision, suffix))

        details = {
            "Baseline": _json_safe(baseline),
            "Adaptive": _json_safe(adaptive),
        }
        if elapsed is not None:
            details["Comparison runtime (s)"] = round(elapsed, 3)
        self.raw_details.setPlainText(json.dumps(details, indent=2, allow_nan=False, default=str))
        self.setVisible(True)


class NetworkView(QGraphicsView):
    """Interactive model-driven single-line diagram."""
    busSelected = Signal(int)

    def __init__(self, net, parent=None):
        super().__init__(parent)
        self.net = net
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setMinimumSize(480, 190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setBackgroundBrush(QBrush(Qt.GlobalColor.white))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.refresh("L10", None, "Pre-fault", 1)

    def refresh(self, fault, plan, view, selected_bus):
        self.scene.clear()
        state = topology_state(self.net, {fault}, plan, view)
        positions = bus_positions(self.net)
        scale = 37
        xy = {bus: (35 + x * scale, 45 + (3-y) * 58) for bus, (x,y) in positions.items()}
        colors = {"faulted":"#dc2626", "normally open tie":"#2563eb", "opened by candidate":"#d97706", "closed by candidate":"#16a34a", "open":"#a1a1aa", "energized":"#64748b", "de-energized segment":"#cbd5e1"}
        for branch in state["branches"]:
            x1,y1=xy[branch["u"]]; x2,y2=xy[branch["v"]]
            color = "#9333ea" if branch["path"] else colors[branch["state"]]
            pen=QPen(Qt.GlobalColor.black if branch["path"] else Qt.GlobalColor.gray, 3 if branch["path"] else 1.6)
            pen.setColor(color)
            if branch["state"] in ("faulted","normally open tie","opened by candidate"):
                pen.setStyle(Qt.PenStyle.DashLine)
            self.scene.addLine(x1,y1,x2,y2,pen)
            self.scene.addText(branch["branch_id"], QFont("Arial",7)).setPos((x1+x2)/2,(y1+y2)/2)
        for bus,(x,y) in xy.items():
            color = "#f59e0b" if bus==selected_bus else "#dc2626" if bus==self.net.source_bus else "#94a3b8" if bus in state["disconnected_buses"] else "#0f766e"
            dot=self.scene.addEllipse(x-7,y-7,14,14,QPen(Qt.GlobalColor.white),QBrush(color))
            dot.setData(0,bus); dot.setToolTip(f"Bus {bus} · {self.net.buses[bus].get('load_kw',0)} kW")
            label = self.scene.addText(str(bus),QFont("Arial",8))
            label.setPos(x-6,y-23)
            label.setData(0, bus)
        self.scene.setSceneRect(self.scene.itemsBoundingRect().adjusted(-20,-15,20,15))
        self._fit_scene()

    def _fit_scene(self):
        rect = self.scene.sceneRect()
        if rect.isEmpty() or self.viewport().width() <= 0 or self.viewport().height() <= 0:
            return
        sx = (self.viewport().width() - 12) / rect.width()
        sy = (self.viewport().height() - 12) / rect.height()
        # Preserve a readable schematic scale on narrow viewports; scrollbars
        # provide access to the full model instead of shrinking labels away.
        scale = min(1.35, max(0.82, min(sx, sy)))
        self.resetTransform()
        self.scale(scale, scale)
        self.centerOn(rect.center())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_scene()

    def mousePressEvent(self, event):
        item=self.itemAt(event.position().toPoint())
        while item and item.data(0) is None: item=item.parentItem()
        if item and item.data(0) is not None: self.busSelected.emit(int(item.data(0)))
        super().mousePressEvent(event)


class GTDEWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GTDE | Feeder Restoration Engine")
        self.resize(1320, 820)
        self.setMinimumSize(780, 560)
        self.results = []
        self.selected_index = 0
        self.selected_bus = 1
        self.net = build_ieee33_network()
        self.thread = None
        self.worker = None

        net = self.net
        branches = supported_faults(net)

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

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        outer.addWidget(split, 1)

        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(8, 8, 8, 8)
        box = QGroupBox("Simulation settings")
        form = QFormLayout(box)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
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
        self.capacitor = QCheckBox("Capacitor support")
        self.capacitor.setChecked(True)
        form.addRow("Faulted branch", self.fault)
        form.addRow("Search strategy", self.strategy)
        form.addRow("Maximum operations", self.operations)
        form.addRow("OpenDSS evaluation budget", self.budget)
        form.addRow("", self.capacitor)
        capacitor_note = QLabel("900 kvar at bus 33 when enabled")
        capacitor_note.setObjectName("muted")
        capacitor_note.setWordWrap(True)
        form.addRow("", capacitor_note)
        lv.addWidget(box)
        self.run_button = QPushButton("Run restoration")
        self.run_button.clicked.connect(self.start)
        lv.addWidget(self.run_button)
        self.compare_button = QPushButton("Compare baseline vs adaptive")
        self.compare_button.clicked.connect(self.start_comparison)
        lv.addWidget(self.compare_button)
        self.progress = QProgressBar()
        lv.addWidget(self.progress)
        self.progress_text = QLabel("Choose settings and run.")
        self.progress_text.setObjectName("muted")
        self.progress_text.setWordWrap(True)
        lv.addWidget(self.progress_text)
        self.network_view_choice = QComboBox()
        self.network_view_choice.addItems(VIEWS)
        lv.addWidget(QLabel("Network state"))
        lv.addWidget(self.network_view_choice)
        self.bus_info = QLabel("Select a bus in the diagram to inspect its load and priority.")
        self.bus_info.setWordWrap(True)
        self.bus_info.setObjectName("muted")
        lv.addWidget(self.bus_info)
        warning = QLabel("Thermal status remains UNASSESSED without verified branch ampacity ratings.")
        warning.setObjectName("muted")
        warning.setWordWrap(True)
        lv.addWidget(warning)
        lv.addStretch()
        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        controls_scroll.setWidget(left)
        controls_scroll.setMinimumWidth(220)
        controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        split.addWidget(controls_scroll)

        right = QWidget()
        rv = QVBoxLayout(right)
        rv.setContentsMargins(8, 8, 8, 8)
        cards = QGridLayout()
        cards.setHorizontalSpacing(8)
        cards.setVerticalSpacing(6)
        self.m_feasible = Metric("Fully verified candidates")
        self.m_thermal_unassessed = Metric(
            "Electrical checks pass; thermal UNASSESSED"
        )
        self.m_load = Metric("Graph-connected load")
        self.m_voltage = Metric("Minimum voltage")
        self.m_loss = Metric("Real losses")
        metrics = (
            self.m_feasible, self.m_thermal_unassessed,
            self.m_load, self.m_voltage, self.m_loss,
        )
        for index, metric in enumerate(metrics):
            metric.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
            metric.setMinimumWidth(130)
            cards.addWidget(metric, index // 3, index % 3)
        rv.addLayout(cards)
        self.summary = QLabel("Run a restoration to inspect candidate plans.")
        self.summary.setWordWrap(True)
        rv.addWidget(self.summary)
        self.comparison_panel = StrategyComparisonPanel()
        rv.addWidget(self.comparison_panel)

        self.network = NetworkView(self.net)
        self.network.busSelected.connect(self.select_bus)
        network_panel = QWidget()
        network_layout = QVBoxLayout(network_panel)
        network_layout.setContentsMargins(0, 0, 0, 0)
        network_layout.addWidget(self.network, 1)
        self.network_legend = QLabel(
            "🔴 Fault/source   ·   🟦 Energized   ·   ⚪ Disconnected   ·   "
            "🔵 Normally open tie   ·   🟢 Candidate close   ·   🟠 Candidate open   ·   🟣 Recovery path"
        )
        self.network_legend.setWordWrap(True)
        self.network_legend.setObjectName("muted")
        network_layout.addWidget(self.network_legend)
        self.fault.currentTextChanged.connect(self.refresh_network)
        self.network_view_choice.currentTextChanged.connect(self.refresh_network)

        self.plot = QChartView()
        self.plot.setMinimumHeight(190)
        self.plot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.table = QTableWidget(0, 16)
        self.table.setHorizontalHeaderLabels([
            "Rank", "Close ties", "Open branches", "Graph-connected kW",
            "Graph-connected %", "Operations", "Converged", "Voltage OK",
            "Graph consistent", "Electrical checks pass", "Fully verified",
            "Min V pu", "Max V pu", "Losses kW", "Thermal status",
            "Rejection reason",
        ])

        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self.select_candidate_row)
        self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.table.setMinimumHeight(170)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Keep the table inside the results viewport; users can scroll its own
        # horizontal bar rather than forcing the surrounding comparison panel wider.
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setDefaultSectionSize(105)
        self.table.setColumnWidth(0, 56)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.export = QPushButton("Export results CSV")
        self.export.setEnabled(False)
        self.export.clicked.connect(self.export_csv)
        exports = QHBoxLayout()
        exports.addWidget(self.export)
        self.compare_export = QPushButton("Export strategy comparison CSV")
        self.compare_export.setEnabled(False)
        self.compare_export.clicked.connect(self.export_comparison)
        exports.addWidget(self.compare_export)
        rv.addLayout(exports)

        results_panel = QWidget()
        results_layout = QVBoxLayout(results_panel)
        results_layout.setContentsMargins(0, 0, 0, 0)
        results_layout.addWidget(self.plot, 1)
        results_layout.addWidget(self.table, 2)
        results_panel.setMinimumHeight(390)
        content_split = QSplitter(Qt.Orientation.Vertical)
        content_split.setChildrenCollapsible(False)
        content_split.addWidget(network_panel)
        content_split.addWidget(results_panel)
        content_split.setStretchFactor(0, 1)
        content_split.setStretchFactor(1, 2)
        rv.addWidget(content_split, 1)

        results_scroll = QScrollArea()
        results_scroll.setWidgetResizable(True)
        results_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        results_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        results_scroll.setWidget(right)
        results_scroll.setMinimumWidth(520)
        split.addWidget(results_scroll)
        split.setSizes([270, 1050])
        split.setCollapsible(0, False)
        split.setCollapsible(1, False)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        self.setStyleSheet(STYLE)
        self.show_chart(None)

    def start_comparison(self):
        if self.thread is not None and self.thread.isRunning():
            return
        self.compare_button.setEnabled(False)
        self.progress.setValue(0)
        self.progress_text.setText("Comparing strategies in the background worker…")
        settings = {"faulted_branches": {self.fault.currentText()}, "max_operations": self.operations.value(), "evaluation_budget": self.budget.value(), "capacitor_bus": 33 if self.capacitor.isChecked() else None, "capacitor_kvar": 900 if self.capacitor.isChecked() else 0}
        self.thread = QThread(self)
        self.worker = CompareWorker(settings)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.done.connect(self.on_comparison_done)
        self.worker.failed.connect(self.on_failed)
        self.worker.done.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.cleanup)
        self.thread.start()

    @Slot(object, float)
    def on_comparison_done(self, rows, elapsed):
        self.comparison = rows
        self.compare_export.setEnabled(bool(rows))
        self.comparison_panel.set_results(rows, elapsed)
        self.progress.setValue(100)
        self.progress_text.setText("Comparison complete. See measured results in the comparison panel.")
        self.status.setText("Comparison complete")
        self.compare_button.setEnabled(True)

    def export_comparison(self):
        if not getattr(self, "comparison", None):
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export strategy comparison", "gtde_strategy_comparison.csv", "CSV files (*.csv)")
        if path:
            pd.DataFrame(self.comparison).to_csv(path, index=False)
            self.status.setText(f"Exported {path}")

    def refresh_network(self, *_):
        plan = self.results[self.selected_index].plan if self.results and self.network_view_choice.currentText() == "Candidate restoration" else None
        self.network.refresh(self.fault.currentText(), plan, self.network_view_choice.currentText(), self.selected_bus)

    def select_bus(self, bus):
        self.selected_bus = bus
        info = self.net.buses[bus]
        priority = info.get("load_priority_weight")
        priority_text = f"priority {priority}" if priority is not None else "priority unavailable in this model"
        self.bus_info.setText(f"Bus {bus} · {float(info.get('load_kw', 0)):.1f} kW demand · {priority_text}")
        self.refresh_network()

    def select_candidate_row(self):
        row = self.table.currentRow()
        if row >= 0 and row < len(self.results):
            self.selected_index = row
            self.refresh_network()

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
        self.selected_index = 0
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
        self.show_chart(self.results)
        self.refresh_network()
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
                loss = result.real_losses_kw
                if loss is not None:
                    bar_set.append(float(loss))
                    categories.append(f"#{i}")

            if categories:
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
                    max(10.0, max(float(r.real_losses_kw) for r in results if r.real_losses_kw is not None) * 1.15),
                )
                chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
                series.attachAxis(axis_y)
            else:
                chart.setTitle("Real losses unavailable for these candidates")

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
