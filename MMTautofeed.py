import sys, os, json, datetime, requests, zipfile, threading, shutil, subprocess, uuid, mimetypes, re

# =====================================================================
# 🌟 针对 Mac 双图标现象的强制合体优化
# =====================================================================
if sys.platform == 'darwin':
    try:
        from AppKit import NSBundle
        bundle = NSBundle.mainBundle()
        if bundle:
            info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
            if info and 'CFBundleName' not in info:
                info['CFBundleName'] = 'MMTautofeed'
    except ImportError:
        pass

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QGroupBox, QLabel, QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QLineEdit, QCheckBox, QScrollArea, QGridLayout, QFormLayout, QSpinBox, QHeaderView, QRadioButton, QButtonGroup, QMessageBox, QFileDialog, QDialog, QSizePolicy, QProgressBar, QListWidget, QAbstractItemView, QListView, QTreeView, QFrame)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QEvent
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QColor

# =====================================================================
# 1. 全局样式表定义区 (明暗双色，专业清爽风格)
# =====================================================================
STYLE_LIGHT = "QMainWindow, QDialog, QWidget { background-color: #f5f5f7; color: #1d1d1f; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; font-size: 13px; } QLabel, QCheckBox, QRadioButton { background: transparent; color: #1d1d1f; } QMessageBox { background-color: #ffffff; border-radius: 8px; border: 1px solid #d2d2d7; } QMessageBox QLabel { background-color: transparent; } QLineEdit, QSpinBox, QComboBox { background-color: #ffffff; color: #1d1d1f; border: 1px solid #c7c7cc; border-radius: 6px; padding: 6px 8px; min-height: 24px; } QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #007aff; } QComboBox::drop-down { border: none; width: 20px; } QComboBox QAbstractItemView, QListView { background-color: #ffffff; color: #1d1d1f; border: 1px solid #c7c7cc; outline: none; border-radius: 6px; } QListView::item { padding: 6px; } QListView::item:selected { background-color: #007aff; color: white; border-radius: 4px; } QListWidget { background-color: #ffffff; color: #1d1d1f; border: 1px solid #c7c7cc; border-radius: 8px; padding: 8px; outline: none; } QListWidget::item { background-color: #e5e5ea; border-radius: 4px; padding: 4px 8px; margin: 2px; color: #1d1d1f; } QListWidget::item:selected { background-color: #ff3b30; color: white; } QGroupBox { font-weight: bold; color: #1d1d1f; border: 1px solid #c7c7cc; border-radius: 8px; margin-top: 20px; padding-top: 15px; background-color: #ffffff; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 15px; top: 0px; color: #007aff; background-color: transparent; } QPushButton { background-color: #ffffff; color: #1d1d1f; border: 1px solid #c7c7cc; border-radius: 6px; padding: 6px 16px; font-weight: bold; } QPushButton:hover { background-color: #f0f0f5; border: 1px solid #8e8e93;} QPushButton:pressed { background-color: #e5e5ea; } QPushButton:disabled { background-color: #f5f5f7; color: #a1a1a6; border: 1px solid #e5e5ea; } QTableWidget { background-color: #ffffff; alternate-background-color: #f2f2f7; color: #1d1d1f; gridline-color: #d2d2d7; border: 1px solid #c7c7cc; border-radius: 8px; } QTableWidget::item:selected { background-color: #007aff; color: white; } QHeaderView::section { background-color: #f5f5f7; color: #86868b; padding: 8px 6px; border: none; border-right: 1px solid #c7c7cc; border-bottom: 1px solid #c7c7cc; font-weight: bold; } QTableCornerButton::section { background-color: #f5f5f7; } QTableWidget QComboBox { min-height: 16px; padding: 2px 4px; margin: 2px; } QTabWidget::pane { border: none; background: transparent; } QTabBar::tab { background: #e5e5ea; color: #86868b; padding: 8px 24px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; border: none; } QTabBar::tab:selected { background: #f5f5f7; color: #007aff; font-weight: bold; border-bottom: 2px solid #007aff; } QScrollArea { border: none; background-color: transparent; } #ScrollContent { background-color: transparent; } QTextEdit { background-color: #ffffff; color: #1d1d1f; border: 1px solid #c7c7cc; border-radius: 6px; padding: 6px; } QTextEdit#LogView, QTextEdit#BatchLogView { background-color: #1e1e1e; color: #34c759; font-family: Consolas, monospace; border: 1px solid #c7c7cc; border-radius: 8px; padding: 8px; } QProgressBar { border: 1px solid #c7c7cc; border-radius: 6px; text-align: center; color: #1d1d1f; background-color: #e5e5ea; font-weight: bold; height: 16px; } QProgressBar::chunk { background-color: #007aff; border-radius: 5px; } QScrollBar:vertical { border: none; background: transparent; width: 14px; margin: 0px; } QScrollBar::handle:vertical { background: #aeaeb2; border-radius: 7px; min-height: 20px; margin: 2px; } QScrollBar::handle:vertical:hover { background: #8e8e93; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; } QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; } QScrollBar:horizontal { border: none; background: transparent; height: 14px; margin: 0px; } QScrollBar::handle:horizontal { background: #aeaeb2; border-radius: 7px; min-width: 20px; margin: 2px; } QScrollBar::handle:horizontal:hover { background: #8e8e93; } QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; } QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }"
STYLE_DARK = "QMainWindow, QDialog { background-color: #1e1e1e; color: #e5e5ea; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; font-size: 13px; } QWidget { background-color: transparent; color: #e5e5ea; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; font-size: 13px; } QLabel, QCheckBox, QRadioButton { background: transparent; color: #e5e5ea; } QMessageBox { background-color: #2c2c2e; border-radius: 8px; border: 1px solid #48484a; } QMessageBox QLabel { background-color: transparent; } QLineEdit, QSpinBox, QComboBox { background-color: #121212; color: #ffffff; border: 1px solid #48484a; border-radius: 6px; padding: 6px 8px; min-height: 24px; } QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #0a84ff; background-color: #000000; } QLineEdit:disabled { background-color: #2c2c2e; color: #8e8e93; border: 1px solid #48484a; } QComboBox::drop-down { border: none; width: 20px; } QComboBox QAbstractItemView, QListView { background-color: #1e1e1e; color: #ffffff; border: 1px solid #636366; outline: none; border-radius: 6px; } QListView::item { padding: 8px; } QListView::item:selected { background-color: #0a84ff; color: white; border-radius: 4px; } QListWidget { background-color: #121212; color: #ffffff; border: 1px solid #48484a; border-radius: 8px; padding: 8px; outline: none; } QListWidget::item { background-color: #3a3a3c; border-radius: 4px; padding: 4px 8px; margin: 2px; color: #e5e5ea; } QListWidget::item:selected { background-color: #ff3b30; color: white; } QGroupBox { font-weight: bold; color: #ffffff; border: 1px solid #48484a; border-radius: 8px; margin-top: 20px; padding-top: 15px; background-color: #2c2c2e; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; left: 15px; top: 0px; color: #0a84ff; background-color: transparent; } QPushButton { background-color: #3a3a3c; color: #ffffff; border: 1px solid #5c5c5e; border-radius: 6px; padding: 6px 16px; font-weight: bold; } QPushButton:hover { background-color: #48484a; border: 1px solid #8e8e93; } QPushButton:pressed { background-color: #636366; } QPushButton:disabled { background-color: #1e1e1e; color: #636366; border: 1px solid #3a3a3c; } QTableWidget { background-color: #1e1e1e; alternate-background-color: #262628; color: #ffffff; gridline-color: #3a3a3c; border: 1px solid #48484a; border-radius: 8px; } QTableWidget::item:selected { background-color: #0a84ff; color: white; } QHeaderView::section { background-color: #2c2c2e; color: #86868b; padding: 8px 6px; border: none; border-right: 1px solid #48484a; border-bottom: 1px solid #48484a; font-weight: bold; } QTableCornerButton::section { background-color: #2c2c2e; } QTableWidget QComboBox { min-height: 16px; padding: 2px 4px; margin: 2px; } QTabWidget::pane { border: none; background: transparent; } QTabBar::tab { background: #2c2c2e; color: #86868b; padding: 8px 24px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; border: none; } QTabBar::tab:selected { background: #1e1e1e; color: #0a84ff; font-weight: bold; border-bottom: 2px solid #0a84ff; } QScrollArea { border: none; background-color: transparent; } #ScrollContent { background-color: transparent; } QTextEdit { background-color: #121212; color: #ffffff; border: 1px solid #636366; border-radius: 6px; padding: 8px; } QTextEdit#LogView, QTextEdit#BatchLogView { background-color: #0d0d0d; color: #30d158; font-family: Consolas, monospace; border: 1px solid #48484a; border-radius: 8px; padding: 8px; } QProgressBar { border: 1px solid #48484a; border-radius: 6px; text-align: center; color: #ffffff; background-color: #1e1e1e; font-weight: bold; height: 16px; } QProgressBar::chunk { background-color: #0a84ff; border-radius: 5px; } QScrollBar:vertical { border: none; background: transparent; width: 14px; margin: 0px; } QScrollBar::handle:vertical { background: #636366; border-radius: 7px; min-height: 20px; margin: 2px; } QScrollBar::handle:vertical:hover { background: #8e8e93; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; } QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; } QScrollBar:horizontal { border: none; background: transparent; height: 14px; margin: 0px; } QScrollBar::handle:horizontal { background: #636366; border-radius: 7px; min-width: 20px; margin: 2px; } QScrollBar::handle:horizontal:hover { background: #8e8e93; } QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; } QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }"

# 站点官方分类与标签配置
SITE_CATEGORIES = ["请选择分类...", "写真", "人像", "风光", "纪实", "杂志", "静物", "儿童", "超现实", "美食", "动物", "人文", "软件", "图书", "预设", "教程", "Special"]
GLOBAL_TAGS = ["OTHER", "GER", "KR", "US", "UK", "FR", "JP", "CN", "大师", "明星", "杂志", "RAW", "可商用", "古风", "COSER", "私房", "马格南", "时光机", "樱花妹"]

