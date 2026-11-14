"""Register one perforation command in the Part workbench."""
import FreeCAD as App
from . import QuickPerforateGui

# FreeCAD's custom-toolbar mechanism loads this when Part is activated.
_toolbar = App.ParamGet("User parameter:BaseApp/Workbench/PartWorkbench/Toolbar/Custom_QuickPerforate")
_toolbar.SetString("Name", "Perforate")
_toolbar.SetBool("Active", True)
_toolbar.SetString("QuickPerforate_Create", "FreeCAD")
