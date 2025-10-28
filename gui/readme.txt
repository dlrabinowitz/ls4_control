Archon GUI is tested using Qt 5.2, which can be downloaded from "http://qt-project.org/downloads".  To compile, first install Qt 5.2.  The Archon GUI code can either be compiled in the Qt Creator IDE or from the command line.  

To use the IDE, launch Qt Creator and open the project file "archongui.pro".  You can accept the default build options.  Select the debug or release build in the lower left of the IDE, and then run.

To compile from the command line, open a terminal with Qt in the path.  From the GUI folder, execute "qmake archongui.pro" followed by "make release" or "make debug".  Note that you'll have to replace "make" by "mingw32-make" on a Windows mingw system.  The executable will be created in the "release" or "debug" folder.