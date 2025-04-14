from PyQt6.QtGui import QStandardItemModel, QStandardItem
from PyQt6.QtWidgets import QComboBox, QLabel
from PyQt6.QtCore import Qt, pyqtSignal


class MultiSelectComboBox(QComboBox):
    on_item_select = pyqtSignal()
    def __init__(self, fields_label: QLabel):
        super().__init__()
        self.setModel(QStandardItemModel(self))
        self.view().pressed.connect(self.handle_item_pressed)
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        self.fields_label = fields_label

        self.update_display()
        self.item_state_change = False
        self.currentTextChanged.connect(self.update_display)

    def add_item(self, text: str) -> None:
        item = QStandardItem(text)
        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        item.setData(Qt.CheckState.Unchecked, Qt.ItemDataRole.CheckStateRole)
        self.model().appendRow(item)
        item.setCheckState(Qt.CheckState.Unchecked)

    def handle_item_pressed(self, index: int) -> None:
        self.on_item_select.emit()
        self.item_state_change = True
        item = self.model().itemFromIndex(index)
        if item.checkState() == Qt.CheckState.Checked:
            item.setCheckState(Qt.CheckState.Unchecked)
        else:
            item.setCheckState(Qt.CheckState.Checked)
        self.update_display()

    def update_display(self) -> None:
        text = "Selected Fields"
        if self.currentText() != text:
            self.setCurrentText(text)

        selected_items = self.get_selected()

        if len(selected_items) > 0:
            self.fields_label.setText("\n".join(selected_items))
        else:
            self.fields_label.setText("No Fields Selected")
        return

    def get_selected(self) -> [str]:
        selected_items = [self.model().item(i).text()
                          for i in range(self.model().rowCount())
                          if self.model().item(i).checkState() == Qt.CheckState.Checked]

        return selected_items

    def hidePopup(self) -> None:
        if self.item_state_change:
            self.item_state_change = False
            return
        super().hidePopup()
