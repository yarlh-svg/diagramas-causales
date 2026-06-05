"""
Diagramas Causales - Teoría General de Sistemas y Dinámica de Sistemas
Aplicación visual interactiva para construir y analizar diagramas causales.
"""

import sys
import json
import math
import copy
from collections import defaultdict

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QInputDialog, QMessageBox,
    QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsTextItem, QGraphicsPathItem,
    QGraphicsDropShadowEffect, QToolBar, QAction, QFrame, QScrollArea,
    QSizePolicy, QMenuBar, QMenu, QStatusBar, QGraphicsRectItem
)
from PyQt5.QtCore import (
    Qt, QPointF, QRectF, QLineF, QTimer, pyqtSignal, QObject,
    QPropertyAnimation, QEasingCurve, QSize
)
from PyQt5.QtGui import (
    QPainter, QPen, QBrush, QColor, QFont, QPainterPath, QPolygonF,
    QLinearGradient, QRadialGradient, QPixmap, QImage, QTransform,
    QFontMetrics, QPalette, QIcon
)


# ──────────────────────────────────────────────
#  PALETA DE COLORES GLOBAL
# ──────────────────────────────────────────────
class Palette:
    BG_DARK       = QColor("#0F1117")
    BG_PANEL      = QColor("#181C27")
    BG_CARD       = QColor("#1E2235")
    ACCENT_BLUE   = QColor("#4B9FFF")
    ACCENT_CYAN   = QColor("#00D4C8")
    ACCENT_PURPLE = QColor("#9B6DFF")
    NODE_GRAD_A   = QColor("#2A3A6E")
    NODE_GRAD_B   = QColor("#1A2550")
    NODE_BORDER   = QColor("#4B9FFF")
    NODE_HOVER    = QColor("#5BAFFF")
    NODE_SELECT   = QColor("#FFD166")
    EDGE_POS      = QColor("#06D6A0")
    EDGE_NEG      = QColor("#EF476F")
    CYCLE_R       = QColor("#FF9F1C")
    CYCLE_B       = QColor("#2EC4B6")
    TEXT_PRIMARY  = QColor("#E8EAF6")
    TEXT_SECONDARY= QColor("#8892B0")
    GRID_LINE     = QColor("#1A1F30")
    GRID_DOT      = QColor("#252A3F")
    BTN_NORMAL    = QColor("#252A3F")
    BTN_HOVER     = QColor("#2E3450")
    BTN_ACTIVE    = QColor("#4B9FFF")
    BTN_DANGER    = QColor("#EF476F")
    SHADOW        = QColor(0, 0, 0, 120)


