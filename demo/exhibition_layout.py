"""Presentation layout using the existing controls and their signal connections."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QWidget, QLabel, QPushButton, QProgressBar,
    QScrollArea, QHBoxLayout,
)
from samurai_guide import SamuraiGuide


def simplify_screen(window):
    root = window.centralWidget().layout()
    window.detail_dialog = QDialog(window)
    window.detail_dialog.setWindowTitle('設定・個別操作・詳細表示')
    window.detail_dialog.resize(920, 850)
    detail = QVBoxLayout(window.detail_dialog)
    detail.addWidget(window.banner)
    if hasattr(window, 'connection_row'):
        root.removeItem(window.connection_row)
        detail.addLayout(window.connection_row)
        detail.addWidget(window.saved_ports_label)
        root.removeItem(window.launch_row)
    detail.addWidget(window.operation_panel, 1)

    # Remove the plot tools from the presentation, retaining all their actions.
    window.plot_actions.parent().removeItem(window.plot_actions)
    detail.addLayout(window.plot_actions)
    if hasattr(window, 'hold_panel'):
        detail.addWidget(window.hold_panel)
    detail.addWidget(window.details_toggle)
    detail.addWidget(window.footer)
    close = QPushButton('閉じる')
    close.clicked.connect(window.detail_dialog.close)
    detail.addWidget(close)

    panel = QWidget()
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 8, 0)
    layout.setSpacing(8)
    window.samurai_guide = SamuraiGuide()
    layout.addWidget(window.samurai_guide)
    window.phase.setStyleSheet('font-size: 14px; font-weight: bold; padding: 4px;')
    layout.addWidget(window.phase)
    layout.addWidget(window.progress)
    window.active_step_progress = QProgressBar()
    layout.addWidget(window.active_step_progress)
    if hasattr(window, 'recipe_progress'):
        layout.addWidget(window.measure_progress)
        layout.addWidget(window.recipe_progress)
        window.recipe_eta.setStyleSheet('font-size: 14px; color: #FFE08A; padding: 4px;')
        layout.addWidget(window.recipe_eta)
    layout.addWidget(window.chip_note)
    layout.addWidget(window.chip_button)
    layout.addStretch()
    # Keep the essential actions outside the scrolling guide, always reachable.
    actions = QHBoxLayout()
    root.addLayout(actions)
    if hasattr(window, 'launch_button'):
        actions.addWidget(window.launch_button)
    actions.addWidget(window.apply_button)
    actions.addWidget(window.batch_button)
    if hasattr(window, 'recipe_start'):
        actions.addWidget(window.recipe_edit)
        actions.addWidget(window.recipe_start)
    else:
        actions.addWidget(window.measure_button)
    actions.addWidget(window.stop_button)
    window.detail_button = QPushButton('設定・詳細操作')
    window.detail_button.clicked.connect(window.detail_dialog.show)
    window.detail_button.clicked.connect(window.detail_dialog.raise_)
    actions.addWidget(window.detail_button)
    sidebar = QScrollArea()
    sidebar.setWidgetResizable(True)
    sidebar.setWidget(panel)
    sidebar.setMinimumWidth(290)
    sidebar.setMaximumWidth(320)
    window.screen_split.insertWidget(0, sidebar)
    window.screen_split.setSizes([310, 995])
    window.screen_split.setStretchFactor(0, 0)
    window.screen_split.setStretchFactor(1, 1)
    window.current_plot.setMaximumHeight(16777215)
    window.hardware_box.setMaximumHeight(16777215)

    def update_progress():
        window.samurai_guide.sync(window)
        source = {
            4: window.first_cut_progress,
            5: window.motor_training_progress,
            6: window.piezo_training_progress,
            9: window.calibration_progress,
        }.get(window.state.active)
        window.active_step_progress.setVisible(source is not None)
        if source is not None:
            window.active_step_progress.setRange(source.minimum(), source.maximum())
            window.active_step_progress.setValue(source.value())
            window.active_step_progress.setFormat(source.format())

    window.plot_timer.timeout.connect(update_progress)
    update_progress()
