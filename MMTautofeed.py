import sys, os, json, datetime, requests, zipfile, subprocess, uuid, mimetypes, re, math, unicodedata
from urllib.parse import urlparse, parse_qs, unquote

if sys.platform == 'win32':
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("mmt.autofeed.app.1_01_0")
    except Exception: pass
elif sys.platform == 'darwin':
    # 只在“源码直接运行”时手动设置应用名/前台策略；
    # 打包成 .app 后由 Info.plist 负责（提前创建 NSApplication 会导致 Dock 出现两个图标）。
    if not getattr(sys, 'frozen', False):
        try:
            from AppKit import NSBundle, NSApplication
            bundle = NSBundle.mainBundle()
            if bundle:
                info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
                if info and 'CFBundleName' not in info: info['CFBundleName'] = 'MMTautofeed'

            app_instance = NSApplication.sharedApplication()
            app_instance.setActivationPolicy_(0)
        except ImportError: pass

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QGroupBox, QLabel, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QLineEdit, QCheckBox, QScrollArea, QGridLayout, QFormLayout, QSpinBox, QHeaderView, QRadioButton, QButtonGroup, QMessageBox, QFileDialog, QDialog, QSizePolicy, QProgressBar, QListWidget, QAbstractItemView, QListView, QTreeView, QFrame, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsPathItem, QGraphicsItem, QSplitter)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QEvent, QTimer, QPointF, QRectF
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor, QIcon, QImage, QPixmap, QPainter, QPainterPath, QPen, QBrush, QPolygonF, QTransform, QPainterPathStroker

# 高对比度边框与ToolTip重构
STYLE_LIGHT = "QMainWindow, QDialog, QWidget { background-color: #f5f5f7; color: #1d1d1f; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; font-size: 13px; } QToolTip { background-color: #ffffe1; color: #000000; border: 1px solid #000000; padding: 4px; border-radius: 4px; font-size: 13px; } QLabel, QCheckBox, QRadioButton { background: transparent; color: #1d1d1f; } QMessageBox { background-color: #ffffff; border-radius: 8px; border: 1px solid #d2d2d7; } QMessageBox QLabel { background-color: transparent; } QLineEdit, QSpinBox, QComboBox { background-color: #ffffff; color: #1d1d1f; border: 1px solid #666666; border-radius: 6px; padding: 6px 8px; min-height: 24px; } QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #007aff; } QComboBox::drop-down { border: none; width: 20px; } QComboBox QAbstractItemView, QListView { background-color: #ffffff; color: #1d1d1f; border: 1px solid #666666; outline: none; border-radius: 6px; selection-background-color: #007aff; selection-color: white; } QComboBox QAbstractItemView::item, QListView::item { padding: 6px; color: #1d1d1f; } QComboBox QAbstractItemView::item:selected, QListView::item:selected { background-color: #007aff; color: white; border-radius: 4px; } QListWidget { background-color: #ffffff; color: #1d1d1f; border: 1px solid #666666; border-radius: 8px; padding: 8px; outline: none; } QListWidget::item { background-color: #e5e5ea; border-radius: 4px; padding: 4px 8px; margin: 2px; color: #1d1d1f; } QListWidget::item:selected { background-color: #ff3b30; color: white; } QGroupBox { font-weight: bold; color: #1d1d1f; border: 1px solid #666666; border-radius: 8px; margin-top: 20px; padding-top: 15px; background-color: #ffffff; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 15px; top: 0px; color: #007aff; background-color: transparent; } QPushButton { background-color: #ffffff; color: #1d1d1f; border: 1px solid #666666; border-radius: 6px; padding: 6px 16px; font-weight: bold; } QPushButton:hover { background-color: #f0f0f5; border: 1px solid #8e8e93;} QPushButton:pressed { background-color: #e5e5ea; } QPushButton:disabled { background-color: #f5f5f7; color: #a1a1a6; border: 1px solid #e5e5ea; } QTableWidget { background-color: #ffffff; alternate-background-color: #f2f2f7; color: #1d1d1f; gridline-color: #d2d2d7; border: 1px solid #666666; border-radius: 8px; } QTableWidget::item:selected { background-color: #007aff; color: white; } QHeaderView::section { background-color: #f5f5f7; color: #86868b; padding: 8px 6px; border: none; border-right: 1px solid #666666; border-bottom: 1px solid #666666; font-weight: bold; } QTableCornerButton::section { background-color: #f5f5f7; } QTableWidget QComboBox { min-height: 16px; padding: 2px 4px; margin: 2px; } QTabWidget::pane { border: none; background: transparent; } QTabBar::tab { background: #e5e5ea; color: #86868b; padding: 8px 24px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; border: none; } QTabBar::tab:selected { background: #f5f5f7; color: #007aff; font-weight: bold; border-bottom: 2px solid #007aff; } QScrollArea { border: none; background-color: transparent; } #ScrollContent { background-color: transparent; } QTextEdit { background-color: #ffffff; color: #1d1d1f; border: 1px solid #666666; border-radius: 6px; padding: 6px; } QTextEdit#LogView, QTextEdit#BatchLogView { background-color: #1e1e1e; color: #34c759; font-family: Consolas, monospace; border: 1px solid #666666; border-radius: 8px; padding: 8px; } QProgressBar { border: 1px solid #666666; border-radius: 6px; text-align: center; color: #1d1d1f; background-color: #e5e5ea; font-weight: bold; height: 16px; } QProgressBar::chunk { background-color: #007aff; border-radius: 5px; } QScrollBar:vertical { border: none; background: transparent; width: 14px; margin: 0px; } QScrollBar::handle:vertical { background: #aeaeb2; border-radius: 7px; min-height: 20px; margin: 2px; } QScrollBar::handle:vertical:hover { background: #8e8e93; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; } QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; } QScrollBar:horizontal { border: none; background: transparent; height: 14px; margin: 0px; } QScrollBar::handle:horizontal { background: #aeaeb2; border-radius: 7px; min-width: 20px; margin: 2px; } QScrollBar::handle:horizontal:hover { background: #8e8e93; } QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; } QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }"
STYLE_DARK = "QMainWindow, QDialog { background-color: #1e1e1e; color: #e5e5ea; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; font-size: 13px; } QToolTip { background-color: #2c2c2e; color: #ffffff; border: 1px solid #aaaaaa; padding: 4px; border-radius: 4px; font-size: 13px; } QWidget { background-color: transparent; color: #e5e5ea; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; font-size: 13px; } QLabel, QCheckBox, QRadioButton { background: transparent; color: #e5e5ea; } QMessageBox { background-color: #2c2c2e; border-radius: 8px; border: 1px solid #aaaaaa; } QMessageBox QLabel { background-color: transparent; } QLineEdit, QSpinBox, QComboBox { background-color: #121212; color: #ffffff; border: 1px solid #aaaaaa; border-radius: 6px; padding: 6px 8px; min-height: 24px; } QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #0a84ff; background-color: #000000; } QLineEdit:disabled { background-color: #2c2c2e; color: #8e8e93; border: 1px solid #48484a; } QComboBox::drop-down { border: none; width: 20px; } QComboBox QAbstractItemView, QListView { background-color: #1e1e1e; color: #ffffff; border: 1px solid #aaaaaa; outline: none; border-radius: 6px; } QListView::item { padding: 8px; } QListView::item:selected { background-color: #0a84ff; color: white; border-radius: 4px; } QListWidget { background-color: #121212; color: #ffffff; border: 1px solid #aaaaaa; border-radius: 8px; padding: 8px; outline: none; } QListWidget::item { background-color: #3a3a3c; border-radius: 4px; padding: 4px 8px; margin: 2px; color: #e5e5ea; } QListWidget::item:selected { background-color: #ff3b30; color: white; } QGroupBox { font-weight: bold; color: #ffffff; border: 1px solid #aaaaaa; border-radius: 8px; margin-top: 20px; padding-top: 15px; background-color: #2c2c2e; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 15px; top: 0px; color: #0a84ff; background-color: transparent; } QPushButton { background-color: #3a3a3c; color: #ffffff; border: 1px solid #aaaaaa; border-radius: 6px; padding: 6px 16px; font-weight: bold; } QPushButton:hover { background-color: #48484a; border: 1px solid #8e8e93; } QPushButton:pressed { background-color: #636366; } QPushButton:disabled { background-color: #1e1e1e; color: #636366; border: 1px solid #3a3a3c; } QTableWidget { background-color: #1e1e1e; alternate-background-color: #262628; color: #ffffff; gridline-color: #3a3a3c; border: 1px solid #aaaaaa; border-radius: 8px; } QTableWidget::item:selected { background-color: #0a84ff; color: white; } QHeaderView::section { background-color: #2c2c2e; color: #86868b; padding: 8px 6px; border: none; border-right: 1px solid #aaaaaa; border-bottom: 1px solid #aaaaaa; font-weight: bold; } QTableCornerButton::section { background-color: #2c2c2e; } QTableWidget QComboBox { min-height: 16px; padding: 2px 4px; margin: 2px; } QTabWidget::pane { border: none; background: transparent; } QTabBar::tab { background: #2c2c2e; color: #86868b; padding: 8px 24px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; border: none; } QTabBar::tab:selected { background: #1e1e1e; color: #0a84ff; font-weight: bold; border-bottom: 2px solid #0a84ff; } QScrollArea { border: none; background-color: transparent; } #ScrollContent { background-color: transparent; } QTextEdit { background-color: #121212; color: #ffffff; border: 1px solid #aaaaaa; border-radius: 6px; padding: 8px; } QTextEdit#LogView, QTextEdit#BatchLogView { background-color: #0d0d0d; color: #30d158; font-family: Consolas, monospace; border: 1px solid #aaaaaa; border-radius: 8px; padding: 8px; } QProgressBar { border: 1px solid #aaaaaa; border-radius: 6px; text-align: center; color: #ffffff; background-color: #1e1e1e; font-weight: bold; height: 16px; } QProgressBar::chunk { background-color: #0a84ff; border-radius: 5px; } QScrollBar:vertical { border: none; background: transparent; width: 14px; margin: 0px; } QScrollBar::handle:vertical { background: #636366; border-radius: 7px; min-height: 20px; margin: 2px; } QScrollBar::handle:vertical:hover { background: #8e8e93; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; } QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; } QScrollBar:horizontal { border: none; background: transparent; height: 14px; margin: 0px; } QScrollBar::handle:horizontal { background: #636366; border-radius: 7px; min-width: 20px; margin: 2px; } QScrollBar::handle:horizontal:hover { background: #8e8e93; } QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; } QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }"

SITE_CATEGORIES = ["请选择分类...", "写真", "人像", "风光", "纪实", "杂志", "静物", "儿童", "超现实", "美食", "动物", "人文", "软件", "图书", "预设", "教程", "Special"]
GLOBAL_TAGS = ["OTHER", "GER", "KR", "US", "UK", "FR", "JP", "CN", "大师", "明星", "杂志", "RAW", "可商用", "古风", "COSER", "私房", "马格南", "时光机", "樱花妹"]

def resolve_category(category, category_map):
    if not category: return None
    cat = str(category).strip()
    if not cat or cat == "请选择分类...": return None
    return category_map.get(cat)

def sanitize_filename(name, max_len=150):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', '_', str(name))
    name = name.rstrip(' .')
    if len(name) > max_len: name = name[:max_len].rstrip(' .')
    return name

def build_bbcode_img(img_url, thumb_path, logger=None):
    if img_url: return f"[img]{img_url}[/img]"
    if logger: logger("图床未配置或上传失败，封面将显示占位提示。", "WARNING")
    return "[img]图床未配置或上传失败[/img]"

def extract_torrent_id(url):
    if not url: return None
    u = str(url)
    try:
        values = parse_qs(urlparse(u).query).get('id')
    except Exception:
        values = None
    if values: return values[0]
    # 成功回跳经常把详情页 URL 编码塞进 returnto 之类的参数里，
    # 例如 login.php?returnto=details.php%3Fid%3D8864%26uploaded%3D1
    decoded = unquote(u)
    match = re.search(r'[?&]id=([^&\s]+)', decoded)
    return match.group(1) if match else None

def check_image_host_reachability(url, session=None, proxies=None):
    session = session or requests
    try:
        resp = session.get(url, timeout=10, proxies=proxies)
        return ("reachable", resp.status_code)
    except Exception as e:
        return ("unreachable", str(e))

def normalize_proxy(addr):
    addr = (addr or "").strip()
    if not addr: return None
    if "://" not in addr: addr = "http://" + addr
    return {"http": addr, "https": addr}

def find_existing_file(path):
    # macOS 会把文件名做 NFD 归一化，用 NFC 构造的路径可能对不上；这里三种写法都试一遍。
    for cand in (path, unicodedata.normalize('NFC', path), unicodedata.normalize('NFD', path)):
        try:
            if os.path.exists(cand): return cand
        except Exception:
            pass
    return None

def find_torrent_in_dir(directory, stem):
    # 容错查找：忽略 Unicode 归一化差异与大小写，必要时按前缀匹配。
    try:
        target = unicodedata.normalize('NFC', stem).lower()
        for f in os.listdir(directory):
            n = unicodedata.normalize('NFC', f).lower()
            if n in (target + '.torrent', target + '.zip.torrent'):
                return os.path.join(directory, f)
        for f in os.listdir(directory):
            n = unicodedata.normalize('NFC', f).lower()
            if n.endswith('.torrent') and (n.startswith(target) or target in n):
                return os.path.join(directory, f)
    except Exception:
        pass
    return None

def get_rounded_poly(poly_pts, r):
    path = QPainterPath()
    for i in range(len(poly_pts)):
        p1 = poly_pts[i - 1]; p2 = poly_pts[i]; p3 = poly_pts[(i + 1) % len(poly_pts)]
        v1 = (p1[0] - p2[0], p1[1] - p2[1]); v2 = (p3[0] - p2[0], p3[1] - p2[1])
        len1 = math.hypot(*v1); len2 = math.hypot(*v2)
        if len1 == 0 or len2 == 0: continue
        u1 = (v1[0] / len1, v1[1] / len1); u2 = (v2[0] / len2, v2[1] / len2)
        dot = max(-1.0, min(1.0, u1[0] * u2[0] + u1[1] * u2[1]))
        angle = math.acos(dot)
        if angle < 0.001: continue
        d = r / math.tan(angle / 2.0)
        d = min(d, len1 / 2.0, len2 / 2.0)
        t1 = (p2[0] + u1[0] * d, p2[1] + u1[1] * d); t2 = (p2[0] + u2[0] * d, p2[1] + u2[1] * d)
        if i == 0: path.moveTo(*t1)
        else: path.lineTo(*t1)
        path.quadTo(p2[0], p2[1], t2[0], t2[1])
    path.closeSubpath()
    return path

class ContainerItem(QGraphicsPathItem):
    def __init__(self, path, parent=None):
        super().__init__(parent); self.setPath(path); self.setPen(QPen(Qt.PenStyle.NoPen)); self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemClipsChildrenToShape, True)

class DraggableImage(QGraphicsPixmapItem):
    def __init__(self, pixmap, parent_view, idx, path, parent=None):
        super().__init__(pixmap, parent)
        self.parent_view = parent_view
        self.idx = idx
        self.img_path = path
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setTransformationMode(Qt.TransformationMode.SmoothTransformation)
        self.setTransformOriginPoint(self.boundingRect().center())
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.parent_view.image_double_clicked.emit(self.idx, self.img_path)
        super().mouseDoubleClickEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        
        # [优化修复] 防飞出修复：如果完全不在自己的画框内，复位到中心
        if self.sceneBoundingRect().width() > 0:
            container_rect = self.parentItem().sceneBoundingRect()
            item_rect = self.sceneBoundingRect()
            if not container_rect.intersects(item_rect):
                cx, cy = self.parent_view.centers[self.idx]
                pixmap = self.pixmap()
                self.setPos(cx - pixmap.width()/2, cy - pixmap.height()/2)

    def wheelEvent(self, event):
        if not self.isSelected():
            event.ignore(); return
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            event.ignore(); return
        try: delta = event.angleDelta().y() if hasattr(event, 'angleDelta') else event.delta()
        except: delta = 120
        factor = 1.05 if delta > 0 else 0.95
        self.setScale(self.scale() * factor)
        event.accept()

