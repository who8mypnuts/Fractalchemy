from PySide6.QtCore import QPointF

from hueclid.model import Gradient
from hueclid.ui.main_window import MainWindow
from hueclid.widgets.mapping import PositionMapper


def test_mapper_round_trips():
    m = PositionMapper(width=400, margin=12)
    for pos in (0.0, 0.25, 1.0):
        assert abs(m.to_position(m.to_x(pos)) - pos) < 1e-9
    assert m.to_position(-100) == 0.0 and m.to_position(10_000) == 1.0


def test_window_loads_and_nodes_follow_drag(qapp, samples):
    window = MainWindow()
    window.resize(800, 300)
    window.show()
    window.files.open_path(samples / "sample gradients" / "saturated rainbox.gradient")
    assert "rainbow" in window.lblGradientName.text()

    window.document.replace(Gradient.from_colors("sparse", [(0, 0, 0), (50, 50, 50), (255, 0, 0), (0, 255, 0), (0, 0, 255)]))
    nodes = window.gradientEditor.nodes
    index = 1
    center = nodes.node_center(index)
    assert nodes.node_at(center) == index
    assert nodes.node_at(QPointF(center.x() + 60, center.y())) == -1

    new_index = window.document.move_stop(index, nodes.mapper().to_position(center.x() + 60))
    assert new_index == index
    assert abs(nodes.node_center(index).x() - (center.x() + 60)) < 1e-6
    assert window.document.modified
    assert nodes.node_at(center) == -1  # it moved away


def test_mouse_drag_moves_node_through_qt_events(qapp):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    window = MainWindow()
    window.resize(800, 300)
    window.show()
    window.document.replace(Gradient.from_colors("sparse", [(0, 0, 0), (255, 0, 0), (255, 255, 255)]))
    nodes = window.gradientEditor.nodes
    start = nodes.node_center(1).toPoint()
    before = window.document.gradient.stops[1].position

    QTest.mousePress(nodes, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    assert window.document.selected_index == 1
    QTest.mouseMove(nodes, start + QPointF(80, 0).toPoint())
    QTest.mouseRelease(nodes, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start + QPointF(80, 0).toPoint())

    assert window.document.gradient.stops[1].position > before
    assert "Node 2/3" in window.statusBar().currentMessage()


def test_mouse_drag_past_other_nodes_keeps_them_in_place(qapp):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    window = MainWindow()
    window.resize(800, 300)
    window.show()
    colors = [(0, 0, 0), (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]
    window.document.replace(Gradient.from_colors("sparse", colors))
    nodes = window.gradientEditor.nodes
    start = nodes.node_center(1).toPoint()
    far_right = nodes.node_center(3).toPoint() + QPointF(40, 0).toPoint()

    QTest.mousePress(nodes, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    for step in range(1, 11):  # sweep across nodes 2 and 3 in small moves
        QTest.mouseMove(nodes, start + (far_right - start) * step / 10)
    QTest.mouseRelease(nodes, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, far_right)

    stops = window.document.gradient.stops
    assert [s.color for s in stops] == [(0, 0, 0), (0, 255, 0), (0, 0, 255), (255, 0, 0), (255, 255, 255)]
    assert [round(s.position, 3) for s in stops if s.color != (255, 0, 0)] == [0.0, 0.5, 0.75, 1.0]
    assert window.document.selected_index == 3  # selection followed the dragged node
    assert "Node 4/5" in window.statusBar().currentMessage()
