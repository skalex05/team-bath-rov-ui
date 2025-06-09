from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QCheckBox


class MultiSelectWidget(QWidget):
    # Signal emitted when an item's selection state changes
    item_selection_changed = pyqtSignal(object, bool)

    def __init__(self, parent=None, items=None, single_selection=False, scroll_height=None):
        super().__init__(parent)
        self.single_selection = single_selection
        self.items = {}  # Dictionary to store display_text -> {'checkbox': QCheckBox, 'data': data}
        self.scroll_height = scroll_height
        self.setup_ui()

        if type(items) is list:
            for item in items:
                self.add_item(item)
        elif type(items) is dict:
            for item in items:
                self.add_item(item, items[item])
        elif items is not None:
            raise ValueError(f"'items' parameter must be of type 'list', 'dict' or 'None' not {type(items)}")

    def setup_ui(self):
        # Main layout
        main_layout = QVBoxLayout(self)

        # Create scroll area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        if self.scroll_height is not None:
            self.scroll_area.setMaximumHeight(self.scroll_height)

        # Create widget to hold checkboxes
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(5, 5, 5, 5)

        # Set the scroll widget
        self.scroll_area.setWidget(self.scroll_widget)

        # Add scroll area to main layout
        main_layout.addWidget(self.scroll_area)

        # Keep layout tight
        self.scroll_layout.addStretch()

    def add_item(self, display_text, data=None):
        if data is None:
            data = display_text
        if display_text in self.items:
            return  # Item already exists

        # Create checkbox
        checkbox = QCheckBox(display_text)
        checkbox.stateChanged.connect(lambda state, txt=display_text: self._on_item_changed(txt, state))

        # Store the checkbox reference and associated data
        self.items[display_text] = {'checkbox': checkbox, 'data': data}

        # Insert before the stretch (second-to-last position)
        insert_index = max(0, self.scroll_layout.count() - 1)
        self.scroll_layout.insertWidget(insert_index, checkbox)

    def remove_item(self, display_text):
        if display_text not in self.items:
            return  # Item doesn't exist

        # Get the checkbox and remove it
        checkbox = self.items[display_text]['checkbox']
        self.scroll_layout.removeWidget(checkbox)
        checkbox.deleteLater()

        # Remove from items dictionary
        del self.items[display_text]

    def _on_item_changed(self, display_text, state):
        is_checked = bool(state)

        # Handle single selection mode
        if self.single_selection and is_checked:
            # Uncheck all other items
            for other_display_text, item_info in self.items.items():
                if other_display_text != display_text and item_info['checkbox'].isChecked():
                    item_info['checkbox'].setChecked(False)

        # Emit signal with the associated data
        data = self.items[display_text]['data']
        self.item_selection_changed.emit(data, is_checked)

    def get_selected_items(self):
        selected = []
        for display_text, item_info in self.items.items():
            if item_info['checkbox'].isChecked():
                selected.append(item_info['data'])
        return selected

    def get_selected_display_texts(self):
        selected = []
        for display_text, item_info in self.items.items():
            if item_info['checkbox'].isChecked():
                selected.append(display_text)
        return selected

    def get_selected_item(self):
        for display_text, item_info in self.items.items():
            if item_info['checkbox'].isChecked():
                return item_info['data']
        return None

    def get_selected_display_text(self):
        for display_text, item_info in self.items.items():
            if item_info['checkbox'].isChecked():
                return display_text
        return None

    def set_selected_item(self, display_text):
        if display_text not in self.items:
            return

        if self.single_selection:
            # Uncheck all items first
            for item_info in self.items.values():
                item_info['checkbox'].setChecked(False)

        # Check the specified item
        self.items[display_text]['checkbox'].setChecked(True)

    def clear_all_items(self):
        """Remove all items from the widget."""
        items_to_remove = list(self.items.keys())
        for item in items_to_remove:
            self.remove_item(item)

    def set_item_checked(self, display_text, checked=True):
        if display_text not in self.items:
            return

        if self.single_selection and checked:
            # Use set_selected_item for consistency in single selection mode
            self.set_selected_item(display_text)
        else:
            self.items[display_text]['checkbox'].setChecked(checked)

    def get_all_items(self):
        return list(self.items.keys())

    def get_all_data(self):
        return [item_info['data'] for item_info in self.items.values()]

    def get_item_data(self, display_text):
        if display_text in self.items:
            return self.items[display_text]['data']
        return None

    def set_checkboxes_enabled(self, enabled):
        for display_text, item_info in self.items.items():
            item_info['checkbox'].setEnabled(enabled)
