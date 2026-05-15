import sys
import os
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import Qt

# Mocking plugin object
class MockPlugin:
    def load_layer_mappings(self):
        return {"table1": {}, "table2": {}}
    @property
    def mergin_manager(self):
        return MockMerginManager()
    def save_current_project_configuration(self): pass
    def compare_project_with_db(self): pass
    def load_database_data(self): pass
    def push_project_data_to_backend(self): pass
    def prepare_mergin_project(self): pass
    def load_project_from_mergin(self): pass
    def refresh_data_via_api(self): pass
    def refresh_data_via_mergin(self): pass
    def sync_validated_data_to_backend(self): pass
    def open_validation_form(self): pass

class MockMerginManager:
    def list_projects(self):
        return [{"name": "Project 1", "id": "1"}, {"name": "Project 2", "id": "2"}]

app = QtWidgets.QApplication(sys.argv)

# Import the class from the file
from mrv_teraka_dockwidget import MrvTerakaDockWidget

# We need to mock the plugin for the constructor
widget = MrvTerakaDockWidget(MockPlugin())
widget.set_authenticated("user@example.com", "http://localhost:8000")
widget.show()

# Resize for a good view
widget.resize(400, 850)

# Take screenshot
widget.grab().save('/home/jules/verification/screenshots/ui_redesign.png')
