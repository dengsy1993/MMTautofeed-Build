"""MMTautofeed —— PT 批量自动发种工具（PyQt6 单文件版）。

整体结构：
  · 顶部为「主题配色与样式系统」：THEME_LIGHT / THEME_DARK 两张调色板 +
    build_stylesheet() 生成全局 QSS，控件用 role 语义属性自动上色。
  · 中间为若干工具函数（名称清洗、种子 ID 解析、代理、封面拼图基元等）。
  · BatchWorkerThread 负责打包制种 / 图床上传 / 发种 / 推送 qB 的后台流程。
  · PTUploaderBase 提供配置读写、主题切换等公共能力。
  · PTUploaderFullGUI 负责五个标签页的界面搭建与交互。
"""
import sys, os, json, datetime, requests, zipfile, subprocess, uuid, mimetypes, re, math, unicodedata, html
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

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QGroupBox, QLabel, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QLineEdit, QCheckBox, QScrollArea, QGridLayout, QFormLayout, QSpinBox, QHeaderView, QRadioButton, QButtonGroup, QMessageBox, QFileDialog, QDialog, QSizePolicy, QProgressBar, QListWidget, QAbstractItemView, QListView, QTreeView, QFrame, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsPathItem, QGraphicsItem, QSplitter, QSystemTrayIcon, QMenu, QPlainTextEdit, QTextBrowser)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QEvent, QTimer, QPointF, QRectF
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor, QIcon, QImage, QPixmap, QPainter, QPainterPath, QPen, QBrush, QPolygonF, QTransform, QPainterPathStroker, QAction, QLinearGradient, QTextCursor

# =============================================================================
# 主题配色与样式系统（UI 美化核心）
# -----------------------------------------------------------------------------
# 设计思路：
#   1) 把颜色集中到 THEME_LIGHT / THEME_DARK 两张「调色板」，再用
#      build_stylesheet() 生成整份 Qt 样式表（QSS）。这样明/暗两套主题
#      只需要维护一份颜色表，界面各控件也不用到处写死颜色。
#   2) 按钮等控件通过动态属性 role 表达语义（primary/success/warning/
#      danger/purple/ghost/link），配合 QSS 里的 [role="..."] 选择器自动上色，
#      见 apply_role()。想换风格只改调色板即可。
# =============================================================================
THEME_LIGHT = {
    'bg': '#eef1f6', 'surface': '#ffffff', 'surface2': '#f5f8fc', 'border': '#dbe2ec',
    'card': 'rgba(255, 255, 255, 170)',  # 卡片半透明，背景图/渐变能透出来一点
    'dialog_bg': 'rgba(255, 255, 255, 225)',  # 对话框：比卡片更实一点（透得更少）
    'field_bg': 'rgba(255, 255, 255, 180)',   # 输入框/下拉框：亮色更透一些（仍比方框 170 实）
    'text': '#1f2937', 'text_muted': '#6b7280',
    'primary': '#2563eb', 'primary_hover': '#1d4ed8', 'primary_text': '#ffffff',
    'success': '#16a34a', 'success_hover': '#15803d',
    'warning': '#f59e0b', 'warning_hover': '#d97706',
    'danger': '#ef4444', 'danger_hover': '#dc2626',
    'purple': '#7c3aed', 'purple_hover': '#6d28d9',
    'input_bg': '#ffffff', 'input_border': '#cdd5e0',
    'table_bg': 'rgba(255, 255, 255, 180)',   # 表格底：与输入框一致的透明度
    'table_alt': 'rgba(247, 249, 252, 110)',  # 表格隔行色
    'table_grid': '#e6ebf2', 'header_bg': '#f3f6fa', 'header_text': '#64748b',
    'console_bg': 'rgba(11, 18, 32, 220)', 'console_text': '#4ade80',
    'selection_bg': '#2563eb', 'selection_text': '#ffffff',
    'scroll': '#c3ccda', 'scroll_hover': '#9aa6b8',
    'tab_bg': '#e2e8f1', 'tab_text': '#5b6b80',
    'disabled_bg': '#eef1f6', 'disabled_text': '#a8b3c2',
    'tooltip_bg': '#111827', 'tooltip_text': '#f9fafb', 'tooltip_border': '#374151',
    'hint_info': '#6b7280', 'hint_primary': '#2563eb', 'hint_warning': '#d97706',
    # 按钮语义色：按 WCAG 对比度挑选，白字/深字都能看清
    'btn_primary': '#2563eb', 'btn_primary_hover': '#1d4ed8',
    'btn_success': '#15803d', 'btn_success_hover': '#166534',
    'btn_warning': '#f59e0b', 'btn_warning_hover': '#d97706', 'btn_warning_text': '#3b2f00',
    'btn_danger': '#dc2626', 'btn_danger_hover': '#b91c1c',
    'btn_purple': '#7c3aed', 'btn_purple_hover': '#6d28d9',
    # 进度条：轨道/填充/文字分开取色，保证百分比文字始终可读
    'progress_bg': '#e9eef6', 'progress_chunk': '#8fb1f2', 'progress_text': '#1f2937',
    # 自定义样式示例用的 7 色渐变（亮色版：鲜艳，半透明以便与背景图共存）
    'grad1': '#ff5f6d', 'grad2': '#ffc371', 'grad3': '#47e891', 'grad4': '#22d3ee',
    'grad5': '#6366f1', 'grad6': '#a855f7', 'grad7': '#ec4899',
    'grad_alpha': 153,  # 有背景图时色膜的不透明度（0-255）
    'card_bg': 'rgba(255, 255, 255, 170)',
}

THEME_DARK = {
    'bg': '#0f141c', 'surface': '#161c26', 'surface2': '#1b222e', 'border': '#2a3342',
    'card': 'rgba(22, 28, 38, 180)',  # 卡片半透明，背景图/渐变能透出来一点
    'dialog_bg': 'rgba(22, 28, 38, 225)',  # 对话框：比卡片更实一点（透得更少）
    'field_bg': 'rgba(13, 19, 28, 220)',   # 输入框/下拉框：带一点透明，但不比方框透
    'text': '#e6ebf3', 'text_muted': '#93a1b5',
    'primary': '#2563eb', 'primary_hover': '#1d4ed8', 'primary_text': '#ffffff',
    'success': '#22c55e', 'success_hover': '#16a34a',
    'warning': '#f59e0b', 'warning_hover': '#d97706',
    'danger': '#f87171', 'danger_hover': '#ef4444',
    'purple': '#a78bfa', 'purple_hover': '#8b5cf6',
    'input_bg': '#0d131c', 'input_border': '#333d4d',
    'table_bg': 'rgba(13, 19, 28, 220)',      # 表格底：与输入框一致的透明度
    'table_alt': 'rgba(30, 38, 50, 110)',     # 表格隔行色
    'table_grid': '#2a3342', 'header_bg': '#1b222e', 'header_text': '#8b9ab0',
    'console_bg': 'rgba(7, 11, 18, 220)', 'console_text': '#4ade80',
    'selection_bg': '#2563eb', 'selection_text': '#ffffff',
    'scroll': '#3a4457', 'scroll_hover': '#4c5870',
    'tab_bg': '#1b222e', 'tab_text': '#8b9ab0',
    'disabled_bg': '#1a212c', 'disabled_text': '#5b6779',
    'tooltip_bg': '#1b222e', 'tooltip_text': '#f1f5f9', 'tooltip_border': '#3a4457',
    'hint_info': '#93a1b5', 'hint_primary': '#60a5fa', 'hint_warning': '#fbbf24',
    # 按钮语义色：与浅色主题保持一致的可读性（白字/深字均可看清）
    'btn_primary': '#2563eb', 'btn_primary_hover': '#1d4ed8',
    'btn_success': '#15803d', 'btn_success_hover': '#166534',
    'btn_warning': '#f59e0b', 'btn_warning_hover': '#d97706', 'btn_warning_text': '#3b2f00',
    'btn_danger': '#dc2626', 'btn_danger_hover': '#b91c1c',
    'btn_purple': '#7c3aed', 'btn_purple_hover': '#6d28d9',
    # 进度条：深色轨道 + 蓝填充 + 浅色文字
    'progress_bg': '#1a212c', 'progress_chunk': '#2b62c9', 'progress_text': '#eaf0f8',
    # 自定义样式示例用的 7 色渐变（暗色版：压深、半透明，保证浅色文字清晰且能与背景图叠加）
    'grad1': '#1e1b4b', 'grad2': '#312e81', 'grad3': '#4c1d95', 'grad4': '#0f766e',
    'grad5': '#7c2d12', 'grad6': '#1e3a8a', 'grad7': '#134e4a',
    'grad_alpha': 184,  # 有背景图时色膜的不透明度（0-255）
    'card_bg': 'rgba(22, 28, 38, 180)',
}

# 整份 QSS 模板：只含 %(key)s 占位符，运行时用调色板渲染（花括号保持原样）。
_STYLE_TEMPLATE = """
* { font-family: "Segoe UI", "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", sans-serif; }
QWidget { background-color: transparent; color: %(text)s; font-size: 13px; }
QMainWindow { background-color: %(bg)s; }
QDialog { background-color: %(dialog_bg)s; }  /* 对话框带一点透明（比卡片方框更实） */
QMessageBox { background-color: %(surface)s; }  /* 系统提示框保持不透明，避免半透明可读性差 */
QToolTip { background-color: %(tooltip_bg)s; color: %(tooltip_text)s; border: 1px solid %(tooltip_border)s; padding: 6px 9px; border-radius: 6px; font-size: 12px; }

/* ---------- 基础文字与勾选项 ---------- */
QLabel, QCheckBox, QRadioButton { background: transparent; color: %(text)s; }
QCheckBox, QRadioButton { spacing: 7px; }
QLabel#AppTitle { font-size: 20px; font-weight: 800; color: %(text)s; }
QLabel#AppSubtitle { font-size: 12px; color: %(text_muted)s; }
QLabel#Badge { background-color: %(btn_primary)s; color: #ffffff; border-radius: 10px; padding: 3px 10px; font-weight: 700; font-size: 11px; }
QLabel#SubTitle { font-size: 13px; font-weight: 700; color: %(primary)s; padding: 6px 0 0 0; }
QLabel#HintWarn { color: %(hint_warning)s; font-size: 12px; font-weight: 600; }
QLabel#HintPrimary { color: %(hint_primary)s; font-size: 12px; }
QFrame#HLine { background-color: %(border)s; }

/* ---------- 顶部品牌栏（现代卡片式页眉） ---------- */
QFrame#Header { background-color: %(card)s; border: none; border-bottom: 1px solid %(border)s; }

/* ---------- 输入类控件 ---------- */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit, QTimeEdit {
    background-color: %(field_bg)s; color: %(text)s; border: 1px solid %(input_border)s;
    border-radius: 8px; padding: 6px 10px; min-height: 20px;
    selection-background-color: %(primary)s; selection-color: %(primary_text)s;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus { border: 1px solid %(primary)s; }
QLineEdit:disabled, QSpinBox:disabled, QComboBox:disabled { background-color: %(disabled_bg)s; color: %(disabled_text)s; }
/* 下拉框只处理按钮区域，箭头保留系统默认绘制，避免自绘三角在部分平台消失 */
QComboBox::drop-down { border: none; background: transparent; width: 22px; }
QComboBox QAbstractItemView, QListView {
    background-color: %(input_bg)s; color: %(text)s; border: 1px solid %(input_border)s;
    border-radius: 8px; outline: none; padding: 4px;
    selection-background-color: %(primary)s; selection-color: %(primary_text)s;
}
QComboBox QAbstractItemView::item, QListView::item { padding: 6px 8px; border-radius: 5px; color: %(text)s; }
/* 可编辑下拉框内部的输入框去掉自身边框，避免与外框形成“双线” */
QComboBox QLineEdit { border: none; background: transparent; padding: 0px; min-height: 0px; }
QComboBox QAbstractItemView::item:selected, QListView::item:selected { background-color: %(primary)s; color: %(primary_text)s; }

/* ---------- 列表 ---------- */
QListWidget { background-color: %(field_bg)s; color: %(text)s; border: 1px solid %(input_border)s; border-radius: 10px; padding: 6px; outline: none; }
QListWidget::item { background-color: %(surface2)s; border: 1px solid %(border)s; border-radius: 6px; padding: 6px 10px; margin: 3px 2px; color: %(text)s; }
QListWidget::item:selected { background-color: %(primary)s; color: %(primary_text)s; border-color: %(primary)s; }

/* ---------- 分组卡片 ---------- */
QGroupBox { font-weight: 600; color: %(text)s; border: 1px solid %(border)s; border-radius: 12px; margin-top: 22px; padding: 12px; background-color: %(card)s; }
/* 标题放在上边框“上方”的 margin 区域，top:0 可避免标题被边框线穿过 */
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 12px; top: 0px; padding: 0 6px; color: %(primary)s; background-color: transparent; }

/* ---------- 按钮（默认样式 + 语义角色） ---------- */
QPushButton { background-color: %(surface)s; color: %(text)s; border: 1px solid %(input_border)s; border-radius: 8px; padding: 7px 16px; font-weight: 600; }
QPushButton:hover { background-color: %(surface2)s; border-color: %(primary)s; }
QPushButton:pressed { background-color: %(border)s; }
QPushButton[role="primary"] { background-color: %(btn_primary)s; color: #ffffff; border: none; }
QPushButton[role="primary"]:hover { background-color: %(btn_primary_hover)s; }
QPushButton[role="success"] { background-color: %(btn_success)s; color: #ffffff; border: none; }
QPushButton[role="success"]:hover { background-color: %(btn_success_hover)s; }
QPushButton[role="warning"] { background-color: %(btn_warning)s; color: %(btn_warning_text)s; border: none; }
QPushButton[role="warning"]:hover { background-color: %(btn_warning_hover)s; }
QPushButton[role="danger"] { background-color: %(btn_danger)s; color: #ffffff; border: none; }
QPushButton[role="danger"]:hover { background-color: %(btn_danger_hover)s; }
QPushButton[role="purple"] { background-color: %(btn_purple)s; color: #ffffff; border: none; }
QPushButton[role="purple"]:hover { background-color: %(btn_purple_hover)s; }
QPushButton[role="ghost"] { background: transparent; border: none; color: %(danger)s; padding: 6px 8px; }
QPushButton[role="ghost"]:hover { background-color: %(surface2)s; border-radius: 6px; }
QPushButton[role="link"] { background: transparent; border: none; color: %(primary)s; padding: 6px 8px; }
QPushButton[role="link"]:hover { background-color: %(surface2)s; border-radius: 6px; }
QPushButton[compact="true"] { padding: 3px 8px; font-size: 11px; border-radius: 6px; }
QPushButton#HeroButton { font-size: 15px; font-weight: 700; padding: 12px 24px; border-radius: 10px; }
QPushButton:disabled { background-color: %(disabled_bg)s; color: %(disabled_text)s; border: 1px solid %(border)s; }

/* ---------- 表格 ---------- */
QTableWidget { background-color: %(table_bg)s; alternate-background-color: %(table_alt)s; color: %(text)s; gridline-color: %(table_grid)s; border: 1px solid %(border)s; border-radius: 10px; }
QTableWidget::item { padding: 4px 6px; }
QTableWidget::item:selected { background-color: %(selection_bg)s; color: %(selection_text)s; }
QHeaderView::section { background-color: %(header_bg)s; color: %(header_text)s; padding: 9px 8px; border: none; border-right: 1px solid %(border)s; border-bottom: 1px solid %(border)s; font-weight: 600; }
QHeaderView::section:first { border-top-left-radius: 9px; }
QHeaderView::section:last { border-top-right-radius: 9px; }
QTableCornerButton::section { background-color: %(header_bg)s; border: none; }
QTableWidget QComboBox { min-height: 16px; padding: 2px 6px; margin: 2px; border-radius: 6px; }

/* ---------- 选项卡 ---------- */
/* 让选项卡整条区域透明，自定义背景（渐变/图片）能连续铺满，不会有割裂色条 */
QTabWidget, QTabBar { background: transparent; }
QTabWidget::pane { border: none; background: transparent; }
QTabBar::tab { background: %(tab_bg)s; color: %(tab_text)s; padding: 9px 22px; margin: 4px 6px 0 0; border: none; border-radius: 10px; font-weight: 600; }
QTabBar::tab:hover { color: %(text)s; }
QTabBar::tab:selected { background: %(btn_primary)s; color: #ffffff; }

/* ---------- 滚动区域 / 文本域 ---------- */
QScrollArea { border: none; background-color: transparent; }
#ScrollContent { background-color: transparent; }
QTextEdit, QTextBrowser { background-color: %(field_bg)s; color: %(text)s; border: 1px solid %(input_border)s; border-radius: 10px; padding: 8px; }
QTextEdit#LogView, QTextEdit#BatchLogView, QTextEdit#CoverLogView,
QTextBrowser#LogView, QTextBrowser#BatchLogView, QTextBrowser#CoverLogView { background-color: %(console_bg)s; color: %(console_text)s; font-family: Consolas, "Cascadia Mono", monospace; border: 1px solid %(border)s; border-radius: 10px; padding: 10px; }
QPlainTextEdit#CssEditor { background-color: %(console_bg)s; color: %(console_text)s; font-family: Consolas, "Cascadia Mono", monospace; font-size: 12px; border: 1px solid %(border)s; border-radius: 10px; padding: 10px; }
QLabel#BgPreview { border: 1px dashed %(border)s; border-radius: 10px; color: %(text_muted)s; background-color: %(surface2)s; }
/* 批量页的进度日志较矮，内边距收小，保证能完整显示约 3 行 */
QTextEdit#BatchLogView, QTextBrowser#BatchLogView { padding: 6px 8px; }
QTextEdit#PresetInfo { background-color: %(field_bg)s; color: %(text)s; border: 1px dashed %(border)s; border-radius: 8px; padding: 8px 10px; }
QGraphicsView#CollageView { border: 1px solid %(border)s; border-radius: 10px; }

/* ---------- 进度条 ---------- */
QProgressBar { border: none; border-radius: 8px; text-align: center; color: %(progress_text)s; background-color: %(progress_bg)s; font-weight: 600; height: 16px; }
QProgressBar::chunk { background-color: %(progress_chunk)s; border-radius: 8px; }

/* ---------- 滚动条 ---------- */
QScrollBar:vertical { border: none; background: transparent; width: 12px; margin: 2px; }
QScrollBar::handle:vertical { background: %(scroll)s; border-radius: 5px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: %(scroll_hover)s; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { border: none; background: transparent; height: 12px; margin: 2px; }
QScrollBar::handle:horizontal { background: %(scroll)s; border-radius: 5px; min-width: 28px; }
QScrollBar::handle:horizontal:hover { background: %(scroll_hover)s; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
QSplitter::handle { background-color: %(border)s; }
"""


