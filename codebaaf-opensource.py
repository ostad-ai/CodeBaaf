#--- updated Nov. 10, 2026 ---

import sys
import os
import re
import json
import time
import subprocess
import tempfile
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPlainTextEdit, QPushButton, QFileDialog, QSplitter, QLabel,
    QMessageBox, QMenu, QMenuBar, QDialog, QDialogButtonBox,
    QLineEdit, QCheckBox, QCompleter, QTabWidget
)
from PySide6.QtCore import Qt, QThread, Signal, QStringListModel, QProcess, QSize, QEvent, QProcessEnvironment
from PySide6.QtGui import (
    QFont, QColor, QTextCharFormat, QSyntaxHighlighter, QShortcut, 
    QKeySequence, QAction, QPainter, QFontDatabase, QTextCursor, QTextDocument, QIcon
)

# ==========================================
# 1. Editor ba Shomare Khat (Line Numbers) + Auto-complete
# ==========================================
class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_number_area = LineNumberArea(self)
        self.show_line_numbers = True
        self.auto_complete_enabled = True
        self.is_dark = True
        
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

        self.completer = QCompleter(self)
        self.completer.setWidget(self)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.activated.connect(self.insert_completion)
        
        self.python_keywords = [
            "and", "as", "assert", "async", "await", "break", "class",
            "continue", "def", "del", "elif", "else", "except", "finally",
            "for", "from", "global", "if", "import", "in", "is", "lambda",
            "nonlocal", "not", "or", "pass", "raise", "return", "try",
            "while", "with", "yield", "print", "len", "range", "str", "int", "float", "list", "dict",
            "True", "False", "None", "self", "super"
        ]
        
        self.completer_model = QStringListModel(self.python_keywords, self)
        self.completer.setModel(self.completer_model)

    def toggle_line_numbers(self, state):
        self.show_line_numbers = state
        self.line_number_area.setVisible(state)
        self.update_line_number_area_width(0)

    def toggle_auto_complete(self, state):
        self.auto_complete_enabled = state
        if not state:
            self.completer.popup().hide()

    def line_number_area_width(self):
        if not self.show_line_numbers:
            return 0
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if not self.show_line_numbers:
            return
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(cr.left(), cr.top(), self.line_number_area_width(), cr.height())

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        if self.is_dark:
            painter.fillRect(event.rect(), QColor("#181825")) 
            painter.setPen(QColor("#6c7086"))
        else:
            painter.fillRect(event.rect(), QColor("#e6e9ef")) 
            painter.setPen(QColor("#8c8fa1"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(0, int(top), self.line_number_area.width() - 5, self.fontMetrics().height(),
                                 Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def highlight_current_line(self):
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            if self.is_dark:
                line_color = QColor("#313244")
            else:
                line_color = QColor("#dce0e8")
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextCharFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)

    def keyPressEvent(self, event):
        if not self.auto_complete_enabled:
            super().keyPressEvent(event)
            return

        if self.completer.popup().isVisible() and event.key() in [
            Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab, Qt.Key_Backtab
        ]:
            event.ignore()
            return

        if event.key() in [
            Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down, 
            Qt.Key_Home, Qt.Key_End, Qt.Key_PageUp, Qt.Key_PageDown
        ]:
            self.completer.popup().hide()
            super().keyPressEvent(event)
            return

        super().keyPressEvent(event)
        
        cursor = self.textCursor()
        cursor.select(cursor.SelectionType.WordUnderCursor)
        prefix = cursor.selectedText()

        if prefix and re.match(r'^[a-zA-Z_]\w*$', prefix):
            self.completer.setCompletionPrefix(prefix)
            
            all_text = self.toPlainText()
            words_in_code = set(re.findall(r'\b[a-zA-Z_]\w*\b', all_text))
            
            current_list = set(self.python_keywords)
            current_list.update(words_in_code)
            self.completer_model.setStringList(sorted(list(current_list)))
            
            popup = self.completer.popup()
            popup.setCurrentIndex(self.completer.completionModel().index(0, 0))
            
            cr = self.cursorRect()
            cr.setWidth(popup.sizeHintForColumn(0) + popup.verticalScrollBar().sizeHint().width())
            self.completer.complete(cr)
        else:
            self.completer.popup().hide()

    def insert_completion(self, completion):
        tc = self.textCursor()
        tc.select(tc.SelectionType.WordUnderCursor)
        tc.insertText(completion)
        self.setTextCursor(tc)


class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)


# ==========================================
# 2. Find & Replace Dialog
# ==========================================
class FindReplaceDialog(QDialog):
    def __init__(self, editor, parent=None):
        super().__init__(parent)
        self.editor = editor
        self.setWindowTitle("Find & Replace")
        self.setFixedSize(400, 200)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout(self)

        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("Find:"))
        self.find_input = QLineEdit()
        find_layout.addWidget(self.find_input)
        layout.addLayout(find_layout)

        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("Replace:"))
        self.replace_input = QLineEdit()
        replace_layout.addWidget(self.replace_input)
        layout.addLayout(replace_layout)

        btn_layout = QHBoxLayout()
        self.find_next_btn = QPushButton("Find Next")
        self.find_next_btn.clicked.connect(lambda: self.find_text(forward=True))
        btn_layout.addWidget(self.find_next_btn)

        self.find_prev_btn = QPushButton("Find Previous")
        self.find_prev_btn.clicked.connect(lambda: self.find_text(forward=False))
        btn_layout.addWidget(self.find_prev_btn)

        self.replace_btn = QPushButton("Replace")
        self.replace_btn.clicked.connect(self.replace_text)
        btn_layout.addWidget(self.replace_btn)

        self.replace_all_btn = QPushButton("Replace All")
        self.replace_all_btn.clicked.connect(self.replace_all_text)
        btn_layout.addWidget(self.replace_all_btn)
        
        layout.addLayout(btn_layout)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #a6e3a1; font-weight: bold;")
        layout.addWidget(self.status_label)

    def find_text(self, forward=True):
        text = self.find_input.text()
        if not text:
            return

        flags = QTextDocument.FindFlags()
        if not forward:
            flags |= QTextDocument.FindBackward

        found = self.editor.find(text, flags)
        
        if not found:
            cursor = self.editor.textCursor()
            if forward:
                cursor.movePosition(QTextCursor.Start)
            else:
                cursor.movePosition(QTextCursor.End)
            self.editor.setTextCursor(cursor)
            found = self.editor.find(text, flags)

        if found:
            self.count_matches(text)
        else:
            self.status_label.setText("No matches found")
            self.status_label.setStyleSheet("color: #d20f39;")

    def count_matches(self, text):
        doc_text = self.editor.toPlainText()
        count = doc_text.count(text)
        self.status_label.setText(f"{count} matches found")
        self.status_label.setStyleSheet("color: #40a02b;")

    def replace_text(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == self.find_input.text():
            cursor.insertText(self.replace_input.text())
            self.editor.setTextCursor(cursor)
        self.find_text(forward=True)

    def replace_all_text(self):
        find_text = self.find_input.text()
        replace_text = self.replace_input.text()
        if not find_text:
            return

        content = self.editor.toPlainText()
        new_content = content.replace(find_text, replace_text)
        count = content.count(find_text)

        self.editor.setPlainText(new_content)
        self.status_label.setText(f"Replaced {count} matches")
        self.status_label.setStyleSheet("color: #40a02b;")


# ==========================================
# 3. Python Syntax Highlighter
# ==========================================
class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.highlighting_rules = []
        self.is_dark = True

        self.keyword_format = QTextCharFormat()
        self.keyword_format.setFontWeight(QFont.Bold)

        self.string_format = QTextCharFormat()
        self.comment_format = QTextCharFormat()
        self.number_format = QTextCharFormat()

        keywords = [
            "and", "as", "assert", "async", "await", "break", "class",
            "continue", "def", "del", "elif", "else", "except", "finally",
            "for", "from", "global", "if", "import", "in", "is", "lambda",
            "nonlocal", "not", "or", "pass", "raise", "return", "try",
            "while", "with", "yield", "print", "len", "range", "str", "int", "float", "list", "dict"
        ]
        for word in keywords:
            self.highlighting_rules.append((rf"\b{word}\b", self.keyword_format))
        
        self.highlighting_rules.append((r'"[^"\\]*(\\.[^"\\]*)*"', self.string_format))
        self.highlighting_rules.append((r"'[^'\\]*(\\.[^'\\]*)*'", self.string_format))
        self.highlighting_rules.append((r'#[^\n]*', self.comment_format))
        self.highlighting_rules.append((r'\b\d+(\.\d+)?\b', self.number_format))
        
        self.update_colors(True)

    def update_colors(self, is_dark):
        self.is_dark = is_dark
        if is_dark:
            self.keyword_format.setForeground(QColor("#89b4fa"))
            self.string_format.setForeground(QColor("#a6e3a1"))
            self.comment_format.setForeground(QColor("#6c7086"))
            self.number_format.setForeground(QColor("#fab387"))
        else:
            self.keyword_format.setForeground(QColor("#1e66f5"))
            self.string_format.setForeground(QColor("#40a02b"))
            self.comment_format.setForeground(QColor("#9ca0b0"))
            self.number_format.setForeground(QColor("#fe640b"))
        self.rehighlight()

    def highlightBlock(self, text):
        for pattern, fmt in self.highlighting_rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


# ==========================================
# 4. Main Window (CodeBaaf)
# ==========================================
class CodeBaaf(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(1100, 750)
        
        if os.name == 'nt':
            try:
                from ctypes import windll
                myappid = 'arle.codebaaf.ide.1.0' 
                windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except ImportError:
                pass

        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        icon_ico_path = os.path.join(base_path, "codebaaf_icon.ico")
        icon_png_path = os.path.join(base_path, "codebaaf_icon.png")

        if os.path.exists(icon_ico_path):
            self.setWindowIcon(QIcon(icon_ico_path))
        elif os.path.exists(icon_png_path):
            self.setWindowIcon(QIcon(icon_png_path))

        self.current_file = None
        self.is_modified = False
        self.loading_file = True 
        self.config_file = "codebaaf_config.json"
        
        self.font_size = 14
        self.is_dark_mode = True
        self.show_line_numbers = True
        self.auto_complete = True
        
        # Terminal Variables
        self._term_busy = False
        self._term_accepts_stdin = False
        self._term_process = None
        self._input_start = 0
        
        self.load_settings()

        self.build_ui()
        self.apply_theme()
        self.update_title()
        
        self.loading_file = False 
        self.start_terminal()

    def load_settings(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.font_size = data.get("font_size", 14)
                    self.is_dark_mode = data.get("is_dark_mode", True)
                    self.show_line_numbers = data.get("show_line_numbers", True)
                    self.auto_complete = data.get("auto_complete", True)
            except Exception:
                pass

    def save_settings(self):
        data = {
            "font_size": self.font_size,
            "is_dark_mode": self.is_dark_mode,
            "show_line_numbers": self.show_line_numbers,
            "auto_complete": self.auto_complete
        }
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception:
            pass

    def build_ui(self):
        self.editor = CodeEditor()
        self.editor.toggle_line_numbers(self.show_line_numbers)
        self.editor.toggle_auto_complete(self.auto_complete)
        self.highlighter = PythonHighlighter(self.editor.document())
        self.editor.setFont(QFont("Consolas", self.font_size))
        self.editor.textChanged.connect(self.on_text_changed)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", self.font_size - 1))
        self.output.setContextMenuPolicy(Qt.CustomContextMenu)
        self.output.customContextMenuRequested.connect(self.show_output_menu)

        self.terminal = QTextEdit()
        self.terminal.setFont(QFont("Consolas", self.font_size - 1))
        self.terminal.setStyleSheet("background-color: #11111b; color: #cdd6f4;")
        self.terminal.setContextMenuPolicy(Qt.CustomContextMenu)
        self.terminal.customContextMenuRequested.connect(self.show_terminal_menu)
        self.terminal.installEventFilter(self)

        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.addTab(self.output, "Output")
        self.bottom_tabs.addTab(self.terminal, "Terminal")

        # Shortcuts
        QShortcut(QKeySequence("F5"), self).activated.connect(self.run_code)
        for seq in ("Ctrl+Return", "Ctrl+Enter"):
            QShortcut(QKeySequence(seq), self).activated.connect(self.run_in_terminal)

        menubar = self.menuBar()

        # File
        file_menu = menubar.addMenu("File")
        new_action = QAction("New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)

        open_action = QAction("Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        file_menu.addSeparator()

        close_action = QAction("Close File", self)
        close_action.triggered.connect(self.close_file)
        file_menu.addAction(close_action)

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit
        edit_menu = menubar.addMenu("Edit")
        undo_action = QAction("Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.editor.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.editor.redo)
        edit_menu.addAction(redo_action)
        edit_menu.addSeparator()

        cut_action = QAction("Cut", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(self.editor.cut)
        edit_menu.addAction(cut_action)

        copy_action = QAction("Copy", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.editor.copy)
        edit_menu.addAction(copy_action)

        paste_action = QAction("Paste", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.editor.paste)
        edit_menu.addAction(paste_action)
        edit_menu.addSeparator()

        select_all_action = QAction("Select All", self)
        select_all_action.setShortcut("Ctrl+A")
        select_all_action.triggered.connect(self.editor.selectAll)
        edit_menu.addAction(select_all_action)
        edit_menu.addSeparator()

        find_action = QAction("Find / Replace...", self)
        find_action.setShortcut(QKeySequence("Ctrl+F"))
        find_action.triggered.connect(self.show_find_dialog)
        edit_menu.addAction(find_action)

        # Settings
        settings_menu = menubar.addMenu("Settings")
        font_up_action = QAction("Increase Font Size", self)
        font_up_action.setShortcuts([QKeySequence("Ctrl+="), QKeySequence("Ctrl++")])
        font_up_action.triggered.connect(lambda: self.change_font_size(1))
        settings_menu.addAction(font_up_action)

        font_down_action = QAction("Decrease Font Size", self)
        font_down_action.setShortcuts([QKeySequence("Ctrl+-")])
        font_down_action.triggered.connect(lambda: self.change_font_size(-1))
        settings_menu.addAction(font_down_action)
        settings_menu.addSeparator()

        theme_action = QAction("Toggle Dark/Light Mode", self)
        theme_action.triggered.connect(self.toggle_theme)
        settings_menu.addAction(theme_action)
        settings_menu.addSeparator()
        
        self.ln_action = QAction("Show Line Numbers", self)
        self.ln_action.setCheckable(True)
        self.ln_action.setChecked(self.show_line_numbers)
        self.ln_action.triggered.connect(self.toggle_line_numbers)
        settings_menu.addAction(self.ln_action)

        self.ac_action = QAction("Enable Auto-complete", self)
        self.ac_action.setCheckable(True)
        self.ac_action.setChecked(self.auto_complete)
        self.ac_action.triggered.connect(self.toggle_auto_complete)
        settings_menu.addAction(self.ac_action)

        # Help
        help_menu = menubar.addMenu("Help")
        guide_action = QAction("User Guide", self)
        guide_action.triggered.connect(self.show_guide)
        help_menu.addAction(guide_action)

        about_action = QAction("About CodeBaaf", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)

        toolbar = QHBoxLayout()
        self.run_btn = QPushButton("▶ Run (F5)")
        self.run_btn.clicked.connect(self.run_code)
        toolbar.addWidget(self.run_btn)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_code)
        toolbar.addWidget(self.stop_btn)

        self.clear_btn = QPushButton("Clear Output")
        self.clear_btn.clicked.connect(lambda: self.output.clear())
        toolbar.addWidget(self.clear_btn)
        
        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.editor)
        splitter.addWidget(self.bottom_tabs)
        splitter.setSizes([500, 250])
        main_layout.addWidget(splitter)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

    # ==========================================
    # TERMINAL LOGIC
    # ==========================================
    def start_terminal(self):
        old_process = getattr(self, "process", None)
        if old_process is not None:
            self._kill_terminal_tree()

        self.process = None
        self._term_process = None
        self._term_busy = False
        self._term_accepts_stdin = False

        if not hasattr(self, "_term_history"):
            self._term_history = []
        self._term_hist_pos = len(self._term_history)

        if not hasattr(self, "_term_cwd"):
            self._term_cwd = os.getcwd()

        self.terminal.setAcceptRichText(False)
        self.terminal.setUndoRedoEnabled(False)
        self.terminal.clear()
        
        self.append_terminal("CodeBaaf Terminal\n", log=False)
        self._show_prompt()

    def _show_prompt(self):
        self.append_terminal(f"\n{self._term_cwd}> ", log=False)

    def append_terminal(self, text, log=True):
        c = QTextCursor(self.terminal.document())
        c.movePosition(QTextCursor.End)
        
        typed = ""
        if c.position() > self._input_start:
            c.setPosition(self._input_start)
            c.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
            typed = c.selectedText()
            c.removeSelectedText()
            
        c.insertText(text)
        self._input_start = c.position()
        
        if typed:
            c.insertText(typed)
            
        self.terminal.setTextCursor(c)
        self.terminal.ensureCursorVisible()
        
        if log and self._term_busy and self._term_accepts_stdin:
            self.append_output_log(text)

    def append_output_log(self, text):
        if not text.strip():
            return
        timestamp = time.strftime("%H:%M:%S")
        color = "#a6e3a1" if self.is_dark_mode else "#40a02b"
        
        c = self.output.textCursor()
        c.movePosition(QTextCursor.End)
        
        safe_text = text.replace("\n", "<br>")
        c.insertHtml(f"<br><span style='color: {color};'>[{timestamp}] {safe_text}</span>")
        
        self.output.setTextCursor(c)
        self.output.ensureCursorVisible()
        
    def _term_clear(self):
        self.terminal.clear()
        self._input_start = 0

    def _kill_terminal_tree(self):
        p = getattr(self, "_term_process", None)
        if p is None or p.state() == QProcess.NotRunning:
            return
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.processId())],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       creationflags=subprocess.CREATE_NO_WINDOW)
        p.waitForFinished(2000)

    def interrupt_terminal(self):
        if getattr(self, "_term_process", None) is not None:
            self._term_process.blockSignals(True)
            self._kill_terminal_tree()
        self.append_terminal("^C\n", log=False)
        self._term_busy = False
        self._term_accepts_stdin = False
        self._show_prompt()

    def _submit_terminal_line(self):
        c = QTextCursor(self.terminal.document())
        c.setPosition(self._input_start)
        c.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        line = c.selectedText().replace("\u2029", "\n").split("\n", 1)[0]

        c.movePosition(QTextCursor.End)
        c.clearSelection()
        c.insertText("\n")
        self._input_start = c.position()
        self.terminal.setTextCursor(c)

        self._send_terminal_line(line)
        
    def _send_terminal_line(self, line):
        if self._term_accepts_stdin and self._term_process is not None:
            if self._term_process.state() == QProcess.Running:
                self._term_process.write((line + "\r\n").encode("utf-8"))
            return

        cmd = line.strip()
        if not cmd:
            self._show_prompt()
            return
            
        self._term_history.append(cmd)
        self._term_hist_pos = len(self._term_history)

        if cmd.lower() == "cls":
            self._term_clear()
            self._show_prompt()
            return

        if cmd.startswith("cd "):
            new_dir = cmd[3:].strip().strip('"')
            try:
                os.chdir(os.path.join(self._term_cwd, new_dir))
                self._term_cwd = os.getcwd()
            except Exception as e:
                self.append_terminal(f"Error: {e}\n")
            self._show_prompt()
            return

        self._start_command_process(cmd)

    def _start_command_process(self, command):
        self._term_busy = True
        self._term_process = QProcess(self)
        self._term_process.setWorkingDirectory(self._term_cwd)
        self._term_process.setProcessChannelMode(QProcess.MergedChannels)
        
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        self._term_process.setProcessEnvironment(env)

        self._term_process.readyReadStandardOutput.connect(self.read_terminal_output)
        self._term_process.finished.connect(self._on_terminal_command_finished)
        
        self._term_accepts_stdin = command.startswith("python")
        
        if command.startswith("python -u "):
            file_path = command[10:].strip().strip('"')
            self._term_process.start("python", ["-u", file_path])
        elif command.startswith("python "):
            file_path = command[7:].strip().strip('"')
            self._term_process.start("python", [file_path])
        else:
            self._term_process.start("cmd.exe", ["/Q", "/C", command])
        
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def read_terminal_output(self):
        if self._term_process is None:
            return
        raw = bytes(self._term_process.readAllStandardOutput())
        if not raw:
            return
        text = raw.decode("utf-8", errors="replace")
        text = text.replace("\r\n", "\n").replace("\r", "")
        
        self.append_terminal(text)

    def _on_terminal_command_finished(self):
        self._term_busy = False
        self._term_accepts_stdin = False
        self._show_prompt()
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def eventFilter(self, obj, event):
        if obj is self.terminal and event.type() == QEvent.Type.KeyPress:
            key, mods = event.key(), event.modifiers()
            ctrl = bool(mods & Qt.ControlModifier)
            cur = self.terminal.textCursor()
            start = self._input_start

            if key in (Qt.Key_Return, Qt.Key_Enter) and not ctrl:
                self._submit_terminal_line()
                return True
                
            if ctrl and key == Qt.Key_C:
                if cur.hasSelection():
                    return False
                self.interrupt_terminal()
                return True
                
            if key in (Qt.Key_Up, Qt.Key_Down):
                if self._term_history and not self._term_busy:
                    step = -1 if key == Qt.Key_Up else 1
                    self._term_hist_pos = max(0, min(len(self._term_history), self._term_hist_pos + step))
                    txt = self._term_history[self._term_hist_pos] if self._term_hist_pos < len(self._term_history) else ""
                    c = QTextCursor(self.terminal.document())
                    c.setPosition(self._input_start)
                    c.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
                    c.insertText(txt)
                    self.terminal.setTextCursor(c)
                return True
                
            if key == Qt.Key_Home:
                cur.setPosition(start, QTextCursor.KeepAnchor if mods & Qt.ShiftModifier else QTextCursor.MoveAnchor)
                self.terminal.setTextCursor(cur)
                return True
                
            if key in (Qt.Key_Backspace, Qt.Key_Left) and not cur.hasSelection() and cur.position() <= start:
                return True

            edits = (bool(event.text()) and not ctrl) or key in (Qt.Key_Backspace, Qt.Key_Delete) \
                    or (ctrl and key in (Qt.Key_V, Qt.Key_X))
            if edits and cur.selectionStart() < start:
                cur.movePosition(QTextCursor.End)
                self.terminal.setTextCursor(cur)
            return False
        return super().eventFilter(obj, event)

    def run_in_terminal(self):
        code = self.editor.toPlainText()
        if not code.strip():
            return
        if self._term_busy:
            self.append_terminal("\n[a program is still running - press Stop or Ctrl+C first]\n", log=False)
            return

        if self.current_file:
            self.save_file()
            file_path = self.current_file
        else:
            file_path = os.path.join(tempfile.gettempdir(), "codebaaf_run.py")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

        command = f'python -u "{file_path}"'
        self.bottom_tabs.setCurrentIndex(1)
        self.terminal.setFocus()
        
        c = QTextCursor(self.terminal.document())
        c.setPosition(self._input_start)
        c.movePosition(QTextCursor.End, QTextCursor.KeepAnchor)
        c.removeSelectedText()
        self.terminal.setTextCursor(c)

        self.append_terminal(command + "\n", log=False)
        self._send_terminal_line(command)

    # ==========================================
    # CODE RUNNER (Output)
    # ==========================================
    def run_code(self):
        self.run_in_terminal()

    def stop_code(self):
        if self._term_busy:
            self.interrupt_terminal()
            self.status_bar.showMessage("Ready")

    def show_output_menu(self, pos):
        menu = QMenu(self)
        copy_action = menu.addAction("Copy")
        select_all_action = menu.addAction("Select All")
        clear_action = menu.addAction("Clear")
        
        action = menu.exec(self.output.mapToGlobal(pos))
        if action == copy_action:
            self.output.copy()
        elif action == select_all_action:
            self.output.selectAll()
        elif action == clear_action:
            self.output.clear()

    def show_terminal_menu(self, pos):
        menu = QMenu(self)
        copy_action = menu.addAction("Copy")
        select_all_action = menu.addAction("Select All")
        clear_action = menu.addAction("Clear")
        
        action = menu.exec(self.terminal.mapToGlobal(pos))
        if action == copy_action:
            self.terminal.copy()
        elif action == select_all_action:
            self.terminal.selectAll()
        elif action == clear_action:
            self._term_clear()
            if not self._term_busy:
                self._show_prompt()

    def update_title(self):
        title = "CodeBaaf"
        if self.current_file:
            title = os.path.basename(self.current_file)
        if self.is_modified:
            title += " ●"
        self.setWindowTitle(f"{title} — CodeBaaf")
    
    def on_text_changed(self):
        if self.loading_file:
            return
            
        # FIX 2: Agar file jadid ast va khali ast, taghir hesab nashe
        if self.current_file is None and self.editor.toPlainText() == "":
            self.is_modified = False
            self.update_title()
            return

        if not self.is_modified:
            self.is_modified = True
            self.update_title()

    def toggle_line_numbers(self, checked):
        self.show_line_numbers = checked
        self.editor.toggle_line_numbers(checked)
        self.save_settings()

    def toggle_auto_complete(self, checked):
        self.auto_complete = checked
        self.editor.toggle_auto_complete(checked)
        self.save_settings()

    def apply_theme(self):
        self.highlighter.update_colors(self.is_dark_mode)
        self.editor.is_dark = self.is_dark_mode
        self.editor.highlight_current_line()
        self.editor.line_number_area.update()

        if self.is_dark_mode:
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #1e1e2e; color: #cdd6f4; }
                QMenuBar { background-color: #181825; color: #cdd6f4; }
                QMenuBar::item:selected { background-color: #313244; }
                QMenu { background-color: #1e1e2e; color: #cdd6f4; border: 1px solid #45475a; }
                QMenu::item:selected { background-color: #313244; }
                QTextEdit, QPlainTextEdit { background-color: #181825; color: #cdd6f4; border: 1px solid #45475a; font-family: Consolas; }
                QPushButton { background-color: #89b4fa; color: #1e1e2e; border-radius: 6px; padding: 6px 12px; font-weight: bold; }
                QPushButton:hover { background-color: #b4befe; }
                QPushButton:disabled { background-color: #45475a; color: #6c7086; }
                QPushButton#stop_btn { background-color: #f38ba8; }
                QPushButton#stop_btn:hover { background-color: #eba0ac; }
                QLineEdit { background-color: #313244; color: #cdd6f4; border: 1px solid #45475a; padding: 4px; border-radius: 4px; }
                QTabWidget::pane { border: 1px solid #45475a; border-radius: 6px; }
                QTabBar::tab { background: #313244; color: #cdd6f4; padding: 8px 16px; border-top-left-radius: 6px; border-top-right-radius: 6px; }
                QTabBar::tab:selected { background: #89b4fa; color: #1e1e2e; }
                QStatusBar { background-color: #181825; color: #a6e3a1; }
            """)
            self.terminal.setStyleSheet("background-color: #11111b; color: #cdd6f4;")
        else:
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #eff1f5; color: #4c4f69; }
                QMenuBar { background-color: #e6e9ef; color: #4c4f69; }
                QMenuBar::item:selected { background-color: #ccd0da; }
                QMenu { background-color: #eff1f5; color: #4c4f69; border: 1px solid #ccd0da; }
                QMenu::item:selected { background-color: #ccd0da; }
                QTextEdit, QPlainTextEdit { background-color: #ffffff; color: #4c4f69; border: 1px solid #ccd0da; font-family: Consolas; }
                QPushButton { background-color: #1e66f5; color: #ffffff; border-radius: 6px; padding: 6px 12px; font-weight: bold; }
                QPushButton:hover { background-color: #7287fd; }
                QPushButton:disabled { background-color: #ccd0da; color: #9ca0b0; }
                QPushButton#stop_btn { background-color: #d20f39; }
                QPushButton#stop_btn:hover { background-color: #e64553; }
                QLineEdit { background-color: #e6e9ef; color: #4c4f69; border: 1px solid #ccd0da; padding: 4px; border-radius: 4px; }
                QTabWidget::pane { border: 1px solid #ccd0da; border-radius: 6px; }
                QTabBar::tab { background: #e6e9ef; color: #4c4f69; padding: 8px 16px; border-top-left-radius: 6px; border-top-right-radius: 6px; }
                QTabBar::tab:selected { background: #1e66f5; color: #ffffff; }
                QStatusBar { background-color: #e6e9ef; color: #40a02b; }
            """)
            self.terminal.setStyleSheet("background-color: #ffffff; color: #4c4f69;")

    def change_font_size(self, delta):
        self.font_size = max(8, min(36, self.font_size + delta))
        self.editor.setFont(QFont("Consolas", self.font_size))
        self.output.setFont(QFont("Consolas", self.font_size - 1))
        self.terminal.setFont(QFont("Consolas", self.font_size - 1))
        self.save_settings()

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.apply_theme()
        self.save_settings()

    def new_file(self):
        self.loading_file = True
        self.editor.clear()
        self.output.clear()
        self.loading_file = False
        
        self.current_file = None
        self.is_modified = False
        self.update_title()
        self.status_bar.showMessage("New file created")

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open", "", "Python Files (*.py);;All Files (*)")
        if path:
            try:
                self.loading_file = True
                with open(path, "r", encoding="utf-8") as f:
                    self.editor.setPlainText(f.read())
                self.loading_file = False
                
                self.current_file = path
                self.is_modified = False
                self.update_title()
                self.status_bar.showMessage(f"Opened: {os.path.basename(path)}")
                
                # FIX 1: Be-rooz kardan-e line numbers
                self.editor.update_line_number_area_width(0)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def save_file(self):
        if self.current_file:
            try:
                with open(self.current_file, "w", encoding="utf-8") as f:
                    f.write(self.editor.toPlainText())
                self.is_modified = False
                self.update_title()
                self.status_bar.showMessage(f"Saved: {os.path.basename(self.current_file)}", 3000)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
        else:
            self.save_file_as()

    def save_file_as(self):
        default_name = "untitled.py"
        if self.current_file:
            default_name = os.path.basename(self.current_file)
            
        path, _ = QFileDialog.getSaveFileName(self, "Save As", default_name, "Python Files (*.py)")
        if path:
            self.current_file = path
            self.is_modified = False
            self.update_title()
            self.save_file()

    def close_file(self):
        self.new_file()

    def show_find_dialog(self):
        if not hasattr(self, 'find_dialog') or not self.find_dialog.isVisible():
            self.find_dialog = FindReplaceDialog(self.editor, self)
            self.find_dialog.show()
        else:
            self.find_dialog.raise_()
            self.find_dialog.activateWindow()
            
        cursor = self.editor.textCursor()
        if cursor.hasSelection():
            self.find_dialog.find_input.setText(cursor.selectedText())
        self.find_dialog.find_input.setFocus()

    def show_guide(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("User Guide")
        dlg.resize(400, 300)
        layout = QVBoxLayout(dlg)
        text = QLabel(
            "<b>CodeBaaf User Guide</b><br><br>"
            "• <b>Run:</b> F5 or ▶ button<br>"
            "• <b>Run in Terminal:</b> Ctrl+Enter<br>"
            "• <b>Save:</b> Ctrl+S<br>"
            "• <b>Open:</b> Ctrl+O<br>"
            "• <b>New:</b> Ctrl+N<br>"
            "• <b>Find:</b> Ctrl+F<br>"
            "• <b>Font Size:</b> Settings Menu (Ctrl+= / Ctrl+-)<br>"
            "• <b>Theme:</b> Settings -> Toggle Dark/Light Mode<br>"
            "• <b>Line Numbers:</b> Settings -> Show Line Numbers<br>"
            "• <b>Auto-complete:</b> Settings -> Enable Auto-complete<br><br>"
            "Output tab holds the results of the code. Terminal tab is for interaction and commands."
        )
        text.setWordWrap(True)
        layout.addWidget(text)
        btn = QDialogButtonBox(QDialogButtonBox.Ok)
        btn.accepted.connect(dlg.accept)
        layout.addWidget(btn)
        dlg.exec()

    def show_about(self):
        QMessageBox.about(
            self, "About CodeBaaf",
            "<h3>CodeBaaf (شناسه‌باف) v0.0</h3>"
            "<p>A lightweight, modern, and open-source Python IDE.</p>"
            "<p>Designed for the open-source community.</p>" 
            "<p>Write code, run it instantly, and weave your ideas into reality.</p>"
            "<p><br><b>Created by Hamed Shah-Hosseini, under A star</b></p>"
            "<p>GitHub: <a href='https://github.com/ostad-ai/CodeBaaf'>github.com/ostad-ai/CodeBaaf</a></p>"
        )

    def closeEvent(self, event):
        self._kill_terminal_tree()

        # FIX 2: Agar file khali ast va untitled ast, payaam nade
        if self.current_file is None and self.editor.toPlainText() == "":
            self.is_modified = False

        if self.is_modified and not self.loading_file:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                "You have unsaved changes. Do you want to save before exiting?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                QMessageBox.Save
            )
            if reply == QMessageBox.Save:
                self.save_file()
                event.accept()
            elif reply == QMessageBox.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CodeBaaf()
    window.show()
    sys.exit(app.exec())