# ──────────────────────────────────────────────
#  NODO (QGraphicsItem)
# ──────────────────────────────────────────────
class CausalNode(QGraphicsItem):
    """Representa una variable del diagrama causal como nodo visual."""

    TYPE = QGraphicsItem.UserType + 1

    def __init__(self, node_id: str, label: str, x: float, y: float):
        super().__init__()
        self.node_id  = node_id
        self.label    = label
        self.width    = 140
        self.height   = 48
        self.radius   = 24          # esquinas redondeadas
        self._hovered  = False
        self._selected_flag = False
        self.edges_out = []         # aristas salientes
        self.edges_in  = []         # aristas entrantes

        self.setPos(x, y)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        self.setZValue(10)

        # sombra
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(Palette.SHADOW)
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def type(self):
        return CausalNode.TYPE

    def boundingRect(self) -> QRectF:
        m = 6  # margen extra para sombra/glow
        return QRectF(-self.width / 2 - m, -self.height / 2 - m,
                      self.width + 2 * m, self.height + 2 * m)

    def shape(self):
        path = QPainterPath()
        path.addRoundedRect(-self.width / 2, -self.height / 2,
                            self.width, self.height, self.radius, self.radius)
        return path

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(-self.width / 2, -self.height / 2,
                      self.width, self.height)

        # ── Gradiente de fondo ──
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        grad.setColorAt(0, Palette.NODE_GRAD_A)
        grad.setColorAt(1, Palette.NODE_GRAD_B)
        painter.setBrush(QBrush(grad))

        # ── Borde ──
        if self.isSelected() or self._selected_flag:
            pen_color = Palette.NODE_SELECT
            pen_width = 2.5
        elif self._hovered:
            pen_color = Palette.NODE_HOVER
            pen_width = 2.0
        else:
            pen_color = Palette.NODE_BORDER
            pen_width = 1.5

        painter.setPen(QPen(pen_color, pen_width))
        painter.drawRoundedRect(rect, self.radius, self.radius)

        # ── Brillo superior sutil ──
        glow_rect = QRectF(-self.width / 2 + 4, -self.height / 2 + 2,
                           self.width - 8, self.height / 2)
        glow_grad = QLinearGradient(glow_rect.topLeft(), glow_rect.bottomLeft())
        glow_grad.setColorAt(0, QColor(255, 255, 255, 18))
        glow_grad.setColorAt(1, QColor(255, 255, 255, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(glow_grad))
        painter.drawRoundedRect(glow_rect, self.radius - 2, self.radius - 2)

        # ── Texto ──
        font = QFont("Segoe UI", 10, QFont.DemiBold)
        painter.setFont(font)
        painter.setPen(QPen(Palette.TEXT_PRIMARY))
        painter.drawText(rect, Qt.AlignCenter, self.label)

    def itemChange(self, change, value):
        # Actualizar aristas cuando el nodo se mueve
        if change == QGraphicsItem.ItemPositionHasChanged:
            for edge in self.edges_out + self.edges_in:
                edge.update_position()
        return super().itemChange(change, value)

    def hoverEnterEvent(self, event):
        self._hovered = True
        self.update()

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self.update()

    def mouseDoubleClickEvent(self, event):
        # Editar nombre con doble clic
        scene = self.scene()
        if scene and hasattr(scene, 'request_rename'):
            scene.request_rename(self)

    def get_border_point(self, target_pos: QPointF) -> QPointF:
        """Devuelve el punto del borde del nodo más cercano a target_pos."""
        center = self.scenePos()
        dx = target_pos.x() - center.x()
        dy = target_pos.y() - center.y()
        angle = math.atan2(dy, dx)

        # Intersección aproximada con el rectángulo redondeado
        hw = self.width / 2
        hh = self.height / 2
        if abs(dx) < 1e-6:
            bx, by = 0, math.copysign(hh, dy)
        elif abs(dy) < 1e-6:
            bx, by = math.copysign(hw, dx), 0
        else:
            tx = hw / abs(dx)
            ty = hh / abs(dy)
            t  = min(tx, ty)
            bx = dx * t
            by = dy * t

        return QPointF(center.x() + bx, center.y() + by)

    def to_dict(self) -> dict:
        return {
            "id":    self.node_id,
            "label": self.label,
            "x":     self.pos().x(),
            "y":     self.pos().y(),
        }


# ──────────────────────────────────────────────
#  ARISTA (QGraphicsItem)
# ──────────────────────────────────────────────
class CausalEdge(QGraphicsItem):
    """Flecha dirigida entre dos nodos con signo + o −."""

    TYPE = QGraphicsItem.UserType + 2

    SIGN_COLORS = {
        "+": Palette.EDGE_POS,
        "-": Palette.EDGE_NEG,
        "~": QColor("#9B6DFF"),
    }

    def __init__(self, edge_id: str, src: CausalNode, dst: CausalNode, sign: str = "+"):
        super().__init__()
        self.edge_id = edge_id
        self.src     = src
        self.dst     = dst
        self.sign    = sign
        self._p1     = QPointF()
        self._p2     = QPointF()
        self._mid    = QPointF()
        self._angle  = 0.0

        self.setZValue(1)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.update_position()

        src.edges_out.append(self)
        dst.edges_in.append(self)

    def type(self):
        return CausalEdge.TYPE

    def update_position(self):
        """Recalcula extremos de la flecha."""
        if self.src is self.dst:
            # Auto-conexión
            self._self_loop = True
        else:
            self._self_loop = False
            p2 = self.dst.scenePos()
            p1 = self.src.scenePos()
            self._p1 = self.src.get_border_point(p2)
            self._p2 = self.dst.get_border_point(p1)
            dx = self._p2.x() - self._p1.x()
            dy = self._p2.y() - self._p1.y()
            self._angle = math.atan2(dy, dx)
            self._mid = QPointF(
                (self._p1.x() + self._p2.x()) / 2,
                (self._p1.y() + self._p2.y()) / 2,
            )
        self.prepareGeometryChange()
        self.update()

    def boundingRect(self) -> QRectF:
        if self._self_loop:
            sp = self.src.scenePos()
            r = 40
            return QRectF(sp.x() + 20, sp.y() - r - 20, r * 2 + 20, r * 2 + 20)
        x1, y1 = self._p1.x(), self._p1.y()
        x2, y2 = self._p2.x(), self._p2.y()
        margin = 20
        return QRectF(
            min(x1, x2) - margin,
            min(y1, y2) - margin,
            abs(x2 - x1) + 2 * margin,
            abs(y2 - y1) + 2 * margin,
        )

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        color = self.SIGN_COLORS.get(self.sign, Palette.EDGE_POS)

        if self._self_loop:
            self._paint_self_loop(painter, color)
            return

        # ── Línea principal ──
        pen = QPen(color, 2.0, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(self._p1, self._p2)

        # ── Punta de flecha ──
        self._draw_arrow_head(painter, color)

        # ── Etiqueta del signo ──
        self._draw_sign_label(painter, color)

    def _draw_arrow_head(self, painter: QPainter, color: QColor):
        arrow_size = 12
        angle = self._angle
        tip = self._p2

        left = QPointF(
            tip.x() - arrow_size * math.cos(angle - math.pi / 6),
            tip.y() - arrow_size * math.sin(angle - math.pi / 6),
        )
        right = QPointF(
            tip.x() - arrow_size * math.cos(angle + math.pi / 6),
            tip.y() - arrow_size * math.sin(angle + math.pi / 6),
        )
        poly = QPolygonF([tip, left, right])
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(poly)

    def _draw_sign_label(self, painter: QPainter, color: QColor):
        mx, my = self._mid.x(), self._mid.y()
        # Offset perpendicular
        perp_angle = self._angle + math.pi / 2
        offset = 14
        lx = mx + offset * math.cos(perp_angle)
        ly = my + offset * math.sin(perp_angle)

        # Círculo de fondo
        r = 10
        painter.setBrush(QBrush(Palette.BG_CARD))
        painter.setPen(QPen(color, 1.5))
        painter.drawEllipse(QPointF(lx, ly), r, r)

        # Texto del signo
        font = QFont("Segoe UI", 9, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QPen(color))
        painter.drawText(
            QRectF(lx - r, ly - r, r * 2, r * 2),
            Qt.AlignCenter,
            self.sign,
        )

    def _paint_self_loop(self, painter: QPainter, color: QColor):
        """Dibuja un arco de auto-conexión."""
        sp = self.src.scenePos()
        cx = sp.x() + self.src.width / 2 + 10
        cy = sp.y() - 20
        r  = 30
        rect = QRectF(cx, cy - r, r * 2, r * 2)
        pen = QPen(color, 2.0)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(rect, 60 * 16, 240 * 16)

        # Etiqueta
        painter.setPen(QPen(color))
        font = QFont("Segoe UI", 9, QFont.Bold)
        painter.setFont(font)
        painter.drawText(QPointF(cx + r + 6, cy), self.sign)

    def toggle_sign(self):
        """Cicla entre +, -, ~."""
        cycle = {"+": "-", "-": "~", "~": "+"}
        self.sign = cycle.get(self.sign, "+")
        self.update()

    def to_dict(self) -> dict:
        return {
            "id":   self.edge_id,
            "src":  self.src.node_id,
            "dst":  self.dst.node_id,
            "sign": self.sign,
        }


# ──────────────────────────────────────────────
#  ETIQUETA DE CICLO
# ──────────────────────────────────────────────
class CycleLabel(QGraphicsItem):
    """Muestra la etiqueta R o B de un ciclo detectado."""

    def __init__(self, label: str, cycle_type: str, center: QPointF):
        super().__init__()
        self.label      = label
        self.cycle_type = cycle_type  # "R" o "B"
        self.setPos(center)
        self.setZValue(20)
        self._size = 36

    def boundingRect(self) -> QRectF:
        s = self._size
        return QRectF(-s, -s, s * 2, s * 2)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.Antialiasing)
        s = self._size

        color = Palette.CYCLE_R if self.cycle_type == "R" else Palette.CYCLE_B
        bg    = QColor(color)
        bg.setAlpha(30)

        # Círculo de fondo semitransparente
        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(color, 2, Qt.DashLine))
        painter.drawEllipse(QPointF(0, 0), s, s)

        # Texto
        font = QFont("Segoe UI", 11, QFont.Bold)
        painter.setFont(font)
        painter.setPen(QPen(color))
        painter.drawText(QRectF(-s, -s, s * 2, s * 2), Qt.AlignCenter, self.label)


