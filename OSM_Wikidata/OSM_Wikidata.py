# -*- coding: utf-8 -*-
"""
 ***************************************************************************
                                 A QGIS plugin
                              -------------------
        begin                : 2020-03-15
        git sha              : $Format:%H$
        copyright            : (C) 2020 by Polyglot
        email                : winfixit@gmail.com
 ***************************************************************************
"""
import json
import re

from .deploy import version
from pathlib import Path

from qgis.gui import QgsRubberBand, QgsDockWidget, QgsExpressionBuilderWidget
from qgis.core import (Qgis, QgsTask, QgsMessageLog, QgsProject, QgsFeature, QgsVectorLayer, QgsMapLayer,
                       QgsLayerTreeLayer, QgsMapLayerStyle, QgsWkbTypes, QgsExpression, QgsFeatureRequest,
                       QgsRectangle, QgsGeometry, QgsSpatialIndex, QgsDataSourceUri, QgsApplication)
from PyQt5.QtCore import (
    Qt,
    QCoreApplication,
    QRect,
    QSize,
    QPoint,
    QPointF,
    QDate,
    QTimer,
    QRegExp
)
from PyQt5.QtGui import (QIcon, QColor, QPainter, QIntValidator, QFont, QStandardItemModel, QStandardItem,
                         QTextDocument, QTextCharFormat, QSyntaxHighlighter, QTextCursor)
from PyQt5.QtWidgets import (
    QFrame,
    QAction,
    QDockWidget,
    QWidget,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QScrollBar,
    QHBoxLayout,
    QCheckBox,
    QFormLayout,
    QGridLayout,
    QSpinBox,
    QPushButton,
    QComboBox,
    QApplication,
    QMessageBox,
    QErrorMessage,
    QTableWidget,
    QTableWidgetItem,
    QSizePolicy,
    QDialog,
    QDialogButtonBox,
    QTabWidget,
    QHeaderView,
    QScrollArea,
    QRadioButton,
    QMenu,
    QSizePolicy,
    QTextEdit,
    QPlainTextEdit,
    QDateEdit,
    QCompleter,
    QCalendarWidget,
    QTableView,
    )

file_path = Path(__file__)
parent_dir = file_path.resolve().parent

VERSION = version.replace("_", ".")

APP_ICON = 'OpenStreetMap_Wikidata_logo.svg'

OSMWD_TOOLS_LOG = 'OSM_Wikidata'


class PerformQueriesTask(QgsTask):
    def __init__(self, description, queries, caller):
        super().__init__(description, QgsTask.CanCancel)
        self.queries = queries
        self.caller = caller
        self.busy = None
        self.exception = None

    def run(self):
        """This method periodically tests for isCancelled() to gracefully abort.
        raising exceptions would crash QGIS, so we handle them internally and
        raise them in self.finished
        """

        QgsMessageLog.logMessage('Started task "{}"'.format(self.description()),
                                 OSMWD_TOOLS_LOG, Qgis.Info)
        self.busy = True

        return True

    def finished(self, task_result):
        self.busy = False

        if task_result:
            pass
        else:
            if self.exception is None:
                pass
            else:
                QgsMessageLog.logMessage('Task "{}" Exception: {}'.format(self.description(), self.exception),
                                         OSMWD_TOOLS_LOG, Qgis.Critical, notifyUser=True)
                raise self.exception

    def cancel(self):
        QgsMessageLog.logMessage('Task "{name}" was cancelled'.format(name=self.description()),
                                 OSMWD_TOOLS_LOG, Qgis.Info)
        super().cancel()


class OSMWDFrame(QFrame):
    """
    By putting content in frames it is possible to show or hide them
    depending on whether the layer they show features for are enabled
    """
    def __init__(self, *__args):
        super().__init__(*__args)
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignTop)
        self.setStyleSheet("padding: 0px;")

    def add_widget(self, widget):
        self.layout.addWidget(widget)


