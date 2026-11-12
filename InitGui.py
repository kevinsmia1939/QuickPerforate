"""FreeCAD workbench registration."""

import os
import sys

import FreeCAD as App
import FreeCADGui as Gui

try:
    MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # FreeCAD executes InitGui.py without __file__ in some builds.
    MODULE_DIR = os.path.join(App.ConfigGet("UserAppData"), "Mod", "QuickPerforate")

if MODULE_DIR not in sys.path:
    sys.path.insert(0, MODULE_DIR)


class QuickPerforateWorkbench(Gui.Workbench):
    MenuText = "Quick Perforate"
    ToolTip = "Perforate a selected planar face with a decorative pattern"
    Icon = os.path.join(App.ConfigGet("UserAppData"), "Mod", "QuickPerforate",
                        "Resources", "quickperforate.svg")

    def Initialize(self):
        import QuickPerforateGui  # registers the command

        commands = ["QuickPerforate_Create"]
        self.appendToolbar("Quick Perforate", commands)
        self.appendMenu("Quick Perforate", commands)

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(QuickPerforateWorkbench())
