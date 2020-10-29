# -*- coding: utf-8 -*-
"""
 ***************************************************************************
                                 A QGIS plugin
                              -------------------
        begin                : 2020-10-14
        git sha              : $Format:%H$
        copyright            : (C) 2020 by Jvenegasperu
        email                : jvenegasperu@gmail.com
 ***************************************************************************
"""

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

OSMWD_TOOLS_LOG = 'Actualizar medidas'


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

        stdMenu = self.createStandardContextMenu()
        newMenu = QMenu("I'm new!")
        stdMenu.insertMenu(stdMenu.actions()[0], newMenu)
        # menu.popup(ui.textedit.viewport().mapToGlobal(pos))

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
    def __init__(self, name, column_name, update_method=None):
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

    def changed_by_user(self, new_index=None):
        self.changed = True
        self.setStyleSheet('background-color: rgb(242,248,141); font-weight:bold;')
        if self.update_method:
            self.update_method()


class PropertiesComboBox(OSMWDComboBox):
    def __init__(self, properties):
        super().__init__('', '')
        properties_list = []
        for wd_property in properties:
            self.add_item(properties[wd_property], wd_property)
            properties_list.append(properties[wd_property])
        self.add_completer(properties_list)
        del(properties_list)


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
        self.cleanup_data_widget_grid_layout = QGridLayout(self.cleanup_data_content_widget)
        self.cleanup_data_widget_tab.setWidgetResizable(True)

        self.interpret_widget_tab = QScrollArea()
        self.interpret_content_widget = QWidget()
        self.interpret_widget_tab.setWidget(self.interpret_content_widget)
        self.interpret_widget_grid_layout = QGridLayout(self.interpret_content_widget)
        self.interpret_widget_tab.setWidgetResizable(True)

        self.tabs_widget.addTab(self.cleanup_data_widget_tab, 'Catastro Tecnico')
        self.tabs_widget.addTab(self.interpret_widget_tab, 'Catastro Comercial')


class ActualizarMedidasDock:
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
        self.menu = self.tr('&Catastro')

        self.toolbar = self.iface.addToolBar('Catastro')
        self.toolbar.setObjectName('Catastro')

        self.text_edit = {}
        self.line_edit = {}
        self.wd_properties = {}

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
        return QCoreApplication.translate('Catastro', message)

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
            text=self.tr('Catastro'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        for action in self.actions:
            self.iface.removePluginDatabaseMenu(
                self.tr('Catastro'),
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
            self.dockwidget.setWindowTitle("Gestion de Catastro EPS del Sector Saneamiento - v{}".format(VERSION))

        # wd_properties_file = Path(__file__).resolve().parent / 'wd properties.pickle'
        # with open(Path(wd_properties_file), 'rb') as handle:
        #     self.wd_properties = pickle.load(handle)

        from pprint import  pprint

        # cleanup_file = Path(__file__).resolve().parent / 'cleanup.json'
        # with open(cleanup_file) as data_file:
        #     data = json.load(data_file)

        # for group in data:
        #     # pprint(group)
        #     if group == 'Catastro Tecnico':
        #         for tag in data[group]:
        #             i = 0
        #             for entry in data[group][tag]:
        #                 for key, contents in entry.items():
        #                     self.text_edit[key] = OSMWDPlainTextEdit(self.dockwidget.cleanup_data_widget_tab,
        #                                                              text='\n'.join(contents))
        #                     self.text_edit[key].setMinimumHeight(len(contents) * 17 + 10)
        #                     self.line_edit[key] = QLineEdit(key, self.dockwidget.cleanup_data_widget_tab)
        #                     self.line_edit[key].setFixedWidth(140)
        #                     self.dockwidget.cleanup_data_widget_grid_layout.addWidget(self.text_edit[key], i, 0, 1, 3)
        #                     self.dockwidget.cleanup_data_widget_grid_layout.addWidget(self.line_edit[key], i, 3)
        #                     i += 1
        #     elif group == 'Catastro Comercial':
        #         pass

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