class OSMWDPlainTextEdit(QPlainTextEdit):
    def __init__(self, *__args, text=''):
        super().__init__(*__args)
        font = QFont()
        font.setFamily("Courier")
        font.setFixedPitch(True)
        font.setPointSize(6)
        self.setFont(font)
        self.highlighter = RegexHighlighter(self.document())
        if text:
            self.setPlainText(text)
        self.textChanged.connect(self.text_changed)
        self.close_parentheses = {'(': ')',
                                  '[': ']',
                                  '{': '}'}

    def keyPressEvent(self, key):
        # print(dir(key.KeyRelease))
        super().keyPressEvent(key)
        if key.text() in self.close_parentheses:
            self.insertPlainText(self.close_parentheses[key.text()])
            self.moveCursor(QTextCursor.PreviousCharacter)

    def text_changed(self):
        self.highlighter.highlightBlock(self.toPlainText())

class OSMWDLabel(QLabel):
    """
    A QLabel that can be set disabled on creation
    """
    def __init__(self, text, enabled=True):
        super().__init__()
        self.setText(text)
        self.setEnabled(enabled)


class OSMWDPushButton(QPushButton):
    """
    A QPushButton that can be set to disabled at creation

    If query and run_query_method are set, pressing the button will cause the query
    to be submitted to the DB
    """
    def __init__(self, text, object_name, icon=None, enabled=True, shortcut_key="", tool_tip=''):
        super().__init__()
        self.query = query
        self.run_query_method = run_query_method
        self.setText(text)
        self.setMinimumWidth(40)
        if icon:
            self.setIcon(icon)
        if not enabled:
            self.setEnabled(False)
        self.setObjectName(object_name)
        if tool_tip:
            self.setToolTip(tool_tip)

        if shortcut_key:
            self.setShortcut(shortcut_key)


class OSMWDComboBox(QComboBox):
    """
    A QComboBox that keeps track of the values it is set to

    It colors differently if multiple values are in the data

    or when the user selects 1 value manually
    """
    def __init__(self, name, column_name, identifier=None, update_method=None):
        super().__init__()
        self.items = {}
        self.reverse_items = {}
        self.values = {}
        self.changed = False
        self.setObjectName(name)
        self.name = name
        self.column_name = column_name
        self.reset_values()
        self.setMaximumHeight(30)
        # The following line of code and the wheelEvent method cause the mouse wheel
        # only to work when the box is explicitly selected
        self.setFocusPolicy(Qt.StrongFocus)
        self.activated.connect(self.changed_by_user)
        self.setStyleSheet('width: 200px;')
        self.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        self.update_method = update_method

    def activate(self):
        self.deactivate()
        self.activated.connect(self.changed_by_user)

    def deactivate(self):
        try:
            self.activated.disconnect(self.changed_by_user)
        except TypeError:
            pass

    def add_completer(self, items):
        self.setEditable(True)
        self.setInsertPolicy(0)
        completer = QCompleter(items, self)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(False)
        self.setCompleter(completer)
        self.setStyleSheet('QScrollBar: vertical {width: 20px;}')

    def wheelEvent(self, e):
        if self.hasFocus():
            super().wheelEvent(e)

    def reset_values(self):
        self.deactivate()
        self.values.clear()
        self.setCurrentIndex(-1)
        self.changed = False
        self.setToolTip(self.name)
        self.setStyleSheet('background-color: rgb(254, 148, 125); font-weight:normal;')
        # reset background color for the items in the dropdown comboboxes back to neutral
        for key in self.items:
            self.setItemData(self.findText(key), QColor(222, 222, 222), Qt.BackgroundRole)

    def add_item(self, text, value, icon=None):
        self.items[text] = value
        self.reverse_items[value] = text
        if icon:
            super().addItem(icon, text)
        else:
            super().addItem(text)

    def insert_item(self, position, text, value, icon=None):
        self.items[text] = value
        self.reverse_items[value] = text
        if icon:
            super().insertItem(position, icon, text)
        else:
            super().insertItem(position, text)

    def current_value(self):
        if self.isEnabled():
            return self.current_item_text()
        else:
            # The combobox for streetname is set to disabled when the selection spans several communes
            return ''

    def current_item_text(self):
        super__current_text = super().currentText()
        if super__current_text in self.items:
            return self.items[super__current_text]
        else:
            return ''

    def set_value(self, value, update_tool_tip=True):
        index = self.findText(value)
        if index < 0:
            self.add_item(value, value)
            index = self.findText(value)
        if index >= 0:
            if value in self.values:
                self.values[value] += 1
            else:
                self.values[value] = 1
        if update_tool_tip:
            self.update_tool_tip()

    def update_tool_tip(self):
        if len(self.values) == 1:
            self.setStyleSheet('background-color: rgb(240, 240, 240); font-weight:normal;')
            self.setCurrentIndex(self.findText(list(self.values)[0]))
        else:
            self.setStyleSheet('background-color: rgb(255, 201, 140); font-weight:normal;')
            self.setCurrentIndex(-1)
            tool_tips = [self.name]
            for key, value in sorted(self.values.items(), key=lambda x: x[0]):
                tool_tips.append('{}x {}'.format(value, key))
                # highlight the rows in the drop down that represent segments from the selection
                self.setItemData(self.findText(key), QColor(205, 92, 92), Qt.BackgroundRole)
            self.setToolTip('\n'.join(tool_tips))

    def get_item_text_for(self, value):
        if value in self.reverse_items:
            return self.reverse_items[value]
        else:
            return ''

    def changed_by_preset(self):
        self.changed = True
        self.setStyleSheet('background-color: rgb(242,248,141); font-weight:bold;')

    def changed_by_user(self, new_index=None):
        self.changed_by_preset()
        if self.update_method:
            self.update_method()