# =====================================================================
# 2. 自定义 UI 控件: 表格内支持多选的下拉复选框
# =====================================================================
class CheckableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent); self.setEditable(True); self.lineEdit().setReadOnly(True); self.lineEdit().installEventFilter(self)
        self.setModel(QStandardItemModel(self)); self.view().pressed.connect(self.handleItemPressed)
        self.view().window().setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)

    def eventFilter(self, obj, event):
        if obj == self.lineEdit() and event.type() == QEvent.Type.MouseButtonRelease: self.showPopup(); return True
        return super().eventFilter(obj, event)

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        item.setCheckState(Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked else Qt.CheckState.Checked)
        self.updateText()

    def set_items(self, items, checked_items=[]):
        self.clear()
        for text in items:
            item = QStandardItem(text); item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            item.setCheckState(Qt.CheckState.Checked if text in checked_items else Qt.CheckState.Unchecked); self.model().appendRow(item)
        self.updateText()

    def get_checked_items(self): return [self.model().item(i).text() for i in range(self.count()) if self.model().item(i).checkState() == Qt.CheckState.Checked]

    def updateText(self):
        checked = self.get_checked_items()
        self.lineEdit().setText(", ".join(checked) if checked else "未选择标签...")

# =====================================================================
# 3. 核心发种大动脉：后台多线程流水线引擎
# =====================================================================
class BatchWorkerThread(QThread):
    log_signal = pyqtSignal(str, str); progress_signal = pyqtSignal(int); cell_update_signal = pyqtSignal(int, int, str, str); finished_signal = pyqtSignal(int, int) 
    
    def __init__(self, mode, tasks, config, parent=None):
        super().__init__(parent); self.mode = mode; self.tasks = tasks; self.config = config; self.is_running = True
        self.tag_id_map = {
            "禁转": "1", "官方": "3", "大师": "8", "时光机": "11", "CN": "15",
            "JP": "16", "FR": "17", "UK": "18", "私房": "19", "COSER": "20",
            "US": "21", "KR": "22", "GER": "23", "古风": "24", "可商用": "25",
            "RAW": "26", "杂志": "27", "OTHER": "28", "马格南": "29", "明星": "30",
            "樱花妹": "31"
        }
        self._tags_fetched = False
        
    def stop(self): self.is_running = False
    def emit_log(self, msg, level="INFO"): self.log_signal.emit(msg, level)
    
    def run(self):
        total_tasks = len(self.tasks); success_count = 0
        if total_tasks == 0: self.finished_signal.emit(0, 0); return
        try: import torf
        except ImportError: self.emit_log("【环境报错】系统未安装 torf 库！请在终端执行: pip install torf", "ERROR"); self.finished_signal.emit(0, total_tasks); return

        torrent_dir = self.config['torrent_dir']; seeding_dir = self.config['seeding_dir'] 
        
        local_torrent_dir = os.path.join(torrent_dir, "Local_Made")
        pt_torrent_dir = os.path.join(torrent_dir, "PT_Official")
        os.makedirs(torrent_dir, exist_ok=True); os.makedirs(seeding_dir, exist_ok=True); os.makedirs(local_torrent_dir, exist_ok=True); os.makedirs(pt_torrent_dir, exist_ok=True)
        
        announce_url = self.config['pt_url'] + "announce.php"; use_zip = self.config['use_zip']
        upload_form_url = f"{self.config['pt_url']}upload.php"
        upload_submit_url = f"{self.config['pt_url']}takeupload.php"

        if self.mode in ['publish', 'auto'] and not self._tags_fetched:
            self.emit_log("🌐 [网络阶段] 正在尝试抓取站点最新标签库进行核对...", "INFO")
            try:
                tu_resp = requests.get(upload_form_url, headers={"Cookie": self.config['cookie']}, timeout=15)
                matches = re.findall(r'name="tags\[\d+\]\[\]"\s+value="(\d+)"\s*/>([^<]+)</label>', tu_resp.text, re.I)
                d_map = {}
                for val, name in matches:
                    if val.isdigit() and name: d_map[name.strip()] = val
                
                if d_map:
                    self.tag_id_map.update(d_map)
                    self.emit_log(f"✅ 标签字典核对并同步成功！(共校验 {len(self.tag_id_map)} 个标签)", "SUCCESS")
                else: 
                    self.emit_log("⚠️ 网页抓取标签字典失败，将启用底层内置安全密码本！", "WARNING")
            except Exception as e: self.emit_log(f"标签库同步网络异常，启用内置密码本: {e}", "WARNING")
            self._tags_fetched = True

        for idx, task in enumerate(self.tasks):
            if not self.is_running: self.emit_log("🛑 任务已被中止！", "WARNING"); break
            row, std_name, folder_path = task['row'], task['std_name'], task['folder_path']
            base_prog = (idx / total_tasks) * 100; task_weight = 100 / total_tasks
            def set_p(percent): self.progress_signal.emit(int(base_prog + (percent / 100.0) * task_weight))
            
            self.emit_log(f"▶️ [开始处理] 正在执行第 {idx+1}/{total_tasks} 项任务: {std_name}", "INFO")
            set_p(5)
            
            if self.mode in ['make', 'auto']:
                if not os.path.exists(folder_path): self.cell_update_signal.emit(row, 8, "❌ 路径失效", "#ff3b30"); set_p(100); continue
                self.cell_update_signal.emit(row, 8, "制作中...", "#ff9500")
                try:
                    target_path = folder_path
                    if use_zip:
                        set_p(15)
                        zip_name = f"{std_name}.zip"; zip_path = os.path.join(seeding_dir, zip_name)
                        self.emit_log(f"📦 [文件打包] 正在将资源打包为 ZIP: {zip_name} ...", "INFO")
                        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                            for root, _, files in os.walk(folder_path):
                                for f in files:
                                    if not self.is_running: raise InterruptedError()
                                    zipf.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), os.path.join(folder_path, '..')))
                        target_path = zip_path
                        self.emit_log(f"✅ ZIP 打包完毕！", "SUCCESS")
                        
                    set_p(35)
                    self.emit_log(f"⚙️ [种子生成] 正在计算文件哈希，制作 .torrent ...", "INFO")
                    t = torf.Torrent(path=target_path, trackers=[announce_url], private=True); t.generate()
                    
                    out_file = os.path.join(local_torrent_dir, f"{std_name}{'.zip' if use_zip else ''}.torrent")
                    t.write(out_file)
                    
                    self.cell_update_signal.emit(row, 8, "✅ 已制种", "#34c759")
                    if self.mode == 'make': success_count += 1
                except Exception as e:
                    self.cell_update_signal.emit(row, 8, "❌ 生成失败", "#ff3b30"); self.emit_log(f"制种出错 ({std_name}): {e}", "ERROR"); set_p(100); continue
                set_p(50 if self.mode == 'auto' else 100)

            if self.mode in ['publish', 'auto']:
                set_p(55 if self.mode == 'auto' else 10)
                img_url = ""
                
                if task['thumb_path'] and os.path.exists(task['thumb_path']):
                    self.cell_update_signal.emit(row, 9, "⬆️ 上传图片...", "#ff9500"); self.emit_log(f"🖼️ [图床通信] 开始上传展示封面...", "INFO")
                    try:
                        mime_type = mimetypes.guess_type(task['thumb_path'])[0] or 'image/jpeg'
                        for retry in range(3):
                            try:
                                with open(task['thumb_path'], 'rb') as f:
                                    files = {"file": (os.path.basename(task['thumb_path']), f, mime_type)}; headers = {"Accept": "application/json"}
                                    if self.config['image_token']: headers["Authorization"] = f"Bearer {self.config['image_token']}"
                                    img_res = requests.post(self.config['image_upload_api'], headers=headers, files=files, timeout=120)
                                if img_res.status_code in [200, 201]:
                                    try:
                                        img_data = img_res.json()
                                        img_url = img_data.get('data', {}).get('links', {}).get('url', '') or img_data.get('data', {}).get('url', '') or img_data.get('image', {}).get('url', '')
                                        self.emit_log(f"✅ 图床上传成功，获取直链: {img_url}", "SUCCESS")
                                    except: pass
                                else: 
                                    self.emit_log(f"❌ 图床拒绝上传! HTTP状态码: {img_res.status_code} | 服务器返回拦截信息: {img_res.text[:150]}", "ERROR")
                                break 
                            except requests.exceptions.Timeout:
                                self.emit_log(f"⚠️ 图床超时，发起重试 {retry+1}/3", "WARNING")
                                if retry == 2: raise
                    except Exception as e: 
                        self.emit_log(f"❌ 图床网络通讯异常，详细错误: {e}", "ERROR")
                
                set_p(65 if self.mode == 'auto' else 30)
                
                cat_id = self.config['category_map'].get(task['category'], "401")
                mode_4_cats = ["401", "402", "403", "404", "416", "415", "414", "413", "412", "411", "405"]
                cat_mode = "4" if cat_id in mode_4_cats else "5"
                tag_param_name = f"tags[{cat_mode}][]"
                
                bbcode_img = f"[img]{img_url}[/img]" if img_url else (f"[img]{task['thumb_path']}[/img]" if task['thumb_path'] and "http" in str(task['thumb_path']) else "[img]图床未配置或上传失败[/img]")
                disclaimer = "\n\n[quote]本站不是一个以盈利为目的的站点，所有资源均来自本人购买实体摄影集拍摄和网上搜集而来，任何涉及商业或盈利目的均不可使用本站资源，否则后果自负，本站将不对本站的任何内容负任何法律责任!所有下载内容仅供测试宽带使用，测试后请立即删除。如您下载本站任何资源，即代表您接受本声明及条款。本站支持正版，请购买正版!如版权持有人发现本站有任何侵犯版权持有人权益的资源，请通知本站管理人员予以删除![/quote]"
                full_descr = f"{task['intro']}\n\n{bbcode_img}{disclaimer}" 
                
                data_payload = {"name": std_name, "type": cat_id, "descr": full_descr}
                if self.config.get('anonymous', True): data_payload['uplver'] = 'yes'
                post_data = list(data_payload.items())
                
                self.emit_log("🔖 [表单组装] 正在组装分类与标签数据...", "INFO")
                final_tags = ["官方", "禁转"] + task['tag_names']
                for t_name in set(final_tags): 
                    if t_name in self.tag_id_map: 
                        post_data.append((tag_param_name, self.tag_id_map[t_name]))
                        self.emit_log(f"   -> 识别到标签 [ {t_name} ]，转化为参数 {tag_param_name}={self.tag_id_map[t_name]}", "SUCCESS")
                    else: 
                        post_data.append((tag_param_name, t_name))
                        self.emit_log(f"   -> ⚠️ 未找到标签 [ {t_name} ] 的 ID，直接使用文本传值。", "WARNING")

                if self.config['test_mode']:
                    log_detail = (
                        f"【测试模式】发种拦截！为避免刷屏，以下为本行专属打包数据:\n"
                        f"📌 最终标题: {std_name}\n"
                        f"📂 站点分类ID: {cat_id}\n"
                        f"🔖 标签参数名: {tag_param_name}\n"
                        f"🏷️ 附带真实标签: {final_tags}\n"
                        f"📝 完整组装简介 (含图床代码):\n"
                        f"----------------------------------------\n"
                        f"{full_descr}\n"
                        f"----------------------------------------"
                    )
                    self.emit_log(log_detail, "INFO")
                    self.cell_update_signal.emit(row, 9, "✅ 模拟完毕", "#34c759"); success_count += 1; set_p(100); continue

                torrent_path = os.path.join(local_torrent_dir, f"{std_name}.torrent")
                if not os.path.exists(torrent_path): torrent_path = os.path.join(local_torrent_dir, f"{std_name}.zip.torrent")
                if not os.path.exists(torrent_path): self.cell_update_signal.emit(row, 9, "❌ 未制作种子", "#ff3b30"); set_p(100); continue
                
                self.cell_update_signal.emit(row, 9, "🚀 推送中...", "#ff9500"); set_p(80 if self.mode == 'auto' else 60)
                
                try:
                    self.emit_log(f"🌐 [网络推送] 正在向 PT 站点发送表单数据...", "INFO")
                    with open(torrent_path, "rb") as file_stream:
                        files = {'file': (os.path.basename(torrent_path), file_stream, 'application/x-bittorrent')}
                        headers = {"User-Agent": "MMTautofeed-Client/v1.0.1", "Cookie": self.config['cookie']}
                        resp = requests.post(upload_submit_url, headers=headers, data=post_data, files=files, timeout=25, allow_redirects=True)
                        
                    match = re.search(r'id(?:=|%3D)(\d+)', resp.url)
                    if resp.status_code in [200, 302] and match:
                        torrent_id = match.group(1)
                        self.cell_update_signal.emit(row, 9, "✅ 发布成功", "#34c759"); self.emit_log(f"🎉【发布成功】成功获取站点新分配的种子ID: {torrent_id}", "SUCCESS")
                        success_count += 1; set_p(90 if self.mode == 'auto' else 80)
                        
                        if self.config['add_to_qb']:
                            dl_url = f"{self.config['pt_url']}download.php?id={torrent_id}"
                            self.emit_log(f"📥 [种子拉取] 正在请求包含个人 Passkey 的官方 Tracker 种子...", "INFO")
                            dl_resp = requests.get(dl_url, headers=headers, timeout=15)
                            if dl_resp.status_code == 200 and len(dl_resp.content) > 100:
                                final_torrent_path = os.path.join(pt_torrent_dir, f"[PT]{std_name}.torrent")
                                with open(final_torrent_path, "wb") as tf: tf.write(dl_resp.content)
                                self.emit_log(f"✅ 官方种子拉取成功！存入专属分仓: {final_torrent_path}", "SUCCESS")
                            else: 
                                self.emit_log("拉取官方种子失败，降级使用本地原始种子推送给 qB", "WARNING")
                                final_torrent_path = torrent_path
                                
                            set_p(95 if self.mode == 'auto' else 90)
                            save_dir = os.path.abspath(seeding_dir if use_zip else os.path.dirname(folder_path))
                            self.push_to_qb(final_torrent_path, save_dir)
                    else:
                        if 'login.php' in resp.url and not match:
                            self.cell_update_signal.emit(row, 9, "❌ Cookie失效", "#ff3b30"); self.emit_log(f"🚨 被重定向至登录页，Cookie失效或权限不足！", "ERROR")
                        else:
                            self.cell_update_signal.emit(row, 9, f"⚠️ 频控或异常", "#ff3b30"); self.emit_log(f"🚨 页面未返回有效的种子 ID。可能必填项为空或触发了站点防刷机制。", "ERROR")
                            
                except Exception as e:
                    self.cell_update_signal.emit(row, 9, "断网/超时", "#ff3b30"); self.emit_log(f"网络连接断开: {e}", "ERROR")
                set_p(100)
            
            if idx < total_tasks - 1 and self.config.get('seed_delay', 3) > 0 and self.mode in ['publish', 'auto']:
                delay_sec = self.config['seed_delay']
                self.emit_log(f"⏳ 触发发种限流保护，等待 {delay_sec} 秒后处理下一个任务...", "INFO")
                for wait_sec in range(delay_sec, 0, -1):
                    if not self.is_running: break
                    self.emit_log(f"⏳ 倒计时: {wait_sec} 秒", "INFO")
                    self.msleep(1000) 
                
        self.progress_signal.emit(100); self.finished_signal.emit(success_count, total_tasks)

    def push_to_qb(self, torrent_path, save_dir):
        try:
            import qbittorrentapi
            client = qbittorrentapi.Client(host=self.config['qb_url'], username=self.config['qb_user'], password=self.config['qb_pwd'])
            client.auth_log_in()
            client.torrents_add(torrent_files=torrent_path, save_path=save_dir, is_paused=False, use_auto_torrent_management=False)
            self.emit_log(f"📡 [qB做种] 任务已成功推送到 qBittorrent 客户端！\n   -> 文件挂载路径: {save_dir}", "SUCCESS")
        except Exception as e: self.emit_log(f"⚠️ qB 客户端无法连接: {e}", "WARNING")

