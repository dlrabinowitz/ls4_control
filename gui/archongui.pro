TEMPLATE = app
TARGET = archongui
QT += core \
	widgets \
        network \
        concurrent \
        svg
CONFIG += debug_and_release
CONFIG(debug, debug|release) {
	DESTDIR = debug
} else {
	DESTDIR = release
}
OBJECTS_DIR = $$DESTDIR/.obj
MOC_DIR = $$DESTDIR/.moc
RCC_DIR = $$DESTDIR/.qrc
UI_DIR = $$DESTDIR/.ui

HEADERS += $$files(src/*.h)
SOURCES += $$files(src/*.cpp)

DEFINES += QWT_MOC_INCLUDE=1
HEADERS += $$files(src/qwt/*.h)
SOURCES += $$files(src/qwt/*.cpp)
INCLUDEPATH += src/qwt

win32 {
	LIBS += -lws2_32
}