class OSMWDDateEdit(QDateEdit):
    """
    A widget based on QDateEdit that keeps track of whether it was set by the user
    and changes color accordingly
    """
    def __init__(self, date=QDate.currentDate()):
        super().__init__()
        self.changed = False
        self.reset_value(date)
        self.setCalendarPopup(True)
        self.setDisplayFormat('dd-MM-yyyy')
        self.cal = self.calendarWidget()
        self.cal.setFirstDayOfWeek(Qt.Monday)
        self.cal.setHorizontalHeaderFormat(QCalendarWidget.SingleLetterDayNames)
        self.cal.setGridVisible(True)
        self.cal.setFixedWidth(300)
        self.editingFinished.connect(self.changed_by_user)

    def reset_value(self, date=QDate.currentDate()):
        self.changed = False
        self.setDate(date)
        self.setStyleSheet('background-color: rgb(240,240,240); font-weight:bold;')

    def changed_by_user(self):
        self.changed = True
        self.setStyleSheet('background-color: rgb(242,248,141); font-weight:bold;')


class OSMWDButtonBar(QWidget):
    """
    A QWidget containing a
    * Label showing how many features are selected
    * 1-6 buttons for presets
    * Buttons depending on context for copying, adding, saving, deleting and so on
    """
    def __init__(self, buttons, preset_buttons=None, *__args):
        super().__init__(*__args)
        self.setStyleSheet("padding: 0px;")
        self.layout = QHBoxLayout(self)
        image_dir = parent_dir / 'img'

        self.lbl_count = OSMWDLabel('', enabled=False)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.lbl_count.setFont(font)

        self.layout.addWidget(self.lbl_count)

        self.buttons = {}
        self.layout.addStretch()

        if preset_buttons:
            for button_letter in preset_buttons:
                self.buttons[button_letter] = OSMWDPushButton(button_letter, "preset_" + button_letter, enabled=False)
                self.buttons[button_letter].setMinimumWidth(20)
                self.buttons[button_letter].setVisible(False)
                self.layout.addWidget(self.buttons[button_letter])

        self.layout.addStretch()

        if 'straighten' in buttons:
            self.straighten_icon = QIcon(str(image_dir / 'StraightenAndDivideEvenly.svg'))
            self.buttons['straighten'] = OSMWDPushButton('', "btn_straighten", icon=self.straighten_icon)
            self.layout.addWidget(self.buttons['straighten'])
        if 'combine' in buttons:
            self.combine_icon = QIcon(str(image_dir / 'CombineTracks.svg'))
            self.buttons['combine'] = OSMWDPushButton('', "btn_combine", icon=self.combine_icon)
            self.layout.addWidget(self.buttons['combine'])
        if 'copy' in buttons:
            self.copy_icon = QIcon(str(image_dir / 'CopyToClipboard.svg'))
            self.buttons['copy'] = OSMWDPushButton('', "btn_copy", icon=self.copy_icon)
            self.layout.addWidget(self.buttons['copy'])
        if 'replace' in buttons:
            self.replace_icon = QIcon(str(image_dir / 'Replace.svg'))
            self.buttons['replace'] = OSMWDPushButton('', "btn_replace", icon=self.replace_icon)
            self.layout.addWidget(self.buttons['replace'])
        if 'add' in buttons:
            self.add_icon = QIcon(str(image_dir / 'Add.svg'))
            self.buttons['add'] = OSMWDPushButton('', "btn_add", icon=self.add_icon)
            self.layout.addWidget(self.buttons['add'])
        if 'save' in buttons:
            self.save_icon = QIcon(str(image_dir / 'Save.svg'))
            self.buttons['save'] = OSMWDPushButton('', "btn_save", icon=self.save_icon)
            self.layout.addWidget(self.buttons['save'])
        if 'historical' in buttons:
            self.historical_icon = QIcon(str(image_dir / 'Historical.svg'))
            self.buttons['historical'] = OSMWDPushButton('', "btn_historical", icon=self.historical_icon)
            self.layout.addWidget(self.buttons['historical'])
        if 'filter' in buttons:
            self.filter_icon = QIcon(str(image_dir / 'Filter.svg'))
            self.buttons['filter'] = OSMWDPushButton('', "btn_filter", icon=self.filter_icon)
            self.layout.addWidget(self.buttons['filter'])
        if 'link_segment' in buttons:
            self.link_segment_icon = QIcon(str(image_dir / 'LinkSegmentToPoi.svg'))
            self.buttons['link_segment'] = OSMWDPushButton('', "btn_link_segment", icon=self.link_segment_icon)
            self.layout.addWidget(self.buttons['link_segment'])
        if 'split_track' in buttons:
            self.split_track_icon = QIcon(str(image_dir / 'SplitTrack.svg'))
            self.buttons['split_track'] = OSMWDPushButton('', "btn_split_track", icon=self.split_track_icon)
            self.layout.addWidget(self.buttons['split_track'])
        if 'delete' in buttons:
            self.delete_icon = QIcon(str(image_dir / 'Remove.svg'))
            self.buttons['delete'] = OSMWDPushButton('', "btn_delete", icon=self.delete_icon)
            self.layout.addWidget(self.buttons['delete'])