# =====================================================================
# 4. 弹窗类：添加/编辑预设 + 预设管理
# =====================================================================
class AddPresetDialog(QDialog):
    def __init__(self, parent=None, font_size=10):
        super().__init__(parent); self.setWindowTitle("添加 / 编辑预设方案"); self.resize(980, 700)
        layout = QVBoxLayout(self); form_layout = QFormLayout(); form_layout.setSpacing(14) 
        self.input_preset_name = QLineEdit(); form_layout.addRow("预设名称*:", self.input_preset_name)
        self.input_photographer = QLineEdit(); form_layout.addRow("摄影师:", self.input_photographer)
        self.input_model = QLineEdit(); form_layout.addRow("主角/模特:", self.input_model)
        
        lbl_h = QLabel("💡 提示：至少填写【摄影师】或【主角/模特】之一才能正确生成名字"); lbl_h.setStyleSheet("color: #ff3b30; font-size: 12px;")
        lbl_h.setContentsMargins(0, 0, 0, 0); form_layout.addRow("", lbl_h)
        
        self.input_intro = QTextEdit(); self.input_intro.setMinimumHeight(150); self.input_intro.setStyleSheet(f"font-size: {font_size}px;")
        
        w_intro = QWidget(); h_intro = QHBoxLayout(w_intro); h_intro.setContentsMargins(0, 0, 0, 0)
        h_intro.addWidget(QLabel("统一简介:")); h_intro.addStretch(); h_intro.addWidget(QLabel("字号调节:"))
        self.spin_intro_font = QSpinBox(); self.spin_intro_font.setRange(9, 24); self.spin_intro_font.setValue(font_size)
        self.spin_intro_font.valueChanged.connect(lambda v: self.input_intro.setStyleSheet(f"font-size: {v}px;"))
        h_intro.addWidget(self.spin_intro_font)
        
        form_layout.addRow(w_intro)
        form_layout.addRow(self.input_intro)
        
        self.combo_category = QComboBox(); self.combo_category.addItems(SITE_CATEGORIES); form_layout.addRow("默认分类:", self.combo_category)
        layout.addLayout(form_layout)
        
        group_tags = QGroupBox("默认附加标签 (已隐去底层强制绑定的 官方、禁转)"); tags_layout = QGridLayout(); tags_layout.setSpacing(10); self.checkboxes = {}
        for i, tag in enumerate(GLOBAL_TAGS):
            cb = QCheckBox(tag); self.checkboxes[tag] = cb; tags_layout.addWidget(cb, i // 5, i % 5)
        group_tags.setLayout(tags_layout); layout.addWidget(group_tags)
        
        layout.addStretch()
        btn_layout = QHBoxLayout(); btn_layout.addStretch()
        btn_save = QPushButton("💾 保存设定"); btn_save.setStyleSheet("background-color: #34c759; color: white;"); btn_save.clicked.connect(self.accept) 
        btn_cancel = QPushButton("取消"); btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_save); btn_layout.addWidget(btn_cancel); layout.addLayout(btn_layout)

    def get_font_size(self):
        return self.spin_intro_font.value()

    def set_data(self, data):
        self.input_preset_name.setText(data.get("name", "")); self.input_photographer.setText(data.get("photographer", "")); self.input_model.setText(data.get("model", "")); self.input_intro.setText(data.get("intro", "")); self.combo_category.setCurrentText(data.get("category", "请选择分类..."))
        for tag, cb in self.checkboxes.items(): cb.setChecked(tag in data.get("tags", []))

    def get_data(self):
        return {"name": self.input_preset_name.text().strip(), "photographer": self.input_photographer.text().strip(), "model": self.input_model.text().strip(), "intro": self.input_intro.toPlainText().strip(), "category": self.combo_category.currentText(), "tags": [t for t, c in self.checkboxes.items() if c.isChecked()]}