def build_stylesheet(theme):
    """把调色板渲染成完整的 Qt 样式表字符串。"""
    return _STYLE_TEMPLATE % theme


def render_tokens(text, theme):
    """把自定义样式里的 @变量 替换成当前主题的颜色值。

    这样用户只写一份 CSS 就能自动跟随明/暗主题，例如：
        QGroupBox { background-color: @card_bg; }
        QMainWindow { background: qlineargradient(..., stop:0 @grad1, stop:1 @grad7); }
    支持的变量见调色板键名（@bg/@surface/@text/@primary/@grad1..@grad7 等）。
    """
    if not text:
        return text
    # 先替换较长的键，避免 @primary 抢先吃掉 @primary_hover / @primary_text
    for key in sorted(theme.keys(), key=len, reverse=True):
        text = text.replace('@' + key, str(theme[key]))
    return text


def apply_role(widget, role, compact=False):
    """给控件打上语义角色标记，QSS 中的 [role="..."] 选择器会据此统一上色。

    role 取值：primary / success / warning / danger / purple / ghost / link。
    compact=True 时会使用更紧凑的内边距，适合放在表格单元格里的小按钮。
    设置后需要 unpolish + polish，界面才会立刻刷新为新样式。
    """
    try:
        widget.setProperty("role", role)
        widget.setProperty("compact", "true" if compact else "false")
        style = widget.style()
        if style is not None:
            style.unpolish(widget)
            style.polish(widget)
        widget.update()
    except Exception:
        pass

STYLE_LIGHT = build_stylesheet(THEME_LIGHT)  # 明亮主题
STYLE_DARK = build_stylesheet(THEME_DARK)  # 夜间主题

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

# 已经是压缩格式的媒体文件：ZIP 里直接存储（再压缩几乎没收益，还拖慢打包）
ZIP_STORE_EXTS = (
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.avif',
    '.mp4', '.mkv', '.avi', '.mov', '.ts', '.m4v', '.wmv', '.flv', '.webm',
    '.mp3', '.flac', '.aac', '.m4a', '.zip', '.rar', '.7z', '.gz', '.xz', '.bz2',
)

def zip_entry_compress_type(filename):
    """按扩展名决定 ZIP 条目的压缩方式：已压缩媒体用 Stored，其余用 Deflate。"""
    ext = os.path.splitext(str(filename))[1].lower()
    return zipfile.ZIP_STORED if ext in ZIP_STORE_EXTS else zipfile.ZIP_DEFLATED

def linkify_log_line(text):
    """把日志行转成 HTML：自动给其中的 http(s) 链接加上下划线锚点，可直接点击外跳。"""
    esc = html.escape(str(text)).replace('\n', '<br>')
    return re.sub(r'(https?://[^\s<]+)',
                  r'<a href="\1" style="color:#6cb6ff; text-decoration:underline;">\1</a>', esc)

def build_details_url(pt_url, torrent_id):
    """由站点域名 + 种子 ID 拼出真正的详情页链接（避免用登录回跳地址）。"""
    base = (pt_url or '').rstrip('/') + '/'
    return f"{base}details.php?id={torrent_id}" if torrent_id else base

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

# qBittorrent 连接超时（秒）：qB 没启动时最多等这么久就报错，避免界面卡死。
QB_TIMEOUT = 5

def make_qb_client(host, username, password):
    """创建带超时的 qBittorrent 客户端。

    qbittorrentapi 默认没有请求超时，qB 未启动时会长时间挂起；
    这里统一加 5 秒超时（连接/读取都用同一上限）。
    """
    import qbittorrentapi
    return qbittorrentapi.Client(
        host=host, username=username, password=password,
        REQUESTS_ARGS={'timeout': QB_TIMEOUT},
    )

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
        # 最小尺寸放小一些，避免把主窗口的最小高度撑到 1080p 屏幕放不下
        self.setBackgroundBrush(QColor("#2c2c2e")); self.setMinimumSize(320, 420)
        self.setObjectName("CollageView")
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff); self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        
        # 画布底改为透明：屏幕上透出主题底色（明/暗一致），导出时 render_to_file 会填充深色底，
        # 因此封面成品依旧保持原来的深色风格。
        bg_rect = self._scene.addRect(0, 0, 1200, 1680, pen=QPen(Qt.PenStyle.NoPen), brush=QColor(0, 0, 0, 0))
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

    def apply_theme_color(self, color):
        """设置画布背景色（跟随主题明暗），导出成品不受影响（仍为深色）。"""
        try:
            self.setBackgroundBrush(QBrush(color))
        except Exception:
            pass

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

class ConnectionTestThread(QThread):
    """通用连接测试线程。

    把可能阻塞的“测试连通性”操作放到后台执行，测完通过 done_signal
    回传 (成功?, 提示信息)，从而避免 qB 未启动时主界面卡住。
    """
    done_signal = pyqtSignal(bool, str)

    def __init__(self, work, parent=None):
        super().__init__(parent)
        self._work = work

    def run(self):
        try:
            ok, msg = self._work()
        except Exception as e:
            ok, msg = False, str(e)
        self.done_signal.emit(ok, msg)