class OSMWDSideBySide(QWidget):
    """
    A QWidget providing a horizontal layout for putting 2 widgets on a single line
    """
    def __init__(self, *__args):
        super().__init__(*__args)
        self.layout = QHBoxLayout(self)
        self.setStyleSheet("width: 200px; padding: 0px;")

    def add_widget(self, widget):
        self.layout.addWidget(widget)


def char_format(color='', style='', background=''):
    format = QTextCharFormat()
    if color:
        _color = QColor()
        _color.setNamedColor(color)
        format.setForeground(_color)

    if background:
        _background = QColor()
        _background.setNamedColor(background)
        format.setBackground(_background)

    if 'bold' in style:
        format.setFontWeight(QFont.Bold)
    if 'italic' in style:
        format.setFontItalic(True)

    return format


STYLES = {
    'operator': char_format('red'),
    'brace': char_format('darkGray'),
    'comment': char_format('Green', 'italic'),
    'numbers': char_format('brown'),
    'group': char_format(background='lightGray'),
    'literal': char_format('blue'),
}


class RegexHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for regular expressions.
    """

    operators = [
        r'\*', r'\+', r'\|', r'\^', r'\$'
    ]

    braces = [
        r'\{', r'\}', r'\(', r'\)', r'\[', r'\]',
    ]

    literals = [
        r'\\w', r'\\s', r'\\b', r'\\.', r'\\+'
    ]

    def __init__(self, document):
        # print(document.toPlainText())
        QSyntaxHighlighter.__init__(self, document)

        rules = [(r'(\(.*\))', 0, STYLES['group']),]

        rules += [(r'%s' % o, 0, STYLES['operator']) for o in RegexHighlighter.operators]
        rules += [(r'%s' % b, 0, STYLES['brace']) for b in RegexHighlighter.braces]
        rules += [(r'%s' % l, 0, STYLES['literal']) for l in RegexHighlighter.literals]

        rules += [
            # From '#' until a newline
            (r'#[^\n]*', 0, STYLES['comment']),

            # Numeric literals
            (r'\b[+-]?[0-9]+[lL]?\b', 0, STYLES['numbers']),


        ]

        self.rules = [(QRegExp(pat), index, fmt) for (pat, index, fmt) in rules]
        # print(self.rules)

    def highlightBlock(self, text):
        for expression, nth, character_format in self.rules:
            index = expression.indexIn(text, 0)
            while index >= 0:
                # We actually want the index of the nth match
                index = expression.pos(nth)
                length = len(expression.cap(nth))
                self.setFormat(index, length, character_format)
                index = expression.indexIn(text, index + length)

        self.setCurrentBlockState(0)

class DockOSMWD(QgsDockWidget):
    """
    These are all the GUI elements

    """

    def __init__(self, *__args):
        super().__init__(*__args)

        self.widget = {}
        self.frames = []

        self.tabs_widget = QTabWidget(self)
        self.tabs_widget.setMinimumWidth(400)
        self.tabs_widget.setMaximumWidth(800)
        # self.tabs_widget.setMaximumHeight(865)

        self.setWidget(self.tabs_widget)

        self.cleanup_data_widget_tab = QScrollArea()
        self.cleanup_data_content_widget = QWidget()
        self.cleanup_data_widget_tab.setWidget(self.cleanup_data_content_widget)
        self.cleanup_data_widget_form_layout = QFormLayout(self.cleanup_data_content_widget)
        self.cleanup_data_widget_tab.setWidgetResizable(True)

        self.interpret_widget = QWidget(self)
        self.interpret_widget.setLayout(QVBoxLayout(self.tabs_widget))

        self.process_widget = QWidget(self)
        self.process_widget.setLayout(QVBoxLayout(self.tabs_widget))

        self.references_widget = QWidget(self)
        self.references_widget.setLayout(QVBoxLayout(self.tabs_widget))

        self.tabs_widget.addTab(self.cleanup_data_widget_tab, 'Cleanup tags')
        self.tabs_widget.addTab(self.interpret_widget, 'Interpret tags')
        self.tabs_widget.addTab(self.process_widget, 'Process')
        self.tabs_widget.addTab(self.references_widget, 'References')

        buttons_dict = {
            'sc_500': ['copy', 'add', 'save', 'delete'],
        }

        # self.tab_widget.resize(500, QApplication.desktop().screenGeometry().bottom() - 100)


class OSMWikidataDock:
    """QGIS Plugin Implementation.
       In this class we define the functionality"""

    def __init__(self, iface):
        """Constructor.

        :param QgsInterface iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS application at run time.
        """
        # Save reference to the QGIS interface
        self.iface = iface
        self.dockwidget = None
        self.task = None

        self.actions = []
        self.menu = self.tr('&OpenStreetMap')

        self.toolbar = self.iface.addToolBar('OpenStreetMap')
        self.toolbar.setObjectName('OSM_Wikidata')

        self.text_edit = {}

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('OpenStreetMap', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):

        icon = QIcon(str(icon_path))
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToDatabaseMenu(self.menu, action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = parent_dir / 'img' / APP_ICON
        self.add_action(
            icon_path,
            text=self.tr('fb_tools_full_audit'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        for action in self.actions:
            self.iface.removePluginDatabaseMenu(
                self.tr('fb_tools_full_audit'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        if self.toolbar:
            del self.toolbar

    def load_icon(self, value):
        images_path_code = self.dockwidget.images_path / (value[:7] + '.svg')
        if not images_path_code.exists():
            images_path_code = self.dockwidget.does_not_exist_icon
        icon = QIcon(str(images_path_code))
        return icon

    def run(self):
        """
        This is invoked when the icon on the QGIS toolbar is clicked

        It fetches data from the database to create all the GUI widgets and to
        populate all the ComboBoxes

        """
        if not self.dockwidget:
            self.dockwidget = DockOSMWD()
            self.dockwidget.setWindowTitle("OpenStreetMap - Wikidata v{}".format(VERSION))

        cleanup_file = Path(__file__).resolve().parent / 'cleanup.json'
        with open(cleanup_file) as data_file:
            data = json.load(data_file)
        # from pprint import  pprint
        # pprint(data)
        for entry in data:
            # pprint(entry)
            for key, contents in entry.items():
                self.text_edit[key] = OSMWDPlainTextEdit(self.dockwidget.cleanup_data_widget_tab,
                                                         text='\n'.join(contents))
                self.text_edit[key].setMinimumHeight(len(contents) * 17 + 10)
                self.dockwidget.cleanup_data_widget_form_layout.addRow(key, self.text_edit[key])

        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)
        self.iface.openMessageLog()


        self.dockwidget.show()

    def enable_button_and_connect_slot(self, button, method):
        """
        When the buttons are disabled the side effects are switched off

        This method enables the buttons, so it responds to user interaction
        and connects it to the appropriate method
        :param button: QButton
        :param method: method to be invoked when button is pressed/released
        :return:
        """
        button.setEnabled(True)
        button.setToolTip('')
        # Make sure there are no existing connections, otherwise the action will be performed multiple times
        try:
            button.released.disconnect()
        except TypeError:
            pass
        button.released.connect(method)

    def perform_query_in_background_thread(self, task_name):
        self.task = PerformQueriesTask(task_name, self.queries, self)
        QgsApplication.taskManager().addTask(self.task)
        self.clear_selection_on_all_layers()

    def clear_selection_on_all_layers(self):
        for layer in self.iface.layerTreeView().selectedLayers():
            if layer.type() == QgsMapLayer.VectorLayer:
                layer.removeSelection()
        self.update_layout_widgets()

    @property
    def center_of_screen(self):
        return str(self.iface.mapCanvas().center()).replace('<QgsPointXY: ', '').replace('>', '')

    @staticmethod
    def get_layer_by_name(name):
        layers = QgsProject.instance().mapLayersByName(name)
        if layers:
            return layers[0]

    def activate_layer(self, name, set_active=True, set_visible=True):
        layer = self.get_layer_by_name(name)
        if layer:
            if set_active:
                self.iface.setActiveLayer(layer)
            lyr = QgsProject.instance().layerTreeRoot().findLayer(layer)
            if set_visible:
                lyr.setItemVisibilityChecked(True)
            else:
                lyr.setItemVisibilityChecked(False)

    def activate_segment(self):
        self.activate_layer('segment')
        self.activate_layer('track', set_active=False, set_visible=False)

    def segment_poi_toggle_visibility(self):
        layer = self.get_layer_by_name('segment_poi')
        if layer:
            lyr = QgsProject.instance().layerTreeRoot().findLayer(layer)
            if lyr.isVisible():
                lyr.setItemVisibilityChecked(False)
            else:
                lyr.setItemVisibilityChecked(True)
