"""Register the Quick Perforate workbench."""
from pathlib import Path
import FreeCADGui as Gui


class QuickPerforateWorkbench(Gui.Workbench):
    MenuText = "Quick Perforate"
    ToolTip = "Perforate a selected planar face with a decorative pattern"
    Icon = str(Path(__file__).parent / "Resources" / "Icons" / "quickperforate.svg")

    def Initialize(self):
        from . import QuickPerforateGui
        commands = ["QuickPerforate_Create"]
        self.appendToolbar("Quick Perforate", commands)
        self.appendMenu("Quick Perforate", commands)

    def GetClassName(self):
        return "Gui::PythonWorkbench"


if "QuickPerforateWorkbench" not in Gui.listWorkbenches():
    Gui.addWorkbench(QuickPerforateWorkbench())