class CollageView(QGraphicsView):
    image_double_clicked = pyqtSignal(int, str)
    image_swapped = pyqtSignal(int, int)
    
    def __init__(self):
        super().__init__()
        self._scene = QGraphicsScene(self); self.setScene(self._scene); self._scene.setSceneRect(0, 0, 1200, 1680)
        self.setRenderHint(QPainter.RenderHint.Antialiasing); self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setBackgroundBrush(QColor("#2c2c2e")); self.setMinimumSize(400, 560)
        self.setStyleSheet("border-radius: 8px; border: 2px solid #8e8e93;")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        
        bg_rect = self._scene.addRect(0, 0, 1200, 1680, pen=QPen(Qt.PenStyle.NoPen), brush=QColor("#141414"))
        bg_rect.setZValue(-1)

        polys = [
            [(20, 20), (445, 20), (595, 835), (20, 939)],
            [(455, 20), (1180, 20), (1180, 735), (605, 835)],
            [(20, 959), (595, 845), (745, 1660), (20, 1660)],
            [(605, 845), (1180, 745), (1180, 1660), (755, 1660)]
        ]
        self.containers = []
        for poly in polys:
            path = get_rounded_poly(poly, 60)
            container = ContainerItem(path); self._scene.addItem(container); self.containers.append(container)
            
        self.current_paths = ["", "", "", ""]; self.image_items = [None, None, None, None]
        self.bboxes = [(20,20,570,914), (460,20,720,810), (20,850,720,810), (610,750,570,910)]
        self.centers = [(307, 479), (820, 425), (380, 1255), (895, 1205)]

    def get_state(self):
        state = []
        for i in range(4):
            item = self.image_items[i]
            if item:
                state.append({
                    'path': self.current_paths[i],
                    'scale': item.scale(),
                    'pos': (item.pos().x(), item.pos().y())
                })
            else:
                state.append(None)
        return state

    def load_state(self, state):
        for img in self.image_items:
            if img:
                try:
                    if img.scene(): img.scene().removeItem(img)
                except RuntimeError:
                    pass
        self.current_paths = ["", "", "", ""]
        self.image_items = [None, None, None, None]
        
        for i in range(4):
            s = state[i]
            if s and s.get('path') and os.path.exists(s['path']):
                self.current_paths[i] = s['path']
                img = QImage(s['path'])
                if img.isNull(): continue
                pixmap = QPixmap.fromImage(img)
                img_item = DraggableImage(pixmap, self, i, s['path'], parent=self.containers[i])
                
                img_item.setScale(s['scale'])
                img_item.setPos(s['pos'][0], s['pos'][1])
                img_item.setZValue(0)
                self.image_items[i] = img_item
                
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def load_images(self, paths):
        for img in self.image_items:
            if img:
                try:
                    if img.scene(): img.scene().removeItem(img)
                except RuntimeError:
                    pass
        self.current_paths = (list(paths) + ["", "", "", ""])[:4]
        for i in range(4):
            path = self.current_paths[i]
            if path and os.path.exists(path):
                img = QImage(path)
                if img.isNull(): continue
                pixmap = QPixmap.fromImage(img)
                img_item = DraggableImage(pixmap, self, i, path, parent=self.containers[i])
                bw, bh = self.bboxes[i][2], self.bboxes[i][3]
                img_ratio = pixmap.width() / pixmap.height(); box_ratio = bw / bh
                scale = bh / pixmap.height() if img_ratio > box_ratio else bw / pixmap.width()
                img_item.setScale(scale); cx, cy = self.centers[i]
                img_item.setPos(cx - pixmap.width()/2, cy - pixmap.height()/2)
                img_item.setZValue(0); self.image_items[i] = img_item
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def replace_image(self, idx, path):
        if self.image_items[idx]:
            try:
                if self.image_items[idx].scene(): self._scene.removeItem(self.image_items[idx])
            except RuntimeError:
                pass
        self.current_paths[idx] = path; img = QImage(path)
        if img.isNull(): return
        pixmap = QPixmap.fromImage(img)
        img_item = DraggableImage(pixmap, self, idx, path, parent=self.containers[idx])
        bw, bh = self.bboxes[idx][2], self.bboxes[idx][3]
        img_ratio = pixmap.width() / pixmap.height(); box_ratio = bw / bh
        scale = bh / pixmap.height() if img_ratio > box_ratio else bw / pixmap.width()
        img_item.setScale(scale); cx, cy = self.centers[idx]
        img_item.setPos(cx - pixmap.width()/2, cy - pixmap.height()/2)
        img_item.setZValue(0); self.image_items[idx] = img_item

    def clear_images(self):
        for img in self.image_items:
            if img:
                try:
                    sc = img.scene()
                    if sc: sc.removeItem(img)
                except RuntimeError:
                    pass
        self.current_paths = ["", "", "", ""]
        self.image_items = [None, None, None, None]
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def swap_images(self, idx1, idx2):
        path1 = self.current_paths[idx1]
        path2 = self.current_paths[idx2]
        self.replace_image(idx1, path2)
        self.replace_image(idx2, path1)
        self.image_swapped.emit(idx1, idx2)

    def wheelEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            try: delta = event.angleDelta().y() if hasattr(event, 'angleDelta') else event.delta()
            except: delta = 120
            factor = 1.1 if delta > 0 else 0.9; self.scale(factor, factor)
            event.accept()
        else: super().wheelEvent(event)

    def render_to_file(self, filepath):
        self._scene.clearSelection()
        img = QImage(1200, 1680, QImage.Format.Format_ARGB32); img.fill(QColor("#141414"))
        painter = QPainter(img); painter.setRenderHint(QPainter.RenderHint.Antialiasing); painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._scene.render(painter, target=QRectF(0,0,1200,1680), source=QRectF(0,0,1200,1680))
        painter.end()
        return img.save(filepath, "JPG", 80)

class CheckableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent); self.setEditable(True); self.lineEdit().setReadOnly(True); self.lineEdit().installEventFilter(self); self.setModel(QStandardItemModel(self)); self.view().viewport().installEventFilter(self)
    def eventFilter(self, obj, event):
        if obj == self.lineEdit() and event.type() == QEvent.Type.MouseButtonRelease: self.showPopup(); return True
        if obj == self.view().viewport() and event.type() == QEvent.Type.MouseButtonRelease:
            index = self.view().indexAt(event.pos())
            if index.isValid():
                item = self.model().itemFromIndex(index); item.setCheckState(Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked); self.updateText()
            return True
        return super().eventFilter(obj, event)
    def set_items(self, items, checked_items=None):
        if checked_items is None: checked_items = []
        self.clear()
        for text in items:
            item = QStandardItem(text); item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled); item.setCheckState(Qt.CheckState.Checked if text in checked_items else Qt.CheckState.Unchecked); self.model().appendRow(item)
        self.updateText()
    def get_checked_items(self): return [self.model().item(i).text() for i in range(self.count()) if self.model().item(i).checkState() == Qt.CheckState.Checked]
    def updateText(self): checked = self.get_checked_items(); self.lineEdit().setText(", ".join(checked) if checked else "未选择标签...")

class BatchWorkerThread(QThread):
    log_signal = pyqtSignal(str, str); progress_signal = pyqtSignal(int); cell_update_signal = pyqtSignal(int, int, str, str); finished_signal = pyqtSignal(int, int) 
    def __init__(self, mode, tasks, config, parent=None):
        super().__init__(parent); self.mode = mode; self.tasks = tasks; self.config = config; self.is_running = True; self._tags_fetched = False
        self.tag_id_map = {"禁转": "1", "官方": "3", "大师": "8", "时光机": "11", "CN": "15", "JP": "16", "FR": "17", "UK": "18", "私房": "19", "COSER": "20", "US": "21", "KR": "22", "GER": "23", "古风": "24", "可商用": "25", "RAW": "26", "杂志": "27", "OTHER": "28", "马格南": "29", "明星": "30", "樱花妹": "31"}
    def stop(self): self.is_running = False
    def emit_log(self, msg, level="INFO"): self.log_signal.emit(msg, level)
    def _proxies(self): return normalize_proxy(self.config.get('proxy_addr')) if self.config.get('use_proxy') else None
    def run(self):
        total_tasks = len(self.tasks); success_count = 0; sim_count = 0
        if total_tasks == 0: self.finished_signal.emit(0, 0); return
        try: import torf
        except ImportError: self.emit_log("【环境报错】未安装 torf 库！请执行: pip install torf", "ERROR"); self.finished_signal.emit(0, total_tasks); return
        torrent_dir = self.config['torrent_dir']; seeding_dir = self.config['seeding_dir'] 
        local_torrent_dir = os.path.join(torrent_dir, "Local_Made"); pt_torrent_dir = os.path.join(torrent_dir, "PT_Official")
        os.makedirs(torrent_dir, exist_ok=True); os.makedirs(seeding_dir, exist_ok=True); os.makedirs(local_torrent_dir, exist_ok=True); os.makedirs(pt_torrent_dir, exist_ok=True)
        announce_url = self.config['pt_url'] + "announce.php"; use_zip = self.config['use_zip']; upload_form_url = f"{self.config['pt_url']}upload.php"; upload_submit_url = f"{self.config['pt_url']}takeupload.php"
        if self.mode in ['publish', 'auto'] and not self._tags_fetched:
            self.emit_log("🌐 [网络阶段] 尝试抓取站点最新标签库...", "INFO")
            try:
                tu_resp = requests.get(upload_form_url, headers={"Cookie": self.config['cookie']}, timeout=15, proxies=self._proxies())
                matches = re.findall(r'name="tags\[\d+\]\[\]"\s+value="(\d+)"\s*/>([^<]+)</label>', tu_resp.text, re.I); d_map = {name.strip(): val for val, name in matches if val.isdigit() and name}
                if d_map: self.tag_id_map.update(d_map); self.emit_log(f"✅ 标签同步成功({len(self.tag_id_map)})", "SUCCESS")
                else: self.emit_log("⚠️ 抓取标签失败，启用内置密码本！", "WARNING")
            except Exception as e: self.emit_log(f"标签库同步异常: {e}", "WARNING")
            self._tags_fetched = True
        for idx, task in enumerate(self.tasks):
            if not self.is_running: self.emit_log("🛑 任务被中止！", "WARNING"); break
            row, std_name, folder_path = task['row'], task['std_name'], task['folder_path']
            base_prog = (idx / total_tasks) * 100; task_weight = 100 / total_tasks
            def set_p(percent): self.progress_signal.emit(int(base_prog + (percent / 100.0) * task_weight))
            self.emit_log(f"▶️ [开始处理] 第 {idx+1}/{total_tasks} 项任务: {std_name}", "INFO"); set_p(5)
            if self.mode in ['make', 'auto']:
                if not os.path.exists(folder_path): self.cell_update_signal.emit(row, 9, "❌ 路径失效", "#ff3b30"); set_p(100); continue
                self.cell_update_signal.emit(row, 9, "制作中...", "#ff9500")
                try:
                    reuse = self.config.get('reuse_existing', False)
                    target_path = folder_path
                    zip_path = os.path.join(seeding_dir, f"{sanitize_filename(std_name)}.zip") if use_zip else None
                    out_file = os.path.join(local_torrent_dir, f"{sanitize_filename(std_name)}{'.zip' if use_zip else ''}.torrent")
                    if reuse and find_existing_file(out_file):
                        out_file = find_existing_file(out_file)
                        self.emit_log(f"♻️ 复用已存在的种子，跳过重新生成: {os.path.basename(out_file)}", "INFO")
                        self.cell_update_signal.emit(row, 9, "✅ 已制种(复用)", "#34c759")
                        if self.mode == 'make': success_count += 1
                    else:
                        if use_zip:
                            if reuse and find_existing_file(zip_path):
                                zip_path = find_existing_file(zip_path); target_path = zip_path; self.emit_log(f"♻️ 复用已存在的 ZIP: {os.path.basename(zip_path)}", "INFO")
                            else:
                                set_p(15); zip_name = os.path.basename(zip_path); self.emit_log(f"📦 [文件打包] 制作极速零压缩封包 ZIP: {zip_name} ...", "INFO")
                                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_STORED) as zipf:
                                    for root, _, files in os.walk(folder_path):
                                        for f in files:
                                            if not self.is_running: raise InterruptedError()
                                            zipf.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), os.path.join(folder_path, '..')))
                                target_path = zip_path; self.emit_log(f"✅ ZIP 打包完毕！", "SUCCESS")
                        set_p(35); self.emit_log(f"⚙️ [种子生成] 计算哈希...", "INFO")
                        t = torf.Torrent(path=target_path, trackers=[announce_url], private=True); t.generate()
                        if find_existing_file(out_file): out_file = find_existing_file(out_file); self.emit_log(f"♻️ 已存在同名种子，覆盖重新生成: {os.path.basename(out_file)}", "WARNING")
                        t.write(out_file, overwrite=True)
                        self.cell_update_signal.emit(row, 9, "✅ 已制种", "#34c759")
                        if self.mode == 'make': success_count += 1
                except Exception as e:
                    self.cell_update_signal.emit(row, 9, "❌ 生成失败", "#ff3b30"); self.emit_log(f"制种出错: {e}", "ERROR"); set_p(100); continue
                set_p(50 if self.mode == 'auto' else 100)
            if self.mode in ['publish', 'auto']:
                set_p(55 if self.mode == 'auto' else 10); img_url = ""
                if task['thumb_path'] and os.path.exists(task['thumb_path']):
                    self.cell_update_signal.emit(row, 10, "⬆️ 上传图片...", "#ff9500"); self.emit_log(f"🖼️ [图床通信] 上传封面...", "INFO")
                    try:
                        mime_type = mimetypes.guess_type(task['thumb_path'])[0] or 'image/jpeg'
                        file_size_mb = os.path.getsize(task['thumb_path']) / (1024 * 1024)
                        if file_size_mb > 5.0: self.emit_log(f"⚠️ 警告: 封面体积({file_size_mb:.2f}MB)超过 5MB 限制！", "WARNING")
                        
                        retry_limit = self.config.get('image_retry_count', 5)
                        for retry in range(retry_limit):
                            try:
                                with open(task['thumb_path'], 'rb') as f:
                                    files = {"file": (os.path.basename(task['thumb_path']), f, mime_type)}; headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
                                    raw_token = self.config.get('image_token', '').strip()
                                    if raw_token:
                                        if raw_token.lower().startswith('bearer '): raw_token = raw_token[7:].strip()
                                        headers["Authorization"] = f"Bearer {raw_token}"
                                    img_res = requests.post(self.config['image_upload_api'], headers=headers, files=files, timeout=120, proxies=self._proxies())
                                if img_res.status_code in [200, 201]:
                                    try:
                                        img_data = img_res.json()
                                        img_url = img_data.get('data', {}).get('links', {}).get('url', '') or img_data.get('data', {}).get('url', '') or img_data.get('image', {}).get('url', '')
                                        self.emit_log(f"✅ 图床上传成功: {img_url}", "SUCCESS")
                                    except: pass
                                else: self.emit_log(f"❌ 图床拒绝上传! 状态码: {img_res.status_code} | 拦截: {img_res.text[:100]}", "ERROR")
                                break 
                            except Exception as e: 
                                self.emit_log(f"⚠️ 图床波动({e})，重试 {retry+1}/{retry_limit}", "WARNING"); QThread.msleep(2000)
                                if retry == retry_limit - 1: raise
                    except Exception as e: self.emit_log(f"❌ 图床通讯失败: {e}", "ERROR")
                set_p(65 if self.mode == 'auto' else 30)
                cat_id = resolve_category(task.get('category'), self.config['category_map'])
                if cat_id is None:
                    self.cell_update_signal.emit(row, 10, "❌ 未选择分类", "#ff3b30")
                    self.emit_log(f"❌ [拦截] 未选择有效分类，已跳过: {std_name}", "ERROR"); set_p(100); continue
                mode_4_cats = ["401", "402", "403", "404", "416", "415", "414", "413", "412", "411", "405"]
                cat_mode = "4" if cat_id in mode_4_cats else "5"; tag_param_name = f"tags[{cat_mode}][]"
                bbcode_img = build_bbcode_img(img_url, task['thumb_path'], self.emit_log)
                disclaimer = "\n\n[quote]本站不是一个以盈利为目的的站点，所有资源均来自本人购买实体摄影集拍摄和网上搜集而来，任何涉及商业或盈利目的均不可使用本站资源，否则后果自负，本站将不对本站的任何内容负任何法律责任!所有下载内容仅供测试宽带使用，测试后请立即删除。如您下载本站任何资源，即代表您接受本声明及条款。本站支持正版，请购买正版!如版权持有人发现本站有任何侵犯版权持有人权益的资源，请通知本站管理人员予以删除![/quote]"
                full_descr = f"{task['intro']}\n\n{bbcode_img}{disclaimer}"; data_payload = {"name": std_name, "type": cat_id, "descr": full_descr}
                if self.config.get('anonymous', True): data_payload['uplver'] = 'yes'
                post_data = list(data_payload.items()); self.emit_log("🔖 [表单组装] 组装分类与标签...", "INFO")
                final_tags = ["官方", "禁转"] + task['tag_names']
                for t_name in set(final_tags): 
                    if t_name in self.tag_id_map: post_data.append((tag_param_name, self.tag_id_map[t_name]))
                    else: post_data.append((tag_param_name, t_name)); self.emit_log(f"   -> ⚠️ 未找到标签 [{t_name}] 的 ID", "WARNING")
                if self.config['test_mode']:
                    self.emit_log(f"【测试模式】发种拦截！\n📌 最终标题: {std_name}\n📂 分类ID: {cat_id}\n🔖 标签参数: {tag_param_name}\n🏷️ 真实标签: {final_tags}\n📝 组装简介:\n------------------\n{full_descr}\n------------------", "INFO")
                    self.cell_update_signal.emit(row, 10, "✅ 模拟完毕", "#34c759"); sim_count += 1; set_p(100); continue
                stem = sanitize_filename(std_name)
                torrent_path = find_existing_file(os.path.join(local_torrent_dir, f"{stem}.torrent")) or find_existing_file(os.path.join(local_torrent_dir, f"{stem}.zip.torrent"))
                if not torrent_path: torrent_path = find_torrent_in_dir(local_torrent_dir, stem)
                if torrent_path:
                    self.emit_log(f"🔎 命中本地种子: {os.path.basename(torrent_path)}", "INFO")
                else:
                    # 兼容 macOS 等场景：种子文件缺失但封包/源文件夹仍在时，现场补做种子
                    self.emit_log(f"⚠️ 未找到本地种子，尝试现场补做...（目录: {local_torrent_dir}）", "WARNING")
                    try:
                        src = None
                        if use_zip:
                            src = find_existing_file(os.path.join(seeding_dir, f"{stem}.zip"))
                            if not src and os.path.isdir(folder_path):
                                src = os.path.join(seeding_dir, f"{stem}.zip")
                                with zipfile.ZipFile(src, 'w', zipfile.ZIP_STORED) as zipf:
                                    for root, _, files in os.walk(folder_path):
                                        for f in files:
                                            zipf.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), os.path.join(folder_path, '..')))
                                self.emit_log(f"✅ 现场补做 ZIP 成功: {os.path.basename(src)}", "SUCCESS")
                        elif os.path.isdir(folder_path): src = folder_path
                        if src:
                            t = torf.Torrent(path=src, trackers=[announce_url], private=True); t.generate()
                            torrent_path = os.path.join(local_torrent_dir, f"{stem}{'.zip' if use_zip else ''}.torrent")
                            t.write(torrent_path, overwrite=True)
                            self.emit_log(f"✅ 现场补做种子成功: {os.path.basename(torrent_path)}", "SUCCESS")
                    except Exception as e:
                        self.emit_log(f"现场补做种子失败: {e}", "ERROR")
                if not torrent_path or not os.path.exists(torrent_path):
                    self.cell_update_signal.emit(row, 10, "❌ 未制作种子", "#ff3b30")
                    try: listing = os.listdir(local_torrent_dir)[:8]
                    except Exception: listing = []
                    self.emit_log(f"❌ 未找到种子文件: {stem}(.zip).torrent | 目录内文件: {listing}", "ERROR"); set_p(100); continue
                self.cell_update_signal.emit(row, 10, "🚀 推送中...", "#ff9500"); set_p(80 if self.mode == 'auto' else 60)
                try:
                    self.emit_log(f"🌐 [网络推送] 发送表单数据...", "INFO")
                    with open(torrent_path, "rb") as file_stream:
                        files = {'file': (os.path.basename(torrent_path), file_stream, 'application/x-bittorrent')}
                        headers = {"User-Agent": "MMTautofeed-Client/V1.00.0", "Cookie": self.config['cookie']}
                        resp = requests.post(upload_submit_url, headers=headers, data=post_data, files=files, timeout=25, allow_redirects=True, proxies=self._proxies())
                    torrent_id = extract_torrent_id(resp.url)
                    if resp.status_code in [200, 302] and torrent_id:
                        self.cell_update_signal.emit(row, 10, "✅ 发布成功", "#34c759"); self.emit_log(f"🎉【发布成功】种子ID: {torrent_id} | 最终URL: {resp.url}", "SUCCESS")
                        success_count += 1; set_p(90 if self.mode == 'auto' else 80)
                        if self.config['add_to_qb']:
                            dl_url = f"{self.config['pt_url']}download.php?id={torrent_id}"; self.emit_log(f"📥 [种子拉取] 请求带 Passkey 的种子...", "INFO")
                            final_torrent_path = torrent_path
                            for dl_retry in range(3):
                                try:
                                    dl_resp = requests.get(dl_url, headers=headers, timeout=30, proxies=self._proxies())
                                    if dl_resp.status_code == 200 and len(dl_resp.content) > 100:
                                        final_torrent_path = os.path.join(pt_torrent_dir, f"[PT]{std_name}.torrent")
                                        with open(final_torrent_path, "wb") as tf: tf.write(dl_resp.content)
                                        self.emit_log(f"✅ 官方种子拉取成功: {final_torrent_path}", "SUCCESS"); break
                                    else: 
                                        if dl_retry == 2: self.emit_log("拉取失败，降级使用本地种子推送", "WARNING")
                                except Exception as e:
                                    self.emit_log(f"⚠️ 官方种子拉取超时({e})，重试 {dl_retry+1}/3", "WARNING"); QThread.msleep(2000)
                            set_p(95 if self.mode == 'auto' else 90); save_dir = os.path.abspath(seeding_dir if use_zip else os.path.dirname(folder_path))
                            try:
                                import qbittorrentapi
                                client = qbittorrentapi.Client(host=self.config['qb_url'], username=self.config['qb_user'], password=self.config['qb_pwd']); client.auth_log_in()
                                add_kwargs = {"torrent_files": final_torrent_path, "save_path": save_dir, "is_paused": False, "use_auto_torrent_management": False}
                                if self.config.get('qb_category'): add_kwargs['category'] = self.config['qb_category']
                                if self.config.get('qb_tags'): add_kwargs['tags'] = self.config['qb_tags']
                                client.torrents_add(**add_kwargs)
                                self.emit_log(f"📡 [qB做种] 成功推送到 qBittorrent！\n   -> 挂载路径: {save_dir}", "SUCCESS")
                            except Exception as e: self.emit_log(f"⚠️ qB 无法连接: {e}", "WARNING")
                    else:
                        self.emit_log(f"🔎 发种响应: HTTP {resp.status_code} | 最终URL: {resp.url}", "INFO")
                        if 'login.php' in resp.url and not torrent_id:
                            self.cell_update_signal.emit(row, 10, "❌ Cookie失效", "#ff3b30")
                            self.emit_log(f"🚨 重定向至登录页，Cookie失效！请在【偏好设置】中重新粘贴浏览器里完整的 Cookie（需包含用户身份项，如 c_secure_uid 和 c_secure_pass）。", "ERROR")
                        else: self.cell_update_signal.emit(row, 10, f"⚠️ 频控或异常", "#ff3b30"); self.emit_log(f"🚨 页面未返回有效的种子 ID。", "ERROR")
                except Exception as e: self.cell_update_signal.emit(row, 10, "断网/超时", "#ff3b30"); self.emit_log(f"网络连接断开: {e}", "ERROR")
                set_p(100)
            if idx < total_tasks - 1 and self.config.get('seed_delay', 5) > 0 and self.mode in ['publish', 'auto']:
                delay_sec = self.config['seed_delay']; self.emit_log(f"⏳ 触发限流保护，等待 {delay_sec} 秒...", "INFO")
                for wait_sec in range(delay_sec, 0, -1):
                    if not self.is_running: break
                    self.emit_log(f"⏳ 倒计时: {wait_sec} 秒", "INFO"); QThread.msleep(1000) 
        if sim_count > 0: self.emit_log(f"🧪 测试模式：共模拟 {sim_count} 项，未实际发布任何种子。", "INFO")
        self.progress_signal.emit(100); self.finished_signal.emit(success_count, total_tasks)