class BatchWorkerThread(QThread):
    """后台工作线程：按 mode 执行 make（制种）/ publish（发布）/ auto（全自动）。

    通过信号把日志、总进度、单元格状态回传给主界面，避免阻塞 UI。
    """
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
                if not os.path.exists(folder_path): self.cell_update_signal.emit(row, 9, "❌ 路径失效", "#ef4444"); set_p(100); continue
                self.cell_update_signal.emit(row, 9, "制作中...", "#f59e0b")
                try:
                    reuse = self.config.get('reuse_existing', False)
                    target_path = folder_path
                    zip_path = os.path.join(seeding_dir, f"{sanitize_filename(std_name)}.zip") if use_zip else None
                    out_file = os.path.join(local_torrent_dir, f"{sanitize_filename(std_name)}{'.zip' if use_zip else ''}.torrent")
                    if reuse and find_existing_file(out_file):
                        out_file = find_existing_file(out_file)
                        self.emit_log(f"♻️ 复用已存在的种子，跳过重新生成: {os.path.basename(out_file)}", "INFO")
                        self.cell_update_signal.emit(row, 9, "✅ 已制种(复用)", "#22c55e")
                        if self.mode == 'make': success_count += 1
                    else:
                        if use_zip:
                            if reuse and find_existing_file(zip_path):
                                zip_path = find_existing_file(zip_path); target_path = zip_path; self.emit_log(f"♻️ 复用已存在的 ZIP: {os.path.basename(zip_path)}", "INFO")
                            else:
                                set_p(15); zip_name = os.path.basename(zip_path); self.emit_log(f"📦 [文件打包] 制作智能压缩 ZIP: {zip_name} ...", "INFO")
                                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                                    for root, _, files in os.walk(folder_path):
                                        for f in files:
                                            if not self.is_running: raise InterruptedError()
                                            full_path = os.path.join(root, f)
                                            # 媒体用 Stored、其它用 Deflate；ZIP 内统一用正斜杠，跨平台才能正确解压
                                            zipf.write(full_path, os.path.relpath(full_path, os.path.join(folder_path, '..')).replace(os.sep, '/'), compress_type=zip_entry_compress_type(f))
                                target_path = zip_path; self.emit_log(f"✅ ZIP 打包完毕！", "SUCCESS")
                        set_p(35); self.emit_log(f"⚙️ [种子生成] 计算哈希...", "INFO")
                        t = torf.Torrent(path=target_path, trackers=[announce_url], private=True); t.generate()
                        if find_existing_file(out_file): out_file = find_existing_file(out_file); self.emit_log(f"♻️ 已存在同名种子，覆盖重新生成: {os.path.basename(out_file)}", "WARNING")
                        t.write(out_file, overwrite=True)
                        self.cell_update_signal.emit(row, 9, "✅ 已制种", "#22c55e")
                        if self.mode == 'make': success_count += 1
                except Exception as e:
                    self.cell_update_signal.emit(row, 9, "❌ 生成失败", "#ef4444"); self.emit_log(f"制种出错: {e}", "ERROR"); set_p(100); continue
                set_p(50 if self.mode == 'auto' else 100)
            if self.mode in ['publish', 'auto']:
                set_p(55 if self.mode == 'auto' else 10); img_url = ""
                if task['thumb_path'] and os.path.exists(task['thumb_path']):
                    self.cell_update_signal.emit(row, 10, "⬆️ 上传图片...", "#f59e0b"); self.emit_log(f"🖼️ [图床通信] 上传封面...", "INFO")
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
                    self.cell_update_signal.emit(row, 10, "❌ 未选择分类", "#ef4444")
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
                    self.cell_update_signal.emit(row, 10, "✅ 模拟完毕", "#22c55e"); sim_count += 1; set_p(100); continue
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
                                with zipfile.ZipFile(src, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zipf:
                                    for root, _, files in os.walk(folder_path):
                                        for f in files:
                                            full_path = os.path.join(root, f)
                                            zipf.write(full_path, os.path.relpath(full_path, os.path.join(folder_path, '..')).replace(os.sep, '/'), compress_type=zip_entry_compress_type(f))
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
                    self.cell_update_signal.emit(row, 10, "❌ 未制作种子", "#ef4444")
                    try: listing = os.listdir(local_torrent_dir)[:8]
                    except Exception: listing = []
                    self.emit_log(f"❌ 未找到种子文件: {stem}(.zip).torrent | 目录内文件: {listing}", "ERROR"); set_p(100); continue
                self.cell_update_signal.emit(row, 10, "🚀 推送中...", "#f59e0b"); set_p(80 if self.mode == 'auto' else 60)
                try:
                    self.emit_log(f"🌐 [网络推送] 发送表单数据...", "INFO")
                    with open(torrent_path, "rb") as file_stream:
                        files = {'file': (os.path.basename(torrent_path), file_stream, 'application/x-bittorrent')}
                        headers = {"User-Agent": "MMTautofeed-Client/V1.00.0", "Cookie": self.config['cookie']}
                        resp = requests.post(upload_submit_url, headers=headers, data=post_data, files=files, timeout=25, allow_redirects=True, proxies=self._proxies())
                    torrent_id = extract_torrent_id(resp.url)
                    if resp.status_code in [200, 302] and torrent_id:
                        details_url = build_details_url(self.config['pt_url'], torrent_id)
                        self.cell_update_signal.emit(row, 10, "✅ 发布成功", "#22c55e"); self.emit_log(f"🎉【发布成功】种子ID: {torrent_id} | 详情页: {details_url}", "SUCCESS")
                        success_count += 1; set_p(90 if self.mode == 'auto' else 80)
                        if self.config['add_to_qb']:
                            dl_url = f"{self.config['pt_url']}download.php?id={torrent_id}"; self.emit_log(f"📥 [种子拉取] 请求带 Passkey 的种子...", "INFO")
                            final_torrent_path = torrent_path
                            for dl_retry in range(3):
                                try:
                                    dl_resp = requests.get(dl_url, headers=headers, timeout=30, proxies=self._proxies())
                                    if dl_resp.status_code == 200 and len(dl_resp.content) > 100:
                                        final_torrent_path = os.path.join(pt_torrent_dir, f"[PT]{sanitize_filename(std_name)}.torrent")  # 标题若被手改含非法字符也不破坏路径
                                        with open(final_torrent_path, "wb") as tf: tf.write(dl_resp.content)
                                        self.emit_log(f"✅ 官方种子拉取成功: {final_torrent_path}", "SUCCESS"); break
                                    else: 
                                        if dl_retry == 2: self.emit_log("拉取失败，降级使用本地种子推送", "WARNING")
                                except Exception as e:
                                    self.emit_log(f"⚠️ 官方种子拉取超时({e})，重试 {dl_retry+1}/3", "WARNING"); QThread.msleep(2000)
                            set_p(95 if self.mode == 'auto' else 90); save_dir = os.path.abspath(seeding_dir if use_zip else os.path.dirname(folder_path))
                            try:
                                # 先硬超时预探测，再带超时创建客户端：qB 未启动时不会卡很久
                                requests.get(self.config['qb_url'], timeout=QB_TIMEOUT)
                                client = make_qb_client(self.config['qb_url'], self.config['qb_user'], self.config['qb_pwd']); client.auth_log_in()
                                add_kwargs = {"torrent_files": final_torrent_path, "save_path": save_dir, "is_paused": False, "use_auto_torrent_management": False}
                                if self.config.get('qb_category'): add_kwargs['category'] = self.config['qb_category']
                                if self.config.get('qb_tags'): add_kwargs['tags'] = self.config['qb_tags']
                                client.torrents_add(**add_kwargs)
                                self.emit_log(f"📡 [qB做种] 成功推送到 qBittorrent！\n   -> 挂载路径: {save_dir}", "SUCCESS")
                            except Exception as e: self.emit_log(f"⚠️ qB 无法连接: {e}", "WARNING")
                    else:
                        self.emit_log(f"🔎 发种响应: HTTP {resp.status_code} | 最终URL: {resp.url}", "INFO")
                        if 'login.php' in resp.url and not torrent_id:
                            self.cell_update_signal.emit(row, 10, "❌ Cookie失效", "#ef4444")
                            self.emit_log(f"🚨 重定向至登录页，Cookie失效！请在【偏好设置】中重新粘贴浏览器里完整的 Cookie（需包含用户身份项，如 c_secure_uid 和 c_secure_pass）。", "ERROR")
                        else: self.cell_update_signal.emit(row, 10, f"⚠️ 频控或异常", "#ef4444"); self.emit_log(f"🚨 页面未返回有效的种子 ID。", "ERROR")
                except Exception as e: self.cell_update_signal.emit(row, 10, "断网/超时", "#ef4444"); self.emit_log(f"网络连接断开: {e}", "ERROR")
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
        super().__init__(parent); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle("添加 / 编辑预设方案"); self.resize(980, 700)
        layout = QVBoxLayout(self); layout.setContentsMargins(18, 18, 18, 18); layout.setSpacing(10)
        form_layout = QFormLayout(); form_layout.setSpacing(12); form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow) 
        self.input_preset_name = QLineEdit(); form_layout.addRow("预设名称*:", self.input_preset_name)
        self.input_photographer = QLineEdit(); form_layout.addRow("摄影师:", self.input_photographer)
        self.input_model = QLineEdit(); form_layout.addRow("主角/模特:", self.input_model)
        lbl_h = QLabel("💡 提示：至少填写【摄影师】或【主角/模特】之一才能正确生成名字"); lbl_h.setObjectName("HintWarn"); lbl_h.setContentsMargins(0, 0, 0, 0); form_layout.addRow("", lbl_h)
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
        btn_save = QPushButton("💾 保存设定"); apply_role(btn_save, "success"); btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("取消"); btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save); btn_layout.addWidget(btn_cancel); layout.addLayout(btn_layout)
    def get_font_size(self): return self.spin_intro_font.value()
    def set_data(self, data):
        self.input_preset_name.setText(data.get("name", "")); self.input_photographer.setText(data.get("photographer", "")); self.input_model.setText(data.get("model", "")); self.input_intro.setText(data.get("intro", "")); self.combo_category.setCurrentText(data.get("category", "请选择分类..."))
        for tag, cb in self.checkboxes.items(): cb.setChecked(tag in data.get("tags", []))
    def get_data(self): return {"name": self.input_preset_name.text().strip(), "photographer": self.input_photographer.text().strip(), "model": self.input_model.text().strip(), "intro": self.input_intro.toPlainText().strip(), "category": self.combo_category.currentText(), "tags": [t for t, c in self.checkboxes.items() if c.isChecked()]}

class ManagePresetsDialog(QDialog):
    def __init__(self, parent_main_window):
        super().__init__(parent_main_window); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.parent_win = parent_main_window; self.setWindowTitle("预设配置管理"); self.resize(980, 600)
        layout = QVBoxLayout(self); h_top = QHBoxLayout()
        btn_add = QPushButton("＋ 新增一条预设"); apply_role(btn_add, "primary"); btn_add.clicked.connect(self.open_add_preset)
        btn_refresh = QPushButton("🔄 刷新表格"); btn_refresh.clicked.connect(self.refresh_table); h_top.addWidget(btn_add); h_top.addWidget(btn_refresh); h_top.addStretch(); layout.addLayout(h_top)
        self.table = QTableWidget(0, 8); self.table.setAlternatingRowColors(True); self.table.setHorizontalHeaderLabels(["模板名称", "摄影师", "模特", "简介", "分类", "标签", "复制", "操作"])
        self.table.horizontalHeader().setStretchLastSection(False); self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 120); self.table.setColumnWidth(1, 90); self.table.setColumnWidth(2, 90); self.table.setColumnWidth(4, 70); self.table.setColumnWidth(5, 100); self.table.setColumnWidth(6, 74); self.table.setColumnWidth(7, 132)
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
            btn_copy = QPushButton("复制"); apply_role(btn_copy, "success", compact=True); btn_copy.clicked.connect(lambda checked, r=row: self.copy_preset(r))
            h_copy.addWidget(btn_copy); self.table.setCellWidget(row, 6, aw_copy)
            aw_act = QWidget(); h_act = QHBoxLayout(aw_act); h_act.setContentsMargins(4, 4, 4, 4); h_act.setSpacing(4)
            btn_edit = QPushButton("编辑"); apply_role(btn_edit, "warning", compact=True); btn_edit.clicked.connect(lambda checked, r=row: self.edit_preset(r))
            btn_del = QPushButton("删除"); apply_role(btn_del, "danger", compact=True); btn_del.clicked.connect(lambda checked, r=row: self.delete_preset(r))
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
        self.lbl_arrow.setContentsMargins(4, 0, 4, 0)
        
        self.input_replace = QLineEdit()
        self.input_replace.setPlaceholderText("替换为 (留空表示直接删除)")
        self.input_replace.setMinimumWidth(80)
        self.input_replace.setMaximumWidth(110)
        self.input_replace.setToolTip("📌 【替换内容】\n输入你想将其替换成的目标文本。\n如果你只想删除前面查找到的文本特征，请将此处保持留空！")
        
        self.btn_del = QPushButton("🗑")
        self.btn_del.setToolTip("删除此条规则")
        apply_role(self.btn_del, "danger", compact=True)
        self.btn_del.setMinimumWidth(34)  # 保证垃圾桶图标不被裁切
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
        """规则行不再自带样式，统一交给全局主题 QSS 渲染，避免明/暗主题割裂。"""
        self.setStyleSheet("")

    def get_data(self):
        return {
            "type": "regex" if self.combo_type.currentText() == "正则匹配" else "replace",
            "search": self.input_search.text(),
            "replace": self.input_replace.text()
        }

    def remove_self(self):
        self.parent_layout.removeWidget(self)
        self.deleteLater()

# 自定义样式示例：只写一份，用 @变量 自动跟随明/暗主题（点「插入示例」填入）
SAMPLE_CSS = """/* MMTautofeed 自定义样式示例（QSS = Qt 版 CSS）
   @变量 会自动替换成当前主题的颜色，所以同一份 CSS 在明/暗主题下都好看。
   常用变量：@bg @surface @surface2 @border @text @text_muted
             @primary @primary_hover @success @warning @danger @purple
             @card_bg  @grad1 … @grad7（7 色渐变）
   写了的属性覆盖内置主题，没写的沿用内置主题。 */

/* ① 7 色渐变背景：@grad1..@grad7 已按主题配好（亮色=鲜艳，暗色=压深） */
QMainWindow, QDialog {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0.000 @grad1,
        stop:0.166 @grad2,
        stop:0.333 @grad3,
        stop:0.500 @grad4,
        stop:0.666 @grad5,
        stop:0.833 @grad6,
        stop:1.000 @grad7);
}

/* ② 卡片 / 页眉改用主题卡片底色，保证两种主题下文字都清晰 */
QGroupBox  { background-color: @card_bg; }
QFrame#Header { background-color: @card_bg; }

/* ③ 文字用主题文字色（亮色=深字，暗色=浅字） */
QLabel, QCheckBox, QRadioButton, QGroupBox, QLineEdit, QComboBox,
QSpinBox, QTableWidget, QListWidget { color: @text; }
QTabBar::tab { color: @text_muted; }

/* ④ 按钮 / 输入框圆角 */
QPushButton { border-radius: 10px; }
QLineEdit, QComboBox, QSpinBox { border-radius: 10px; }

/* ⑤ 选中标签配色（取消注释即可） */
/* QTabBar::tab:selected { background: #ff7a59; } */
"""


class CssEditorDialog(QDialog):
    """自定义样式编辑器：粘贴/编辑 QSS(CSS) 代码，保存后写入 config.json。"""

    def __init__(self, parent=None, code="", sample=SAMPLE_CSS):
        super().__init__(parent); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._sample = sample
        self.setWindowTitle("编辑自定义样式 (CSS/QSS)"); self.resize(780, 620)
        layout = QVBoxLayout(self); layout.setContentsMargins(16, 16, 16, 16); layout.setSpacing(10)
        hint = QLabel("直接粘贴或编写 CSS/QSS 代码；保存后会叠加在内置主题之上（相同属性以你的为准）。")
        hint.setObjectName("HintPrimary"); hint.setWordWrap(True); layout.addWidget(hint)
        self.editor = QPlainTextEdit(); self.editor.setObjectName("CssEditor")
        self.editor.setPlainText(code)
        layout.addWidget(self.editor, 1)
        hb = QHBoxLayout()
        b_demo = QPushButton("插入示例"); b_demo.setToolTip("按当前主题插入一段带注释的示例样式（亮/暗各一份）。"); b_demo.clicked.connect(lambda: self.editor.setPlainText(self._sample))
        b_import = QPushButton("从文件导入"); b_import.setToolTip("把已有的 .qss/.css 文件内容读进来。"); b_import.clicked.connect(self._import_file)
        hb.addWidget(b_demo); hb.addWidget(b_import); hb.addStretch()
        b_cancel = QPushButton("取消"); b_cancel.clicked.connect(self.reject)
        b_save = QPushButton("💾 保存并应用"); apply_role(b_save, "primary"); b_save.clicked.connect(self.accept)
        hb.addWidget(b_cancel); hb.addWidget(b_save)
        layout.addLayout(hb)

    def _import_file(self):
        fp, _ = QFileDialog.getOpenFileName(self, "导入样式文件", "", "样式文件 (*.qss *.css *.txt);;所有文件 (*.*)")
        if fp:
            try:
                with open(fp, 'r', encoding='utf-8') as f: self.editor.setPlainText(f.read())
            except Exception as e:
                QMessageBox.warning(self, "读取失败", str(e))

    def get_code(self):
        return self.editor.toPlainText()