# ──────────────────────────────────────────────
#  ESCENA PRINCIPAL
# ──────────────────────────────────────────────
class DiagramScene(QGraphicsScene):
    """Escena que gestiona nodos, aristas y la lógica del diagrama."""

    status_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSceneRect(-2000, -2000, 4000, 4000)
        self.setBackgroundBrush(QBrush(Palette.BG_DARK))

        self._nodes: dict[str, CausalNode] = {}
        self._edges: dict[str, CausalEdge] = {}
        self._cycle_labels: list[CycleLabel] = []

        self._node_counter = 0
        self._edge_counter = 0
        self._mode         = "select"   # "select" | "connect" | "delete"
        self._connect_src: CausalNode | None = None

    # ── Modo de interacción ──
    def set_mode(self, mode: str):
        self._mode = mode
        self._connect_src = None
        # Quitar resaltado de selección de conexión pendiente
        for node in self._nodes.values():
            node._selected_flag = False
            node.update()
        msg_map = {
            "select":  "Modo: Seleccionar / Mover",
            "connect": "Modo: Conectar — clic en nodo origen, luego destino",
            "delete":  "Modo: Eliminar — clic en nodo o conexión",
        }
        self.status_message.emit(msg_map.get(mode, ""))

    # ── Crear nodo en posición ──
    def create_node(self, pos: QPointF, label: str = None) -> CausalNode:
        self._node_counter += 1
        nid   = f"n{self._node_counter}"
        label = label or f"Variable {self._node_counter}"
        node  = CausalNode(nid, label, pos.x(), pos.y())
        self._nodes[nid] = node
        self.addItem(node)
        self.status_message.emit(f"Nodo '{label}' creado")
        return node

    # ── Crear arista ──
    def create_edge(self, src: CausalNode, dst: CausalNode, sign: str = "+") -> CausalEdge | None:
        # Evitar duplicados
        for e in self._edges.values():
            if e.src is src and e.dst is dst:
                self.status_message.emit("Esa conexión ya existe")
                return None
        self._edge_counter += 1
        eid  = f"e{self._edge_counter}"
        edge = CausalEdge(eid, src, dst, sign)
        self._edges[eid] = edge
        self.addItem(edge)
        self.status_message.emit(
            f"Conexión {src.label} → {dst.label}  [{sign}]"
        )
        return edge

    # ── Eliminar nodo ──
    def delete_node(self, node: CausalNode):
        # Eliminar aristas asociadas
        edges_to_remove = [
            e for e in list(self._edges.values())
            if e.src is node or e.dst is node
        ]
        for e in edges_to_remove:
            self._remove_edge(e)
        self.removeItem(node)
        del self._nodes[node.node_id]
        self.status_message.emit(f"Nodo '{node.label}' eliminado")

    # ── Eliminar arista ──
    def _remove_edge(self, edge: CausalEdge):
        edge.src.edges_out.remove(edge)
        edge.dst.edges_in.remove(edge)
        self.removeItem(edge)
        del self._edges[edge.edge_id]

    # ── Solicitar renombrar nodo (llamado desde el nodo) ──
    def request_rename(self, node: CausalNode):
        view = self.views()[0] if self.views() else None
        parent_widget = view if view else None
        text, ok = QInputDialog.getText(
            parent_widget, "Renombrar variable",
            "Nombre:", text=node.label
        )
        if ok and text.strip():
            node.label = text.strip()
            node.update()
            self.status_message.emit(f"Variable renombrada a '{node.label}'")

    # ── Limpiar escena ──
    def clear_diagram(self):
        for item in list(self.items()):
            self.removeItem(item)
        self._nodes.clear()
        self._edges.clear()
        self._cycle_labels.clear()
        self._node_counter = 0
        self._edge_counter = 0
        self.status_message.emit("Diagrama limpiado")

    # ── Eventos de ratón ──
    def mousePressEvent(self, event):
        pos  = event.scenePos()
        item = self.itemAt(pos, QTransform())

        if event.button() == Qt.RightButton:
            # Cambiar signo de arista con clic derecho
            if isinstance(item, CausalEdge):
                item.toggle_sign()
                self.status_message.emit(
                    f"Signo cambiado a '{item.sign}' en {item.src.label}→{item.dst.label}"
                )
            return

        if event.button() == Qt.LeftButton:
            if self._mode == "connect":
                node = self._find_node_at(pos)
                if node:
                    if self._connect_src is None:
                        self._connect_src = node
                        node._selected_flag = True
                        node.update()
                        self.status_message.emit(
                            f"Origen: '{node.label}' — ahora selecciona el destino"
                        )
                    else:
                        src = self._connect_src
                        src._selected_flag = False
                        src.update()
                        self.create_edge(src, node)
                        self._connect_src = None
                return

            if self._mode == "delete":
                if isinstance(item, CausalNode):
                    self.delete_node(item)
                elif isinstance(item, CausalEdge):
                    self._remove_edge(item)
                    self.status_message.emit("Conexión eliminada")
                return

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        pos  = event.scenePos()
        item = self.itemAt(pos, QTransform())
        if item is None or isinstance(item, (QGraphicsRectItem,)):
            # Doble clic en espacio vacío → crear nodo
            if self._mode in ("select", "connect"):
                self.create_node(pos)
        super().mouseDoubleClickEvent(event)

    def _find_node_at(self, pos: QPointF) -> CausalNode | None:
        for item in self.items(pos):
            if isinstance(item, CausalNode):
                return item
        return None

    # ──────────────────────────────────────────
    #  DETECCIÓN DE CICLOS (DFS)
    # ──────────────────────────────────────────
    def detect_cycles(self):
        """Detecta todos los ciclos simples usando Johnson's-style DFS y los muestra."""
        # Limpiar etiquetas anteriores
        for lbl in self._cycle_labels:
            self.removeItem(lbl)
        self._cycle_labels.clear()

        # Construir grafo de adyacencia
        adj: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for edge in self._edges.values():
            adj[edge.src.node_id].append((edge.dst.node_id, edge.sign))

        cycles = []
        visited_global = set()

        def dfs(start: str, current: str, path: list, path_set: set,
                signs: list):
            for neighbor, sign in adj.get(current, []):
                if neighbor == start and len(path) >= 2:
                    cycles.append((list(path), list(signs) + [sign]))
                    return
                if neighbor not in path_set and neighbor not in visited_global:
                    path.append(neighbor)
                    path_set.add(neighbor)
                    signs.append(sign)
                    dfs(start, neighbor, path, path_set, signs)
                    path.pop()
                    path_set.discard(neighbor)
                    signs.pop()

        for nid in list(self._nodes.keys()):
            dfs(nid, nid, [nid], {nid}, [])
            visited_global.add(nid)

        # Deduplicar ciclos (rotar y comparar)
        unique_cycles = []
        seen_sets = []
        for cycle, signs in cycles:
            frozen = frozenset(cycle)
            if frozen not in seen_sets:
                seen_sets.append(frozen)
                unique_cycles.append((cycle, signs))

        if not unique_cycles:
            self.status_message.emit("No se detectaron ciclos en el diagrama")
            return

        for i, (cycle, signs) in enumerate(unique_cycles):
            # Determinar tipo: R si número par de signos negativos, B si impar
            neg_count = signs.count("-")
            ctype = "R" if neg_count % 2 == 0 else "B"
            clabel_text = f"{'R' if ctype=='R' else 'B'}{i+1}"

            # Centro aproximado del ciclo
            cx = sum(self._nodes[n].pos().x() for n in cycle if n in self._nodes)
            cy = sum(self._nodes[n].pos().y() for n in cycle if n in self._nodes)
            count = len([n for n in cycle if n in self._nodes])
            if count:
                cx /= count
                cy /= count

            lbl = CycleLabel(clabel_text, ctype, QPointF(cx, cy))
            self._cycle_labels.append(lbl)
            self.addItem(lbl)

        r_count = sum(1 for (_, s) in unique_cycles if s.count("-") % 2 == 0)
        b_count = len(unique_cycles) - r_count
        self.status_message.emit(
            f"Ciclos detectados: {len(unique_cycles)} "
            f"({r_count} reforzadores R, {b_count} balanceadores B)"
        )

    # ──────────────────────────────────────────
    #  SERIALIZACIÓN JSON
    # ──────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [e.to_dict() for e in self._edges.values()],
        }

    def from_dict(self, data: dict):
        self.clear_diagram()
        for nd in data.get("nodes", []):
            node = CausalNode(nd["id"], nd["label"], nd["x"], nd["y"])
            # Preservar contador
            try:
                num = int(nd["id"].lstrip("n"))
                if num > self._node_counter:
                    self._node_counter = num
            except ValueError:
                pass
            self._nodes[nd["id"]] = node
            self.addItem(node)

        for ed in data.get("edges", []):
            src = self._nodes.get(ed["src"])
            dst = self._nodes.get(ed["dst"])
            if src and dst:
                self._edge_counter += 1
                edge = CausalEdge(ed["id"], src, dst, ed.get("sign", "+"))
                self._edges[ed["id"]] = edge
                self.addItem(edge)

        self.status_message.emit("Diagrama cargado correctamente")