class AddPresetDialog(QDialog):
    def __init__(self, parent=None, font_size=10):
        super().__init__(parent); self.setWindowTitle("添加 / 编辑预设方案"); self.resize(980, 700)
        layout = QVBoxLayout(self); form_layout = QFormLayout(); form_layout.setSpacing(14) 
        self.input_preset_name = QLineEdit(); form_layout.addRow("预设名称*:", self.input_preset_name)
        self.input_photographer = QLineEdit(); form_layout.addRow("摄影师:", self.input_photographer)
        self.input_model = QLineEdit(); form_layout.addRow("主角/模特:", self.input_model)
        lbl_h = QLabel("💡 提示：至少填写【摄影师】或【主角/模特】之一才能正确生成名字"); lbl_h.setStyleSheet("color: #ff3b30; font-size: 12px;"); lbl_h.setContentsMargins(0, 0, 0, 0); form_layout.addRow("", lbl_h)
        self.input_intro = QTextEdit(); self.input_intro.setMinimumHeight(150); self.input_intro.setAcceptRichText(False) 
        self.input_intro.setStyleSheet(f"QTextEdit {{ font-size: {font_size}pt; }}"); font = self.input_intro.font(); font.setPointSize(font_size); self.input_intro.setFont(font); self.input_intro.document().setDefaultFont(font) 
        w_intro = QWidget(); h_intro = QHBoxLayout(w_intro); h_intro.setContentsMargins(0, 0, 0, 0)
        h_intro.addWidget(QLabel("统一简介:")); h_intro.addStretch(); h_intro.addWidget(QLabel("字号调节:"))
        self.spin_intro_font = QSpinBox(); self.spin_intro_font.setRange(9, 24); self.spin_intro_font.setValue(font_size)
        def update_font(v): self.input_intro.setStyleSheet(f"QTextEdit {{ font-size: {v}pt; }}"); f = self.input_intro.font(); f.setPointSize(v); self.input_intro.setFont(f); self.input_intro.document().setDefaultFont(f)
        self.spin_intro_font.valueChanged.connect(update_font); h_intro.addWidget(self.spin_intro_font)
        form_layout.addRow(w_intro); form_layout.addRow(self.input_intro)
        self.combo_category = QComboBox(); self.combo_category.addItems(SITE_CATEGORIES); form_layout.addRow("默认分类:", self.combo_category)
        layout.addLayout(form_layout)
        group_tags = QGroupBox("默认附加标签 (已隐去底层强制绑定的 官方、禁转)"); tags_layout = QGridLayout(); tags_layout.setSpacing(10); self.checkboxes = {}
        for i, tag in enumerate(GLOBAL_TAGS): cb = QCheckBox(tag); self.checkboxes[tag] = cb; tags_layout.addWidget(cb, i // 5, i % 5)
        group_tags.setLayout(tags_layout); layout.addWidget(group_tags)
        layout.addStretch(); btn_layout = QHBoxLayout(); btn_layout.addStretch()
        btn_save = QPushButton("💾 保存设定"); btn_save.setStyleSheet("background-color: #34c759; color: white;"); btn_save.clicked.connect(self.accept) 
        btn_cancel = QPushButton("取消"); btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save); btn_layout.addWidget(btn_cancel); layout.addLayout(btn_layout)
    def get_font_size(self): return self.spin_intro_font.value()
    def set_data(self, data):
        self.input_preset_name.setText(data.get("name", "")); self.input_photographer.setText(data.get("photographer", "")); self.input_model.setText(data.get("model", "")); self.input_intro.setText(data.get("intro", "")); self.combo_category.setCurrentText(data.get("category", "请选择分类..."))
        for tag, cb in self.checkboxes.items(): cb.setChecked(tag in data.get("tags", []))
    def get_data(self): return {"name": self.input_preset_name.text().strip(), "photographer": self.input_photographer.text().strip(), "model": self.input_model.text().strip(), "intro": self.input_intro.toPlainText().strip(), "category": self.combo_category.currentText(), "tags": [t for t, c in self.checkboxes.items() if c.isChecked()]}

