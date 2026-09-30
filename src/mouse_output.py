"""OS mouse output via PyAutoGUI (imported lazily; needs a graphical session)."""


class MouseController:
    def __init__(self, offset_x: int = 0, offset_y: int = 0):
        import pyautogui

        # FAILSAFE must be off: touches in the projector corner map to (0, 0) and would
        # otherwise raise FailSafeException and leave the button pressed.
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0
        self._gui = pyautogui
        self.ox, self.oy = int(offset_x), int(offset_y)
        self.is_down = False

    def _abs(self, x, y):
        return int(round(float(x))) + self.ox, int(round(float(y))) + self.oy

    def handle(self, event: str, x, y) -> None:
        gui = self._gui
        ax, ay = self._abs(x, y)
        if event == "move":
            gui.moveTo(ax, ay)
        elif event == "down":
            gui.moveTo(ax, ay)
            if not self.is_down:
                gui.mouseDown(button="left")
                self.is_down = True
        elif event == "up":
            gui.moveTo(ax, ay)
            self.release()
        elif event == "click":
            self.release()
            gui.click(ax, ay)
        elif event == "right_click":
            self.release()
            gui.rightClick(ax, ay)

    def release(self) -> None:
        if self.is_down:
            self._gui.mouseUp(button="left")
            self.is_down = False
