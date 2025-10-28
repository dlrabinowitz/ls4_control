#include "modules.h"
#include <QRadioButton>
#include <QGroupBox>
#include <QShortcut>
#include <QApplication>
#include <QClipboard>

#include <qwt_plot_grid.h>

/////////////////////////////////////////////////////////////////////////////////
TModule::TModule(TArchonGUI *_parent, QString _key, int _slot)
{
	parent = _parent;
	key = _key;
	slot = _slot;
}

/////////////////////////////////////////////////////////////////////////////////
// Driver Module
DRIVER::DRIVER(TArchonGUI *parent, QString key, int slot) : TModule(parent, key, slot)
{
	build = parent->system.value(QString("MOD%1_VERSION").arg(slot)).split(".").value(2).toInt();
	backplane_build = parent->system.value("BACKPLANE_VERSION").split(".").value(2).toInt();
}
//---------------------------------------------------------------------------
void DRIVER::createUI()
{
	int i, y;
	QVBoxLayout *vl;
	QGridLayout *gl;
	QHBoxLayout *hl;
	QLabel *label;
	QPushButton *button;
	QFont font;
	QString s;
	QTabWidget *tabs;
	QWidget *tab;
	QShortcut *shortcut;

	// Module UI
	tabs = parent->systemTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: DRIVER").arg(slot));
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	gl = new QGridLayout();
	vl->addLayout(gl);
	gl->setHorizontalSpacing(10);
	gl->setVerticalSpacing(4);
	label = new QLabel("ID");
	font = label->font();
	font.setBold(true);
	label->setFont(font);
	gl->addWidget(label, 0, 0);
	label = new QLabel("Label");
	label->setFont(font);
	gl->addWidget(label, 0, 1);
	label = new QLabel("Fast Slew Rate (0.001..1000 V/us)");
	label->setFont(font);
	gl->addWidget(label, 0, 2);
	label = new QLabel("Slow Slew Rate (0.001..1000 V/us)");
	label->setFont(font);
	gl->addWidget(label, 0, 3);
	label = new QLabel("Enable");
	label->setFont(font);
	gl->addWidget(label, 0, 4);
	if ((build >= 1063) && (backplane_build >= 1064))
	{
		label = new QLabel("Source");
		label->setFont(font);
		gl->addWidget(label, 0, 5);
	}
	for (i = 0; i < DRIVER_COUNT; i++)
	{
		y = i + 1;
		// Driver ID and label
		label = new QLabel(QString("DRV%1").arg(i + 1));
		gl->addWidget(label, y, 0);
		leLabels[i] = new QLineEdit();
		gl->addWidget(leLabels[i], y, 1);
		// Slew rates
		leFastSlewRates[i] = new QLineEdit();
		gl->addWidget(leFastSlewRates[i], y, 2);
		leSlowSlewRates[i] = new QLineEdit();
		gl->addWidget(leSlowSlewRates[i], y, 3);
		// Driver enables
		cbEnabled[i] = new QCheckBox();
		gl->addWidget(cbEnabled[i], y, 4, Qt::AlignHCenter);
		// Source selection
		if ((build >= 1063) && (backplane_build >= 1064))
		{
			leSource[i] = new QLineEdit(QString::number(i + 1));
			gl->addWidget(leSource[i], y, 5);
		}
	}
	gl->setColumnStretch(6, 1);
	vl->addStretch(1);
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	button = new QPushButton("Apply");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(apply()));
	hl->addWidget(button);
	hl->addStretch(1);

	// Timing UI
	tabs = parent->waveformTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: DRIVER").arg(slot));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_C), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(copyClocks()));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_V), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(pasteClocks()));
	gl = new QGridLayout();
	tab->setLayout(gl);
	gl->setSpacing(10);
	label = new QLabel("Name");
	label->setFont(font);
	gl->addWidget(label, 0, 0);
	label = new QLabel("Level (V)");
	label->setFont(font);
	gl->addWidget(label, 0, 1);
	label = new QLabel("Slew Fast");
	label->setFont(font);
	gl->addWidget(label, 0, 2);
	label = new QLabel("Keep");
	label->setFont(font);
	gl->addWidget(label, 0, 3);
	label = new QLabel("ID");
	label->setFont(font);
	gl->addWidget(label, 0, 4);
	for (i = 0; i < DRIVER_COUNT; i++)
	{
		lRefLabels[i] = new QLabel();
		connect(leLabels[i], SIGNAL(textChanged(QString)), lRefLabels[i], SLOT(setText(QString)));
		leLevels[i] = new QLineEdit();
		cbSlews[i] = new QCheckBox();
		cbKeeps[i] = new QCheckBox();
		connect(leLevels[i], SIGNAL(textChanged(QString)), this, SLOT(clockChanged()));
		connect(cbSlews[i], SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		connect(cbKeeps[i], SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		label = new QLabel();
		label->setText(QString("CH%1").arg(i + 1));
		gl->addWidget(lRefLabels[i], i + 1, 0);
		gl->addWidget(leLevels[i], i + 1, 1);
		gl->addWidget(cbSlews[i], i + 1, 2, Qt::AlignHCenter);
		gl->addWidget(cbKeeps[i], i + 1, 3, Qt::AlignHCenter);
		gl->addWidget(label, i + 1, 4);
	}
	gl->setVerticalSpacing(4);
	gl->setColumnStretch(5, 1);
	gl->setRowStretch(DRIVER_COUNT + 1, 1);

	// Sync UI with current settings
	updateUI();
}
//---------------------------------------------------------------------------
void DRIVER::parseUI()
{
	for (int i = 0; i < DRIVER_COUNT; i++)
	{
		parent->config.insert(key + QString("/LABEL%1").arg(i + 1), leLabels[i]->text());
		parent->config.insert(key + QString("/FASTSLEWRATE%1").arg(i + 1), leFastSlewRates[i]->text());
		parent->config.insert(key + QString("/SLOWSLEWRATE%1").arg(i + 1), leSlowSlewRates[i]->text());
		parent->config.insert(key + QString("/ENABLE%1").arg(i + 1), cbEnabled[i]->isChecked() ? "1" : "0");
		if ((build >= 1063) && (backplane_build >= 1064))
			parent->config.insert(key + QString("/SOURCE%1").arg(i + 1), leSource[i]->text());
	}
}
//---------------------------------------------------------------------------
void DRIVER::updateUI()
{
	for (int i = 0; i < DRIVER_COUNT; i++)
	{
		leLabels[i]->setText(parent->config.value(key + QString("/LABEL%1").arg(i + 1)));
		leFastSlewRates[i]->setText(parent->config.value(key + QString("/FASTSLEWRATE%1").arg(i + 1), "1"));
		leSlowSlewRates[i]->setText(parent->config.value(key + QString("/SLOWSLEWRATE%1").arg(i + 1), "1"));
		cbEnabled[i]->setChecked(parent->config.value(key + QString("/ENABLE%1").arg(i + 1)) == "1");
		leSlowSlewRates[i]->setText(parent->config.value(key + QString("/SLOWSLEWRATE%1").arg(i + 1), "1"));
		if ((build >= 1063) && (backplane_build >= 1064))
			leSource[i]->setText(parent->config.value(key + QString("/SOURCE%1").arg(i + 1), QString::number(i + 1)));
	}
}
//---------------------------------------------------------------------------
void DRIVER::apply()
{
	parent->applyModule(slot);
}
//---------------------------------------------------------------------------
void DRIVER::setClocks(const QVariantMap& map)
{
	int i;
	QStringList sl = map.value(key).toString().split(",");

	for (i = 0; i < DRIVER_COUNT; i++)
	{
		leLevels[i]->setText(sl.value(i * 3, ""));
		cbSlews[i]->setChecked(sl.value(i * 3 + 1, "1") == "1");
		cbKeeps[i]->setChecked(sl.value(i * 3 + 2, "1") == "1");
		leLevels[i]->setEnabled(!cbKeeps[i]->isChecked());
		cbSlews[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
}
//---------------------------------------------------------------------------
void DRIVER::getClocks(QVariantMap& map)
{
	int i;
	QStringList sl;

	for (i = 0; i < DRIVER_COUNT; i++)
	{
		sl.append(leLevels[i]->text());
		sl.append(cbSlews[i]->isChecked() ? "1" : "0");
		sl.append(cbKeeps[i]->isChecked() ? "1" : "0");
	}
	map.insert(key, sl.join(","));
}
//---------------------------------------------------------------------------
void DRIVER::clockChanged()
{
	int i;

	for (i = 0; i < DRIVER_COUNT; i++)
	{
		leLevels[i]->setEnabled(!cbKeeps[i]->isChecked());
		cbSlews[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
	parent->clockChanged();
}
//---------------------------------------------------------------------------
void DRIVER::copyClocks()
{
	int i;
	QStringList sl;
	QString s;

	for (i = 0; i < DRIVER_COUNT; i++)
	{
		sl.append(leLevels[i]->text());
		sl.append(cbSlews[i]->isChecked() ? "1" : "0");
		sl.append(cbKeeps[i]->isChecked() ? "1" : "0");
	}
	s = sl.join(",");
	QApplication::clipboard()->setText(s);
}
//---------------------------------------------------------------------------
void DRIVER::pasteClocks()
{
	int i;
	QStringList sl;

	sl = QApplication::clipboard()->text().split(",");
	for (i = 0; i < DRIVER_COUNT; i++)
	{
		leLevels[i]->setText(sl.value(i * 3, "0"));
		cbSlews[i]->setChecked(sl.value(i * 3 + 1, "1") == "1");
		cbKeeps[i]->setChecked(sl.value(i * 3 + 2, "1") == "1");
		leLevels[i]->setEnabled(!cbKeeps[i]->isChecked());
		cbSlews[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
}

/////////////////////////////////////////////////////////////////////////////////
// DriverX Module
DRIVERX::DRIVERX(TArchonGUI *parent, QString key, int slot) : TModule(parent, key, slot)
{
	build = parent->system.value(QString("MOD%1_VERSION").arg(slot)).split(".").value(2).toInt();
	backplane_build = parent->system.value("BACKPLANE_VERSION").split(".").value(2).toInt();
}
//---------------------------------------------------------------------------
void DRIVERX::createUI()
{
	int i, y;
	QVBoxLayout *vl;
	QGridLayout *gl;
	QHBoxLayout *hl;
	QLabel *label;
	QPushButton *button;
	QFont font;
	QString s;
	QTabWidget *tabs;
	QWidget *tab;
	QShortcut *shortcut;

	// Module UI
	tabs = parent->systemTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: DRIVERX").arg(slot));
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	gl = new QGridLayout();
	vl->addLayout(gl);
	gl->setHorizontalSpacing(10);
	gl->setVerticalSpacing(4);
	label = new QLabel("ID");
	font = label->font();
	font.setBold(true);
	label->setFont(font);
	gl->addWidget(label, 0, 0);
	label = new QLabel("Label");
	label->setFont(font);
	gl->addWidget(label, 0, 1);
	label = new QLabel("Fast Slew Rate (0.001..1000 V/us)");
	label->setFont(font);
	gl->addWidget(label, 0, 2);
	label = new QLabel("Slow Slew Rate (0.001..1000 V/us)");
	label->setFont(font);
	gl->addWidget(label, 0, 3);
	label = new QLabel("Enable");
	label->setFont(font);
	gl->addWidget(label, 0, 4);
	label = new QLabel("Source");
	label->setFont(font);
	gl->addWidget(label, 0, 5);
	for (i = 0; i < DRIVERX_COUNT; i++)
	{
		y = i + 1;
		// Driver ID and label
		label = new QLabel(QString("DRV%1").arg(i + 1));
		gl->addWidget(label, y, 0);
		leLabels[i] = new QLineEdit();
		gl->addWidget(leLabels[i], y, 1);
		// Slew rates
		leFastSlewRates[i] = new QLineEdit();
		gl->addWidget(leFastSlewRates[i], y, 2);
		leSlowSlewRates[i] = new QLineEdit();
		gl->addWidget(leSlowSlewRates[i], y, 3);
		// Driver enables
		cbEnabled[i] = new QCheckBox();
		gl->addWidget(cbEnabled[i], y, 4, Qt::AlignHCenter);
		// Source selection
		leSource[i] = new QLineEdit(QString::number(i + 1));
		gl->addWidget(leSource[i], y, 5);
	}
	gl->setColumnStretch(6, 1);
	vl->addStretch(1);
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	button = new QPushButton("Apply");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(apply()));
	hl->addWidget(button);
	hl->addStretch(1);

	// Timing UI
	tabs = parent->waveformTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: DRIVERX").arg(slot));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_C), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(copyClocks()));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_V), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(pasteClocks()));
	gl = new QGridLayout();
	tab->setLayout(gl);
	gl->setSpacing(10);
	label = new QLabel("Name");
	label->setFont(font);
	gl->addWidget(label, 0, 0);
	label = new QLabel("Level (V)");
	label->setFont(font);
	gl->addWidget(label, 0, 1);
	label = new QLabel("Slew Fast");
	label->setFont(font);
	gl->addWidget(label, 0, 2);
	label = new QLabel("Keep");
	label->setFont(font);
	gl->addWidget(label, 0, 3);
	label = new QLabel("ID");
	label->setFont(font);
	gl->addWidget(label, 0, 4);
	for (i = 0; i < DRIVERX_COUNT; i++)
	{
		lRefLabels[i] = new QLabel();
		connect(leLabels[i], SIGNAL(textChanged(QString)), lRefLabels[i], SLOT(setText(QString)));
		leLevels[i] = new QLineEdit();
		cbSlews[i] = new QCheckBox();
		cbKeeps[i] = new QCheckBox();
		connect(leLevels[i], SIGNAL(textChanged(QString)), this, SLOT(clockChanged()));
		connect(cbSlews[i], SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		connect(cbKeeps[i], SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		label = new QLabel();
		label->setText(QString("CH%1").arg(i + 1));
		gl->addWidget(lRefLabels[i], i + 1, 0);
		gl->addWidget(leLevels[i], i + 1, 1);
		gl->addWidget(cbSlews[i], i + 1, 2, Qt::AlignHCenter);
		gl->addWidget(cbKeeps[i], i + 1, 3, Qt::AlignHCenter);
		gl->addWidget(label, i + 1, 4);
	}
	gl->setVerticalSpacing(4);
	gl->setColumnStretch(5, 1);
	gl->setRowStretch(DRIVERX_COUNT + 1, 1);

	// Sync UI with current settings
	updateUI();
}
//---------------------------------------------------------------------------
void DRIVERX::parseUI()
{
	for (int i = 0; i < DRIVERX_COUNT; i++)
	{
		parent->config.insert(key + QString("/LABEL%1").arg(i + 1), leLabels[i]->text());
		parent->config.insert(key + QString("/FASTSLEWRATE%1").arg(i + 1), leFastSlewRates[i]->text());
		parent->config.insert(key + QString("/SLOWSLEWRATE%1").arg(i + 1), leSlowSlewRates[i]->text());
		parent->config.insert(key + QString("/ENABLE%1").arg(i + 1), cbEnabled[i]->isChecked() ? "1" : "0");
		if ((build >= 1063) && (backplane_build >= 1064))
			parent->config.insert(key + QString("/SOURCE%1").arg(i + 1), leSource[i]->text());
	}
}
//---------------------------------------------------------------------------
void DRIVERX::updateUI()
{
	for (int i = 0; i < DRIVERX_COUNT; i++)
	{
		leLabels[i]->setText(parent->config.value(key + QString("/LABEL%1").arg(i + 1)));
		leFastSlewRates[i]->setText(parent->config.value(key + QString("/FASTSLEWRATE%1").arg(i + 1), "1"));
		leSlowSlewRates[i]->setText(parent->config.value(key + QString("/SLOWSLEWRATE%1").arg(i + 1), "1"));
		cbEnabled[i]->setChecked(parent->config.value(key + QString("/ENABLE%1").arg(i + 1)) == "1");
		leSlowSlewRates[i]->setText(parent->config.value(key + QString("/SLOWSLEWRATE%1").arg(i + 1), "1"));
		if ((build >= 1063) && (backplane_build >= 1064))
			leSource[i]->setText(parent->config.value(key + QString("/SOURCE%1").arg(i + 1), QString::number(i + 1)));
	}
}
//---------------------------------------------------------------------------
void DRIVERX::apply()
{
	parent->applyModule(slot);
}
//---------------------------------------------------------------------------
void DRIVERX::setClocks(const QVariantMap& map)
{
	int i;
	QStringList sl = map.value(key).toString().split(",");

	for (i = 0; i < DRIVERX_COUNT; i++)
	{
		leLevels[i]->setText(sl.value(i * 3, ""));
		cbSlews[i]->setChecked(sl.value(i * 3 + 1, "1") == "1");
		cbKeeps[i]->setChecked(sl.value(i * 3 + 2, "1") == "1");
		leLevels[i]->setEnabled(!cbKeeps[i]->isChecked());
		cbSlews[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
}
//---------------------------------------------------------------------------
void DRIVERX::getClocks(QVariantMap& map)
{
	int i;
	QStringList sl;

	for (i = 0; i < DRIVERX_COUNT; i++)
	{
		sl.append(leLevels[i]->text());
		sl.append(cbSlews[i]->isChecked() ? "1" : "0");
		sl.append(cbKeeps[i]->isChecked() ? "1" : "0");
	}
	map.insert(key, sl.join(","));
}
//---------------------------------------------------------------------------
void DRIVERX::clockChanged()
{
	int i;

	for (i = 0; i < DRIVERX_COUNT; i++)
	{
		leLevels[i]->setEnabled(!cbKeeps[i]->isChecked());
		cbSlews[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
	parent->clockChanged();
}
//---------------------------------------------------------------------------
void DRIVERX::copyClocks()
{
	int i;
	QStringList sl;
	QString s;

	for (i = 0; i < DRIVERX_COUNT; i++)
	{
		sl.append(leLevels[i]->text());
		sl.append(cbSlews[i]->isChecked() ? "1" : "0");
		sl.append(cbKeeps[i]->isChecked() ? "1" : "0");
	}
	s = sl.join(",");
	QApplication::clipboard()->setText(s);
}
//---------------------------------------------------------------------------
void DRIVERX::pasteClocks()
{
	int i;
	QStringList sl;

	sl = QApplication::clipboard()->text().split(",");
	for (i = 0; i < DRIVERX_COUNT; i++)
	{
		leLevels[i]->setText(sl.value(i * 3, "0"));
		cbSlews[i]->setChecked(sl.value(i * 3 + 1, "1") == "1");
		cbKeeps[i]->setChecked(sl.value(i * 3 + 2, "1") == "1");
		leLevels[i]->setEnabled(!cbKeeps[i]->isChecked());
		cbSlews[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
}

/////////////////////////////////////////////////////////////////////////////////
// AD Module
AD::AD(TArchonGUI *parent, QString key, int slot) : TModule(parent, key, slot)
{
	rev = char(parent->system.value(QString("MOD%1_REV").arg(slot)).toInt()) + 'A';
}
//---------------------------------------------------------------------------
void AD::createUI()
{
	int i, x, y;
	QVBoxLayout *vl;
	QGridLayout *gl;
	QHBoxLayout *hl;
	QLabel *label;
	QPushButton *button;
	QFont font;
	QTabWidget *tabs;
	QWidget *tab;
	QShortcut *shortcut;

	// Module UI
	tabs = parent->systemTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: AD").arg(slot));
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	gl = new QGridLayout();
	vl->addLayout(gl);
	gl->setHorizontalSpacing(10);
	gl->setVerticalSpacing(4);
	y = 0;
	if (rev <= 'C')
	{
		label = new QLabel("Clamp Low (-2.5V..2.5V):");
		gl->addWidget(label, y, 0);
		leClampLow = new QLineEdit();
		gl->addWidget(leClampLow, y++, 1);
		label = new QLabel("Clamp High (-2.5V..2.5V):");
		gl->addWidget(label, y, 0);
		leClampHigh = new QLineEdit();
		gl->addWidget(leClampHigh, y++, 1);
	}
	else
	{
		for (i = 0; i < 4; i++)
		{
			label = new QLabel(QString("Clamp %1: (-2.5V..2.5V):").arg(i + 1));
			gl->addWidget(label, y, 0);
			leClamps[i] = new QLineEdit();
			gl->addWidget(leClamps[i], y++, 1);
		}
	}
	label = new QLabel("Preamp Gain:");
	gl->addWidget(label, y, 0);
	cbGain = new QComboBox();
	cbGain->addItems(QStringList() << "LOW" << "HIGH");
	cbGain->setCurrentIndex(0);
	gl->addWidget(cbGain, y++, 1);
	gl->setColumnMinimumWidth(2, 20);
	gl->setColumnStretch(5, 1);
	if ((rev >= 'G') && ENABLE_AD_CALIBRATION)
	{
		y = 0;
		x = 3;
		label = new QLabel("Calibration Levels (V)");
		gl->addWidget(label, y++, x);
		for (i = 0; i < 8; i++)
		{
			leCal[i] = new QLineEdit("0.0");
			gl->addWidget(leCal[i], y++, x);
		}
		button = new QPushButton("Clear Calibration");
		gl->addWidget(button, y++, x);
		QObject::connect(button, SIGNAL(clicked()), this, SLOT(clearCal()));
		button = new QPushButton("Set Calibration");
		gl->addWidget(button, y++, x);
		QObject::connect(button, SIGNAL(clicked()), this, SLOT(setCal()));
	}
	vl->addStretch(1);
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	button = new QPushButton("Apply");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(apply()));
	hl->addWidget(button);
	hl->addStretch(1);

	// Timing UI
	tabs = parent->waveformTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: AD").arg(slot));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_C), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(copyClocks()));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_V), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(pasteClocks()));
	gl = new QGridLayout();
	tab->setLayout(gl);
	gl->setSpacing(10);
	label = new QLabel("Clamp");
	font = label->font();
	font.setBold(true);
	label->setFont(font);
	gl->addWidget(label, 0, 0);
	label = new QLabel("Keep");
	label->setFont(font);
	gl->addWidget(label, 0, 1);
	cbClamp = new QCheckBox();
	gl->addWidget(cbClamp, 1, 0, Qt::AlignHCenter);
	cbKeep = new QCheckBox();
	gl->addWidget(cbKeep, 1, 1, Qt::AlignHCenter);
	connect(cbClamp, SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
	connect(cbKeep, SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
	gl->setVerticalSpacing(4);
	gl->setColumnStretch(2, 1);
	gl->setRowStretch(2, 1);

	// Sync UI with current settings
	updateUI();
}
//---------------------------------------------------------------------------
void AD::parseUI()
{
	int i;

	if (rev <= 'C')
	{
		parent->config.insert(key + "/CLAMPHIGH", leClampHigh->text());
		parent->config.insert(key + "/CLAMPLOW", leClampLow->text());
	}
	else
	{
		for (i = 0; i < 4; i++)
			parent->config.insert(key + "/CLAMP" + QString::number(i + 1), leClamps[i]->text());
	}
	parent->config.insert(key + "/PREAMPGAIN", QString::number(cbGain->currentIndex()));
}
//---------------------------------------------------------------------------
void AD::updateUI()
{
	int i;

	if (rev <= 'C')
	{
		leClampHigh->setText(parent->config.value(key + "/CLAMPHIGH", "0.0"));
		leClampLow->setText(parent->config.value(key + "/CLAMPLOW", "0.0"));
	}
	else
	{
		for (i = 0; i < 4; i++)
			leClamps[i]->setText(parent->config.value(key + "/CLAMP" + QString::number(i + 1), "0.0"));
	}
	cbGain->setCurrentIndex(qBound(0, parent->config.value(key + "/PREAMPGAIN").toInt(), 1));
}
//---------------------------------------------------------------------------
void AD::apply()
{
	parent->applyModule(slot);
}
//---------------------------------------------------------------------------
void AD::clearCal()
{
	QString s;
	s = QString("CLEARAD%1").arg(slot);
	parent->direct(s);
}
//---------------------------------------------------------------------------
void AD::setCal()
{
	int i;
	QString s;
	QStringList sl;
	for (i = 0; i < 8; i++)
		sl.append(leCal[i]->text());
	s = QString("CALAD%1,").arg(slot);
	s.append(sl.join(","));
	parent->direct(s);
}
//---------------------------------------------------------------------------
void AD::setClocks(const QVariantMap& map)
{
	QStringList sl = map.value(key).toString().split(",");

	cbClamp->setChecked(sl.value(0, "1") == "1");
	cbKeep->setChecked(sl.value(1, "1") == "1");
}
//---------------------------------------------------------------------------
void AD::getClocks(QVariantMap& map)
{
	QStringList sl;

	sl.append(cbClamp->isChecked() ? "1" : "0");
	sl.append(cbKeep->isChecked() ? "1" : "0");
	map.insert(key, sl.join(","));
}
//---------------------------------------------------------------------------
void AD::clockChanged()
{
	cbClamp->setEnabled(!cbKeep->isChecked());
	parent->clockChanged();
}
//---------------------------------------------------------------------------
void AD::copyClocks()
{
	QStringList sl;
	QString s;

	sl.append(cbClamp->isChecked() ? "1" : "0");
	sl.append(cbKeep->isChecked() ? "1" : "0");
	s = sl.join(",");
	QApplication::clipboard()->setText(s);
}
//---------------------------------------------------------------------------
void AD::pasteClocks()
{
	QStringList sl;

	sl = QApplication::clipboard()->text().split(",");
	cbClamp->setChecked(sl.value(0, "1") == "1");
	cbKeep->setChecked(sl.value(1, "1") == "1");
}

/////////////////////////////////////////////////////////////////////////////////
// ADF Module
ADF::ADF(TArchonGUI *parent, QString key, int slot) : TModule(parent, key, slot)
{
	rev = char(parent->system.value(QString("MOD%1_REV").arg(slot)).toInt()) + 'A';
}
//---------------------------------------------------------------------------
void ADF::createUI()
{
	int i, x, y;
	QVBoxLayout *vl;
	QGridLayout *gl;
	QHBoxLayout *hl;
	QLabel *label;
	QPushButton *button;
	QFont font;
	QTabWidget *tabs;
	QWidget *tab;
	QShortcut *shortcut;

	// Module UI
	tabs = parent->systemTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: ADF").arg(slot));
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	gl = new QGridLayout();
	vl->addLayout(gl);
	gl->setHorizontalSpacing(10);
	gl->setVerticalSpacing(4);
	y = 0;
	for (i = 0; i < 4; i++)
	{
		label = new QLabel(QString("Clamp %1: (-2.5V..2.5V):").arg(i + 1));
		gl->addWidget(label, y, 0);
		leClamps[i] = new QLineEdit();
		gl->addWidget(leClamps[i], y++, 1);
	}
	gl->setColumnStretch(5, 1);
	if ((rev >= 'B') && ENABLE_AD_CALIBRATION)
	{
		y = 0;
		x = 3;
		label = new QLabel("Calibration Levels (V)");
		gl->addWidget(label, y++, x);
		for (i = 0; i < 8; i++)
		{
			leCal[i] = new QLineEdit("0.0");
			gl->addWidget(leCal[i], y++, x);
		}
		button = new QPushButton("Clear Calibration");
		gl->addWidget(button, y++, x);
		QObject::connect(button, SIGNAL(clicked()), this, SLOT(clearCal()));
		button = new QPushButton("Set Calibration");
		gl->addWidget(button, y++, x);
		QObject::connect(button, SIGNAL(clicked()), this, SLOT(setCal()));
	}
	vl->addStretch(1);
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	button = new QPushButton("Apply");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(apply()));
	hl->addWidget(button);
	hl->addStretch(1);

	// Timing UI
	tabs = parent->waveformTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: ADF").arg(slot));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_C), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(copyClocks()));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_V), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(pasteClocks()));
	gl = new QGridLayout();
	tab->setLayout(gl);
	gl->setSpacing(10);
	label = new QLabel("Clamp");
	font = label->font();
	font.setBold(true);
	label->setFont(font);
	gl->addWidget(label, 0, 0);
	label = new QLabel("Keep");
	label->setFont(font);
	gl->addWidget(label, 0, 1);
	cbClamp = new QCheckBox();
	gl->addWidget(cbClamp, 1, 0, Qt::AlignHCenter);
	cbKeep = new QCheckBox();
	gl->addWidget(cbKeep, 1, 1, Qt::AlignHCenter);
	connect(cbClamp, SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
	connect(cbKeep, SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
	gl->setVerticalSpacing(4);
	gl->setColumnStretch(2, 1);
	gl->setRowStretch(2, 1);

	// Sync UI with current settings
	updateUI();
}
//---------------------------------------------------------------------------
void ADF::parseUI()
{
	int i;

	for (i = 0; i < 4; i++)
		parent->config.insert(key + "/CLAMP" + QString::number(i + 1), leClamps[i]->text());
}
//---------------------------------------------------------------------------
void ADF::updateUI()
{
	int i;

	for (i = 0; i < 4; i++)
		leClamps[i]->setText(parent->config.value(key + "/CLAMP" + QString::number(i + 1), "0.0"));
}
//---------------------------------------------------------------------------
void ADF::apply()
{
	parent->applyModule(slot);
}
//---------------------------------------------------------------------------
void ADF::clearCal()
{
	QString s;
	s = QString("CLEARAD%1").arg(slot);
	parent->direct(s);
}
//---------------------------------------------------------------------------
void ADF::setCal()
{
	int i;
	QString s;
	QStringList sl;
	for (i = 0; i < 8; i++)
		sl.append(leCal[i]->text());
	s = QString("CALAD%1,").arg(slot);
	s.append(sl.join(","));
	parent->direct(s);
}
//---------------------------------------------------------------------------
void ADF::setClocks(const QVariantMap& map)
{
	QStringList sl = map.value(key).toString().split(",");

	cbClamp->setChecked(sl.value(0, "1") == "1");
	cbKeep->setChecked(sl.value(1, "1") == "1");
}
//---------------------------------------------------------------------------
void ADF::getClocks(QVariantMap& map)
{
	QStringList sl;

	sl.append(cbClamp->isChecked() ? "1" : "0");
	sl.append(cbKeep->isChecked() ? "1" : "0");
	map.insert(key, sl.join(","));
}
//---------------------------------------------------------------------------
void ADF::clockChanged()
{
	cbClamp->setEnabled(!cbKeep->isChecked());
	parent->clockChanged();
}
//---------------------------------------------------------------------------
void ADF::copyClocks()
{
	QStringList sl;
	QString s;

	sl.append(cbClamp->isChecked() ? "1" : "0");
	sl.append(cbKeep->isChecked() ? "1" : "0");
	s = sl.join(",");
	QApplication::clipboard()->setText(s);
}
//---------------------------------------------------------------------------
void ADF::pasteClocks()
{
	QStringList sl;

	sl = QApplication::clipboard()->text().split(",");
	cbClamp->setChecked(sl.value(0, "1") == "1");
	cbKeep->setChecked(sl.value(1, "1") == "1");
}

/////////////////////////////////////////////////////////////////////////////////
// ADX Module
ADX::ADX(TArchonGUI *parent, QString key, int slot) : TModule(parent, key, slot)
{
	rev = char(parent->system.value(QString("MOD%1_REV").arg(slot)).toInt()) + 'A';
}
//---------------------------------------------------------------------------
void ADX::createUI()
{
	int i, y;
	QVBoxLayout *vl;
	QGridLayout *gl;
	QHBoxLayout *hl;
	QLabel *label;
	QPushButton *button;
	QFont font;
	QTabWidget *tabs;
	QWidget *tab;
	QShortcut *shortcut;

	// Module UI
	tabs = parent->systemTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: ADX").arg(slot));
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	gl = new QGridLayout();
	vl->addLayout(gl);
	gl->setHorizontalSpacing(10);
	gl->setVerticalSpacing(4);
	y = 0;
	for (i = 0; i < 4; i++)
	{
		label = new QLabel(QString("Clamp %1: (-2.5V..2.5V):").arg(i + 1));
		gl->addWidget(label, y, 0);
		leClamps[i] = new QLineEdit();
		gl->addWidget(leClamps[i], y++, 1);
	}
	gl->setColumnStretch(5, 1);
	vl->addStretch(1);
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	button = new QPushButton("Apply");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(apply()));
	hl->addWidget(button);
	hl->addStretch(1);

	// Timing UI
	tabs = parent->waveformTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: ADX").arg(slot));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_C), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(copyClocks()));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_V), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(pasteClocks()));
	gl = new QGridLayout();
	tab->setLayout(gl);
	gl->setSpacing(10);
	label = new QLabel("Clamp");
	font = label->font();
	font.setBold(true);
	label->setFont(font);
	gl->addWidget(label, 0, 0);
	label = new QLabel("Keep");
	label->setFont(font);
	gl->addWidget(label, 0, 1);
	cbClamp = new QCheckBox();
	gl->addWidget(cbClamp, 1, 0, Qt::AlignHCenter);
	cbKeep = new QCheckBox();
	gl->addWidget(cbKeep, 1, 1, Qt::AlignHCenter);
	connect(cbClamp, SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
	connect(cbKeep, SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
	gl->setVerticalSpacing(4);
	gl->setColumnStretch(2, 1);
	gl->setRowStretch(2, 1);

	// Sync UI with current settings
	updateUI();
}
//---------------------------------------------------------------------------
void ADX::parseUI()
{
	int i;

	for (i = 0; i < 4; i++)
		parent->config.insert(key + "/CLAMP" + QString::number(i + 1), leClamps[i]->text());
}
//---------------------------------------------------------------------------
void ADX::updateUI()
{
	int i;

	for (i = 0; i < 4; i++)
		leClamps[i]->setText(parent->config.value(key + "/CLAMP" + QString::number(i + 1), "0.0"));
}
//---------------------------------------------------------------------------
void ADX::apply()
{
	parent->applyModule(slot);
}
//---------------------------------------------------------------------------
void ADX::setClocks(const QVariantMap& map)
{
	QStringList sl = map.value(key).toString().split(",");

	cbClamp->setChecked(sl.value(0, "1") == "1");
	cbKeep->setChecked(sl.value(1, "1") == "1");
}
//---------------------------------------------------------------------------
void ADX::getClocks(QVariantMap& map)
{
	QStringList sl;

	sl.append(cbClamp->isChecked() ? "1" : "0");
	sl.append(cbKeep->isChecked() ? "1" : "0");
	map.insert(key, sl.join(","));
}
//---------------------------------------------------------------------------
void ADX::clockChanged()
{
	cbClamp->setEnabled(!cbKeep->isChecked());
	parent->clockChanged();
}
//---------------------------------------------------------------------------
void ADX::copyClocks()
{
	QStringList sl;
	QString s;

	sl.append(cbClamp->isChecked() ? "1" : "0");
	sl.append(cbKeep->isChecked() ? "1" : "0");
	s = sl.join(",");
	QApplication::clipboard()->setText(s);
}
//---------------------------------------------------------------------------
void ADX::pasteClocks()
{
	QStringList sl;

	sl = QApplication::clipboard()->text().split(",");
	cbClamp->setChecked(sl.value(0, "1") == "1");
	cbKeep->setChecked(sl.value(1, "1") == "1");
}

/////////////////////////////////////////////////////////////////////////////////
// ADLN Module
ADLN::ADLN(TArchonGUI *parent, QString key, int slot) : TModule(parent, key, slot)
{
	rev = char(parent->system.value(QString("MOD%1_REV").arg(slot)).toInt()) + 'A';
}
//---------------------------------------------------------------------------
void ADLN::createUI()
{
	int i, x, y;
	QVBoxLayout *vl;
	QGridLayout *gl;
	QHBoxLayout *hl;
	QLabel *label;
	QPushButton *button;
	QFont font;
	QTabWidget *tabs;
	QWidget *tab;
	QShortcut *shortcut;

	// Module UI
	tabs = parent->systemTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: ADLN").arg(slot));
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	gl = new QGridLayout();
	vl->addLayout(gl);
	gl->setHorizontalSpacing(10);
	gl->setVerticalSpacing(4);
	y = 0;
	for (i = 0; i < 4; i++)
	{
		label = new QLabel(QString("Clamp %1: (-2.5V..2.5V):").arg(i + 1));
		gl->addWidget(label, y, 0);
		leClamps[i] = new QLineEdit();
		gl->addWidget(leClamps[i], y++, 1);
	}
	gl->setColumnStretch(5, 1);
	if (ENABLE_AD_CALIBRATION)
	{
		y = 0;
		x = 3;
		label = new QLabel("Calibration Levels (V)");
		gl->addWidget(label, y++, x);
		for (i = 0; i < 8; i++)
		{
			leCal[i] = new QLineEdit("0.0");
			gl->addWidget(leCal[i], y++, x);
		}
		button = new QPushButton("Clear Calibration");
		gl->addWidget(button, y++, x);
		QObject::connect(button, SIGNAL(clicked()), this, SLOT(clearCal()));
		button = new QPushButton("Set Calibration");
		gl->addWidget(button, y++, x);
		QObject::connect(button, SIGNAL(clicked()), this, SLOT(setCal()));
	}
	vl->addStretch(1);
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	button = new QPushButton("Apply");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(apply()));
	hl->addWidget(button);
	hl->addStretch(1);

	// Timing UI
	tabs = parent->waveformTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: ADLN").arg(slot));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_C), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(copyClocks()));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_V), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(pasteClocks()));
	gl = new QGridLayout();
	tab->setLayout(gl);
	gl->setSpacing(10);
	label = new QLabel("Clamp");
	font = label->font();
	font.setBold(true);
	label->setFont(font);
	gl->addWidget(label, 0, 0);
	label = new QLabel("Keep");
	label->setFont(font);
	gl->addWidget(label, 0, 1);
	cbClamp = new QCheckBox();
	gl->addWidget(cbClamp, 1, 0, Qt::AlignHCenter);
	cbKeep = new QCheckBox();
	gl->addWidget(cbKeep, 1, 1, Qt::AlignHCenter);
	connect(cbClamp, SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
	connect(cbKeep, SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
	gl->setVerticalSpacing(4);
	gl->setColumnStretch(2, 1);
	gl->setRowStretch(2, 1);

	// Sync UI with current settings
	updateUI();
}
//---------------------------------------------------------------------------
void ADLN::parseUI()
{
	int i;

	for (i = 0; i < 4; i++)
		parent->config.insert(key + "/CLAMP" + QString::number(i + 1), leClamps[i]->text());
}
//---------------------------------------------------------------------------
void ADLN::updateUI()
{
	int i;

	for (i = 0; i < 4; i++)
		leClamps[i]->setText(parent->config.value(key + "/CLAMP" + QString::number(i + 1), "0.0"));
}
//---------------------------------------------------------------------------
void ADLN::apply()
{
	parent->applyModule(slot);
}
//---------------------------------------------------------------------------
void ADLN::clearCal()
{
	QString s;
	s = QString("CLEARAD%1").arg(slot);
	parent->direct(s);
}
//---------------------------------------------------------------------------
void ADLN::setCal()
{
	int i;
	QString s;
	QStringList sl;
	for (i = 0; i < 8; i++)
		sl.append(leCal[i]->text());
	s = QString("CALAD%1,").arg(slot);
	s.append(sl.join(","));
	parent->direct(s);
}
//---------------------------------------------------------------------------
void ADLN::setClocks(const QVariantMap& map)
{
	QStringList sl = map.value(key).toString().split(",");

	cbClamp->setChecked(sl.value(0, "1") == "1");
	cbKeep->setChecked(sl.value(1, "1") == "1");
}
//---------------------------------------------------------------------------
void ADLN::getClocks(QVariantMap& map)
{
	QStringList sl;

	sl.append(cbClamp->isChecked() ? "1" : "0");
	sl.append(cbKeep->isChecked() ? "1" : "0");
	map.insert(key, sl.join(","));
}
//---------------------------------------------------------------------------
void ADLN::clockChanged()
{
	cbClamp->setEnabled(!cbKeep->isChecked());
	parent->clockChanged();
}
//---------------------------------------------------------------------------
void ADLN::copyClocks()
{
	QStringList sl;
	QString s;

	sl.append(cbClamp->isChecked() ? "1" : "0");
	sl.append(cbKeep->isChecked() ? "1" : "0");
	s = sl.join(",");
	QApplication::clipboard()->setText(s);
}
//---------------------------------------------------------------------------
void ADLN::pasteClocks()
{
	QStringList sl;

	sl = QApplication::clipboard()->text().split(",");
	cbClamp->setChecked(sl.value(0, "1") == "1");
	cbKeep->setChecked(sl.value(1, "1") == "1");
}

/////////////////////////////////////////////////////////////////////////////////
// ADM Module
ADM::ADM(TArchonGUI *parent, QString key, int slot) : TModule(parent, key, slot)
{
	rev = char(parent->system.value(QString("MOD%1_REV").arg(slot)).toInt()) + 'A';
}
//---------------------------------------------------------------------------
void ADM::createUI()
{
	QTabWidget *tabs;
	QWidget *tab;

	// Module UI
	tabs = parent->systemTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: ADM").arg(slot));
	// Sync UI with current settings
	updateUI();
}
//---------------------------------------------------------------------------
void ADM::parseUI()
{
}
//---------------------------------------------------------------------------
void ADM::updateUI()
{
}
//---------------------------------------------------------------------------
void ADM::setClocks(const QVariantMap& map)
{
	Q_UNUSED(map);
}
//---------------------------------------------------------------------------
void ADM::getClocks(QVariantMap& map)
{
	Q_UNUSED(map);
}
//---------------------------------------------------------------------------
void ADM::clockChanged()
{
}
//---------------------------------------------------------------------------
void ADM::copyClocks()
{
}
//---------------------------------------------------------------------------
void ADM::pasteClocks()
{
}

/////////////////////////////////////////////////////////////////////////////////
// LVBias Module
LVBIAS::LVBIAS(TArchonGUI *parent, QString key, int slot) : TModule(parent, key, slot)
{
	build = parent->system.value(QString("MOD%1_VERSION").arg(slot)).split(".").value(2).toInt();
}
//---------------------------------------------------------------------------
void LVBIAS::createUI()
{
	int i;
	QVBoxLayout *vl;
	QGridLayout *gl;
	QHBoxLayout *hl;
	QLabel *label;
	QPushButton *button;
	QTabWidget *tabs;
	QWidget *tab;
	QShortcut *shortcut;
	QFont boldFont, fixedFont;
	QString s;

	// Module UI
	tabs = parent->systemTabs();
	tab = new QWidget();
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	gl = new QGridLayout();
	vl->addLayout(gl);
	gl->setHorizontalSpacing(10);
	gl->setVerticalSpacing(4);

	// LVLC
	label = new QLabel("Command");
	boldFont = label->font();
	boldFont.setBold(true);
	fixedFont = label->font();
	fixedFont.setFamily("Monotype");
	fixedFont.setStyleHint(QFont::TypeWriter);
	label->setFont(boldFont);
	gl->addWidget(label, 0, 2, Qt::AlignHCenter);
	label = new QLabel("Measured");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 3, 1, 2, Qt::AlignHCenter);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 0);
	label = new QLabel("Label");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 1);
	label = new QLabel("V (-14..14)");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 2);
	label = new QLabel("V");
	label->setAlignment(Qt::AlignHCenter);
	label->setFont(boldFont);
	gl->addWidget(label, 1, 3);
	label = new QLabel("mA");
	label->setAlignment(Qt::AlignHCenter);
	label->setFont(boldFont);
	gl->addWidget(label, 1, 4);
	label = new QLabel("Order");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 5);
	for (i = 0; i < LVLC_COUNT; i++)
	{
		// IDs and labels
		label = new QLabel(QString("LV%1").arg(i + 1));
		gl->addWidget(label, i + 2, 0);
		lvlc_label[i] = new QLineEdit();
		gl->addWidget(lvlc_label[i], i + 2, 1);
		// Commanded voltage
		lvlc_v_cmd[i] = new QLineEdit("0.0");
		gl->addWidget(lvlc_v_cmd[i], i + 2, 2);
		// Voltage and current readings
		lvlc_v[i] = new QLabel("-");
		lvlc_v[i]->setFont(fixedFont);
		gl->addWidget(lvlc_v[i], i + 2, 3);
		lvlc_i[i] = new QLabel("-");
		lvlc_i[i]->setFont(fixedFont);
		gl->addWidget(lvlc_i[i], i + 2, 4);
		// Power on order
		lvlc_order[i] = new QLineEdit("0");
		gl->addWidget(lvlc_order[i], i + 2, 5);
	}
	gl->setColumnMinimumWidth(6, 30);

	// LVHC
	label = new QLabel("Command");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 9, 1, 2, Qt::AlignHCenter);
	label = new QLabel("Measured");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 11, 1, 2, Qt::AlignHCenter);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 7);
	label = new QLabel("Label");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 8);
	label = new QLabel("V (-14..14)");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 9);
	label = new QLabel("mA (0..500)");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 10);
	label = new QLabel("V");
	label->setAlignment(Qt::AlignHCenter);
	label->setFont(boldFont);
	gl->addWidget(label, 1, 11);
	label = new QLabel("mA");
	label->setAlignment(Qt::AlignHCenter);
	label->setFont(boldFont);
	gl->addWidget(label, 1, 12);
	label = new QLabel("Order");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 13);
	label = new QLabel("Enable");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 14);
	for (i = 0; i < LVHC_COUNT; i++)
	{
		// IDs and labels
		label = new QLabel(QString("LV%1").arg(i + LVLC_COUNT + 1));
		gl->addWidget(label, i + 2, 7);
		lvhc_label[i] = new QLineEdit();
		gl->addWidget(lvhc_label[i], i + 2, 8);
		// Commanded voltage and current limit
		lvhc_v_cmd[i] = new QLineEdit("0.0");
		gl->addWidget(lvhc_v_cmd[i], i + 2, 9);
		lvhc_il[i] = new QLineEdit("0");
		gl->addWidget(lvhc_il[i], i + 2, 10);
		// Voltage and current readings
		lvhc_v[i] = new QLabel("-");
		lvhc_v[i]->setFont(fixedFont);
		gl->addWidget(lvhc_v[i], i + 2, 11);
		lvhc_i[i] = new QLabel("-");
		lvhc_i[i]->setFont(fixedFont);
		gl->addWidget(lvhc_i[i], i + 2, 12);
		// Power on order
		lvhc_order[i] = new QLineEdit("0");
		gl->addWidget(lvhc_order[i], i + 2, 13);
		// Channel enable
		lvhc_enable[i] = new QCheckBox();
		gl->addWidget(lvhc_enable[i], i + 2, 14, Qt::AlignHCenter);
	}
	gl->setColumnMinimumWidth(15, 30);

	// DIO
	label = new QLabel("Digital I/O");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 16, 1, 3, Qt::AlignHCenter);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 16);
	label = new QLabel("Label");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 17);
	label = new QLabel("Source");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 18);
	label = new QLabel("Status");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 19);
	label = new QLabel("Direction");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 20);
	for (i = 0; i < DIO_COUNT; i++)
	{
		// IDs and labels
		label = new QLabel(QString("DIO%1").arg(i + 1));
		gl->addWidget(label, i + 2, 16);
		leLabels[i] = new QLineEdit();
		gl->addWidget(leLabels[i], i + 2, 17);
		cbSources[i] = new QComboBox();
		cbSources[i]->addItem("Low");
		cbSources[i]->addItem("High");
		cbSources[i]->addItem("Clocked");
		cbSources[i]->addItem("VCPU");
		gl->addWidget(cbSources[i], i + 2, 18);
		lStatus[i] = new QLabel("-");
		gl->addWidget(lStatus[i], i + 2, 19);
	}
	for (i = 0; i < DIO_COUNT / 2; i++)
	{
		cbDirections[i] = new QComboBox();
		cbDirections[i]->addItem("Input");
		cbDirections[i]->addItem("Output");
		gl->addWidget(cbDirections[i], i * 2 + 2, 20, 2, 1);
	}
	label = new QLabel("DIO Power");
	label->setFont(boldFont);
	gl->addWidget(label, DIO_COUNT + 3, 16, 1, 2);
	cbPower = new QComboBox();
	cbPower->addItem("Disabled");
	cbPower->addItem("Enabled");
	gl->addWidget(cbPower, DIO_COUNT + 3, 18);
	gl->setColumnStretch(19, 1);

	vl->addStretch(1);
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	button = new QPushButton("Apply");
	connect(button, SIGNAL(clicked()), this, SLOT(apply()));
	hl->addWidget(button);
	hl->addStretch(1);
	QScrollArea *scroll = new QScrollArea();
	scroll->setWidget(tab);
	if (parent->system.value(QString("MOD%1_TYPE").arg(slot)).toInt() == MOD_TYPE_LVBIAS)
		s = QString("Slot %1: LVBIAS").arg(slot);
	else
		s = QString("Slot %1: LVXBIAS").arg(slot);
	tabs->addTab(scroll, s);

	// Timing UI
	tabs = parent->waveformTabs();
	tab = new QWidget();
	tabs->addTab(tab, s);
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_C), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(copyClocks()));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_V), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(pasteClocks()));
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	gl = new QGridLayout();
	vl->addLayout(gl);
	gl->setSpacing(10);
	label = new QLabel("Label");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 0);
	label = new QLabel("State");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 1);
	label = new QLabel("Keep");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 2);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 3);
	for (i = 0; i < DIO_COUNT; i++)
	{
		lRefLabels[i] = new QLabel();
		connect(leLabels[i], SIGNAL(textChanged(QString)), lRefLabels[i], SLOT(setText(QString)));
		cbStates[i] = new QCheckBox();
		cbKeeps[i] = new QCheckBox();
		connect(cbStates[i], SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		connect(cbKeeps[i], SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		label = new QLabel();
		label->setText(QString("DIO%1").arg(i + 1));
		gl->addWidget(lRefLabels[i], i + 1, 0);
		gl->addWidget(cbStates[i], i + 1, 1, Qt::AlignHCenter);
		gl->addWidget(cbKeeps[i], i + 1, 2, Qt::AlignHCenter);
		gl->addWidget(label, i + 1, 3);
	}
	gl->setVerticalSpacing(4);
	gl->setColumnStretch(4, 1);
	if (build > 832)
	{
		vl->addSpacing(10);
		gl = new QGridLayout();
		vl->addLayout(gl);
		label = new QLabel("Command");
		label->setFont(boldFont);
		gl->addWidget(label, 0, 0);
		label = new QLabel("Channel (1-30)");
		label->setFont(boldFont);
		gl->addWidget(label, 0, 1);
		label = new QLabel("Voltage (V)");
		label->setFont(boldFont);
		gl->addWidget(label, 0, 2);
		cbBiasCmd = new QCheckBox();
		connect(cbBiasCmd, SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		leBiasChannel = new QLineEdit("1");
		connect(leBiasChannel, SIGNAL(textChanged(QString)), this, SLOT(clockChanged()));
		leBiasVoltage = new QLineEdit("0.0");
		connect(leBiasVoltage, SIGNAL(textChanged(QString)), this, SLOT(clockChanged()));
		gl->addWidget(cbBiasCmd, 1, 0, Qt::AlignHCenter);
		gl->addWidget(leBiasChannel, 1, 1);
		gl->addWidget(leBiasVoltage, 1, 2);
		gl->setVerticalSpacing(4);
		gl->setColumnStretch(3, 1);
	}
	vl->addStretch();

	// VCPU UI
	tabs = parent->vcpuTabs();
	tab = new QWidget();
	tabs->addTab(tab, s);
	gl = new QGridLayout();
	tab->setLayout(gl);
	gl->setSpacing(10);
	teVCPU = new QPlainTextEdit();
	teVCPU->setLineWrapMode(QPlainTextEdit::NoWrap);
	label = new QLabel("Code");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 0);
	gl->addWidget(teVCPU, 1, 0, VCPU_COUNT + 1, 1);
	label = new QLabel("Register");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 1);
	label = new QLabel("Input");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 2);
	label = new QLabel("Output");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 3);
	for (i = 0; i < VCPU_COUNT; i++)
	{
		label = new QLabel(QString("REG%1").arg(i));
		gl->addWidget(label, i + 1, 1);
		leVCPUInReg[i] = new QLineEdit("0");
		gl->addWidget(leVCPUInReg[i], i + 1, 2);
		lVCPUOutReg[i] = new QLabel("-");
		gl->addWidget(lVCPUOutReg[i], i + 1, 3);
	}
	gl->setColumnStretch(0, 1);
	gl->setRowStretch(VCPU_COUNT + 1, 1);
	gl->setColumnMinimumWidth(3, 100);
	hl = new QHBoxLayout();
	button = new QPushButton("Apply");
	connect(button, SIGNAL(clicked()), this, SLOT(applyDIO()));
	hl->addWidget(button);
	hl->addStretch(0);
	gl->addLayout(hl, VCPU_COUNT + 2, 0);

	// Sync UI with current settings
	updateUI();
}
//---------------------------------------------------------------------------
void LVBIAS::parseUI()
{
	int i, count;
	QStringList sl;

	for (i = 0; i < LVLC_COUNT; i++)
	{
		parent->config.insert(key + QString("/LVLC_LABEL%1").arg(i + 1), lvlc_label[i]->text());
		parent->config.insert(key + QString("/LVLC_V%1").arg(i + 1), lvlc_v_cmd[i]->text());
		parent->config.insert(key + QString("/LVLC_ORDER%1").arg(i + 1), lvlc_order[i]->text());
	}
	for (i = 0; i < LVHC_COUNT; i++)
	{
		parent->config.insert(key + QString("/LVHC_LABEL%1").arg(i + 1), lvhc_label[i]->text());
		parent->config.insert(key + QString("/LVHC_V%1").arg(i + 1), lvhc_v_cmd[i]->text());
		parent->config.insert(key + QString("/LVHC_IL%1").arg(i + 1), lvhc_il[i]->text());
		parent->config.insert(key + QString("/LVHC_ORDER%1").arg(i + 1), lvhc_order[i]->text());
		parent->config.insert(key + QString("/LVHC_ENABLE%1").arg(i + 1), lvhc_enable[i]->isChecked() ? "1" : "0");
	}
	for (i = 0; i < DIO_COUNT; i++)
	{
		parent->config.insert(key + QString("/DIO_LABEL%1").arg(i + 1), leLabels[i]->text());
		parent->config.insert(key + QString("/DIO_SOURCE%1").arg(i + 1), QString::number(cbSources[i]->currentIndex()));
	}
	for (i = 0; i < DIO_COUNT / 2; i++)
	{
		parent->config.insert(key + QString("/DIO_DIR%1%2").arg(i * 2 + 1).arg(i * 2 + 2), QString::number(cbDirections[i]->currentIndex()));
	}
	parent->config.insert(key + "/DIO_POWER", QString::number(cbPower->currentIndex()));
	// VCPU code
	sl = teVCPU->toPlainText().split('\n');
	count = sl.count();
	parent->config.insert(key + "/VCPU_LINES", QString::number(count));
	for (i = 0; i < count; i++)
		parent->config.insert(key + QString("/VCPU_LINE%1").arg(i), sl[i]);
	for (i = 0; i < VCPU_COUNT; i++)
		parent->config.insert(key + QString("/VCPU_INREG%1").arg(i), leVCPUInReg[i]->text());
}
//---------------------------------------------------------------------------
void LVBIAS::updateUI()
{
	int i, count;
	bool ok;

	for (i = 0; i < LVLC_COUNT; i++)
	{
		lvlc_label[i]->setText(parent->config.value(key + QString("/LVLC_LABEL%1").arg(i + 1)));
		lvlc_v_cmd[i]->setText(parent->config.value(key + QString("/LVLC_V%1").arg(i + 1), "0.0"));
		lvlc_order[i]->setText(parent->config.value(key + QString("/LVLC_ORDER%1").arg(i + 1), "0"));
	}
	for (i = 0; i < LVHC_COUNT; i++)
	{
		lvhc_label[i]->setText(parent->config.value(key + QString("/LVHC_LABEL%1").arg(i + 1)));
		lvhc_v_cmd[i]->setText(parent->config.value(key + QString("/LVHC_V%1").arg(i + 1), "0.0"));
		lvhc_il[i]->setText(parent->config.value(key + QString("/LVHC_IL%1").arg(i + 1), "0"));
		lvhc_order[i]->setText(parent->config.value(key + QString("/LVHC_ORDER%1").arg(i + 1), "0"));
		lvhc_enable[i]->setChecked(parent->config.value(key + QString("/LVHC_ENABLE%1").arg(i + 1)) == "1");
	}
	for (i = 0; i < DIO_COUNT; i++)
	{
		leLabels[i]->setText(parent->config.value(key + QString("/DIO_LABEL%1").arg(i + 1)));
		cbSources[i]->setCurrentIndex(qBound(0, parent->config.value(key + QString("/DIO_SOURCE%1").arg(i + 1)).toInt(), 3));
	}
	for (i = 0; i < DIO_COUNT / 2; i++)
	{
		cbDirections[i]->setCurrentIndex(qBound(0, parent->config.value(key + QString("/DIO_DIR%1%2").arg(i * 2 + 1).arg(i * 2 + 2)).toInt(), 1));
	}
	cbPower->setCurrentIndex(qBound(0, parent->config.value(key + "/DIO_POWER").toInt(), 1));
	// VCPU code
	count = parent->config.value(key + "/VCPU_LINES").toInt(&ok);
	if (ok)
	{
		teVCPU->clear();
		for (i = 0; i < count; i++)
			teVCPU->appendPlainText(parent->config.value(key + QString("/VCPU_LINE%1").arg(i)));
	}
	for (i = 0; i < VCPU_COUNT; i++)
		leVCPUInReg[i]->setText(parent->config.value(key + QString("/VCPU_INREG%1").arg(i + 1), "0"));
}
//---------------------------------------------------------------------------
void LVBIAS::apply()
{
	parent->applyModule(slot);
}
//---------------------------------------------------------------------------
void LVBIAS::applyDIO()
{
	parent->applyModuleDIO(slot);
}
//---------------------------------------------------------------------------
void LVBIAS::setClocks(const QVariantMap& map)
{
	int i;
	QStringList sl = map.value(key).toString().split(",");

	for (i = 0; i < DIO_COUNT; i++)
	{
		cbStates[i]->setChecked(sl.value(i * 2, "1") == "1");
		cbKeeps[i]->setChecked(sl.value(i * 2 + 1, "1") == "1");
		cbStates[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
	if (build < 833)
		return;
	cbBiasCmd->setChecked(sl.value(DIO_COUNT * 2, "0") == "1");
	leBiasChannel->setText(sl.value(DIO_COUNT * 2 + 1, "1"));
	leBiasVoltage->setText(sl.value(DIO_COUNT * 2 + 2, "0.0"));
}
//---------------------------------------------------------------------------
void LVBIAS::getClocks(QVariantMap& map)
{
	int i;
	QStringList sl;

	for (i = 0; i < DIO_COUNT; i++)
	{
		sl.append(cbStates[i]->isChecked() ? "1" : "0");
		sl.append(cbKeeps[i]->isChecked() ? "1" : "0");
	}
	if (build >= 833)
	{
		sl.append(cbBiasCmd->isChecked() ? "1" : "0");
		sl.append(leBiasChannel->text());
		sl.append(leBiasVoltage->text());
	}
	map.insert(key, sl.join(","));
}
//---------------------------------------------------------------------------
void LVBIAS::clockChanged()
{
	int i;

	for (i = 0; i < DIO_COUNT; i++)
	{
		cbStates[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
	parent->clockChanged();
}
//---------------------------------------------------------------------------
void LVBIAS::copyClocks()
{
	int i;
	QStringList sl;
	QString s;

	for (i = 0; i < DIO_COUNT; i++)
	{
		sl.append(cbStates[i]->isChecked() ? "1" : "0");
		sl.append(cbKeeps[i]->isChecked() ? "1" : "0");
	}
	if (build >= 833)
	{
		sl.append(cbBiasCmd->isChecked() ? "1" : "0");
		sl.append(leBiasChannel->text());
		sl.append(leBiasVoltage->text());
	}
	s = sl.join(",");
	QApplication::clipboard()->setText(s);
}
//---------------------------------------------------------------------------
void LVBIAS::pasteClocks()
{
	int i;
	QStringList sl;

	sl = QApplication::clipboard()->text().split(",");
	for (i = 0; i < DIO_COUNT; i++)
	{
		cbStates[i]->setChecked(sl.value(i * 2, "1") == "1");
		cbKeeps[i]->setChecked(sl.value(i * 2 + 1, "1") == "1");
		cbStates[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
	if (build < 833)
		return;
	cbBiasCmd->setChecked(sl.value(DIO_COUNT * 2, "0") == "1");
	leBiasChannel->setText(sl.value(DIO_COUNT * 2 + 1, "1"));
	leBiasVoltage->setText(sl.value(DIO_COUNT * 2 + 2, "0.0"));
}
//---------------------------------------------------------------------------
void LVBIAS::parseStatus(const RMap &data)
{
	int i;
	QString s;

	for (i = 0; i < LVLC_COUNT; i++)
	{
		lvlc_v[i]->setText(data.value(key + QString("/LVLC_V%1").arg(i + 1), "-").rightJustified(8));
		lvlc_i[i]->setText(data.value(key + QString("/LVLC_I%1").arg(i + 1), "-").rightJustified(8));
	}
	for (i = 0; i < LVHC_COUNT; i++)
	{
		lvhc_v[i]->setText(data.value(key + QString("/LVHC_V%1").arg(i + 1), "-").rightJustified(8));
		lvhc_i[i]->setText(data.value(key + QString("/LVHC_I%1").arg(i + 1), "-").rightJustified(8));
	}
	// DIO
	s = data.value(key + "/DINPUTS", "--------");
	if (s.length() != DIO_COUNT)
		s = "--------";
	for (i = 0; i < DIO_COUNT; i++)
		lStatus[i]->setText(s.mid(i, 1));
	// VCPU registers
	for (i = 0; i < VCPU_COUNT; i++)
	{
		s = data.value(key + QString("/VCPU_OUTREG%1").arg(i), "-");
		lVCPUOutReg[i]->setText(s);
	}
}

/////////////////////////////////////////////////////////////////////////////////
// HVBias Module
HVBIAS::HVBIAS(TArchonGUI *parent, QString key, int slot) : TModule(parent, key, slot)
{
	build = parent->system.value(QString("MOD%1_VERSION").arg(slot)).split(".").value(2).toInt();
}
//---------------------------------------------------------------------------
void HVBIAS::createUI()
{
	int i;
	QVBoxLayout *vl;
	QGridLayout *gl;
	QHBoxLayout *hl;
	QLabel *label;
	QPushButton *button;
	QTabWidget *tabs;
	QWidget *tab;
	QShortcut *shortcut;
	QFont boldFont, fixedFont;
	QString s;

	// Module UI
	tabs = parent->systemTabs();
	tab = new QWidget();
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	gl = new QGridLayout();
	vl->addLayout(gl);
	gl->setHorizontalSpacing(10);
	gl->setVerticalSpacing(4);

	// HVLC
	label = new QLabel("Command");
	boldFont = label->font();
	boldFont.setBold(true);
	fixedFont = label->font();
	fixedFont.setFamily("Monotype");
	fixedFont.setStyleHint(QFont::TypeWriter);
	label->setFont(boldFont);
	gl->addWidget(label, 0, 2, Qt::AlignHCenter);
	label = new QLabel("Measured");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 3, 1, 2, Qt::AlignHCenter);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 0);
	label = new QLabel("Label");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 1);
	label = new QLabel("V (0..31)");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 2);
	label = new QLabel("V");
	label->setAlignment(Qt::AlignHCenter);
	label->setFont(boldFont);
	gl->addWidget(label, 1, 3);
	label = new QLabel("mA");
	label->setAlignment(Qt::AlignHCenter);
	label->setFont(boldFont);
	gl->addWidget(label, 1, 4);
	label = new QLabel("Order");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 5);
	for (i = 0; i < HVLC_COUNT; i++)
	{
		// IDs and labels
		label = new QLabel(QString("HV%1").arg(i + 1));
		gl->addWidget(label, i + 2, 0);
		hvlc_label[i] = new QLineEdit();
		gl->addWidget(hvlc_label[i], i + 2, 1);
		// Commanded voltage
		hvlc_v_cmd[i] = new QLineEdit("0.0");
		gl->addWidget(hvlc_v_cmd[i], i + 2, 2);
		// Voltage and current readings
		hvlc_v[i] = new QLabel("-");
		hvlc_v[i]->setFont(fixedFont);
		gl->addWidget(hvlc_v[i], i + 2, 3);
		hvlc_i[i] = new QLabel("-");
		hvlc_i[i]->setFont(fixedFont);
		gl->addWidget(hvlc_i[i], i + 2, 4);
		// Power on order
		hvlc_order[i] = new QLineEdit("0");
		gl->addWidget(hvlc_order[i], i + 2, 5);
	}
	gl->setColumnMinimumWidth(6, 30);

	// HVHC
	label = new QLabel("Command");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 9, 1, 2, Qt::AlignHCenter);
	label = new QLabel("Measured");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 11, 1, 2, Qt::AlignHCenter);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 7);
	label = new QLabel("Label");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 8);
	label = new QLabel("V (0..31)");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 9);
	label = new QLabel("mA (0..250)");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 10);
	label = new QLabel("V");
	label->setAlignment(Qt::AlignHCenter);
	label->setFont(boldFont);
	gl->addWidget(label, 1, 11);
	label = new QLabel("mA");
	label->setAlignment(Qt::AlignHCenter);
	label->setFont(boldFont);
	gl->addWidget(label, 1, 12);
	label = new QLabel("Order");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 13);
	label = new QLabel("Enable");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 14);
	for (i = 0; i < HVHC_COUNT; i++)
	{
		// IDs and labels
		label = new QLabel(QString("HV%1").arg(i + HVLC_COUNT + 1));
		gl->addWidget(label, i + 2, 7);
		hvhc_label[i] = new QLineEdit();
		gl->addWidget(hvhc_label[i], i + 2, 8);
		// Commanded voltage and current limit
		hvhc_v_cmd[i] = new QLineEdit("0.0");
		gl->addWidget(hvhc_v_cmd[i], i + 2, 9);
		hvhc_il[i] = new QLineEdit("0");
		gl->addWidget(hvhc_il[i], i + 2, 10);
		// Voltage and current readings
		hvhc_v[i] = new QLabel("-");
		hvhc_v[i]->setFont(fixedFont);
		gl->addWidget(hvhc_v[i], i + 2, 11);
		hvhc_i[i] = new QLabel("-");
		hvhc_i[i]->setFont(fixedFont);
		gl->addWidget(hvhc_i[i], i + 2, 12);
		// Power on order
		hvhc_order[i] = new QLineEdit("0");
		gl->addWidget(hvhc_order[i], i + 2, 13);
		// Channel enable
		hvhc_enable[i] = new QCheckBox();
		gl->addWidget(hvhc_enable[i], i + 2, 14, Qt::AlignHCenter);
	}

	gl->setColumnStretch(15, 1);
	vl->addStretch(1);
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	button = new QPushButton("Apply");
	connect(button, SIGNAL(clicked()), this, SLOT(apply()));
	hl->addWidget(button);
	hl->addStretch(1);
	QScrollArea *scroll = new QScrollArea();
	scroll->setWidget(tab);
	if (parent->system.value(QString("MOD%1_TYPE").arg(slot)).toInt() == MOD_TYPE_HVBIAS)
		s = QString("Slot %1: HVBIAS").arg(slot);
	else
		s = QString("Slot %1: HVXBIAS").arg(slot);
	tabs->addTab(scroll, s);

	if (build > 832)
	{
		// Timing UI
		tabs = parent->waveformTabs();
		tab = new QWidget();
		tabs->addTab(tab, s);
		shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_C), tab);
		QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(copyClocks()));
		shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_V), tab);
		QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(pasteClocks()));
		gl = new QGridLayout();
		tab->setLayout(gl);
		gl->setSpacing(10);
		label = new QLabel("Command");
		label->setFont(boldFont);
		gl->addWidget(label, 0, 0);
		label = new QLabel("Channel (1-30)");
		label->setFont(boldFont);
		gl->addWidget(label, 0, 1);
		label = new QLabel("Voltage (V)");
		label->setFont(boldFont);
		gl->addWidget(label, 0, 2);
		cbBiasCmd = new QCheckBox();
		connect(cbBiasCmd, SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		leBiasChannel = new QLineEdit("1");
		connect(leBiasChannel, SIGNAL(textChanged(QString)), this, SLOT(clockChanged()));
		leBiasVoltage = new QLineEdit("0.0");
		connect(leBiasVoltage, SIGNAL(textChanged(QString)), this, SLOT(clockChanged()));
		gl->addWidget(cbBiasCmd, 1, 0, Qt::AlignHCenter);
		gl->addWidget(leBiasChannel, 1, 1);
		gl->addWidget(leBiasVoltage, 1, 2);
		gl->setVerticalSpacing(4);
		gl->setColumnStretch(3, 1);
		gl->setRowStretch(2, 1);
	}

	// Sync UI with current settings
	updateUI();
}
//---------------------------------------------------------------------------
void HVBIAS::parseUI()
{
	int i;

	for (i = 0; i < HVLC_COUNT; i++)
	{
		parent->config.insert(key + QString("/HVLC_LABEL%1").arg(i + 1), hvlc_label[i]->text());
		parent->config.insert(key + QString("/HVLC_V%1").arg(i + 1), hvlc_v_cmd[i]->text());
		parent->config.insert(key + QString("/HVLC_ORDER%1").arg(i + 1), hvlc_order[i]->text());
	}
	for (i = 0; i < HVHC_COUNT; i++)
	{
		parent->config.insert(key + QString("/HVHC_LABEL%1").arg(i + 1), hvhc_label[i]->text());
		parent->config.insert(key + QString("/HVHC_V%1").arg(i + 1), hvhc_v_cmd[i]->text());
		parent->config.insert(key + QString("/HVHC_IL%1").arg(i + 1), hvhc_il[i]->text());
		parent->config.insert(key + QString("/HVHC_ORDER%1").arg(i + 1), hvhc_order[i]->text());
		parent->config.insert(key + QString("/HVHC_ENABLE%1").arg(i + 1), hvhc_enable[i]->isChecked() ? "1" : "0");
	}
}
//---------------------------------------------------------------------------
void HVBIAS::updateUI()
{
	int i;

	for (i = 0; i < HVLC_COUNT; i++)
	{
		hvlc_label[i]->setText(parent->config.value(key + QString("/HVLC_LABEL%1").arg(i + 1)));
		hvlc_v_cmd[i]->setText(parent->config.value(key + QString("/HVLC_V%1").arg(i + 1), "0.0"));
		hvlc_order[i]->setText(parent->config.value(key + QString("/HVLC_ORDER%1").arg(i + 1), "0"));
	}
	for (i = 0; i < HVHC_COUNT; i++)
	{
		hvhc_label[i]->setText(parent->config.value(key + QString("/HVHC_LABEL%1").arg(i + 1)));
		hvhc_v_cmd[i]->setText(parent->config.value(key + QString("/HVHC_V%1").arg(i + 1), "0.0"));
		hvhc_il[i]->setText(parent->config.value(key + QString("/HVHC_IL%1").arg(i + 1), "0"));
		hvhc_order[i]->setText(parent->config.value(key + QString("/HVHC_ORDER%1").arg(i + 1), "0"));
		hvhc_enable[i]->setChecked(parent->config.value(key + QString("/HVHC_ENABLE%1").arg(i + 1)) == "1");
	}
}
//---------------------------------------------------------------------------
void HVBIAS::apply()
{
	parent->applyModule(slot);
}
//---------------------------------------------------------------------------
void HVBIAS::setClocks(const QVariantMap& map)
{
	if (build < 833)
		return;
	QStringList sl = map.value(key).toString().split(",");
	cbBiasCmd->setChecked(sl.value(0, "0") == "1");
	leBiasChannel->setText(sl.value(1, "1"));
	leBiasVoltage->setText(sl.value(2, "0.0"));
}
//---------------------------------------------------------------------------
void HVBIAS::getClocks(QVariantMap& map)
{
	if (build < 833)
		return;
	QStringList sl;
	sl.append(cbBiasCmd->isChecked() ? "1" : "0");
	sl.append(leBiasChannel->text());
	sl.append(leBiasVoltage->text());
	map.insert(key, sl.join(","));
}
//---------------------------------------------------------------------------
void HVBIAS::clockChanged()
{
	parent->clockChanged();
}
//---------------------------------------------------------------------------
void HVBIAS::copyClocks()
{
	if (build < 833)
		return;
	QStringList sl;
	QString s;
	sl.append(cbBiasCmd->isChecked() ? "1" : "0");
	sl.append(leBiasChannel->text());
	sl.append(leBiasVoltage->text());
	s = sl.join(",");
	QApplication::clipboard()->setText(s);
}
//---------------------------------------------------------------------------
void HVBIAS::pasteClocks()
{
	if (build < 833)
		return;
	QStringList sl;

	sl = QApplication::clipboard()->text().split(",");
	cbBiasCmd->setChecked(sl.value(0, "0") == "1");
	leBiasChannel->setText(sl.value(1, "1"));
	leBiasVoltage->setText(sl.value(2, "0.0"));
}
//---------------------------------------------------------------------------
void HVBIAS::parseStatus(const RMap &data)
{
	int i;

	for (i = 0; i < HVLC_COUNT; i++)
	{
		hvlc_v[i]->setText(data.value(key + QString("/HVLC_V%1").arg(i + 1), "-").rightJustified(8));
		hvlc_i[i]->setText(data.value(key + QString("/HVLC_I%1").arg(i + 1), "-").rightJustified(8));
	}
	for (i = 0; i < HVHC_COUNT; i++)
	{
		hvhc_v[i]->setText(data.value(key + QString("/HVHC_V%1").arg(i + 1), "-").rightJustified(8));
		hvhc_i[i]->setText(data.value(key + QString("/HVHC_I%1").arg(i + 1), "-").rightJustified(8));
	}
}
/////////////////////////////////////////////////////////////////////////////////
// Heater Module
HEATER::HEATER(TArchonGUI *parent, QString key, int slot) : TModule(parent, key, slot)
{
	build = parent->system.value(QString("MOD%1_VERSION").arg(slot)).split(".").value(2).toInt();
}
//---------------------------------------------------------------------------
void HEATER::createUI()
{
	int i, x, y;
	QVBoxLayout *vl;
	QGridLayout *gl;
	QHBoxLayout *hl;
	QLabel *label;
	QPushButton *button;
	QTabWidget *tabs;
	QWidget *tab;
	QShortcut *shortcut;
	QwtPlotGrid *grid;
	QFont boldFont;

	// Module UI
	tabs = parent->systemTabs();
	tab = new QWidget();
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	gl = new QGridLayout();
	vl->addLayout(gl);
	// TempA and TempB readings
	x = 0;
	y = 0;
	label = new QLabel("Temp A (C):");
	boldFont = label->font();
	boldFont.setBold(true);
	gl->addWidget(label, y, x);
	tempa = new QLabel("-");
	gl->addWidget(tempa, y, x + 1);
	label = new QLabel("Temp B (C):");
	gl->addWidget(label, y, x + 7);
	tempb = new QLabel("-");
	gl->addWidget(tempb, y, x + 8);
	gl->setColumnMinimumWidth(x + 2, 20);
	gl->setColumnMinimumWidth(x + 6, 30);
	gl->setColumnMinimumWidth(x + 9, 20);
	gl->setColumnStretch(x + 12, 1);
	// Sensor types
	label = new QLabel("Sensor A Type:");
	gl->addWidget(label, y, x + 3);
	TempASensorType = new QComboBox();
	TempASensorType->addItem("DT-670");
	TempASensorType->addItem("DT-470");
	TempASensorType->addItem("RTD100");
	TempASensorType->addItem("RTD400");
	gl->addWidget(TempASensorType, y, x + 4);
	label = new QLabel("Sensor B Type:");
	gl->addWidget(label, y, x + 10);
	TempBSensorType = new QComboBox();
	TempBSensorType->addItem("DT-670");
	TempBSensorType->addItem("DT-470");
	TempBSensorType->addItem("RTD100");
	TempBSensorType->addItem("RTD400");
	gl->addWidget(TempBSensorType, y, x + 11);
	y++;
	if (build >= 592)
	{
		// Sensor limits
		label = new QLabel("Temp A Lower Limit (C):");
		gl->addWidget(label, y, x);
		TempALowerLimit = new QLineEdit("-150.0");
		gl->addWidget(TempALowerLimit, y, x + 1);
		label = new QLabel("Temp A Upper Limit (C):");
		gl->addWidget(label, y, x + 3);
		TempAUpperLimit = new QLineEdit("50.0");
		gl->addWidget(TempAUpperLimit, y, x + 4);
		label = new QLabel("Temp B Lower Limit (C):");
		gl->addWidget(label, y, x + 7);
		TempBLowerLimit = new QLineEdit("-150.0");
		gl->addWidget(TempBLowerLimit, y, x + 8);
		label = new QLabel("Temp B Upper Limit (C):");
		gl->addWidget(label, y, x + 10);
		TempBUpperLimit = new QLineEdit("50.0");
		gl->addWidget(TempBUpperLimit, y, x + 11);
		y++;
	}
	// Heater enables
	label = new QLabel("Heater A Enable:");
	gl->addWidget(label, y, x);
	cbEnableA = new QCheckBox();
	gl->addWidget(cbEnableA, y, x + 1);
	label = new QLabel("Heater B Enable:");
	gl->addWidget(label, y, x + 7);
	cbEnableB = new QCheckBox();
	gl->addWidget(cbEnableB, y++, x + 8);
	// Heater A and B outputs
	label = new QLabel("Heater A Output (V):");
	gl->addWidget(label, y, x);
	heaterOutputA = new QLabel("-");
	gl->addWidget(heaterOutputA, y, x + 1);
	label = new QLabel("Heater B Output (V):");
	gl->addWidget(label, y, x + 7);
	heaterOutputB = new QLabel("-");
	gl->addWidget(heaterOutputB, y++, x + 8);
	// Heater target levels
	label = new QLabel("Heater A Target (C):");
	gl->addWidget(label, y, x);
	HeaterATarget = new QLineEdit("0");
	gl->addWidget(HeaterATarget, y, x + 1);
	label = new QLabel("Heater B Target (C):");
	gl->addWidget(label, y, x + 7);
	HeaterBTarget= new QLineEdit("0");
	gl->addWidget(HeaterBTarget, y++, x + 8);
	// PID sensor selections
	label = new QLabel("Heater A Sensor:");
	gl->addWidget(label, y, x);
	TempASensor = new QComboBox();
	TempASensor->addItem("TempA");
	TempASensor->addItem("TempB");
	gl->addWidget(TempASensor, y, x + 1);
	label = new QLabel("Heater B Sensor:");
	gl->addWidget(label, y, x + 7);
	TempBSensor = new QComboBox();
	TempBSensor->addItem("TempA");
	TempBSensor->addItem("TempB");
	gl->addWidget(TempBSensor, y++, x + 8);
	y++;
	if (build >= 478)
	{
		label = new QLabel("PID Update Time (ms):");
		gl->addWidget(label, y, x);
		HeaterUpdateTime = new QLineEdit("1000");
		gl->addWidget(HeaterUpdateTime, y++, x + 1);
	}

	y = 2;
	x += 3;
	// Heater force mode
	label = new QLabel("Heater A Force:");
	gl->addWidget(label, y, x);
	cbForceA = new QCheckBox();
	gl->addWidget(cbForceA, y, x + 1);
	label = new QLabel("Heater B Force:");
	gl->addWidget(label, y, x + 7);
	cbForceB = new QCheckBox();
	gl->addWidget(cbForceB, y++, x + 8);
	// Heater force levels
	label = new QLabel("Heater A Force Level (V):");
	gl->addWidget(label, y, x);
	HeaterAForceLevel = new QLineEdit("0");
	gl->addWidget(HeaterAForceLevel, y, x + 1);
	label = new QLabel("Heater B Force Level (V):");
	gl->addWidget(label, y, x + 7);
	HeaterBForceLevel = new QLineEdit("0");
	gl->addWidget(HeaterBForceLevel, y++, x + 8);
	if (build >= 592)
	{
		// Heater output limits
		label = new QLabel("Heater A Limit (V):");
		gl->addWidget(label, y, x);
		HeaterALimit = new QLineEdit("25.0");
		gl->addWidget(HeaterALimit, y, x + 1);
		label = new QLabel("Heater B Limit (V):");
		gl->addWidget(label, y, x + 7);
		HeaterBLimit = new QLineEdit("25.0");
		gl->addWidget(HeaterBLimit, y++, x + 8);
	}
	// Heater P terms
	label = new QLabel("Heater A P:");
	gl->addWidget(label, y, x);
	HeaterAP = new QLineEdit("1");
	gl->addWidget(HeaterAP, y, x + 1);
	HeaterAPErr = new QLabel("0");
	gl->addWidget(HeaterAPErr, y, x + 2);
	label = new QLabel("Heater B P:");
	gl->addWidget(label, y, x + 7);
	HeaterBP = new QLineEdit("1");
	gl->addWidget(HeaterBP, y, x + 8);
	HeaterBPErr = new QLabel("0");
	gl->addWidget(HeaterBPErr, y++, x + 9);
	if (build >= 478)
	{
		// Heater I terms
		label = new QLabel("Heater A I:");
		gl->addWidget(label, y, x);
		HeaterAI = new QLineEdit("0");
		gl->addWidget(HeaterAI, y, x + 1);
		HeaterAIErr = new QLabel("0");
		gl->addWidget(HeaterAIErr, y, x + 2);
		label = new QLabel("Heater B I:");
		gl->addWidget(label, y, x + 7);
		HeaterBI = new QLineEdit("0");
		gl->addWidget(HeaterBI, y, x + 8);
		HeaterBIErr = new QLabel("0");
		gl->addWidget(HeaterBIErr, y++, x + 9);
		// Heater D terms
		label = new QLabel("Heater A D:");
		gl->addWidget(label, y, x);
		HeaterAD = new QLineEdit("0");
		gl->addWidget(HeaterAD, y, x + 1);
		HeaterADErr = new QLabel("0");
		gl->addWidget(HeaterADErr, y, x + 2);
		label = new QLabel("Heater B D:");
		gl->addWidget(label, y, x + 7);
		HeaterBD = new QLineEdit("0");
		gl->addWidget(HeaterBD, y, x + 8);
		HeaterBDErr = new QLabel("0");
		gl->addWidget(HeaterBDErr, y++, x + 9);
		// Heater IL terms
		label = new QLabel("Heater A IL:");
		gl->addWidget(label, y, x);
		HeaterAIL = new QLineEdit("1000");
		gl->addWidget(HeaterAIL, y, x + 1);
		label = new QLabel("Heater B IL:");
		gl->addWidget(label, y, x + 7);
		HeaterBIL = new QLineEdit("1000");
		gl->addWidget(HeaterBIL, y++, x + 8);
	}
	if (build >= 547)
	{
		// Heater ramp enable
		label = new QLabel("Heater A Ramp:");
		gl->addWidget(label, y, x);
		cbHeaterARamp = new QCheckBox();
		gl->addWidget(cbHeaterARamp, y, x + 1);
		label = new QLabel("Heater B Ramp:");
		gl->addWidget(label, y, x + 7);
		cbHeaterBRamp = new QCheckBox();
		gl->addWidget(cbHeaterBRamp, y++, x + 8);
		// Heater ramp rates
		label = new QLabel("Heater A Ramp Rate (mK / tick):");
		gl->addWidget(label, y, x);
		HeaterARampRate = new QLineEdit("1");
		gl->addWidget(HeaterARampRate, y, x + 1);
		label = new QLabel("Heater B Ramp Rate (mK / tick):");
		gl->addWidget(label, y, x + 7);
		HeaterBRampRate = new QLineEdit("1");
		gl->addWidget(HeaterBRampRate, y++, x + 8);
	}
	gl->setColumnMinimumWidth(x + 9, 30);

	// DIO
	y = 0;
	x += 10;
	label = new QLabel("Digital I/O");
	label->setFont(boldFont);
	gl->addWidget(label, y++, x, 1, 3, Qt::AlignHCenter);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, y, x);
	label = new QLabel("Label");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 1);
	label = new QLabel("Source");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 2);
	label = new QLabel("Status");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 3);
	label = new QLabel("Direction");
	label->setFont(boldFont);
	gl->addWidget(label, y++, x + 4);
	for (i = 0; i < DIO_COUNT; i++)
	{
		// IDs and labels
		label = new QLabel(QString("DIO%1").arg(i + 1));
		gl->addWidget(label, y + i, x);
		leLabels[i] = new QLineEdit();
		gl->addWidget(leLabels[i], y + i, x + 1);
		cbSources[i] = new QComboBox();
		cbSources[i]->addItem("Low");
		cbSources[i]->addItem("High");
		cbSources[i]->addItem("Clocked");
		cbSources[i]->addItem("VCPU");
		gl->addWidget(cbSources[i], y + i, x + 2);
		lStatus[i] = new QLabel("-");
		gl->addWidget(lStatus[i], y + i, x + 3);
	}
	for (i = 0; i < DIO_COUNT / 2; i++)
	{
		cbDirections[i] = new QComboBox();
		cbDirections[i]->addItem("Input");
		cbDirections[i]->addItem("Output");
		gl->addWidget(cbDirections[i], y + i * 2, x + 4, 2, 1);
	}
	y += DIO_COUNT;
	label = new QLabel("DIO Power");
	label->setFont(boldFont);
	gl->addWidget(label, y, x, 1, 2);
	cbPower = new QComboBox();
	cbPower->addItem("Disabled");
	cbPower->addItem("Enabled");
	gl->addWidget(cbPower, y++, x + 2);
	gl->setColumnStretch(x + 5, 1);

	vl->addSpacing(20);
	hl = new QHBoxLayout();
	vl->addLayout(hl, 1);
	HPlotA = new QwtPlot();
	hl->addWidget(HPlotA, 1);
	grid = new QwtPlotGrid;
	grid->attach(HPlotA);
	grid->setMajorPen(QPen(Qt::gray, 0, Qt::DotLine));
	HCurveA = new QwtPlotCurve();
	HCurveA->attach(HPlotA);
	HCurveA->setPen(QPen(Qt::red));
	HPlotA->setAxisTitle(QwtPlot::yLeft,"Temperature A (C)");
	HPlotA->setAxisTitle(QwtPlot::xBottom,"Time (sec)");
	HPannerA = new QwtPlotPanner(HPlotA->canvas());
	HPannerA->setMouseButton(Qt::RightButton);
	HZoomerA = new QwtPlotZoomer(HPlotA->canvas());
	HZoomerA->setMousePattern(QwtEventPattern::MouseSelect2,Qt::MiddleButton, Qt::NoModifier);

	HPlotB = new QwtPlot();
	hl->addWidget(HPlotB, 1);
	grid = new QwtPlotGrid;
	grid->attach(HPlotB);
	grid->setMajorPen(QPen(Qt::gray, 0, Qt::DotLine));
	HCurveB = new QwtPlotCurve();
	HCurveB->attach(HPlotB);
	HCurveB->setPen(QPen(Qt::blue));
	HPlotB->setAxisTitle(QwtPlot::yLeft,"Temperature B (C)");
	HPlotB->setAxisTitle(QwtPlot::xBottom,"Time (sec)");
	HPannerB = new QwtPlotPanner(HPlotB->canvas());
	HPannerB->setMouseButton(Qt::RightButton);
	HZoomerB = new QwtPlotZoomer(HPlotB->canvas());
	HZoomerB->setMousePattern(QwtEventPattern::MouseSelect2,Qt::MiddleButton, Qt::NoModifier);

	// Bottom temperature UI
	plottingEnabled = false;
	vl->addStretch(1);
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	button = new QPushButton("Apply");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(apply()));
	hl->addWidget(button);
	button = new QPushButton("Enable Plotting");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(enablePlotting()));
	hl->addWidget(button);
	button = new QPushButton("Disable Plotting");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(disablePlotting()));
	hl->addWidget(button);
	button = new QPushButton("Save Plots");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(savePlots()));
	hl->addWidget(button);
	hl->addStretch(1);
	QScrollArea *scroll = new QScrollArea();
	scroll->setWidget(tab);
	tabs->addTab(scroll, QString("Slot %1: HEATER").arg(slot));

	// Timing UI
	tabs = parent->waveformTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: HEATER").arg(slot));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_C), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(copyClocks()));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_V), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(pasteClocks()));
	gl = new QGridLayout();
	tab->setLayout(gl);
	gl->setSpacing(10);
	label = new QLabel("Label");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 0);
	label = new QLabel("State");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 1);
	label = new QLabel("Keep");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 2);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 3);
	for (i = 0; i < DIO_COUNT; i++)
	{
		lRefLabels[i] = new QLabel();
		connect(leLabels[i], SIGNAL(textChanged(QString)), lRefLabels[i], SLOT(setText(QString)));
		cbStates[i] = new QCheckBox();
		cbKeeps[i] = new QCheckBox();
		connect(cbStates[i], SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		connect(cbKeeps[i], SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		label = new QLabel();
		label->setText(QString("DIO%1").arg(i + 1));
		gl->addWidget(lRefLabels[i], i + 1, 0);
		gl->addWidget(cbStates[i], i + 1, 1, Qt::AlignHCenter);
		gl->addWidget(cbKeeps[i], i + 1, 2, Qt::AlignHCenter);
		gl->addWidget(label, i + 1, 3);
	}
	gl->setVerticalSpacing(4);
	gl->setColumnStretch(4, 1);
	gl->setRowStretch(DIO_COUNT + 1, 1);

	// VCPU UI
	tabs = parent->vcpuTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: HEATER").arg(slot));
	gl = new QGridLayout();
	tab->setLayout(gl);
	gl->setSpacing(10);
	teVCPU = new QPlainTextEdit();
	teVCPU->setLineWrapMode(QPlainTextEdit::NoWrap);
	label = new QLabel("Code");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 0);
	gl->addWidget(teVCPU, 1, 0, VCPU_COUNT + 1, 1);
	label = new QLabel("Register");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 1);
	label = new QLabel("Input");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 2);
	label = new QLabel("Output");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 3);
	for (i = 0; i < VCPU_COUNT; i++)
	{
		label = new QLabel(QString("REG%1").arg(i));
		gl->addWidget(label, i + 1, 1);
		leVCPUInReg[i] = new QLineEdit("0");
		gl->addWidget(leVCPUInReg[i], i + 1, 2);
		lVCPUOutReg[i] = new QLabel("-");
		gl->addWidget(lVCPUOutReg[i], i + 1, 3);
	}
	gl->setColumnStretch(0, 1);
	gl->setRowStretch(VCPU_COUNT + 1, 1);
	gl->setColumnMinimumWidth(3, 100);
	hl = new QHBoxLayout();
	button = new QPushButton("Apply");
	connect(button, SIGNAL(clicked()), this, SLOT(applyDIO()));
	hl->addWidget(button);
	hl->addStretch(0);
	gl->addLayout(hl, VCPU_COUNT + 2, 0);

	// Sync UI with current settings
	updateUI();
}
//---------------------------------------------------------------------------
void HEATER::parseUI()
{
	int i, count;
	QStringList sl;

	// Heater control
	parent->config.insert(key + "/HEATERAENABLE", cbEnableA->isChecked() ? "1" : "0");
	parent->config.insert(key + "/HEATERBENABLE", cbEnableB->isChecked() ? "1" : "0");
	parent->config.insert(key + "/HEATERAFORCE", cbForceA->isChecked() ? "1" : "0");
	parent->config.insert(key + "/HEATERBFORCE", cbForceB->isChecked() ? "1" : "0");
	parent->config.insert(key + "/HEATERAFORCELEVEL", HeaterAForceLevel->text());
	parent->config.insert(key + "/HEATERBFORCELEVEL", HeaterBForceLevel->text());
	parent->config.insert(key + "/HEATERASENSOR", QString::number(TempASensor->currentIndex()));
	parent->config.insert(key + "/HEATERBSENSOR", QString::number(TempBSensor->currentIndex()));
	parent->config.insert(key + "/HEATERASENSORTYPE", QString::number(TempASensorType->currentIndex()));
	parent->config.insert(key + "/HEATERBSENSORTYPE", QString::number(TempBSensorType->currentIndex()));
	parent->config.insert(key + "/HEATERATARGET", HeaterATarget->text());
	parent->config.insert(key + "/HEATERBTARGET", HeaterBTarget->text());
	parent->config.insert(key + "/HEATERAP", HeaterAP->text());
	parent->config.insert(key + "/HEATERBP", HeaterBP->text());
	if (build >= 478)
	{
		parent->config.insert(key + "/HEATERAI", HeaterAI->text());
		parent->config.insert(key + "/HEATERBI", HeaterBI->text());
		parent->config.insert(key + "/HEATERAD", HeaterAD->text());
		parent->config.insert(key + "/HEATERBD", HeaterBD->text());
		parent->config.insert(key + "/HEATERAIL", HeaterAIL->text());
		parent->config.insert(key + "/HEATERBIL", HeaterBIL->text());
		parent->config.insert(key + "/HEATERUPDATETIME", HeaterUpdateTime->text());
	}
	if (build >= 547)
	{
		parent->config.insert(key + "/HEATERARAMP", cbHeaterARamp->isChecked() ? "1" : "0");
		parent->config.insert(key + "/HEATERBRAMP", cbHeaterBRamp->isChecked() ? "1" : "0");
		parent->config.insert(key + "/HEATERARAMPRATE", HeaterARampRate->text());
		parent->config.insert(key + "/HEATERBRAMPRATE", HeaterBRampRate->text());
	}
	if (build >= 592)
	{
		parent->config.insert(key + "/HEATERALIMIT", HeaterALimit->text());
		parent->config.insert(key + "/HEATERBLIMIT", HeaterBLimit->text());
		parent->config.insert(key + "/SENSORALOWERLIMIT", TempALowerLimit->text());
		parent->config.insert(key + "/SENSORAUPPERLIMIT", TempAUpperLimit->text());
		parent->config.insert(key + "/SENSORBLOWERLIMIT", TempBLowerLimit->text());
		parent->config.insert(key + "/SENSORBUPPERLIMIT", TempBUpperLimit->text());
	}
	for (i = 0; i < DIO_COUNT; i++)
	{
		parent->config.insert(key + QString("/DIO_LABEL%1").arg(i + 1), leLabels[i]->text());
		parent->config.insert(key + QString("/DIO_SOURCE%1").arg(i + 1), QString::number(cbSources[i]->currentIndex()));
	}
	for (i = 0; i < DIO_COUNT / 2; i++)
	{
		parent->config.insert(key + QString("/DIO_DIR%1%2").arg(i * 2 + 1).arg(i * 2 + 2), QString::number(cbDirections[i]->currentIndex()));
	}
	parent->config.insert(key + "/DIO_POWER", QString::number(cbPower->currentIndex()));
	// VCPU code
	sl = teVCPU->toPlainText().split('\n');
	count = sl.count();
	parent->config.insert(key + "/VCPU_LINES", QString::number(count));
	for (i = 0; i < count; i++)
		parent->config.insert(key + QString("/VCPU_LINE%1").arg(i), sl[i]);
	for (i = 0; i < VCPU_COUNT; i++)
		parent->config.insert(key + QString("/VCPU_INREG%1").arg(i), leVCPUInReg[i]->text());
}
//---------------------------------------------------------------------------
void HEATER::updateUI()
{
	int i, count;
	bool ok;

	cbEnableA->setChecked(parent->config.value(key + "/HEATERAENABLE") == "1");
	cbEnableB->setChecked(parent->config.value(key + "/HEATERBENABLE") == "1");
	cbForceA->setChecked(parent->config.value(key + "/HEATERAFORCE") == "1");
	cbForceB->setChecked(parent->config.value(key + "/HEATERBFORCE") == "1");
	HeaterAForceLevel->setText(parent->config.value(key + "/HEATERAFORCELEVEL", "0"));
	HeaterBForceLevel->setText(parent->config.value(key + "/HEATERBFORCELEVEL", "0"));
	TempASensor->setCurrentIndex(qBound(0, parent->config.value(key + "/HEATERASENSOR").toInt(), 1));
	TempBSensor->setCurrentIndex(qBound(0, parent->config.value(key + "/HEATERBSENSOR").toInt(), 1));
	TempASensorType->setCurrentIndex(qBound(0, parent->config.value(key + "/HEATERASENSORTYPE").toInt(), TempASensorType->count() - 1));
	TempBSensorType->setCurrentIndex(qBound(0, parent->config.value(key + "/HEATERBSENSORTYPE").toInt(), TempBSensorType->count() - 1));
	HeaterATarget->setText(parent->config.value(key + "/HEATERATARGET", "0"));
	HeaterBTarget->setText(parent->config.value(key + "/HEATERBTARGET", "0"));
	HeaterAP->setText(parent->config.value(key + "/HEATERAP", "0"));
	HeaterBP->setText(parent->config.value(key + "/HEATERBP", "0"));
	if (build >= 478)
	{
		HeaterAI->setText(parent->config.value(key + "/HEATERAI", "0"));
		HeaterBI->setText(parent->config.value(key + "/HEATERBI", "0"));
		HeaterAD->setText(parent->config.value(key + "/HEATERAD", "0"));
		HeaterBD->setText(parent->config.value(key + "/HEATERBD", "0"));
		HeaterAIL->setText(parent->config.value(key + "/HEATERAIL", "1000"));
		HeaterBIL->setText(parent->config.value(key + "/HEATERBIL", "1000"));
		HeaterUpdateTime->setText(parent->config.value(key + "/HEATERUPDATETIME", "1000"));
	}
	if (build >= 547)
	{
		cbHeaterARamp->setChecked(parent->config.value(key + "/HEATERARAMP") == "1");
		cbHeaterBRamp->setChecked(parent->config.value(key + "/HEATERBRAMP") == "1");
		HeaterARampRate->setText(parent->config.value(key + "/HEATERARAMPRATE", "1"));
		HeaterBRampRate->setText(parent->config.value(key + "/HEATERBRAMPRATE", "1"));
	}
	if (build >= 592)
	{
		HeaterALimit->setText(parent->config.value(key + "/HEATERALIMIT", "25.0"));
		HeaterBLimit->setText(parent->config.value(key + "/HEATERBLIMIT", "25.0"));
		TempALowerLimit->setText(parent->config.value(key + "/SENSORALOWERLIMIT", "-150.0"));
		TempAUpperLimit->setText(parent->config.value(key + "/SENSORAUPPERLIMIT", "50.0"));
		TempBLowerLimit->setText(parent->config.value(key + "/SENSORBLOWERLIMIT", "-150.0"));
		TempBUpperLimit->setText(parent->config.value(key + "/SENSORBUPPERLIMIT", "50.0"));
	}
	for (i = 0; i < DIO_COUNT; i++)
	{
		leLabels[i]->setText(parent->config.value(key + QString("/DIO_LABEL%1").arg(i + 1)));
		cbSources[i]->setCurrentIndex(qBound(0, parent->config.value(key + QString("/DIO_SOURCE%1").arg(i + 1)).toInt(), 3));
	}
	for (i = 0; i < DIO_COUNT / 2; i++)
	{
		cbDirections[i]->setCurrentIndex(qBound(0, parent->config.value(key + QString("/DIO_DIR%1%2").arg(i * 2 + 1).arg(i * 2 + 2)).toInt(), 1));
	}
	cbPower->setCurrentIndex(qBound(0, parent->config.value(key + "/DIO_POWER").toInt(), 1));
	// VCPU code
	count = parent->config.value(key + "/VCPU_LINES").toInt(&ok);
	if (ok)
	{
		teVCPU->clear();
		for (i = 0; i < count; i++)
			teVCPU->appendPlainText(parent->config.value(key + QString("/VCPU_LINE%1").arg(i)));
	}
	for (i = 0; i < VCPU_COUNT; i++)
		leVCPUInReg[i]->setText(parent->config.value(key + QString("/VCPU_INREG%1").arg(i + 1), "0"));
}
//---------------------------------------------------------------------------
void HEATER::apply()
{
	parent->applyModule(slot);
}
//---------------------------------------------------------------------------
void HEATER::applyDIO()
{
	parent->applyModuleDIO(slot);
}
//---------------------------------------------------------------------------
void HEATER::enablePlotting()
{
	plottingEnabled = true;
	htime.clear();
	htempa.clear();
	htempb.clear();
	pollt = QDateTime::currentDateTime();
}
//---------------------------------------------------------------------------
void HEATER::disablePlotting()
{
	plottingEnabled = false;
}
//---------------------------------------------------------------------------
void HEATER::savePlots()
{
	FILE *fout = fopen("heaterplots.txt","w");
	fprintf(fout,"Time (s)\tTemp A (C)\tTemp B (C)\n");
	for (int i = 0; i < htime.count(); i++)
		fprintf(fout,"%0.6lf\t%0.6lf\t%0.6lf\n", htime[i], htempa[i], htempb[i]);
	fclose(fout);
}
//---------------------------------------------------------------------------
void HEATER::setClocks(const QVariantMap& map)
{
	int i;
	QStringList sl = map.value(key).toString().split(",");

	for (i = 0; i < DIO_COUNT; i++)
	{
		cbStates[i]->setChecked(sl.value(i * 2, "1") == "1");
		cbKeeps[i]->setChecked(sl.value(i * 2 + 1, "1") == "1");
		cbStates[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
}
//---------------------------------------------------------------------------
void HEATER::getClocks(QVariantMap& map)
{
	int i;
	QStringList sl;

	for (i = 0; i < DIO_COUNT; i++)
	{
		sl.append(cbStates[i]->isChecked() ? "1" : "0");
		sl.append(cbKeeps[i]->isChecked() ? "1" : "0");
	}
	map.insert(key, sl.join(","));
}
//---------------------------------------------------------------------------
void HEATER::clockChanged()
{
	int i;

	for (i = 0; i < DIO_COUNT; i++)
	{
		cbStates[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
	parent->clockChanged();
}
//---------------------------------------------------------------------------
void HEATER::copyClocks()
{
	int i;
	QStringList sl;
	QString s;

	for (i = 0; i < DIO_COUNT; i++)
	{
		sl.append(cbStates[i]->isChecked() ? "1" : "0");
		sl.append(cbKeeps[i]->isChecked() ? "1" : "0");
	}
	s = sl.join(",");
	QApplication::clipboard()->setText(s);
}
//---------------------------------------------------------------------------
void HEATER::pasteClocks()
{
	int i;
	QStringList sl;

	sl = QApplication::clipboard()->text().split(",");
	for (i = 0; i < DIO_COUNT; i++)
	{
		cbStates[i]->setChecked(sl.value(i * 2, "1") == "1");
		cbKeeps[i]->setChecked(sl.value(i * 2 + 1, "1") == "1");
		cbStates[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
}
//---------------------------------------------------------------------------
void HEATER::parseStatus(const RMap &data)
{
	int i;
	double d;
	double t;
	bool ok;
	double minval, maxval, ta, tb;
	QString s;

	ta = data.value(key + "/TEMPA", "-").toDouble(&ok);
	if (ok)
		tempa->setText(flt(ta, 0, 3));
	tb = data.value(key + "/TEMPB", "-").toDouble(&ok);
	if (ok)
		tempb->setText(flt(tb, 0, 3));
	d = data.value(key + "/HEATERAOUTPUT", "-").toDouble(&ok);
	if (ok)
		heaterOutputA->setText(flt(d, 0, 3));
	d = data.value(key + "/HEATERBOUTPUT", "-").toDouble(&ok);
	if (ok)
		heaterOutputB->setText(flt(d, 0, 3));
	HeaterAPErr->setText(data.value(key + "/HEATERAP", "0"));
	HeaterAIErr->setText(data.value(key + "/HEATERAI", "0"));
	HeaterADErr->setText(data.value(key + "/HEATERAD", "0"));
	HeaterBPErr->setText(data.value(key + "/HEATERBP", "0"));
	HeaterBIErr->setText(data.value(key + "/HEATERBI", "0"));
	HeaterBDErr->setText(data.value(key + "/HEATERBD", "0"));
	if (plottingEnabled)
	{
		t = double(pollt.msecsTo(QDateTime::currentDateTime())) / 1000.0;
		if (htime.count() == 10000)
		{
			htime.remove(0);
			htempa.remove(0);
			htempb.remove(0);
		}
		htime.append(t);
		htempa.append(ta);
		htempb.append(tb);
		HCurveA->setSamples(htime, htempa);
		HPlotA->replot();
		HCurveB->setSamples(htime, htempb);
		HPlotB->replot();
		HPlotA->setAxisScale(QwtPlot::xBottom, htime[0], t);
		minval = htempa[0];
		maxval = htempa[0];
		for (i = 0; i < htempa.count(); i++)
		{
			 minval = qMin(minval, htempa[i]);
			 maxval = qMax(maxval, htempa[i]);
		}
		HPlotA->setAxisScale(QwtPlot::yLeft, minval, maxval);
		HZoomerA->setZoomBase();
		HPlotB->setAxisScale(QwtPlot::xBottom, htime[0], t);
		minval = htempb[0];
		maxval = htempb[0];
		for (i = 0; i < htempb.count(); i++)
		{
		  minval = qMin(minval, htempb[i]);
		  maxval = qMax(maxval, htempb[i]);
		}
		HPlotB->setAxisScale(QwtPlot::yLeft, minval, maxval);
		HZoomerB->setZoomBase();
	}

	// DIO
	s = data.value(key + "/DINPUTS", "--------");
	if (s.length() != DIO_COUNT)
		s = "--------";
	for (i = 0; i < DIO_COUNT; i++)
		lStatus[i]->setText(s.mid(i, 1));
	// VCPU registers
	for (i = 0; i < VCPU_COUNT; i++)
	{
		s = data.value(key + QString("/VCPU_OUTREG%1").arg(i), "-");
		lVCPUOutReg[i]->setText(s);
	}
}
/////////////////////////////////////////////////////////////////////////////////
// Atlas Module
ATLAS::ATLAS(TArchonGUI *parent, QString key, int slot) : TModule(parent, key, slot)
{
}
//---------------------------------------------------------------------------
void ATLAS::createUI()
{
	int i, x, y;
	QVBoxLayout *vl;
	QGridLayout *gl, *tabgl;
	QGroupBox *gb;
	QHBoxLayout *hl;
	QPushButton *button;
	QTabWidget *tabs;
	QWidget *tab;
	QLabel *label;
	QShortcut *shortcut;
	QFont boldFont;

	// Module UI
	tabs = parent->systemTabs();
	tab = new QWidget();
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	tabgl = new QGridLayout();
	vl->addLayout(tabgl);
	tabgl->setHorizontalSpacing(10);
	tabgl->setVerticalSpacing(4);

	// TEC
	x = 0;
	y = 0;
	gb = new QGroupBox("TEC");
	gl = new QGridLayout(gb);
	tabgl->addWidget(gb, 0, 0);
	label = new QLabel("Enable TEC:");
	boldFont = label->font();
	boldFont.setBold(true);
	gl->addWidget(label, y, x);
	enable_tec = new QComboBox();
	enable_tec->addItem("Off");
	enable_tec->addItem("On");
	enable_tec->addItem("Keep");
	gl->addWidget(enable_tec, y++, x + 1);
	enable_tec->setCurrentIndex(2);
	label = new QLabel("TEC:");
	gl->addWidget(label, y, x);
	tec_enabled = new QLabel("-");
	gl->addWidget(tec_enabled, y++, x + 1);
	label = new QLabel("TEC Voltage (V):");
	gl->addWidget(label, y, x);
	tec_voltage = new QLabel("-");
	gl->addWidget(tec_voltage, y++, x + 1);
	label = new QLabel("TEC Current (A):");
	gl->addWidget(label, y, x);
	tec_current = new QLabel("-");
	gl->addWidget(tec_current, y++, x + 1);

	// Ion Pump
	x = 0;
	y = 0;
	gb = new QGroupBox("Ion Pump");
	gl = new QGridLayout(gb);
	tabgl->addWidget(gb, 0, 1);
	label = new QLabel("Enable Ion Pump:");
	gl->addWidget(label, y, x);
	enable_ion = new QComboBox();
	enable_ion->addItem("Off");
	enable_ion->addItem("On");
	enable_ion->addItem("Keep");
	gl->addWidget(enable_ion, y++, x + 1);
	enable_ion->setCurrentIndex(2);
	label = new QLabel("Ion Pump:");
	gl->addWidget(label, y, x);
	ion_enabled = new QLabel("-");
	gl->addWidget(ion_enabled, y++, x + 1);
	label = new QLabel("Ion Pump Monitor (V):");
	gl->addWidget(label, y, x);
	ion_voltage = new QLabel("-");
	gl->addWidget(ion_voltage, y++, x + 1);
	label = new QLabel("Ion Pump Current (A):");
	gl->addWidget(label, y, x);
	ion_current = new QLabel("-");
	gl->addWidget(ion_current, y++, x + 1);

	// RTDs
	x = 0;
	y = 0;
	gb = new QGroupBox("RTDs");
	gl = new QGridLayout(gb);
	tabgl->addWidget(gb, 1, 0);
	for (i = 0; i < RTD_COUNT; i++)
	{
		label = new QLabel(QString("RTD%1 (C):").arg(i + 1));
		gl->addWidget(label, y, x);
		rtd[i] = new QLabel("-");
		gl->addWidget(rtd[i], y++, x + 1);
	}

	// Halls
	x = 0;
	y = 0;
	gb = new QGroupBox("Hall Sensors");
	gl = new QGridLayout(gb);
	tabgl->addWidget(gb, 1, 1);
	for (i = 0; i < HALL_COUNT; i++)
	{
		label = new QLabel(QString("Hall Sensor %1 (V):").arg(i + 1));
		gl->addWidget(label, y, x);
		hall[i] = new QLabel("-");
		gl->addWidget(hall[i], y++, x + 1);
	}
	gl->setRowStretch(y, 0);

	// Pirani vacuum gauge
	x = 0;
	y = 0;
	gb = new QGroupBox("Vacuum Gauge");
	gl = new QGridLayout(gb);
	tabgl->addWidget(gb, 0, 2);
	label = new QLabel("Vacuum Reading (Torr):");
	gl->addWidget(label, y, x);
	vac_reading = new QLabel("-");
	gl->addWidget(vac_reading, y++, x + 1);
	gl->setRowStretch(y, 0);

	// Motors
	x = 0;
	y = 0;
	gb = new QGroupBox("Picomotors");
	gl = new QGridLayout(gb);
	tabgl->addWidget(gb, 1, 2);
	label = new QLabel("Motor 1 (steps):");
	gl->addWidget(label, y, x);
	motor1 = new QLineEdit("0");
	gl->addWidget(motor1, y, x + 1);
	button = new QPushButton("Move");
	gl->addWidget(button, y++, x + 2);
	connect(button, SIGNAL(clicked()), this, SLOT(moveMotor1()));
	label = new QLabel("Motor 2 (steps):");
	gl->addWidget(label, y, x);
	motor2 = new QLineEdit("0");
	gl->addWidget(motor2, y, x + 1);
	button = new QPushButton("Move");
	gl->addWidget(button, y++, x + 2);
	connect(button, SIGNAL(clicked()), this, SLOT(moveMotor2()));
	label = new QLabel("Motor 3 (steps):");
	gl->addWidget(label, y, x);
	motor3 = new QLineEdit("0");
	gl->addWidget(motor3, y, x + 1);
	button = new QPushButton("Move");
	gl->addWidget(button, y++, x + 2);
	connect(button, SIGNAL(clicked()), this, SLOT(moveMotor3()));
	gl->setRowStretch(y, 0);

	// LEDs
	x = 0;
	y = 0;
	gb = new QGroupBox("LEDs");
	gl = new QGridLayout(gb);
	tabgl->addWidget(gb, 2, 0);
	for (i = 0; i < LED_COUNT; i++)
	{
		label = new QLabel(QString("LED %1:").arg(i + 1));
		gl->addWidget(label, y, x);
		cbLEDs[i] = new QComboBox();
		cbLEDs[i]->addItem("Off");
		cbLEDs[i]->addItem("On");
		cbLEDs[i]->addItem("Timed");
		gl->addWidget(cbLEDs[i], y++, x + 1);
	}
	gl->setRowStretch(y, 0);

	tabgl->setColumnStretch(3, 1);
	vl->addStretch(1);
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	button = new QPushButton("Apply");
	connect(button, SIGNAL(clicked()), this, SLOT(apply()));
	hl->addWidget(button);
	hl->addStretch(1);
	tabs->addTab(tab, QString("Slot %1: ATLAS").arg(slot));

	// Timing UI
	tabs = parent->waveformTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: ATLAS").arg(slot));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_C), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(copyClocks()));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_V), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(pasteClocks()));
	gl = new QGridLayout();
	tab->setLayout(gl);
	gl->setSpacing(10);
	label = new QLabel("LED");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 0);
	label = new QLabel("Keep");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 1);
	cbLED = new QCheckBox();
	gl->addWidget(cbLED, 1, 0, Qt::AlignHCenter);
	cbKeep = new QCheckBox();
	gl->addWidget(cbKeep, 1, 1, Qt::AlignHCenter);
	connect(cbLED, SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
	connect(cbKeep, SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
	gl->setVerticalSpacing(4);
	gl->setColumnStretch(2, 1);
	gl->setRowStretch(2, 1);

	// Sync UI with current settings
	updateUI();
}
//---------------------------------------------------------------------------
void ATLAS::parseUI()
{
	parent->config.insert(key + "/TECENABLE", QString::number(enable_tec->currentIndex()));
	parent->config.insert(key + "/IONENABLE", QString::number(enable_ion->currentIndex()));
	for (int i = 0; i < LED_COUNT; i++)
		parent->config.insert(key + QString("/LED%1").arg(i + 1), QString::number(cbLEDs[i]->currentIndex()));
}
//---------------------------------------------------------------------------
void ATLAS::updateUI()
{
	enable_tec->setCurrentIndex(qBound(0, parent->config.value(key + "/TECENABLE").toInt(), 2));
	enable_ion->setCurrentIndex(qBound(0, parent->config.value(key + "/IONENABLE").toInt(), 2));
	for (int i = 0; i < LED_COUNT; i++)
		cbLEDs[i]->setCurrentIndex(qBound(0, parent->config.value(key + QString("/LED%1").arg(i + 1)).toInt(), 2));
}
//---------------------------------------------------------------------------
void ATLAS::apply()
{
	parent->applyModule(slot);
}
//---------------------------------------------------------------------------
void ATLAS::moveMotor1()
{
	QStringList sl;

	sl.append("1");
	sl.append(motor1->text());
	parent->moduleCommand(slot, "ATLASMOVE", sl);
}
//---------------------------------------------------------------------------
void ATLAS::moveMotor2()
{
	QStringList sl;

	sl.append("2");
	sl.append(motor2->text());
	parent->moduleCommand(slot, "ATLASMOVE", sl);
}
//---------------------------------------------------------------------------
void ATLAS::moveMotor3()
{
	QString s;
	QStringList sl;

	sl.append("3");
	sl.append(motor3->text());
	parent->moduleCommand(slot, "ATLASMOVE", sl);
}
//---------------------------------------------------------------------------
void ATLAS::setClocks(const QVariantMap& map)
{
	QStringList sl = map.value(key).toString().split(",");

	cbLED->setChecked(sl.value(0, "1") == "1");
	cbKeep->setChecked(sl.value(1, "1") == "1");
}
//---------------------------------------------------------------------------
void ATLAS::getClocks(QVariantMap& map)
{
	QStringList sl;

	sl.append(cbLED->isChecked() ? "1" : "0");
	sl.append(cbKeep->isChecked() ? "1" : "0");
	map.insert(key, sl.join(","));
}
//---------------------------------------------------------------------------
void ATLAS::clockChanged()
{
	cbLED->setEnabled(!cbKeep->isChecked());
	parent->clockChanged();
}
//---------------------------------------------------------------------------
void ATLAS::copyClocks()
{
	QStringList sl;
	QString s;

	sl.append(cbLED->isChecked() ? "1" : "0");
	sl.append(cbKeep->isChecked() ? "1" : "0");
	s = sl.join(",");
	QApplication::clipboard()->setText(s);
}
//---------------------------------------------------------------------------
void ATLAS::pasteClocks()
{
	QStringList sl;

	sl = QApplication::clipboard()->text().split(",");
	cbLED->setChecked(sl.value(0, "1") == "1");
	cbKeep->setChecked(sl.value(1, "1") == "1");
}
//---------------------------------------------------------------------------
double convrtd(double r)
{
	int i;
	double t, e, x;

	// DIN 43760 alpha = 0.00385 curve
	double A = 3.9080e-3;
	double B = -5.8019e-7;
	double C = -4.2735e-12;
	double R0 = 1000.0;

	if (r > R0)
		C = 0.0;

	// Initial guess
	t = (r / R0 - 1) / A;

	// Iterate
	for (i = 0; i < 10; i++)
	{
		x = R0 * (1.0 + A * t + B * t * t + C * (t - 100.0) * t * t * t);
		e = r - x;
		t += 0.9 * (e / R0) / A;
	}

	return t;
}

//---------------------------------------------------------------------------
void ATLAS::parseStatus(const RMap &data)
{
	int i;
	double d, t;
	bool ok;

	i = data.value(key + "/TEC_ENABLE", "-").toInt(&ok);
	if (ok)
		tec_enabled->setText(i ? "Enabled" : "Disabled");
	tec_voltage->setText(data.value(key + "/TEC_V", "-"));
	tec_current->setText(data.value(key + "/TEC_I", "-"));

	i = data.value(key + "/ION_ENABLE", "-").toInt(&ok);
	if (ok)
		ion_enabled->setText(i ? "Enabled" : "Disabled");
	ion_voltage->setText(data.value(key + "/ION_V", "-"));
	ion_current->setText(data.value(key + "/ION_I", "-"));

	for (i = 0; i < RTD_COUNT; i++)
	{
		d = data.value(key + QString("/RTD%1").arg(i + 1), "-").toDouble(&ok);
		if (!ok || (d < 10.0) || (d > 2000.0))
			rtd[i]->setText("-");
		else
		{
			t = convrtd(d);
			rtd[i]->setText(QString::number(t, 'f', 2));
		}
	}

	for (i = 0; i < HALL_COUNT; i++)
		hall[i]->setText(data.value(key + QString("/HALL%1").arg(i + 1), "-"));

	d = data.value(key + "/VAC", "0").toDouble(&ok);
	if (ok && (d > 0))
		vac_reading->setText(sci(d / 1E6, 0, 3));
	else
		vac_reading->setText("ERR");
}
/////////////////////////////////////////////////////////////////////////////////
// HS Module
HS::HS(TArchonGUI *parent, QString key, int slot) : TModule(parent, key, slot)
{
}
//---------------------------------------------------------------------------
void HS::createUI()
{
	int i, x;
	QVBoxLayout *vl;
	QGridLayout *gl;
	QHBoxLayout *hl;
	QLabel *label;
	QPushButton *button;
	QTabWidget *tabs;
	QWidget *tab;
	QShortcut *shortcut;
	QFont boldFont, fixedFont;

	// Module UI
	tabs = parent->systemTabs();
	tab = new QWidget();
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	gl = new QGridLayout();
	vl->addLayout(gl);
	gl->setHorizontalSpacing(10);
	gl->setVerticalSpacing(4);

	// High speed clock
	label = new QLabel("HS Clock");
	boldFont = label->font();
	boldFont.setBold(true);
	fixedFont = label->font();
	fixedFont.setFamily("Monotype");
	fixedFont.setStyleHint(QFont::TypeWriter);
	label->setFont(boldFont);
	gl->addWidget(label, 0, 0, 1, 2, Qt::AlignHCenter);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 0);
	label = new QLabel("Label");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 1);
	for (i = 0; i < HS_COUNT; i++)
	{
		// IDs and labels
		label = new QLabel(QString("HS%1").arg(i + 1));
		gl->addWidget(label, i + 2, 0);
		hs_label[i] = new QLineEdit();
		gl->addWidget(hs_label[i], i + 2, 1);
	}
	gl->setColumnMinimumWidth(2, 30);

	// Mag
	x = 3;
	label = new QLabel("Magnitude");
	label->setFont(boldFont);
	gl->addWidget(label, 0, x, 1, 2, Qt::AlignHCenter);
	label = new QLabel("Measured");
	label->setFont(boldFont);
	gl->addWidget(label, 0, x + 2, 1, 2, Qt::AlignHCenter);
	label = new QLabel("Mag Label");
	label->setFont(boldFont);
	gl->addWidget(label, 1, x);
	label = new QLabel("V (5..14)");
	label->setFont(boldFont);
	gl->addWidget(label, 1, x + 1);
	label = new QLabel("V");
	label->setAlignment(Qt::AlignHCenter);
	label->setFont(boldFont);
	gl->addWidget(label, 1, x + 2);
	label = new QLabel("mA");
	label->setAlignment(Qt::AlignHCenter);
	label->setFont(boldFont);
	gl->addWidget(label, 1, x + 3);
	for (i = 0; i < HS_COUNT; i++)
	{
		// Label
		mag_label[i] = new QLineEdit();
		gl->addWidget(mag_label[i], i + 2, x);
		// Commanded voltage
		mag_v_cmd[i] = new QLineEdit("5.0");
		gl->addWidget(mag_v_cmd[i], i + 2, x + 1);
		// Voltage and current readings
		mag_v[i] = new QLabel("-");
		mag_v[i]->setFont(fixedFont);
		gl->addWidget(mag_v[i], i + 2, x + 2);
		mag_i[i] = new QLabel("-");
		mag_i[i]->setFont(fixedFont);
		gl->addWidget(mag_i[i], i + 2, x + 3);
	}
	gl->setColumnMinimumWidth(x + 4, 30);
	x += 5;

	// Ofs
	label = new QLabel("Offset");
	label->setFont(boldFont);
	gl->addWidget(label, 0, x, 1, 2, Qt::AlignHCenter);
	label = new QLabel("Measured");
	label->setFont(boldFont);
	gl->addWidget(label, 0, x + 2, 1, 2, Qt::AlignHCenter);
	label = new QLabel("Ofs Label");
	label->setFont(boldFont);
	gl->addWidget(label, 1, x);
	label = new QLabel("V (-14..14)");
	label->setFont(boldFont);
	gl->addWidget(label, 1, x + 1);
	label = new QLabel("V");
	label->setAlignment(Qt::AlignHCenter);
	label->setFont(boldFont);
	gl->addWidget(label, 1, x + 2);
	label = new QLabel("mA");
	label->setAlignment(Qt::AlignHCenter);
	label->setFont(boldFont);
	gl->addWidget(label, 1, x + 3);
	for (i = 0; i < HS_COUNT; i++)
	{
		// Label
		ofs_label[i] = new QLineEdit();
		gl->addWidget(ofs_label[i], i + 2, x);
		// Commanded voltage
		ofs_v_cmd[i] = new QLineEdit("0.0");
		gl->addWidget(ofs_v_cmd[i], i + 2, x + 1);
		// Voltage and current readings
		ofs_v[i] = new QLabel("-");
		ofs_v[i]->setFont(fixedFont);
		gl->addWidget(ofs_v[i], i + 2, x + 2);
		ofs_i[i] = new QLabel("-");
		ofs_i[i]->setFont(fixedFont);
		gl->addWidget(ofs_i[i], i + 2, x + 3);
	}
	gl->setColumnMinimumWidth(x + 4, 30);
	x += 5;

	// DIO
	label = new QLabel("Digital I/O");
	label->setFont(boldFont);
	gl->addWidget(label, 0, x, 1, 3, Qt::AlignHCenter);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, 1, x);
	label = new QLabel("Label");
	label->setFont(boldFont);
	gl->addWidget(label, 1, x + 1);
	label = new QLabel("Source");
	label->setFont(boldFont);
	gl->addWidget(label, 1, x + 2);
	label = new QLabel("Status");
	label->setFont(boldFont);
	gl->addWidget(label, 1, x + 3);
	label = new QLabel("Direction");
	label->setFont(boldFont);
	gl->addWidget(label, 1, x + 4);
	for (i = 0; i < DIO_HS_COUNT; i++)
	{
		// IDs and labels
		label = new QLabel(QString("DIO%1").arg(i + 1));
		gl->addWidget(label, i + 2, x);
		leDIOLabels[i] = new QLineEdit();
		gl->addWidget(leDIOLabels[i], i + 2, x + 1);
		cbDIOSources[i] = new QComboBox();
		cbDIOSources[i]->addItem("Low");
		cbDIOSources[i]->addItem("High");
		cbDIOSources[i]->addItem("Clocked");
		cbDIOSources[i]->addItem("VCPU");
		gl->addWidget(cbDIOSources[i], i + 2, x + 2);
		lDIOStatus[i] = new QLabel("-");
		gl->addWidget(lDIOStatus[i], i + 2, x + 3);
		cbDIODirections[i] = new QComboBox();
		cbDIODirections[i]->addItem("Input");
		cbDIODirections[i]->addItem("Output");
		gl->addWidget(cbDIODirections[i], i + 2, x + 4);
	}
	label = new QLabel("DIO Power");
	label->setFont(boldFont);
	gl->addWidget(label, DIO_HS_COUNT + 3, x, 1, 2);
	cbDIOPower = new QComboBox();
	cbDIOPower->addItem("Disabled");
	cbDIOPower->addItem("Enabled");
	gl->addWidget(cbDIOPower, DIO_HS_COUNT + 3, x + 2);
	gl->setColumnStretch(x + 5, 1);
	vl->addStretch(1);
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	button = new QPushButton("Apply");
	connect(button, SIGNAL(clicked()), this, SLOT(apply()));
	hl->addWidget(button);
	hl->addStretch(1);
	QScrollArea *scroll = new QScrollArea();
	scroll->setWidget(tab);
	tabs->addTab(scroll, QString("Slot %1: HS").arg(slot));

	// Timing UI
	tabs = parent->waveformTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: HS").arg(slot));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_C), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(copyClocks()));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_V), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(pasteClocks()));
	gl = new QGridLayout();
	tab->setLayout(gl);
	gl->setSpacing(10);
	label = new QLabel("Name");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 0);
	label = new QLabel("Sequence");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 1);
	label = new QLabel("Keep");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 2);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 3);
	for (i = 0; i < HS_COUNT; i++)
	{
		lRefLabels[i] = new QLabel();
		connect(hs_label[i], SIGNAL(textChanged(QString)), lRefLabels[i], SLOT(setText(QString)));
		hs_sequence[i] = new QLineEdit("0000000000");
		cbKeeps[i] = new QCheckBox();
		connect(hs_sequence[i], SIGNAL(textChanged(QString)), this, SLOT(clockChanged()));
		connect(cbKeeps[i], SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		label = new QLabel();
		label->setText(QString("HS%1").arg(i + 1));
		gl->addWidget(lRefLabels[i], i + 1, 0);
		gl->addWidget(hs_sequence[i], i + 1, 1);
		gl->addWidget(cbKeeps[i], i + 1, 2, Qt::AlignHCenter);
		gl->addWidget(label, i + 1, 3);
	}
	gl->setColumnMinimumWidth(4, 30);
	// DIO Timing
	label = new QLabel("DIO Label");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 5);
	label = new QLabel("DIO State");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 6);
	label = new QLabel("Keep");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 7);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 8);
	for (i = 0; i < DIO_HS_COUNT; i++)
	{
		lDIORefLabels[i] = new QLabel();
		connect(leDIOLabels[i], SIGNAL(textChanged(QString)), lDIORefLabels[i], SLOT(setText(QString)));
		cbDIOStates[i] = new QCheckBox();
		cbDIOKeeps[i] = new QCheckBox();
		connect(cbDIOStates[i], SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		connect(cbDIOKeeps[i], SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		label = new QLabel();
		label->setText(QString("DIO%1").arg(i + 1));
		gl->addWidget(lDIORefLabels[i], i + 1, 5);
		gl->addWidget(cbDIOStates[i], i + 1, 6, Qt::AlignHCenter);
		gl->addWidget(cbDIOKeeps[i], i + 1, 7, Qt::AlignHCenter);
		gl->addWidget(label, i + 1, 8);
	}

	gl->setVerticalSpacing(4);
	gl->setColumnStretch(9, 1);
	gl->setRowStretch(HS_COUNT + 1, 1);

	// VCPU UI
	tabs = parent->vcpuTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: HS").arg(slot));
	gl = new QGridLayout();
	tab->setLayout(gl);
	gl->setSpacing(10);
	teVCPU = new QPlainTextEdit();
	teVCPU->setLineWrapMode(QPlainTextEdit::NoWrap);
	label = new QLabel("Code");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 0);
	gl->addWidget(teVCPU, 1, 0, VCPU_COUNT + 1, 1);
	label = new QLabel("Register");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 1);
	label = new QLabel("Input");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 2);
	label = new QLabel("Output");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 3);
	for (i = 0; i < VCPU_COUNT; i++)
	{
		label = new QLabel(QString("REG%1").arg(i));
		gl->addWidget(label, i + 1, 1);
		leVCPUInReg[i] = new QLineEdit("0");
		gl->addWidget(leVCPUInReg[i], i + 1, 2);
		lVCPUOutReg[i] = new QLabel("-");
		gl->addWidget(lVCPUOutReg[i], i + 1, 3);
	}
	gl->setColumnStretch(0, 1);
	gl->setRowStretch(VCPU_COUNT + 1, 1);
	gl->setColumnMinimumWidth(3, 100);
	hl = new QHBoxLayout();
	button = new QPushButton("Apply");
	connect(button, SIGNAL(clicked()), this, SLOT(applyDIO()));
	hl->addWidget(button);
	hl->addStretch(0);
	gl->addLayout(hl, VCPU_COUNT + 2, 0);

	// Sync UI with current settings
	updateUI();
}
//---------------------------------------------------------------------------
void HS::parseUI()
{
	int i, count;
	QStringList sl;

	for (i = 0; i < HS_COUNT; i++)
	{
		parent->config.insert(key + QString("/HS_LABEL%1").arg(i + 1), hs_label[i]->text());
		parent->config.insert(key + QString("/MAG_LABEL%1").arg(i + 1), mag_label[i]->text());
		parent->config.insert(key + QString("/MAG_V%1").arg(i + 1), mag_v_cmd[i]->text());
		parent->config.insert(key + QString("/OFS_LABEL%1").arg(i + 1), ofs_label[i]->text());
		parent->config.insert(key + QString("/OFS_V%1").arg(i + 1), ofs_v_cmd[i]->text());
	}
	for (i = 0; i < DIO_HS_COUNT; i++)
	{
		parent->config.insert(key + QString("/DIO_LABEL%1").arg(i + 1), leDIOLabels[i]->text());
		parent->config.insert(key + QString("/DIO_SOURCE%1").arg(i + 1), QString::number(cbDIOSources[i]->currentIndex()));
		parent->config.insert(key + QString("/DIO_DIR%1").arg(i + 1), QString::number(cbDIODirections[i]->currentIndex()));
	}
	parent->config.insert(key + "/DIO_POWER", QString::number(cbDIOPower->currentIndex()));
	// VCPU code
	sl = teVCPU->toPlainText().split('\n');
	count = sl.count();
	parent->config.insert(key + "/VCPU_LINES", QString::number(count));
	for (i = 0; i < count; i++)
		parent->config.insert(key + QString("/VCPU_LINE%1").arg(i), sl[i]);
	for (i = 0; i < VCPU_COUNT; i++)
		parent->config.insert(key + QString("/VCPU_INREG%1").arg(i), leVCPUInReg[i]->text());
}
//---------------------------------------------------------------------------
void HS::updateUI()
{
	int i, count;
	bool ok;

	for (i = 0; i < HS_COUNT; i++)
	{
		hs_label[i]->setText(parent->config.value(key + QString("/HS_LABEL%1").arg(i + 1)));
		mag_label[i]->setText(parent->config.value(key + QString("/MAG_LABEL%1").arg(i + 1)));
		mag_v_cmd[i]->setText(parent->config.value(key + QString("/MAG_V%1").arg(i + 1), "5.0"));
		ofs_label[i]->setText(parent->config.value(key + QString("/OFS_LABEL%1").arg(i + 1)));
		ofs_v_cmd[i]->setText(parent->config.value(key + QString("/OFS_V%1").arg(i + 1), "0.0"));
	}
	for (i = 0; i < DIO_HS_COUNT; i++)
	{
		leDIOLabels[i]->setText(parent->config.value(key + QString("/DIO_LABEL%1").arg(i + 1)));
		cbDIOSources[i]->setCurrentIndex(qBound(0, parent->config.value(key + QString("/DIO_SOURCE%1").arg(i + 1)).toInt(), 3));
		cbDIODirections[i]->setCurrentIndex(qBound(0, parent->config.value(key + QString("/DIO_DIR%1").arg(i + 1)).toInt(), 1));
	}
	cbDIOPower->setCurrentIndex(qBound(0, parent->config.value(key + "/DIO_POWER").toInt(), 1));
	// VCPU code
	count = parent->config.value(key + "/VCPU_LINES").toInt(&ok);
	if (ok)
	{
		teVCPU->clear();
		for (i = 0; i < count; i++)
			teVCPU->appendPlainText(parent->config.value(key + QString("/VCPU_LINE%1").arg(i)));
	}
	for (i = 0; i < VCPU_COUNT; i++)
		leVCPUInReg[i]->setText(parent->config.value(key + QString("/VCPU_INREG%1").arg(i + 1), "0"));
}
//---------------------------------------------------------------------------
void HS::apply()
{
	parent->applyModule(slot);
}
//---------------------------------------------------------------------------
void HS::applyDIO()
{
	parent->applyModuleDIO(slot);
}
//---------------------------------------------------------------------------
void HS::setClocks(const QVariantMap& map)
{
	int i;
	QStringList sl = map.value(key).toString().split(",");

	for (i = 0; i < HS_COUNT; i++)
	{
		hs_sequence[i]->setText(sl.value(i * 2, "0000000000"));
		cbKeeps[i]->setChecked(sl.value(i * 2 + 1, "1") == "1");
		hs_sequence[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
	for (i = 0; i < DIO_HS_COUNT; i++)
	{
		cbDIOStates[i]->setChecked(sl.value((i + HS_COUNT) * 2, "1") == "1");
		cbDIOKeeps[i]->setChecked(sl.value((i + HS_COUNT) * 2 + 1, "1") == "1");
		cbDIOStates[i]->setEnabled(!cbDIOKeeps[i]->isChecked());
	}
}
//---------------------------------------------------------------------------
void HS::getClocks(QVariantMap& map)
{
	int i;
	QStringList sl;

	for (i = 0; i < HS_COUNT; i++)
	{
		sl.append(hs_sequence[i]->text());
		sl.append(cbKeeps[i]->isChecked() ? "1" : "0");
	}
	for (i = 0; i < DIO_HS_COUNT; i++)
	{
		sl.append(cbDIOStates[i]->isChecked() ? "1" : "0");
		sl.append(cbDIOKeeps[i]->isChecked() ? "1" : "0");
	}
	map.insert(key, sl.join(","));
}
//---------------------------------------------------------------------------
void HS::clockChanged()
{
	int i;

	for (i = 0; i < HS_COUNT; i++)
	{
		hs_sequence[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
	for (i = 0; i < DIO_HS_COUNT; i++)
	{
		cbDIOStates[i]->setEnabled(!cbDIOKeeps[i]->isChecked());
	}
	parent->clockChanged();
}
//---------------------------------------------------------------------------
void HS::copyClocks()
{
	int i;
	QStringList sl;
	QString s;

	for (i = 0; i < HS_COUNT; i++)
	{
		sl.append(hs_sequence[i]->text());
		sl.append(cbKeeps[i]->isChecked() ? "1" : "0");
	}
	for (i = 0; i < DIO_HS_COUNT; i++)
	{
		sl.append(cbDIOStates[i]->isChecked() ? "1" : "0");
		sl.append(cbDIOKeeps[i]->isChecked() ? "1" : "0");
	}
	s = sl.join(",");
	QApplication::clipboard()->setText(s);
}
//---------------------------------------------------------------------------
void HS::pasteClocks()
{
	int i;
	QStringList sl;

	sl = QApplication::clipboard()->text().split(",");
	for (i = 0; i < HS_COUNT; i++)
	{
		hs_sequence[i]->setText(sl.value(i * 2, "0000000000"));
		cbKeeps[i]->setChecked(sl.value(i * 2 + 1, "1") == "1");
		hs_sequence[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
	for (i = 0; i < DIO_HS_COUNT; i++)
	{
		cbDIOStates[i]->setChecked(sl.value((i + HS_COUNT) * 2, "1") == "1");
		cbDIOKeeps[i]->setChecked(sl.value((i + HS_COUNT) * 2 + 1, "1") == "1");
		cbDIOStates[i]->setEnabled(!cbDIOKeeps[i]->isChecked());
	}
}
//---------------------------------------------------------------------------
void HS::parseStatus(const RMap &data)
{
	int i;
	QString s;

	for (i = 0; i < HS_COUNT; i++)
	{
		mag_v[i]->setText(data.value(key + QString("/MAG_V%1").arg(i + 1), "-").rightJustified(8));
		mag_i[i]->setText(data.value(key + QString("/MAG_I%1").arg(i + 1), "-").rightJustified(8));
		ofs_v[i]->setText(data.value(key + QString("/OFS_V%1").arg(i + 1), "-").rightJustified(8));
		ofs_i[i]->setText(data.value(key + QString("/OFS_I%1").arg(i + 1), "-").rightJustified(8));
	}
	// DIO
	s = data.value(key + "/DINPUTS", "----");
	if (s.length() != DIO_HS_COUNT)
		s = "----";
	for (i = 0; i < DIO_HS_COUNT; i++)
		lDIOStatus[i]->setText(s.mid(i, 1));
	// VCPU registers
	for (i = 0; i < VCPU_COUNT; i++)
	{
		s = data.value(key + QString("/VCPU_OUTREG%1").arg(i), "-");
		lVCPUOutReg[i]->setText(s);
	}
}
/////////////////////////////////////////////////////////////////////////////////
// LVDS Module
LVDS::LVDS(TArchonGUI *parent, QString key, int slot) : TModule(parent, key, slot)
{
}
//---------------------------------------------------------------------------
void LVDS::createUI()
{
	int i, x;
	QVBoxLayout *vl;
	QGridLayout *gl;
	QHBoxLayout *hl;
	QLabel *label;
	QPushButton *button;
	QTabWidget *tabs;
	QWidget *tab;
	QShortcut *shortcut;
	QFont boldFont, fixedFont;

	// Module UI
	tabs = parent->systemTabs();
	tab = new QWidget();
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	gl = new QGridLayout();
	vl->addLayout(gl);
	gl->setHorizontalSpacing(10);
	gl->setVerticalSpacing(4);

	// LVDS clock
	label = new QLabel("LVDS Clock");
	boldFont = label->font();
	boldFont.setBold(true);
	fixedFont = label->font();
	fixedFont.setFamily("Monotype");
	fixedFont.setStyleHint(QFont::TypeWriter);
	label->setFont(boldFont);
	gl->addWidget(label, 0, 0, 1, 2, Qt::AlignHCenter);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 0);
	label = new QLabel("Label");
	label->setFont(boldFont);
	gl->addWidget(label, 1, 1);
	for (i = 0; i < LVDS_COUNT; i++)
	{
		// IDs and labels
		label = new QLabel(QString("LVDS%1").arg(i + 1));
		gl->addWidget(label, i + 2, 0);
		lvds_label[i] = new QLineEdit();
		gl->addWidget(lvds_label[i], i + 2, 1);
	}
	gl->setColumnMinimumWidth(2, 30);

	// DIO
	x = 3;
	label = new QLabel("Digital I/O");
	label->setFont(boldFont);
	gl->addWidget(label, 0, x, 1, 3, Qt::AlignHCenter);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, 1, x);
	label = new QLabel("Label");
	label->setFont(boldFont);
	gl->addWidget(label, 1, x + 1);
	label = new QLabel("Source");
	label->setFont(boldFont);
	gl->addWidget(label, 1, x + 2);
	label = new QLabel("Status");
	label->setFont(boldFont);
	gl->addWidget(label, 1, x + 3);
	label = new QLabel("Direction");
	label->setFont(boldFont);
	gl->addWidget(label, 1, x + 4);
	for (i = 0; i < DIO_LVDS_COUNT; i++)
	{
		// IDs and labels
		label = new QLabel(QString("DIO%1").arg(i + 1));
		gl->addWidget(label, i + 2, x);
		leDIOLabels[i] = new QLineEdit();
		gl->addWidget(leDIOLabels[i], i + 2, x + 1);
		cbDIOSources[i] = new QComboBox();
		cbDIOSources[i]->addItem("Low");
		cbDIOSources[i]->addItem("High");
		cbDIOSources[i]->addItem("Clocked");
		cbDIOSources[i]->addItem("VCPU");
		gl->addWidget(cbDIOSources[i], i + 2, x + 2);
		lDIOStatus[i] = new QLabel("-");
		gl->addWidget(lDIOStatus[i], i + 2, x + 3);
		cbDIODirections[i] = new QComboBox();
		cbDIODirections[i]->addItem("Input");
		cbDIODirections[i]->addItem("Output");
		gl->addWidget(cbDIODirections[i], i + 2, x + 4);
	}
	label = new QLabel("DIO Power");
	label->setFont(boldFont);
	gl->addWidget(label, DIO_LVDS_COUNT + 3, x, 1, 2);
	cbDIOPower = new QComboBox();
	cbDIOPower->addItem("Disabled");
	cbDIOPower->addItem("Enabled");
	gl->addWidget(cbDIOPower, DIO_LVDS_COUNT + 3, x + 2);
	gl->setColumnStretch(x + 5, 1);
	vl->addStretch(1);
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	button = new QPushButton("Apply");
	connect(button, SIGNAL(clicked()), this, SLOT(apply()));
	hl->addWidget(button);
	hl->addStretch(1);
	QScrollArea *scroll = new QScrollArea();
	scroll->setWidget(tab);
	tabs->addTab(scroll, QString("Slot %1: LVDS").arg(slot));

	// Timing UI
	tabs = parent->waveformTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: LVDS").arg(slot));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_C), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(copyClocks()));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_V), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(pasteClocks()));
	gl = new QGridLayout();
	tab->setLayout(gl);
	gl->setSpacing(10);
	label = new QLabel("Name");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 0);
	label = new QLabel("State");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 1);
	label = new QLabel("Keep");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 2);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 3);
	for (i = 0; i < LVDS_COUNT; i++)
	{
		lRefLabels[i] = new QLabel();
		connect(lvds_label[i], SIGNAL(textChanged(QString)), lRefLabels[i], SLOT(setText(QString)));
		lvds_state[i] = new QLineEdit("0");
		cbKeeps[i] = new QCheckBox();
		connect(lvds_state[i], SIGNAL(textChanged(QString)), this, SLOT(clockChanged()));
		connect(cbKeeps[i], SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		label = new QLabel();
		label->setText(QString("LVDS%1").arg(i + 1));
		gl->addWidget(lRefLabels[i], i + 1, 0);
		gl->addWidget(lvds_state[i], i + 1, 1);
		gl->addWidget(cbKeeps[i], i + 1, 2, Qt::AlignHCenter);
		gl->addWidget(label, i + 1, 3);
	}
	gl->setColumnMinimumWidth(4, 30);
	// DIO Timing
	label = new QLabel("DIO Label");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 5);
	label = new QLabel("DIO State");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 6);
	label = new QLabel("Keep");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 7);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 8);
	for (i = 0; i < DIO_LVDS_COUNT; i++)
	{
		lDIORefLabels[i] = new QLabel();
		connect(leDIOLabels[i], SIGNAL(textChanged(QString)), lDIORefLabels[i], SLOT(setText(QString)));
		cbDIOStates[i] = new QCheckBox();
		cbDIOKeeps[i] = new QCheckBox();
		connect(cbDIOStates[i], SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		connect(cbDIOKeeps[i], SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		label = new QLabel();
		label->setText(QString("DIO%1").arg(i + 1));
		gl->addWidget(lDIORefLabels[i], i + 1, 5);
		gl->addWidget(cbDIOStates[i], i + 1, 6, Qt::AlignHCenter);
		gl->addWidget(cbDIOKeeps[i], i + 1, 7, Qt::AlignHCenter);
		gl->addWidget(label, i + 1, 8);
	}

	gl->setVerticalSpacing(4);
	gl->setColumnStretch(9, 1);
	gl->setRowStretch(LVDS_COUNT + 1, 1);

	// VCPU UI
	tabs = parent->vcpuTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: LVDS").arg(slot));
	gl = new QGridLayout();
	tab->setLayout(gl);
	gl->setSpacing(10);
	teVCPU = new QPlainTextEdit();
	teVCPU->setLineWrapMode(QPlainTextEdit::NoWrap);
	label = new QLabel("Code");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 0);
	gl->addWidget(teVCPU, 1, 0, VCPU_COUNT + 1, 1);
	label = new QLabel("Register");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 1);
	label = new QLabel("Input");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 2);
	label = new QLabel("Output");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 3);
	for (i = 0; i < VCPU_COUNT; i++)
	{
		label = new QLabel(QString("REG%1").arg(i));
		gl->addWidget(label, i + 1, 1);
		leVCPUInReg[i] = new QLineEdit("0");
		gl->addWidget(leVCPUInReg[i], i + 1, 2);
		lVCPUOutReg[i] = new QLabel("-");
		gl->addWidget(lVCPUOutReg[i], i + 1, 3);
	}
	gl->setColumnStretch(0, 1);
	gl->setRowStretch(VCPU_COUNT + 1, 1);
	gl->setColumnMinimumWidth(3, 100);
	hl = new QHBoxLayout();
	button = new QPushButton("Apply");
	connect(button, SIGNAL(clicked()), this, SLOT(apply()));
	hl->addWidget(button);
	hl->addStretch(0);
	gl->addLayout(hl, VCPU_COUNT + 2, 0);

	// Sync UI with current settings
	updateUI();
}
//---------------------------------------------------------------------------
void LVDS::parseUI()
{
	int i, count;
	QStringList sl;

	for (i = 0; i < LVDS_COUNT; i++)
	{
		parent->config.insert(key + QString("/LVDS_LABEL%1").arg(i + 1), lvds_label[i]->text());
	}
	for (i = 0; i < DIO_LVDS_COUNT; i++)
	{
		parent->config.insert(key + QString("/DIO_LABEL%1").arg(i + 1), leDIOLabels[i]->text());
		parent->config.insert(key + QString("/DIO_SOURCE%1").arg(i + 1), QString::number(cbDIOSources[i]->currentIndex()));
		parent->config.insert(key + QString("/DIO_DIR%1").arg(i + 1), QString::number(cbDIODirections[i]->currentIndex()));
	}
	parent->config.insert(key + "/DIO_POWER", QString::number(cbDIOPower->currentIndex()));
	// VCPU code
	sl = teVCPU->toPlainText().split('\n');
	count = sl.count();
	parent->config.insert(key + "/VCPU_LINES", QString::number(count));
	for (i = 0; i < count; i++)
		parent->config.insert(key + QString("/VCPU_LINE%1").arg(i), sl[i]);
	for (i = 0; i < VCPU_COUNT; i++)
		parent->config.insert(key + QString("/VCPU_INREG%1").arg(i), leVCPUInReg[i]->text());
}
//---------------------------------------------------------------------------
void LVDS::updateUI()
{
	int i, count;
	bool ok;

	for (i = 0; i < LVDS_COUNT; i++)
	{
		lvds_label[i]->setText(parent->config.value(key + QString("/LVDS_LABEL%1").arg(i + 1)));
	}
	for (i = 0; i < DIO_LVDS_COUNT; i++)
	{
		leDIOLabels[i]->setText(parent->config.value(key + QString("/DIO_LABEL%1").arg(i + 1)));
		cbDIOSources[i]->setCurrentIndex(qBound(0, parent->config.value(key + QString("/DIO_SOURCE%1").arg(i + 1)).toInt(), 3));
		cbDIODirections[i]->setCurrentIndex(qBound(0, parent->config.value(key + QString("/DIO_DIR%1").arg(i + 1)).toInt(), 1));
	}
	cbDIOPower->setCurrentIndex(qBound(0, parent->config.value(key + "/DIO_POWER").toInt(), 1));
	// VCPU code
	count = parent->config.value(key + "/VCPU_LINES").toInt(&ok);
	if (ok)
	{
		teVCPU->clear();
		for (i = 0; i < count; i++)
			teVCPU->appendPlainText(parent->config.value(key + QString("/VCPU_LINE%1").arg(i)));
	}
	for (i = 0; i < VCPU_COUNT; i++)
		leVCPUInReg[i]->setText(parent->config.value(key + QString("/VCPU_INREG%1").arg(i + 1), "0"));
}
//---------------------------------------------------------------------------
void LVDS::apply()
{
	parent->applyModule(slot);
}
//---------------------------------------------------------------------------
void LVDS::setClocks(const QVariantMap& map)
{
	int i;
	QStringList sl = map.value(key).toString().split(",");

	for (i = 0; i < LVDS_COUNT; i++)
	{
		lvds_state[i]->setText(sl.value(i * 2, "0"));
		cbKeeps[i]->setChecked(sl.value(i * 2 + 1, "1") == "1");
		lvds_state[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
	for (i = 0; i < DIO_LVDS_COUNT; i++)
	{
		cbDIOStates[i]->setChecked(sl.value((i + LVDS_COUNT) * 2, "1") == "1");
		cbDIOKeeps[i]->setChecked(sl.value((i + LVDS_COUNT) * 2 + 1, "1") == "1");
		cbDIOStates[i]->setEnabled(!cbDIOKeeps[i]->isChecked());
	}
}
//---------------------------------------------------------------------------
void LVDS::getClocks(QVariantMap& map)
{
	int i;
	QStringList sl;

	for (i = 0; i < LVDS_COUNT; i++)
	{
		sl.append(lvds_state[i]->text());
		sl.append(cbKeeps[i]->isChecked() ? "1" : "0");
	}
	for (i = 0; i < DIO_LVDS_COUNT; i++)
	{
		sl.append(cbDIOStates[i]->isChecked() ? "1" : "0");
		sl.append(cbDIOKeeps[i]->isChecked() ? "1" : "0");
	}
	map.insert(key, sl.join(","));
}
//---------------------------------------------------------------------------
void LVDS::clockChanged()
{
	int i;

	for (i = 0; i < LVDS_COUNT; i++)
	{
		lvds_state[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
	for (i = 0; i < DIO_LVDS_COUNT; i++)
	{
		cbDIOStates[i]->setEnabled(!cbDIOKeeps[i]->isChecked());
	}
	parent->clockChanged();
}
//---------------------------------------------------------------------------
void LVDS::copyClocks()
{
	int i;
	QStringList sl;
	QString s;

	for (i = 0; i < LVDS_COUNT; i++)
	{
		sl.append(lvds_state[i]->text());
		sl.append(cbKeeps[i]->isChecked() ? "1" : "0");
	}
	for (i = 0; i < DIO_LVDS_COUNT; i++)
	{
		sl.append(cbDIOStates[i]->isChecked() ? "1" : "0");
		sl.append(cbDIOKeeps[i]->isChecked() ? "1" : "0");
	}
	s = sl.join(",");
	QApplication::clipboard()->setText(s);
}
//---------------------------------------------------------------------------
void LVDS::pasteClocks()
{
	int i;
	QStringList sl;

	sl = QApplication::clipboard()->text().split(",");
	for (i = 0; i < LVDS_COUNT; i++)
	{
		lvds_state[i]->setText(sl.value(i * 2, "0"));
		cbKeeps[i]->setChecked(sl.value(i * 2 + 1, "1") == "1");
		lvds_state[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
	for (i = 0; i < DIO_LVDS_COUNT; i++)
	{
		cbDIOStates[i]->setChecked(sl.value((i + LVDS_COUNT) * 2, "1") == "1");
		cbDIOKeeps[i]->setChecked(sl.value((i + LVDS_COUNT) * 2 + 1, "1") == "1");
		cbDIOStates[i]->setEnabled(!cbDIOKeeps[i]->isChecked());
	}
}
//---------------------------------------------------------------------------
void LVDS::parseStatus(const RMap &data)
{
	int i;
	QString s;

	// DIO
	s = data.value(key + "/DINPUTS", "----");
	if (s.length() != DIO_LVDS_COUNT)
		s = "----";
	for (i = 0; i < DIO_LVDS_COUNT; i++)
		lDIOStatus[i]->setText(s.mid(i, 1));
	// VCPU registers
	for (i = 0; i < VCPU_COUNT; i++)
	{
		s = data.value(key + QString("/VCPU_OUTREG%1").arg(i), "-");
		lVCPUOutReg[i]->setText(s);
	}
}
/////////////////////////////////////////////////////////////////////////////////
// HeaterX Module
HEATERX::HEATERX(TArchonGUI *parent, QString key, int slot) : TModule(parent, key, slot)
{
	build = parent->system.value(QString("MOD%1_VERSION").arg(slot)).split(".").value(2).toInt();
	backplane_build = parent->system.value("BACKPLANE_VERSION").split(".").value(2).toInt();
}
//---------------------------------------------------------------------------
void HEATERX::createUI()
{
	int i, x, y;
	QVBoxLayout *vl;
	QGridLayout *gl;
	QHBoxLayout *hl;
	QLabel *label;
	QPushButton *button;
	QTabWidget *tabs;
	QWidget *tab;
	QShortcut *shortcut;
	QwtPlotGrid *grid;
	QFont boldFont;

	// Module UI
	tabs = parent->systemTabs();
	tab = new QWidget();
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	gl = new QGridLayout();
	vl->addLayout(gl);
	// PID update time
	x = 0;
	y = 13;
	label = new QLabel("PID Update Time (ms):");
	gl->addWidget(label, y, x);
	HeaterUpdateTime = new QLineEdit("1000");
	gl->addWidget(HeaterUpdateTime, y, x + 1);
	// Sensor headings
	x = 0;
	y = 0;
	label = new QLabel("Sensor A");
	boldFont = label->font();
	boldFont.setBold(true);
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 1);
	label = new QLabel("Sensor B");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 3);
	label = new QLabel("Sensor C");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 5);
	y++;
	// SensorA/SensorB/SensorC labels
	label = new QLabel("Label:");
	gl->addWidget(label, y, x);
	SensorALabel = new QLineEdit("");
	gl->addWidget(SensorALabel, y, x + 1);
	SensorBLabel = new QLineEdit("");
	gl->addWidget(SensorBLabel, y, x + 3);
	SensorCLabel = new QLineEdit("");
	gl->addWidget(SensorCLabel, y, x + 5);
	gl->setColumnMinimumWidth(x + 2, 20);
	gl->setColumnMinimumWidth(x + 4, 20);
	gl->setColumnMinimumWidth(x + 6, 20);
	gl->setColumnMinimumWidth(x + 13, 20);
	gl->setColumnStretch(x + 19, 1);
	y++;
	// SensorA/SensorB/SensorC readings
	label = new QLabel("Reading (C):");
	gl->addWidget(label, y, x);
	SensorA = new QLabel("-");
	gl->addWidget(SensorA, y, x + 1);
	SensorB = new QLabel("-");
	gl->addWidget(SensorB, y, x + 3);
	SensorC = new QLabel("-");
	gl->addWidget(SensorC, y, x + 5);
	y++;
	// Sensor types
	label = new QLabel("Type:");
	gl->addWidget(label, y, x);
	SensorAType = new QComboBox();
	SensorAType->addItem("DT-670");
	SensorAType->addItem("DT-470");
	SensorAType->addItem("RTD100");
	SensorAType->addItem("RTD400");
	SensorAType->addItem("RTD1000");
	gl->addWidget(SensorAType, y, x + 1);
	SensorBType = new QComboBox();
	SensorBType->addItem("DT-670");
	SensorBType->addItem("DT-470");
	SensorBType->addItem("RTD100");
	SensorBType->addItem("RTD400");
	SensorBType->addItem("RTD1000");
	gl->addWidget(SensorBType, y, x + 3);
	SensorCType = new QComboBox();
	SensorCType->addItem("DT-670");
	SensorCType->addItem("DT-470");
	SensorCType->addItem("RTD100");
	SensorCType->addItem("RTD400");
	SensorCType->addItem("RTD1000");
	gl->addWidget(SensorCType, y, x + 5);
	y++;
	// Sensor currents
	label = new QLabel("Current (nA):");
	gl->addWidget(label, y, x);
	SensorACurrent = new QLineEdit("10000");
	gl->addWidget(SensorACurrent, y, x + 1);
	SensorBCurrent = new QLineEdit("10000");
	gl->addWidget(SensorBCurrent, y, x + 3);
	SensorCCurrent = new QLineEdit("10000");
	gl->addWidget(SensorCCurrent, y, x + 5);
	y++;
	// Sensor limits
	label = new QLabel("Upper Limit (C):");
	gl->addWidget(label, y, x);
	SensorAUpperLimit = new QLineEdit("50.0");
	gl->addWidget(SensorAUpperLimit, y, x + 1);
	SensorBUpperLimit = new QLineEdit("50.0");
	gl->addWidget(SensorBUpperLimit, y, x + 3);
	SensorCUpperLimit = new QLineEdit("50.0");
	gl->addWidget(SensorCUpperLimit, y, x + 5);
	y++;
	label = new QLabel("Lower Limit (C):");
	gl->addWidget(label, y, x);
	SensorALowerLimit = new QLineEdit("-150.0");
	gl->addWidget(SensorALowerLimit, y, x + 1);
	SensorBLowerLimit = new QLineEdit("-150.0");
	gl->addWidget(SensorBLowerLimit, y, x + 3);
	SensorCLowerLimit = new QLineEdit("-150.0");
	gl->addWidget(SensorCLowerLimit, y, x + 5);
	y++;
	if ((build >= 1046) && (backplane_build >= 1049))
	{
		// Sensor filters
		label = new QLabel("Filter:");
		gl->addWidget(label, y, x);
		SensorAFilter = new QComboBox();
		SensorAFilter->addItem("1");
		SensorAFilter->addItem("2");
		SensorAFilter->addItem("4");
		SensorAFilter->addItem("8");
		SensorAFilter->addItem("16");
		SensorAFilter->addItem("32");
		SensorAFilter->addItem("64");
		SensorAFilter->addItem("128");
		SensorAFilter->addItem("256");
		gl->addWidget(SensorAFilter, y, x + 1);
		SensorBFilter = new QComboBox();
		SensorBFilter->addItem("1");
		SensorBFilter->addItem("2");
		SensorBFilter->addItem("4");
		SensorBFilter->addItem("8");
		SensorBFilter->addItem("16");
		SensorBFilter->addItem("32");
		SensorBFilter->addItem("64");
		SensorBFilter->addItem("128");
		SensorBFilter->addItem("256");
		gl->addWidget(SensorBFilter, y, x + 3);
		SensorCFilter = new QComboBox();
		SensorCFilter->addItem("1");
		SensorCFilter->addItem("2");
		SensorCFilter->addItem("4");
		SensorCFilter->addItem("8");
		SensorCFilter->addItem("16");
		SensorCFilter->addItem("32");
		SensorCFilter->addItem("64");
		SensorCFilter->addItem("128");
		SensorCFilter->addItem("256");
		gl->addWidget(SensorCFilter, y, x + 5);
		y++;
	}

	// Heaters
	x = 7;
	y = 0;
	label = new QLabel("Heater A");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 1);
	label = new QLabel("Heater B");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 4);
	y++;
	// Heater labels
	label = new QLabel("Label:");
	gl->addWidget(label, y, x);
	HeaterALabel = new QLineEdit("");
	gl->addWidget(HeaterALabel, y, x + 1);
	HeaterBLabel = new QLineEdit("");
	gl->addWidget(HeaterBLabel, y, x + 4);
	y++;
	// Heater enables
	label = new QLabel("Enable:");
	gl->addWidget(label, y, x);
	cbHeaterAEnable = new QCheckBox();
	gl->addWidget(cbHeaterAEnable, y, x + 1);
	cbHeaterBEnable = new QCheckBox();
	gl->addWidget(cbHeaterBEnable, y, x + 4);
	y++;
	// Heater A and B outputs
	label = new QLabel("Output (V):");
	gl->addWidget(label, y, x);
	HeaterAOutput = new QLabel("-");
	gl->addWidget(HeaterAOutput, y, x + 1);
	HeaterBOutput = new QLabel("-");
	gl->addWidget(HeaterBOutput, y, x + 4);
	y++;
	// Heater target levels
	label = new QLabel("Target (C):");
	gl->addWidget(label, y, x);
	HeaterATarget = new QLineEdit("0");
	gl->addWidget(HeaterATarget, y, x + 1);
	HeaterBTarget= new QLineEdit("0");
	gl->addWidget(HeaterBTarget, y, x + 4);
	y++;
	// PID sensor selections
	label = new QLabel("Sensor:");
	gl->addWidget(label, y, x);
	HeaterASensor = new QComboBox();
	HeaterASensor->addItem("Sensor A");
	HeaterASensor->addItem("Sensor B");
	HeaterASensor->addItem("Sensor C");
	gl->addWidget(HeaterASensor, y, x + 1);
	HeaterBSensor = new QComboBox();
	HeaterBSensor->addItem("Sensor A");
	HeaterBSensor->addItem("Sensor B");
	HeaterBSensor->addItem("Sensor C");
	gl->addWidget(HeaterBSensor, y, x + 4);
	y++;
	// Heater force mode
	label = new QLabel("Force:");
	gl->addWidget(label, y, x);
	cbHeaterAForce = new QCheckBox();
	gl->addWidget(cbHeaterAForce, y, x + 1);
	cbHeaterBForce = new QCheckBox();
	gl->addWidget(cbHeaterBForce, y, x + 4);
	y++;
	// Heater force levels
	label = new QLabel("Force Level (V):");
	gl->addWidget(label, y, x);
	HeaterAForceLevel = new QLineEdit("0");
	gl->addWidget(HeaterAForceLevel, y, x + 1);
	HeaterBForceLevel = new QLineEdit("0");
	gl->addWidget(HeaterBForceLevel, y, x + 4);
	y++;
	// Heater output limits
	label = new QLabel("Limit (V):");
	gl->addWidget(label, y, x);
	HeaterALimit = new QLineEdit("25.0");
	gl->addWidget(HeaterALimit, y, x + 1);
	HeaterBLimit = new QLineEdit("25.0");
	gl->addWidget(HeaterBLimit, y, x + 4);
	y++;
	// Heater P terms
	label = new QLabel("P:");
	gl->addWidget(label, y, x);
	HeaterAP = new QLineEdit("1");
	gl->addWidget(HeaterAP, y, x + 1);
	HeaterAPErr = new QLabel("0");
	gl->addWidget(HeaterAPErr, y, x + 2);
	HeaterBP = new QLineEdit("1");
	gl->addWidget(HeaterBP, y, x + 4);
	HeaterBPErr = new QLabel("0");
	gl->addWidget(HeaterBPErr, y, x + 5);
	y++;
	// Heater I terms
	label = new QLabel("I:");
	gl->addWidget(label, y, x);
	HeaterAI = new QLineEdit("0");
	gl->addWidget(HeaterAI, y, x + 1);
	HeaterAIErr = new QLabel("0");
	gl->addWidget(HeaterAIErr, y, x + 2);
	HeaterBI = new QLineEdit("0");
	gl->addWidget(HeaterBI, y, x + 4);
	HeaterBIErr = new QLabel("0");
	gl->addWidget(HeaterBIErr, y, x + 5);
	y++;
	// Heater D terms
	label = new QLabel("D:");
	gl->addWidget(label, y, x);
	HeaterAD = new QLineEdit("0");
	gl->addWidget(HeaterAD, y, x + 1);
	HeaterADErr = new QLabel("0");
	gl->addWidget(HeaterADErr, y, x + 2);
	HeaterBD = new QLineEdit("0");
	gl->addWidget(HeaterBD, y, x + 4);
	HeaterBDErr = new QLabel("0");
	gl->addWidget(HeaterBDErr, y, x + 5);
	y++;
	// Heater IL terms
	label = new QLabel("IL:");
	gl->addWidget(label, y, x);
	HeaterAIL = new QLineEdit("1000");
	gl->addWidget(HeaterAIL, y, x + 1);
	HeaterBIL = new QLineEdit("1000");
	gl->addWidget(HeaterBIL, y, x + 4);
	y++;
	// Heater ramp enable
	label = new QLabel("Ramp Enable:");
	gl->addWidget(label, y, x);
	cbHeaterARamp = new QCheckBox();
	gl->addWidget(cbHeaterARamp, y, x + 1);
	cbHeaterBRamp = new QCheckBox();
	gl->addWidget(cbHeaterBRamp, y, x + 4);
	y++;
	// Heater ramp rates
	label = new QLabel("Ramp Rate (mK/tick):");
	gl->addWidget(label, y, x);
	HeaterARampRate = new QLineEdit("1");
	gl->addWidget(HeaterARampRate, y, x + 1);
	HeaterBRampRate = new QLineEdit("1");
	gl->addWidget(HeaterBRampRate, y, x + 4);

	// DIO
	y = 0;
	x = 14;
	label = new QLabel("Digital I/O");
	label->setFont(boldFont);
	gl->addWidget(label, y++, x, 1, 3, Qt::AlignHCenter);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, y, x);
	label = new QLabel("Label");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 1);
	label = new QLabel("Source");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 2);
	label = new QLabel("Status");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 3);
	label = new QLabel("Direction");
	label->setFont(boldFont);
	gl->addWidget(label, y++, x + 4);
	for (i = 0; i < DIO_COUNT; i++)
	{
		// IDs and labels
		label = new QLabel(QString("DIO%1").arg(i + 1));
		gl->addWidget(label, y + i, x);
		leLabels[i] = new QLineEdit();
		gl->addWidget(leLabels[i], y + i, x + 1);
		cbSources[i] = new QComboBox();
		cbSources[i]->addItem("Low");
		cbSources[i]->addItem("High");
		cbSources[i]->addItem("Clocked");
		cbSources[i]->addItem("VCPU");
		gl->addWidget(cbSources[i], y + i, x + 2);
		lStatus[i] = new QLabel("-");
		gl->addWidget(lStatus[i], y + i, x + 3);
	}
	for (i = 0; i < DIO_COUNT / 2; i++)
	{
		cbDirections[i] = new QComboBox();
		cbDirections[i]->addItem("Input");
		cbDirections[i]->addItem("Output");
		gl->addWidget(cbDirections[i], y + i * 2, x + 4, 2, 1);
	}
	y += DIO_COUNT;
	label = new QLabel("DIO Power");
	label->setFont(boldFont);
	gl->addWidget(label, y, x, 1, 2);
	cbPower = new QComboBox();
	cbPower->addItem("Disabled");
	cbPower->addItem("Enabled");
	gl->addWidget(cbPower, y++, x + 2);

	// Mid temperature UI
	plottingEnabled = false;
	vl->addSpacing(20);
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	button = new QPushButton("Apply");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(apply()));
	hl->addWidget(button);
	button = new QPushButton("Enable Plotting");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(enablePlotting()));
	hl->addWidget(button);
	button = new QPushButton("Disable Plotting");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(disablePlotting()));
	hl->addWidget(button);
	button = new QPushButton("Save Plots");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(savePlots()));
	hl->addWidget(button);
	hl->addStretch(1);

	HPlotA = new QwtPlot();
	vl->addSpacing(20);
	vl->addWidget(HPlotA, 1);
	grid = new QwtPlotGrid;
	grid->attach(HPlotA);
	grid->setMajorPen(QPen(Qt::gray, 0, Qt::DotLine));
	HCurveA = new QwtPlotCurve();
	HCurveA->attach(HPlotA);
	HCurveA->setPen(QPen(Qt::red));
	HPlotA->setAxisTitle(QwtPlot::yLeft,"Temperature A (C)");
	HPlotA->setAxisTitle(QwtPlot::xBottom,"Time (sec)");
	HPannerA = new QwtPlotPanner(HPlotA->canvas());
	HPannerA->setMouseButton(Qt::RightButton);
	HZoomerA = new QwtPlotZoomer(HPlotA->canvas());
	HZoomerA->setMousePattern(QwtEventPattern::MouseSelect2,Qt::MiddleButton, Qt::NoModifier);

	HPlotB = new QwtPlot();
	vl->addSpacing(20);
	vl->addWidget(HPlotB, 1);
	grid = new QwtPlotGrid;
	grid->attach(HPlotB);
	grid->setMajorPen(QPen(Qt::gray, 0, Qt::DotLine));
	HCurveB = new QwtPlotCurve();
	HCurveB->attach(HPlotB);
	HCurveB->setPen(QPen(Qt::blue));
	HPlotB->setAxisTitle(QwtPlot::yLeft,"Temperature B (C)");
	HPlotB->setAxisTitle(QwtPlot::xBottom,"Time (sec)");
	HPannerB = new QwtPlotPanner(HPlotB->canvas());
	HPannerB->setMouseButton(Qt::RightButton);
	HZoomerB = new QwtPlotZoomer(HPlotB->canvas());
	HZoomerB->setMousePattern(QwtEventPattern::MouseSelect2,Qt::MiddleButton, Qt::NoModifier);

	HPlotC = new QwtPlot();
	vl->addSpacing(20);
	vl->addWidget(HPlotC, 1);
	grid = new QwtPlotGrid;
	grid->attach(HPlotC);
	grid->setMajorPen(QPen(Qt::gray, 0, Qt::DotLine));
	HCurveC = new QwtPlotCurve();
	HCurveC->attach(HPlotC);
	HCurveC->setPen(QPen(Qt::blue));
	HPlotC->setAxisTitle(QwtPlot::yLeft,"Temperature C (C)");
	HPlotC->setAxisTitle(QwtPlot::xBottom,"Time (sec)");
	HPannerC = new QwtPlotPanner(HPlotC->canvas());
	HPannerC->setMouseButton(Qt::RightButton);
	HZoomerC = new QwtPlotZoomer(HPlotC->canvas());
	HZoomerC->setMousePattern(QwtEventPattern::MouseSelect2,Qt::MiddleButton, Qt::NoModifier);

	QScrollArea *scroll = new QScrollArea();
	scroll->setWidget(tab);
	tabs->addTab(scroll, QString("Slot %1: HEATERX").arg(slot));

	// Timing UI
	tabs = parent->waveformTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: HEATERX").arg(slot));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_C), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(copyClocks()));
	shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_V), tab);
	QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(pasteClocks()));
	gl = new QGridLayout();
	tab->setLayout(gl);
	gl->setSpacing(10);
	label = new QLabel("Label");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 0);
	label = new QLabel("State");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 1);
	label = new QLabel("Keep");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 2);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 3);
	for (i = 0; i < DIO_COUNT; i++)
	{
		lRefLabels[i] = new QLabel();
		connect(leLabels[i], SIGNAL(textChanged(QString)), lRefLabels[i], SLOT(setText(QString)));
		cbStates[i] = new QCheckBox();
		cbKeeps[i] = new QCheckBox();
		connect(cbStates[i], SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		connect(cbKeeps[i], SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		label = new QLabel();
		label->setText(QString("DIO%1").arg(i + 1));
		gl->addWidget(lRefLabels[i], i + 1, 0);
		gl->addWidget(cbStates[i], i + 1, 1, Qt::AlignHCenter);
		gl->addWidget(cbKeeps[i], i + 1, 2, Qt::AlignHCenter);
		gl->addWidget(label, i + 1, 3);
	}
	gl->setVerticalSpacing(4);
	gl->setColumnStretch(4, 1);
	gl->setRowStretch(DIO_COUNT + 1, 1);

	// VCPU UI
	tabs = parent->vcpuTabs();
	tab = new QWidget();
	tabs->addTab(tab, QString("Slot %1: HEATERX").arg(slot));
	gl = new QGridLayout();
	tab->setLayout(gl);
	gl->setSpacing(10);
	teVCPU = new QPlainTextEdit();
	teVCPU->setLineWrapMode(QPlainTextEdit::NoWrap);
	label = new QLabel("Code");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 0);
	gl->addWidget(teVCPU, 1, 0, VCPU_COUNT + 1, 1);
	label = new QLabel("Register");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 1);
	label = new QLabel("Input");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 2);
	label = new QLabel("Output");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 3);
	for (i = 0; i < VCPU_COUNT; i++)
	{
		label = new QLabel(QString("REG%1").arg(i));
		gl->addWidget(label, i + 1, 1);
		leVCPUInReg[i] = new QLineEdit("0");
		gl->addWidget(leVCPUInReg[i], i + 1, 2);
		lVCPUOutReg[i] = new QLabel("-");
		gl->addWidget(lVCPUOutReg[i], i + 1, 3);
	}
	gl->setColumnStretch(0, 1);
	gl->setRowStretch(VCPU_COUNT + 1, 1);
	gl->setColumnMinimumWidth(3, 100);
	hl = new QHBoxLayout();
	button = new QPushButton("Apply");
	connect(button, SIGNAL(clicked()), this, SLOT(applyDIO()));
	hl->addWidget(button);
	hl->addStretch(0);
	gl->addLayout(hl, VCPU_COUNT + 2, 0);

	// Sync UI with current settings
	updateUI();
}
//---------------------------------------------------------------------------
void HEATERX::parseUI()
{
	int i, count;
	QStringList sl;

	// Heater control
	parent->config.insert(key + "/HEATERALABEL", HeaterALabel->text());
	parent->config.insert(key + "/HEATERBLABEL", HeaterBLabel->text());
	parent->config.insert(key + "/HEATERAENABLE", cbHeaterAEnable->isChecked() ? "1" : "0");
	parent->config.insert(key + "/HEATERBENABLE", cbHeaterBEnable->isChecked() ? "1" : "0");
	parent->config.insert(key + "/HEATERAFORCE", cbHeaterAForce->isChecked() ? "1" : "0");
	parent->config.insert(key + "/HEATERBFORCE", cbHeaterBForce->isChecked() ? "1" : "0");
	parent->config.insert(key + "/HEATERAFORCELEVEL", HeaterAForceLevel->text());
	parent->config.insert(key + "/HEATERBFORCELEVEL", HeaterBForceLevel->text());
	parent->config.insert(key + "/HEATERASENSOR", QString::number(HeaterASensor->currentIndex()));
	parent->config.insert(key + "/HEATERBSENSOR", QString::number(HeaterBSensor->currentIndex()));
	parent->config.insert(key + "/HEATERATARGET", HeaterATarget->text());
	parent->config.insert(key + "/HEATERBTARGET", HeaterBTarget->text());
	parent->config.insert(key + "/HEATERAP", HeaterAP->text());
	parent->config.insert(key + "/HEATERBP", HeaterBP->text());
	parent->config.insert(key + "/HEATERAI", HeaterAI->text());
	parent->config.insert(key + "/HEATERBI", HeaterBI->text());
	parent->config.insert(key + "/HEATERAD", HeaterAD->text());
	parent->config.insert(key + "/HEATERBD", HeaterBD->text());
	parent->config.insert(key + "/HEATERAIL", HeaterAIL->text());
	parent->config.insert(key + "/HEATERBIL", HeaterBIL->text());
	parent->config.insert(key + "/HEATERUPDATETIME", HeaterUpdateTime->text());
	parent->config.insert(key + "/HEATERARAMP", cbHeaterARamp->isChecked() ? "1" : "0");
	parent->config.insert(key + "/HEATERBRAMP", cbHeaterBRamp->isChecked() ? "1" : "0");
	parent->config.insert(key + "/HEATERARAMPRATE", HeaterARampRate->text());
	parent->config.insert(key + "/HEATERBRAMPRATE", HeaterBRampRate->text());
	parent->config.insert(key + "/HEATERALIMIT", HeaterALimit->text());
	parent->config.insert(key + "/HEATERBLIMIT", HeaterBLimit->text());
	parent->config.insert(key + "/SENSORALABEL", SensorALabel->text());
	parent->config.insert(key + "/SENSORBLABEL", SensorBLabel->text());
	parent->config.insert(key + "/SENSORCLABEL", SensorCLabel->text());
	parent->config.insert(key + "/SENSORATYPE", QString::number(SensorAType->currentIndex()));
	parent->config.insert(key + "/SENSORBTYPE", QString::number(SensorBType->currentIndex()));
	parent->config.insert(key + "/SENSORCTYPE", QString::number(SensorCType->currentIndex()));
	parent->config.insert(key + "/SENSORACURRENT", SensorACurrent->text());
	parent->config.insert(key + "/SENSORBCURRENT", SensorBCurrent->text());
	parent->config.insert(key + "/SENSORCCURRENT", SensorCCurrent->text());
	parent->config.insert(key + "/SENSORAUPPERLIMIT", SensorAUpperLimit->text());
	parent->config.insert(key + "/SENSORBUPPERLIMIT", SensorBUpperLimit->text());
	parent->config.insert(key + "/SENSORCUPPERLIMIT", SensorCUpperLimit->text());
	parent->config.insert(key + "/SENSORALOWERLIMIT", SensorALowerLimit->text());
	parent->config.insert(key + "/SENSORBLOWERLIMIT", SensorBLowerLimit->text());
	parent->config.insert(key + "/SENSORCLOWERLIMIT", SensorCLowerLimit->text());
	if ((build >= 1046) && (backplane_build >= 1049))
	{
		parent->config.insert(key + "/SENSORAFILTER", QString::number(SensorAFilter->currentIndex()));
		parent->config.insert(key + "/SENSORBFILTER", QString::number(SensorBFilter->currentIndex()));
		parent->config.insert(key + "/SENSORCFILTER", QString::number(SensorCFilter->currentIndex()));
	}
	for (i = 0; i < DIO_COUNT; i++)
	{
		parent->config.insert(key + QString("/DIO_LABEL%1").arg(i + 1), leLabels[i]->text());
		parent->config.insert(key + QString("/DIO_SOURCE%1").arg(i + 1), QString::number(cbSources[i]->currentIndex()));
	}
	for (i = 0; i < DIO_COUNT / 2; i++)
	{
		parent->config.insert(key + QString("/DIO_DIR%1%2").arg(i * 2 + 1).arg(i * 2 + 2), QString::number(cbDirections[i]->currentIndex()));
	}
	parent->config.insert(key + "/DIO_POWER", QString::number(cbPower->currentIndex()));
	// VCPU code
	sl = teVCPU->toPlainText().split('\n');
	count = sl.count();
	parent->config.insert(key + "/VCPU_LINES", QString::number(count));
	for (i = 0; i < count; i++)
		parent->config.insert(key + QString("/VCPU_LINE%1").arg(i), sl[i]);
	for (i = 0; i < VCPU_COUNT; i++)
		parent->config.insert(key + QString("/VCPU_INREG%1").arg(i), leVCPUInReg[i]->text());
}
//---------------------------------------------------------------------------
void HEATERX::updateUI()
{
	int i, count;
	bool ok;

	HeaterALabel->setText(parent->config.value(key + "/HEATERALABEL", ""));
	HeaterBLabel->setText(parent->config.value(key + "/HEATERBLABEL", ""));
	cbHeaterAEnable->setChecked(parent->config.value(key + "/HEATERAENABLE") == "1");
	cbHeaterBEnable->setChecked(parent->config.value(key + "/HEATERBENABLE") == "1");
	cbHeaterAForce->setChecked(parent->config.value(key + "/HEATERAFORCE") == "1");
	cbHeaterBForce->setChecked(parent->config.value(key + "/HEATERBFORCE") == "1");
	HeaterAForceLevel->setText(parent->config.value(key + "/HEATERAFORCELEVEL", "0"));
	HeaterBForceLevel->setText(parent->config.value(key + "/HEATERBFORCELEVEL", "0"));
	HeaterASensor->setCurrentIndex(qBound(0, parent->config.value(key + "/HEATERASENSOR").toInt(), 2));
	HeaterBSensor->setCurrentIndex(qBound(0, parent->config.value(key + "/HEATERBSENSOR").toInt(), 2));
	HeaterATarget->setText(parent->config.value(key + "/HEATERATARGET", "0"));
	HeaterBTarget->setText(parent->config.value(key + "/HEATERBTARGET", "0"));
	HeaterAP->setText(parent->config.value(key + "/HEATERAP", "0"));
	HeaterBP->setText(parent->config.value(key + "/HEATERBP", "0"));
	HeaterAI->setText(parent->config.value(key + "/HEATERAI", "0"));
	HeaterBI->setText(parent->config.value(key + "/HEATERBI", "0"));
	HeaterAD->setText(parent->config.value(key + "/HEATERAD", "0"));
	HeaterBD->setText(parent->config.value(key + "/HEATERBD", "0"));
	HeaterAIL->setText(parent->config.value(key + "/HEATERAIL", "1000"));
	HeaterBIL->setText(parent->config.value(key + "/HEATERBIL", "1000"));
	HeaterUpdateTime->setText(parent->config.value(key + "/HEATERUPDATETIME", "1000"));
	cbHeaterARamp->setChecked(parent->config.value(key + "/HEATERARAMP") == "1");
	cbHeaterBRamp->setChecked(parent->config.value(key + "/HEATERBRAMP") == "1");
	HeaterARampRate->setText(parent->config.value(key + "/HEATERARAMPRATE", "1"));
	HeaterBRampRate->setText(parent->config.value(key + "/HEATERBRAMPRATE", "1"));
	HeaterALimit->setText(parent->config.value(key + "/HEATERALIMIT", "25.0"));
	HeaterBLimit->setText(parent->config.value(key + "/HEATERBLIMIT", "25.0"));
	SensorALabel->setText(parent->config.value(key + "/SENSORALABEL", ""));
	SensorBLabel->setText(parent->config.value(key + "/SENSORBLABEL", ""));
	SensorCLabel->setText(parent->config.value(key + "/SENSORCLABEL", ""));
	SensorAType->setCurrentIndex(qBound(0, parent->config.value(key + "/SENSORATYPE").toInt(), SensorAType->count() - 1));
	SensorBType->setCurrentIndex(qBound(0, parent->config.value(key + "/SENSORBTYPE").toInt(), SensorBType->count() - 1));
	SensorCType->setCurrentIndex(qBound(0, parent->config.value(key + "/SENSORCTYPE").toInt(), SensorCType->count() - 1));
	SensorACurrent->setText(parent->config.value(key + "/SENSORACURRENT", "10000"));
	SensorBCurrent->setText(parent->config.value(key + "/SENSORBCURRENT", "10000"));
	SensorCCurrent->setText(parent->config.value(key + "/SENSORCCURRENT", "10000"));
	SensorAUpperLimit->setText(parent->config.value(key + "/SENSORAUPPERLIMIT", "50.0"));
	SensorBUpperLimit->setText(parent->config.value(key + "/SENSORBUPPERLIMIT", "50.0"));
	SensorCUpperLimit->setText(parent->config.value(key + "/SENSORCUPPERLIMIT", "50.0"));
	SensorALowerLimit->setText(parent->config.value(key + "/SENSORALOWERLIMIT", "-150.0"));
	SensorBLowerLimit->setText(parent->config.value(key + "/SENSORBLOWERLIMIT", "-150.0"));
	SensorCLowerLimit->setText(parent->config.value(key + "/SENSORCLOWERLIMIT", "-150.0"));
	if ((build >= 1046) && (backplane_build >= 1049))
	{
		SensorAFilter->setCurrentIndex(qBound(0, parent->config.value(key + "/SENSORAFILTER").toInt(), SensorAFilter->count() - 1));
		SensorBFilter->setCurrentIndex(qBound(0, parent->config.value(key + "/SENSORBFILTER").toInt(), SensorBFilter->count() - 1));
		SensorCFilter->setCurrentIndex(qBound(0, parent->config.value(key + "/SENSORCFILTER").toInt(), SensorCFilter->count() - 1));
	}
	for (i = 0; i < DIO_COUNT; i++)
	{
		leLabels[i]->setText(parent->config.value(key + QString("/DIO_LABEL%1").arg(i + 1)));
		cbSources[i]->setCurrentIndex(qBound(0, parent->config.value(key + QString("/DIO_SOURCE%1").arg(i + 1)).toInt(), 3));
	}
	for (i = 0; i < DIO_COUNT / 2; i++)
	{
		cbDirections[i]->setCurrentIndex(qBound(0, parent->config.value(key + QString("/DIO_DIR%1%2").arg(i * 2 + 1).arg(i * 2 + 2)).toInt(), 1));
	}
	cbPower->setCurrentIndex(qBound(0, parent->config.value(key + "/DIO_POWER").toInt(), 1));
	// VCPU code
	count = parent->config.value(key + "/VCPU_LINES").toInt(&ok);
	if (ok)
	{
		teVCPU->clear();
		for (i = 0; i < count; i++)
			teVCPU->appendPlainText(parent->config.value(key + QString("/VCPU_LINE%1").arg(i)));
	}
	for (i = 0; i < VCPU_COUNT; i++)
		leVCPUInReg[i]->setText(parent->config.value(key + QString("/VCPU_INREG%1").arg(i + 1), "0"));
}
//---------------------------------------------------------------------------
void HEATERX::apply()
{
	parent->applyModule(slot);
}
//---------------------------------------------------------------------------
void HEATERX::applyDIO()
{
	parent->applyModuleDIO(slot);
}
//---------------------------------------------------------------------------
void HEATERX::enablePlotting()
{
	plottingEnabled = true;
	htime.clear();
	htempa.clear();
	htempb.clear();
	htempc.clear();
	pollt = QDateTime::currentDateTime();
}
//---------------------------------------------------------------------------
void HEATERX::disablePlotting()
{
	plottingEnabled = false;
}
//---------------------------------------------------------------------------
void HEATERX::savePlots()
{
	FILE *fout = fopen("heaterplots.txt","w");
	fprintf(fout,"Time (s)\tTemp A (C)\tTemp B (C)\tTemp C (C)\n");
	for (int i = 0; i < htime.count(); i++)
		fprintf(fout,"%0.6lf\t%0.6lf\t%0.6lf\t%0.6lf\n", htime[i], htempa[i], htempb[i], htempc[i]);
	fclose(fout);
}
//---------------------------------------------------------------------------
void HEATERX::setClocks(const QVariantMap& map)
{
	int i;
	QStringList sl = map.value(key).toString().split(",");

	for (i = 0; i < DIO_COUNT; i++)
	{
		cbStates[i]->setChecked(sl.value(i * 2, "1") == "1");
		cbKeeps[i]->setChecked(sl.value(i * 2 + 1, "1") == "1");
		cbStates[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
}
//---------------------------------------------------------------------------
void HEATERX::getClocks(QVariantMap& map)
{
	int i;
	QStringList sl;

	for (i = 0; i < DIO_COUNT; i++)
	{
		sl.append(cbStates[i]->isChecked() ? "1" : "0");
		sl.append(cbKeeps[i]->isChecked() ? "1" : "0");
	}
	map.insert(key, sl.join(","));
}
//---------------------------------------------------------------------------
void HEATERX::clockChanged()
{
	int i;

	for (i = 0; i < DIO_COUNT; i++)
	{
		cbStates[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
	parent->clockChanged();
}
//---------------------------------------------------------------------------
void HEATERX::copyClocks()
{
	int i;
	QStringList sl;
	QString s;

	for (i = 0; i < DIO_COUNT; i++)
	{
		sl.append(cbStates[i]->isChecked() ? "1" : "0");
		sl.append(cbKeeps[i]->isChecked() ? "1" : "0");
	}
	s = sl.join(",");
	QApplication::clipboard()->setText(s);
}
//---------------------------------------------------------------------------
void HEATERX::pasteClocks()
{
	int i;
	QStringList sl;

	sl = QApplication::clipboard()->text().split(",");
	for (i = 0; i < DIO_COUNT; i++)
	{
		cbStates[i]->setChecked(sl.value(i * 2, "1") == "1");
		cbKeeps[i]->setChecked(sl.value(i * 2 + 1, "1") == "1");
		cbStates[i]->setEnabled(!cbKeeps[i]->isChecked());
	}
}
//---------------------------------------------------------------------------
void HEATERX::parseStatus(const RMap &data)
{
	int i;
	double d;
	double t;
	bool ok;
	double minval, maxval, ta, tb, tc;
	QString s;

	ta = data.value(key + "/TEMPA", "-").toDouble(&ok);
	if (ok)
		SensorA->setText(flt(ta, 0, 6));
	tb = data.value(key + "/TEMPB", "-").toDouble(&ok);
	if (ok)
		SensorB->setText(flt(tb, 0, 6));
	tc = data.value(key + "/TEMPC", "-").toDouble(&ok);
	if (ok)
		SensorC->setText(flt(tc, 0, 6));
	d = data.value(key + "/HEATERAOUTPUT", "-").toDouble(&ok);
	if (ok)
		HeaterAOutput->setText(flt(d, 0, 3));
	d = data.value(key + "/HEATERBOUTPUT", "-").toDouble(&ok);
	if (ok)
		HeaterBOutput->setText(flt(d, 0, 3));
	HeaterAPErr->setText(data.value(key + "/HEATERAP", "0"));
	HeaterAIErr->setText(data.value(key + "/HEATERAI", "0"));
	HeaterADErr->setText(data.value(key + "/HEATERAD", "0"));
	HeaterBPErr->setText(data.value(key + "/HEATERBP", "0"));
	HeaterBIErr->setText(data.value(key + "/HEATERBI", "0"));
	HeaterBDErr->setText(data.value(key + "/HEATERBD", "0"));
	if (plottingEnabled)
	{
		t = double(pollt.msecsTo(QDateTime::currentDateTime())) / 1000.0;
		if (htime.count() == 10000)
		{
			htime.remove(0);
			htempa.remove(0);
			htempb.remove(0);
			htempc.remove(0);
		}
		htime.append(t);
		htempa.append(ta);
		htempb.append(tb);
		htempc.append(tc);
		HCurveA->setSamples(htime, htempa);
		HPlotA->replot();
		HCurveB->setSamples(htime, htempb);
		HPlotB->replot();
		HCurveC->setSamples(htime, htempc);
		HPlotC->replot();
		HPlotA->setAxisScale(QwtPlot::xBottom, htime[0], t);
		minval = htempa[0];
		maxval = htempa[0];
		for (i = 0; i < htempa.count(); i++)
		{
			 minval = qMin(minval, htempa[i]);
			 maxval = qMax(maxval, htempa[i]);
		}
		HPlotA->setAxisScale(QwtPlot::yLeft, minval, maxval);
		HZoomerA->setZoomBase();
		HPlotB->setAxisScale(QwtPlot::xBottom, htime[0], t);
		minval = htempb[0];
		maxval = htempb[0];
		for (i = 0; i < htempb.count(); i++)
		{
		  minval = qMin(minval, htempb[i]);
		  maxval = qMax(maxval, htempb[i]);
		}
		HPlotB->setAxisScale(QwtPlot::yLeft, minval, maxval);
		HZoomerB->setZoomBase();
		HPlotC->setAxisScale(QwtPlot::xBottom, htime[0], t);
		minval = htempc[0];
		maxval = htempc[0];
		for (i = 0; i < htempc.count(); i++)
		{
			 minval = qMin(minval, htempc[i]);
			 maxval = qMax(maxval, htempc[i]);
		}
		HPlotC->setAxisScale(QwtPlot::yLeft, minval, maxval);
		HZoomerC->setZoomBase();
	}

	// DIO
	s = data.value(key + "/DINPUTS", "--------");
	if (s.length() != DIO_COUNT)
		s = "--------";
	for (i = 0; i < DIO_COUNT; i++)
		lStatus[i]->setText(s.mid(i, 1));
	// VCPU registers
	for (i = 0; i < VCPU_COUNT; i++)
	{
		s = data.value(key + QString("/VCPU_OUTREG%1").arg(i), "-");
		lVCPUOutReg[i]->setText(s);
	}
}
/////////////////////////////////////////////////////////////////////////////////
// XVBias Module
XVBIAS::XVBIAS(TArchonGUI *parent, QString key, int slot) : TModule(parent, key, slot)
{
	build = parent->system.value(QString("MOD%1_VERSION").arg(slot)).split(".").value(2).toInt();
}
//---------------------------------------------------------------------------
void XVBIAS::createUI()
{
	int i, x, y;
	QVBoxLayout *vl;
	QGridLayout *gl;
	QHBoxLayout *hl;
	QLabel *label;
	QPushButton *button;
	QTabWidget *tabs;
	QWidget *tab;
	QShortcut *shortcut;
	QFont boldFont, fixedFont;
	QString s;

	// Module UI
	tabs = parent->systemTabs();
	tab = new QWidget();
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	gl = new QGridLayout();
	vl->addLayout(gl);
	gl->setHorizontalSpacing(10);
	gl->setVerticalSpacing(4);

	// Positive biases
	x = 0;
	y = 0;
	label = new QLabel("Command");
	boldFont = label->font();
	boldFont.setBold(true);
	fixedFont = label->font();
	fixedFont.setFamily("Monotype");
	fixedFont.setStyleHint(QFont::TypeWriter);
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 2, Qt::AlignHCenter);
	label = new QLabel("Measured");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 3, 1, 2, Qt::AlignHCenter);
	y++;
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, y, x);
	label = new QLabel("Label");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 1);
	label = new QLabel("V (0..95)");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 2);
	label = new QLabel("V");
	label->setAlignment(Qt::AlignHCenter);
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 3);
	label = new QLabel("mA");
	label->setAlignment(Qt::AlignHCenter);
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 4);
	label = new QLabel("Order");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 5);
	label = new QLabel("Enable");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 6);
	y++;
	for (i = 0; i < XV_COUNT; i++)
	{
		// IDs and labels
		label = new QLabel(QString("PV%1").arg(i + 1));
		gl->addWidget(label, y, x);
		xvp_label[i] = new QLineEdit();
		gl->addWidget(xvp_label[i], y, x + 1);
		// Commanded voltage
		xvp_v_cmd[i] = new QLineEdit("0.0");
		gl->addWidget(xvp_v_cmd[i], y, x + 2);
		// Voltage and current readings
		xvp_v[i] = new QLabel("-");
		xvp_v[i]->setFont(fixedFont);
		gl->addWidget(xvp_v[i], y, x + 3);
		xvp_i[i] = new QLabel("-");
		xvp_i[i]->setFont(fixedFont);
		gl->addWidget(xvp_i[i], y, x + 4);
		// Power on order
		xvp_order[i] = new QLineEdit("0");
		gl->addWidget(xvp_order[i], y, x + 5);
		// Channel enable
		xvp_enable[i] = new QCheckBox();
		gl->addWidget(xvp_enable[i], y, x + 6, Qt::AlignHCenter);
		y++;
	}
	gl->setRowMinimumHeight(y, 20);
	y++;

	// Negative biases
	label = new QLabel("Command");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 2, Qt::AlignHCenter);
	label = new QLabel("Measured");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 3, 1, 2, Qt::AlignHCenter);
	y++;
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, y, x);
	label = new QLabel("Label");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 1);
	label = new QLabel("V (-95..0)");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 2);
	label = new QLabel("V");
	label->setAlignment(Qt::AlignHCenter);
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 3);
	label = new QLabel("mA");
	label->setAlignment(Qt::AlignHCenter);
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 4);
	label = new QLabel("Order");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 5);
	label = new QLabel("Enable");
	label->setFont(boldFont);
	gl->addWidget(label, y, x + 6);
	y++;
	for (i = 0; i < XV_COUNT; i++)
	{
		// IDs and labels
		label = new QLabel(QString("NV%1").arg(i + 1));
		gl->addWidget(label, y, x);
		xvn_label[i] = new QLineEdit();
		gl->addWidget(xvn_label[i], y, x + 1);
		// Commanded voltage
		xvn_v_cmd[i] = new QLineEdit("0.0");
		gl->addWidget(xvn_v_cmd[i], y, x + 2);
		// Voltage and current readings
		xvn_v[i] = new QLabel("-");
		xvn_v[i]->setFont(fixedFont);
		gl->addWidget(xvn_v[i], y, x + 3);
		xvn_i[i] = new QLabel("-");
		xvn_i[i]->setFont(fixedFont);
		gl->addWidget(xvn_i[i], y, x + 4);
		// Power on order
		xvn_order[i] = new QLineEdit("0");
		gl->addWidget(xvn_order[i], y, x + 5);
		// Channel enable
		xvn_enable[i] = new QCheckBox();
		gl->addWidget(xvn_enable[i], y, x + 6, Qt::AlignHCenter);
		y++;
	}

	gl->setColumnStretch(7, 1);
	vl->addStretch(1);
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	button = new QPushButton("Apply");
	connect(button, SIGNAL(clicked()), this, SLOT(apply()));
	hl->addWidget(button);
	hl->addStretch(1);
	QScrollArea *scroll = new QScrollArea();
	scroll->setWidget(tab);
	s = QString("Slot %1: XVBIAS").arg(slot);
	tabs->addTab(scroll, s);

	if (build >= 1090)
	{
		// Timing UI
		tabs = parent->waveformTabs();
		tab = new QWidget();
		tabs->addTab(tab, s);
		shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_C), tab);
		QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(copyClocks()));
		shortcut = new QShortcut(QKeySequence(Qt::CTRL | Qt::Key_V), tab);
		QObject::connect(shortcut, SIGNAL(activated()), this, SLOT(pasteClocks()));
		gl = new QGridLayout();
		tab->setLayout(gl);
		gl->setSpacing(10);
		label = new QLabel("P Command");
		label->setFont(boldFont);
		gl->addWidget(label, 0, 0);
		label = new QLabel("P Channel (1-4)");
		label->setFont(boldFont);
		gl->addWidget(label, 0, 1);
		label = new QLabel("P Voltage (V)");
		label->setFont(boldFont);
		gl->addWidget(label, 0, 2);
		cbPBiasCmd = new QCheckBox();
		connect(cbPBiasCmd, SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		lePBiasChannel = new QLineEdit("1");
		connect(lePBiasChannel, SIGNAL(textChanged(QString)), this, SLOT(clockChanged()));
		lePBiasVoltage = new QLineEdit("0.0");
		connect(lePBiasVoltage, SIGNAL(textChanged(QString)), this, SLOT(clockChanged()));
		gl->addWidget(cbPBiasCmd, 1, 0, Qt::AlignHCenter);
		gl->addWidget(lePBiasChannel, 1, 1);
		gl->addWidget(lePBiasVoltage, 1, 2);
		label = new QLabel("N Command");
		label->setFont(boldFont);
		gl->addWidget(label, 2, 0);
		label = new QLabel("N Channel (1-4)");
		label->setFont(boldFont);
		gl->addWidget(label, 2, 1);
		label = new QLabel("N Voltage (V)");
		label->setFont(boldFont);
		gl->addWidget(label, 2, 2);
		cbNBiasCmd = new QCheckBox();
		connect(cbNBiasCmd, SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		leNBiasChannel = new QLineEdit("1");
		connect(leNBiasChannel, SIGNAL(textChanged(QString)), this, SLOT(clockChanged()));
		leNBiasVoltage = new QLineEdit("0.0");
		connect(leNBiasVoltage, SIGNAL(textChanged(QString)), this, SLOT(clockChanged()));
		gl->addWidget(cbNBiasCmd, 3, 0, Qt::AlignHCenter);
		gl->addWidget(leNBiasChannel, 3, 1);
		gl->addWidget(leNBiasVoltage, 3, 2);
		gl->setVerticalSpacing(4);
		gl->setColumnStretch(3, 1);
		gl->setRowStretch(4, 1);
	}

	// Sync UI with current settings
	updateUI();
}
//---------------------------------------------------------------------------
void XVBIAS::parseUI()
{
	int i;

	for (i = 0; i < XV_COUNT; i++)
	{
		parent->config.insert(key + QString("/XVP_LABEL%1").arg(i + 1), xvp_label[i]->text());
		parent->config.insert(key + QString("/XVP_V%1").arg(i + 1), xvp_v_cmd[i]->text());
		parent->config.insert(key + QString("/XVP_ORDER%1").arg(i + 1), xvp_order[i]->text());
		parent->config.insert(key + QString("/XVP_ENABLE%1").arg(i + 1), xvp_enable[i]->isChecked() ? "1" : "0");
		parent->config.insert(key + QString("/XVN_LABEL%1").arg(i + 1), xvn_label[i]->text());
		parent->config.insert(key + QString("/XVN_V%1").arg(i + 1), xvn_v_cmd[i]->text());
		parent->config.insert(key + QString("/XVN_ORDER%1").arg(i + 1), xvn_order[i]->text());
		parent->config.insert(key + QString("/XVN_ENABLE%1").arg(i + 1), xvn_enable[i]->isChecked() ? "1" : "0");
	}
}
//---------------------------------------------------------------------------
void XVBIAS::updateUI()
{
	int i;

	for (i = 0; i < XV_COUNT; i++)
	{
		xvp_label[i]->setText(parent->config.value(key + QString("/XVP_LABEL%1").arg(i + 1)));
		xvp_v_cmd[i]->setText(parent->config.value(key + QString("/XVP_V%1").arg(i + 1), "0.0"));
		xvp_order[i]->setText(parent->config.value(key + QString("/XVP_ORDER%1").arg(i + 1), "0"));
		xvp_enable[i]->setChecked(parent->config.value(key + QString("/XVP_ENABLE%1").arg(i + 1)) == "1");
		xvn_label[i]->setText(parent->config.value(key + QString("/XVN_LABEL%1").arg(i + 1)));
		xvn_v_cmd[i]->setText(parent->config.value(key + QString("/XVN_V%1").arg(i + 1), "0.0"));
		xvn_order[i]->setText(parent->config.value(key + QString("/XVN_ORDER%1").arg(i + 1), "0"));
		xvn_enable[i]->setChecked(parent->config.value(key + QString("/XVN_ENABLE%1").arg(i + 1)) == "1");
	}
}
//---------------------------------------------------------------------------
void XVBIAS::apply()
{
	parent->applyModule(slot);
}
//---------------------------------------------------------------------------
void XVBIAS::setClocks(const QVariantMap& map)
{
	if (build < 1090)
		return;
	QStringList sl = map.value(key).toString().split(",");
	cbPBiasCmd->setChecked(sl.value(0, "0") == "1");
	lePBiasChannel->setText(sl.value(1, "1"));
	lePBiasVoltage->setText(sl.value(2, "0.0"));
	cbNBiasCmd->setChecked(sl.value(3, "0") == "1");
	leNBiasChannel->setText(sl.value(4, "1"));
	leNBiasVoltage->setText(sl.value(5, "0.0"));
}
//---------------------------------------------------------------------------
void XVBIAS::getClocks(QVariantMap& map)
{
	if (build < 1090)
		return;
	QStringList sl;
	sl.append(cbPBiasCmd->isChecked() ? "1" : "0");
	sl.append(lePBiasChannel->text());
	sl.append(lePBiasVoltage->text());
	sl.append(cbNBiasCmd->isChecked() ? "1" : "0");
	sl.append(leNBiasChannel->text());
	sl.append(leNBiasVoltage->text());
	map.insert(key, sl.join(","));
}
//---------------------------------------------------------------------------
void XVBIAS::clockChanged()
{
	parent->clockChanged();
}
//---------------------------------------------------------------------------
void XVBIAS::copyClocks()
{
	if (build < 1090)
		return;
	QStringList sl;
	QString s;
	sl.append(cbPBiasCmd->isChecked() ? "1" : "0");
	sl.append(lePBiasChannel->text());
	sl.append(lePBiasVoltage->text());
	sl.append(cbNBiasCmd->isChecked() ? "1" : "0");
	sl.append(leNBiasChannel->text());
	sl.append(leNBiasVoltage->text());
	s = sl.join(",");
	QApplication::clipboard()->setText(s);
}
//---------------------------------------------------------------------------
void XVBIAS::pasteClocks()
{
	if (build < 1090)
		return;
	QStringList sl;

	sl = QApplication::clipboard()->text().split(",");
	cbPBiasCmd->setChecked(sl.value(0, "0") == "1");
	lePBiasChannel->setText(sl.value(1, "1"));
	lePBiasVoltage->setText(sl.value(2, "0.0"));
	cbNBiasCmd->setChecked(sl.value(0, "0") == "1");
	leNBiasChannel->setText(sl.value(1, "1"));
	leNBiasVoltage->setText(sl.value(2, "0.0"));
}
//---------------------------------------------------------------------------
void XVBIAS::parseStatus(const RMap &data)
{
	int i;

	for (i = 0; i < XV_COUNT; i++)
	{
		xvp_v[i]->setText(data.value(key + QString("/XVP_V%1").arg(i + 1), "-").rightJustified(8));
		xvp_i[i]->setText(data.value(key + QString("/XVP_I%1").arg(i + 1), "-").rightJustified(8));
		xvn_v[i]->setText(data.value(key + QString("/XVN_V%1").arg(i + 1), "-").rightJustified(8));
		xvn_i[i]->setText(data.value(key + QString("/XVN_I%1").arg(i + 1), "-").rightJustified(8));
	}
}