class ManagePresetsDialog(QDialog):
    def __init__(self, parent_main_window):
        super().__init__(parent_main_window); self.parent_win = parent_main_window; self.setWindowTitle("预设配置管理"); self.resize(980, 600)
        layout = QVBoxLayout(self); h_top = QHBoxLayout()
        btn_add = QPushButton("十 新增一条预设"); btn_add.setStyleSheet("background-color: #007aff; color: white; border: none; padding: 6px;"); btn_add.clicked.connect(self.open_add_preset)
        btn_refresh = QPushButton("🔄 刷新表格"); btn_refresh.clicked.connect(self.refresh_table); h_top.addWidget(btn_add); h_top.addWidget(btn_refresh); h_top.addStretch(); layout.addLayout(h_top)
        self.table = QTableWidget(0, 8); self.table.setHorizontalHeaderLabels(["模板名称", "摄影师", "模特", "简介", "分类", "标签", "复制", "操作"])
        self.table.horizontalHeader().setStretchLastSection(False); self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 120); self.table.setColumnWidth(1, 90); self.table.setColumnWidth(2, 90); self.table.setColumnWidth(4, 70); self.table.setColumnWidth(5, 100); self.table.setColumnWidth(6, 60); self.table.setColumnWidth(7, 90)
        self.table.verticalHeader().setDefaultSectionSize(36); layout.addWidget(self.table)
        h_bottom = QHBoxLayout(); h_bottom.addStretch(); btn_close = QPushButton("关闭管理面板"); btn_close.clicked.connect(self.accept); h_bottom.addWidget(btn_close); layout.addLayout(h_bottom); self.refresh_table()
    def open_add_preset(self):
        dialog = AddPresetDialog(self, font_size=self.parent_win.preset_font_size); dialog.setStyleSheet(self.parent_win.styleSheet())
        if dialog.exec(): 
            d = dialog.get_data()
            if not d["name"]: return QMessageBox.warning(self, "错误", "名称不能为空！")
            self.parent_win.presets_data.append(d); self.parent_win.save_presets(); self.refresh_table(); self.parent_win.refresh_main_preset_combo(); self.parent_win.preset_font_size = dialog.get_font_size(); self.parent_win.save_config(silent=True)
    def edit_preset(self, row):
        dialog = AddPresetDialog(self, font_size=self.parent_win.preset_font_size); dialog.setStyleSheet(self.parent_win.styleSheet()); dialog.set_data(self.parent_win.presets_data[row])
        if dialog.exec(): 
            nd = dialog.get_data()
            if not nd["name"]: return
            self.parent_win.presets_data[row] = nd; self.parent_win.save_presets(); self.refresh_table(); self.parent_win.refresh_main_preset_combo(); self.parent_win.preset_font_size = dialog.get_font_size(); self.parent_win.save_config(silent=True)
    def copy_preset(self, row):
        src = self.parent_win.presets_data[row] if 0 <= row < len(self.parent_win.presets_data) else None
        if not isinstance(src, dict): self.parent_win.log_msg("❌ 复制失败：预设数据无效", "ERROR"); return
        new_data = src.copy(); new_data["name"] = (new_data.get("name") or "未命名预设") + "-副本"; self.parent_win.presets_data.append(new_data)
        self.parent_win.save_presets(); self.refresh_table(); self.parent_win.refresh_main_preset_combo(); self.parent_win.log_msg(f"已成功复制生成预设副本：{new_data['name']}", "SUCCESS")
    def refresh_table(self):
        self.table.setRowCount(0)
        for row, preset in enumerate(self.parent_win.presets_data):
            self.table.insertRow(row); self.table.setItem(row, 0, QTableWidgetItem(preset.get("name", ""))); self.table.setItem(row, 1, QTableWidgetItem(preset.get("photographer", ""))); self.table.setItem(row, 2, QTableWidgetItem(preset.get("model", ""))); self.table.setItem(row, 3, QTableWidgetItem(preset.get("intro", ""))); self.table.setItem(row, 4, QTableWidgetItem(preset.get("category", ""))); self.table.setItem(row, 5, QTableWidgetItem(", ".join(preset.get("tags", []))))
            aw_copy = QWidget(); h_copy = QHBoxLayout(aw_copy); h_copy.setContentsMargins(6, 4, 6, 4)
            btn_copy = QPushButton("复制"); btn_copy.setStyleSheet("background-color: #34c759; color: white; padding: 4px; font-size: 11px; border:none; border-radius: 4px;"); btn_copy.clicked.connect(lambda checked, r=row: self.copy_preset(r))
            h_copy.addWidget(btn_copy); self.table.setCellWidget(row, 6, aw_copy)
            aw_act = QWidget(); h_act = QHBoxLayout(aw_act); h_act.setContentsMargins(4, 4, 4, 4); h_act.setSpacing(4)
            btn_edit = QPushButton("编辑"); btn_edit.setStyleSheet("background-color: #ff9500; color: white; padding: 4px; font-size: 11px; border:none; border-radius: 4px;"); btn_edit.clicked.connect(lambda checked, r=row: self.edit_preset(r))
            btn_del = QPushButton("删除"); btn_del.setStyleSheet("background-color: #ff3b30; color: white; padding: 4px; font-size: 11px; border:none; border-radius: 4px;"); btn_del.clicked.connect(lambda checked, r=row: self.delete_preset(r))
            h_act.addWidget(btn_edit); h_act.addWidget(btn_del); self.table.setCellWidget(row, 7, aw_act)
    def delete_preset(self, row):
        if QMessageBox.question(self, '确认删除', "确定永久删除此条预设？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes: del self.parent_win.presets_data[row]; self.parent_win.save_presets(); self.refresh_table(); self.parent_win.refresh_main_preset_combo()

class RuleWidget(QWidget):
    def __init__(self, parent_layout, rule_data=None, is_dark=False):
        super().__init__()
        self.parent_layout = parent_layout
        self.is_dark = is_dark
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.combo_type = QComboBox()
        self.combo_type.addItems(["文本替换", "正则匹配"]) 
        self.combo_type.setToolTip("选择解析引擎的匹配模式")
        
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("[A-Z] (你想消除或替换的特征)")
        self.input_search.setMinimumWidth(80)
        self.input_search.setMaximumWidth(110)
        self.input_search.setToolTip("📌 【查找特征】\n输入你需要查找或消除的文本特征。\n如果左侧选择了'正则匹配'，此处可直接填入正则表达式。")
        
        self.lbl_arrow = QLabel("➔")
        self.lbl_arrow.setStyleSheet("font-weight: bold; margin: 0 5px;")
        
        self.input_replace = QLineEdit()
        self.input_replace.setPlaceholderText("替换为 (留空表示直接删除)")
        self.input_replace.setMinimumWidth(80)
        self.input_replace.setMaximumWidth(110)
        self.input_replace.setToolTip("📌 【替换内容】\n输入你想将其替换成的目标文本。\n如果你只想删除前面查找到的文本特征，请将此处保持留空！")
        
        self.btn_del = QPushButton("🗑")
        self.btn_del.setToolTip("删除此条规则")
        self.btn_del.clicked.connect(self.remove_self)
        
        layout.addWidget(self.combo_type)
        layout.addWidget(self.input_search)
        layout.addWidget(self.lbl_arrow)
        layout.addWidget(self.input_replace)
        layout.addWidget(self.btn_del)
        layout.addStretch()  
        
        if rule_data:
            self.combo_type.setCurrentText("正则匹配" if rule_data.get("type") == "regex" else "文本替换")
            self.input_search.setText(rule_data.get("search", ""))
            self.input_replace.setText(rule_data.get("replace", ""))

        self.apply_local_style()

    def apply_local_style(self):
        if self.is_dark:
            style = """
                QWidget { background: transparent; }
                QComboBox, QLineEdit { background-color: #121212; color: #ffffff; border: 1px solid #aaaaaa; border-radius: 4px; padding: 5px; min-height: 24px; }
                QComboBox:focus, QLineEdit:focus { border: 1px solid #0a84ff; }
                QComboBox QAbstractItemView { background-color: #1e1e1e; color: #ffffff; selection-background-color: #0a84ff; border: 1px solid #aaaaaa; }
                QToolTip { background-color: #2c2c2e; color: #ffffff; border: 1px solid #aaaaaa; font-size: 13px; padding: 4px; border-radius: 4px;}
                QPushButton { background-color: #ff3b30; color: #ffffff; border-radius: 4px; padding: 5px; font-weight: bold; border: none; }
                QPushButton:hover { background-color: #ff453a; }
                QLabel { color: #aaaaaa; }
            """
        else:
            style = """
                QWidget { background: transparent; }
                QComboBox, QLineEdit { background-color: #ffffff; color: #000000; border: 1px solid #666666; border-radius: 4px; padding: 5px; min-height: 24px; }
                QComboBox:focus, QLineEdit:focus { border: 1px solid #007aff; }
                QComboBox QAbstractItemView { background-color: #ffffff; color: #000000; selection-background-color: #007aff; border: 1px solid #666666; }
                QToolTip { background-color: #ffffe1; color: #000000; border: 1px solid #000000; font-size: 13px; padding: 4px; border-radius: 4px;}
                QPushButton { background-color: #ff3b30; color: #ffffff; border-radius: 4px; padding: 5px; font-weight: bold; border: none; }
                QPushButton:hover { background-color: #ff453a; }
                QLabel { color: #666666; }
            """
        self.setStyleSheet(style)

    def get_data(self):
        return {
            "type": "regex" if self.combo_type.currentText() == "正则匹配" else "replace",
            "search": self.input_search.text(),
            "replace": self.input_replace.text()
        }

    def remove_self(self):
        self.parent_layout.removeWidget(self)
        self.deleteLater()

class PTUploaderBase(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MMTautofeed批量发种工具 V1.00.0 (带名称解析引擎)")
        self.resize(1300, 880) 
        self.current_theme = "light"; self.hint_labels = []; self.presets_data = []; self.clean_keywords = []; self.clean_exts = []; self.preset_font_size = 10; self.base_dir = ""; self.last_dir = ""
        self.custom_rules = []
        
        self.cover_assignments = {}
        self.cover_states = {} 
        self.current_preview_folder = None

    def init_directories(self):
        if getattr(sys, 'frozen', False):
            if sys.platform == 'darwin': self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(sys.executable))))
            else: self.base_dir = os.path.dirname(sys.executable)
        else: self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.last_dir = self.base_dir
        os.makedirs(os.path.join(self.get_data_dir(), 'logs'), exist_ok=True)

    def get_data_dir(self):
        if getattr(sys, 'frozen', False):
            if sys.platform == 'darwin':
                data_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'MMTautofeed')
            else:
                data_dir = os.path.dirname(sys.executable)
        else:
            data_dir = os.path.dirname(os.path.abspath(__file__))
        os.makedirs(data_dir, exist_ok=True)
        return data_dir

    def log_msg(self, msg, level="INFO"):
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        log_line = f"{time_str} | {level} | {msg}"
        if hasattr(self, 'log_view'): 
            self.log_view.append(log_line); self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())
        if hasattr(self, 'batch_log'): 
            self.batch_log.append(log_line); self.batch_log.verticalScrollBar().setValue(self.batch_log.verticalScrollBar().maximum())
        QApplication.processEvents()
        try:
            log_file = os.path.join(self.get_data_dir(), 'logs', f"mmtauto_{datetime.datetime.now().strftime('%Y%m%d')}.log")
            with open(log_file, 'a', encoding='utf-8') as f: f.write(log_line + '\n')
        except Exception: pass

    def load_presets(self):
        preset_file = os.path.join(self.get_data_dir(), 'presets.json')
        if os.path.exists(preset_file):
            try:
                with open(preset_file, 'r', encoding='utf-8') as f: self.presets_data = json.load(f)
            except Exception: pass

    def save_presets(self):
        try:
            with open(os.path.join(self.get_data_dir(), 'presets.json'), 'w', encoding='utf-8') as f: json.dump(self.presets_data, f, indent=4, ensure_ascii=False)
        except Exception as e: self.log_msg(f"写入预设文件异常: {e}", "ERROR")

    def apply_theme(self, theme_mode):
        self.current_theme = theme_mode
        style = STYLE_DARK if theme_mode == "dark" else STYLE_LIGHT
        self.setStyleSheet(style)
        QApplication.instance().setStyleSheet(style)
        self.refresh_hint_colors()
        
        if hasattr(self, 'layout_rules'):
            for i in range(self.layout_rules.count()):
                w = self.layout_rules.itemAt(i).widget()
                if isinstance(w, RuleWidget):
                    w.is_dark = (theme_mode == "dark")
                    w.apply_local_style()

    def theme_changed(self): self.apply_theme("dark" if self.combo_theme.currentIndex() == 1 else "light")

    def save_config(self, silent=False):
        parse_mode = "simple"
        if hasattr(self, 'rb_none') and self.rb_none.isChecked(): parse_mode = "none"
        elif hasattr(self, 'rb_full') and self.rb_full.isChecked(): parse_mode = "full"
        config_data = {
            "theme": "dark" if self.combo_theme.currentIndex() == 1 else "light",
            "pt_url": self.input_pt_url.text(), "cookie": self.input_cookie.text(), "api_key": self.input_api_key.text(),
            "torrent_path": self.input_t_path.text(), "seeding_path": self.input_s_path.text(),
            "image_email": self.input_img_email.text(), "image_pwd": self.input_img_pwd.text(), "image_token": self.input_img_token.text(),
            "image_upload_api": self.input_img_upload_url.text(), "image_token_url": self.input_img_token_url.text(),
            "image_retry_count": self.spin_img_retry.value() if hasattr(self, 'spin_img_retry') else 5,
            "seed_delay": self.spin_delay.value(), "qb_url": self.input_qb_url.text(), "qb_user": self.input_qb_user.text(), "qb_pwd": self.input_qb_pwd.text(),
            "qb_auto_add": self.chk_qb_add.isChecked(), "anonymous": self.cb_batch_anon.isChecked(), "parse_mode": parse_mode,
            "clean_keywords": [self.list_kw.item(i).text() for i in range(self.list_kw.count())] if hasattr(self, 'list_kw') else [],
            "clean_exts": [self.list_ext.item(i).text() for i in range(self.list_ext.count())] if hasattr(self, 'list_ext') else [],
            "preset_font_size": self.preset_font_size,
            "custom_rules": self.custom_rules,
            "reuse_existing": self.chk_reuse_existing.isChecked() if hasattr(self, 'chk_reuse_existing') else False,
            "use_proxy": self.chk_proxy.isChecked() if hasattr(self, 'chk_proxy') else False,
            "proxy_addr": self.input_proxy.text().strip() if hasattr(self, 'input_proxy') else "127.0.0.1:7897",
            "qb_category": self.input_qb_category.text() if hasattr(self, 'input_qb_category') else "",
            "qb_tags": self.input_qb_tags.text() if hasattr(self, 'input_qb_tags') else ""
        }
        try:
            with open(os.path.join(self.get_data_dir(), 'config.json'), 'w', encoding='utf-8') as f: json.dump(config_data, f, indent=4, ensure_ascii=False)
            if not silent: QMessageBox.information(self, "操作成功", "设置已保存！"); self.log_msg("偏好设置保存成功", "SUCCESS")
        except Exception as e: self.log_msg(f"配置保存失败: {e}", "ERROR")

    def load_config(self):
        config_file = os.path.join(self.get_data_dir(), 'config.json')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f: config_data = json.load(f)
                theme = config_data.get("theme", "light"); self.combo_theme.setCurrentIndex(1 if theme == "dark" else 0); self.apply_theme(theme)
                self.input_pt_url.setText(config_data.get("pt_url") or "https://www.momentpt.top/")
                self.input_cookie.setText(config_data.get("cookie", "")); self.input_api_key.setText(config_data.get("api_key", ""))
                self.input_t_path.setText(config_data.get("torrent_path") or "./torrents"); self.input_s_path.setText(config_data.get("seeding_path") or "./seeding")
                self.input_img_email.setText(config_data.get("image_email", "")); self.input_img_pwd.setText(config_data.get("image_pwd", "")); self.input_img_token.setText(config_data.get("image_token", ""))
                self.input_img_upload_url.setText(config_data.get("image_upload_api") or "https://img.momentpt.top/api/v1/upload")
                self.input_img_token_url.setText(config_data.get("image_token_url") or "https://img.momentpt.top/api/v1/tokens")
                if hasattr(self, 'spin_img_retry'): self.spin_img_retry.setValue(config_data.get("image_retry_count", 5))
                self.spin_delay.setValue(config_data.get("seed_delay", 5)); self.input_qb_url.setText(config_data.get("qb_url") or "http://127.0.0.1:8080")
                self.input_qb_user.setText(config_data.get("qb_user") or "admin"); self.input_qb_pwd.setText(config_data.get("qb_pwd", ""))
                
                if hasattr(self, 'input_qb_category'): self.input_qb_category.setText(config_data.get("qb_category", ""))
                if hasattr(self, 'input_qb_tags'): self.input_qb_tags.setText(config_data.get("qb_tags", ""))

                self.chk_qb_add.setChecked(config_data.get("qb_auto_add", True)); self.cb_batch_anon.setChecked(config_data.get("anonymous", True))
                if hasattr(self, 'chk_reuse_existing'): self.chk_reuse_existing.setChecked(config_data.get("reuse_existing", False))
                if hasattr(self, 'chk_proxy'): self.chk_proxy.setChecked(config_data.get("use_proxy", False))
                if hasattr(self, 'input_proxy'): self.input_proxy.setText(config_data.get("proxy_addr") or "127.0.0.1:7897")
                p_mode = config_data.get("parse_mode", "simple")
                if p_mode == "none": self.rb_none.setChecked(True)
                elif p_mode == "full": self.rb_full.setChecked(True)
                else: self.rb_simple.setChecked(True)
                
                if hasattr(self, 'sandbox_combo_mode'):
                    if p_mode == "none": self.sandbox_combo_mode.setCurrentIndex(2)
                    elif p_mode == "full": self.sandbox_combo_mode.setCurrentIndex(1)
                    else: self.sandbox_combo_mode.setCurrentIndex(0)

                if hasattr(self, 'list_kw'): self.list_kw.clear(); self.list_kw.addItems(config_data.get("clean_keywords", []))
                if hasattr(self, 'list_ext'): self.list_ext.clear(); self.list_ext.addItems(config_data.get("clean_exts", []))
                self.preset_font_size = config_data.get("preset_font_size", 10)
                self.custom_rules = config_data.get("custom_rules", [])
            except Exception as e: self.log_msg(f"读取配置文件失败: {e}", "ERROR")
        else:
            self.apply_theme("light"); self.input_pt_url.setText("https://www.momentpt.top/"); self.input_img_upload_url.setText("https://img.momentpt.top/api/v1/upload"); self.input_img_token_url.setText("https://img.momentpt.top/api/v1/tokens")
            self.input_t_path.setText("./torrents"); self.input_s_path.setText("./seeding"); self.spin_delay.setValue(5); self.input_qb_url.setText("http://127.0.0.1:8080"); self.input_qb_user.setText("admin")
            self.chk_qb_add.setChecked(True); self.rb_simple.setChecked(True); self.preset_font_size = 10
            if hasattr(self, 'chk_reuse_existing'): self.chk_reuse_existing.setChecked(False)
            if hasattr(self, 'chk_proxy'): self.chk_proxy.setChecked(False)
            if hasattr(self, 'input_proxy'): self.input_proxy.setText("127.0.0.1:7897")
            self.custom_rules = []
            if hasattr(self, 'input_qb_category'): self.input_qb_category.setText("")
            if hasattr(self, 'input_qb_tags'): self.input_qb_tags.setText("")
            if hasattr(self, 'sandbox_combo_mode'): self.sandbox_combo_mode.setCurrentIndex(0)
            
        if hasattr(self, 'sandbox_load_rules'):
            self.sandbox_load_rules()

    def get_abs_path(self, path):
        path = path.strip()
        if not path: return self.base_dir
        if path.startswith('~'): path = os.path.expanduser(path)
        if os.path.isabs(path): return os.path.normpath(path)
        
        if getattr(sys, 'frozen', False) and sys.platform == 'darwin':
            return os.path.normpath(os.path.join(os.path.expanduser('~'), path))
            
        return os.path.normpath(os.path.join(self.base_dir, path))

    def browse_folder(self, target_line_edit):
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹", self.last_dir)
        if folder_path: self.last_dir = folder_path; target_line_edit.setText(folder_path)

    def get_hline(self): 
        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setStyleSheet("background-color: rgba(150, 150, 150, 100); max-height: 1px; margin: 8px 0;"); return line

    def create_hint_label(self, text, role="info"): 
        lbl = QLabel(text); lbl.setWordWrap(True); lbl.setContentsMargins(0, 0, 0, 0); self.hint_labels.append((lbl, role)); return lbl

    def refresh_hint_colors(self):
        d = self.current_theme == "dark"
        for l, r in self.hint_labels: l.setStyleSheet(f"color: {'#ff9500' if d and r=='warning' else '#0a84ff' if d and r=='primary' else '#ff3b30' if not d and r=='warning' else '#007aff' if not d and r=='primary' else '#8e8e93'}; font-size: 12px; background: transparent;")

    def get_parsed_name(self, f_name, amount_str, preset, parse_mode, override_rules=None):
        rules_to_use = override_rules if override_rules is not None else self.custom_rules
        raw_title = f_name
        
        for rule in rules_to_use:
            r_type = rule.get("type", "replace")
            search = rule.get("search", "")
            replace = rule.get("replace", "")
            if not search: continue
            try:
                if r_type == "replace":
                    raw_title = raw_title.replace(search, replace)
                elif r_type == "regex":
                    raw_title = re.sub(search, replace, raw_title)
            except Exception:
                pass

        year = ""
        d_match = re.search(r'((19\d{2}|20\d{2})[-.\s]?\d{2}[-.\s]?\d{2})', raw_title)
        y_match = re.search(r'(19\d{2}|20\d{2})', raw_title)
        if d_match: year = d_match.group(2)
        elif y_match: year = y_match.group(1)

        std_name = raw_title
        if parse_mode != "none":
            p_m = preset.get("model", "")
            p_p = preset.get("photographer", "")
            if parse_mode == "full":
                if p_m and p_m in raw_title: raw_title = raw_title.replace(p_m, "")
                if p_p and p_p in raw_title: raw_title = raw_title.replace(p_p, "")
                if d_match: raw_title = raw_title.replace(d_match.group(1), "")
                elif y_match: raw_title = raw_title.replace(y_match.group(1), "")
                raw_title = re.sub(r'[-\s_]+', ' ', raw_title).strip()
            
            parts = [f"『{raw_title}』" if raw_title else "", p_m, p_p, year, amount_str, "Moment"]
            std_name = "-".join([x for x in parts if x])
            
        # 防止Mac/Windows下含有特殊符号（如斜杠/）破坏Zip/种子生成的路径结构（两种解析模式都生效）
        std_name = sanitize_filename(std_name)
        return std_name, year

    def find_preset(self, name):
        return next((p for p in self.presets_data if isinstance(p, dict) and p.get("name") == name), {})