# ──────────────────────────────────────────────
#  VISTA PRINCIPAL (QGraphicsView)
# ──────────────────────────────────────────────
class DiagramView(QGraphicsView):
    """Vista con zoom, pan y cuadrícula de fondo."""

    def __init__(self, scene: DiagramScene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setViewportUpdateMode(QGraphicsView.FullViewportUpdate)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("border: none; background: transparent;")

        self._panning = False
        self._pan_start = None
        self._scale_factor = 1.0

    def drawBackground(self, painter: QPainter, rect: QRectF):
        """Cuadrícula de puntos elegante."""
        painter.fillRect(rect, QBrush(Palette.BG_DARK))

        grid_step = 40
        left   = int(rect.left())  - (int(rect.left())  % grid_step)
        top    = int(rect.top())   - (int(rect.top())   % grid_step)
        right  = int(rect.right())
        bottom = int(rect.bottom())

        painter.setPen(QPen(Palette.GRID_DOT, 1.5))
        for x in range(left, right, grid_step):
            for y in range(top, bottom, grid_step):
                painter.drawPoint(x, y)

        # Líneas de cuadrícula mayor cada 200px
        major = 200
        pen_major = QPen(Palette.GRID_LINE, 1, Qt.SolidLine)
        painter.setPen(pen_major)
        left_m  = int(rect.left())  - (int(rect.left())  % major)
        top_m   = int(rect.top())   - (int(rect.top())   % major)
        for x in range(left_m, right + major, major):
            painter.drawLine(x, int(rect.top()), x, int(rect.bottom()))
        for y in range(top_m, bottom + major, major):
            painter.drawLine(int(rect.left()), y, int(rect.right()), y)

    def wheelEvent(self, event):
        """Zoom con la rueda del ratón."""
        delta = event.angleDelta().y()
        factor = 1.12 if delta > 0 else 1 / 1.12
        new_scale = self._scale_factor * factor
        if 0.15 <= new_scale <= 4.0:
            self._scale_factor = new_scale
            self.scale(factor, factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._panning = True
            self._pan_start = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning and self._pan_start is not None:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            return
        super().mouseReleaseEvent(event)

    def reset_view(self):
        self.resetTransform()
        self._scale_factor = 1.0
        self.centerOn(0, 0)


# ──────────────────────────────────────────────
#  BOTÓN DEL PANEL LATERAL
# ──────────────────────────────────────────────
class SideButton(QPushButton):
    """Botón estilizado para el panel lateral."""

    def __init__(self, text: str, icon_char: str = "", danger: bool = False, parent=None):
        super().__init__(parent)
        self._danger  = danger
        self._active  = False
        self._icon_ch = icon_char
        self.setText(f"  {icon_char}  {text}" if icon_char else text)
        self.setFixedHeight(44)
        self.setFont(QFont("Segoe UI", 9, QFont.Medium))
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style()

    def _apply_style(self):
        if self._danger:
            base = Palette.BTN_DANGER
            hover = QColor("#FF6B8A")
        elif self._active:
            base = Palette.BTN_ACTIVE
            hover = QColor("#6BAFFF")
        else:
            base = Palette.BTN_NORMAL
            hover = Palette.BTN_HOVER

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {base.name()};
                color: #E8EAF6;
                border: 1px solid rgba(255,255,255,0.06);
                border-radius: 10px;
                padding: 0 14px;
                text-align: left;
                font-size: 9pt;
            }}
            QPushButton:hover {{
                background-color: {hover.name()};
                border: 1px solid rgba(255,255,255,0.12);
            }}
            QPushButton:pressed {{
                background-color: {Palette.ACCENT_BLUE.name()};
            }}
        """)

    def set_active(self, active: bool):
        self._active = active
        self._apply_style()


# ──────────────────────────────────────────────
#  PANEL LATERAL
# ──────────────────────────────────────────────
class SidePanel(QWidget):
    """Panel lateral con herramientas y controles."""

    # Señales hacia la ventana principal
    sig_create_node  = pyqtSignal()
    sig_mode_select  = pyqtSignal()
    sig_mode_connect = pyqtSignal()
    sig_mode_delete  = pyqtSignal()
    sig_detect_cycles= pyqtSignal()
    sig_clear        = pyqtSignal()
    sig_reset_view   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(210)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {Palette.BG_PANEL.name()};
                border-right: 1px solid rgba(255,255,255,0.05);
            }}
        """)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 20, 12, 20)
        layout.setSpacing(8)

        # ── Logo / Título ──
        title = QLabel("Diagramas\nCausales")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet(f"color: {Palette.ACCENT_BLUE.name()}; background: transparent;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Dinámica de Sistemas")
        subtitle.setFont(QFont("Segoe UI", 8))
        subtitle.setStyleSheet(f"color: {Palette.TEXT_SECONDARY.name()}; background: transparent;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(16)
        self._separator(layout, "HERRAMIENTAS")

        # ── Botones de modo ──
        self.btn_select  = SideButton("Seleccionar",  "↖")
        self.btn_create  = SideButton("Crear variable","⊕")
        self.btn_connect = SideButton("Conectar",      "⟶")
        self.btn_delete  = SideButton("Eliminar",      "✕", danger=True)

        self.btn_select.clicked.connect(lambda: self.sig_mode_select.emit())
        self.btn_create.clicked.connect(lambda: self.sig_create_node.emit())
        self.btn_connect.clicked.connect(lambda: self.sig_mode_connect.emit())
        self.btn_delete.clicked.connect(lambda: self.sig_mode_delete.emit())

        for btn in (self.btn_select, self.btn_create, self.btn_connect, self.btn_delete):
            layout.addWidget(btn)

        layout.addSpacing(12)
        self._separator(layout, "ANÁLISIS")

        self.btn_cycles = SideButton("Detectar ciclos", "◎")
        self.btn_cycles.clicked.connect(lambda: self.sig_detect_cycles.emit())
        layout.addWidget(self.btn_cycles)

        layout.addSpacing(12)
        self._separator(layout, "VISTA")

        self.btn_reset_view = SideButton("Centrar vista", "⊡")
        self.btn_reset_view.clicked.connect(lambda: self.sig_reset_view.emit())
        layout.addWidget(self.btn_reset_view)

        layout.addSpacing(12)
        self._separator(layout, "DIAGRAMA")

        self.btn_clear = SideButton("Limpiar todo", "⊘", danger=True)
        self.btn_clear.clicked.connect(lambda: self.sig_clear.emit())
        layout.addWidget(self.btn_clear)

        layout.addStretch()

        # ── Leyenda ──
        self._separator(layout, "LEYENDA")
        self._legend_item(layout, Palette.EDGE_POS,  "+ Relación positiva")
        self._legend_item(layout, Palette.EDGE_NEG,  "−  Relación negativa")
        self._legend_item(layout, Palette.CYCLE_R,   "R  Ciclo reforzador")
        self._legend_item(layout, Palette.CYCLE_B,   "B  Ciclo balanceador")

        layout.addSpacing(8)
        hint = QLabel("Doble clic → nuevo nodo\nClic derecho → cambiar signo\nRueda → zoom | Medio → pan")
        hint.setFont(QFont("Segoe UI", 7))
        hint.setStyleSheet(f"color: {Palette.TEXT_SECONDARY.name()}; background: transparent;")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

    def _separator(self, layout, text: str):
        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 7, QFont.Bold))
        lbl.setStyleSheet(f"color: {Palette.TEXT_SECONDARY.name()}; background: transparent; letter-spacing: 1px;")
        layout.addWidget(lbl)
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background: rgba(255,255,255,0.06); border: none; max-height: 1px;")
        layout.addWidget(line)

    def _legend_item(self, layout, color: QColor, text: str):
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        hl  = QHBoxLayout(row)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)

        dot = QLabel("●")
        dot.setFont(QFont("Segoe UI", 10))
        dot.setStyleSheet(f"color: {color.name()}; background: transparent;")
        dot.setFixedWidth(16)

        lbl = QLabel(text)
        lbl.setFont(QFont("Segoe UI", 8))
        lbl.setStyleSheet(f"color: {Palette.TEXT_SECONDARY.name()}; background: transparent;")

        hl.addWidget(dot)
        hl.addWidget(lbl)
        hl.addStretch()
        layout.addWidget(row)

    def set_active_mode(self, mode: str):
        self.btn_select.set_active(mode == "select")
        self.btn_connect.set_active(mode == "connect")
        self.btn_delete.set_active(mode == "delete")