class ManagePresetsDialog(QDialog):
    def __init__(self, parent_main_window):
        super().__init__(parent_main_window); self.parent_win = parent_main_window; self.setWindowTitle("预设配置管理"); self.resize(980, 600)
        layout = QVBoxLayout(self); h_top = QHBoxLayout()
        btn_add = QPushButton("十 新增一条预设"); btn_add.setStyleSheet("background-color: #007aff; color: white; border: none; padding: 6px;"); btn_add.clicked.connect(self.open_add_preset)
        btn_refresh = QPushButton("🔄 刷新表格"); btn_refresh.clicked.connect(self.refresh_table)
        h_top.addWidget(btn_add); h_top.addWidget(btn_refresh); h_top.addStretch(); layout.addLayout(h_top)
        
        self.table = QTableWidget(0, 8); self.table.setHorizontalHeaderLabels(["模板名称", "摄影师", "模特", "简介", "分类", "标签", "复制", "操作"])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(1, 90)
        self.table.setColumnWidth(2, 90)
        self.table.setColumnWidth(4, 70)
        self.table.setColumnWidth(5, 100)
        self.table.setColumnWidth(6, 60)
        self.table.setColumnWidth(7, 90)
        self.table.verticalHeader().setDefaultSectionSize(36)
        layout.addWidget(self.table)
        
        h_bottom = QHBoxLayout(); h_bottom.addStretch(); btn_close = QPushButton("关闭管理面板"); btn_close.clicked.connect(self.accept); h_bottom.addWidget(btn_close); layout.addLayout(h_bottom)
        self.refresh_table()

    def open_add_preset(self):
        dialog = AddPresetDialog(self, font_size=self.parent_win.preset_font_size); dialog.setStyleSheet(self.parent_win.styleSheet())
        if dialog.exec(): 
            d = dialog.get_data()
            if not d["name"]: return QMessageBox.warning(self, "错误", "名称不能为空！")
            self.parent_win.presets_data.append(d); self.parent_win.save_presets(); self.refresh_table(); self.parent_win.refresh_main_preset_combo()
            self.parent_win.preset_font_size = dialog.get_font_size(); self.parent_win.save_config(silent=True)

    def edit_preset(self, row):
        dialog = AddPresetDialog(self, font_size=self.parent_win.preset_font_size); dialog.setStyleSheet(self.parent_win.styleSheet()); dialog.set_data(self.parent_win.presets_data[row])
        if dialog.exec(): 
            nd = dialog.get_data()
            if not nd["name"]: return
            self.parent_win.presets_data[row] = nd; self.parent_win.save_presets(); self.refresh_table(); self.parent_win.refresh_main_preset_combo()
            self.parent_win.preset_font_size = dialog.get_font_size(); self.parent_win.save_config(silent=True)

    def copy_preset(self, row):
        new_data = self.parent_win.presets_data[row].copy()
        new_data["name"] = new_data["name"] + "-副本"
        self.parent_win.presets_data.append(new_data)
        self.parent_win.save_presets()
        self.refresh_table()
        self.parent_win.refresh_main_preset_combo()
        self.parent_win.log_msg(f"已成功复制生成预设副本：{new_data['name']}", "SUCCESS")

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
        if QMessageBox.question(self, '确认删除', "确定永久删除此条预设？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            del self.parent_win.presets_data[row]; self.parent_win.save_presets(); self.refresh_table(); self.parent_win.refresh_main_preset_combo()

class TagsSelectDialog(QDialog):
    def __init__(self, current_tags, parent=None):
        super().__init__(parent); self.setWindowTitle("选择发种标签"); self.resize(400, 250); layout = QVBoxLayout(self)
        lbl = QLabel("💡 提示：系统将在发包时自动在后台附加【官方】与【禁转】标签，此处无需勾选。"); lbl.setStyleSheet("color: #e65100; font-size: 12px; margin-bottom: 10px;"); layout.addWidget(lbl)
        grid = QGridLayout(); self.cbs = {}
        for i, t in enumerate(SITE_TAGS):
            cb = QCheckBox(t); cb.setChecked(t in current_tags); self.cbs[t] = cb; grid.addWidget(cb, i // 4, i % 4)
        layout.addLayout(grid); layout.addStretch()
        btn_ok = QPushButton("确认选择"); btn_ok.setStyleSheet("background-color: #007aff; color: white;"); btn_ok.clicked.connect(self.accept)
        layout.addWidget(btn_ok, alignment=Qt.AlignmentFlag.AlignRight)
    def get_selected(self): return [t for t, cb in self.cbs.items() if cb.isChecked()]
# =====================================================================
# 5. 主程序 GUI 与核心信号槽装载
# =====================================================================
class PTUploaderFullGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MMTautofeed批量发种工具 (v1.0.1)")
        self.resize(1300, 880) 
        self.init_directories()
        
        self.current_theme = "light"
        self.hint_labels = []
        self.presets_data = []
        self.clean_keywords = []
        self.clean_exts = []
        self.preset_font_size = 10 
        
        self.load_presets()
        
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.tab_batch = QWidget()
        self.tab_settings = QWidget()
        self.tab_log = QWidget()
        
        self.tabs.addTab(self.tab_batch, "⚡ 批量上传流水线")
        self.tabs.addTab(self.tab_settings, "⚙️ 偏好设置")
        self.tabs.addTab(self.tab_log, "🖥️ 运行日志监控")

        self.setup_log_tab()
        self.setup_batch_upload_tab()
        self.setup_settings_tab()
        self.load_config()
        
        self.log_msg(f"✅ GUI 界面渲染完成，核心功能已就绪！", "SUCCESS")

    def get_abs_path(self, path):
        path = path.strip()
        if not path: return self.base_dir
        path = path.lstrip('\\/')
        if path.startswith('./') or path.startswith('.\\'): path = path[2:]
        if not os.path.isabs(path): return os.path.normpath(os.path.join(self.base_dir, path))
        return os.path.normpath(path)

    def init_directories(self):
        if getattr(sys, 'frozen', False):
            if sys.platform == 'darwin':
                self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(sys.executable))))
            else:
                self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            
        os.makedirs(os.path.join(self.base_dir, 'logs'), exist_ok=True)

    def log_msg(self, msg, level="INFO"):
        time_str = datetime.datetime.now().strftime("%H:%M:%S")
        log_line = f"{time_str} | {level} | {msg}"
        if hasattr(self, 'log_view'): 
            self.log_view.append(log_line)
            self.log_view.verticalScrollBar().setValue(self.log_view.verticalScrollBar().maximum())
        if hasattr(self, 'batch_log'): 
            self.batch_log.append(log_line)
            self.batch_log.verticalScrollBar().setValue(self.batch_log.verticalScrollBar().maximum())
        QApplication.processEvents()
        
        try:
            log_file = os.path.join(self.base_dir, 'logs', f"mmtauto_{datetime.datetime.now().strftime('%Y%m%d')}.log")
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_line + '\n')
        except Exception: pass

    def load_presets(self):
        preset_file = os.path.join(self.base_dir, 'presets.json')
        if os.path.exists(preset_file):
            try:
                with open(preset_file, 'r', encoding='utf-8') as f: self.presets_data = json.load(f)
            except Exception: pass

    def save_presets(self):
        try:
            with open(os.path.join(self.base_dir, 'presets.json'), 'w', encoding='utf-8') as f: 
                json.dump(self.presets_data, f, indent=4, ensure_ascii=False)
        except Exception as e: self.log_msg(f"写入预设文件异常: {e}", "ERROR")

    def apply_theme(self, theme_mode):
        self.current_theme = theme_mode
        self.setStyleSheet(STYLE_DARK if theme_mode == "dark" else STYLE_LIGHT)
        self.refresh_hint_colors()

    def theme_changed(self): 
        self.apply_theme("dark" if self.combo_theme.currentIndex() == 1 else "light")

    def save_config(self, silent=False):
        parse_mode = "simple"
        if self.rb_none.isChecked(): parse_mode = "none"
        elif self.rb_full.isChecked(): parse_mode = "full"
        
        config_data = {
            "theme": "dark" if self.combo_theme.currentIndex() == 1 else "light",
            "pt_url": self.input_pt_url.text(), 
            "cookie": self.input_cookie.text(), 
            "api_key": self.input_api_key.text(),
            "torrent_path": self.input_t_path.text(), 
            "seeding_path": self.input_s_path.text(),
            "image_email": self.input_img_email.text(), 
            "image_pwd": self.input_img_pwd.text(), 
            "image_token": self.input_img_token.text(),
            "image_upload_api": self.input_img_upload_url.text(), 
            "image_token_url": self.input_img_token_url.text(), 
            "seed_delay": self.spin_delay.value(), 
            "qb_url": self.input_qb_url.text(), 
            "qb_user": self.input_qb_user.text(), 
            "qb_pwd": self.input_qb_pwd.text(),
            "qb_auto_add": self.chk_qb_add.isChecked(), 
            "anonymous": self.cb_batch_anon.isChecked(), 
            "parse_mode": parse_mode,
            "clean_keywords": [self.list_kw.item(i).text() for i in range(self.list_kw.count())],
            "clean_exts": [self.list_ext.item(i).text() for i in range(self.list_ext.count())],
            "preset_font_size": self.preset_font_size
        }
        try:
            with open(os.path.join(self.base_dir, 'config.json'), 'w', encoding='utf-8') as f: 
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            if not silent:
                QMessageBox.information(self, "操作成功", "设置已保存！")
                self.log_msg("偏好设置保存成功", "SUCCESS")
        except Exception as e: self.log_msg(f"配置保存失败: {e}", "ERROR")

    def load_config(self):
        config_file = os.path.join(self.base_dir, 'config.json')
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f: config_data = json.load(f)
                theme = config_data.get("theme", "light")
                self.combo_theme.setCurrentIndex(1 if theme == "dark" else 0)
                self.apply_theme(theme)
                
                self.input_pt_url.setText(config_data.get("pt_url") or "https://www.momentpt.top/")
                self.input_cookie.setText(config_data.get("cookie", ""))
                self.input_api_key.setText(config_data.get("api_key", ""))
                self.input_t_path.setText(config_data.get("torrent_path") or "./torrents")
                self.input_s_path.setText(config_data.get("seeding_path") or "./seeding")
                
                self.input_img_email.setText(config_data.get("image_email", ""))
                self.input_img_pwd.setText(config_data.get("image_pwd", ""))
                self.input_img_token.setText(config_data.get("image_token", ""))
                self.input_img_upload_url.setText(config_data.get("image_upload_api") or "https://img.momentpt.top/api/v1/upload")
                self.input_img_token_url.setText(config_data.get("image_token_url") or "https://img.momentpt.top/api/v1/tokens")
                
                self.spin_delay.setValue(config_data.get("seed_delay", 3))
                
                self.input_qb_url.setText(config_data.get("qb_url") or "http://127.0.0.1:8080")
                self.input_qb_user.setText(config_data.get("qb_user") or "admin")
                self.input_qb_pwd.setText(config_data.get("qb_pwd", ""))
                
                self.chk_qb_add.setChecked(config_data.get("qb_auto_add", True))
                self.cb_batch_anon.setChecked(config_data.get("anonymous", True))
                
                p_mode = config_data.get("parse_mode", "simple")
                if p_mode == "none": self.rb_none.setChecked(True)
                elif p_mode == "full": self.rb_full.setChecked(True)
                else: self.rb_simple.setChecked(True)
                
                self.list_kw.clear(); self.list_kw.addItems(config_data.get("clean_keywords", []))
                self.list_ext.clear(); self.list_ext.addItems(config_data.get("clean_exts", []))
                self.preset_font_size = config_data.get("preset_font_size", 10)
            except Exception as e: self.log_msg(f"读取配置文件失败: {e}", "ERROR")
        else:
            self.apply_theme("light")
            self.input_pt_url.setText("https://www.momentpt.top/")
            self.input_img_upload_url.setText("https://img.momentpt.top/api/v1/upload")
            self.input_img_token_url.setText("https://img.momentpt.top/api/v1/tokens")
            self.input_t_path.setText("./torrents")
            self.input_s_path.setText("./seeding")
            self.spin_delay.setValue(3)
            self.input_qb_url.setText("http://127.0.0.1:8080")
            self.input_qb_user.setText("admin")
            self.chk_qb_add.setChecked(True)
            self.rb_simple.setChecked(True)
            self.preset_font_size = 10

    def browse_folder(self, target_line_edit):
        folder_path = QFileDialog.getExistingDirectory(self, "选择文件夹", self.base_dir)
        if folder_path: target_line_edit.setText(folder_path)

    def create_hint_label(self, text, role="info"): 
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setContentsMargins(0, 0, 0, 0)
        self.hint_labels.append((lbl, role))
        return lbl

    def refresh_hint_colors(self):
        d = self.current_theme == "dark"
        for l, r in self.hint_labels: 
            l.setStyleSheet(f"color: {'#ff9500' if d and r=='warning' else '#0a84ff' if d and r=='primary' else '#ff3b30' if not d and r=='warning' else '#007aff' if not d and r=='primary' else '#8e8e93'}; font-size: 12px; background: transparent;")

    def add_cleanup_item(self, line_edit, list_widget):
        txt = line_edit.text().strip()
        if txt and not list_widget.findItems(txt, Qt.MatchFlag.MatchExactly): 
            list_widget.addItem(txt); line_edit.clear()

    def del_cleanup_item(self, list_widget):
        for item in list_widget.selectedItems(): list_widget.takeItem(list_widget.row(item))

    def clear_all_cleanup_items(self, list_widget): 
        list_widget.clear()

    def batch_rename_files(self):
        if self.table.rowCount() == 0: 
            return QMessageBox.warning(self, "提示", "请先点击【添加文件夹】导入需要处理的内容。")
        reply = QMessageBox.question(self, "去广告重命名", "此操作会将目标文件夹内的图片和视频重命名为纯数字（1.jpg 等），并且操作不可逆转！是否继续？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes: return
            
        exts = ('.jpg', '.jpeg', '.png', '.mp4', '.mkv', '.avi', '.mov', '.ts')
        renamed_total = 0
        self.log_msg("开始执行序列化去广告重命名...", "INFO")
        
        for row in range(self.table.rowCount()):
            f_item = self.table.item(row, 3) 
            if not f_item or not os.path.exists(f_item.text()): continue
                
            target_files = sorted([os.path.join(root, file) for root, _, files in os.walk(f_item.text()) for file in files if file.lower().endswith(exts)])
            temp_files = []
            
            for fp in target_files:
                temp_name = os.path.join(os.path.dirname(fp), f"temp_{uuid.uuid4().hex}{os.path.splitext(fp)[1]}")
                os.rename(fp, temp_name)
                temp_files.append(temp_name)
                
            for i, tp in enumerate(temp_files):
                os.rename(tp, os.path.join(os.path.dirname(tp), f"{i+1}{os.path.splitext(tp)[1]}"))
                renamed_total += 1
                
        self.log_msg(f"重命名执行完毕，共处理 {renamed_total} 个文件", "SUCCESS")
        QMessageBox.information(self, "完成", f"重命名完毕，共处理了 {renamed_total} 个文件。")

    def open_manage_presets(self): 
        dialog = ManagePresetsDialog(self)
        dialog.setStyleSheet(self.styleSheet())
        dialog.exec()

    def refresh_main_preset_combo(self):
        cur = self.preset_combo.currentText()
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("请选择预设模板...")
        for p in self.presets_data: 
            self.preset_combo.addItem(p["name"])
        
        idx = self.preset_combo.findText(cur)
        if idx >= 0: self.preset_combo.setCurrentIndex(idx)
        self.preset_combo.blockSignals(False)

    def preset_changed(self):
        p_name = self.preset_combo.currentText()
        for p in self.presets_data:
            if p["name"] == p_name:
                tags_str = ", ".join(p.get("tags", []))
                info_text = (f"📸 摄影师：{p.get('photographer', '未配置')}   |   👤 主角/模特：{p.get('model', '未配置')}\n"
                             f"🎯 默认分类：{p.get('category', '默认')}   |   🏷️ 附带标签：{tags_str}\n"
                             f"📝 简介内容：{p.get('intro', '无')}")
                self.preset_info_label.setText(info_text)
                break
        if p_name == "请选择预设模板...": 
            self.preset_info_label.setText("💡 请在左侧选择一个全局默认预设，作为后续新增资源的初始配置。")

    def batch_add_folder(self):
        dialog = QFileDialog(self, "选择存放作品的多个文件夹 (可按Ctrl多选)", self.base_dir)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        
        tree = dialog.findChild(QTreeView)
        if tree:
            tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_folders = dialog.selectedFiles()
            for path in selected_folders:
                self.add_single_folder_to_table(os.path.abspath(path))

    def add_single_folder_to_table(self, folder_path):
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        self.table.setItem(row, 0, QTableWidgetItem(os.path.basename(folder_path)))
        self.table.setItem(row, 1, QTableWidgetItem("（等待扫描中...）"))
        
        combo_preset = QComboBox()
        combo_preset.addItem("无预设")
        for p in self.presets_data: combo_preset.addItem(p["name"])
        global_preset = self.preset_combo.currentText()
        if global_preset != "请选择预设模板...":
            combo_preset.setCurrentText(global_preset)
        combo_preset.currentIndexChanged.connect(lambda idx, r=row: self.on_row_preset_changed(r))
        self.table.setCellWidget(row, 2, combo_preset)
        
        self.table.setItem(row, 3, QTableWidgetItem(folder_path))
        self.table.setItem(row, 4, QTableWidgetItem("未知"))
        self.table.setItem(row, 5, QTableWidgetItem("未知"))
        
        combo_cat = QComboBox()
        combo_cat.addItems(SITE_CATEGORIES)
        self.table.setCellWidget(row, 6, combo_cat)
        
        combo_tags = CheckableComboBox()
        combo_tags.set_items(GLOBAL_TAGS)
        self.table.setCellWidget(row, 7, combo_tags)
        
        self.table.setItem(row, 8, QTableWidgetItem("未制作"))
        self.table.setItem(row, 9, QTableWidgetItem("待处理"))
        
        btn_del = QPushButton("移除")
        btn_del.setStyleSheet("background-color: #ff3b30; color: white; border: none; padding: 2px 4px; border-radius: 4px;")
        btn_del.clicked.connect(self.remove_table_row)
        self.table.setCellWidget(row, 10, btn_del)

    def remove_table_row(self):
        btn = self.sender()
        if btn:
            idx = self.table.indexAt(btn.pos())
            if idx.isValid(): self.table.removeRow(idx.row())

    def on_row_preset_changed(self, row):
        self.table.blockSignals(True)
        try:
            preset_name = self.table.cellWidget(row, 2).currentText()
            preset = next((p for p in self.presets_data if p["name"] == preset_name), {})
            
            if cw := self.table.cellWidget(row, 6): 
                cw.setCurrentText(preset.get("category", "写真"))
            if tw := self.table.cellWidget(row, 7): 
                tw.set_items(GLOBAL_TAGS, preset.get("tags", []))
        finally:
            self.table.blockSignals(False)
        self.on_table_cell_changed(row, 0)

    def on_table_cell_changed(self, row, col):
        if col in [0, 4, 5]:
            self.table.blockSignals(True)
            try:
                preset_name = self.table.cellWidget(row, 2).currentText() if self.table.cellWidget(row, 2) else ""
                preset = next((p for p in self.presets_data if p["name"] == preset_name), {})
                
                f_name = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
                amount = self.table.item(row, 4).text() if self.table.item(row, 4) else ""
                year = self.table.item(row, 5).text() if self.table.item(row, 5) else ""
                
                parse_mode = "simple"
                if self.rb_none.isChecked(): parse_mode = "none"
                elif self.rb_full.isChecked(): parse_mode = "full"
                
                if parse_mode == "none": 
                    std_name = f_name
                elif parse_mode == "simple": 
                    std_name = "-".join([x for x in [f"『{f_name}』" if f_name else "", preset.get("model", ""), preset.get("photographer", ""), year, amount, "Moment"] if x])
                elif parse_mode == "full":
                    raw_title = f_name
                    p_m = preset.get("model", "")
                    p_p = preset.get("photographer", "")
                    if p_m and p_m in raw_title: raw_title = raw_title.replace(p_m, "")
                    if p_p and p_p in raw_title: raw_title = raw_title.replace(p_p, "")
                    
                    d_match = re.search(r'\b((19\d{2}|20\d{2})[-.\s]?\d{2}[-.\s]?\d{2})\b', raw_title)
                    if d_match:
                        raw_title = raw_title.replace(d_match.group(1), "")
                    else:
                        y_match = re.search(r'\b(19\d{2}|20\d{2})\b', raw_title)
                        if y_match:
                            raw_title = raw_title.replace(y_match.group(1), "")
                            
                    raw_title = re.sub(r'[-\s_]+', ' ', raw_title).strip()
                    std_name = "-".join([x for x in [f"『{raw_title}』" if raw_title else "", p_m, p_p, year, amount, "Moment"] if x])
                
                self.table.setItem(row, 1, QTableWidgetItem(std_name))
            finally: self.table.blockSignals(False) 

    def batch_auto_match_thumbs(self):
        if self.table.rowCount() == 0: return False
        thumb_dir = QFileDialog.getExistingDirectory(self, "请选择存放所有封面的图库文件夹", self.base_dir)
        if not thumb_dir: return False
            
        thumb_dir = self.get_abs_path(thumb_dir)
        mc = 0
        self.batch_progress.setValue(0)
        self.log_msg(f"开始在文件夹 {thumb_dir} 中自动匹配封面...", "INFO")
        
        for row in range(self.table.rowCount()):
            name = self.table.item(row, 0).text().strip()
            QApplication.processEvents()
            mp = None
            
            for ext in ['.jpg', '.jpeg', '.png']:
                tp = os.path.join(thumb_dir, f"{name}{ext}")
                if os.path.exists(tp): 
                    mp = tp
                    break
                    
            if mp: 
                self.table.item(row, 3).setData(Qt.ItemDataRole.UserRole, mp)
                self.table.setItem(row, 9, QTableWidgetItem("✅ 封面已匹配"))
                mc += 1
            else: 
                self.table.setItem(row, 9, QTableWidgetItem("❌ 未找到封面"))
                
            self.batch_progress.setValue(int(((row + 1) / self.table.rowCount()) * 100))
            
        self.log_msg(f"自动匹配完成, 成功找回 {mc} 张封面图片。", "SUCCESS")
        return True

    def batch_manual_thumb(self):
        sel = self.table.selectedRanges()
        if not sel: 
            return QMessageBox.warning(self, "提示", "请先在表格中点击选中一行。")
            
        fp, _ = QFileDialog.getOpenFileName(self, "手动选择封面图片", self.base_dir, "Images (*.png *.jpg *.jpeg)")
        if fp: 
            self.table.item(sel[0].topRow(), 3).setData(Qt.ItemDataRole.UserRole, fp)
            self.table.setItem(sel[0].topRow(), 9, QTableWidgetItem("✅ 封面已手动指定"))
            self.batch_progress.setValue(100)

    def batch_scan_folders(self):
        kws = [self.list_kw.item(i).text().lower() for i in range(self.list_kw.count())]
        exts = [self.list_ext.item(i).text().lower() for i in range(self.list_ext.count())]
        
        total_cleaned = 0
        self.batch_progress.setValue(0)
        
        parse_mode = "simple"
        if self.rb_none.isChecked(): parse_mode = "none"
        elif self.rb_full.isChecked(): parse_mode = "full"
        
        self.log_msg(f"开始智能扫描提取 (采用提取模式: {parse_mode})", "INFO")
        self.table.blockSignals(True)

        for row in range(self.table.rowCount()):
            f_path = self.table.item(row, 3).text()
            f_name = os.path.basename(f_path)
            QApplication.processEvents()
            
            preset_name = self.table.cellWidget(row, 2).currentText() if self.table.cellWidget(row, 2) else ""
            preset = next((p for p in self.presets_data if p["name"] == preset_name), {})
            
            if kws or exts:
                try:
                    for root, _, files in os.walk(f_path):
                        for file in files:
                            lf = file.lower()
                            if any(lf.endswith(ext) for ext in exts) or any(kw in lf for kw in kws):
                                os.remove(os.path.join(root, file))
                                total_cleaned += 1
                                self.log_msg(f"🛡 触发防拦截规则，已删除文件: {file}", "WARNING")
                                QApplication.processEvents()
                except Exception as e: 
                    self.log_msg(f"清理文件时报错: {e}", "ERROR")
            
            img_c = len([f for f in os.listdir(f_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
            vid_c = len([f for f in os.listdir(f_path) if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov', '.ts'))])
            amount_str = ""
            if (tot := img_c + vid_c) > 0: 
                amount_str = f"{tot}P/V" if vid_c > 0 else f"{tot}P"
            self.table.setItem(row, 4, QTableWidgetItem(amount_str))
            
            year = ""
            if parse_mode in ["simple", "full"]:
                d_match = re.search(r'\b((19\d{2}|20\d{2})[-.\s]?\d{2}[-.\s]?\d{2})\b', f_name)
                if d_match: 
                    year = d_match.group(2)
                else:
                    y_match = re.search(r'\b(19\d{2}|20\d{2})\b', f_name)
                    if y_match: 
                        year = y_match.group(1)
            self.table.setItem(row, 5, QTableWidgetItem(year))
            
            if parse_mode == "none": 
                std_name = f_name
            elif parse_mode == "simple": 
                std_name = "-".join([x for x in [f"『{f_name}』" if f_name else "", preset.get("model", ""), preset.get("photographer", ""), year, amount_str, "Moment"] if x])
            elif parse_mode == "full":
                raw_title = f_name
                p_m = preset.get("model", "")
                p_p = preset.get("photographer", "")
                if p_m and p_m in raw_title: raw_title = raw_title.replace(p_m, "")
                if p_p and p_p in raw_title: raw_title = raw_title.replace(p_p, "")
                
                d_match = re.search(r'\b((19\d{2}|20\d{2})[-.\s]?\d{2}[-.\s]?\d{2})\b', raw_title)
                if d_match:
                    raw_title = raw_title.replace(d_match.group(1), "")
                else:
                    y_match = re.search(r'\b(19\d{2}|20\d{2})\b', raw_title)
                    if y_match:
                        raw_title = raw_title.replace(y_match.group(1), "")
                        
                raw_title = re.sub(r'[-\s_]+', ' ', raw_title).strip()
                std_name = "-".join([x for x in [f"『{raw_title}』" if raw_title else "", p_m, p_p, year, amount_str, "Moment"] if x])
            
            self.table.setItem(row, 1, QTableWidgetItem(std_name))
            self.log_msg(f" -> 提取并组装名称: {std_name}")
            
            if cw := self.table.cellWidget(row, 6): 
                cw.setCurrentText(preset.get("category", "写真"))
            if tw := self.table.cellWidget(row, 7): 
                tw.set_items(GLOBAL_TAGS, preset.get("tags", []))
                
            self.table.setItem(row, 9, QTableWidgetItem("✅ 参数校验完毕"))
            self.batch_progress.setValue(int(((row + 1) / self.table.rowCount()) * 100))

        self.table.blockSignals(False)
        
        if total_cleaned > 0: 
            self.log_msg(f"扫描完毕，共计删除 {total_cleaned} 个违规广告文件。", "SUCCESS")
            QMessageBox.information(self, "防误抓提示", f"拦截规则生效，共清理了 {total_cleaned} 个可能会引发站内封号的文件。")

    def set_buttons_state(self, running):
        state = not running
        self.btn_auto.setEnabled(state)
        self.btn_make.setEnabled(state)
        self.btn_pub.setEnabled(state)
        self.btn_stop.setEnabled(running)

    def build_config_for_worker(self):
        return {
            'pt_url': self.input_pt_url.text().strip() + ('/' if not self.input_pt_url.text().endswith('/') else ''),
            'cookie': self.input_cookie.text().strip(),
            'torrent_dir': self.get_abs_path(self.input_t_path.text()), 
            'seeding_dir': self.get_abs_path(self.input_s_path.text()),
            'use_zip': self.cb_batch_zip.isChecked(), 
            'test_mode': self.cb_batch_test.isChecked(),
            'anonymous': self.cb_batch_anon.isChecked(),
            'category_map': {"写真": "401", "人像": "402", "风光": "403", "纪实": "404", "杂志": "405", "静物": "406", "儿童": "407", "超现实": "408", "美食": "409", "动物": "410", "人文": "411", "软件": "412", "图书": "413", "预设": "414", "教程": "415", "Special": "416"},
            'qb_url': self.input_qb_url.text().strip(), 
            'qb_user': self.input_qb_user.text().strip(), 
            'qb_pwd': self.input_qb_pwd.text().strip(),
            'add_to_qb': self.chk_qb_add.isChecked(), 
            'image_token': self.input_img_token.text().strip(), 
            'image_upload_api': self.input_img_upload_url.text().strip(),
            'seed_delay': self.spin_delay.value()
        }

    def start_worker(self, mode):
        tasks = []
        for r in range(self.table.rowCount()):
            preset_name = self.table.cellWidget(r, 2).currentText() if self.table.cellWidget(r, 2) else ""
            row_preset = next((p for p in self.presets_data if p["name"] == preset_name), {})
            tasks.append({
                'row': r, 
                'std_name': self.table.item(r, 1).text().strip(), 
                'folder_path': self.table.item(r, 3).text().strip(), 
                'thumb_path': self.table.item(r, 3).data(Qt.ItemDataRole.UserRole), 
                'category': self.table.cellWidget(r, 6).currentText(), 
                'tag_names': self.table.cellWidget(r, 7).get_checked_items(),
                'intro': row_preset.get('intro', '')
            })
        
        if not tasks: 
            return QMessageBox.warning(self, "提示", "待处理列表为空，请先添加文件夹！")
            
        self.set_buttons_state(True)
        self.batch_progress.setValue(0)
        
        self.worker = BatchWorkerThread(mode, tasks, self.build_config_for_worker())
        self.worker.log_signal.connect(self.log_msg)
        self.worker.progress_signal.connect(self.batch_progress.setValue)
        self.worker.cell_update_signal.connect(self.update_table_cell)
        self.worker.finished_signal.connect(self.worker_finished)
        self.worker.start()

    def worker_finished(self, success, total):
        self.set_buttons_state(False)
        QMessageBox.information(self, "任务完成", f"队列任务已全部处理完毕。\n成功次数: {success}/{total}")

    def force_stop_worker(self):
        if hasattr(self, 'worker') and self.worker.isRunning(): 
            self.worker.stop()
            self.log_msg("🛑 已强行停止后台线程。", "WARNING")

    def run_auto_publish(self):
        if QMessageBox.question(self, "一键全自动", "将依次执行：自动找图 ➔ 打包制种 ➔ 推送图床 ➔ 表单发布 ➔ 添加做种。是否继续？", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            if not self.batch_auto_match_thumbs(): 
                self.log_msg("图库选择已取消，终止全自动流程。", "WARNING")
                return
            self.start_worker('auto')

    def open_torrent_folder(self):
        path = self.get_abs_path(self.input_t_path.text())
        os.makedirs(path, exist_ok=True)
        os.startfile(path) if sys.platform == 'win32' else subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', path])

    def test_pt_connection(self):
        try:
            r = requests.get(self.input_pt_url.text().strip(), headers={"Cookie": self.input_cookie.text()}, timeout=5)
            if "login" in r.url: 
                QMessageBox.warning(self, "提示", "能连通 PT 站，但被要求登录，请检查 Cookie 是否过期。")
            else: 
                QMessageBox.information(self, "成功", "PT站点连接顺畅，身份验证成功。")
        except Exception as e: 
            QMessageBox.critical(self, "错误", f"连接失败: {e}")

    def test_qb_connection(self):
        try:
            import qbittorrentapi
            qb = qbittorrentapi.Client(host=self.input_qb_url.text(), username=self.input_qb_user.text(), password=self.input_qb_pwd.text())
            qb.auth_log_in()
            QMessageBox.information(self, "成功", "已成功与本机的 qBittorrent 建立通信。")
        except Exception as e: 
            QMessageBox.critical(self, "错误", f"无法连接 qBittorrent: {e}")

    def get_image_token(self):
        email = self.input_img_email.text().strip()
        pwd = self.input_img_pwd.text()
        token_url = self.input_img_token_url.text().strip()
        if not email or not token_url: return
        self.log_msg(f"正在向图床请求获取 Token...")
        try:
            response = requests.post(token_url, json={"email": email, "password": pwd}, timeout=10)
            data = response.json()
            if (token := data.get("token") or data.get("data", {}).get("token")):
                self.input_img_token.setText(token)
                QMessageBox.information(self, "成功", "已成功获取并填入 Token。")
            else: 
                QMessageBox.warning(self, "警告", "获取失败，请检查账号密码。")
        except Exception as e: 
            QMessageBox.critical(self, "错误", f"请求异常:\n{e}")

    def setup_log_tab(self):
        layout = QVBoxLayout(self.tab_log)
        group_log = QGroupBox("🖥️ 实时运行日志")
        v_log = QVBoxLayout()
        self.log_view = QTextEdit()
        self.log_view.setObjectName("LogView")
        self.log_view.setReadOnly(True)
        
        h_tool = QHBoxLayout()
        h_tool.addWidget(QLabel("📌 记录程序详细工作状态、接口返回值和异常报错。"))
        h_tool.addStretch()
        
        btn_open_dir = QPushButton("📂 打开日志文件夹")
        btn_open_dir.clicked.connect(lambda: os.startfile(os.path.join(self.base_dir, 'logs')) if sys.platform == 'win32' else subprocess.Popen(['open' if sys.platform == 'darwin' else 'xdg-open', os.path.join(self.base_dir, 'logs')]))
        
        btn_clear = QPushButton("🗑 清空当前面板")
        btn_clear.setStyleSheet("background-color: #ff3b30; color: white; border: none;")
        btn_clear.clicked.connect(self.log_view.clear)
        
        h_tool.addWidget(btn_open_dir)
        h_tool.addWidget(btn_clear)
        v_log.addLayout(h_tool)
        v_log.addWidget(self.log_view)
        group_log.setLayout(v_log)
        layout.addWidget(group_log)

    def setup_batch_upload_tab(self):
        layout = QVBoxLayout(self.tab_batch)
        
        group_top = QGroupBox("第一步：选择发布预设与基础设定")
        h_top = QHBoxLayout()
        self.preset_combo = QComboBox()
        self.preset_combo.currentIndexChanged.connect(self.preset_changed)
        self.preset_combo.setMinimumWidth(200)
        h_top.addWidget(QLabel("发布预设:"))
        h_top.addWidget(self.preset_combo)
        
        btn_m = QPushButton("⚙ 管理预设")
        btn_m.clicked.connect(self.open_manage_presets)
        h_top.addWidget(btn_m)
        
        btn_r = QPushButton("刷新菜单")
        btn_r.clicked.connect(self.refresh_main_preset_combo)
        h_top.addWidget(btn_r)
        
        h_top.addStretch()
        
        self.cb_batch_anon = QCheckBox("匿名上传")
        self.cb_batch_anon.setChecked(True)
        self.cb_batch_zip = QCheckBox("打包为ZIP格式")
        self.cb_batch_zip.setChecked(True)
        self.cb_batch_test = QCheckBox("仅测试(不发送)")
        
        h_top.addWidget(self.cb_batch_anon)
        h_top.addWidget(self.cb_batch_zip)
        h_top.addWidget(self.cb_batch_test)
        
        v_top = QVBoxLayout()
        v_top.addLayout(h_top)
        self.preset_info_label = QTextEdit()
        self.preset_info_label.setFixedHeight(80)
        self.preset_info_label.setReadOnly(True)
        v_top.addWidget(self.preset_info_label)
        group_top.setLayout(v_top)
        layout.addWidget(group_top, 0)
        
        self.refresh_main_preset_combo()

        group_mid = QGroupBox("第二步：装载文件夹与提取信息")
        v_mid = QVBoxLayout()
        
        h_toolbar = QHBoxLayout()
        b_add = QPushButton("📁 1.添加文件夹")
        b_add.setStyleSheet("background:#34c759; color:white; border:none;")
        b_add.clicked.connect(self.batch_add_folder)
        
        b_scn = QPushButton("🔍 2.智能扫描提取")
        b_scn.setStyleSheet("background:#007aff; color:white; border:none;")
        b_scn.clicked.connect(self.batch_scan_folders)

        b_rn = QPushButton("🔄 3.序列化重命名 (可选)")
        b_rn.setStyleSheet("background:#ff9500; color:white; border:none;")
        b_rn.clicked.connect(self.batch_rename_files)
        
        b_clr = QPushButton("🗑 4.清空列表")
        b_clr.setStyleSheet("background:#ff3b30; color:white; border:none;")
        b_clr.clicked.connect(lambda: self.table.setRowCount(0))
        
        h_toolbar.addWidget(b_add)
        h_toolbar.addWidget(b_scn)
        h_toolbar.addWidget(b_rn)
        h_toolbar.addStretch()
        h_toolbar.addWidget(b_clr)
        v_mid.addLayout(h_toolbar)

        self.table = QTableWidget(0, 11)
        self.table.verticalHeader().setDefaultSectionSize(34)
        self.table.setHorizontalHeaderLabels(["原始文件夹名", "最终种子名称", "应用预设", "物理路径", "P/V数", "年份", "分类", "附加标签", "种子", "状态", "操作"])
        
        head = self.table.horizontalHeader()
        head.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setColumnWidth(0, 100)
        head.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 70)
        self.table.setColumnWidth(5, 60)
        self.table.setColumnWidth(6, 75)
        self.table.setColumnWidth(7, 120)
        self.table.setColumnWidth(8, 75)
        self.table.setColumnWidth(9, 80)
        self.table.setColumnWidth(10, 50)
        
        self.table.cellChanged.connect(self.on_table_cell_changed)
        v_mid.addWidget(self.table)
        group_mid.setLayout(v_mid)
        layout.addWidget(group_mid, 1) 

        group_bot = QGroupBox("第三步：多线程任务操作台")
        v_bot = QVBoxLayout()
        h_exec = QHBoxLayout()
        
        b_auto_img = QPushButton("① 自动寻找封面")
        b_auto_img.clicked.connect(self.batch_auto_match_thumbs)
        b_man_img = QPushButton("① 手动指定封面")
        b_man_img.clicked.connect(self.batch_manual_thumb)
        
        self.btn_make = QPushButton("② 后台打包制种")
        self.btn_make.clicked.connect(lambda: self.start_worker('make'))
        self.btn_pub = QPushButton("③ 推送到 PT 站")
        self.btn_pub.clicked.connect(lambda: self.start_worker('publish'))
        
        b5 = QPushButton("📁 打开种子目录")
        b5.clicked.connect(self.open_torrent_folder)
        
        h_exec.addWidget(QLabel("分步执行:"))
        h_exec.addWidget(b_auto_img)
        h_exec.addWidget(b_man_img)
        h_exec.addWidget(self.btn_make)
        h_exec.addWidget(self.btn_pub)
        h_exec.addWidget(b5)
        h_exec.addStretch()
        v_bot.addLayout(h_exec)
        
        h_main_btn = QHBoxLayout()
        self.btn_auto = QPushButton("🚀 一键全自动上传 (推荐)")
        self.btn_auto.setStyleSheet("background: #007aff; color: white; font-size: 14px; padding: 10px 24px; border: none;")
        self.btn_auto.clicked.connect(self.run_auto_publish)
        
        self.btn_stop = QPushButton("🛑 强行终止任务")
        self.btn_stop.setStyleSheet("background: #ff3b30; color: white; padding: 10px 20px; border: none;")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self.force_stop_worker)
        
        h_main_btn.addWidget(self.btn_auto, 3)
        h_main_btn.addWidget(self.btn_stop)
        v_bot.addLayout(h_main_btn)
        
        lbl_desc = self.create_hint_label("💡 流程说明：1.添加文件夹 ➔ 2.扫描提取参数 ➔ 3.启动自动化上传 (包含自动找图/打ZIP/上图床/发种/自动做种)", "primary")
        v_bot.addWidget(lbl_desc)

        self.batch_progress = QProgressBar()
        self.batch_progress.setValue(0)
        v_bot.addWidget(self.batch_progress)
        
        h_log_header = QHBoxLayout()
        h_log_header.addWidget(QLabel("📝 进度监听:"))
        h_log_header.addStretch()
        
        self.batch_log = QTextEdit()
        self.batch_log.setObjectName("BatchLogView")
        self.batch_log.setFixedHeight(120)
        self.batch_log.setReadOnly(True)
        
        btn_clr_batch_log = QPushButton("🗑 清空回显")
        btn_clr_batch_log.setStyleSheet("color:#ff3b30; background:transparent; border:none;")
        btn_clr_batch_log.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clr_batch_log.clicked.connect(self.batch_log.clear)
        
        h_log_header.addWidget(btn_clr_batch_log)
        v_bot.addLayout(h_log_header)
        v_bot.addWidget(self.batch_log)
        group_bot.setLayout(v_bot)
        layout.addWidget(group_bot, 0)

    def get_hline(self):
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: rgba(150, 150, 150, 100); max-height: 1px; margin: 8px 0;")
        return line

    def setup_settings_tab(self):
        sa = QScrollArea()
        sa.setWidgetResizable(True)
        mw = QWidget()
        layout = QVBoxLayout(mw)
        layout.setSpacing(16)
        
        gb_b = QGroupBox("📌 基础路径设置")
        fb = QFormLayout()
        fb.setSpacing(14)
        self.combo_theme = QComboBox()
        self.combo_theme.addItems(["明亮白昼模式", "夜间护眼模式"])
        self.combo_theme.currentIndexChanged.connect(self.theme_changed)
        fb.addRow("渲染主题:", self.combo_theme)
        
        self.input_t_path = QLineEdit()
        self.input_t_path.setPlaceholderText("建议填 ./torrents")
        self.input_s_path = QLineEdit()
        self.input_s_path.setPlaceholderText("建议填 ./seeding")
        
        h1 = QHBoxLayout()
        h1.addWidget(self.input_t_path)
        b1 = QPushButton("浏览")
        b1.clicked.connect(lambda: self.browse_folder(self.input_t_path))
        h1.addWidget(b1)
        
        h2 = QHBoxLayout()
        h2.addWidget(self.input_s_path)
        b2 = QPushButton("浏览")
        b2.clicked.connect(lambda: self.browse_folder(self.input_s_path))
        h2.addWidget(b2)
        
        fb.addRow("官方种子存放位置:", h1)
        fb.addRow("做种文件位置:", h2)
        fb.addRow("", self.create_hint_label("💡 说明：为了防乱，从 PT 站下载回来的带个人 Passkey 的官方种子会保存在【种子存放位置】下的【PT_Official】子文件夹内。\n而本地打包后自己生成的原始种子会放入该路径下的【Local_Made】子文件夹内。", "primary"))
        gb_b.setLayout(fb)
        layout.addWidget(gb_b)

        gn = QGroupBox("🌐 PT站点与图床配置")
        fn = QFormLayout()
        fn.setSpacing(14)
        
        self.input_pt_url = QLineEdit()
        self.input_cookie = QLineEdit()
        self.input_api_key = QLineEdit()
        fn.addRow("PT站域名:", self.input_pt_url)
        fn.addRow("账号 Cookie:", self.input_cookie)
        fn.addRow("API Key (选填):", self.input_api_key)
        
        b_pt = QPushButton("测试能否连通 PT 站")
        b_pt.setStyleSheet("background-color: #007aff; color: white; border: none;")
        b_pt.clicked.connect(self.test_pt_connection)
        fn.addRow("", b_pt)
        
        fn.addRow(self.get_hline())
        
        self.input_img_upload_url = QLineEdit()
        self.input_img_email = QLineEdit()
        self.input_img_pwd = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        self.input_img_token = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        self.input_img_token_url = QLineEdit()
        
        fn.addRow("图床上传API:", self.input_img_upload_url)
        fn.addRow("验证 Token:", self.input_img_token)
        fn.addRow("获取 Token API:", self.input_img_token_url)
        
        fn.addRow("图床邮箱:", self.input_img_email)
        fn.addRow("图床密码:", self.input_img_pwd)
        
        b_gt = QPushButton("向图床申请获取 Token")
        b_gt.setStyleSheet("background-color: #34c759; color: white; border: none;")
        b_gt.clicked.connect(self.get_image_token)
        fn.addRow("", b_gt)
        
        hr = QHBoxLayout()
        hr.addWidget(QLabel("自动发种时，两个种子间隔时间:"))
        self.spin_delay = QSpinBox()
        self.spin_delay.setMaximum(9999)
        hr.addWidget(self.spin_delay)
        hr.addWidget(QLabel("秒 (默认3秒，为0时不限制)"))
        hr.addStretch()
        fn.addRow("发种限流保护:", hr)
        
        gn.setLayout(fn)
        layout.addWidget(gn)

        ga = QGroupBox("⚙️ 防误抓拦截规则与自动化配置")
        fa = QFormLayout()
        fa.setSpacing(14)
        
        self.input_qb_url = QLineEdit()
        self.input_qb_user = QLineEdit()
        self.input_qb_pwd = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        self.chk_qb_add = QCheckBox("将种子自动推送到 qBittorrent 并强制开启做种")
        
        fa.addRow("qB 端口地址:", self.input_qb_url)
        fa.addRow("qB 账号:", self.input_qb_user)
        fa.addRow("qB 密码:", self.input_qb_pwd)
        fa.addRow("", self.chk_qb_add)
        
        b_qb = QPushButton("测试连接 qBittorrent")
        b_qb.setStyleSheet("background-color: #007aff; color: white; border: none;")
        b_qb.clicked.connect(self.test_qb_connection)
        fa.addRow("", b_qb)
        
        fa.addRow(self.get_hline())
        
        pl = QVBoxLayout()
        self.btn_group_parse = QButtonGroup()
        self.rb_none = QRadioButton("禁用提取")
        self.rb_simple = QRadioButton("简单提取")
        self.rb_full = QRadioButton("强效重组")
        self.btn_group_parse.addButton(self.rb_none)
        self.btn_group_parse.addButton(self.rb_simple)
        self.btn_group_parse.addButton(self.rb_full)
        
        pl.addWidget(self.rb_none)
        pl.addWidget(self.create_hint_label("💡 禁用提取：直接使用资源文件夹的名称作为种子标题，不做任何拼装。\n【适用场景】提前已经按标准修改好文件夹名称。", "info"))
        
        pl.addWidget(self.rb_simple)
        pl.addWidget(self.create_hint_label("💡 简单提取 (推荐)：将文件夹完整名称作为『主题』，然后自动补充年份和P数，其他缺失项用预设补齐。\n【举例】文件夹叫：秀人网写真 ➔ 『秀人网写真』-预设模特-预设摄影师-63P-Moment", "info"))
        
        pl.addWidget(self.rb_full)
        pl.addWidget(self.create_hint_label("💡 强效重组：根据文件夹的名称来判断，有和预设一样的摄影师/模特，需去掉不在主题里面显示；文件夹名称有疑似日期数字的，需提取年份出来回填，同样也不在主题里面显示。\n例1：MintYe薄荷叶 Vol.004 何梦兮Stacy ➔ 『MintYe薄荷叶 Vol.004』-预设补齐\n例2：MintYe薄荷叶 2021.02.28 Vol.004 何梦兮Stacy ➔ 『MintYe薄荷叶 Vol.004』-预设补齐-2021-63P-Moment", "info"))
        fa.addRow("名称解析模式:", pl)
        
        fa.addRow(self.get_hline())
        
        lc = QGridLayout()
        self.input_kw = QLineEdit()
        self.input_kw.setPlaceholderText("在此打字，按回车添加...")
        self.input_kw.returnPressed.connect(lambda: self.add_cleanup_item(self.input_kw, self.list_kw))
        
        self.input_ext = QLineEdit()
        self.input_ext.setPlaceholderText("在此打字，按回车添加...")
        self.input_ext.returnPressed.connect(lambda: self.add_cleanup_item(self.input_ext, self.list_ext))
        
        self.list_kw = QListWidget()
        self.list_kw.setViewMode(QListWidget.ViewMode(1))
        self.list_kw.setResizeMode(QListWidget.ResizeMode(1))
        self.list_kw.setSpacing(4)
        
        self.list_ext = QListWidget()
        self.list_ext.setViewMode(QListWidget.ViewMode(1))
        self.list_ext.setResizeMode(QListWidget.ResizeMode(1))
        self.list_ext.setSpacing(4)
        
        b_dk = QPushButton("删除选中")
        b_dk.setStyleSheet("background:#ff3b30; color:white; border:none; padding:4px;")
        b_dk.clicked.connect(lambda: self.del_cleanup_item(self.list_kw))
        b_ck = QPushButton("全部清空")
        b_ck.clicked.connect(lambda: self.clear_all_cleanup_items(self.list_kw))
        
        b_de = QPushButton("删除选中")
        b_de.setStyleSheet("background:#ff3b30; color:white; border:none; padding:4px;")
        b_de.clicked.connect(lambda: self.del_cleanup_item(self.list_ext))
        b_ce = QPushButton("全部清空")
        b_ce.clicked.connect(lambda: self.clear_all_cleanup_items(self.list_ext))
        
        lc.addWidget(QLabel("包含以下文字则删除:"), 0, 0)
        lc.addWidget(self.input_kw, 0, 1, 1, 2)
        lc.addWidget(QLabel("属于以下后缀则删除:"), 0, 3)
        lc.addWidget(self.input_ext, 0, 4, 1, 2)
        lc.addWidget(self.list_kw, 1, 0, 1, 3)
        lc.addWidget(self.list_ext, 1, 3, 1, 3)
        
        hk = QHBoxLayout()
        hk.addWidget(b_dk)
        hk.addWidget(b_ck)
        hk.addStretch()
        he = QHBoxLayout()
        he.addWidget(b_de)
        he.addWidget(b_ce)
        he.addStretch()
        
        lc.addLayout(hk, 2, 0, 1, 3)
        lc.addLayout(he, 2, 3, 1, 3)
        fa.addRow("广告文件拦截器:", lc)
        
        lbl_ad = self.create_hint_label("💡 操作指南：在上方输入框内输入你想拦截的词汇或后缀名（例如：.url、.txt、网址、赌场），然后按键盘上的【回车键 (Enter)】，即可将其加入拦截库中。", "primary")
        fa.addRow("", lbl_ad)
        
        ga.setLayout(fa)
        layout.addWidget(ga)

        hb = QHBoxLayout()
        br = QPushButton("取消更改，恢复上次保存配置")
        br.setStyleSheet("background:#8e8e93; color:white; padding:12px; border:none;")
        br.clicked.connect(self.load_config)
        bs = QPushButton("💾 保存偏好设置")
        bs.setStyleSheet("background:#007aff; color:white; font-size:14px; padding:12px; border:none;")
        bs.clicked.connect(self.save_config)
        hb.addWidget(br)
        hb.addWidget(bs)
        layout.addLayout(hb)
        
        sa.setWidget(mw)
        lyt = QVBoxLayout(self.tab_settings)
        lyt.setContentsMargins(0,0,0,0)
        lyt.addWidget(sa)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PTUploaderFullGUI()
    window.show()
    sys.exit(app.exec())