class PTUploaderFullGUI(PTUploaderBase):
    def init_all(self):
        self.init_directories()
        meipass = getattr(sys, '_MEIPASS', self.base_dir)
        icon_candidates = [
            os.path.join(self.base_dir, 'app_icon.ico'), os.path.join(self.base_dir, 'app_icon.icns'),
            os.path.join(meipass, 'app_icon.ico'), os.path.join(meipass, 'app_icon.icns'),
            os.path.join(self.base_dir, 'Contents', 'Resources', 'app_icon.icns'),
            os.path.join(os.path.dirname(sys.executable), 'app_icon.ico'),
            os.path.join(os.path.dirname(sys.executable), 'app_icon.icns'),
        ]
        icon_path = next((p for p in icon_candidates if os.path.exists(p)), None)
        if icon_path:
            QApplication.instance().setWindowIcon(QIcon(icon_path))
            self.setWindowIcon(QIcon(icon_path))
            
        self.load_presets()
        
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tab_batch = QWidget()
        self.tab_sandbox = QWidget()
        self.tab_cover = QWidget()
        self.tab_settings = QWidget()
        self.tab_log = QWidget()
        
        self.tabs.addTab(self.tab_batch, "⚡ 批量上传流水线")
        self.tabs.addTab(self.tab_sandbox, "🧪 名称解析沙盒")
        self.tabs.addTab(self.tab_cover, "🖼️ 封面拼图台")
        self.tabs.addTab(self.tab_settings, "⚙️ 偏好设置")
        self.tabs.addTab(self.tab_log, "🖥️ 运行日志监控")
        
        self.setup_log_tab()
        self.setup_batch_upload_tab()
        self.setup_sandbox_tab()
        self.setup_cover_tab()
        self.setup_settings_tab()
        self.load_config()
        self.ensure_data_dirs()
        self.log_msg(f"✅ GUI 界面渲染完成，大一统核心引擎已全面就绪！", "SUCCESS")

    def ensure_data_dirs(self):
        for le in (getattr(self, 'input_t_path', None), getattr(self, 'input_s_path', None)):
            if le is None: continue
            try:
                p = self.get_abs_path(le.text())
                os.makedirs(p, exist_ok=True)
                if not os.access(p, os.W_OK): self.log_msg(f"⚠️ 目录不可写，请更换: {p}", "WARNING")
            except Exception as e:
                self.log_msg(f"⚠️ 无法创建/访问目录: {getattr(le, 'text', lambda: '?')()} -> {e}", "ERROR")

    def setup_log_tab(self):
        layout = QVBoxLayout(self.tab_log); group_log = QGroupBox("🖥️ 实时运行日志"); v_log = QVBoxLayout(); self.log_view = QTextEdit(); self.log_view.setObjectName("LogView"); self.log_view.setReadOnly(True)
        h_tool = QHBoxLayout(); h_tool.addWidget(QLabel("📌 记录程序详细工作状态、接口返回值和异常报错。")); h_tool.addStretch()
        btn_open_dir = QPushButton("📂 打开日志文件夹"); btn_open_dir.clicked.connect(lambda: os.startfile(os.path.join(self.get_data_dir(), 'logs')) if sys.platform == 'win32' else subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', os.path.join(self.get_data_dir(), 'logs')]))
        btn_clear = QPushButton("🗑 清空当前面板"); btn_clear.setStyleSheet("background-color: #ff3b30; color: white; border: none;"); btn_clear.clicked.connect(self.log_view.clear)
        h_tool.addWidget(btn_open_dir); h_tool.addWidget(btn_clear); v_log.addLayout(h_tool); v_log.addWidget(self.log_view); group_log.setLayout(v_log); layout.addWidget(group_log)

    def update_table_cell(self, row, col, text, color_hex):
        item = self.table.item(row, col)
        if not item:
            item = QTableWidgetItem(text)
            self.table.setItem(row, col, item)
        else:
            item.setText(text)
        if color_hex:
            item.setForeground(QBrush(QColor(color_hex)))

    def setup_batch_upload_tab(self):
        batch_scroll = QScrollArea(); batch_scroll.setWidgetResizable(True); batch_scroll.setStyleSheet("QScrollArea { border: none; }")
        batch_page = QWidget(); layout = QVBoxLayout(batch_page)
        group_top = QGroupBox("第一步：选择发布预设与基础设定"); h_top = QHBoxLayout()
        self.preset_combo = QComboBox(); self.preset_combo.currentIndexChanged.connect(self.preset_changed); self.preset_combo.setMinimumWidth(240); self.preset_combo.setToolTip("选择一个“模板”，它决定了标题里的摄影/模特、简介、默认分类和标签。")
        h_top.addWidget(QLabel("发布预设:")); h_top.addWidget(self.preset_combo)
        btn_m = QPushButton("⚙ 管理预设"); btn_m.setToolTip("新增 / 编辑 / 删除预设模板。"); btn_m.clicked.connect(self.open_manage_presets); h_top.addWidget(btn_m)
        btn_r = QPushButton("刷新"); btn_r.setToolTip("重新读取预设列表。"); btn_r.clicked.connect(self.refresh_main_preset_combo); h_top.addWidget(btn_r); h_top.addStretch()
        self.cb_batch_anon = QCheckBox("匿名上传"); self.cb_batch_anon.setChecked(True); self.cb_batch_anon.setToolTip("发布时不显示发布者，推荐勾选。")
        self.cb_batch_zip = QCheckBox("打包为ZIP"); self.cb_batch_zip.setChecked(True); self.cb_batch_zip.setToolTip("把每个资源文件夹压成一个 ZIP 再制作种子；推荐勾选，方便做种和下载。")
        self.cb_batch_test = QCheckBox("仅测试(不发到PT)"); self.cb_batch_test.setToolTip("只演练整个流程、检查标题/分类/标签，不会真的发到 PT 站，也不会推送 qB。")
        h_top.addWidget(self.cb_batch_anon); h_top.addWidget(self.cb_batch_zip); h_top.addWidget(self.cb_batch_test)
        v_top = QVBoxLayout(); v_top.addLayout(h_top)
        v_top.addWidget(self.create_hint_label("💡 这里决定“默认模板”和基本选项：先在【发布预设】里选好模板；需要新模板就点【⚙ 管理预设】。下面灰框会显示当前预设的摄影/模特/分类/标签，方便你核对。", "primary"))
        self.preset_info_label = QTextEdit(); self.preset_info_label.setFixedHeight(50); self.preset_info_label.setReadOnly(True); self.preset_info_label.setToolTip("当前所选预设的详情预览。")
        v_top.addWidget(self.preset_info_label); group_top.setLayout(v_top); layout.addWidget(group_top, 0)

        group_mid = QGroupBox("第二步：添加资源文件夹并自动提取名称/数量"); v_mid = QVBoxLayout()
        v_mid.addWidget(self.create_hint_label("💡 操作顺序：【1.添加文件夹】把资源文件夹批量导入 → 【2.智能扫描提取】自动算出 P/V 数和最终标题。\n表格里任何一格都可以双击手动修改（比如标题、分类、标签）；改完会自动刷新。选错行就点【➖ 移除选中行】。", "primary"))
        h_toolbar = QHBoxLayout()
        b_add = QPushButton("📁 1.添加文件夹"); b_add.setStyleSheet("background:#34c759; color:white; border:none;"); b_add.setToolTip("可按住 Ctrl（Mac 为 Command）多选，一次导入多个资源文件夹。"); b_add.clicked.connect(self.batch_add_folder)
        b_scn = QPushButton("🔍 2.智能扫描提取"); b_scn.setStyleSheet("background:#007aff; color:white; border:none;"); b_scn.setToolTip("扫描每个文件夹里的图片/视频数量，并按当前预设生成最终种子标题。"); b_scn.clicked.connect(self.batch_scan_folders)
        b_rn = QPushButton("🔄 3.序列化重命名 (可选)"); b_rn.setStyleSheet("background:#ff9500; color:white; border:none;"); b_rn.setToolTip("把文件夹内的图片/视频重命名为 1.jpg、2.mp4…；不可逆，非必要别点。"); b_rn.clicked.connect(self.batch_rename_files)
        b_sandbox = QPushButton("🧪 4.名称解析沙盒(调试)"); b_sandbox.setStyleSheet("background:#c2185b; color:white; border:none;"); b_sandbox.setToolTip("想预览/调试标题解析规则时用，看效果、不会影响正式流程。"); b_sandbox.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        b_del = QPushButton("➖ 移除选中行"); b_del.setStyleSheet("color:#ff3b30;"); b_del.setToolTip("把表格里选中的行从待发布列表移除。"); b_del.clicked.connect(self.batch_remove_row)
        b_clr = QPushButton("🗑 清空列表"); b_clr.setStyleSheet("background:#ff3b30; color:white; border:none;"); b_clr.setToolTip("清空整个待发布列表。"); b_clr.clicked.connect(lambda: self.table.setRowCount(0))
        h_toolbar.addWidget(b_add); h_toolbar.addWidget(b_scn); h_toolbar.addWidget(b_rn); h_toolbar.addWidget(b_sandbox); h_toolbar.addWidget(b_del); h_toolbar.addStretch(); h_toolbar.addWidget(b_clr); v_mid.addLayout(h_toolbar)

        self.table = QTableWidget(0, 12); self.table.setMinimumHeight(90); self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setHorizontalHeaderLabels(["原始文件夹名", "最终种子名称", "应用预设", "锁定", "物理路径", "P/V数", "年份", "分类", "附加标签", "种子", "状态", "操作"])
        for _i, _tip in enumerate([
            "导入时的原始文件夹名（参考，不可改）",
            "发布用的最终标题，可双击修改",
            "这一行使用的预设模板",
            "勾选后，切换顶部全局预设不会覆盖本行",
            "资源在磁盘上的位置",
            "图片/视频数量，例如 52P、1V",
            "从名称里识别出的年份",
            "发布到 PT 站的分类板块",
            "除“官方/禁转”外额外附加的标签（可多选）",
            "种子是否已生成",
            "当前处理状态（成功/失败原因看这里）",
            "单独移除这一行",
        ]):
            item = self.table.horizontalHeaderItem(_i)
            if item: item.setToolTip(_tip)
        head = self.table.horizontalHeader(); head.setSectionResizeMode(QHeaderView.ResizeMode.Interactive); self.table.setColumnWidth(0, 100); head.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(2, 110); self.table.setColumnWidth(3, 40); self.table.setColumnWidth(4, 90); self.table.setColumnWidth(5, 70); self.table.setColumnWidth(6, 60); self.table.setColumnWidth(7, 75); self.table.setColumnWidth(8, 120); self.table.setColumnWidth(9, 75); self.table.setColumnWidth(10, 80); self.table.setColumnWidth(11, 50)
        self.table.cellChanged.connect(self.on_table_cell_changed); v_mid.addWidget(self.table); group_mid.setLayout(v_mid); layout.addWidget(group_mid, 1) 

        # ---------- 第三步：封面准备 / 打包 / 发布 ----------
        group_bot = QGroupBox("第三步：封面准备 ➜ 打包制种 ➜ 发布做种（新手可直接用底部【一键全自动】）"); v_bot = QVBoxLayout()

        # 3.1 封面准备
        v_bot.addWidget(QLabel("3.1 封面准备（可选；不设置也能发布，只是帖子没有封面图）"))
        h_cover = QHBoxLayout()
        b_auto_img = QPushButton("🖼️ 自动匹配本地封面"); b_auto_img.setToolTip("选择一个装了封面图的文件夹，程序会按资源名称自动找同名图片（支持 jpg / jpeg / png）。")
        b_auto_img.clicked.connect(self.batch_auto_match_thumbs)
        b_man_img = QPushButton("📌 为选中行指定封面"); b_man_img.setToolTip("先在上方表格里点选一行，再挑一张图片作为该资源的封面。")
        b_man_img.clicked.connect(self.batch_manual_thumb)
        b_jump_cover = QPushButton("🎨 去【封面拼图台】做四宫格封面"); b_jump_cover.setStyleSheet("background: #af52de; color: white;")
        b_jump_cover.setToolTip("把每个资源的多张图拼成一张精美的四宫格封面；做好后在封面台设置输出目录并保存。")
        b_jump_cover.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        self.chk_auto_cover = QCheckBox("全自动时，自动使用【封面拼图台】输出目录里的封面")
        self.chk_auto_cover.setChecked(True); self.chk_auto_cover.setStyleSheet("color: #007aff; font-weight: bold;")
        self.chk_auto_cover.setToolTip("勾选后，点【一键全自动】时会先去封面输出目录把拼好的封面抓过来用。")
        h_cover.addWidget(b_auto_img); h_cover.addWidget(b_man_img); h_cover.addWidget(b_jump_cover); h_cover.addWidget(self.chk_auto_cover); h_cover.addStretch()
        v_bot.addLayout(h_cover)
        v_bot.addWidget(self.create_hint_label("💡 可跳过：先去【封面拼图台】拼好封面，再点【自动匹配本地封面】，或勾选上一项让全自动去抓。", "primary"))

        # 3.2 分步执行
        v_bot.addWidget(QLabel("3.2 分步执行（只想单独重跑某一步时用；两步通常要按顺序做）"))
        h_exec2 = QHBoxLayout()
        self.btn_make = QPushButton("📦 第1步：打包并制作种子"); self.btn_make.setStyleSheet("background:#34c759; color:white; border:none; padding:7px 12px; border-radius:4px;")
        self.btn_make.setToolTip("把每个资源的文件夹压缩成 ZIP，并生成对应的 .torrent 种子文件（不做这一步就没法发布）。")
        self.btn_make.clicked.connect(lambda: self.start_worker('make'))
        self.btn_pub = QPushButton("🚀 第2步：推送到 PT 站并做种"); self.btn_pub.setStyleSheet("background:#ff9500; color:white; border:none; padding:7px 12px; border-radius:4px;")
        self.btn_pub.setToolTip("把上一步做好的种子发布到 PT 站，并推送到 qBittorrent 开始做种（需要先在偏好设置里填好 Cookie 和 qB）。")
        self.btn_pub.clicked.connect(lambda: self.start_worker('publish'))
        h_exec2.addWidget(self.btn_make); h_exec2.addWidget(self.btn_pub); h_exec2.addStretch()
        v_bot.addLayout(h_exec2)

        # 3.3 一键全自动 + 停止
        h_main_btn = QHBoxLayout()
        self.btn_auto = QPushButton("🚀 一键全自动打包发布（新手推荐）"); self.btn_auto.setStyleSheet("background: #007aff; color: white; font-size: 14px; padding: 10px 24px; border: none; border-radius: 5px;")
        self.btn_auto.setToolTip("自动依次完成：找封面 ➜ 打包制种 ➜ 上传图床 ➜ 发布 PT ➜ 推送 qB 做种。")
        self.btn_auto.clicked.connect(self.run_auto_publish)
        self.btn_stop = QPushButton("🛑 停止当前任务"); self.btn_stop.setStyleSheet("background: #ff3b30; color: white; padding: 10px 20px; border: none; border-radius: 5px;")
        self.btn_stop.setToolTip("中断正在进行的后台任务（建议等当前这一项处理完再点）。")
        self.btn_stop.setEnabled(False); self.btn_stop.clicked.connect(self.force_stop_worker)
        h_main_btn.addWidget(self.btn_auto, 3); h_main_btn.addWidget(self.btn_stop)
        v_bot.addLayout(h_main_btn)
        v_bot.addWidget(self.create_hint_label("💡 新手直接用【一键全自动】即可；只在想单独重做某一步时，才用上面的【3.2 分步执行】。", "primary"))

        self.batch_progress = QProgressBar(); self.batch_progress.setValue(0); v_bot.addWidget(self.batch_progress)

        h_log_header = QHBoxLayout(); h_log_header.addWidget(QLabel("📝 实时进度（这里会显示每一步的结果和报错）")); h_log_header.addStretch()
        self.batch_log = QTextEdit(); self.batch_log.setObjectName("BatchLogView"); self.batch_log.setMinimumHeight(70); self.batch_log.setFixedHeight(80); self.batch_log.setReadOnly(True)
        btn_clr_batch_log = QPushButton("🗑 清空"); btn_clr_batch_log.setStyleSheet("color:#ff3b30; background:transparent; border:none;"); btn_clr_batch_log.setCursor(Qt.CursorShape.PointingHandCursor); btn_clr_batch_log.clicked.connect(self.batch_log.clear)
        h_log_header.addWidget(btn_clr_batch_log); v_bot.addLayout(h_log_header); v_bot.addWidget(self.batch_log); group_bot.setLayout(v_bot); layout.addWidget(group_bot, 0)

        batch_scroll.setWidget(batch_page)
        batch_outer = QVBoxLayout(self.tab_batch); batch_outer.setContentsMargins(0, 0, 0, 0); batch_outer.addWidget(batch_scroll)

        self.refresh_main_preset_combo()

    def setup_sandbox_tab(self):
        layout = QVBoxLayout(self.tab_sandbox)
        
        lbl_info = QLabel(
            "<div style='line-height: 1.6; padding: 5px;'>"
            "<b>💡 名称解析引擎与沙盒测试说明：</b><br>"
            "&nbsp;&nbsp;1. <b>【简单提取】：</b> 保留原文件夹名称，仅追加提取出的数量和年份。<i>（例：原标题-2023-50P-Moment）</i><br>"
            "&nbsp;&nbsp;2. <b>【强效重组】：</b> 智能剔除原标题中的模特和年份防重复，并严格按照 <i>『主题』-模特-摄影师-年份-数量-Moment</i> 的标准格式重新组装。<br>"
            "&nbsp;&nbsp;3. <b>【沙盒规则】：</b> 您在下方添加的自定义处理规则，将<b>优先、且仅针对您的原始标题主体生效</b>，程序绝对不会误伤尾部自动生成的后缀（如 P数、年份 或 Moment 等标识）。"
            "</div>"
        )
        lbl_info.setWordWrap(True)
        self.hint_labels.append((lbl_info, "primary")) 
        layout.addWidget(lbl_info)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #c7c7cc; width: 2px; }")
        
        group_left = QGroupBox("🧠 自定义处理规则 (从上至下执行)")
        v_left = QVBoxLayout()
        h_left_top = QHBoxLayout()
        btn_add_rule = QPushButton("➕ 添加规则")
        btn_add_rule.setToolTip("添加一条“查找 ➜ 替换”规则，用来清洗标题里的多余文字（按从上到下的顺序执行）。")
        btn_add_rule.clicked.connect(self.sandbox_add_rule)
        btn_save_rule = QPushButton("💾 保存规则到配置")
        btn_save_rule.setStyleSheet("background-color: #34c759; color: white; border: none; padding: 6px 15px; border-radius: 4px;")
        btn_save_rule.clicked.connect(self.sandbox_save_rules)
        h_left_top.addStretch()
        h_left_top.addWidget(btn_add_rule)
        h_left_top.addWidget(btn_save_rule)
        v_left.addLayout(h_left_top)
        
        scroll_rules = QScrollArea()
        scroll_rules.setWidgetResizable(True)
        scroll_rules.setStyleSheet("border: none; background: transparent;")
        self.widget_rules = QWidget()
        self.layout_rules = QVBoxLayout(self.widget_rules)
        self.layout_rules.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_rules.setWidget(self.widget_rules)
        v_left.addWidget(scroll_rules)
        group_left.setLayout(v_left)
        
        group_right = QGroupBox("🔬 标题推演全景对照表")
        v_right = QVBoxLayout()
        h_right_top = QHBoxLayout()
        self.sandbox_combo_mode = QComboBox()
        self.sandbox_combo_mode.addItems(["模拟【简单提取】效果", "模拟【强效重组】效果", "模拟【禁用提取】效果"])
        self.sandbox_combo_mode.setToolTip("只改变下面预览用的解析方式，不会影响正式流程。")
        
        btn_run_test = QPushButton("▶️ 运行解析对照测试")
        btn_run_test.setStyleSheet("background-color: #007aff; color: white; padding: 6px 15px; border-radius: 4px; font-weight: bold; border: none;")
        btn_run_test.setToolTip("用上方列表里的资源跑一遍，看看每个资源最终会生成什么标题。")
        btn_run_test.clicked.connect(self.sandbox_run_test)
        
        btn_goto_settings = QPushButton("⚙️ 检查全局解析模式 (去设置页)")
        btn_goto_settings.setStyleSheet("background-color: #5856d6; color: white; padding: 6px 15px; border-radius: 4px; font-weight: bold; border: none;")
        btn_goto_settings.setToolTip("真正生效的解析模式在【偏好设置】里，这里只做预览。")
        btn_goto_settings.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        
        h_right_top.addWidget(self.sandbox_combo_mode)
        h_right_top.addWidget(btn_run_test)
        h_right_top.addStretch()
        h_right_top.addWidget(btn_goto_settings)
        
        v_right.addLayout(h_right_top)
        
        lbl_mode_hint = QLabel("⚠️ 注意：沙盒主要用于调试『自定义规则』，上方下拉框仅切换预览视图，实际流水线将严格按照【偏好设置】中的模式执行！")
        lbl_mode_hint.setStyleSheet("color: #ff3b30; font-size: 11px;")
        v_right.addWidget(lbl_mode_hint)
        
        self.sandbox_table = QTableWidget(0, 2)
        self.sandbox_table.setHorizontalHeaderLabels(["原始文件夹加载列", "最终组装输出预览列"])
        self.sandbox_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.sandbox_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.sandbox_table.setColumnWidth(0, 350)
        self.sandbox_table.verticalHeader().setDefaultSectionSize(30)
        v_right.addWidget(self.sandbox_table)
        
        group_right.setLayout(v_right)
        
        splitter.addWidget(group_left)
        splitter.addWidget(group_right)
        splitter.setSizes([320, 780])
        layout.addWidget(splitter, 1)

    def sandbox_add_rule(self, rule_data=None):
        if not isinstance(rule_data, dict): rule_data = None
        is_dark = (self.current_theme == "dark")
        rule_widget = RuleWidget(self.layout_rules, rule_data, is_dark)
        self.layout_rules.addWidget(rule_widget)

    def sandbox_load_rules(self):
        for i in reversed(range(self.layout_rules.count())):
            widget = self.layout_rules.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        for rule in self.custom_rules:
            self.sandbox_add_rule(rule)

    def sandbox_save_rules(self):
        new_rules = []
        for i in range(self.layout_rules.count()):
            widget = self.layout_rules.itemAt(i).widget()
            if isinstance(widget, RuleWidget):
                data = widget.get_data()
                if data["search"]: 
                    new_rules.append(data)
        
        self.custom_rules = new_rules
        self.save_config(silent=True)
        self.log_msg("💾 沙盒自定义解析规则已保存并写入", "SUCCESS")
        QMessageBox.information(self, "成功", "规则已保存并写入 config.json！")

    def sandbox_run_test(self):
        current_rules = []
        for i in range(self.layout_rules.count()):
            widget = self.layout_rules.itemAt(i).widget()
            if isinstance(widget, RuleWidget):
                current_rules.append(widget.get_data())
                
        mode_text = self.sandbox_combo_mode.currentText()
        if "简单提取" in mode_text: parse_mode = "simple"
        elif "强效重组" in mode_text: parse_mode = "full"
        else: parse_mode = "none"
        
        row_count = self.table.rowCount()
        if row_count == 0:
            QMessageBox.warning(self, "提示", "流水线列表为空，请先在【批量上传流水线】添加文件夹。")
            return
            
        self.sandbox_table.setRowCount(0)
        self.log_msg(f"🧪 沙盒运行了解析对照测试，当前推演模式: {mode_text}", "INFO")
        
        for r in range(row_count):
            raw_title = self.table.item(r, 0).text() if self.table.item(r, 0) else ""
            amount_str = self.table.item(r, 5).text() if self.table.item(r, 5) else ""
            
            preset_name = self.table.cellWidget(r, 2).currentText() if self.table.cellWidget(r, 2) else ""
            preset = self.find_preset(preset_name)
            
            std_name, _ = self.get_parsed_name(raw_title, amount_str, preset, parse_mode, current_rules)
            
            self.sandbox_table.insertRow(r)
            item_raw = QTableWidgetItem(raw_title)
            item_std = QTableWidgetItem(std_name)
            
            self.sandbox_table.setItem(r, 0, item_raw)
            self.sandbox_table.setItem(r, 1, item_std)

    def setup_cover_tab(self):
        layout = QVBoxLayout(self.tab_cover)
        g_paths = QGroupBox("① 封面输出目录（拼好的封面统一保存在这里）"); f_paths = QFormLayout()
        self.cover_save_dir = QLineEdit(); self.cover_save_dir.setPlaceholderText("点右侧【浏览】选择保存封面的文件夹…")
        self.cover_save_dir.setToolTip("封面会按“资源名.jpg”保存到这里；批量发布时按文件名自动匹配，所以建议用固定目录。")
        h_dir = QHBoxLayout(); h_dir.addWidget(self.cover_save_dir); btn_dir = QPushButton("浏览"); btn_dir.setToolTip("选择封面输出文件夹"); btn_dir.clicked.connect(lambda: self.browse_folder(self.cover_save_dir)); h_dir.addWidget(btn_dir)
        f_paths.addRow("封面输出目录:", h_dir); g_paths.setLayout(f_paths); layout.addWidget(g_paths, 0)
        
        h_main = QHBoxLayout()
        g_list = QGroupBox("② 待处理资源库（可多选批量操作）"); v_list = QVBoxLayout(); h_list_btns = QHBoxLayout()
        btn_add_f = QPushButton("📁 加载资源文件夹"); btn_add_f.setToolTip("把要拼封面的资源文件夹加进来（可一次多选）。"); btn_add_f.clicked.connect(self.cover_load_folders)
        btn_del_f = QPushButton("➖ 移除选中"); btn_del_f.setStyleSheet("color: #ff3b30;"); btn_del_f.setToolTip("从列表里移除选中的资源。"); btn_del_f.clicked.connect(self.cover_remove_selected_folder)
        btn_sel_all = QPushButton("☑️ 全选列表"); btn_sel_all.setToolTip("选中列表里的全部资源。"); btn_sel_all.clicked.connect(lambda: self.cover_list.selectAll())
        btn_clear_f = QPushButton("🗑 清空库"); btn_clear_f.setToolTip("清空整个列表。"); btn_clear_f.clicked.connect(lambda: self.cover_list.clear())
        h_list_btns.addWidget(btn_add_f); h_list_btns.addWidget(btn_sel_all); h_list_btns.addWidget(btn_del_f); h_list_btns.addWidget(btn_clear_f); v_list.addLayout(h_list_btns)
        lbl_hint_list = QLabel("💡 在列表里点一个资源，右边就会出现它的四宫格预览；按住 Shift 或 Ctrl(Command) 可多选。"); lbl_hint_list.setStyleSheet("color: #007aff; font-size: 11px;"); lbl_hint_list.setWordWrap(True); v_list.addWidget(lbl_hint_list)
        self.cover_list = QListWidget()
        self.cover_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection) 
        self.cover_list.itemSelectionChanged.connect(self.cover_item_selected); v_list.addWidget(self.cover_list); g_list.setLayout(v_list); h_main.addWidget(g_list, 1)
        
        g_prev = QGroupBox("③ 封面预览与微调工作台"); v_prev = QVBoxLayout()
        
        lbl_prev_hint = QLabel("💡 画布操作：\n1. 点住图片可拖动位置、滚轮（先点选图片）可缩放，拖太远松手会自动复位。\n2. 【双击图片】可替换那一格的图片。\n3. 满意后点下方【💾 保存并生成】，会按资源名保存到上面的输出目录。")
        lbl_prev_hint.setStyleSheet("color: #ff9500; font-size: 11px; font-weight: bold;"); v_prev.addWidget(lbl_prev_hint)
        
        self.lbl_preview = CollageView()
        self.lbl_preview.image_double_clicked.connect(self.cover_change_single_image_from_event)
        self.lbl_preview.image_swapped.connect(self.cover_on_image_swapped)
        v_prev.addWidget(self.lbl_preview, 1)
        
        self.cover_progress = QProgressBar(); self.cover_progress.setValue(0); self.cover_progress.setFixedHeight(12); v_prev.addWidget(self.cover_progress)
        self.cover_log = QTextEdit(); self.cover_log.setReadOnly(True); self.cover_log.setFixedHeight(60); self.cover_log.setStyleSheet("background-color: #1e1e1e; color: #34c759; font-family: Consolas; font-size: 11px;"); v_prev.addWidget(self.cover_log)
        
        h_actions1 = QHBoxLayout()
        btn_rand = QPushButton("🎲 随机换一批（对选中的项）")
        btn_rand.setStyleSheet("background: #007aff; color: white; padding: 8px; border-radius: 5px; font-weight: bold; border: none;")
        btn_rand.setToolTip("从每个选中资源里重新随机挑 4 张图放进四宫格。")
        btn_rand.clicked.connect(self.cover_gen_random_selected)
        
        btn_save_single = QPushButton("💾 保存并生成封面（对选中的项）")
        btn_save_single.setStyleSheet("background: #ff9500; color: white; padding: 8px; border-radius: 5px; font-weight: bold; border: none;")
        btn_save_single.setToolTip("把选中的资源逐个渲染并保存成“资源名.jpg”到输出目录。")
        btn_save_single.clicked.connect(self.cover_save_selected)
        
        h_actions1.addWidget(btn_rand); h_actions1.addWidget(btn_save_single); v_prev.addLayout(h_actions1)
        g_prev.setLayout(v_prev); h_main.addWidget(g_prev, 2); layout.addLayout(h_main, 1)

    def setup_settings_tab(self):
        sa = QScrollArea(); sa.setWidgetResizable(True); mw = QWidget(); layout = QVBoxLayout(mw); layout.setSpacing(16)
        gb_b = QGroupBox("📌 基础路径设置"); fb = QFormLayout(); fb.setSpacing(14)
        self.combo_theme = QComboBox(); self.combo_theme.addItems(["明亮白昼模式", "夜间护眼模式"]); self.combo_theme.currentIndexChanged.connect(self.theme_changed); fb.addRow("渲染主题:", self.combo_theme)
        self.input_t_path = QLineEdit(); self.input_t_path.setPlaceholderText("建议填 ./torrents"); self.input_s_path = QLineEdit(); self.input_s_path.setPlaceholderText("建议填 ./seeding")
        h1 = QHBoxLayout(); h1.addWidget(self.input_t_path); b1 = QPushButton("浏览"); b1.clicked.connect(lambda: self.browse_folder(self.input_t_path)); h1.addWidget(b1)
        h2 = QHBoxLayout(); h2.addWidget(self.input_s_path); b2 = QPushButton("浏览"); b2.clicked.connect(lambda: self.browse_folder(self.input_s_path)); h2.addWidget(b2)
        fb.addRow("官方种子存放位置:", h1); fb.addRow("做种文件位置:", h2); fb.addRow("", self.create_hint_label("💡 说明：为了防乱，从 PT 站下载回来的带个人 Passkey 的官方种子会保存在【种子存放位置】下的【PT_Official】子文件夹内。\n而本地打包后自己生成的原始种子会放入该路径下的【Local_Made】子文件夹内。", "primary")); gb_b.setLayout(fb); layout.addWidget(gb_b)
        gn = QGroupBox("🌐 PT站点与图床配置"); fn = QFormLayout(); fn.setSpacing(14)
        self.input_pt_url = QLineEdit(); self.input_cookie = QLineEdit(); self.input_api_key = QLineEdit()
        fn.addRow("PT站域名:", self.input_pt_url); fn.addRow("账号 Cookie:", self.input_cookie); fn.addRow("API Key (选填):", self.input_api_key)
        b_pt = QPushButton("测试能否连通 PT 站"); b_pt.setStyleSheet("background-color: #007aff; color: white; border: none;"); b_pt.clicked.connect(self.test_pt_connection); fn.addRow("", b_pt)
        fn.addRow(self.get_hline())
        
        self.input_img_upload_url = QLineEdit(); self.input_img_email = QLineEdit(); self.input_img_pwd = QLineEdit(echoMode=QLineEdit.EchoMode.Password); self.input_img_token = QLineEdit(echoMode=QLineEdit.EchoMode.Password); self.input_img_token_url = QLineEdit()
        fn.addRow("图床上传API:", self.input_img_upload_url); fn.addRow("验证 Token:", self.input_img_token); fn.addRow("获取 Token API:", self.input_img_token_url)
        fn.addRow("图床邮箱:", self.input_img_email); fn.addRow("图床密码:", self.input_img_pwd)
        
        # 图床测试与Token获取区
        b_gt = QPushButton("向图床申请获取 Token"); b_gt.setStyleSheet("background-color: #34c759; color: white; border: none;"); b_gt.clicked.connect(self.get_image_token)
        b_test_img = QPushButton("测试图床连通性"); b_test_img.setStyleSheet("background-color: #007aff; color: white; border: none;"); b_test_img.clicked.connect(self.test_image_host_connection)
        h_img_btns = QHBoxLayout(); h_img_btns.addWidget(b_gt); h_img_btns.addWidget(b_test_img); fn.addRow("", h_img_btns)
        
        # 增加上传重试控制控件
        hr2 = QHBoxLayout(); hr2.addWidget(QLabel("图床上传失败时重试次数:")); self.spin_img_retry = QSpinBox(); self.spin_img_retry.setRange(1, 10); self.spin_img_retry.setValue(5); hr2.addWidget(self.spin_img_retry); hr2.addWidget(QLabel("次 (默认5次)")); hr2.addStretch(); fn.addRow("图床容错机制:", hr2)
        
        hr = QHBoxLayout(); hr.addWidget(QLabel("自动发种时，两个种子间隔时间:")); self.spin_delay = QSpinBox(); self.spin_delay.setMaximum(9999); self.spin_delay.setValue(5); hr.addWidget(self.spin_delay); hr.addWidget(QLabel("秒 (默认5秒，为0时不限制)")); hr.addStretch(); fn.addRow("发种限流保护:", hr)
        hp = QHBoxLayout(); self.chk_proxy = QCheckBox("启用网络代理"); self.chk_proxy.setChecked(False); self.chk_proxy.setToolTip("使用 VPN / 代理（如 Clash、v2ray）时勾选，否则 PT 站/图床请求可能失败。默认关闭。")
        self.input_proxy = QLineEdit(); self.input_proxy.setText("127.0.0.1:7897"); self.input_proxy.setPlaceholderText("例如 127.0.0.1:7897")
        hp.addWidget(self.chk_proxy); hp.addWidget(QLabel("代理地址:")); hp.addWidget(self.input_proxy); hp.addStretch(); fn.addRow("网络代理:", hp)
        gn.setLayout(fn); layout.addWidget(gn)
        ga = QGroupBox("⚙️ 防误抓拦截规则与自动化配置"); fa = QFormLayout(); fa.setSpacing(14)
        
        self.input_qb_url = QLineEdit(); self.input_qb_user = QLineEdit(); self.input_qb_pwd = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        self.input_qb_category = QLineEdit(); self.input_qb_category.setPlaceholderText("选填，例如：PT")
        self.input_qb_tags = QLineEdit(); self.input_qb_tags.setPlaceholderText("选填，多个标签请用英文逗号分隔")
        self.chk_qb_add = QCheckBox("将种子自动推送到 qBittorrent 并强制开启做种")
        self.chk_reuse_existing = QCheckBox("复用已存在的 ZIP/种子（内容未变时跳过重新生成，提速；默认关闭）")
        self.chk_reuse_existing.setToolTip("勾选后：若做种目录里已有同名 ZIP，且种子目录里已有同名 .torrent，则直接复用，不重新打包/制种。\n注意：源文件夹内容变化后请取消勾选，或手动删除旧文件，否则会用到过期的种子。")
        
        fa.addRow("qB 端口地址:", self.input_qb_url); fa.addRow("qB 账号:", self.input_qb_user); fa.addRow("qB 密码:", self.input_qb_pwd)
        fa.addRow("qB 下载分类:", self.input_qb_category); fa.addRow("qB 下载标签:", self.input_qb_tags)
        fa.addRow("", self.chk_qb_add)
        fa.addRow("", self.chk_reuse_existing)
        
        b_qb = QPushButton("测试连接 qBittorrent"); b_qb.setStyleSheet("background-color: #007aff; color: white; border: none;"); b_qb.clicked.connect(self.test_qb_connection); fa.addRow("", b_qb)
        fa.addRow(self.get_hline())
        pl = QVBoxLayout(); self.btn_group_parse = QButtonGroup(); self.rb_none = QRadioButton("禁用提取"); self.rb_simple = QRadioButton("简单提取"); self.rb_full = QRadioButton("强效重组"); self.btn_group_parse.addButton(self.rb_none); self.btn_group_parse.addButton(self.rb_simple); self.btn_group_parse.addButton(self.rb_full)
        
        self.rb_none.toggled.connect(lambda checked: self.sandbox_combo_mode.setCurrentIndex(2) if checked and hasattr(self, 'sandbox_combo_mode') else None)
        self.rb_simple.toggled.connect(lambda checked: self.sandbox_combo_mode.setCurrentIndex(0) if checked and hasattr(self, 'sandbox_combo_mode') else None)
        self.rb_full.toggled.connect(lambda checked: self.sandbox_combo_mode.setCurrentIndex(1) if checked and hasattr(self, 'sandbox_combo_mode') else None)
        
        pl.addWidget(self.rb_none); pl.addWidget(self.create_hint_label("💡 禁用提取：直接使用资源文件夹的名称作为种子标题，不做任何拼装。\n【适用场景】提前已经按标准修改好文件夹名称。", "info"))
        pl.addWidget(self.rb_simple); pl.addWidget(self.create_hint_label("💡 简单提取 (推荐)：将文件夹完整名称作为『主题』，然后自动补充年份和P数，其他缺失项用预设补齐。\n【举例】文件夹叫：秀人网写真 ➔ 『秀人网写真』-预设模特-预设摄影师-63P-Moment", "info"))
        pl.addWidget(self.rb_full); pl.addWidget(self.create_hint_label("💡 强效重组：根据文件夹的名称来判断，有和预设一样的摄影师/模特，需去掉不在主题里面显示；文件夹名称有疑似日期数字的，需提取年份出来回填，同样也不在主题里面显示。\n例1：MintYe薄荷叶 Vol.004 何梦兮Stacy ➔ 『MintYe薄荷叶 Vol.004』-预设补齐\n例2：MintYe薄荷叶 2021.02.28 Vol.004 何梦兮Stacy ➔ 『MintYe薄荷叶 Vol.004』-预设补齐-2021-63P-Moment", "info")); fa.addRow("名称解析模式:", pl)
        fa.addRow(self.get_hline())
        lc = QGridLayout(); self.input_kw = QLineEdit(); self.input_kw.setPlaceholderText("在此打字，按回车添加..."); self.input_kw.returnPressed.connect(lambda: self.add_cleanup_item(self.input_kw, self.list_kw)); self.input_ext = QLineEdit(); self.input_ext.setPlaceholderText("在此打字，按回车添加..."); self.input_ext.returnPressed.connect(lambda: self.add_cleanup_item(self.input_ext, self.list_ext))
        self.list_kw = QListWidget(); self.list_kw.setViewMode(QListWidget.ViewMode(1)); self.list_kw.setResizeMode(QListWidget.ResizeMode(1)); self.list_kw.setSpacing(4); self.list_ext = QListWidget(); self.list_ext.setViewMode(QListWidget.ViewMode(1)); self.list_ext.setResizeMode(QListWidget.ResizeMode(1)); self.list_ext.setSpacing(4)
        b_dk = QPushButton("删除选中"); b_dk.setStyleSheet("background:#ff3b30; color:white; border:none; padding:4px;"); b_dk.clicked.connect(lambda: self.del_cleanup_item(self.list_kw)); b_ck = QPushButton("全部清空"); b_ck.clicked.connect(lambda: self.clear_all_cleanup_items(self.list_kw))
        b_de = QPushButton("删除选中"); b_de.setStyleSheet("background:#ff3b30; color:white; border:none; padding:4px;"); b_de.clicked.connect(lambda: self.del_cleanup_item(self.list_ext)); b_ce = QPushButton("全部清空"); b_ce.clicked.connect(lambda: self.clear_all_cleanup_items(self.list_ext))
        lc.addWidget(QLabel("包含以下文字则删除:"), 0, 0); lc.addWidget(self.input_kw, 0, 1, 1, 2); lc.addWidget(QLabel("属于以下后缀则删除:"), 0, 3); lc.addWidget(self.input_ext, 0, 4, 1, 2); lc.addWidget(self.list_kw, 1, 0, 1, 3); lc.addWidget(self.list_ext, 1, 3, 1, 3)
        hk = QHBoxLayout(); hk.addWidget(b_dk); hk.addWidget(b_ck); hk.addStretch(); he = QHBoxLayout(); he.addWidget(b_de); he.addWidget(b_ce); he.addStretch()
        lc.addLayout(hk, 2, 0, 1, 3); lc.addLayout(he, 2, 3, 1, 3); fa.addRow("广告文件拦截器:", lc)
        lbl_ad = self.create_hint_label("💡 操作指南：在上方输入框内输入你想拦截的词汇或后缀名（例如：.url、.txt、网址、赌场），然后按键盘上的【回车键 (Enter)】，即可将其加入拦截库中。", "primary"); fa.addRow("", lbl_ad)
        ga.setLayout(fa); layout.addWidget(ga)
        hb = QHBoxLayout(); br = QPushButton("取消更改，恢复上次保存配置"); br.setStyleSheet("background:#8e8e93; color:white; padding:12px; border:none;"); br.clicked.connect(self.load_config); bs = QPushButton("💾 保存偏好设置"); bs.setStyleSheet("background:#007aff; color:white; font-size:14px; padding:12px; border:none;"); bs.clicked.connect(self.save_config); hb.addWidget(br); hb.addWidget(bs); layout.addLayout(hb)
        sa.setWidget(mw); lyt = QVBoxLayout(self.tab_settings); lyt.setContentsMargins(0,0,0,0); lyt.addWidget(sa)

    def add_cleanup_item(self, line_edit, list_widget):
        txt = line_edit.text().strip()
        if txt and not list_widget.findItems(txt, Qt.MatchFlag.MatchExactly): list_widget.addItem(txt); line_edit.clear()

    def del_cleanup_item(self, list_widget):
        for item in list_widget.selectedItems(): list_widget.takeItem(list_widget.row(item))

    def clear_all_cleanup_items(self, list_widget): list_widget.clear()

    def batch_remove_row(self):
        sel = self.table.selectedRanges()
        if not sel: return QMessageBox.warning(self, "提示", "请先在下方表格中选中要移除的行。")
        for r in reversed(range(sel[0].topRow(), sel[0].bottomRow() + 1)): self.table.removeRow(r)
        self.log_msg("➖ 已从流水线移除选中的任务行", "INFO")

    def batch_rename_files(self):
        if self.table.rowCount() == 0: return QMessageBox.warning(self, "提示", "请先点击【添加文件夹】导入需要处理的内容。")
        reply = QMessageBox.question(self, "去广告重命名", "此操作会将目标文件夹内的图片和视频重命名为纯数字（1.jpg 等），并且操作不可逆转！是否继续？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
        exts = ('.jpg', '.jpeg', '.png', '.mp4', '.mkv', '.avi', '.mov', '.ts'); renamed_total = 0; self.log_msg("开始执行序列化去广告重命名...", "INFO")
        for row in range(self.table.rowCount()):
            f_item = self.table.item(row, 4) 
            if not f_item or not os.path.exists(f_item.text()): continue
            target_files = sorted([os.path.join(root, file) for root, _, files in os.walk(f_item.text()) for file in files if file.lower().endswith(exts)]); temp_files = []
            for fp in target_files: temp_name = os.path.join(os.path.dirname(fp), f"temp_{uuid.uuid4().hex}{os.path.splitext(fp)[1]}"); os.rename(fp, temp_name); temp_files.append(temp_name)
            for i, tp in enumerate(temp_files): os.rename(tp, os.path.join(os.path.dirname(tp), f"{i+1}{os.path.splitext(tp)[1]}")); renamed_total += 1
        self.log_msg(f"🔄 序列化重命名执行完毕，共处理 {renamed_total} 个文件", "SUCCESS"); QMessageBox.information(self, "完成", f"重命名完毕，共处理了 {renamed_total} 个文件。")

    def open_manage_presets(self): dialog = ManagePresetsDialog(self); dialog.setStyleSheet(self.styleSheet()); dialog.exec()

    def refresh_main_preset_combo(self):
        cur = self.preset_combo.currentText(); self.preset_combo.blockSignals(True); self.preset_combo.clear(); self.preset_combo.addItem("请选择预设模板...")
        for p in self.presets_data:
            pname = p.get("name") if isinstance(p, dict) else None
            if not pname: self.log_msg("⚠️ 跳过缺少名称的预设条目", "WARNING"); continue
            self.preset_combo.addItem(pname)
        idx = self.preset_combo.findText(cur)
        if idx >= 0: self.preset_combo.setCurrentIndex(idx)
        else: self.preset_combo.setCurrentIndex(0)
        self.preset_combo.blockSignals(False)
        
        for row in range(self.table.rowCount()):
            row_combo = self.table.cellWidget(row, 2)
            if row_combo:
                row_cur = row_combo.currentText(); row_combo.blockSignals(True); row_combo.clear(); row_combo.addItem("无预设")
                for p in self.presets_data:
                    pname = p.get("name") if isinstance(p, dict) else None
                    if not pname: continue
                    row_combo.addItem(pname)
                row_idx = row_combo.findText(row_cur)
                if row_idx >= 0: row_combo.setCurrentIndex(row_idx)
                row_combo.blockSignals(False)
                
        self.preset_changed()

    def preset_changed(self):
        p_name = self.preset_combo.currentText()
        preset = self.find_preset(p_name)
        if preset:
            tags_str = ", ".join(preset.get("tags", []))
            info_text = (f"📸 摄影师：{preset.get('photographer', '未配置')}   |   👤 主角/模特：{preset.get('model', '未配置')}\n🎯 默认分类：{preset.get('category', '默认')}   |   🏷️ 附带标签：{tags_str}\n📝 简介内容：{preset.get('intro', '无')}")
            self.preset_info_label.setText(info_text)
        if p_name == "请选择预设模板...": self.preset_info_label.setText("💡 请选择一个全局默认预设，作为后续新增资源的初始配置。")

        for row in range(self.table.rowCount()):
            is_locked = False
            w_lock = self.table.cellWidget(row, 3)
            if w_lock:
                chk = w_lock.findChild(QCheckBox)
                if chk and chk.isChecked(): is_locked = True
            
            row_combo = self.table.cellWidget(row, 2)
            if not is_locked and p_name != "请选择预设模板..." and row_combo:
                if row_combo.currentText() != p_name: row_combo.setCurrentText(p_name)
                else: self.on_row_preset_changed(row)
            else:
                self.on_row_preset_changed(row)

    def batch_add_folder(self):
        dialog = QFileDialog(self, "选择存放作品的多个文件夹 (Win按Ctrl / Mac按Command 多选)", self.last_dir); dialog.setFileMode(QFileDialog.FileMode.Directory)
        
        # [修复] 释放 macOS 原生弹窗，解决因为 TCC 权限被锁导致看不到文件夹的问题
        if sys.platform != 'darwin': 
            dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
            
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        tree = dialog.findChild(QTreeView)
        if tree: tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_folders = dialog.selectedFiles()
            if selected_folders: 
                self.last_dir = os.path.dirname(selected_folders[0])
                self.log_msg(f"📁 批量导入了 {len(selected_folders)} 个资源文件夹到流水线", "INFO")
            for path in selected_folders: self.add_single_folder_to_table(os.path.abspath(path))

    def add_single_folder_to_table(self, folder_path):
        row = self.table.rowCount(); self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(os.path.basename(folder_path))); self.table.setItem(row, 1, QTableWidgetItem("（等待扫描中...）"))
        combo_preset = QComboBox(); combo_preset.addItem("无预设")
        for p in self.presets_data:
            pname = p.get("name") if isinstance(p, dict) else None
            if not pname: self.log_msg("⚠️ 跳过缺少名称的预设条目", "WARNING"); continue
            combo_preset.addItem(pname)
        global_preset = self.preset_combo.currentText()
        if global_preset != "请选择预设模板...": combo_preset.setCurrentText(global_preset)
        combo_preset.currentIndexChanged.connect(lambda idx, r=row: self.on_row_preset_changed(r)); self.table.setCellWidget(row, 2, combo_preset)
        w_lock = QWidget(); l_lock = QHBoxLayout(w_lock); l_lock.setContentsMargins(0, 0, 0, 0); chk_lock = QCheckBox(); chk_lock.setToolTip("锁定此行预设，防止被顶部的全局预设覆盖"); l_lock.addWidget(chk_lock, alignment=Qt.AlignmentFlag.AlignCenter); self.table.setCellWidget(row, 3, w_lock)
        self.table.setItem(row, 4, QTableWidgetItem(folder_path)); self.table.setItem(row, 5, QTableWidgetItem("未知")); self.table.setItem(row, 6, QTableWidgetItem("未知"))
        combo_cat = QComboBox(); combo_cat.addItems(SITE_CATEGORIES); self.table.setCellWidget(row, 7, combo_cat)
        combo_tags = CheckableComboBox(); combo_tags.set_items(GLOBAL_TAGS); self.table.setCellWidget(row, 8, combo_tags)
        self.table.setItem(row, 9, QTableWidgetItem("未制作")); self.table.setItem(row, 10, QTableWidgetItem("待处理"))
        btn_del = QPushButton("移除"); btn_del.setStyleSheet("background-color: #ff3b30; color: white; border: none; padding: 2px 4px; border-radius: 4px;"); btn_del.clicked.connect(self.remove_table_row); self.table.setCellWidget(row, 11, btn_del)

    def remove_table_row(self):
        btn = self.sender()
        if btn:
            idx = self.table.indexAt(btn.pos())
            if idx.isValid(): self.table.removeRow(idx.row())

    def on_row_preset_changed(self, row):
        self.table.blockSignals(True)
        try:
            preset_name = self.table.cellWidget(row, 2).currentText() if self.table.cellWidget(row, 2) else ""; preset = self.find_preset(preset_name)
            if cw := self.table.cellWidget(row, 7): cw.setCurrentText(preset.get("category", "请选择分类..."))
            if tw := self.table.cellWidget(row, 8): tw.set_items(GLOBAL_TAGS, preset.get("tags", []))
        finally: self.table.blockSignals(False)
        self.on_table_cell_changed(row, 0)

    def on_table_cell_changed(self, row, col):
        if col in [0, 5]:
            self.table.blockSignals(True)
            try:
                preset_name = self.table.cellWidget(row, 2).currentText() if self.table.cellWidget(row, 2) else ""
                preset = self.find_preset(preset_name)
                f_name = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
                amount = self.table.item(row, 5).text() if self.table.item(row, 5) else ""
                
                parse_mode = "simple"
                if self.rb_none.isChecked(): parse_mode = "none"
                elif self.rb_full.isChecked(): parse_mode = "full"
                
                std_name, _ = self.get_parsed_name(f_name, amount, preset, parse_mode)
                
                self.table.setItem(row, 1, QTableWidgetItem(std_name))
            finally: self.table.blockSignals(False) 

    def batch_scan_folders(self):
        kws = [self.list_kw.item(i).text().lower() for i in range(self.list_kw.count())]; exts = [self.list_ext.item(i).text().lower() for i in range(self.list_ext.count())]
        total_cleaned = 0; self.batch_progress.setValue(0); parse_mode = "simple"
        if self.rb_none.isChecked(): parse_mode = "none"
        elif self.rb_full.isChecked(): parse_mode = "full"
        self.log_msg(f"开始智能扫描提取 (采用提取模式: {parse_mode})", "INFO"); self.table.blockSignals(True)
        global_preset = self.preset_combo.currentText()
        try:
            for row in range(self.table.rowCount()):
                folder_item = self.table.item(row, 4)
                if not folder_item:
                    self.log_msg(f"⚠️ 第 {row+1} 行缺少路径数据，已跳过", "WARNING")
                    self.table.setItem(row, 10, QTableWidgetItem("❌ 无路径"))
                    continue
                f_path = folder_item.text(); f_name = os.path.basename(f_path); QApplication.processEvents()
                if not os.path.isdir(f_path):
                    self.log_msg(f"⚠️ 路径已失效，跳过: {f_path}", "WARNING")
                    status_item = QTableWidgetItem("❌ 路径失效"); status_item.setForeground(QBrush(QColor("#ff3b30")))
                    self.table.setItem(row, 10, status_item)
                    continue
                is_locked = False; w_lock = self.table.cellWidget(row, 3)
                if w_lock:
                    chk = w_lock.findChild(QCheckBox)
                    if chk and chk.isChecked(): is_locked = True
                row_combo = self.table.cellWidget(row, 2)
                if row_combo and global_preset != "请选择预设模板..." and not is_locked: row_combo.setCurrentText(global_preset)
                preset_name = self.table.cellWidget(row, 2).currentText() if self.table.cellWidget(row, 2) else ""; preset = self.find_preset(preset_name)
                deleted_paths = set()
                if kws or exts:
                    try:
                        for root, _, files in os.walk(f_path):
                            for file in files:
                                lf = file.lower()
                                if any(lf.endswith(ext) for ext in exts) or any(kw in lf for kw in kws):
                                    full_path = os.path.join(root, file)
                                    try: os.remove(full_path); deleted_paths.add(os.path.normcase(full_path))
                                    except Exception as e: self.log_msg(f"删除文件失败 {file}: {e}", "ERROR"); continue
                                    total_cleaned += 1; self.log_msg(f"🛡 触发防拦截规则，已删除文件: {file}", "WARNING"); QApplication.processEvents()
                    except Exception as e: self.log_msg(f"清理文件时报错: {e}", "ERROR")
                img_c = 0; vid_c = 0
                for root, _, files in os.walk(f_path):
                    for file in files:
                        if os.path.normcase(os.path.join(root, file)) in deleted_paths: continue
                        lf = file.lower()
                        if lf.endswith(('.jpg', '.jpeg', '.png')): img_c += 1
                        elif lf.endswith(('.mp4', '.mkv', '.avi', '.mov', '.ts')): vid_c += 1
                amount_parts = []
                if img_c > 0: amount_parts.append(f"{img_c}P")
                if vid_c > 0: amount_parts.append(f"{vid_c}V")
                amount_str = "".join(amount_parts); self.table.setItem(row, 5, QTableWidgetItem(amount_str))
                std_name, year = self.get_parsed_name(f_name, amount_str, preset, parse_mode)
                self.table.setItem(row, 6, QTableWidgetItem(year))
                self.table.setItem(row, 1, QTableWidgetItem(std_name)); self.log_msg(f" -> 提取并组装名称: {std_name}")
                if cw := self.table.cellWidget(row, 7):
                    if cw.currentText() == "请选择分类...": cw.setCurrentText(preset.get("category", "请选择分类..."))
                if tw := self.table.cellWidget(row, 8): tw.set_items(GLOBAL_TAGS, preset.get("tags", []))
                self.table.setItem(row, 10, QTableWidgetItem("✅ 参数校验完毕")); self.batch_progress.setValue(int(((row + 1) / self.table.rowCount()) * 100))
        finally:
            self.table.blockSignals(False)
        if total_cleaned > 0: self.log_msg(f"扫描完毕，共计删除 {total_cleaned} 个违规广告文件。", "SUCCESS"); QMessageBox.information(self, "防误抓提示", f"拦截规则生效，共清理了 {total_cleaned} 个可能会引发站内封号的文件。")

    def log_cover(self, msg, level="INFO"):
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        self.cover_log.append(f"{time_str} | {msg}")
        self.cover_log.verticalScrollBar().setValue(self.cover_log.verticalScrollBar().maximum())
        QApplication.processEvents()
        self.log_msg(f"[封面拼图] {msg}", level)

    def _assign_random_images(self, folder_path):
        all_imgs = []
        for root, _, files in os.walk(folder_path):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png')): all_imgs.append(os.path.join(root, f))
        if not all_imgs: return []
        import random
        if len(all_imgs) >= 4: selected = random.sample(all_imgs, 4)
        else:
            selected = list(all_imgs)
            while len(selected) < 4: selected.append(selected[0] if selected else "")
        self.cover_assignments[folder_path] = selected
        return selected

    def cover_load_folders(self):
        dialog = QFileDialog(self, "选择存放作品的多个文件夹", self.last_dir); dialog.setFileMode(QFileDialog.FileMode.Directory)
        
        # [修复] 释放 macOS 原生弹窗
        if sys.platform != 'darwin': 
            dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
            
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        tree = dialog.findChild(QTreeView)
        if tree: tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_folders = dialog.selectedFiles()
            if selected_folders: 
                self.last_dir = os.path.dirname(selected_folders[0])
                self.log_msg(f"📁 封面拼图台已加载 {len(selected_folders)} 个资源文件夹", "INFO")
            for path in selected_folders:
                path = os.path.abspath(path)
                if not self.cover_list.findItems(path, Qt.MatchFlag.MatchExactly): self.cover_list.addItem(path)

    def cover_remove_selected_folder(self):
        for item in self.cover_list.selectedItems(): 
            if getattr(self, 'current_preview_folder', None) == item.text():
                self.current_preview_folder = None
                self.lbl_preview.clear_images()
            
            if item.text() in self.cover_states: del self.cover_states[item.text()]
            if item.text() in self.cover_assignments: del self.cover_assignments[item.text()]
            
            self.cover_list.takeItem(self.cover_list.row(item))

    def cover_item_selected(self):
        sel = self.cover_list.selectedItems()
        if not sel: return
        
        current_item = self.cover_list.currentItem()
        if not current_item or current_item not in sel:
            current_item = sel[0]
            
        folder_path = current_item.text()
        
        if getattr(self, 'current_preview_folder', None) == folder_path:
            return
            
        prev_folder = getattr(self, 'current_preview_folder', None)
        if prev_folder:
            self.cover_states[prev_folder] = self.lbl_preview.get_state()
            self.cover_assignments[prev_folder] = self.lbl_preview.current_paths.copy()
            
        self.current_preview_folder = folder_path
        
        if folder_path in self.cover_states:
            self.lbl_preview.load_state(self.cover_states[folder_path])
        else:
            if folder_path in self.cover_assignments:
                paths = self.cover_assignments[folder_path]
            else:
                paths = self._assign_random_images(folder_path)
                
            if paths: 
                self.lbl_preview.load_images(paths)
                self.cover_states[folder_path] = self.lbl_preview.get_state()
            else: 
                self.lbl_preview.clear_images()
                self.log_cover("❌ 此文件夹内无图片", "WARNING")

    def cover_change_single_image_from_event(self, idx, current_path):
        folder = os.path.dirname(current_path) if current_path and os.path.exists(current_path) else self.last_dir
        path, _ = QFileDialog.getOpenFileName(self, "选择替换图片", folder, "Images (*.jpg *.jpeg *.png)")
        if path:
            self.last_dir = os.path.dirname(path)
            self.lbl_preview.replace_image(idx, path)
            
            if getattr(self, 'current_preview_folder', None):
                self.cover_assignments[self.current_preview_folder] = self.lbl_preview.current_paths.copy()
                
            self.log_cover(f"已成功替换第 {idx+1} 张图片", "SUCCESS")

    def cover_on_image_swapped(self, idx1, idx2):
        if getattr(self, 'current_preview_folder', None):
            self.cover_assignments[self.current_preview_folder] = self.lbl_preview.current_paths.copy()
        self.log_cover(f"已成功对调图 {idx1+1} 和图 {idx2+1} 的位置", "INFO")

    def cover_gen_random_selected(self):
        sel = self.cover_list.selectedItems()
        if not sel: return QMessageBox.warning(self, "提示", "请先在列表中选中要处理的文件夹！")
        for item in sel:
            folder_path = item.text()
            self._assign_random_images(folder_path)
            
            if folder_path in self.cover_states:
                del self.cover_states[folder_path]
        
        if getattr(self, 'current_preview_folder', None) in [item.text() for item in sel]:
            self.lbl_preview.load_images(self.cover_assignments[self.current_preview_folder])
            self.cover_states[self.current_preview_folder] = self.lbl_preview.get_state()
            
        self.log_cover(f"已为选中的 {len(sel)} 个文件夹重新分配了随机图库", "SUCCESS")

    # 【修复核心】彻底重构了这里的批量生成逻辑，保证每次绘制前都能读取自身状态，杜绝最后一项串图的问题
    def cover_save_selected(self):
        save_dir = self.cover_save_dir.text().strip()
        if not save_dir or not os.path.exists(save_dir): return QMessageBox.warning(self, "提示", "请先在上方设置一个有效的封面输出目录！")
        sel = self.cover_list.selectedItems()
        if not sel: return QMessageBox.warning(self, "提示", "请先在列表中选中要生成的文件夹！")
        
        self.log_cover(f"🚀 开始批量生成 {len(sel)} 个拼图...", "INFO")
        self.cover_progress.setValue(0)
        mc = 0
        
        current_preview = getattr(self, 'current_preview_folder', None)
        
        # 将当前显示在 UI 上的画布参数实时同步到状态字典中，防止改动丢失
        if current_preview:
            self.cover_states[current_preview] = self.lbl_preview.get_state()
            self.cover_assignments[current_preview] = self.lbl_preview.current_paths.copy()
        
        items_to_process = list(sel)
        
        for i, item in enumerate(items_to_process):
            folder_path = item.text()
            folder_name = os.path.basename(folder_path); safe_name = sanitize_filename(folder_name)
            
            if folder_path not in self.cover_assignments:
                self._assign_random_images(folder_path)
            
            paths = self.cover_assignments.get(folder_path)
            if not paths: continue
            
            # 不再跳过当前预览项，无差别强制挂载对应数据到画布，保证渲染准确
            if folder_path in self.cover_states:
                self.lbl_preview.load_state(self.cover_states[folder_path])
            else:
                self.lbl_preview.load_images(paths)
                self.cover_states[folder_path] = self.lbl_preview.get_state()
            QApplication.processEvents()
                
            out_path = os.path.join(save_dir, f"{safe_name}.jpg")
            if not self.lbl_preview.render_to_file(out_path):
                self.log_cover(f"❌ 封面写入失败: {safe_name}.jpg", "ERROR")
            else:
                self.log_cover(f"[{i+1}/{len(sel)}] 已生成: {safe_name}.jpg", "SUCCESS")
            mc += 1
            self.cover_progress.setValue(int(((i + 1) / len(sel)) * 100))
            
        # 批量导出结束后，安静地将界面恢复到一开始你正盯着的那张拼图
        if current_preview:
            if current_preview in self.cover_states:
                self.lbl_preview.load_state(self.cover_states[current_preview])
            
        self.log_cover(f"🎉 批量拼图结束，成功产出 {mc} 张封面！", "SUCCESS")

    def batch_auto_match_thumbs(self, auto_dir=None):
        if self.table.rowCount() == 0: return False
        if auto_dir and os.path.exists(auto_dir): thumb_dir = auto_dir
        else:
            thumb_dir = QFileDialog.getExistingDirectory(self, "请选择存放所有封面的图库文件夹", self.last_dir)
            if not thumb_dir: return False
            self.last_dir = thumb_dir
            
        thumb_dir = self.get_abs_path(thumb_dir); mc = 0; self.batch_progress.setValue(0); self.log_msg(f"开始在文件夹 {thumb_dir} 中自动匹配封面...", "INFO")
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0); path_item = self.table.item(row, 4)
            name = sanitize_filename(name_item.text().strip()) if name_item else ""
            QApplication.processEvents(); mp = None
            if name:
                for ext in ['.jpg', '.jpeg', '.png']:
                    tp = find_existing_file(os.path.join(thumb_dir, f"{name}{ext}"))
                    if tp: mp = tp; break
            if mp:
                if path_item: path_item.setData(Qt.ItemDataRole.UserRole, mp)
                self.table.setItem(row, 10, QTableWidgetItem("✅ 封面已匹配")); mc += 1
            else:
                if path_item: path_item.setData(Qt.ItemDataRole.UserRole, None)
                self.table.setItem(row, 10, QTableWidgetItem("❌ 未找到封面"))
            self.batch_progress.setValue(int(((row + 1) / self.table.rowCount()) * 100))
        self.log_msg(f"自动匹配完成, 成功找回 {mc} 张封面图片。", "SUCCESS"); return True

    def batch_manual_thumb(self):
        sel = self.table.selectedRanges()
        if not sel: return QMessageBox.warning(self, "提示", "请先在表格中点击选中一行。")
        fp, _ = QFileDialog.getOpenFileName(self, "手动选择封面图片", self.last_dir, "Images (*.png *.jpg *.jpeg)")
        if fp:
            self.last_dir = os.path.dirname(fp); row = sel[0].topRow(); path_item = self.table.item(row, 4)
            if path_item: path_item.setData(Qt.ItemDataRole.UserRole, fp)
            self.table.setItem(row, 10, QTableWidgetItem("✅ 封面已手动指定")); self.batch_progress.setValue(100)

    def set_buttons_state(self, running):
        state = not running; self.btn_auto.setEnabled(state); self.btn_make.setEnabled(state); self.btn_pub.setEnabled(state); self.btn_stop.setEnabled(running)

    def build_config_for_worker(self):
        return {
            'pt_url': self.input_pt_url.text().strip() + ('/' if not self.input_pt_url.text().endswith('/') else ''), 'cookie': self.input_cookie.text().strip(), 'torrent_dir': self.get_abs_path(self.input_t_path.text()), 'seeding_dir': self.get_abs_path(self.input_s_path.text()), 'use_zip': self.cb_batch_zip.isChecked(), 'test_mode': self.cb_batch_test.isChecked(), 'anonymous': self.cb_batch_anon.isChecked(), 'category_map': {"写真": "401", "人像": "402", "风光": "403", "纪实": "404", "杂志": "405", "静物": "406", "儿童": "407", "超现实": "408", "美食": "409", "动物": "410", "人文": "411", "软件": "412", "图书": "413", "预设": "414", "教程": "415", "Special": "416"}, 'qb_url': self.input_qb_url.text().strip(), 'qb_user': self.input_qb_user.text().strip(), 'qb_pwd': self.input_qb_pwd.text().strip(), 'qb_category': self.input_qb_category.text().strip() if hasattr(self, 'input_qb_category') else "", 'qb_tags': self.input_qb_tags.text().strip() if hasattr(self, 'input_qb_tags') else "", 'add_to_qb': self.chk_qb_add.isChecked(), 'image_token': self.input_img_token.text().strip(), 'image_upload_api': self.input_img_upload_url.text().strip(), 'seed_delay': self.spin_delay.value(), 'reuse_existing': self.chk_reuse_existing.isChecked() if hasattr(self, 'chk_reuse_existing') else False, 'use_proxy': self.chk_proxy.isChecked() if hasattr(self, 'chk_proxy') else False, 'proxy_addr': self.input_proxy.text().strip() if hasattr(self, 'input_proxy') else '127.0.0.1:7897',
            'image_retry_count': self.spin_img_retry.value() if hasattr(self, 'spin_img_retry') else 5
        }

    def start_worker(self, mode):
        tasks = []
        for r in range(self.table.rowCount()):
            preset_name = self.table.cellWidget(r, 2).currentText() if self.table.cellWidget(r, 2) else ""; row_preset = self.find_preset(preset_name)
            name_item = self.table.item(r, 1); path_item = self.table.item(r, 4)
            cat_widget = self.table.cellWidget(r, 7); tag_widget = self.table.cellWidget(r, 8)
            tasks.append({'row': r, 'std_name': name_item.text().strip() if name_item else '', 'folder_path': path_item.text().strip() if path_item else '', 'thumb_path': path_item.data(Qt.ItemDataRole.UserRole) if path_item else None, 'category': cat_widget.currentText() if cat_widget else '', 'tag_names': tag_widget.get_checked_items() if tag_widget else [], 'intro': row_preset.get('intro', '')})
        if not tasks: return QMessageBox.warning(self, "提示", "待处理列表为空，请先添加文件夹！")
        self.set_buttons_state(True); self.batch_progress.setValue(0)
        self.worker = BatchWorkerThread(mode, tasks, self.build_config_for_worker()); self.worker.log_signal.connect(self.log_msg); self.worker.progress_signal.connect(self.batch_progress.setValue); self.worker.cell_update_signal.connect(self.update_table_cell); self.worker.finished_signal.connect(self.worker_finished); self.worker.start()

    def worker_finished(self, success, total):
        self.set_buttons_state(False); QMessageBox.information(self, "任务完成", f"队列任务已全部处理完毕。\n成功次数: {success}/{total}")

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            if not self.worker.wait(8000):
                self.log_msg("⚠️ 后台任务未能在 8 秒内停止，已取消关闭窗口。", "WARNING")
                QMessageBox.warning(self, "提示", "后台任务仍在运行，请稍候再关闭窗口。")
                event.ignore(); return
        super().closeEvent(event)

    def force_stop_worker(self):
        if hasattr(self, 'worker') and self.worker.isRunning(): self.worker.stop(); self.log_msg("🛑 已强行停止后台线程。", "WARNING")

    def run_auto_publish(self):
        reply = QMessageBox.question(self, "一键全自动", "将依次执行：自动找图 ➔ 打包制种 ➔ 推送图床 ➔ 表单发布 ➔ 添加做种。是否继续？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if sys.platform == 'darwin': QTimer.singleShot(400, self._execute_auto_publish)
            else: self._execute_auto_publish()

    def _execute_auto_publish(self):
        target_dir = None
        if hasattr(self, 'chk_auto_cover') and self.chk_auto_cover.isChecked(): target_dir = self.cover_save_dir.text().strip()
        if target_dir and os.path.exists(target_dir): self.batch_auto_match_thumbs(auto_dir=target_dir)
        else: self.batch_auto_match_thumbs()
        self.start_worker('auto')

    def get_proxy_config(self):
        if not (hasattr(self, 'chk_proxy') and self.chk_proxy.isChecked()): return None
        addr = self.input_proxy.text().strip() if hasattr(self, 'input_proxy') else ""
        return normalize_proxy(addr or "127.0.0.1:7897")

    def test_pt_connection(self):
        try:
            r = requests.get(self.input_pt_url.text().strip(), headers={"Cookie": self.input_cookie.text()}, timeout=5, proxies=self.get_proxy_config())
            if "login" in r.url: 
                self.log_msg("PT站连接成功，但要求登录，可能 Cookie 已失效", "WARNING")
                QMessageBox.warning(self, "提示", "能连通 PT 站，但被要求登录，请检查 Cookie 是否过期。")
            else: 
                self.log_msg("🌐 PT站点连接顺畅，身份验证成功。", "SUCCESS")
                QMessageBox.information(self, "成功", "PT站点连接顺畅，身份验证成功。")
        except Exception as e: 
            self.log_msg(f"PT连通性测试失败: {e}", "ERROR")
            QMessageBox.critical(self, "错误", f"连接失败: {e}")

    # 新增的测试图床连通性模块
    def test_image_host_connection(self):
        url = self.input_img_upload_url.text().strip()
        if not url: return QMessageBox.warning(self, "警告", "请先填写图床上传API。")
        self.log_msg(f"正在测试图床连通性: {url} ...")
        status, detail = check_image_host_reachability(url, proxies=self.get_proxy_config())
        if status == "reachable":
            self.log_msg(f"✅ 图床服务器可达（HTTP 响应状态码: {detail}）", "SUCCESS")
            QMessageBox.information(self, "成功", f"图床服务器可达（已收到 HTTP 响应）。\n(响应状态码: {detail})\n注意：此测试仅验证连通性，不代表该接口一定可接收上传。")
        else:
            self.log_msg(f"❌ 图床连接失败: {detail}", "ERROR")
            QMessageBox.critical(self, "错误", f"无法连接到图床服务器，请检查网络策略或代理设置！\n\n报错信息: {detail}")

    def test_qb_connection(self):
        try:
            import qbittorrentapi
            qb = qbittorrentapi.Client(host=self.input_qb_url.text(), username=self.input_qb_user.text(), password=self.input_qb_pwd.text())
            qb.auth_log_in()
            self.log_msg("📡 已成功与本机的 qBittorrent 建立通信。", "SUCCESS")
            QMessageBox.information(self, "成功", "已成功与本机的 qBittorrent 建立通信。")
        except Exception as e: 
            self.log_msg(f"无法连接 qBittorrent: {e}", "ERROR")
            QMessageBox.critical(self, "错误", f"无法连接 qBittorrent: {e}")

    def get_image_token(self):
        email = self.input_img_email.text().strip(); pwd = self.input_img_pwd.text(); token_url = self.input_img_token_url.text().strip()
        if not email or not token_url: return
        self.log_msg("正在向图床请求获取 Token...")
        try:
            response = requests.post(token_url, json={"email": email, "password": pwd}, timeout=10, proxies=self.get_proxy_config()); data = response.json()
            token = None
            if isinstance(data, dict):
                token = data.get("token")
                if not token and isinstance(data.get("data"), dict): token = data["data"].get("token")
            if token:
                self.input_img_token.setText(token); QMessageBox.information(self, "成功", "已成功获取并填入 Token。")
            else: QMessageBox.warning(self, "警告", "获取失败，请检查账号密码。")
        except Exception as e: QMessageBox.critical(self, "错误", f"请求异常:\n{e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PTUploaderFullGUI()
    window.init_all()
    window.show()
    sys.exit(app.exec())