# ──────────────────────────────────────────────
#  VENTANA PRINCIPAL
# ──────────────────────────────────────────────
class MainWindow(QMainWindow):
    """Ventana principal de la aplicación."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Diagramas Causales — Dinámica de Sistemas")
        self.setMinimumSize(1100, 720)
        self.resize(1280, 800)
        self._current_file: str | None = None

        self._build_ui()
        self._build_menu()
        self._connect_signals()
        self._apply_global_style()

        # Modo inicial
        self._set_mode("select")

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        hbox = QHBoxLayout(central)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)

        # Panel lateral
        self.side_panel = SidePanel()
        hbox.addWidget(self.side_panel)

        # Escena y vista
        self.scene = DiagramScene()
        self.view  = DiagramView(self.scene)
        hbox.addWidget(self.view, 1)

        # Barra de estado
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background: {Palette.BG_PANEL.name()};
                color: {Palette.TEXT_SECONDARY.name()};
                border-top: 1px solid rgba(255,255,255,0.05);
                font-size: 8pt;
                padding: 0 8px;
            }}
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Listo — Doble clic en el área para crear una variable")

    def _build_menu(self):
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet(f"""
            QMenuBar {{
                background: {Palette.BG_PANEL.name()};
                color: {Palette.TEXT_PRIMARY.name()};
                border-bottom: 1px solid rgba(255,255,255,0.05);
                font-size: 9pt;
            }}
            QMenuBar::item:selected {{
                background: {Palette.BTN_HOVER.name()};
                border-radius: 4px;
            }}
            QMenu {{
                background: {Palette.BG_CARD.name()};
                color: {Palette.TEXT_PRIMARY.name()};
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 6px;
                font-size: 9pt;
            }}
            QMenu::item:selected {{
                background: {Palette.BTN_HOVER.name()};
            }}
            QMenu::separator {{
                height: 1px;
                background: rgba(255,255,255,0.07);
                margin: 4px 8px;
            }}
        """)

        # Archivo
        file_menu = menu_bar.addMenu("  Archivo  ")
        act_new   = QAction("Nuevo diagrama", self)
        act_open  = QAction("Abrir JSON…", self)
        act_save  = QAction("Guardar JSON…", self)
        act_export= QAction("Exportar PNG…", self)
        act_quit  = QAction("Salir", self)
        act_new.setShortcut("Ctrl+N")
        act_open.setShortcut("Ctrl+O")
        act_save.setShortcut("Ctrl+S")
        act_export.setShortcut("Ctrl+E")
        act_quit.setShortcut("Ctrl+Q")
        file_menu.addAction(act_new)
        file_menu.addSeparator()
        file_menu.addAction(act_open)
        file_menu.addAction(act_save)
        file_menu.addSeparator()
        file_menu.addAction(act_export)
        file_menu.addSeparator()
        file_menu.addAction(act_quit)

        act_new.triggered.connect(self._action_new)
        act_open.triggered.connect(self._action_open)
        act_save.triggered.connect(self._action_save)
        act_export.triggered.connect(self._action_export)
        act_quit.triggered.connect(self.close)

        # Diagrama
        diag_menu = menu_bar.addMenu("  Diagrama  ")
        act_cycles = QAction("Detectar ciclos", self)
        act_cycles.setShortcut("Ctrl+D")
        act_cycles.triggered.connect(self.scene.detect_cycles)
        diag_menu.addAction(act_cycles)

        # Acerca de
        help_menu = menu_bar.addMenu("  Ayuda  ")
        act_about = QAction("Acerca de…", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    def _connect_signals(self):
        self.scene.status_message.connect(self.status_bar.showMessage)
        self.side_panel.sig_create_node.connect(self._create_node_center)
        self.side_panel.sig_mode_select.connect(lambda: self._set_mode("select"))
        self.side_panel.sig_mode_connect.connect(lambda: self._set_mode("connect"))
        self.side_panel.sig_mode_delete.connect(lambda: self._set_mode("delete"))
        self.side_panel.sig_detect_cycles.connect(self.scene.detect_cycles)
        self.side_panel.sig_clear.connect(self._action_clear)
        self.side_panel.sig_reset_view.connect(self.view.reset_view)

    def _set_mode(self, mode: str):
        self.scene.set_mode(mode)
        self.side_panel.set_active_mode(mode)
        if mode == "select":
            self.view.setDragMode(QGraphicsView.RubberBandDrag)
        else:
            self.view.setDragMode(QGraphicsView.NoDrag)

    def _create_node_center(self):
        """Crea un nodo en el centro visible de la vista."""
        center = self.view.mapToScene(
            self.view.viewport().rect().center()
        )
        # Offset ligero para evitar superposición
        import random
        offset = QPointF(random.uniform(-60, 60), random.uniform(-60, 60))
        self.scene.create_node(center + offset)

    # ── Acciones de menú ──
    def _action_new(self):
        reply = QMessageBox.question(
            self, "Nuevo diagrama",
            "¿Descartar el diagrama actual y empezar uno nuevo?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.scene.clear_diagram()
            self._current_file = None
            self.setWindowTitle("Diagramas Causales — Dinámica de Sistemas")

    def _action_open(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir diagrama", "", "JSON (*.json)"
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.scene.from_dict(data)
                self._current_file = path
                self.setWindowTitle(
                    f"Diagramas Causales — {path.split('/')[-1]}"
                )
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"No se pudo abrir:\n{exc}")

    def _action_save(self):
        path = self._current_file
        if not path:
            path, _ = QFileDialog.getSaveFileName(
                self, "Guardar diagrama", "diagrama_causal.json", "JSON (*.json)"
            )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.scene.to_dict(), f, indent=2, ensure_ascii=False)
                self._current_file = path
                self.status_bar.showMessage(f"Guardado en {path}")
                self.setWindowTitle(
                    f"Diagramas Causales — {path.split('/')[-1]}"
                )
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{exc}")

    def _action_export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar imagen", "diagrama_causal.png", "PNG (*.png)"
        )
        if path:
            try:
                # Calcular bounding rect con margen
                items_rect = self.scene.itemsBoundingRect()
                margin = 60
                export_rect = items_rect.adjusted(-margin, -margin, margin, margin)
                if export_rect.isEmpty():
                    export_rect = QRectF(-400, -300, 800, 600)

                scale = 2  # alta resolución
                image = QImage(
                    int(export_rect.width() * scale),
                    int(export_rect.height() * scale),
                    QImage.Format_ARGB32_Premultiplied,
                )
                image.fill(Palette.BG_DARK)
                painter = QPainter(image)
                painter.setRenderHint(QPainter.Antialiasing)
                self.scene.render(painter, source=export_rect)
                painter.end()
                image.save(path)
                self.status_bar.showMessage(f"Imagen exportada: {path}")
            except Exception as exc:
                QMessageBox.critical(self, "Error", f"No se pudo exportar:\n{exc}")

    def _action_clear(self):
        reply = QMessageBox.question(
            self, "Limpiar diagrama",
            "¿Eliminar todos los nodos y conexiones?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.scene.clear_diagram()

    def _show_about(self):
        QMessageBox.about(
            self,
            "Acerca de Diagramas Causales",
            "<h3 style='color:#4B9FFF;'>Diagramas Causales</h3>"
            "<p>Herramienta visual interactiva para la construcción y análisis "
            "de diagramas causales en el marco de la <b>Teoría General de Sistemas</b> "
            "y la <b>Dinámica de Sistemas</b>.</p>"
            "<ul>"
            "<li>Crear variables (nodos)</li>"
            "<li>Conectar con relaciones + / − / ~</li>"
            "<li>Detección automática de ciclos reforzadores (R) y balanceadores (B)</li>"
            "<li>Guardar / Cargar JSON</li>"
            "<li>Exportar PNG</li>"
            "</ul>"
            "<p style='color:#8892B0; font-size:8pt;'>Desarrollado con Python 3 + PyQt5</p>"
        )

    def _apply_global_style(self):
        self.setStyleSheet(f"""
            QMainWindow {{
                background: {Palette.BG_DARK.name()};
            }}
            QMessageBox {{
                background: {Palette.BG_CARD.name()};
                color: {Palette.TEXT_PRIMARY.name()};
            }}
            QInputDialog {{
                background: {Palette.BG_CARD.name()};
                color: {Palette.TEXT_PRIMARY.name()};
            }}
            QInputDialog QLineEdit {{
                background: {Palette.BG_DARK.name()};
                color: {Palette.TEXT_PRIMARY.name()};
                border: 1px solid {Palette.ACCENT_BLUE.name()};
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QFileDialog {{
                background: {Palette.BG_CARD.name()};
                color: {Palette.TEXT_PRIMARY.name()};
            }}
        """)


# ──────────────────────────────────────────────
#  ENTRADA PRINCIPAL
# ──────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Diagramas Causales")
    app.setStyle("Fusion")

    # Paleta oscura base para diálogos del sistema
    palette = QPalette()
    palette.setColor(QPalette.Window,          Palette.BG_DARK)
    palette.setColor(QPalette.WindowText,      Palette.TEXT_PRIMARY)
    palette.setColor(QPalette.Base,            Palette.BG_CARD)
    palette.setColor(QPalette.AlternateBase,   Palette.BG_PANEL)
    palette.setColor(QPalette.ToolTipBase,     Palette.BG_CARD)
    palette.setColor(QPalette.ToolTipText,     Palette.TEXT_PRIMARY)
    palette.setColor(QPalette.Text,            Palette.TEXT_PRIMARY)
    palette.setColor(QPalette.Button,          Palette.BTN_NORMAL)
    palette.setColor(QPalette.ButtonText,      Palette.TEXT_PRIMARY)
    palette.setColor(QPalette.BrightText,      Qt.red)
    palette.setColor(QPalette.Link,            Palette.ACCENT_BLUE)
    palette.setColor(QPalette.Highlight,       Palette.ACCENT_BLUE)
    palette.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()