class BackgroundImageDialog(QDialog):
    """背景图片设置：粘贴图片直链或选择本地图片，可预览；保存后作为主窗口背景。"""

    def __init__(self, parent=None, url=""):
        super().__init__(parent); self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowTitle("设置背景图片"); self.resize(640, 440)
        layout = QVBoxLayout(self); layout.setContentsMargins(16, 16, 16, 16); layout.setSpacing(10)
        hint = QLabel("粘贴图片直链（http/https），或选择本地图片；点【预览】确认后保存。背景图会与自定义 CSS 同时生效。")
        hint.setObjectName("HintPrimary"); hint.setWordWrap(True); layout.addWidget(hint)
        h = QHBoxLayout()
        self.input_url = QLineEdit(); self.input_url.setPlaceholderText("https://…/image.jpg"); self.input_url.setText(url)
        h.addWidget(self.input_url, 1)
        b_local = QPushButton("选择本地图片"); b_local.clicked.connect(self._pick_local); h.addWidget(b_local)
        layout.addLayout(h)
        self.preview = QLabel("预览区域"); self.preview.setObjectName("BgPreview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter); self.preview.setMinimumHeight(240)
        layout.addWidget(self.preview, 1)
        hb = QHBoxLayout()
        b_preview = QPushButton("🔍 预览"); apply_role(b_preview, "primary"); b_preview.clicked.connect(self._preview); hb.addWidget(b_preview)
        hb.addStretch()
        b_cancel = QPushButton("取消"); b_cancel.clicked.connect(self.reject)
        b_ok = QPushButton("💾 使用此图"); apply_role(b_ok, "success"); b_ok.clicked.connect(self.accept)
        hb.addWidget(b_cancel); hb.addWidget(b_ok)
        layout.addLayout(hb)

    def _pick_local(self):
        fp, _ = QFileDialog.getOpenFileName(self, "选择背景图片", "", "图片 (*.jpg *.jpeg *.png *.bmp *.webp *.gif);;所有文件 (*.*)")
        if fp: self.input_url.setText(fp)

    def _fetch_pixmap(self):
        """从链接或本地文件取回图片（网络走系统代理环境）。"""
        src = self.input_url.text().strip()
        if not src: return None
        if os.path.isfile(src):
            pm = QPixmap(src); return pm if not pm.isNull() else None
        try:
            resp = requests.get(src, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()
            pm = QPixmap(); pm.loadFromData(resp.content); return pm if not pm.isNull() else None
        except Exception:
            return None

    def _preview(self):
        pm = self._fetch_pixmap()
        if pm is None:
            QMessageBox.warning(self, "无法加载", "图片加载失败，请检查链接是否可访问。"); return
        self.preview.setPixmap(pm.scaled(self.preview.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def get_url(self):
        return self.input_url.text().strip()


class PTUploaderBase(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MMTautofeed批量发种工具 V1.00.0 (带名称解析引擎)")
        # 默认尺寸按屏幕可用区域自适应：尽量让「批量上传流水线」首屏无需滚动
        try:
            _avail = QApplication.primaryScreen().availableGeometry()
            _w = min(1360, max(1100, _avail.width() - 100))
            _h = min(1060, max(760, _avail.height() - 80))
        except Exception:
            _w, _h = 1320, 960
        self.resize(_w, _h) 
        self.current_theme = "light"; self.hint_labels = []; self.presets_data = []; self.clean_keywords = []; self.clean_exts = []; self.preset_font_size = 10; self.base_dir = ""; self.last_dir = ""
        self.custom_rules = []
        self.tray_icon = None          # 系统托盘图标（惰性创建）
        self._really_quit = False      # 托盘「退出程序」置为 True，绕过“关闭到托盘”
        self.custom_css_code = ""      # 用户自定义 CSS/QSS 代码（存于 config.json）
        self.bg_image_url = ""         # 背景图片链接（网络直链或本地路径，存于 config.json）
        self._bg_pixmap = None         # 背景图内存副本（paintEvent 实时按窗口尺寸绘制）
        
        self.cover_assignments = {}
        self.cover_states = {} 
        self.current_preview_folder = None

    def init_directories(self):
        if getattr(sys, 'frozen', False):
            if sys.platform == 'darwin': self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(sys.executable))))
            else: self.base_dir = os.path.dirname(sys.executable)
        else: self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.last_dir = self.base_dir
        os.makedirs(os.path.join(self.get_data_dir(), 'logs'), exist_ok=True)  # 日志与 userdata 同级

    def get_data_dir(self):
        if getattr(sys, 'frozen', False):
            if sys.platform == 'darwin':
                data_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'MMTautofeed')
            else:
                data_dir = os.path.dirname(sys.executable)
        else:
            data_dir = os.path.dirname(os.path.abspath(__file__))
        try:
            os.makedirs(data_dir, exist_ok=True)
            # 目录不可写（如 exe 装在 Program Files）时退回用户目录，保证配置能保存
            return data_dir if os.access(data_dir, os.W_OK) else self._user_fallback_dir()
        except Exception:
            return self._user_fallback_dir()

    def _user_fallback_dir(self):
        """数据目录不可写时的兜底位置（跨平台）。"""
        if sys.platform == 'darwin':
            base = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support')
        elif sys.platform == 'win32':
            base = os.environ.get('APPDATA') or os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming')
        else:
            base = os.path.join(os.path.expanduser('~'), '.local', 'share')
        d = os.path.join(base, 'MMTautofeed')
        try: os.makedirs(d, exist_ok=True)
        except Exception: pass
        return d

    def get_user_dir(self):
        """用户数据统一目录（config.json / presets.json / logs / 背景图都放这里）。

        升级版本时，只要保留这个 userdata 文件夹，替换程序本体即可保留全部配置。
        首次运行会把旧版本散落在数据目录根下的文件迁移进来。
        """
        base = self.get_data_dir()
        user_dir = os.path.join(base, 'userdata')
        os.makedirs(user_dir, exist_ok=True)
        self._migrate_legacy_data(base, user_dir)
        return user_dir

    def _migrate_legacy_data(self, base, user_dir):
        """数据归位（仅首次）：
        · config.json / presets.json 收进 userdata；
        · logs/ 保持在数据目录下（与 userdata 同级，也把之前误放进 userdata 的挪回来）；
        · 背景图统一为单个 userdata/background.jpg。
        """
        try:
            for name in ('config.json', 'presets.json'):
                src = os.path.join(base, name); dst = os.path.join(user_dir, name)
                if os.path.exists(src) and not os.path.exists(dst):
                    try: os.replace(src, dst)
                    except Exception: pass
            # logs 与 userdata 同级：把 userdata 下已有的日志合并回数据目录根，然后删掉空目录
            src_logs = os.path.join(user_dir, 'logs'); dst_logs = os.path.join(base, 'logs')
            if os.path.isdir(src_logs):
                os.makedirs(dst_logs, exist_ok=True)
                for f in os.listdir(src_logs):
                    s = os.path.join(src_logs, f); d = os.path.join(dst_logs, f)
                    try:
                        if not os.path.exists(d):
                            os.replace(s, d)
                        elif os.path.getsize(s) > os.path.getsize(d):  # 两边都有时保留更完整的那份
                            os.replace(s, d)
                        else:
                            os.remove(s)
                    except Exception: pass
                try:
                    if not os.listdir(src_logs): os.rmdir(src_logs)
                except Exception: pass
            # 背景图统一成单个 background.jpg（优先保留原图）
            bg_new = os.path.join(user_dir, 'background.jpg')
            old_names = ('background_source.jpg', 'background_wallpaper_0.jpg',
                         'background_wallpaper_1.jpg', 'background_wallpaper.jpg')
            if not os.path.exists(bg_new):
                for cand in old_names:
                    src = os.path.join(user_dir, cand)
                    if os.path.exists(src):
                        try: os.replace(src, bg_new)
                        except Exception: pass
                        break
            for cand in old_names:  # 清理旧的分散背景文件
                fp = os.path.join(user_dir, cand)
                if os.path.exists(fp):
                    try: os.remove(fp)
                    except Exception: pass
            for f in os.listdir(base):  # 旧版可能把背景图放在数据目录根
                if f.startswith('background_wallpaper') or f.startswith('background_source'):
                    if not os.path.exists(bg_new):
                        try: os.replace(os.path.join(base, f), bg_new)
                        except Exception: pass
                    else:
                        try: os.remove(os.path.join(base, f))
                        except Exception: pass
        except Exception:
            pass

    def _append_log_html(self, widget, html_line):
        """把一行 HTML 追加到日志控件末尾并滚到底（这样链接才可点击）。"""
        try:
            widget.moveCursor(QTextCursor.MoveOperation.End)
            widget.insertHtml(html_line + '<br>')
            sb = widget.verticalScrollBar()
            sb.setValue(sb.maximum())
        except Exception:
            pass

    def log_msg(self, msg, level="INFO"):
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        log_line = f"{time_str} | {level} | {msg}"
        html_line = linkify_log_line(log_line)  # 链接自动加下划线、可点击外跳
        if hasattr(self, 'log_view'):
            self._append_log_html(self.log_view, html_line)
        if hasattr(self, 'batch_log'):
            self._append_log_html(self.batch_log, html_line)
        QApplication.processEvents()
        try:
            log_file = os.path.join(self.get_data_dir(), 'logs', f"mmtauto_{datetime.datetime.now().strftime('%Y%m%d')}.log")
            with open(log_file, 'a', encoding='utf-8') as f: f.write(log_line + '\n')
        except Exception: pass

    def load_presets(self):
        preset_file = os.path.join(self.get_user_dir(), 'presets.json')
        if os.path.exists(preset_file):
            try:
                with open(preset_file, 'r', encoding='utf-8') as f: self.presets_data = json.load(f)
            except Exception: pass

    def save_presets(self):
        try:
            with open(os.path.join(self.get_user_dir(), 'presets.json'), 'w', encoding='utf-8') as f: json.dump(self.presets_data, f, indent=4, ensure_ascii=False)
        except Exception as e: self.log_msg(f"写入预设文件异常: {e}", "ERROR")

    def _load_custom_css(self):
        """返回用户保存在 config.json 里的自定义样式代码（未启用则返回空串）。"""
        if not (hasattr(self, 'chk_custom_css') and self.chk_custom_css.isChecked()):
            return ""
        return getattr(self, 'custom_css_code', '') or ""

    def apply_theme(self, theme_mode):
        """切换明/暗主题：把对应调色板渲染成 QSS 应用到整个应用。

        若开启了「自定义样式」，会把用户 CSS/QSS 文件的内容拼在内置主题之后，
        从而实现“叠加式”美化（相同属性以自定义样式为准）。
        """
        self.current_theme = theme_mode
        self.theme = THEME_DARK if theme_mode == "dark" else THEME_LIGHT  # 供提示文字等动态取色
        style = STYLE_DARK if theme_mode == "dark" else STYLE_LIGHT
        custom = self._load_custom_css() if hasattr(self, '_load_custom_css') else ""
        # 记录自定义 CSS 里是否写了渐变，供 paintEvent 在背景图之上重绘（这样方框透出来的是渐变而非纯图）
        self._custom_has_gradient = bool(custom and 'qlineargradient' in custom)
        if custom:
            custom = render_tokens(custom, self.theme)  # @变量 → 当前主题颜色，一份 CSS 适配明暗
            style = style + "\n\n/* ===== 用户自定义样式 (CSS/QSS) ===== */\n" + custom
        # 有背景图时窗口背景透明：图片与渐变都交由 paintEvent 绘制，避免样式表把图盖住
        if getattr(self, '_bg_pixmap', None) is not None:
            style = style + "\nQMainWindow { background-color: transparent; }"
        self.setStyleSheet(style)
        QApplication.instance().setStyleSheet(style)
        self.refresh_hint_colors()
        if hasattr(self, '_update_theme_button'):
            self._update_theme_button()  # 顶部按钮图标随主题变化
        try:
            if hasattr(self, 'lbl_preview'):
                _c = QColor(self.theme.get('surface', '#ffffff')); _c.setAlpha(170)
                self.lbl_preview.apply_theme_color(_c)  # 封面画布底色跟随主题
        except Exception:
            pass

        # 自定义规则行（RuleWidget）会记录自身主题，便于局部重绘
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
            "qb_tags": self.input_qb_tags.text() if hasattr(self, 'input_qb_tags') else "",
            "close_action": self._close_action() if hasattr(self, '_close_action') else "ask",
            "tray_notify": self.chk_tray_notify.isChecked() if hasattr(self, 'chk_tray_notify') else True,
            "custom_css_enabled": self.chk_custom_css.isChecked() if hasattr(self, 'chk_custom_css') else False,
            "custom_css_code": getattr(self, 'custom_css_code', ''),  # 自定义样式代码直接存进 config.json
            "bg_image_enabled": self.chk_bg_image.isChecked() if hasattr(self, 'chk_bg_image') else False,
            "bg_image_url": getattr(self, 'bg_image_url', '')
        }
        try:
            with open(os.path.join(self.get_user_dir(), 'config.json'), 'w', encoding='utf-8') as f: json.dump(config_data, f, indent=4, ensure_ascii=False)
            if not silent: QMessageBox.information(self, "操作成功", "设置已保存！"); self.log_msg("偏好设置保存成功", "SUCCESS")
        except Exception as e: self.log_msg(f"配置保存失败: {e}", "ERROR")

    def load_config(self):
        config_file = os.path.join(self.get_user_dir(), 'config.json')
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
                ca = config_data.get("close_action")
                if ca not in ('ask', 'tray', 'quit'):
                    ca = 'tray' if config_data.get("minimize_to_tray") else 'ask'  # 兼容旧配置
                if hasattr(self, 'combo_close_action'): self.combo_close_action.setCurrentIndex(('ask', 'tray', 'quit').index(ca))
                if hasattr(self, 'chk_tray_notify'): self.chk_tray_notify.setChecked(config_data.get("tray_notify", True))
                self.custom_css_code = config_data.get("custom_css_code", "") or ""
                if hasattr(self, 'chk_custom_css'): self.chk_custom_css.setChecked(config_data.get("custom_css_enabled", False))
                if hasattr(self, '_update_css_status'): self._update_css_status()
                self.bg_image_url = config_data.get("bg_image_url", "") or ""
                if hasattr(self, 'chk_bg_image'): self.chk_bg_image.setChecked(config_data.get("bg_image_enabled", False))
                if hasattr(self, '_load_bg_pixmap'):
                    # 启用了背景图但本地文件丢了（比如换机/清理过），自动按链接补下
                    if (self.chk_bg_image.isChecked() and self.bg_image_url
                            and hasattr(self, '_bg_file') and not os.path.exists(self._bg_file())):
                        try: self._download_bg_source(self.bg_image_url)
                        except Exception as e: self.log_msg(f"⚠️ 背景图片重新下载失败：{e}", "WARNING")
                    self._load_bg_pixmap()
                if hasattr(self, '_update_bg_status'): self._update_bg_status()
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
            if hasattr(self, 'combo_close_action'): self.combo_close_action.setCurrentIndex(0)
            if hasattr(self, 'chk_tray_notify'): self.chk_tray_notify.setChecked(True)
            if hasattr(self, 'chk_custom_css'): self.chk_custom_css.setChecked(False)
            self.custom_css_code = ""
            if hasattr(self, 'chk_bg_image'): self.chk_bg_image.setChecked(False)
            self.bg_image_url = ""

        if hasattr(self, 'sandbox_load_rules'):
            self.sandbox_load_rules()
        if hasattr(self, '_sync_tray'):
            self._sync_tray()  # 按配置决定是否显示托盘图标
        if hasattr(self, 'chk_custom_css'):
            self.apply_theme(self.current_theme)  # 自定义样式此时才读到，重应用一次让其生效

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
        """一条细分割线，用于在设置页里分隔不同的配置区块。"""
        line = QFrame(); line.setObjectName("HLine"); line.setFrameShape(QFrame.Shape.HLine); line.setFixedHeight(1); return line

    def create_hint_label(self, text, role="info"):
        """创建一段随主题变色的说明文字；role: info / primary / warning。"""
        lbl = QLabel(text); lbl.setWordWrap(True); lbl.setContentsMargins(0, 0, 0, 0); self.hint_labels.append((lbl, role)); return lbl

    def sub_title(self, text):
        """分区小标题（如「3.1 封面准备」），统一由 QSS 渲染。"""
        lbl = QLabel(text); lbl.setObjectName("SubTitle"); return lbl

    def refresh_hint_colors(self):
        """主题切换时刷新所有说明文字的颜色。"""
        t = getattr(self, 'theme', THEME_LIGHT)
        palette = {'info': t['hint_info'], 'primary': t['hint_primary'], 'warning': t['hint_warning']}
        for l, r in self.hint_labels:
            l.setStyleSheet(f"color: {palette.get(r, t['hint_info'])}; font-size: 12px; background: transparent;")

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
        else:
            # 找不到 app_icon 时用代码画的图标兜底，保证窗口/任务栏始终有图标
            fallback_icon = self._make_tray_icon()
            QApplication.instance().setWindowIcon(fallback_icon)
            self.setWindowIcon(fallback_icon)
            
        self.load_presets()
        
        # 顶部品牌栏 + 选项卡共同组成主界面，整体更有现代应用的层次感
        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(self._build_header())

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        central_layout.addWidget(self.tabs, 1)
        self.setCentralWidget(central)
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

    def _build_header(self):
        """顶部品牌栏：左侧工具名 + 一句话简介，右侧版本徽标。"""
        header = QFrame(); header.setObjectName("Header"); header.setFixedHeight(66)
        h = QHBoxLayout(header); h.setContentsMargins(22, 10, 22, 10); h.setSpacing(12)
        title_box = QVBoxLayout(); title_box.setSpacing(1)
        title = QLabel("MMTautofeed"); title.setObjectName("AppTitle")
        subtitle = QLabel("PT 批量自动发种工具 · 打包制种 / 图床上传 / 一键发布 / qB 做种")
        subtitle.setObjectName("AppSubtitle")
        title_box.addWidget(title); title_box.addWidget(subtitle)
        h.addLayout(title_box); h.addStretch()
        # 一键切换明/暗主题，无需再进设置页找下拉框
        self.btn_theme = QPushButton("🌙 夜间模式"); apply_role(self.btn_theme, "link")
        self.btn_theme.setToolTip("切换到夜间护眼主题")
        self.btn_theme.clicked.connect(self._toggle_theme)
        h.addWidget(self.btn_theme, alignment=Qt.AlignmentFlag.AlignVCenter)
        badge = QLabel("V1.00.0"); badge.setObjectName("Badge"); badge.setToolTip("当前程序版本")
        h.addWidget(badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        return header

    def _toggle_theme(self):
        """顶部主题按钮：自动同步到偏好设置里的下拉框。"""
        if hasattr(self, 'combo_theme'):
            self.combo_theme.setCurrentIndex(0 if self.combo_theme.currentIndex() == 1 else 1)

    def _update_theme_button(self):
        """让顶部按钮的文字/图标跟随当前主题：亮色显示“🌙 夜间模式”，暗色显示“☀️ 白昼模式”。"""
        if not hasattr(self, 'btn_theme'):
            return
        if self.current_theme == "dark":
            self.btn_theme.setText("☀️ 白昼模式"); self.btn_theme.setToolTip("切换到明亮白昼主题")
        else:
            self.btn_theme.setText("🌙 夜间模式"); self.btn_theme.setToolTip("切换到夜间护眼主题")

    def _open_css_editor(self, use_sample=False):
        """弹出样式编辑器：粘贴/编写 CSS(QSS)，保存后写入 config.json 并立即生效。"""
        sample = SAMPLE_CSS  # 一份示例即可，@变量会自动跟随当前主题
        code = sample if use_sample else getattr(self, 'custom_css_code', '')
        dlg = CssEditorDialog(self, code, sample)
        if dlg.exec():
            self.custom_css_code = dlg.get_code()
            self.chk_custom_css.setChecked(bool(self.custom_css_code.strip()))
            self._update_css_status()
            self.apply_theme(self.current_theme)
            self.log_msg("🎨 自定义样式已更新并应用", "SUCCESS")

    def _update_css_status(self):
        """刷新样式状态文字（保存后调用，也用于启动时显示）。"""
        if not hasattr(self, 'lbl_css_status'):
            return
        n = len(getattr(self, 'custom_css_code', '') or '')
        if n:
            self.lbl_css_status.setText(f"✅ 已保存样式代码（约 {n} 字符），勾选上方开关即生效")
        else:
            self.lbl_css_status.setText("未设置样式代码（点右侧按钮粘贴）")

    # ---------------- 背景图片（单文件 + 实时自适应绘制） ----------------
    def _bg_file(self):
        """唯一的背景图文件（放在 userdata 下，方便管理与替换）。"""
        return os.path.join(self.get_user_dir(), 'background.jpg')

    def _load_bg_pixmap(self):
        """把背景图读入内存；未启用或文件不存在则清空。"""
        self._bg_pixmap = None
        if not (hasattr(self, 'chk_bg_image') and self.chk_bg_image.isChecked()):
            return
        p = self._bg_file()
        if os.path.exists(p):
            pm = QPixmap(p)
            if not pm.isNull():
                self._bg_pixmap = pm

    def paintEvent(self, event):
        """先按 cover 方式画背景图，再交给样式表绘制。

        这样自定义 CSS 的渐变会叠加在图片之上（把渐变写成半透明即可与图共存），
        且绘制随窗口尺寸实时进行，窗口化/最大化切换不卡、磁盘上也只有一张图。
        """
        try:
            pm = getattr(self, '_bg_pixmap', None)
            if pm is not None and not pm.isNull():
                target = self.rect()
                tw, th = target.width(), target.height()
                iw, ih = pm.width(), pm.height()
                if tw > 0 and th > 0 and iw > 0 and ih > 0:
                    # cover：从原图中心取一块与窗口同比例的区域，铺满整个窗口
                    scale = max(tw / iw, th / ih)
                    sw, sh = tw / scale, th / scale
                    sx, sy = (iw - sw) / 2.0, (ih - sh) / 2.0
                    painter = QPainter(self)
                    try:
                        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
                        painter.drawPixmap(QRectF(0, 0, tw, th), pm, QRectF(sx, sy, sw, sh))
                        # 在图片之上再叠一层自定义 CSS 的渐变色膜：这样方框透出来的是"图 + CSS 渐变"，
                        # 而不是只有照片，方框上就能看到 CSS 效果了。
                        if getattr(self, '_custom_has_gradient', False):
                            self._paint_css_gradient_overlay(painter, target)
                    finally:
                        painter.end()
        except Exception:
            pass  # 绘制异常绝不冒泡，避免拖垮整个界面
        super().paintEvent(event)

    def _paint_css_gradient_overlay(self, painter, rect):
        """用当前主题的 7 色渐变（与示例 @grad1..@grad7 一致）在图片上叠一层半透明色膜。"""
        keys = ('grad1', 'grad2', 'grad3', 'grad4', 'grad5', 'grad6', 'grad7')
        pos = (0.0, 0.166, 0.333, 0.5, 0.666, 0.833, 1.0)
        alpha = int(self.theme.get('grad_alpha', 160))
        grad = QLinearGradient(QPointF(rect.left(), rect.top()), QPointF(rect.right(), rect.bottom()))
        for k, p in zip(keys, pos):
            c = QColor(str(self.theme.get(k, '#000000')))
            if c.isValid():
                c.setAlpha(alpha)
                grad.setColorAt(p, c)
        painter.fillRect(rect, grad)

    def resizeEvent(self, event):
        """窗口尺寸变化只需重绘（不写盘、不重建样式），因此跟手不卡。"""
        super().resizeEvent(event)
        if getattr(self, '_bg_pixmap', None) is not None:
            self.update()

    def _download_bg_source(self, src):
        """下载/复制背景图，保存为唯一的 userdata/background.jpg，返回路径。"""
        if os.path.isfile(src):
            img = QImage(src)
        else:
            proxies = self.get_proxy_config() if hasattr(self, 'get_proxy_config') else None
            resp = requests.get(src, timeout=20, headers={"User-Agent": "Mozilla/5.0"}, proxies=proxies)
            resp.raise_for_status()
            img = QImage(); img.loadFromData(resp.content)
        if img.isNull():
            raise ValueError("无法解析图片内容（可能不是有效图片）")
        if max(img.width(), img.height()) > 4096:  # 限制尺寸，控制内存
            img = img.scaled(4096, 4096, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        out = self._bg_file()
        if not img.save(out, 'JPG', 92):
            raise ValueError("写入背景图失败")
        return out

    def _on_bg_toggle(self, checked):
        """开关切换：按需补下图片、载入内存并刷新。"""
        if checked:
            try:
                if getattr(self, 'bg_image_url', '') and not os.path.exists(self._bg_file()):
                    self._download_bg_source(self.bg_image_url)
            except Exception as e:
                self.log_msg(f"⚠️ 背景图片准备失败：{e}", "WARNING")
        self._load_bg_pixmap()
        self._update_bg_status()
        self.apply_theme(self.current_theme)
        self.update()

    def _open_bg_dialog(self):
        dlg = BackgroundImageDialog(self, getattr(self, 'bg_image_url', ''))
        if not dlg.exec():
            return
        url = dlg.get_url()
        if not url:
            self._clear_bg_image(); return
        try:
            self._download_bg_source(url)
        except Exception as e:
            QMessageBox.critical(self, "背景设置失败", f"下载 / 处理图片失败：\n{e}"); return
        self.bg_image_url = url
        self.chk_bg_image.setChecked(True)
        self._load_bg_pixmap()
        self._update_bg_status()
        self.apply_theme(self.current_theme)
        self.update()
        self.log_msg("🖼️ 背景图片已更新", "SUCCESS")

    def _clear_bg_image(self):
        self.bg_image_url = ""
        if hasattr(self, 'chk_bg_image'): self.chk_bg_image.setChecked(False)
        self._bg_pixmap = None
        try:
            fp = self._bg_file()
            if os.path.exists(fp): os.remove(fp)
        except Exception:
            pass
        self._update_bg_status()
        self.apply_theme(self.current_theme)
        self.update()

    def _update_bg_status(self):
        if not hasattr(self, 'lbl_bg_status'):
            return
        if hasattr(self, 'chk_bg_image') and self.chk_bg_image.isChecked() and os.path.exists(self._bg_file()):
            self.lbl_bg_status.setText("✅ 已启用背景图片（单张图，随窗口实时自适应铺满，与自定义 CSS 共存）")
        elif getattr(self, 'bg_image_url', ''):
            self.lbl_bg_status.setText("已保存链接，但图片文件缺失")
        else:
            self.lbl_bg_status.setText("未设置背景图片")

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
        """运行日志页：一个只读控制台 + 打开日志目录 / 清空按钮。"""
        layout = QVBoxLayout(self.tab_log); layout.setContentsMargins(16, 16, 16, 16)
        group_log = QGroupBox("🖥️ 实时运行日志"); v_log = QVBoxLayout(); v_log.setSpacing(10)
        self.log_view = QTextBrowser(); self.log_view.setObjectName("LogView"); self.log_view.setReadOnly(True); self.log_view.setOpenExternalLinks(True)
        h_tool = QHBoxLayout(); h_tool.addWidget(QLabel("📌 记录程序详细工作状态、接口返回值和异常报错。")); h_tool.addStretch()
        btn_open_dir = QPushButton("📂 打开日志文件夹")
        btn_open_dir.clicked.connect(lambda: os.startfile(os.path.join(self.get_data_dir(), 'logs')) if sys.platform == 'win32' else subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', os.path.join(self.get_data_dir(), 'logs')]))
        btn_clear = QPushButton("🗑 清空当前面板"); apply_role(btn_clear, "danger"); btn_clear.clicked.connect(self.log_view.clear)
        h_tool.addWidget(btn_open_dir); h_tool.addWidget(btn_clear)
        v_log.addLayout(h_tool); v_log.addWidget(self.log_view, 1)
        group_log.setLayout(v_log); layout.addWidget(group_log)

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
        """批量上传页：三步式布局（选预设 → 加资源 → 封面/制种/发布）。

        整页放在 QScrollArea 里，小窗口时自动出现滚动条，大窗口时不留白。
        """
        batch_scroll = QScrollArea(); batch_scroll.setWidgetResizable(True)
        batch_page = QWidget(); layout = QVBoxLayout(batch_page); layout.setContentsMargins(8, 8, 8, 8); layout.setSpacing(10)
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
        # 预设详情预览：固定高度给足 3 行，避免简介被截断
        self.preset_info_label = QTextEdit(); self.preset_info_label.setObjectName("PresetInfo"); self.preset_info_label.setFixedHeight(74); self.preset_info_label.setReadOnly(True); self.preset_info_label.setToolTip("当前所选预设的详情预览。")
        v_top.addWidget(self.preset_info_label); group_top.setLayout(v_top); layout.addWidget(group_top, 0)

        group_mid = QGroupBox("第二步：添加资源文件夹并自动提取名称/数量"); v_mid = QVBoxLayout()
        v_mid.addWidget(self.create_hint_label("💡 先【1.添加文件夹】再【2.智能扫描提取】；表格任意格可双击修改，选错行点【➖ 移除选中行】。", "primary"))
        h_toolbar = QHBoxLayout()
        b_add = QPushButton("📁 1.添加文件夹"); apply_role(b_add, "success"); b_add.setToolTip("可按住 Ctrl（Mac 为 Command）多选，一次导入多个资源文件夹。"); b_add.clicked.connect(self.batch_add_folder)
        b_scn = QPushButton("🔍 2.智能扫描提取"); apply_role(b_scn, "primary"); b_scn.setToolTip("扫描每个文件夹里的图片/视频数量，并按当前预设生成最终种子标题。"); b_scn.clicked.connect(self.batch_scan_folders)
        b_rn = QPushButton("🔄 3.序列化重命名 (可选)"); apply_role(b_rn, "warning"); b_rn.setToolTip("把文件夹内的图片/视频重命名为 1.jpg、2.mp4…；不可逆，非必要别点。"); b_rn.clicked.connect(self.batch_rename_files)
        b_sandbox = QPushButton("🧪 4.名称解析沙盒(调试)"); apply_role(b_sandbox, "purple"); b_sandbox.setToolTip("想预览/调试标题解析规则时用，看效果、不会影响正式流程。"); b_sandbox.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        b_del = QPushButton("➖ 移除选中行"); apply_role(b_del, "danger"); b_del.setToolTip("把表格里选中的行从待发布列表移除。"); b_del.clicked.connect(self.batch_remove_row)
        b_clr = QPushButton("🗑 清空列表"); apply_role(b_clr, "danger"); b_clr.setToolTip("清空整个待发布列表。"); b_clr.clicked.connect(lambda: self.table.setRowCount(0))
        h_toolbar.addWidget(b_add); h_toolbar.addWidget(b_scn); h_toolbar.addWidget(b_rn); h_toolbar.addWidget(b_sandbox); h_toolbar.addWidget(b_del); h_toolbar.addStretch(); h_toolbar.addWidget(b_clr); v_mid.addLayout(h_toolbar)

        self.table = QTableWidget(0, 12); self.table.setMinimumHeight(72); self.table.verticalHeader().setDefaultSectionSize(34); self.table.setAlternatingRowColors(True)
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
        self.table.setColumnWidth(2, 110); self.table.setColumnWidth(3, 40); self.table.setColumnWidth(4, 90); self.table.setColumnWidth(5, 70); self.table.setColumnWidth(6, 60); self.table.setColumnWidth(7, 75);         self.table.setColumnWidth(8, 120); self.table.setColumnWidth(9, 75); self.table.setColumnWidth(10, 80); self.table.setColumnWidth(11, 62)
        self.table.cellChanged.connect(self.on_table_cell_changed); v_mid.addWidget(self.table); group_mid.setLayout(v_mid); layout.addWidget(group_mid, 1) 

        # ---------- 第三步：封面准备 / 打包 / 发布 ----------
        group_bot = QGroupBox("第三步：封面准备 ➜ 打包制种 ➜ 发布做种（新手直接用底部【一键全自动】）"); v_bot = QVBoxLayout(); v_bot.setSpacing(6)

        # 3.1 封面准备（可选）：三枚按钮 + 一个复选框；说明都收进 tooltip，保持首屏紧凑
        h_cover = QHBoxLayout()
        b_auto_img = QPushButton("🖼️ 自动匹配本地封面"); b_auto_img.setToolTip("选择一个装了封面图的文件夹，程序会按资源名称自动找同名图片（支持 jpg / jpeg / png）。")
        b_auto_img.clicked.connect(self.batch_auto_match_thumbs)
        b_man_img = QPushButton("📌 为选中行指定封面"); b_man_img.setToolTip("先在上方表格里点选一行，再挑一张图片作为该资源的封面。")
        b_man_img.clicked.connect(self.batch_manual_thumb)
        b_jump_cover = QPushButton("🎨 去【封面拼图台】做四宫格封面"); apply_role(b_jump_cover, "purple")
        b_jump_cover.setToolTip("把每个资源的多张图拼成一张精美的四宫格封面；做好后在封面台设置输出目录并保存。")
        b_jump_cover.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        self.chk_auto_cover = QCheckBox("全自动时使用封面台输出目录的封面")
        self.chk_auto_cover.setChecked(True)
        self.chk_auto_cover.setToolTip("勾选后，点【一键全自动】时会先去封面输出目录把拼好的封面抓过来用。")
        h_cover.addWidget(b_auto_img); h_cover.addWidget(b_man_img); h_cover.addWidget(b_jump_cover); h_cover.addWidget(self.chk_auto_cover); h_cover.addStretch()
        v_bot.addLayout(h_cover)
        v_bot.addWidget(self.create_hint_label("💡 封面可选：不设置也能发布，只是帖子没有封面图。想省事先去【封面拼图台】拼好，再点【自动匹配本地封面】。", "primary"))

        # 3.2 分步执行：只想单独重跑某一步时用（按钮文案已自解释，无需额外小标题）
        h_exec2 = QHBoxLayout()
        self.btn_make = QPushButton("📦 第1步：打包并制作种子"); apply_role(self.btn_make, "success")
        self.btn_make.setToolTip("把每个资源的文件夹压缩成 ZIP，并生成对应的 .torrent 种子文件（不做这一步就没法发布）。")
        self.btn_make.clicked.connect(lambda: self.start_worker('make'))
        self.btn_pub = QPushButton("🚀 第2步：推送到 PT 站并做种"); apply_role(self.btn_pub, "warning")
        self.btn_pub.setToolTip("把上一步做好的种子发布到 PT 站，并推送到 qBittorrent 开始做种（需要先在偏好设置里填好 Cookie 和 qB）。")
        self.btn_pub.clicked.connect(lambda: self.start_worker('publish'))
        h_exec2.addWidget(self.btn_make); h_exec2.addWidget(self.btn_pub); h_exec2.addStretch()
        v_bot.addLayout(h_exec2)

        # 3.3 一键全自动 + 停止：新手主入口，做成醒目大按钮
        h_main_btn = QHBoxLayout()
        self.btn_auto = QPushButton("🚀 一键全自动打包发布（新手推荐）"); self.btn_auto.setObjectName("HeroButton"); apply_role(self.btn_auto, "primary")
        self.btn_auto.setToolTip("自动依次完成：找封面 ➜ 打包制种 ➜ 上传图床 ➜ 发布 PT ➜ 推送 qB 做种。")
        self.btn_auto.clicked.connect(self.run_auto_publish)
        self.btn_stop = QPushButton("🛑 停止当前任务"); self.btn_stop.setObjectName("HeroButton"); apply_role(self.btn_stop, "danger")
        self.btn_stop.setToolTip("中断正在进行的后台任务（建议等当前这一项处理完再点）。")
        self.btn_stop.setEnabled(False); self.btn_stop.clicked.connect(self.force_stop_worker)
        h_main_btn.addWidget(self.btn_auto, 3); h_main_btn.addWidget(self.btn_stop)
        v_bot.addLayout(h_main_btn)
        v_bot.addWidget(self.create_hint_label("💡 新手直接点【一键全自动】即可；只想单独重做某一步时，再用上面的【第1步 / 第2步】。", "primary"))

        # 进度条与日志标题合并到同一行，进一步压缩首屏高度
        self.batch_progress = QProgressBar(); self.batch_progress.setValue(0)
        h_log_header = QHBoxLayout(); h_log_header.addWidget(QLabel("📝 实时进度")); h_log_header.addWidget(self.batch_progress, 1)
        self.batch_log = QTextBrowser(); self.batch_log.setObjectName("BatchLogView"); self.batch_log.setMinimumHeight(56); self.batch_log.setFixedHeight(64); self.batch_log.setReadOnly(True); self.batch_log.setOpenExternalLinks(True)
        btn_clr_batch_log = QPushButton("🗑 清空"); apply_role(btn_clr_batch_log, "ghost"); btn_clr_batch_log.setCursor(Qt.CursorShape.PointingHandCursor); btn_clr_batch_log.clicked.connect(self.batch_log.clear)
        h_log_header.addWidget(btn_clr_batch_log); v_bot.addLayout(h_log_header); v_bot.addWidget(self.batch_log); group_bot.setLayout(v_bot); layout.addWidget(group_bot, 0)

        batch_scroll.setWidget(batch_page)
        batch_outer = QVBoxLayout(self.tab_batch); batch_outer.setContentsMargins(0, 0, 0, 0); batch_outer.addWidget(batch_scroll)

        self.refresh_main_preset_combo()

    def setup_sandbox_tab(self):
        """名称解析沙盒页：左侧自定义清洗规则，右侧标题推演对照表。"""
        layout = QVBoxLayout(self.tab_sandbox); layout.setContentsMargins(16, 16, 16, 16); layout.setSpacing(12)
        
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
        
        group_left = QGroupBox("🧠 自定义处理规则 (从上至下执行)")
        v_left = QVBoxLayout()
        h_left_top = QHBoxLayout()
        btn_add_rule = QPushButton("➕ 添加规则")
        btn_add_rule.setToolTip("添加一条“查找 ➜ 替换”规则，用来清洗标题里的多余文字（按从上到下的顺序执行）。")
        apply_role(btn_add_rule, "primary")
        btn_add_rule.clicked.connect(self.sandbox_add_rule)
        btn_save_rule = QPushButton("💾 保存规则到配置")
        apply_role(btn_save_rule, "success")
        btn_save_rule.clicked.connect(self.sandbox_save_rules)
        h_left_top.addStretch()
        h_left_top.addWidget(btn_add_rule)
        h_left_top.addWidget(btn_save_rule)
        v_left.addLayout(h_left_top)
        
        scroll_rules = QScrollArea()
        scroll_rules.setWidgetResizable(True)
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
        apply_role(btn_run_test, "primary")
        btn_run_test.setToolTip("用上方列表里的资源跑一遍，看看每个资源最终会生成什么标题。")
        btn_run_test.clicked.connect(self.sandbox_run_test)
        
        btn_goto_settings = QPushButton("⚙️ 检查全局解析模式 (去设置页)")
        apply_role(btn_goto_settings, "purple")
        btn_goto_settings.setToolTip("真正生效的解析模式在【偏好设置】里，这里只做预览。")
        btn_goto_settings.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        
        h_right_top.addWidget(self.sandbox_combo_mode)
        h_right_top.addWidget(btn_run_test)
        h_right_top.addStretch()
        h_right_top.addWidget(btn_goto_settings)
        
        v_right.addLayout(h_right_top)
        
        lbl_mode_hint = QLabel("⚠️ 注意：沙盒主要用于调试『自定义规则』，上方下拉框仅切换预览视图，实际流水线将严格按照【偏好设置】中的模式执行！")
        lbl_mode_hint.setObjectName("HintWarn")
        v_right.addWidget(lbl_mode_hint)
        
        self.sandbox_table = QTableWidget(0, 2); self.sandbox_table.setAlternatingRowColors(True)
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
        layout = QVBoxLayout(self.tab_cover); layout.setContentsMargins(16, 16, 16, 16); layout.setSpacing(12)
        g_paths = QGroupBox("① 封面输出目录（拼好的封面统一保存在这里）"); f_paths = QFormLayout()
        self.cover_save_dir = QLineEdit(); self.cover_save_dir.setPlaceholderText("点右侧【浏览】选择保存封面的文件夹…")
        self.cover_save_dir.setToolTip("封面会按“资源名.jpg”保存到这里；批量发布时按文件名自动匹配，所以建议用固定目录。")
        h_dir = QHBoxLayout(); h_dir.addWidget(self.cover_save_dir); btn_dir = QPushButton("浏览"); btn_dir.setToolTip("选择封面输出文件夹"); btn_dir.clicked.connect(lambda: self.browse_folder(self.cover_save_dir)); h_dir.addWidget(btn_dir)
        f_paths.addRow("封面输出目录:", h_dir); g_paths.setLayout(f_paths); layout.addWidget(g_paths, 0)
        
        h_main = QHBoxLayout()
        g_list = QGroupBox("② 待处理资源库（可多选批量操作）"); v_list = QVBoxLayout(); h_list_btns = QHBoxLayout()
        btn_add_f = QPushButton("📁 加载资源文件夹"); apply_role(btn_add_f, "primary"); btn_add_f.setToolTip("把要拼封面的资源文件夹加进来（可一次多选）。"); btn_add_f.clicked.connect(self.cover_load_folders)
        btn_del_f = QPushButton("➖ 移除选中"); apply_role(btn_del_f, "danger"); btn_del_f.setToolTip("从列表里移除选中的资源。"); btn_del_f.clicked.connect(self.cover_remove_selected_folder)
        btn_sel_all = QPushButton("☑️ 全选列表"); btn_sel_all.setToolTip("选中列表里的全部资源。"); btn_sel_all.clicked.connect(lambda: self.cover_list.selectAll())
        btn_clear_f = QPushButton("🗑 清空库"); apply_role(btn_clear_f, "danger"); btn_clear_f.setToolTip("清空整个列表。"); btn_clear_f.clicked.connect(lambda: self.cover_list.clear())
        h_list_btns.addWidget(btn_add_f); h_list_btns.addWidget(btn_sel_all); h_list_btns.addWidget(btn_del_f); h_list_btns.addWidget(btn_clear_f); v_list.addLayout(h_list_btns)
        lbl_hint_list = QLabel("💡 在列表里点一个资源，右边就会出现它的四宫格预览；按住 Shift 或 Ctrl(Command) 可多选。"); lbl_hint_list.setObjectName("HintPrimary"); lbl_hint_list.setWordWrap(True); v_list.addWidget(lbl_hint_list)
        self.cover_list = QListWidget()
        self.cover_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection) 
        self.cover_list.itemSelectionChanged.connect(self.cover_item_selected); v_list.addWidget(self.cover_list); g_list.setLayout(v_list); h_main.addWidget(g_list, 1)
        
        g_prev = QGroupBox("③ 封面预览与微调工作台"); v_prev = QVBoxLayout()
        
        lbl_prev_hint = QLabel("💡 画布操作：\n1. 点住图片可拖动位置、滚轮（先点选图片）可缩放，拖太远松手会自动复位。\n2. 【双击图片】可替换那一格的图片。\n3. 满意后点下方【💾 保存并生成】，会按资源名保存到上面的输出目录。")
        lbl_prev_hint.setObjectName("HintWarn"); v_prev.addWidget(lbl_prev_hint)
        
        self.lbl_preview = CollageView()
        self.lbl_preview.image_double_clicked.connect(self.cover_change_single_image_from_event)
        self.lbl_preview.image_swapped.connect(self.cover_on_image_swapped)
        v_prev.addWidget(self.lbl_preview, 1)
        
        self.cover_progress = QProgressBar(); self.cover_progress.setValue(0); self.cover_progress.setFixedHeight(16); v_prev.addWidget(self.cover_progress)
        self.cover_log = QTextBrowser(); self.cover_log.setObjectName("CoverLogView"); self.cover_log.setReadOnly(True); self.cover_log.setOpenExternalLinks(True); self.cover_log.setFixedHeight(60); v_prev.addWidget(self.cover_log)
        
        h_actions1 = QHBoxLayout()
        btn_rand = QPushButton("🎲 随机换一批（对选中的项）")
        apply_role(btn_rand, "primary")
        btn_rand.setToolTip("从每个选中资源里重新随机挑 4 张图放进四宫格。")
        btn_rand.clicked.connect(self.cover_gen_random_selected)
        
        btn_save_single = QPushButton("💾 保存并生成封面（对选中的项）")
        apply_role(btn_save_single, "warning")
        btn_save_single.setToolTip("把选中的资源逐个渲染并保存成“资源名.jpg”到输出目录。")
        btn_save_single.clicked.connect(self.cover_save_selected)
        
        h_actions1.addWidget(btn_rand); h_actions1.addWidget(btn_save_single); v_prev.addLayout(h_actions1)
        g_prev.setLayout(v_prev); h_main.addWidget(g_prev, 2); layout.addLayout(h_main, 1)

    def setup_settings_tab(self):
        """偏好设置页：路径 / PT 与图床 / 自动化与拦截规则，整页可滚动。"""
        sa = QScrollArea(); sa.setWidgetResizable(True); mw = QWidget(); layout = QVBoxLayout(mw); layout.setContentsMargins(16, 16, 16, 16); layout.setSpacing(16)
        gb_b = QGroupBox("📌 基础路径设置"); fb = QFormLayout(); fb.setSpacing(14); fb.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        fb.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)  # 输入框铺满卡片宽度
        self.combo_theme = QComboBox(); self.combo_theme.addItems(["明亮白昼模式", "夜间护眼模式"]); self.combo_theme.currentIndexChanged.connect(self.theme_changed); fb.addRow("渲染主题:", self.combo_theme)
        self.input_t_path = QLineEdit(); self.input_t_path.setPlaceholderText("建议填 ./torrents"); self.input_s_path = QLineEdit(); self.input_s_path.setPlaceholderText("建议填 ./seeding")
        h1 = QHBoxLayout(); h1.addWidget(self.input_t_path); b1 = QPushButton("浏览"); b1.clicked.connect(lambda: self.browse_folder(self.input_t_path)); h1.addWidget(b1)
        h2 = QHBoxLayout(); h2.addWidget(self.input_s_path); b2 = QPushButton("浏览"); b2.clicked.connect(lambda: self.browse_folder(self.input_s_path)); h2.addWidget(b2)
        fb.addRow("官方种子存放位置:", h1); fb.addRow("做种文件位置:", h2); fb.addRow(self.create_hint_label("💡 说明：为了防乱，从 PT 站下载回来的带个人 Passkey 的官方种子会保存在【种子存放位置】下的【PT_Official】子文件夹内。\n而本地打包后自己生成的原始种子会放入该路径下的【Local_Made】子文件夹内。", "primary")); gb_b.setLayout(fb); layout.addWidget(gb_b)
        gn = QGroupBox("🌐 PT站点与图床配置"); fn = QFormLayout(); fn.setSpacing(14); fn.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        fn.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)  # 输入框铺满卡片宽度
        self.input_pt_url = QLineEdit(); self.input_cookie = QLineEdit(); self.input_api_key = QLineEdit()
        fn.addRow("PT站域名:", self.input_pt_url); fn.addRow("账号 Cookie:", self.input_cookie); fn.addRow("API Key (选填):", self.input_api_key)
        b_pt = QPushButton("测试能否连通 PT 站"); apply_role(b_pt, "primary"); b_pt.clicked.connect(self.test_pt_connection); fn.addRow("", b_pt)
        fn.addRow(self.get_hline())
        
        self.input_img_upload_url = QLineEdit(); self.input_img_email = QLineEdit(); self.input_img_pwd = QLineEdit(echoMode=QLineEdit.EchoMode.Password); self.input_img_token = QLineEdit(echoMode=QLineEdit.EchoMode.Password); self.input_img_token_url = QLineEdit()
        fn.addRow("图床上传API:", self.input_img_upload_url); fn.addRow("验证 Token:", self.input_img_token); fn.addRow("获取 Token API:", self.input_img_token_url)
        fn.addRow("图床邮箱:", self.input_img_email); fn.addRow("图床密码:", self.input_img_pwd)
        
        # 图床测试与Token获取区
        b_gt = QPushButton("向图床申请获取 Token"); apply_role(b_gt, "success"); b_gt.clicked.connect(self.get_image_token)
        b_test_img = QPushButton("测试图床连通性"); apply_role(b_test_img, "primary"); b_test_img.clicked.connect(self.test_image_host_connection)
        h_img_btns = QHBoxLayout(); h_img_btns.addWidget(b_gt); h_img_btns.addWidget(b_test_img); fn.addRow("", h_img_btns)
        
        # 增加上传重试控制控件
        hr2 = QHBoxLayout(); hr2.addWidget(QLabel("图床上传失败时重试次数:")); self.spin_img_retry = QSpinBox(); self.spin_img_retry.setRange(1, 10); self.spin_img_retry.setValue(5); hr2.addWidget(self.spin_img_retry); hr2.addWidget(QLabel("次 (默认5次)")); hr2.addStretch(); fn.addRow("图床容错机制:", hr2)
        
        hr = QHBoxLayout(); hr.addWidget(QLabel("自动发种时，两个种子间隔时间:")); self.spin_delay = QSpinBox(); self.spin_delay.setMaximum(9999); self.spin_delay.setValue(5); hr.addWidget(self.spin_delay); hr.addWidget(QLabel("秒 (默认5秒，为0时不限制)")); hr.addStretch(); fn.addRow("发种限流保护:", hr)
        hp = QHBoxLayout(); self.chk_proxy = QCheckBox("启用网络代理"); self.chk_proxy.setChecked(False); self.chk_proxy.setToolTip("使用 VPN / 代理（如 Clash、v2ray）时勾选，否则 PT 站/图床请求可能失败。默认关闭。")
        self.input_proxy = QLineEdit(); self.input_proxy.setText("127.0.0.1:7897"); self.input_proxy.setPlaceholderText("例如 127.0.0.1:7897")
        hp.addWidget(self.chk_proxy); hp.addWidget(QLabel("代理地址:")); hp.addWidget(self.input_proxy); hp.addStretch(); fn.addRow("网络代理:", hp)
        gn.setLayout(fn); layout.addWidget(gn)

        # 窗口与托盘：点击关闭时的行为（常规软件做法：询问 / 最小化到托盘 / 直接退出）
        gt = QGroupBox("🖥️ 窗口与托盘"); ft = QFormLayout(); ft.setSpacing(14)
        self.combo_close_action = QComboBox()
        self.combo_close_action.addItems(["关闭时询问我", "最小化到系统托盘", "直接退出程序"])
        self.combo_close_action.setToolTip("点击右上角关闭时的行为。选「询问」会弹窗让你每次选择（可勾选不再询问）。")
        self.combo_close_action.currentIndexChanged.connect(lambda _i: self._sync_tray())
        ft.addRow("关闭窗口时:", self.combo_close_action)
        self.chk_tray_notify = QCheckBox("最小化到托盘时弹出提示通知")
        self.chk_tray_notify.setChecked(True)
        self.chk_tray_notify.setToolTip("取消勾选后，收进托盘时不再弹系统通知，更安静。")
        ft.addRow(self.chk_tray_notify)
        ft.addRow(self.create_hint_label("💡 选「询问」时，关闭会弹窗选择【最小化到托盘 / 关闭软件】，并可勾选「记住我的选择」以后不再弹。", "primary"))
        gt.setLayout(ft); layout.addWidget(gt)

        # 自定义样式 (CSS/QSS)：把自己的样式叠加到内置主题之上，用于个性化美化
        gs = QGroupBox("🎨 自定义样式 (CSS/QSS)"); fs = QFormLayout(); fs.setSpacing(14)
        self.chk_custom_css = QCheckBox("启用自定义样式（叠加在当前主题之上）")
        self.chk_custom_css.setToolTip("Qt 的 QSS 就是 CSS 语法：可自定义颜色、圆角、字号、间距等。未写的属性沿用内置主题。代码保存在 config.json。")
        self.chk_custom_css.toggled.connect(lambda _checked: self.apply_theme(self.current_theme))
        fs.addRow("", self.chk_custom_css)
        self.lbl_css_status = QLabel("未设置样式代码"); self.lbl_css_status.setObjectName("HintPrimary"); self.lbl_css_status.setWordWrap(True)
        h_css = QHBoxLayout(); h_css.addWidget(self.lbl_css_status, 1)
        b_css = QPushButton("✏️ 编辑样式代码…"); apply_role(b_css, "primary"); b_css.setToolTip("弹出编辑器，粘贴 / 编写 CSS(QSS) 代码，保存后写入 config.json。")
        b_css.clicked.connect(lambda: self._open_css_editor(False)); h_css.addWidget(b_css)
        fs.addRow("样式代码:", h_css)
        fs.addRow(self.create_hint_label("💡 QSS = Qt 版 CSS。点【编辑样式代码】粘贴即可；相同属性覆盖内置主题，并随 config.json 一起保存。", "primary"))
        gs.setLayout(fs); layout.addWidget(gs)

        # 背景图片：支持图床/网络直链，作为窗口背景且与自定义 CSS 共存
        gbg = QGroupBox("🖼️ 背景图片"); fbg = QFormLayout(); fbg.setSpacing(14)
        self.chk_bg_image = QCheckBox("启用背景图片（作为主窗口背景，与自定义 CSS 共存）")
        self.chk_bg_image.setToolTip("勾选后主窗口显示你设置的图片；按钮、卡片、文字等自定义样式仍然生效。")
        self.chk_bg_image.toggled.connect(self._on_bg_toggle)
        fbg.addRow(self.chk_bg_image)
        self.lbl_bg_status = QLabel("未设置背景图片"); self.lbl_bg_status.setObjectName("HintPrimary"); self.lbl_bg_status.setWordWrap(True)
        h_bg = QHBoxLayout(); h_bg.addWidget(self.lbl_bg_status, 1)
        b_bg = QPushButton("🖼️ 设置背景图片…"); apply_role(b_bg, "primary"); b_bg.setToolTip("粘贴图床/网络图片直链，或选择本地图片。")
        b_bg.clicked.connect(self._open_bg_dialog); h_bg.addWidget(b_bg)
        b_bg_clear = QPushButton("清除"); b_bg_clear.clicked.connect(self._clear_bg_image); h_bg.addWidget(b_bg_clear)
        fbg.addRow("背景图片:", h_bg)
        fbg.addRow(self.create_hint_label("💡 支持网络直链或本地图片；背景图与自定义 CSS（按钮/卡片/文字等效果）会同时生效。", "primary"))
        gbg.setLayout(fbg); layout.addWidget(gbg)

        ga = QGroupBox("⚙️ 防误抓拦截规则与自动化配置"); fa = QFormLayout(); fa.setSpacing(14); fa.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        fa.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)  # 输入框铺满卡片宽度
        
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
        
        b_qb = QPushButton("测试连接 qBittorrent"); apply_role(b_qb, "primary"); b_qb.clicked.connect(self.test_qb_connection); fa.addRow("", b_qb)
        fa.addRow(self.get_hline())
        # 名称解析模式：整行占满宽度，注释才能完整显示（不再挤在窄小的“值列”里）
        w_parse = QWidget(); pl = QVBoxLayout(w_parse); pl.setContentsMargins(0, 0, 0, 0); pl.setSpacing(6)
        pl.addWidget(QLabel("<b>名称解析模式（三选一）：</b>"))
        self.btn_group_parse = QButtonGroup(); self.rb_none = QRadioButton("禁用提取"); self.rb_simple = QRadioButton("简单提取"); self.rb_full = QRadioButton("强效重组"); self.btn_group_parse.addButton(self.rb_none); self.btn_group_parse.addButton(self.rb_simple); self.btn_group_parse.addButton(self.rb_full)
        
        self.rb_none.toggled.connect(lambda checked: self.sandbox_combo_mode.setCurrentIndex(2) if checked and hasattr(self, 'sandbox_combo_mode') else None)
        self.rb_simple.toggled.connect(lambda checked: self.sandbox_combo_mode.setCurrentIndex(0) if checked and hasattr(self, 'sandbox_combo_mode') else None)
        self.rb_full.toggled.connect(lambda checked: self.sandbox_combo_mode.setCurrentIndex(1) if checked and hasattr(self, 'sandbox_combo_mode') else None)
        
        pl.addWidget(self.rb_none); pl.addWidget(self.create_hint_label("💡 禁用提取：直接使用资源文件夹的名称作为种子标题，不做任何拼装。\n【适用场景】提前已经按标准修改好文件夹名称。", "info"))
        pl.addWidget(self.rb_simple); pl.addWidget(self.create_hint_label("💡 简单提取 (推荐)：将文件夹完整名称作为『主题』，然后自动补充年份和P数，其他缺失项用预设补齐。\n【举例】文件夹叫：秀人网写真 ➔ 『秀人网写真』-预设模特-预设摄影师-63P-Moment", "info"))
        pl.addWidget(self.rb_full); pl.addWidget(self.create_hint_label("💡 强效重组：根据文件夹的名称来判断，有和预设一样的摄影师/模特，需去掉不在主题里面显示；文件夹名称有疑似日期数字的，需提取年份出来回填，同样也不在主题里面显示。\n例1：MintYe薄荷叶 Vol.004 何梦兮Stacy ➔ 『MintYe薄荷叶 Vol.004』-预设补齐\n例2：MintYe薄荷叶 2021.02.28 Vol.004 何梦兮Stacy ➔ 『MintYe薄荷叶 Vol.004』-预设补齐-2021-63P-Moment", "info")); fa.addRow(w_parse)
        fa.addRow(self.get_hline())
        lc = QGridLayout(); self.input_kw = QLineEdit(); self.input_kw.setPlaceholderText("输入后按回车添加"); self.input_kw.setMinimumWidth(150); self.input_kw.returnPressed.connect(lambda: self.add_cleanup_item(self.input_kw, self.list_kw)); self.input_ext = QLineEdit(); self.input_ext.setPlaceholderText("输入后按回车添加"); self.input_ext.setMinimumWidth(150); self.input_ext.returnPressed.connect(lambda: self.add_cleanup_item(self.input_ext, self.list_ext))
        self.list_kw = QListWidget(); self.list_kw.setViewMode(QListWidget.ViewMode(1)); self.list_kw.setResizeMode(QListWidget.ResizeMode(1)); self.list_kw.setSpacing(4); self.list_ext = QListWidget(); self.list_ext.setViewMode(QListWidget.ViewMode(1)); self.list_ext.setResizeMode(QListWidget.ResizeMode(1)); self.list_ext.setSpacing(4)
        b_dk = QPushButton("删除选中"); apply_role(b_dk, "danger", compact=True); b_dk.clicked.connect(lambda: self.del_cleanup_item(self.list_kw)); b_ck = QPushButton("全部清空"); apply_role(b_ck, "default", compact=True); b_ck.clicked.connect(lambda: self.clear_all_cleanup_items(self.list_kw))
        b_de = QPushButton("删除选中"); apply_role(b_de, "danger", compact=True); b_de.clicked.connect(lambda: self.del_cleanup_item(self.list_ext)); b_ce = QPushButton("全部清空"); apply_role(b_ce, "default", compact=True); b_ce.clicked.connect(lambda: self.clear_all_cleanup_items(self.list_ext))
        lc.addWidget(QLabel("包含以下文字则删除:"), 0, 0); lc.addWidget(self.input_kw, 0, 1, 1, 2); lc.addWidget(QLabel("属于以下后缀则删除:"), 0, 3); lc.addWidget(self.input_ext, 0, 4, 1, 2); lc.addWidget(self.list_kw, 1, 0, 1, 3); lc.addWidget(self.list_ext, 1, 3, 1, 3)
        hk = QHBoxLayout(); hk.addWidget(b_dk); hk.addWidget(b_ck); hk.addStretch(); he = QHBoxLayout(); he.addWidget(b_de); he.addWidget(b_ce); he.addStretch()
        lc.addLayout(hk, 2, 0, 1, 3); lc.addLayout(he, 2, 3, 1, 3); fa.addRow("广告文件拦截器:", lc)
        lbl_ad = self.create_hint_label("💡 操作指南：在上方输入框内输入你想拦截的词汇或后缀名（例如：.url、.txt、网址、赌场），然后按键盘上的【回车键 (Enter)】，即可将其加入拦截库中。", "primary"); fa.addRow(lbl_ad)
        ga.setLayout(fa); layout.addWidget(ga)
        hb = QHBoxLayout()
        br = QPushButton("取消更改，恢复上次保存配置"); br.setToolTip("放弃未保存的修改，重新读取 config.json。"); br.clicked.connect(self.load_config)
        bs = QPushButton("💾 保存偏好设置"); bs.setObjectName("HeroButton"); apply_role(bs, "primary"); bs.setToolTip("把当前设置写入 config.json。"); bs.clicked.connect(self.save_config)
        hb.addWidget(br); hb.addWidget(bs); layout.addLayout(hb)
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
        btn_del = QPushButton("移除"); apply_role(btn_del, "danger", compact=True); btn_del.clicked.connect(self.remove_table_row); self.table.setCellWidget(row, 11, btn_del)

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
                    status_item = QTableWidgetItem("❌ 路径失效"); status_item.setForeground(QBrush(QColor("#ef4444")))
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
        self._append_log_html(self.cover_log, linkify_log_line(f"{time_str} | {msg}"))
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
        if save_dir: save_dir = self.get_abs_path(save_dir)  # 统一解析相对路径/~，兼容 .app/.exe
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

    def _make_tray_icon(self):
        """没有 app_icon 时，用代码画一个简单的圆形图标兜底。"""
        pm = QPixmap(64, 64); pm.fill(QColor("#2563eb"))
        p = QPainter(pm); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QColor("#ffffff")); f = p.font(); f.setPointSize(30); f.setBold(True); p.setFont(f)
        p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "M"); p.end()
        return QIcon(pm)

    def _sync_tray(self):
        """根据「关闭到托盘」开关显示/隐藏托盘图标（惰性创建，跨平台安全）。"""
        try:
            available = QSystemTrayIcon.isSystemTrayAvailable()
        except Exception:
            available = False
        if not available:
            return
        enabled = self._tray_needed()
        if self.tray_icon is None:
            icon = self.windowIcon()
            if icon is None or icon.isNull():
                icon = QApplication.instance().windowIcon()
            if icon is None or icon.isNull():
                icon = self._make_tray_icon()
            self.tray_icon = QSystemTrayIcon(icon, self)
            menu = QMenu()
            act_show = QAction("显示主窗口", self); act_show.triggered.connect(self._restore_from_tray); menu.addAction(act_show)
            menu.addSeparator()
            act_quit = QAction("退出程序", self); act_quit.triggered.connect(self._quit_app); menu.addAction(act_quit)
            self.tray_icon.setContextMenu(menu)
            self.tray_icon.setToolTip("MMTautofeed 批量发种工具")
            self.tray_icon.activated.connect(self._on_tray_activated)
        if enabled:
            self.tray_icon.show()
        else:
            self.tray_icon.hide()

    def _on_tray_activated(self, reason):
        """单击/双击托盘图标时恢复主窗口。"""
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self._restore_from_tray()

    def _restore_from_tray(self):
        self.showNormal(); self.raise_(); self.activateWindow()

    def _close_action(self):
        """读取「关闭窗口时」的设置：ask=询问 / tray=最小化到托盘 / quit=直接退出。"""
        if hasattr(self, 'combo_close_action'):
            i = self.combo_close_action.currentIndex()
            if i in (0, 1, 2):
                return ('ask', 'tray', 'quit')[i]
        return 'ask'

    def _tray_needed(self):
        """询问或托盘模式下需要显示托盘图标。"""
        return self._close_action() in ('ask', 'tray')

    def _minimize_to_tray(self):
        """收进系统托盘（后台继续运行）。"""
        self.hide()
        if self.tray_icon is not None:
            self.tray_icon.show()
            try:
                if not hasattr(self, 'chk_tray_notify') or self.chk_tray_notify.isChecked():
                    self.tray_icon.showMessage("MMTautofeed", "已最小化到托盘，后台任务继续运行。",
                                               QSystemTrayIcon.MessageIcon.Information, 3000)
            except Exception:
                pass

    def _confirm_close(self):
        """常规关闭确认弹窗，返回 ('tray'|'quit', 是否记住) ；用户取消返回 None。"""
        box = QMessageBox(self)
        box.setWindowTitle("关闭 MMTautofeed")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText("要最小化到系统托盘（后台继续运行），还是关闭软件？")
        btn_tray = box.addButton("最小化到系统托盘", QMessageBox.ButtonRole.AcceptRole)
        btn_quit = box.addButton("关闭软件", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        chk = QCheckBox("记住我的选择，以后不再询问")
        box.setCheckBox(chk)
        box.setDefaultButton(btn_tray)
        box.exec()
        clicked = box.clickedButton()
        if clicked is btn_tray:
            return ('tray', chk.isChecked())
        if clicked is btn_quit:
            return ('quit', chk.isChecked())
        return None  # 取消（或直接关掉弹窗）

    def _quit_app(self):
        """托盘菜单的「退出程序」：真正退出并结束后台线程。"""
        self._really_quit = True
        if self.tray_icon is not None:
            self.tray_icon.hide()
        self.close()

    def closeEvent(self, event):
        # 「托盘菜单→退出程序」直接走真正的关闭流程
        if not self._really_quit:
            tray_ok = self.tray_icon is not None
            action = self._close_action()
            if tray_ok and action == 'ask':
                # 常规做法：弹窗让用户选择，可勾选「记住我的选择」
                result = self._confirm_close()
                if result is None:
                    event.ignore(); return  # 用户取消，保持窗口
                choice, remember = result
                if remember and hasattr(self, 'combo_close_action'):
                    self.combo_close_action.setCurrentIndex(1 if choice == 'tray' else 2)
                    self.save_config(silent=True)
                if choice == 'tray':
                    self._minimize_to_tray(); event.ignore(); return
                # choice == 'quit'：继续往下走真正的关闭
            elif tray_ok and action == 'tray':
                self._minimize_to_tray(); event.ignore(); return
            # action == 'quit' 或无托盘：真正关闭
        if hasattr(self, 'worker') and self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            if not self.worker.wait(8000):
                self.log_msg("⚠️ 后台任务未能在 8 秒内停止，已取消关闭窗口。", "WARNING")
                QMessageBox.warning(self, "提示", "后台任务仍在运行，请稍候再关闭窗口。")
                event.ignore(); return
        super().closeEvent(event)
        # 真正退出时：隐藏托盘并结束事件循环，确保进程退出、释放 exe 占用
        try:
            if self.tray_icon is not None: self.tray_icon.hide()
            QApplication.instance().quit()
        except Exception:
            pass

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
        if target_dir: target_dir = self.get_abs_path(target_dir)  # 统一解析路径，兼容 .app/.exe
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
        """测试 qBittorrent 连接。

        放到后台线程执行并限制 5 秒超时：qB 没开时界面不会卡死，
        最多 5 秒就会提示连接失败。
        """
        host = self.input_qb_url.text().strip()
        user = self.input_qb_user.text().strip()
        pwd = self.input_qb_pwd.text()
        self.log_msg(f"正在测试 qBittorrent 连接: {host} ...（超时 {QB_TIMEOUT} 秒）", "INFO")

        def work():
            # 先用普通 requests 做一次硬超时预探测：qbittorrentapi 内部会重试多次，
            # 单靠它自身的 timeout 无法保证 5 秒内返回；预探测能确保 qB 没开时快速失败。
            try:
                requests.get(host, timeout=QB_TIMEOUT)
            except Exception as e:
                return False, f"无法连接 {host}（{QB_TIMEOUT} 秒内无响应）: {e}"
            try:
                client = make_qb_client(host, user, pwd)
                client.auth_log_in()
                return True, "已成功与本机的 qBittorrent 建立通信。"
            except Exception as e:
                return False, str(e)

        self._qb_test_thread = ConnectionTestThread(work, self)
        self._qb_test_thread.done_signal.connect(self._on_qb_test_done)
        self._qb_test_thread.start()

    def _on_qb_test_done(self, ok, msg):
        """qB 连接测试线程的回调：更新日志并弹出结果。"""
        if ok:
            self.log_msg("📡 已成功与本机的 qBittorrent 建立通信。", "SUCCESS")
            QMessageBox.information(self, "成功", msg)
        else:
            self.log_msg(f"无法连接 qBittorrent: {msg}", "ERROR")
            QMessageBox.critical(self, "错误", f"无法连接 qBittorrent（{QB_TIMEOUT} 秒内未响应）:\n{msg}")

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
    app.setQuitOnLastWindowClosed(True)
    window = PTUploaderFullGUI()
    window.init_all()
    window.show()
    rc = app.exec()
    # 退出前收尾：结束后台线程、隐藏托盘，避免 PyInstaller 单文件进程残留占用 .exe
    try:
        if hasattr(window, 'worker') and window.worker is not None and window.worker.isRunning():
            window.worker.stop(); window.worker.wait(3000)
    except Exception:
        pass
    try:
        if getattr(window, 'tray_icon', None) is not None: window.tray_icon.hide()
    except Exception:
        pass
    # 强制结束进程，确保 .exe 立即释放（否则单文件版可能残留进程导致无法覆盖）
    os._exit(rc if isinstance(rc, int) else 0)