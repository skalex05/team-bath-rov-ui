from threading import Thread

from PyQt6.QtWidgets import QRadioButton

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app import App


class ActionThread(Thread):
    def __init__(self, action: QRadioButton, target, retain_state=False, **kwargs):
        self.action: QRadioButton = action
        self.retain_state = retain_state
        self.kwargs = kwargs
        self.target = target
        kwargs["target"] = target
        super().__init__(**kwargs)
        action.clicked.connect(self.check_run)
    def check_run(self):
        if self.is_alive():
            self.action.setChecked(not self.action.isChecked())
            return
        else:
            self.start()
    def run(self):
        if not self.retain_state:
            self.action.setChecked(True)
        self.target()
        if not self.retain_state:
            self.action.setChecked(False)
        # Reinitialise the thread so that it can be restarted
        self.__init__(self.action, retain_state=self.retain_state, **self.kwargs)