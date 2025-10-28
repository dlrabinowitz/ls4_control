#include "archongui.h"

#include <QtGui>
#include <QApplication>

int main(int argc, char *argv[])
{
	QApplication a(argc, argv);
	TArchonGUI w(a.arguments().value(1));
	w.show();
	return a.exec();
}
