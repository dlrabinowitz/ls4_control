#include "archongui.h"
#include <QFileDialog>
#include <QSettings>
#include <QMessageBox>
#include <QApplication>
#include <QGridLayout>
#include <QSplitter>
#include <QSignalMapper>
#include <QInputDialog>
#include <QGroupBox>
#include <QCollator>
#include <math.h>
#include <qwt_plot_grid.h>
#include <QtEndian>
#include <QActionGroup>
#if (QT_VERSION >= 0x051400)
	 #define QT_ENDL Qt::endl
#else
	 #define QT_ENDL endl
#endif

TArchonGUI::TArchonGUI(QString loadFilename, QWidget *parent) : QMainWindow(parent)
{
	int i, x, y;
	QLabel *label;
	QHBoxLayout *hl, *tophl;
	QVBoxLayout *vl, *vl2, *tabvl;
	QGridLayout *gl, *gl2;
	QWidget *tab;
	QWidget *qw;
	QSplitter *splitter;
	QSignalMapper *signalMapper;
	QFont boldFont, fixedFont;
	QwtPlotGrid *grid;
	QwtSymbol *symbol;
	QGroupBox *gb;

	sPROMFilename = "D:/Archon/RevC/ArchonBackplaneX12RevH/FPGA/archonbackplanerevh.mcs";
	QPushButton *button;
	archon = new Archon();

	cmdinprogress = false;
	cmderror = false;
	pollstep = 0;
	connected = false;
	system_valid = false;
	mod_count = 0;
	for (i = 0; i < MAX_MODULES; i++)
		modules[i] = NULL;
	ptccount = 0;
	savecount = 0;

	// Top level GUI
	GUIVersion = "Archon GUI 1.0.1191";
	setWindowTitle(GUIVersion);
	QWidget *cw = new QWidget();
	if (qApp->arguments().contains("-small"))
	{
		QScrollArea *scroll = new QScrollArea();
		setCentralWidget(scroll);
		scroll->setWidget(cw);
		scroll->setWidgetResizable(true);
	}
	else
	{
		setCentralWidget(cw);
	}
	QVBoxLayout *topvl = new QVBoxLayout(cw);
	splitter = new QSplitter(Qt::Vertical);
	topvl->addWidget(splitter);

	// Communication/log area
	qw = new QWidget();
	hl = new QHBoxLayout();
	qw->setLayout(hl);
	hl->setContentsMargins(0, 0, 0, 0);
	vl = new QVBoxLayout();
	label = new QLabel("Archon IP Address");
	boldFont = label->font();
	boldFont.setBold(true);
	fixedFont = label->font();
	fixedFont.setFamily("Monotype");
	fixedFont.setStyleHint(QFont::TypeWriter);
	vl->addWidget(label);
	leAddress = new QLineEdit("10.0.0.2");
	vl->addWidget(leAddress);
	connectButton = new QPushButton("Connect");
	connect(connectButton, SIGNAL(clicked()), this, SLOT(connectClicked()));
	vl->addWidget(connectButton);
	vl->addStretch();
	button = new QPushButton("Clear Log");
	vl->addWidget(button);
	hl->addLayout(vl);
	telog = new QPlainTextEdit();
	telog->setLineWrapMode(QPlainTextEdit::NoWrap);
	telog->setUndoRedoEnabled(false);
	telog->setReadOnly(true);
	telog->setMaximumBlockCount(1000);
	hl->addWidget(telog, 1);
	connect(button, SIGNAL(clicked()), telog, SLOT(clear()));
	splitter->addWidget(qw);

	// Tabbed area
	twTabs = new QTabWidget();
	splitter->addWidget(twTabs);
	fixedTabs = 13;
	// Twelve tabs that are always present:
	// System, Timing Script, Timing States, Parameters, VCPU, CDS,
	// Image, HPlot, VPlot, PTCPlot,
	// Raw Image, Raw HPlot, Raw VPlot

	// System
	tab = new QWidget();
	twTabs->addTab(tab, "System");
	tabvl = new QVBoxLayout(tab);
	tophl = new QHBoxLayout();
	tabvl->addLayout(tophl);

	// First column of system boxes
	vl = new QVBoxLayout();
	tophl->addLayout(vl);

	// Module listing
	gb = new QGroupBox("System");
	gl = new QGridLayout(gb);
	vl->addWidget(gb);
	x = 1;
	y = 0;
	label = new QLabel("Backplane");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("Rev");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("Version");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("Temp");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	y++;
	x = 1;
	backplane_type = new QLabel();
	gl->addWidget(backplane_type, y, x++);
	backplane_rev = new QLabel();
	gl->addWidget(backplane_rev, y, x++);
	backplane_ver = new QLabel();
	backplane_ver->setFont(fixedFont);
	backplane_ver->setTextInteractionFlags(Qt::TextSelectableByMouse);
	gl->addWidget(backplane_ver, y, x++);
	backplane_id = new QLabel();
	backplane_id->setFont(fixedFont);
	backplane_id->setTextInteractionFlags(Qt::TextSelectableByMouse);
	gl->addWidget(backplane_id, y, x++);
	backplane_temp = new QLabel();
	gl->addWidget(backplane_temp, y, x++);
	y++;
	x = 0;
	label = new QLabel("Slot");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("Module");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("Rev");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("Version");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("ID");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("Temp");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	x = 0;
	y++;
	for (i = 0; i < MAX_MODULES; i++)
	{
		x = 0;
		mod_slot[i] = new QLabel(QString::number(i + 1));
		mod_slot[i]->hide();
		gl->addWidget(mod_slot[i], y, x++);
		mod_type[i] = new QLabel();
		mod_type[i]->hide();
		gl->addWidget(mod_type[i], y, x++);
		mod_rev[i] = new QLabel();
		mod_rev[i]->hide();
		gl->addWidget(mod_rev[i], y, x++);
		mod_ver[i] = new QLabel();
		mod_ver[i]->setFont(fixedFont);
		mod_ver[i]->setTextInteractionFlags(Qt::TextSelectableByMouse);
		mod_ver[i]->hide();
		gl->addWidget(mod_ver[i], y, x++);
		mod_id[i] = new QLabel();
		mod_id[i]->setFont(fixedFont);
		mod_id[i]->setTextInteractionFlags(Qt::TextSelectableByMouse);
		mod_id[i]->hide();
		gl->addWidget(mod_id[i], y, x++);
		mod_temp[i] = new QLabel();
		mod_temp[i]->hide();
		gl->addWidget(mod_temp[i], y, x++);
		y++;
	}
	gl->setColumnStretch(x, 1);
	y++;

	// Frame buffers
	gb = new QGroupBox("Frame Buffers");
	gl = new QGridLayout(gb);
	vl->addWidget(gb);
	x = 0;
	y = 0;
	label = new QLabel("Buffer");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("Frame");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("Width");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("Height");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("Pixels");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("Lines");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("Raw Blocks");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("Raw Lines");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("Status");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	x = 0;
	y = 1;
	signalMapper = new QSignalMapper(this);
#if (QT_VERSION >= 0x051500)
	connect(signalMapper, SIGNAL(mappedInt(int)), this, SLOT(fetchFrame(int)));
#else
	connect(signalMapper, SIGNAL(mapped(int)), this, SLOT(fetchFrame(int)));
#endif
	for (i = 0; i < 3; i++)
	{
		label = new QLabel(QString::number(i + 1));
		gl->addWidget(label, y + i, x);
		bufframes[i] = new QLabel();
		bufframes[i]->setFont(fixedFont);
		gl->addWidget(bufframes[i], y + i, x + 1);
		bufwidths[i] = new QLabel();
		bufwidths[i]->setFont(fixedFont);
		gl->addWidget(bufwidths[i], y + i, x + 2);
		bufheights[i] = new QLabel();
		bufheights[i]->setFont(fixedFont);
		gl->addWidget(bufheights[i], y + i, x + 3);
		bufpixels[i] = new QLabel();
		bufpixels[i]->setFont(fixedFont);
		gl->addWidget(bufpixels[i], y + i, x + 4);
		buflines[i] = new QLabel();
		buflines[i]->setFont(fixedFont);
		gl->addWidget(buflines[i], y + i, x + 5);
		bufrawblocks[i] = new QLabel();
		bufrawblocks[i]->setFont(fixedFont);
		gl->addWidget(bufrawblocks[i], y + i, x + 6);
		bufrawlines[i] = new QLabel();
		bufrawlines[i]->setFont(fixedFont);
		gl->addWidget(bufrawlines[i], y + i, x + 7);
		bufstate[i] = new QLabel();
		bufstate[i]->setFont(fixedFont);
		gl->addWidget(bufstate[i], y + i, x + 8);
		button = new QPushButton("Fetch");
		signalMapper->setMapping(button, i);
		connect(button, SIGNAL(clicked()), signalMapper, SLOT(map()));
		gl->addWidget(button, y + i, x + 9);
	}
	y += 3;
	cbAutoFetch = new QCheckBox("Auto Fetch");
	gl->addWidget(cbAutoFetch, y++, 0, 1, 10);
	gl->setColumnStretch(x + 10, 1);
	label = new QLabel("Base Filename:");
	gl->addWidget(label, y, 0);
	leBaseFilename = new QLineEdit("temp");
	gl->addWidget(leBaseFilename, y++, 1, 1, 9);

	// Network configuration
	gb = new QGroupBox("Network Configuration");
	gl = new QGridLayout(gb);
	gl->setHorizontalSpacing(10);
	gl->setVerticalSpacing(4);
	vl->addWidget(gb);
	y = 0;
	label = new QLabel("IP:");
	gl->addWidget(label, y, 0);
	leIP = new QLineEdit("10.0.0.2");
	gl->addWidget(leIP, y++, 1);
	button = new QPushButton("Apply Network Configuration");
	connect(button, SIGNAL(clicked()), this, SLOT(applyNet()));
	gl->addWidget(button, y, 0, 1, 2);
	gl->setColumnStretch(2, 1);
	vl->addStretch(1);

	// Second system column
	vl = new QVBoxLayout();
	tophl->addLayout(vl);

	// Status
	gb = new QGroupBox("Status");
	gl = new QGridLayout(gb);
	vl->addWidget(gb);
	y = 0;
	label = new QLabel("Status Valid:");
	gl->addWidget(label, y, 0);
	status_valid = new QLabel("-");
	status_valid->setFont(fixedFont);
	gl->addWidget(status_valid, y++, 1);
	label = new QLabel("Status Count:");
	gl->addWidget(label, y, 0);
	status_count = new QLabel("-");
	status_count->setFont(fixedFont);
	gl->addWidget(status_count, y++, 1);
	fan_speed_label = new QLabel("Fan Speed (RPM):");
	gl->addWidget(fan_speed_label, y, 0);
	fan_speed = new QLabel("-");
	fan_speed->setFont(fixedFont);
	gl->addWidget(fan_speed, y++, 1);
	ext_clock_present_label = new QLabel("External Clock:");
	gl->addWidget(ext_clock_present_label, y, 0);
	ext_clock_present = new QLabel("-");
	ext_clock_present->setFont(fixedFont);
	gl->addWidget(ext_clock_present, y++, 1);
	gl->setColumnStretch(2, 1);

	// Power Supplies
	gb = new QGroupBox("Power");
	gl = new QGridLayout(gb);
	vl->addWidget(gb);
	x = 0;
	y = 0;
	label = new QLabel("Power ID:");
	gl->addWidget(label, y, x);
	power_id = new QLabel("-");
	power_id->setFont(fixedFont);
	power_id->setTextInteractionFlags(Qt::TextSelectableByMouse);
	gl->addWidget(power_id, y++, x + 1, 1, 2);
	label = new QLabel("Power Flags:");
	gl->addWidget(label, y, x);
	power_flags = new QLabel("-");
	gl->addWidget(power_flags, y++, x + 1, 1, 2);
	label = new QLabel("Supply");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("V");
	label->setFont(boldFont);
	gl->addWidget(label, y, x++);
	label = new QLabel("A");
	label->setFont(boldFont);
	gl->addWidget(label, y++, x++);
	x = 0;
	gl->setColumnStretch(3, 1);
	label = new QLabel("P2V5");
	gl->addWidget(label, y, x);
	p2v5_v = new QLabel("-");
	p2v5_v->setFont(fixedFont);
	gl->addWidget(p2v5_v, y, x + 1);
	p2v5_i = new QLabel("-");
	p2v5_i->setFont(fixedFont);
	gl->addWidget(p2v5_i, y++, x + 2);
	label = new QLabel("P5V");
	gl->addWidget(label, y, x);
	p5v_v = new QLabel("-");
	p5v_v->setFont(fixedFont);
	gl->addWidget(p5v_v, y, x + 1);
	p5v_i = new QLabel("-");
	p5v_i->setFont(fixedFont);
	gl->addWidget(p5v_i, y++, x + 2);
	label = new QLabel("P6V");
	gl->addWidget(label, y, x);
	p6v_v = new QLabel("-");
	p6v_v->setFont(fixedFont);
	gl->addWidget(p6v_v, y, x + 1);
	p6v_i = new QLabel("-");
	p6v_i->setFont(fixedFont);
	gl->addWidget(p6v_i, y++, x + 2);
	label = new QLabel("N6V");
	gl->addWidget(label, y, x);
	n6v_v = new QLabel("-");
	n6v_v->setFont(fixedFont);
	gl->addWidget(n6v_v, y, x + 1);
	n6v_i = new QLabel("-");
	n6v_i->setFont(fixedFont);
	gl->addWidget(n6v_i, y++, x + 2);
	label = new QLabel("P17V");
	gl->addWidget(label, y, x);
	p17v_v = new QLabel("-");
	p17v_v->setFont(fixedFont);
	gl->addWidget(p17v_v, y, x + 1);
	p17v_i = new QLabel("-");
	p17v_i->setFont(fixedFont);
	gl->addWidget(p17v_i, y++, x + 2);
	label = new QLabel("N17V");
	gl->addWidget(label, y, x);
	n17v_v = new QLabel("-");
	n17v_v->setFont(fixedFont);
	gl->addWidget(n17v_v, y, x + 1);
	n17v_i = new QLabel("-");
	n17v_i->setFont(fixedFont);
	gl->addWidget(n17v_i, y++, x + 2);
	label = new QLabel("P35V");
	gl->addWidget(label, y, x);
	p35v_v = new QLabel("-");
	p35v_v->setFont(fixedFont);
	gl->addWidget(p35v_v, y, x + 1);
	p35v_i = new QLabel("-");
	p35v_i->setFont(fixedFont);
	gl->addWidget(p35v_i, y++, x + 2);
	label = new QLabel("N35V");
	gl->addWidget(label, y, x);
	n35v_v = new QLabel("-");
	n35v_v->setFont(fixedFont);
	gl->addWidget(n35v_v, y, x + 1);
	n35v_i = new QLabel("-");
	n35v_i->setFont(fixedFont);
	gl->addWidget(n35v_i, y++, x + 2);
	label = new QLabel("P100V");
	gl->addWidget(label, y, x);
	p100v_v = new QLabel("-");
	p100v_v->setFont(fixedFont);
	gl->addWidget(p100v_v, y, x + 1);
	p100v_i = new QLabel("-");
	p100v_i->setFont(fixedFont);
	gl->addWidget(p100v_i, y++, x + 2);
	label = new QLabel("N100V");
	gl->addWidget(label, y, x);
	n100v_v = new QLabel("-");
	n100v_v->setFont(fixedFont);
	gl->addWidget(n100v_v, y, x + 1);
	n100v_i = new QLabel("-");
	n100v_i->setFont(fixedFont);
	gl->addWidget(n100v_i, y++, x + 2);
	label = new QLabel("USER");
	gl->addWidget(label, y, x);
	user_v = new QLabel("-");
	user_v->setFont(fixedFont);
	gl->addWidget(user_v, y, x + 1);
	user_i = new QLabel("-");
	user_i->setFont(fixedFont);
	gl->addWidget(user_i, y++, x + 2);
	label = new QLabel("HEATER");
	gl->addWidget(label, y, x);
	heater_v = new QLabel("-");
	heater_v->setFont(fixedFont);
	gl->addWidget(heater_v, y, x + 1);
	heater_i = new QLabel("-");
	heater_i->setFont(fixedFont);
	gl->addWidget(heater_i, y++, x + 2);

	gb = new QGroupBox("System");
	vl2 = new QVBoxLayout(gb);
	vl->addWidget(gb);
	cbTrigOutForce = new QCheckBox("Trigger Out Force");
	vl2->addWidget(cbTrigOutForce);
	cbTrigOutLevel = new QCheckBox("Trigger Out Level");
	vl2->addWidget(cbTrigOutLevel);
	cbTrigOutInvert = new QCheckBox("Trigger Out Invert");
	vl2->addWidget(cbTrigOutInvert);
	cbTrigOutPower = new QCheckBox("Trigger Out Power");
	vl2->addWidget(cbTrigOutPower);
	cbTrigInEnable = new QCheckBox("Trigger In Enable");
	vl2->addWidget(cbTrigInEnable);
	cbTrigInInvert = new QCheckBox("Trigger In Invert");
	vl2->addWidget(cbTrigInInvert);
	cbTrigInEdge = new QCheckBox("Trigger In Edge Mode");
	vl2->addWidget(cbTrigInEdge);
	cbExternalClock = new QCheckBox("External Clock");
	vl2->addWidget(cbExternalClock);
	cbFanDisable = new QCheckBox("Fan Disable");
	vl2->addWidget(cbFanDisable);
	cbApplyAll = new QCheckBox("Apply All At Startup");
	vl2->addWidget(cbApplyAll);
	cbPowerOn = new QCheckBox("Power On At Startup");
	vl2->addWidget(cbPowerOn);
	button = new QPushButton("Apply");
	connect(button, SIGNAL(clicked()), this, SLOT(applySystem()));
	hl = new QHBoxLayout();
	hl->addWidget(button);
	hl->addStretch();
	vl2->addLayout(hl);

	vl->addStretch();

	hl = new QHBoxLayout();
//	button = new QPushButton("Test");
//	connect(button, SIGNAL(clicked()), this, SLOT(testButton()));
//	hl->addWidget(button);
	hl->addStretch(1);
	tabvl->addStretch();
	tabvl->addLayout(hl);

	// Timing Script tab
	tab = new QWidget();
	twTabs->addTab(tab, "Timing Script");
	teScript = new QPlainTextEdit();
	teScript->setLineWrapMode(QPlainTextEdit::NoWrap);
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	vl->addWidget(teScript, 1);
	hl = new QHBoxLayout();
	button = new QPushButton("Load Timing");
	connect(button, SIGNAL(clicked()), this, SLOT(loadTiming()));
	hl->addWidget(button);
	button = new QPushButton("Timing Reset");
	connect(button, SIGNAL(clicked()), this, SLOT(resetTiming()));
	hl->addWidget(button);
	button = new QPushButton("Timing Hold");
	connect(button, SIGNAL(clicked()), this, SLOT(holdTiming()));
	hl->addWidget(button);
	button = new QPushButton("Timing Release");
	connect(button, SIGNAL(clicked()), this, SLOT(releaseTiming()));
	hl->addWidget(button);
	hl->addStretch(1);
	vl->addLayout(hl);

	// Timing states tab
	clock_lock = false;
	tab = new QWidget();
	twTabs->addTab(tab, "Timing States");
	gl = new QGridLayout();
	tab->setLayout(gl);
	gl->setSpacing(10);
	label = new QLabel("State Name");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 0, 1, 2);
	lwStates = new QListWidget();
	connect(lwStates, SIGNAL(itemSelectionChanged()),
		this, SLOT(stateChanged()));
	gl->addWidget(lwStates, 1, 0, 1, 2);
	label = new QLabel("Signal States");
	label->setFont(boldFont);
	gl->addWidget(label, 0, 2);
	twModuleSignalTabs = new QTabWidget();
	gl->addWidget(twModuleSignalTabs, 1, 2, 3, 1);

	// Control clocks
	tab = new QWidget();
	twModuleSignalTabs->addTab(tab, "Control");
	gl2 = new QGridLayout();
	tab->setLayout(gl2);
	gl2->setSpacing(10);
	label = new QLabel("State");
	label->setFont(boldFont);
	gl2->addWidget(label, 0, 1);
	label = new QLabel("Keep");
	label->setFont(boldFont);
	gl2->addWidget(label, 0, 2);
	label = new QLabel("INT");
	label->setFont(boldFont);
	gl2->addWidget(label, 1, 0);
	label = new QLabel("FRAME");
	label->setFont(boldFont);
	gl2->addWidget(label, 2, 0);
	label = new QLabel("LINE");
	label->setFont(boldFont);
	gl2->addWidget(label, 3, 0);
	label = new QLabel("PIXEL");
	label->setFont(boldFont);
	gl2->addWidget(label, 4, 0);
	label = new QLabel("TRIGA");
	label->setFont(boldFont);
	gl2->addWidget(label, 5, 0);
	label = new QLabel("TRIGB");
	label->setFont(boldFont);
	gl2->addWidget(label, 6, 0);
	for (i = 0; i < CONTROL_COUNT; i++)
	{
		control_clock[i] = new QCheckBox();
		control_keep[i] = new QCheckBox();
		connect(control_clock[i], SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		connect(control_keep[i], SIGNAL(toggled(bool)), this, SLOT(clockChanged()));
		gl2->addWidget(control_clock[i], i + 1, 1, Qt::AlignHCenter);
		gl2->addWidget(control_keep[i], i + 1, 2, Qt::AlignHCenter);
	}
	gl2->setRowStretch(CONTROL_COUNT + 2, 1);
	gl2->setColumnStretch(3, 1);

	button = new QPushButton("Move Up");
	connect(button, SIGNAL(clicked()), this, SLOT(stateUp()));
	gl->addWidget(button, 2, 0);
	button = new QPushButton("Move Down");
	connect(button, SIGNAL(clicked()), this, SLOT(stateDown()));
	gl->addWidget(button, 2, 1);
	button = new QPushButton("Add");
	connect(button, SIGNAL(clicked()), this, SLOT(stateAdd()));
	gl->addWidget(button, 3, 0);
	button = new QPushButton("Delete");
	connect(button, SIGNAL(clicked()), this, SLOT(stateDelete()));
	gl->addWidget(button, 3, 1);
	button = new QPushButton("Duplicate");
	connect(button, SIGNAL(clicked()), this, SLOT(stateDuplicate()));
	gl->addWidget(button, 4, 0);
	gl->setColumnStretch(2, 1);

	// Parameters/Constants tab
	tab = new QWidget();
	twTabs->addTab(tab, "Parameters");
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	gl = new QGridLayout();
	vl->addLayout(gl);
	gl->setHorizontalSpacing(10);
	gl->setVerticalSpacing(4);
	label = new QLabel("Parameters");
	gl->addWidget(label, 0, 0);
	teParameters = new QPlainTextEdit("");
	teParameters->setLineWrapMode(QPlainTextEdit::NoWrap);
	gl->addWidget(teParameters, 1, 0);
	label = new QLabel("Constants");
	gl->addWidget(label, 0, 1);
	teConstants = new QPlainTextEdit("");
	teConstants->setLineWrapMode(QPlainTextEdit::NoWrap);
	gl->addWidget(teConstants, 1, 1);
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	button = new QPushButton("Apply");
	hl->addWidget(button);
	connect(button, SIGNAL(clicked()), this, SLOT(loadParameters()));
	button = new QPushButton("Test");
	hl->addWidget(button);
	connect(button, SIGNAL(clicked()), this, SLOT(test()));
	hl->addStretch(1);

	// VCPU tab
	tab = new QWidget();
	twTabs->addTab(tab, "VCPU");
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	twModuleVCPUTabs = new QTabWidget();
	vl->addWidget(twModuleVCPUTabs);

	// CDS / Deinterlacing tab
	tab = new QWidget();
	twTabs->addTab(tab, "CDS / Deint");
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	gl = new QGridLayout();
	vl->addLayout(gl);
	gl->setHorizontalSpacing(10);
	gl->setVerticalSpacing(4);
	y = 0;
	label = new QLabel("First Reset Sample:");
	gl->addWidget(label, y, 0);
	shp1 = new QLineEdit("0");
	gl->addWidget(shp1, y++, 1);
	label = new QLabel("Last Reset Sample:");
	gl->addWidget(label, y, 0);
	shp2 = new QLineEdit("0");
	gl->addWidget(shp2, y++, 1);
	label = new QLabel("First Video Sample:");
	gl->addWidget(label, y, 0);
	shd1 = new QLineEdit("0");
	gl->addWidget(shd1, y++, 1);
	label = new QLabel("Last Video Sample:");
	gl->addWidget(label, y, 0);
	shd2 = new QLineEdit("0");
	gl->addWidget(shd2, y++, 1);
	pclkdelaylabel = new QLabel("PCLK Delay:");
	gl->addWidget(pclkdelaylabel, y, 0);
	pclkdelay = new QLineEdit("0");
	gl->addWidget(pclkdelay, y++, 1);
	label = new QLabel("Sample Mode:");
	gl->addWidget(label, y, 0);
	samplemode = new QComboBox;
	samplemode->addItem("NORMAL");
	samplemode->addItem("HDR");
	gl->addWidget(samplemode, y++, 1);
	label = new QLabel("Pixels Per Tap:");
	gl->addWidget(label, y, 0);
	pixelcount = new QLineEdit("1");
	gl->addWidget(pixelcount, y++, 1);
	label = new QLabel("Lines Per Tap:");
	gl->addWidget(label, y, 0);
	linecount = new QLineEdit("1");
	gl->addWidget(linecount, y++, 1);
	label = new QLabel("Frame Mode:");
	gl->addWidget(label, y, 0);
	framemode = new QComboBox;
	framemode->addItem("TOP");
	framemode->addItem("BOTTOM");
	framemode->addItem("SPLIT");
	gl->addWidget(framemode, y++, 1);
	label = new QLabel("Big Buffers:");
	gl->addWidget(label, y, 0);
	bigBuffers = new QCheckBox();
	gl->addWidget(bigBuffers, y++, 1);
	label = new QLabel("Raw Enable:");
	gl->addWidget(label, y, 0);
	rawEnable = new QCheckBox();
	gl->addWidget(rawEnable, y++, 1);
	adxrawlabel = new QLabel("ADX Raw Mode:");
	gl->addWidget(adxrawlabel, y, 0);
	adxraw = new QCheckBox();
	gl->addWidget(adxraw, y++, 1);
	adxcdslabel = new QLabel("ADX CDS Mode:");
	gl->addWidget(adxcdslabel, y, 0);
	adxcds = new QCheckBox();
	gl->addWidget(adxcds, y++, 1);
	linescanlabel = new QLabel("Line Scan Mode:");
	gl->addWidget(linescanlabel, y, 0);
	linescan = new QCheckBox();
	gl->addWidget(linescan, y++, 1);
	label = new QLabel("Raw Channel Select:");
	gl->addWidget(label, y, 0);
	rawsel = new QComboBox;
	for (i = 1; i <= 32; i++)
		rawsel->addItem(QString::number(i));
	gl->addWidget(rawsel, y++, 1);
	label = new QLabel("Raw Start Line:");
	gl->addWidget(label, y, 0);
	rawStartLine = new QLineEdit("0");
	gl->addWidget(rawStartLine, y++, 1);
	label = new QLabel("Raw End Line:");
	gl->addWidget(label, y, 0);
	rawEndLine = new QLineEdit("0");
	gl->addWidget(rawEndLine, y++, 1);
	label = new QLabel("Raw Start Pixel:");
	gl->addWidget(label, y, 0);
	rawStartPixel = new QLineEdit("0");
	gl->addWidget(rawStartPixel, y++, 1);
	label = new QLabel("Raw Samples:");
	gl->addWidget(label, y, 0);
	rawSamples = new QLineEdit("0");
	gl->addWidget(rawSamples, y++, 1);
	gl->setColumnMinimumWidth(2, 40);
	label = new QLabel("Tap Order:");
	gl->addWidget(label, 0, 3);
	teTapOrder = new QPlainTextEdit();
	teTapOrder->setLineWrapMode(QPlainTextEdit::NoWrap);
	gl->addWidget(teTapOrder, 1, 3, ++y, 1);
	gl->setColumnStretch(4, 1);
	gl->setRowStretch(y, 1);
	hl = new QHBoxLayout();
	button = new QPushButton("Apply");
	connect(button, SIGNAL(clicked()), this, SLOT(applyCDS()));
	hl->addWidget(button);
	hl->addStretch(1);
	vl->addLayout(hl);

	// Image tab
	tab = new QWidget();
	twTabs->addTab(tab, "Image");
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	imageScroll = new ImageScrollWidget(0, false);
	vl->addWidget(imageScroll);
	connect(imageScroll, SIGNAL(statChanged(int,int,int,int)), this, SLOT(statChanged(int,int,int,int)));
	connect(imageScroll, SIGNAL(noiseChanged(int,int,int,int)), this, SLOT(noiseChanged(int,int,int,int)));
	connect(imageScroll, SIGNAL(plotChanged(int,int)), this, SLOT(plotChanged(int,int)));
	// Image statistics
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	statsLabel = new QLabel("");
	hl->addWidget(statsLabel, 1);
	noiseLabel = new QLabel("");
	hl->addWidget(noiseLabel, 1);
	diffStatsLabel = new QLabel("");
	hl->addWidget(diffStatsLabel,1);
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	sbGain = new QSlider(Qt::Horizontal);
	sbGain->setMinimum(-1000);
	sbGain->setValue(0);
	sbGain->setMaximum(1000);
	sbGain->setTracking(true);
	hl->addWidget(sbGain, 1);
	QObject::connect(sbGain, SIGNAL(valueChanged(int)), this, SLOT(gainChange(int)));
	sbOffset = new QSlider(Qt::Horizontal);
	sbOffset->setMinimum(-65535);
	sbOffset->setMaximum(65535);
	sbOffset->setValue(0);
	sbOffset->setTracking(true);
	hl->addWidget(sbOffset, 1);
	QObject::connect(sbOffset, SIGNAL(valueChanged(int)), this, SLOT(offsetChange(int)));
	button = new QPushButton("Reset LUT");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(resetGainOffset()));
	hl->addWidget(button);
	button = new QPushButton("Fit LUT");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(fitGainOffset()));
	hl->addWidget(button);
	imageMode = new QComboBox();
	imageMode->addItem("Nearest");
	imageMode->addItem("Max");
	imageMode->addItem("Min");
	QObject::connect(imageMode, SIGNAL(currentIndexChanged(int)), this, SLOT(changeImageMode(int)));
	hl->addWidget(imageMode);
	// Zoom buttons
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	button = new QPushButton("Zoom In");
	connect(button,SIGNAL(clicked()),this,SLOT(zoomInClick()));
	hl->addWidget(button);
	button = new QPushButton("Zoom 1:1");
	connect(button,SIGNAL(clicked()),this,SLOT(zoom1Click()));
	hl->addWidget(button);
	button = new QPushButton("Zoom Out");
	connect(button,SIGNAL(clicked()),this,SLOT(zoomOutClick()));
	hl->addWidget(button);
	button = new QPushButton("Zoom Fit");
	connect(button,SIGNAL(clicked()),this,SLOT(zoomFitClick()));
	hl->addWidget(button);
	hl->addStretch();
	button = new QPushButton("Open Frame");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(openFrame()));
	hl->addWidget(button);
	button = new QPushButton("Open HDR Frame");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(openHDRFrame()));
	hl->addWidget(button);
	button = new QPushButton("Open FITS");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(openFITS()));
	hl->addWidget(button);
	button = new QPushButton("Save Frame");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(saveFrame()));
	hl->addWidget(button);
	button = new QPushButton("Save FITS");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(saveFITS()));
	hl->addWidget(button);
	button = new QPushButton("Save Sequence");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(saveSequence()));
	hl->addWidget(button);
	label = new QLabel("Save Sequence frame count:");
	hl->addWidget(label);
	leSaveCount = new QLineEdit("1");
	hl->addWidget(leSaveCount);
	cbSaveAll = new QCheckBox("Save all frames");
	hl->addWidget(cbSaveAll);

	// Horizontal plot tab
	tab = new QWidget();
	twTabs->addTab(tab,"Horizontal Plot");
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	HPlot = new QwtPlot();
	vl->addWidget(HPlot);
	grid = new QwtPlotGrid;
	grid->attach(HPlot);
	grid->setMajorPen(QPen(Qt::gray, 0, Qt::DotLine));
	HCurve = new QwtPlotCurve();
	HCurve->attach(HPlot);
	HCurve->setPen(QPen(Qt::red));
	HPlot->setAxisTitle(QwtPlot::yLeft,"DN");
	HPlot->setAxisTitle(QwtPlot::xBottom,"Pixel");
	HPanner = new QwtPlotPanner(HPlot->canvas());
	HPanner->setMouseButton(Qt::RightButton);
	HZoomer = new QwtPlotZoomer(HPlot->canvas());
	HZoomer->setMousePattern(QwtEventPattern::MouseSelect2,Qt::MiddleButton, Qt::NoModifier);
	m_hplot = 0;
	cbHAvgCheckBox = new QCheckBox("Average over signal area");
	QObject::connect(cbHAvgCheckBox,SIGNAL(clicked()),this,SLOT(plotChanged()));
	button = new QPushButton("Save Plot");
	QObject::connect(button,SIGNAL(clicked()),this,SLOT(saveHPlot()));
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	hl->addWidget(cbHAvgCheckBox);
	hl->addStretch(1);
	hl->addWidget(button);

	// Vertical plot tab
	tab = new QWidget();
	twTabs->addTab(tab,"Vertical Plot");
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	VPlot = new QwtPlot();
	vl->addWidget(VPlot);
	grid = new QwtPlotGrid;
	grid->attach(VPlot);
	grid->setMajorPen(QPen(Qt::gray, 0, Qt::DotLine));
	VCurve = new QwtPlotCurve();
	VCurve->attach(VPlot);
	VCurve->setPen(QPen(Qt::blue));
	VPlot->setAxisTitle(QwtPlot::yLeft,"DN");
	VPlot->setAxisTitle(QwtPlot::xBottom,"Pixel");
	VPanner = new QwtPlotPanner(VPlot->canvas());
	VPanner->setMouseButton(Qt::RightButton);
	VZoomer = new QwtPlotZoomer(VPlot->canvas());
	VZoomer->setMousePattern(QwtEventPattern::MouseSelect2,Qt::MiddleButton, Qt::NoModifier);
	m_vplot = 0;
	cbVAvgCheckBox = new QCheckBox("Average over signal area");
	QObject::connect(cbVAvgCheckBox,SIGNAL(clicked()),this,SLOT(plotChanged()));
	button = new QPushButton("Save Plot");
	QObject::connect(button,SIGNAL(clicked()),this,SLOT(saveVPlot()));
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	hl->addWidget(cbVAvgCheckBox);
	hl->addStretch(1);
	hl->addWidget(button);

	// PTC plot tab
	tab = new QWidget();
	twTabs->addTab(tab,"PTC Plot");
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	PTCPlot = new QwtPlot();
	vl->addWidget(PTCPlot);
	grid = new QwtPlotGrid;
	grid->attach(PTCPlot);
	grid->setMajorPen(QPen(Qt::gray, 0, Qt::DotLine));
	PTCSymbol = new QwtSymbol();
	PTCSymbol->setStyle(QwtSymbol::Ellipse);
	PTCSymbol->setPen(QColor(Qt::darkGreen));
	PTCSymbol->setBrush(QColor(Qt::darkGreen));
	PTCSymbol->setSize(5);
	PTCCurve = new QwtPlotCurve();
	PTCCurve->attach(PTCPlot);
	PTCCurve->setPen(QPen(Qt::darkGreen));
	PTCCurve->setSymbol(PTCSymbol);
	PTCPlot->setAxisTitle(QwtPlot::yLeft,"Variance");
	PTCPlot->setAxisTitle(QwtPlot::xBottom,"Signal");
	PTCPanner = new QwtPlotPanner(PTCPlot->canvas());
	PTCPanner->setMouseButton(Qt::RightButton);
	PTCZoomer = new QwtPlotZoomer(PTCPlot->canvas());
	PTCZoomer->setMousePattern(QwtEventPattern::MouseSelect2,Qt::MiddleButton, Qt::NoModifier);
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	button = new QPushButton("Snap PTC");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(snapPTC()));
	hl->addWidget(button);
	hl->addSpacing(20);
	label = new QLabel("PTC Frames to average:");
	hl->addWidget(label);
	lePTCCount = new QLineEdit("1");
	hl->addWidget(lePTCCount);
	hl->addStretch(1);
	button = new QPushButton("Reset PTC");
	QObject::connect(button,SIGNAL(clicked()),this,SLOT(resetPTC()));
	hl->addWidget(button);
	button = new QPushButton("Save PTC");
	QObject::connect(button,SIGNAL(clicked()),this,SLOT(savePTC()));
	hl->addWidget(button);

	// Raw image tab
	tab = new QWidget();
	twTabs->addTab(tab, "Raw Image");
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	rawImageScroll = new ImageScrollWidget(0, true);
	vl->addWidget(rawImageScroll);
	connect(rawImageScroll, SIGNAL(statChanged(int,int,int,int)), this, SLOT(rawStatChanged(int,int,int,int)));
	connect(rawImageScroll, SIGNAL(noiseChanged(int,int,int,int)), this, SLOT(rawNoiseChanged(int,int,int,int)));
	connect(rawImageScroll, SIGNAL(plotChanged(int,int)), this, SLOT(rawPlotChanged(int,int)));
	// Image statistics
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	rawStatsLabel = new QLabel("");
	hl->addWidget(rawStatsLabel, 1);
	rawNoiseLabel = new QLabel("");
	hl->addWidget(rawNoiseLabel, 1);
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	sbRawGain = new QSlider(Qt::Horizontal);
	sbRawGain->setMinimum(-1000);
	sbRawGain->setValue(0);
	sbRawGain->setMaximum(1000);
	sbRawGain->setTracking(true);
	hl->addWidget(sbRawGain, 1);
	QObject::connect(sbRawGain, SIGNAL(valueChanged(int)), this, SLOT(rawGainChange(int)));
	sbRawOffset = new QSlider(Qt::Horizontal);
	sbRawOffset->setMinimum(-65535);
	sbRawOffset->setMaximum(65535);
	sbRawOffset->setValue(0);
	sbRawOffset->setTracking(true);
	hl->addWidget(sbRawOffset, 1);
	QObject::connect(sbRawOffset, SIGNAL(valueChanged(int)), this, SLOT(rawOffsetChange(int)));
	button = new QPushButton("Reset LUT");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(resetRawGainOffset()));
	hl->addWidget(button);
	// Zoom buttons
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	button = new QPushButton("Zoom In");
	connect(button,SIGNAL(clicked()),this,SLOT(rawZoomInClick()));
	hl->addWidget(button);
	button = new QPushButton("Zoom 1:1");
	connect(button,SIGNAL(clicked()),this,SLOT(rawZoom1Click()));
	hl->addWidget(button);
	button = new QPushButton("Zoom Out");
	connect(button,SIGNAL(clicked()),this,SLOT(rawZoomOutClick()));
	hl->addWidget(button);
	hl->addStretch();
	button = new QPushButton("Save Frame");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(saveRawFrame()));
	hl->addWidget(button);

	// Horizontal plot tab
	tab = new QWidget();
	twTabs->addTab(tab, "Horizontal Raw Plot");
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	rawHPlot = new QwtPlot();
	vl->addWidget(rawHPlot);
	grid = new QwtPlotGrid;
	grid->attach(rawHPlot);
	grid->setMajorPen(QPen(Qt::gray, 0, Qt::DotLine));
	rawHCurve = new QwtPlotCurve();
	rawHCurve->attach(rawHPlot);
	rawHCurve->setPen(QPen(Qt::red));
	symbol = new QwtSymbol(QwtSymbol::Diamond, QBrush(Qt::red), QPen(Qt::red), QSize(5, 5));
	rawHCurve->setSymbol(symbol);
	rawHPlot->setAxisTitle(QwtPlot::yLeft, "DN");
	rawHPlot->setAxisTitle(QwtPlot::xBottom, "Sample (10ns)");
	rawHPanner = new QwtPlotPanner(rawHPlot->canvas());
	rawHPanner->setMouseButton(Qt::RightButton);
	rawHZoomer = new QwtPlotZoomer(rawHPlot->canvas());
	rawHZoomer->setMousePattern(QwtEventPattern::MouseSelect2, Qt::MiddleButton, Qt::NoModifier);
	m_rawhplot = 0;
	cbRawHAvgCheckBox = new QCheckBox("Average over signal area");
	QObject::connect(cbRawHAvgCheckBox, SIGNAL(clicked()), this, SLOT(rawPlotChanged()));
	button = new QPushButton("Save Plot");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(saveRawHPlot()));
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	hl->addWidget(cbRawHAvgCheckBox);
	hl->addStretch(1);
	hl->addWidget(button);

	// Vertical plot tab
	tab = new QWidget();
	twTabs->addTab(tab, "Vertical Raw Plot");
	vl = new QVBoxLayout();
	tab->setLayout(vl);
	rawVPlot = new QwtPlot();
	vl->addWidget(rawVPlot);
	grid = new QwtPlotGrid;
	grid->attach(rawVPlot);
	grid->setMajorPen(QPen(Qt::gray, 0, Qt::DotLine));
	rawVCurve = new QwtPlotCurve();
	rawVCurve->attach(rawVPlot);
	rawVCurve->setPen(QPen(Qt::blue));
	rawVPlot->setAxisTitle(QwtPlot::yLeft, "DN");
	rawVPlot->setAxisTitle(QwtPlot::xBottom, "Pixel");
	rawVPanner = new QwtPlotPanner(rawVPlot->canvas());
	rawVPanner->setMouseButton(Qt::RightButton);
	rawVZoomer = new QwtPlotZoomer(rawVPlot->canvas());
	rawVZoomer->setMousePattern(QwtEventPattern::MouseSelect2, Qt::MiddleButton, Qt::NoModifier);
	m_rawvplot = 0;
	cbRawVAvgCheckBox = new QCheckBox("Average over signal area");
	QObject::connect(cbRawVAvgCheckBox, SIGNAL(clicked()), this, SLOT(rawPlotChanged()));
	button = new QPushButton("Save Plot");
	QObject::connect(button, SIGNAL(clicked()), this, SLOT(saveRawVPlot()));
	hl = new QHBoxLayout();
	vl->addLayout(hl);
	hl->addWidget(cbRawVAvgCheckBox);
	hl->addStretch(1);
	hl->addWidget(button);

	// Bottom buttons
	hl = new QHBoxLayout();
	topvl->addLayout(hl);
	button = new QPushButton("Apply All");
	connect(button, SIGNAL(clicked()), this, SLOT(applyAll()));
	hl->addWidget(button);
	hl->addStretch(1);
	// Polling On
	button = new QPushButton("Polling On");
	hl->addWidget(button);
	connect(button, SIGNAL(clicked()), this, SLOT(pollOn()));
	// Polling Off
	button = new QPushButton("Polling Off");
	hl->addWidget(button);
	connect(button, SIGNAL(clicked()), this, SLOT(pollOff()));
	// Power status indicator
	wPower = new PowerWidget();
	wPower->setToolTip("UNKNOWN");
	wPower->setColor(Qt::darkGray);
	hl->addWidget(wPower);
	// Power On
	button = new QPushButton("Power On");
	hl->addWidget(button);
	connect(button, SIGNAL(clicked()), this, SLOT(powerOn()));
	// Power Off
	button = new QPushButton("Power Off");
	hl->addWidget(button);
	connect(button, SIGNAL(clicked()), this, SLOT(powerOff()));

	// Main menu
	// File
	QMenu *menu = menuBar()->addMenu("&File");
	actionOpen = new QAction("&Open ACF", this);
	menu->addAction(actionOpen);
	connect(actionOpen, SIGNAL(triggered()), this, SLOT(openFile()));
	actionSave = new QAction("&Save ACF", this);
	menu->addAction(actionSave);
	connect(actionSave, SIGNAL(triggered()), this, SLOT(saveFile()));
	menu->addSeparator();
	actionOpenNice = new QAction("O&pen NCF", this);
	menu->addAction(actionOpenNice);
	connect(actionOpenNice, SIGNAL(triggered()), this, SLOT(openNiceFile()));
	actionSaveNice = new QAction("S&ave NCF", this);
	menu->addAction(actionSaveNice);
	connect(actionSaveNice, SIGNAL(triggered()), this, SLOT(saveNiceFile()));
	menu->addSeparator();
	actionExit = new QAction("E&xit", this);
	menu->addAction(actionExit);
	connect(actionExit, SIGNAL(triggered()), qApp, SLOT(quit()));

	// System
	menu = menuBar()->addMenu("&System");
	actionFlash = new QAction("&Flash", this);
	menu->addAction(actionFlash);
	connect(actionFlash, SIGNAL(triggered()), this, SLOT(flashClicked()));
	actionVerify = new QAction("&Verify", this);
	menu->addAction(actionVerify);
	connect(actionVerify, SIGNAL(triggered()), this, SLOT(verifyClicked()));
	actionReboot = new QAction("&Reboot", this);
	menu->addAction(actionReboot);
	connect(actionReboot, SIGNAL(triggered()), this, SLOT(rebootClicked()));
	actionWarmboot = new QAction("&Warmboot", this);
	menu->addAction(actionWarmboot);
	connect(actionWarmboot, SIGNAL(triggered()), this, SLOT(warmbootClicked()));
	menu->addSeparator();
	actionFlashBackplane = new QAction("Firmware", this);
	actionFlashBackplane->setCheckable(true);
	actionFlashBackplane->setChecked(true);
	menu->addAction(actionFlashBackplane);
	actionFlashCode = new QAction("Software", this);
	actionFlashCode->setCheckable(true);
	actionFlashCode->setChecked(true);
	menu->addAction(actionFlashCode);
	actionFlashConfig = new QAction("Config", this);
	actionFlashConfig->setCheckable(true);
	actionFlashConfig->setMenuRole(QAction::NoRole); // Avoids OSX moving menu entry
//	actionFlashConfig->setChecked(true);
	menu->addAction(actionFlashConfig);
	menu->addSeparator();
	actionFlashActiveConfig = new QAction("Flash Active Config", this);
	connect(actionFlashActiveConfig, SIGNAL(triggered()), this, SLOT(flashActiveConfigClicked()));
	menu->addAction(actionFlashActiveConfig);
	actionEraseStoredConfig = new QAction("Erase Stored Config", this);
	connect(actionEraseStoredConfig, SIGNAL(triggered()), this, SLOT(eraseStoredConfigClicked()));
	menu->addAction(actionEraseStoredConfig);

	// Modules
	menu = menuBar()->addMenu("&Module");
	actionModuleFlash = new QAction("&Flash", this);
	menu->addAction(actionModuleFlash);
	connect(actionModuleFlash, SIGNAL(triggered()), this, SLOT(flashModuleClicked()));
	actionModuleVerify = new QAction("&Verify", this);
	menu->addAction(actionModuleVerify);
	connect(actionModuleVerify, SIGNAL(triggered()), this, SLOT(verifyModuleClicked()));
	menu->addSeparator();
	agModules = new QActionGroup(this);
	for (i = 0; i < MAX_MODULES; i++)
	{
		actionFlashModule[i] = new QAction(QString("Module %1").arg(i + 1), agModules);
		actionFlashModule[i]->setCheckable(true);
		actionFlashModule[i]->setVisible(false);
		menu->addAction(actionFlashModule[i]);
	}

	// Help
	menu = menuBar()->addMenu("&Help");
	actionAbout = new QAction("&About",this);
	menu->addAction(actionAbout);
	connect(actionAbout, SIGNAL(triggered()), this, SLOT(showAbout()));

	// Status bar
	StatusLabel = new QLabel("Idle");
	StatusLabel->setMinimumWidth(150);
	statusBar()->addWidget(StatusLabel);
	spProgress = new SimpleProgress();
	spProgress->setMinimumWidth(50);
	statusBar()->addWidget(spProgress, 1);
	connect(archon, SIGNAL(progressMessage(QString, int, int)), this, SLOT(progressMessage(QString, int, int)));
	frameLabel = new QLabel("");
	frameLabel->setMinimumWidth(50);
	statusBar()->addWidget(frameLabel, 1);
	zoomLabel = new QLabel("");
	zoomLabel->setMinimumWidth(50);
	statusBar()->addWidget(zoomLabel, 1);
	DRLabel = new QLabel("");
	DRLabel->setMinimumWidth(50);
	statusBar()->addWidget(DRLabel, 2);
	imageXYLabel = new QLabel("");
	imageXYLabel->setMinimumWidth(50);
	statusBar()->addWidget(imageXYLabel, 2);
	filenameLabel = new QLabel("");
	filenameLabel->setMinimumWidth(50);
	statusBar()->addWidget(filenameLabel, 2);
	connect(imageScroll, SIGNAL(mousexy(int, int, uint)), this, SLOT(imageMouseXY(int, int, uint)));
	connect(rawImageScroll, SIGNAL(mousexy(int, int, uint)), this, SLOT(rawImageMouseXY(int, int, uint)));

	// Archon signals
	connect(archon, SIGNAL(logMessage(QString)), this, SLOT(logMessage(QString)));
	connect(archon, SIGNAL(msgSystem(RMap)), this, SLOT(msgSystem(RMap)));
	connect(archon, SIGNAL(msgStatus(RMap)), this, SLOT(msgStatus(RMap)));
	connect(archon, SIGNAL(msgFrameStatus(RMap)), this, SLOT(msgFrameStatus(RMap)));
	connect(archon, SIGNAL(msgConnected(bool)), this, SLOT(msgConnected(bool)));
	connect(archon, SIGNAL(newFrame()), this, SLOT(newFrame()));
	archon->init();

	// Start timer for polling at 5Hz
	updateTimer = new TUpdateTimer(this);
	connect(updateTimer, SIGNAL(update()), this, SLOT(poll()));
	updateTimer->startUpdateTimer(500);

	// Allocate frame buffers
	archon->frames.resize(2);

	// Create test frame
	displayframe = -1;
	displayindex = -1;
	int w = 16, h = 16;
	lastw = lasth = 0;
//	archon->frames[0].setSize(w, h, true);
//	unsigned *data32 = (unsigned *)archon->frames[0].Data;
//	for (x = 0; x < w; x++)
//		for (y = 0; y < h; y++)
//			data32[y * w + x] = (y << 28) | (x << 24);
	archon->frames[0].setSize(w, h, false);
	for (x = 0; x < w; x++)
		for (y = 0; y < h; y++)
			archon->frames[0].Data[y * w + x] = (y << 12) | (x << 8);
	archon->frames[0].Frame = 0;
	dv = 0;
	newFrame();
	fetchedframe = -1;
	if (openFrame(loadFilename))
	{
		twTabs->setCurrentIndex(6);
		QList<int> l;
		l << 0 << 1;
		splitter->setSizes(l);
		this->showMaximized();
	}
}
//---------------------------------------------------------------------------
TArchonGUI::~TArchonGUI()
{
	updateTimer->stopUpdateTimer();
	delete archon;
}
//---------------------------------------------------------------------------
void TArchonGUI::showAbout()
{
	QMessageBox mb;
	mb.setWindowTitle("About " + GUIVersion);
	mb.setText("Archon GUI is Copyright (c) 2020 Semiconductor Technology Associates, Inc.\n\n"
			   "Archon GUI uses the Qt Toolkit, "
			   "Copyright (c) 2013 Digia PLC and/or its subsidiary(-ies) and other contributors.  "
			   "Qt is available under the GNU Lesser General Public License, version 2.1 (LGPL).  "
			   "A copy of the LGPL is provided with Archon GUI in the file \"LICENSE.LGPL\".\n\n"
			   "Archon GUI is based in part on the work of the Qwt project (http://qwt.sf.net)."
			   );
	mb.exec();
}
//---------------------------------------------------------------------------
void TArchonGUI::openFile()
{
	QStringList keys;

	sConfigFilename.replace(".ncf", ".acf", Qt::CaseInsensitive);
	QString filename = QFileDialog::getOpenFileName(this,
		"Load Archon Configuration", sConfigFilename, "Archon Configuration Files (*.acf)");
	if (filename.isEmpty())
		return;
	sConfigFilename	= filename;
	QSettings ini(filename, QSettings::IniFormat);

	system.clear();
	ini.beginGroup("SYSTEM");
	keys = ini.allKeys();
	for (int i = 0; i < keys.count(); i++)
		system.insert(keys[i], ini.value(keys[i]).toString());
	ini.endGroup();
	parseSystem();

	config.clear();
	ini.beginGroup("CONFIG");
	keys = ini.allKeys();
	for (int i = 0; i < keys.count(); i++)
		config.insert(keys[i], ini.value(keys[i]).toString());
	ini.endGroup();
	updateUI();
}
//---------------------------------------------------------------------------
void TArchonGUI::saveFile()
{
	RMap::const_iterator it;

	sConfigFilename.replace(".ncf", ".acf", Qt::CaseInsensitive);
	QString filename = QFileDialog::getSaveFileName(this,
		"Save Archon Configuration", sConfigFilename, "Archon Configuration Files (*.acf)");
	if (filename.isEmpty())
		return;
	sConfigFilename	= filename;
	if (parseUI())
		return;
	QSettings ini(filename, QSettings::IniFormat);

	ini.beginGroup("SYSTEM");
	it = system.begin();
	while (it != system.end())
	{
		ini.setValue(it.key(), it.value());
		++it;
	}
	ini.endGroup();

	ini.beginGroup("CONFIG");
	it = config.begin();
	while (it != config.end())
	{
		ini.setValue(it.key(), it.value());
		++it;
	}
	ini.endGroup();
}
//---------------------------------------------------------------------------
void TArchonGUI::openNiceFile()
{
	int i, j;
	QString s;

	sConfigFilename.replace(".acf", ".ncf", Qt::CaseInsensitive);
	QString filename = QFileDialog::getOpenFileName(this,
		"Load Archon Configuration", sConfigFilename, "Archon Configuration Files (*.ncf)");
	if (filename.isEmpty())
		return;
	sConfigFilename	= filename;

	QFile f(filename);
	if (!f.open(QIODevice::ReadOnly))
		return;
	QTextStream ts(&f);

	// Find [SYSTEM] header
	while (1)
	{
		s = ts.readLine();
		if (s.isNull())
			goto done;
		if (s == "[SYSTEM]")
			break;
	}
	// Read [SYSTEM] contents
	system.clear();
	while (1)
	{
		s = ts.readLine();
		if (s.isNull())
			goto done;
		if (s == "[CONFIG]")
			break;
		i = s.indexOf('=');
		if (i > 0)
			system.insert(s.left(i), s.mid(i + 1));
	}
	// Read [CONFIG] contents
	config.clear();
	while (1)
	{
		s = ts.readLine();
		if (s.isNull())
			goto done;
		if (s == "[TIMINGSCRIPT]")
			break;
		i = s.indexOf('=');
		if (i > 0)
			config.insert(s.left(i), s.mid(i + 1));
	}
	// Read [TIMINGSCRIPT] contents
	i = 0;
	teScript->clear();
	while (1)
	{
		s = ts.readLine();
		if (s.isNull())
			goto done;
		if (s == "[PARAMETERS]")
			break;
		config.insert(QString("LINE%1").arg(i++), s);
	}
	config.insert("LINES", QString::number(i));
	// Read [PARAMETERS] contents
	i = 0;
	teParameters->clear();
	while (1)
	{
		s = ts.readLine();
		if (s.isNull())
			goto done;
		if (s == "[CONSTANTS]")
			break;
		config.insert(QString("PARAMETER%1").arg(i++), s);
	}
	config.insert("PARAMETERS", QString::number(i));
	// Read [CONSTANTS] contents
	i = 0;
	teConstants->clear();
	while (1)
	{
		s = ts.readLine();
		if (s.isNull())
			goto done;
		if (s == "[TAPLINES]")
			break;
		config.insert(QString("CONSTANT%1").arg(i++), s);
	}
	config.insert("CONSTANTS", QString::number(i));
	// Read [TAPLINES] contents
	i = 0;
	teTapOrder->clear();
	while (1)
	{
		s = ts.readLine();
		if (s.isNull())
			goto done;
		if (s.startsWith("["))
			break;
		config.insert(QString("TAPLINE%1").arg(i++), s);
	}
	config.insert("TAPLINES", QString::number(i));
	// Read [STATE] contents
	i = 0;
	while (1)
	{
		if (s != "[STATE]")
			break;
		while (1)
		{
			s = ts.readLine();
			if (s.isNull())
				goto done;
			if (s.startsWith("["))
				break;
			j = s.indexOf('=');
			if (j > 0)
				config.insert(QString("STATE%1/").arg(i) + s.left(j), s.mid(j + 1));
		}
		i++;
	}
	config.insert("STATES", QString::number(i));
	// Read [VCPUx] contents
	while (1)
	{
		if (s.left(5) != "[VCPU")
			break;
		i = s.mid(5).section(']', 0, 0).toInt();
		j = 0;
		while (1)
		{
			s = ts.readLine();
			if (s.isNull())
				goto done;
			if (s.startsWith("["))
				break;
			config.insert(QString("MOD%1/VCPU_LINE%2").arg(i).arg(j++), s);
		}
		config.insert(QString("MOD%1/VCPU_LINES").arg(i), QString::number(j));
	}

done:
	f.close();
	parseSystem();
	updateUI();
}
//---------------------------------------------------------------------------
void TArchonGUI::saveNiceFile()
{
	RMap::iterator it;
	int i, j, count;
	QStringList sl;
	QVariantMap map;
	QVariantMap::iterator vit;
	QCollator collator;

	collator.setNumericMode(true);
	sConfigFilename.replace(".acf", ".ncf", Qt::CaseInsensitive);
	QString filename = QFileDialog::getSaveFileName(this,
		"Save Archon Configuration", sConfigFilename, "Archon Configuration Files (*.ncf)");
	if (filename.isEmpty())
		return;
	sConfigFilename	= filename;
	if (parseUI())
		return;

	QFile f(filename);
	if (!f.open(QIODevice::WriteOnly))
		return;
	QTextStream ts(&f);

	// System configuration
	ts << "[SYSTEM]" << QT_ENDL;
	sl.clear();
	it = system.begin();
	while (it != system.end())
	{
		sl.append(it.key() + "=" + it.value());
		++it;
	}
	std::sort(sl.begin(), sl.end(), collator);
	for (i = 0; i < sl.count(); i++)
		ts << sl[i] << QT_ENDL;

	// Configuration keys
	ts << QT_ENDL << "[CONFIG]" << QT_ENDL;
	sl.clear();
	it = config.begin();
	while (it != config.end())
	{
		// Skip lists, record all other keys
		if (
				(it.key().left(9) == "LINECOUNT") || (
				(it.key().left(7) != "TAPLINE") && (it.key().left(4) != "LINE") &&
				(it.key().left(8) != "CONSTANT") && (it.key().left(9) != "PARAMETER") &&
				(it.key().left(5) != "STATE") && (!it.key().contains("VCPU_LINE"))))
			sl.append(it.key() + "=" + it.value());
		++it;
	}
	std::sort(sl.begin(), sl.end(), collator);
	for (i = 0; i < sl.count(); i++)
		ts << sl[i] << QT_ENDL;

	// Timing script lines
	ts << QT_ENDL << "[TIMINGSCRIPT]" << QT_ENDL;
	sl = teScript->toPlainText().split('\n');
	count = sl.count();
	for (i = 0; i < count; i++)
		ts << sl[i] << QT_ENDL;

	// Parameters
	ts << "[PARAMETERS]" << QT_ENDL;
	sl = teParameters->toPlainText().split('\n');
	count = sl.count();
	for (i = 0; i < count; i++)
		ts << sl[i] << QT_ENDL;

	// Constants
	ts << "[CONSTANTS]" << QT_ENDL;
	sl = teConstants->toPlainText().split('\n');
	count = sl.count();
	for (i = 0; i < count; i++)
		ts << sl[i] << QT_ENDL;

	// Tap lines
	ts << "[TAPLINES]" << QT_ENDL;
	sl = teTapOrder->toPlainText().split('\n');
	count = sl.count();
	for (i = 0; i < count; i++)
		ts << sl[i] << QT_ENDL;

	// Timing states
	count = lwStates->count();
	for (i = 0; i < count; i++)
	{
		ts << "[STATE]" << QT_ENDL;
		sl.clear();
		map = lwStates->item(i)->data(Qt::UserRole).toMap();
		vit = map.begin();
		while (vit != map.end())
		{
			sl.append(vit.key() + "=" + vit.value().toString());
			++vit;
		}
		std::sort(sl.begin(), sl.end(), collator);
		for (j = 0; j < sl.count(); j++)
			ts << sl[j] << QT_ENDL;
	}

	// VCPU code
	for (i = 1; i < MAX_MODULES; i++)
	{
		count = config[QString("MOD%1/VCPU_LINES").arg(i)].toInt();
		if (count <= 0)
			continue;
		ts << "[VCPU" << i << "]" << QT_ENDL;
		for (j = 0; j < count; j++)
			ts << config[QString("MOD%1/VCPU_LINE%2").arg(i).arg(j)] << QT_ENDL;
	}

	ts << "[END]" << QT_ENDL;
	f.close();
}
//---------------------------------------------------------------------------
void TArchonGUI::applyAll()
{
	int e;

	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	parseUI();
	archon->getResult();
	archon->setConfig(config);
	e = archon->getResult();
	if (!e)
	{
		archon->command("APPLYALL");
		archon->getResult();
	}
}
//---------------------------------------------------------------------------
void TArchonGUI::loadTiming()
{
	int e;

	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	parseUI();
	archon->getResult();
	archon->setConfig(config);
	e = archon->getResult();
	if (!e)
	{
		archon->command("LOADTIMING");
		archon->getResult();
	}
}
//---------------------------------------------------------------------------
void TArchonGUI::loadParameters()
{
	int e;

	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	parseUI();
	archon->getResult();
	archon->setConfig(config);
	e = archon->getResult();
	if (!e)
	{
		archon->command("LOADPARAMS");
		archon->getResult();
	}
}
//---------------------------------------------------------------------------
void TArchonGUI::test()
{
	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	archon->getResult();
	archon->command("LOADPARAM", "Exposures");
	archon->getResult();
}
//---------------------------------------------------------------------------
void TArchonGUI::resetTiming()
{
	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	archon->getResult();
	archon->command("RESETTIMING");
	archon->getResult();
}
//---------------------------------------------------------------------------
void TArchonGUI::holdTiming()
{
	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	archon->getResult();
	archon->command("HOLDTIMING");
	archon->getResult();
}
//---------------------------------------------------------------------------
void TArchonGUI::releaseTiming()
{
	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	archon->getResult();
	archon->command("RELEASETIMING");
	archon->getResult();
}
//---------------------------------------------------------------------------
void TArchonGUI::applySystem()
{
	int e;

	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	parseUI();
	archon->getResult();
	archon->setConfig(config);
	e = archon->getResult();
	if (!e)
	{
		archon->command("APPLYSYSTEM");
		archon->getResult();
	}
}
//---------------------------------------------------------------------------
void TArchonGUI::applyCDS()
{
	int e;

	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	parseUI();
	archon->getResult();
	archon->setConfig(config);
	e = archon->getResult();
	if (!e)
	{
		archon->command("APPLYCDS");
		archon->getResult();
	}
}
//---------------------------------------------------------------------------
void TArchonGUI::applyModule(int slot)
{
	int e;
	QString s;

	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	parseUI();
	archon->getResult();
	archon->setConfig(config);
	e = archon->getResult();
	if (!e)
	{
		archon->command("APPLYMOD", QString::number(slot - 1));
		archon->getResult();
	}
}
//---------------------------------------------------------------------------
void TArchonGUI::applyModuleDIO(int slot)
{
	int e;
	QString s;

	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	parseUI();
	archon->getResult();
	archon->setConfig(config);
	e = archon->getResult();
	if (!e)
	{
		archon->command("APPLYDIO", QString::number(slot - 1));
		archon->getResult();
	}
}
//---------------------------------------------------------------------------
void TArchonGUI::direct(QString cmd)
{
	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	archon->getResult();
	archon->command("DIRECT", cmd);
	archon->getResult();
}
//---------------------------------------------------------------------------
void TArchonGUI::moduleCommand(int slot, QString cmd, QStringList params)
{
	QStringList sl;

	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	parseUI();
	archon->getResult();
	sl.append(QString::number(slot - 1));
	sl.append(params);
	archon->command(cmd, sl);
	archon->getResult();
}
//---------------------------------------------------------------------------
void TArchonGUI::fetchFrame(int frame)
{
	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	archon->getResult();
	archon->command("LOCK", QString::number(frame + 1));
	archon->getResult();
	archon->command("FETCH");
}
//---------------------------------------------------------------------------
void TArchonGUI::powerOn()
{
	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	archon->getResult();
	archon->command("POWERON");
}
//---------------------------------------------------------------------------
void TArchonGUI::powerOff()
{
	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	archon->getResult();
	archon->command("POWEROFF");
}
//---------------------------------------------------------------------------
void TArchonGUI::pollOn()
{
	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	archon->getResult();
	archon->command("POLLON");
}
//---------------------------------------------------------------------------
void TArchonGUI::pollOff()
{
	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	archon->getResult();
	archon->command("POLLOFF");
}
//---------------------------------------------------------------------------
void TArchonGUI::logMessage(const QString& msg)
{
	telog->appendPlainText(msg);
}
//---------------------------------------------------------------------------
void TArchonGUI::progressMessage(const QString& msg, int newstep, int newtotal)
{
	StatusLabel->setText(msg);
	spProgress->setProgress(newstep, newtotal);
}
//---------------------------------------------------------------------------
void TArchonGUI::msgSystem(const RMap &data)
{
	system = data;
	parseSystem();

//	QString s;
//	QMapIterator<QString, QString> i(data);
//	while (i.hasNext()) {
//		i.next();
//		s = i.key() + ": " + i.value();
//		logMessage(s);
//	}
}
//---------------------------------------------------------------------------
void TArchonGUI::parseSystem()
{
	int i, j, id, build;
	QString s;
	bool ok;
	QWidget *tab;

	i = system.value("BACKPLANE_TYPE").toInt();
	if (i == BACKPLANE_TYPE_X12)
	{
		mod_count = 12;
		backplane_type->setText("Backplane X12");
	}
	else if (i == BACKPLANE_TYPE_X16)
	{
		mod_count = 16;
		backplane_type->setText("Backplane X16");
	}
	else
		goto error;
	j = system.value("BACKPLANE_REV").toInt(&ok);
	if (!ok || (j < 0)) goto error;
	backplane_rev->setText(QString(QLatin1Char('A' + j)));
	s = system.value("BACKPLANE_VERSION");
	backplane_ver->setText(s);
	build = s.section('.',2).toInt();
	backplane_id->setText(system.value("BACKPLANE_ID"));
	power_id->setText(system.value("POWER_ID"));

	// Show all optional GUI elements
	fan_speed->show();
	fan_speed_label->show();
	ext_clock_present->show();
	ext_clock_present_label->show();
	cbFanDisable->show();
	cbApplyAll->show();
	cbPowerOn->show();
	cbExternalClock->show();
	cbTrigOutPower->show();
	cbTrigInEdge->show();
	adxrawlabel->show();
	adxraw->show();
	adxcdslabel->show();
	adxcds->show();
	linescanlabel->show();
	linescan->show();
	// Hide unused GUI elements
	if (i == BACKPLANE_TYPE_X12)
	{
		if (build < 1042)
		{
			cbApplyAll->hide();
			cbPowerOn->hide();
		}
		if (build < 1179)
			cbTrigInEdge->hide();
		if (j < 4)
		{
			adxrawlabel->hide();
			adxraw->hide();
			adxcdslabel->hide();
			adxcds->hide();
			pclkdelaylabel->hide();
			pclkdelay->hide();
			linescanlabel->hide();
			linescan->hide();
		}
		if (j < 5)
		{
			fan_speed->hide();
			fan_speed_label->hide();
			ext_clock_present->hide();
			ext_clock_present_label->hide();
			cbFanDisable->hide();
		}
		if (j >= 4)
		{
			cbExternalClock->hide();
			if (build < 930)
			{
				adxrawlabel->hide();
				adxraw->hide();
				adxcdslabel->hide();
				adxcds->hide();
				pclkdelaylabel->hide();
				pclkdelay->hide();
			}
			if (build < 1028)
			{
				linescanlabel->hide();
				linescan->hide();
			}
		}
		if (j >= 5)
		{
			cbTrigOutPower->hide();
		}
	}
	else if (i == BACKPLANE_TYPE_X16)
	{
		fan_speed->hide();
		fan_speed_label->hide();
		ext_clock_present->hide();
		ext_clock_present_label->hide();
		cbFanDisable->hide();
		cbApplyAll->hide();
		cbPowerOn->hide();
		cbExternalClock->hide();
		adxrawlabel->hide();
		adxraw->hide();
		adxcdslabel->hide();
		adxcds->hide();
		pclkdelaylabel->hide();
		pclkdelay->hide();
		linescanlabel->hide();
		linescan->hide();
	}

	// Only show available slots
	for (i = 0; i < MAX_MODULES; i++)
	{
		if (i < mod_count)
		{
			id = system.value(QString("MOD%1_TYPE").arg(i + 1)).toInt();
			if ((id <= MOD_TYPE_NONE) || (id >= MOD_TYPE_UNKNOWN))
			{
				if (id == MOD_TYPE_NONE)
					mod_type[i]->setText("Empty");
				else
					mod_type[i]->setText("Unknown");
				mod_rev[i]->clear();
				mod_ver[i]->clear();
				mod_id[i]->clear();
			}
			else
			{
				switch (id)
				{
					case MOD_TYPE_DRIVER: mod_type[i]->setText("Driver"); break;
					case MOD_TYPE_DRIVERX: mod_type[i]->setText("DriverX"); break;
					case MOD_TYPE_AD: mod_type[i]->setText("AD"); break;
					case MOD_TYPE_LVBIAS: mod_type[i]->setText("LV Bias"); break;
					case MOD_TYPE_HVBIAS: mod_type[i]->setText("HV Bias"); break;
					case MOD_TYPE_HEATER: mod_type[i]->setText("Heater"); break;
					case MOD_TYPE_ATLAS: mod_type[i]->setText("Atlas"); break;
					case MOD_TYPE_HS: mod_type[i]->setText("HS"); break;
					case MOD_TYPE_HVXBIAS: mod_type[i]->setText("HVX Bias"); break;
					case MOD_TYPE_LVXBIAS: mod_type[i]->setText("LVX Bias"); break;
					case MOD_TYPE_LVDS: mod_type[i]->setText("LVDS"); break;
					case MOD_TYPE_HEATERX: mod_type[i]->setText("HeaterX"); break;
					case MOD_TYPE_XVBIAS: mod_type[i]->setText("XV Bias"); break;
					case MOD_TYPE_ADF: mod_type[i]->setText("ADF"); break;
					case MOD_TYPE_ADX: mod_type[i]->setText("ADX"); break;
					case MOD_TYPE_ADLN: mod_type[i]->setText("ADLN"); break;
					case MOD_TYPE_ADM: mod_type[i]->setText("ADM"); break;
				}
				id = system.value(QString("MOD%1_REV").arg(i + 1)).toInt(&ok);
				if (!ok || (id < 0))
					mod_rev[i]->setText("?");
				else
					mod_rev[i]->setText(QString(QLatin1Char('A' + id)));
				mod_ver[i]->setText(system.value(QString("MOD%1_VERSION").arg(i + 1)));
				mod_id[i]->setText(system.value(QString("MOD%1_ID").arg(i + 1)));
			}
			mod_temp[i]->clear();
			mod_slot[i]->show();
			mod_type[i]->show();
			mod_rev[i]->show();
			mod_ver[i]->show();
			mod_id[i]->show();
			mod_temp[i]->show();
			actionFlashModule[i]->setVisible(true);
		}
		else
		{
			mod_slot[i]->hide();
			mod_type[i]->hide();
			mod_rev[i]->hide();
			mod_ver[i]->hide();
			mod_id[i]->hide();
			mod_temp[i]->hide();
			actionFlashModule[i]->setVisible(false);
		}
	}
	// Clear system tabs and waveform tabs
	while (twTabs->count() > fixedTabs)
	{
		tab = twTabs->widget(fixedTabs);
		twTabs->removeTab(fixedTabs);
		tab->deleteLater();
	}
	while (twModuleSignalTabs->count() > 1)
	{
		tab = twModuleSignalTabs->widget(1);
		twModuleSignalTabs->removeTab(1);
		tab->deleteLater();
	}
	while (twModuleVCPUTabs->count() > 0)
	{
		tab = twModuleVCPUTabs->widget(0);
		twModuleVCPUTabs->removeTab(0);
		tab->deleteLater();
	}
	// Add daughter boards
	for (i = 0; i < mod_count; i++)
	{
		if (modules[i])
		{
			delete modules[i];
			modules[i] = NULL;
		}
		id = system.value(QString("MOD%1_TYPE").arg(i + 1)).toInt();
		if ((id <= MOD_TYPE_NONE) || (id >= MOD_TYPE_UNKNOWN))
			continue;
		switch (id)
		{
		case MOD_TYPE_DRIVER: modules[i] = new DRIVER(this, QString("MOD%1").arg(i + 1), i + 1); break;
		case MOD_TYPE_DRIVERX: modules[i] = new DRIVERX(this, QString("MOD%1").arg(i + 1), i + 1); break;
		case MOD_TYPE_AD: modules[i] = new AD(this, QString("MOD%1").arg(i + 1), i + 1); break;
		case MOD_TYPE_LVXBIAS:
		case MOD_TYPE_LVBIAS: modules[i] = new LVBIAS(this, QString("MOD%1").arg(i + 1), i + 1); break;
		case MOD_TYPE_HVXBIAS:
		case MOD_TYPE_HVBIAS: modules[i] = new HVBIAS(this, QString("MOD%1").arg(i + 1), i + 1); break;
		case MOD_TYPE_HEATER: modules[i] = new HEATER(this, QString("MOD%1").arg(i + 1), i + 1); break;
		case MOD_TYPE_ATLAS: modules[i] = new ATLAS(this, QString("MOD%1").arg(i + 1), i + 1); break;
		case MOD_TYPE_HS: modules[i] = new HS(this, QString("MOD%1").arg(i + 1), i + 1); break;
		case MOD_TYPE_LVDS: modules[i] = new LVDS(this, QString("MOD%1").arg(i + 1), i + 1); break;
		case MOD_TYPE_HEATERX: modules[i] = new HEATERX(this, QString("MOD%1").arg(i + 1), i + 1); break;
		case MOD_TYPE_XVBIAS: modules[i] = new XVBIAS(this, QString("MOD%1").arg(i + 1), i + 1); break;
		case MOD_TYPE_ADF: modules[i] = new ADF(this, QString("MOD%1").arg(i + 1), i + 1); break;
		case MOD_TYPE_ADX: modules[i] = new ADX(this, QString("MOD%1").arg(i + 1), i + 1); break;
		case MOD_TYPE_ADLN: modules[i] = new ADLN(this, QString("MOD%1").arg(i + 1), i + 1); break;
		case MOD_TYPE_ADM: modules[i] = new ADM(this, QString("MOD%1").arg(i + 1), i + 1); break;
		}
		if (modules[i])
			modules[i]->createUI();
	}
	// Sync timing state GUI with current settings
	stateChanged();

	system_valid = true;
	return;
error:
	system_valid = false;
	logMessage("Error parsing system configuration");
}
//---------------------------------------------------------------------------
void TArchonGUI::msgStatus(const RMap &data)
{
	status = data;
	parseStatus();

//	QString s;
//	QMapIterator<QString, QString> i(data);
//	while (i.hasNext()) {
//		i.next();
//		s = i.key() + ": " + i.value();
//		logMessage(s);
//	}
//	QString filename = "templog.txt";
//	bool first = !QFile::exists(filename);
//	QFile file(filename);
//	if (!file.open(QFile::ReadWrite | QFile::Append))
//		return;
//	QTextStream ts(&file);
//	if (first)
//		ts << "Time\tHeaterX Temp\tRTD Temp\tRef Temp\r\n";
//	ts << QDateTime::currentDateTimeUtc().toString("yyyy-MM-ddThh:mm:ss.zzz") << "\t";
//	ts << data.value("MOD4/TEMP", "-") << "\t";
//	ts << data.value("MOD4/TEMPB", "-") << "\t";
//	ts << data.value("MOD4/TEMPBREF", "-") << "\r\n";
}
//---------------------------------------------------------------------------
void TArchonGUI::parseStatus()
{
	int i;
	unsigned u;
	double d;
	bool ok;
	QString s;

	i = status.value("VALID", "-").toInt(&ok);
	if (ok)
		status_valid->setText(QString::number(i));
	u = status.value("COUNT", "-").toUInt(&ok);
	if (ok)
		status_count->setText(QString::number(u));
	u = status.value("FANTACH", "-").toUInt(&ok);
	if (!ok)
		u = 0;
	fan_speed->setText(QString::number(u));
	u = status.value("EXTCLKPRESENT", "-").toUInt(&ok);
	if (!ok)
		u = 0;
	ext_clock_present->setText(u ? "Present" : "Absent");
	u = status.value("POWER", "-").toUInt(&ok);
	if (ok)
	{
		if (u == PWR_NOT_CONFIGURED)
		{
			wPower->setToolTip("NOT CONFIGURED");
			wPower->setColor(Qt::gray);
		}
		else if (u == PWR_OFF)
		{
			wPower->setToolTip("OFF");
			wPower->setColor(Qt::red);
		}
		else if (u == PWR_INTERMEDIATE)
		{
			wPower->setToolTip("INTERMEDIATE");
			wPower->setColor(Qt::yellow);
		}
		else if (u == PWR_ON)
		{
			wPower->setToolTip("ON");
			wPower->setColor(Qt::green);
		}
		else if (u == PWR_STANDBY)
		{
			wPower->setToolTip("STANDBY");
			wPower->setColor(Qt::blue);
			return;
		}
		else
		{
			wPower->setToolTip("UNKNOWN");
			wPower->setColor(Qt::darkGray);
		}
	}
	else
	{
		wPower->setToolTip("UNKNOWN");
		wPower->setColor(Qt::darkGray);
	}
	d = status.value("BACKPLANE_TEMP").toDouble(&ok);
	if (ok)
		backplane_temp->setText(flt(d, 0, 1) + " C");

	s = "";
	u = status.value("OVERHEAT", "-").toUInt(&ok);
	if (ok && (u == 1))
		s.append("OVERHEAT ");
	u = status.value("POWERGOOD", "-").toUInt(&ok);
	if (ok && (u == 0))
		s.append("POWERFAIL ");
	power_flags->setText(s);
	d = status.value("P2V5_V", "0").toDouble(&ok);
	if (ok)
		p2v5_v->setText(flt(d, 7, 3));
	d = status.value("P2V5_I", "0").toDouble(&ok);
	if (ok)
		p2v5_i->setText(flt(d, 7, 3));
	d = status.value("P5V_V", "0").toDouble(&ok);
	if (ok)
		p5v_v->setText(flt(d, 7, 3));
	d = status.value("P5V_I", "0").toDouble(&ok);
	if (ok)
		p5v_i->setText(flt(d, 7, 3));
	d = status.value("P6V_V", "0").toDouble(&ok);
	if (ok)
		p6v_v->setText(flt(d, 7, 3));
	d = status.value("P6V_I", "0").toDouble(&ok);
	if (ok)
		p6v_i->setText(flt(d, 7, 3));
	d = status.value("N6V_V", "0").toDouble(&ok);
	if (ok)
		n6v_v->setText(flt(d, 7, 3));
	d = status.value("N6V_I", "0").toDouble(&ok);
	if (ok)
		n6v_i->setText(flt(d, 7, 3));
	d = status.value("P17V_V", "0").toDouble(&ok);
	if (ok)
		p17v_v->setText(flt(d, 7, 3));
	d = status.value("P17V_I", "0").toDouble(&ok);
	if (ok)
		p17v_i->setText(flt(d, 7, 3));
	d = status.value("N17V_V", "0").toDouble(&ok);
	if (ok)
		n17v_v->setText(flt(d, 7, 3));
	d = status.value("N17V_I", "0").toDouble(&ok);
	if (ok)
		n17v_i->setText(flt(d, 7, 3));
	d = status.value("P35V_V", "0").toDouble(&ok);
	if (ok)
		p35v_v->setText(flt(d, 7, 3));
	d = status.value("P35V_I", "0").toDouble(&ok);
	if (ok)
		p35v_i->setText(flt(d, 7, 3));
	d = status.value("N35V_V", "0").toDouble(&ok);
	if (ok)
		n35v_v->setText(flt(d, 7, 3));
	d = status.value("N35V_I", "0").toDouble(&ok);
	if (ok)
		n35v_i->setText(flt(d, 7, 3));
	d = status.value("P100V_V", "0").toDouble(&ok);
	if (ok)
		p100v_v->setText(flt(d, 7, 3));
	d = status.value("P100V_I", "0").toDouble(&ok);
	if (ok)
		p100v_i->setText(flt(d, 7, 3));
	d = status.value("N100V_V", "0").toDouble(&ok);
	if (ok)
		n100v_v->setText(flt(d, 7, 3));
	d = status.value("N100V_I", "0").toDouble(&ok);
	if (ok)
		n100v_i->setText(flt(d, 7, 3));
	d = status.value("USER_V", "0").toDouble(&ok);
	if (ok)
		user_v->setText(flt(d, 7, 3));
	d = status.value("USER_I", "0").toDouble(&ok);
	if (ok)
		user_i->setText(flt(d, 7, 3));
	d = status.value("HEATER_V", "0").toDouble(&ok);
	if (ok)
		heater_v->setText(flt(d, 7, 3));
	d = status.value("HEATER_I", "0").toDouble(&ok);
	if (ok)
		heater_i->setText(flt(d, 7, 3));

	for (i = 0; i < MAX_MODULES; i++)
	{
		if (i < mod_count)
		{
			d = status.value(QString("MOD%1/TEMP").arg(i + 1)).toDouble(&ok);
			if (ok)
				mod_temp[i]->setText(flt(d, 0, 1) + " C");
			if (modules[i])
				modules[i]->parseStatus(status);
		}
	}
}
//---------------------------------------------------------------------------
void TArchonGUI::msgFrameStatus(const RMap &data)
{
//		QString s;
//		QMapIterator<QString, QString> i(data);
//		while (i.hasNext()) {
//			i.next();
//			s = i.key() + ": " + i.value();
//			logMessage(s);
//		}
	frameStatus = data;
	parseFrameStatus();
}
//---------------------------------------------------------------------------
void TArchonGUI::parseFrameStatus()
{
	int i, rbuf, wbuf;
	QString s;
	int frames[3];
	bool framecomplete[3];
	int newestframe, newestbuf;

	rbuf = frameStatus.value("RBUF", "-").toInt() - 1;
	wbuf = frameStatus.value("WBUF", "-").toInt() - 1;
	for (i = 0; i < 3; i++)
	{
		frames[i] = frameStatus.value(QString("BUF%1FRAME").arg(i + 1), "-").toInt();
		bufframes[i]->setText(frameStatus.value(QString("BUF%1FRAME").arg(i + 1), "-"));
		bufwidths[i]->setText(frameStatus.value(QString("BUF%1WIDTH").arg(i + 1), "-"));
		bufheights[i]->setText(frameStatus.value(QString("BUF%1HEIGHT").arg(i + 1), "-"));
		bufpixels[i]->setText(frameStatus.value(QString("BUF%1PIXELS").arg(i + 1), "-"));
		buflines[i]->setText(frameStatus.value(QString("BUF%1LINES").arg(i + 1), "-"));
		bufrawblocks[i]->setText(frameStatus.value(QString("BUF%1RAWBLOCKS").arg(i + 1), "-"));
		bufrawlines[i]->setText(frameStatus.value(QString("BUF%1RAWLINES").arg(i + 1), "-"));
		s.clear();
		if (rbuf == i)
			s.append("R");
		if (wbuf == i)
			s.append("W");
		if (frameStatus.value(QString("BUF%1COMPLETE").arg(i + 1), "-") == "1")
		{
			s.append("C");
			framecomplete[i] = true;
		}
		else
			framecomplete[i] = false;
		bufstate[i]->setText(s);
	}
	// Look for newest frame available
	newestframe = -1;
	newestbuf = -1;
	for (i = 0; i < 3; i++)
	{
		if ((frames[i] > newestframe) && framecomplete[i])
		{
			newestframe = frames[i];
			newestbuf = i;
		}
	}
	// Fetch newest frame if necessary
	if (cbAutoFetch->isChecked() && (newestframe != fetchedframe) && (newestbuf >= 0))
	{
		fetchedframe = newestframe;
		fetchFrame(newestbuf);
	}
}
//---------------------------------------------------------------------------
int TArchonGUI::parseUI()
{
	int i, count;
	QStringList sl;
	QVariantMap map;
	QVariantMap::const_iterator it;

	config.clear();

	// System
	config.insert("TRIGOUTFORCE", cbTrigOutForce->isChecked() ? "1" : "0");
	config.insert("TRIGOUTLEVEL", cbTrigOutLevel->isChecked() ? "1" : "0");
	config.insert("TRIGOUTINVERT", cbTrigOutInvert->isChecked() ? "1" : "0");
	if (!cbTrigOutPower->isHidden())
		config.insert("TRIGOUTPOWER", cbTrigOutPower->isChecked() ? "1" : "0");
	config.insert("TRIGINENABLE", cbTrigInEnable->isChecked() ? "1" : "0");
	config.insert("TRIGININVERT", cbTrigInInvert->isChecked() ? "1" : "0");
	if (!cbTrigInEdge->isHidden())
		config.insert("TRIGINEDGE", cbTrigInEdge->isChecked() ? "1" : "0");
	if (!cbExternalClock->isHidden())
		config.insert("EXTCLOCK", cbExternalClock->isChecked() ? "1" : "0");
	if (!cbFanDisable->isHidden())
		config.insert("FANDISABLE", cbFanDisable->isChecked() ? "1" : "0");
	if (!cbApplyAll->isHidden())
		config.insert("APPLYALL", cbApplyAll->isChecked() ? "1" : "0");
	if (!cbPowerOn->isHidden())
		config.insert("POWERON", cbPowerOn->isChecked() ? "1" : "0");
	config.insert("IP", leIP->text());

	// CDS / Deinterlacing
	config.insert("SHP1", shp1->text());
	config.insert("SHP2", shp2->text());
	config.insert("SHD1", shd1->text());
	config.insert("SHD2", shd2->text());
	if (!pclkdelay->isHidden())
		config.insert("PCLKDELAY", pclkdelay->text());
	config.insert("SAMPLEMODE", QString::number(samplemode->currentIndex()));
	config.insert("PIXELCOUNT", pixelcount->text());
	config.insert("LINECOUNT", linecount->text());
	config.insert("FRAMEMODE", QString::number(framemode->currentIndex()));
	config.insert("BIGBUF", bigBuffers->isChecked() ? "1" : "0");
	if (!adxraw->isHidden())
		config.insert("ADXRAW", adxraw->isChecked() ? "1" : "0");
	if (adxraw->isChecked())
		rawHPlot->setAxisTitle(QwtPlot::xBottom, "Sample (2.5ns)");
	else
		rawHPlot->setAxisTitle(QwtPlot::xBottom, "Sample (10ns)");
	if (!adxcds->isHidden())
		config.insert("ADXCDS", adxcds->isChecked() ? "1" : "0");
	if (!linescan->isHidden())
		config.insert("LINESCAN", linescan->isChecked() ? "1" : "0");
	config.insert("RAWENABLE", rawEnable->isChecked() ? "1" : "0");
	config.insert("RAWSEL", QString::number(rawsel->currentIndex()));
	config.insert("RAWSTARTLINE", rawStartLine->text());
	config.insert("RAWENDLINE", rawEndLine->text());
	config.insert("RAWSTARTPIXEL", rawStartPixel->text());
	config.insert("RAWSAMPLES", rawSamples->text());
	sl = teTapOrder->toPlainText().split('\n');
	count = sl.count();
	config.insert("TAPLINES", QString::number(count));
	for (i = 0; i < count; i++)
		config.insert(QString("TAPLINE%1").arg(i), sl[i]);

	// Modules
	for (i = 0; i < mod_count; i++)
	{
		if (!modules[i])
			continue;
		modules[i]->parseUI();
	}

	// Add timing script into config
	sl = teScript->toPlainText().split('\n');
	count = sl.count();
	config.insert("LINES", QString::number(count));
	for (i = 0; i < count; i++)
		config.insert(QString("LINE%1").arg(i), sl[i]);

	// Add timing states into config
	count = lwStates->count();
	config.insert("STATES", QString::number(count));
	for (i = 0; i < count; i++)
	{
		map = lwStates->item(i)->data(Qt::UserRole).toMap();
		it = map.begin();
		while (it != map.end())
		{
			config.insert(QString("STATE%1/").arg(i) + it.key(), it.value().toString());
			++it;
		}
		config.insert(QString("STATE%1/NAME").arg(i), lwStates->item(i)->text());
	}

	// Add timing parameters and constants into config
	sl = teParameters->toPlainText().split('\n');
	count = sl.count();
	config.insert("PARAMETERS", QString::number(count));
	for (i = 0; i < count; i++)
		config.insert(QString("PARAMETER%1").arg(i), sl[i]);
	sl = teConstants->toPlainText().split('\n');
	count = sl.count();
	config.insert("CONSTANTS", QString::number(count));
	for (i = 0; i < count; i++)
		config.insert(QString("CONSTANT%1").arg(i), sl[i]);

	return 0;
}
//---------------------------------------------------------------------------
void TArchonGUI::updateUI()
{
	int i, j, count;
	bool ok;
	QString s, base, key;
	QStringList sl;
	QVariantMap map;

	// System
	cbTrigOutForce->setChecked(config.value("TRIGOUTFORCE") == "1");
	cbTrigOutLevel->setChecked(config.value("TRIGOUTLEVEL") == "1");
	cbTrigOutInvert->setChecked(config.value("TRIGOUTINVERT") == "1");
	cbTrigOutPower->setChecked(config.value("TRIGOUTPOWER") == "1");
	cbTrigInEnable->setChecked(config.value("TRIGINENABLE") == "1");
	cbTrigInInvert->setChecked(config.value("TRIGININVERT") == "1");
	cbTrigInEdge->setChecked(config.value("TRIGINEDGE") == "1");
	cbExternalClock->setChecked(config.value("EXTCLOCK") == "1");
	cbFanDisable->setChecked(config.value("FANDISABLE") == "1");
	cbApplyAll->setChecked(config.value("APPLYALL") == "1");
	cbPowerOn->setChecked(config.value("POWERON") == "1");
	leIP->setText(config.value("IP", "10.0.0.2"));

	// CDS / Deinterlacing
	shp1->setText(config.value("SHP1", "0"));
	shp2->setText(config.value("SHP2", "0"));
	shd1->setText(config.value("SHD1", "0"));
	shd2->setText(config.value("SHD2", "0"));
	pclkdelay->setText(config.value("PCLKDELAY", "0"));
	samplemode->setCurrentIndex(qBound(0, config.value("SAMPLEMODE").toInt(), 1));
	pixelcount->setText(config.value("PIXELCOUNT", "0"));
	linecount->setText(config.value("LINECOUNT", "0"));
	framemode->setCurrentIndex(qBound(0, config.value("FRAMEMODE").toInt(), 2));
	bigBuffers->setChecked(config.value("BIGBUF") == "1");
	adxraw->setChecked(config.value("ADXRAW") == "1");
	if (adxraw->isChecked())
		rawHPlot->setAxisTitle(QwtPlot::xBottom, "Sample (2.5ns)");
	else
		rawHPlot->setAxisTitle(QwtPlot::xBottom, "Sample (10ns)");
	adxcds->setChecked(config.value("ADXCDS") == "1");
	linescan->setChecked(config.value("LINESCAN") == "1");
	rawEnable->setChecked(config.value("RAWENABLE") == "1");
	rawsel->setCurrentIndex(qBound(0, config.value("RAWSEL").toInt(), 15));
	rawStartLine->setText(config.value("RAWSTARTLINE", "0"));
	rawEndLine->setText(config.value("RAWENDLINE", "0"));
	rawStartPixel->setText(config.value("RAWSTARTPIXEL", "0"));
	rawSamples->setText(config.value("RAWSAMPLES", "0"));
	count = config.value("TAPLINES").toInt(&ok);
	if (ok)
	{
		teTapOrder->clear();
		for (i = 0; i < count; i++)
			teTapOrder->appendPlainText(config.value(QString("TAPLINE%1").arg(i)));
	}

	// Modules
	for (i = 0; i < mod_count; i++)
	{
		if (!modules[i])
			continue;
		modules[i]->updateUI();
	}

	// Timing script
	count = config.value("LINES").toInt(&ok);
	if (ok)
	{
		teScript->clear();
		for (i = 0; i < count; i++)
			teScript->appendPlainText(config.value(QString("LINE%1").arg(i)));
	}

	// Timing states
	count = config.value("STATES").toInt(&ok);
	if (ok)
	{
		QListWidgetItem *lwi;
		lwStates->clear();
		for (i = 0; i < count; i++)
		{
			lwi = new QListWidgetItem(config.value(QString("STATE%1/NAME").arg(i), ""));
			sl = config.keys();
			base = QString("STATE%1/").arg(i);
			map.clear();
			for (j = 0; j < sl.count(); j++)
			{
				key = sl[j];
				if (!key.startsWith(base))
					continue;
				key.remove(0, base.length());
				map.insert(key, config.value(sl[j]));
			}
			lwi->setData(Qt::UserRole, map);
			lwi->setFlags(lwi->flags() | Qt::ItemIsEditable);
			lwStates->addItem(lwi);
		}
		if (lwStates->count())
			lwStates->setCurrentRow(0, QItemSelectionModel::ClearAndSelect);
	}

	// Timing parameters
	count = config.value("PARAMETERS").toInt(&ok);
	if (ok)
	{
		teParameters->clear();
		for (i = 0; i < count; i++)
			teParameters->appendPlainText(config.value(QString("PARAMETER%1").arg(i)));
	}

	// Timing constants
	count = config.value("CONSTANTS").toInt(&ok);
	if (ok)
	{
		teConstants->clear();
		for (i = 0; i < count; i++)
			teConstants->appendPlainText(config.value(QString("CONSTANT%1").arg(i)));
	}
}
//---------------------------------------------------------------------------
void TArchonGUI::msgConnected(const bool connected)
{
	wPower->setToolTip("UNKNOWN");
	wPower->setColor(Qt::darkGray);
	this->connected = connected;
	if (connected)
	{
		archon->command("SYSTEM");
		connectButton->setText("Disconnect");
	}
	else
		connectButton->setText("Connect");
}
//---------------------------------------------------------------------------
void TArchonGUI::connectClicked()
{
	QStringList params;

	parseUI();
	archon->getResult();
	if (!connected)
	{
		params.append(leAddress->text());
		params.append(QString::number(4242));
		archon->command("CONNECT", params);
	}
	else
	{
		connected = false;
		archon->command("DISCONNECT");
	}
	archon->getResult();
}
//---------------------------------------------------------------------------
void TArchonGUI::flashClicked()
{
	QString filename;
	QStringList params;

	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	filename = QFileDialog::getOpenFileName(this,
		"Flash Archon PROM", sPROMFilename, "Archon PROM Files (*.mcs)");
	if (filename.isEmpty()) return;
	sPROMFilename = filename;
	params.append(filename);
	params.append(actionFlashBackplane->isChecked() ? "1" : "0");
	params.append(actionFlashCode->isChecked() ? "1" : "0");
	params.append(actionFlashConfig->isChecked() ? "1" : "0");
	archon->getResult();
	archon->command("FLASH", params);
}
//---------------------------------------------------------------------------
void TArchonGUI::verifyClicked()
{
	QString filename;
	QStringList params;

	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	filename = QFileDialog::getOpenFileName(this,
	 "Verify Archon PROM", sPROMFilename, "Archon PROM Files (*.mcs)");
	if (filename.isEmpty()) return;
	sPROMFilename = filename;
	params.append(filename);
	params.append(actionFlashBackplane->isChecked() ? "1" : "0");
	params.append(actionFlashCode->isChecked() ? "1" : "0");
	params.append(actionFlashConfig->isChecked() ? "1" : "0");
	archon->getResult();
	archon->command("VERIFY", params);
}
//---------------------------------------------------------------------------
void TArchonGUI::rebootClicked()
{
	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	archon->getResult();
	archon->command("REBOOT");
}
//---------------------------------------------------------------------------
void TArchonGUI::warmbootClicked()
{
	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	archon->getResult();
	archon->command("WARMBOOT");
}
//---------------------------------------------------------------------------
void TArchonGUI::flashActiveConfigClicked()
{
	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	archon->getResult();
	archon->command("FLASHACTIVECONFIG");
}
//---------------------------------------------------------------------------
void TArchonGUI::eraseStoredConfigClicked()
{
	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	archon->getResult();
	archon->command("ERASESTOREDCONFIG");
}
//---------------------------------------------------------------------------
void TArchonGUI::flashModuleClicked()
{
	int i;
	int module = -1;
	QString filename;
	QStringList params;

	// Find module to flash
	for (i = 0; i < MAX_MODULES; i++)
		if (agModules->checkedAction() == actionFlashModule[i])
			module = i;
	if (module < 0)
		return;
	// Get ROM file
	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	filename = QFileDialog::getOpenFileName(this,
		"Flash Archon PROM", sPROMFilename, "Archon PROM Files (*.mcs)");
	if (filename.isEmpty()) return;
	sPROMFilename = filename;
	params.append(filename);
	// Flash module
	if (module >= 0)
	{
		params.append(QString::number(module));
		archon->getResult();
		archon->command("FLASHMOD", params);
	}
}
//---------------------------------------------------------------------------
void TArchonGUI::verifyModuleClicked()
{
	int i;
	int module = -1;
	QString filename;
	QStringList params;

	// Find module to verify
	for (i = 0; i < MAX_MODULES; i++)
		if (agModules->checkedAction() == actionFlashModule[i])
			module = i;
	if (module < 0)
		return;
	// Get ROM file
	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	filename = QFileDialog::getOpenFileName(this,
		"Verify Archon PROM", sPROMFilename, "Archon PROM Files (*.mcs)");
	if (filename.isEmpty()) return;
	sPROMFilename = filename;
	params.append(filename);
	// Verify module
	if (module >= 0)
	{
		params.append(QString::number(module));
		archon->getResult();
		archon->command("VERIFYMOD", params);
	}
}
//---------------------------------------------------------------------------
void TArchonGUI::poll()
{
	if (connected)
	{
		switch (pollstep)
		{
		case 0:
			if (!archon->command("STATUS"))
				pollstep++;
			break;
		case 1:
			if (!archon->command("FRAME"))
				pollstep++;
			break;
		}
		if (pollstep > 1)
			pollstep = 0;
	}
}
//---------------------------------------------------------------------------
void TArchonGUI::stateChanged()
{
	bool ok;
	int i, clock, keep;
	int current = lwStates->currentRow();
	if (current < 0)
		return;
	if (clock_lock)
		return;
	clock_lock = true;
	QStringList sl;
	QVariantMap map;
	map = lwStates->item(current)->data(Qt::UserRole).toMap();
	sl = map.value("CONTROL", "").toString().split(",");
	clock = sl.value(0, "FF").toInt(&ok, 16);
	keep = sl.value(1, "FF").toInt(&ok, 16);
	for (i = 0; i < CONTROL_COUNT; i++)
	{
		control_clock[i]->setChecked(clock & (1 << i));
		control_keep[i]->setChecked(keep & (1 << i));
		control_clock[i]->setEnabled(!control_keep[i]->isChecked());
	}
	for (i = 0; i < mod_count; i++)
	{
		if (!modules[i])
			continue;
		modules[i]->setClocks(map);
	}
	clock_lock = false;
}
//---------------------------------------------------------------------------
void TArchonGUI::clockChanged()
{
	int i, current, clock, keep;
	QVariantMap map;
	QStringList sl;

	current = lwStates->currentRow();
	if (current < 0)
		return;
	if (clock_lock)
		return;
	clock_lock = true;
	map = lwStates->item(current)->data(Qt::UserRole).toMap();
	clock = 0;
	keep = 0;
	for (i = 0; i < CONTROL_COUNT; i++)
	{
		if (control_clock[i]->isChecked())
			clock |= 1 << i;
		if (control_keep[i]->isChecked())
			keep |= 1 << i;
		control_clock[i]->setEnabled(!control_keep[i]->isChecked());
	}
	sl.append(QString::number(clock, 16).toUpper());
	sl.append(QString::number(keep, 16).toUpper());
	map.insert("CONTROL", sl.join(","));
	for (i = 0; i < mod_count; i++)
	{
		if (!modules[i])
			continue;
		modules[i]->getClocks(map);
	}
	lwStates->item(current)->setData(Qt::UserRole, map);
	clock_lock = false;
}
//---------------------------------------------------------------------------
void TArchonGUI::stateUp()
{
	QListWidgetItem *lwi;
	int current = lwStates->currentRow();
	if (current < 1)
		return;
	lwi = lwStates->takeItem(current);
	lwStates->insertItem(current - 1, lwi);
	lwStates->setCurrentRow(current - 1, QItemSelectionModel::ClearAndSelect);
}
//---------------------------------------------------------------------------
void TArchonGUI::stateDown()
{
	QListWidgetItem *lwi;
	int current = lwStates->currentRow();
	int last = lwStates->count() - 1;
	if ((current < 0) || (current == last))
		return;
	lwi = lwStates->takeItem(current);
	lwStates->insertItem(current + 1, lwi);
	lwStates->setCurrentRow(current + 1, QItemSelectionModel::ClearAndSelect);
}
//---------------------------------------------------------------------------
void TArchonGUI::stateAdd()
{
	QVariantMap map;
	QListWidgetItem *lwi = new QListWidgetItem("new");
	lwi->setData(Qt::UserRole, map);
	lwi->setFlags(lwi->flags() | Qt::ItemIsEditable);
	lwStates->addItem(lwi);
	lwStates->setCurrentRow(lwStates->count() - 1, QItemSelectionModel::ClearAndSelect);
	clockChanged();
}
//---------------------------------------------------------------------------
void TArchonGUI::stateDelete()
{
	int current = lwStates->currentRow();
	if (current < 0)
		return;
	delete lwStates->takeItem(current);
	if (current < lwStates->count())
		lwStates->setCurrentRow(current, QItemSelectionModel::ClearAndSelect);
}
//---------------------------------------------------------------------------
void TArchonGUI::stateDuplicate()
{
	int current = lwStates->currentRow();
	if (current < 0)
		return;
	QVariantMap map = lwStates->item(current)->data(Qt::UserRole).toMap();
	QListWidgetItem *lwi = new QListWidgetItem("duplicate");
	lwi->setData(Qt::UserRole, map);
	lwi->setFlags(lwi->flags() | Qt::ItemIsEditable);
	lwStates->addItem(lwi);
	lwStates->setCurrentRow(lwStates->count() - 1, QItemSelectionModel::ClearAndSelect);
}
//---------------------------------------------------------------------------
void TArchonGUI::setZoom(double zoom)
{
//	ZoomLabel->setText(QString("Zoom: %1x").arg(zoom));
	imageScroll->setZoom(zoom);
}
//---------------------------------------------------------------------------
void TArchonGUI::zoomInClick()
{
	setZoom(imageScroll->zoom() * 2.0);
}
//---------------------------------------------------------------------------
void TArchonGUI::zoom1Click()
{
	setZoom(1.0);
}
//---------------------------------------------------------------------------
void TArchonGUI::zoomOutClick()
{
	setZoom(imageScroll->zoom() / 2.0);
}
//---------------------------------------------------------------------------
void TArchonGUI::zoomFitClick()
{
	imageScroll->zoomFit();
}
//---------------------------------------------------------------------------
void TArchonGUI::imageMouseXY(int x, int y, unsigned sample)
{
	if (twTabs->currentIndex() == 6)
		imageXYLabel->setText(QString("X: %1  Y: %2  Value: %3").arg(x).arg(y).arg(sample));
}
//---------------------------------------------------------------------------
void TArchonGUI::gainChange(int value)
{
	imageScroll->setGain(exp(double(value) / 100.0));
}
//---------------------------------------------------------------------------
void TArchonGUI::offsetChange(int value)
{
	imageScroll->setOffset(double(value));
}
//---------------------------------------------------------------------------
void TArchonGUI::resetGainOffset()
{
	sbGain->setValue(0);
	sbOffset->setValue(0);
}
//---------------------------------------------------------------------------
void TArchonGUI::fitGainOffset()
{
	int x, y, w, h, x1, y1, x2, y2;
	unsigned max, min;
	TFrameBuffer *frame = imageScroll->frame();
	unsigned short *buf;
	unsigned *buf32;

	if ((frame == NULL) || (frame->isEmpty()))
		return;
	buf = frame->Data;
	buf32 = (unsigned *)buf;
	w = frame->width();
	h = frame->height();

	if ((statX1 == statX2) && (statY1 == statY2))
	{
		x1 = 0;
		x2 = w - 1;
		y1 = 0;
		y2 = h -1;
	}
	else
	{
		x1 = qBound(0, statX1, w - 1);
		x2 = qBound(0, statX2, w - 1);
		y1 = qBound(0, statY1, h - 1);
		y2 = qBound(0, statY2, h - 1);
	}
	if (frame->isHDR())
	{
		max = buf32[y1 * w + x1] >> 12;
		min = buf32[y1 * w + x1] >> 12;
		for (y = y1; y <= y2; y++)
			for (x = x1; x <= x2; x++)
			{
				max = qMax(max, buf32[y * w + x] >> 12);
				min = qMin(min, buf32[y * w + x] >> 12);
			}
	}
	else
	{
		max = buf[y1 * w + x1];
		min = buf[y1 * w + x1];
		for (y = y1; y <= y2; y++)
			for (x = x1; x <= x2; x++)
			{
				max = qMax(max, unsigned(buf[y * w + x]));
				min = qMin(min, unsigned(buf[y * w + x]));
			}
	}
	if (frame->isHDR())
	{
		sbOffset->setValue(min / 16);
		if (max != min)
			sbGain->setValue(qBound(-1000, int(100.0 * log(1048575.0 / (max - min))), 1000));
	}
	else
	{
		sbOffset->setValue(min);
		if (max != min)
			sbGain->setValue(qBound(-1000, int(100.0 * log(65535.0 / (max - min))), 1000));
	}
}
//---------------------------------------------------------------------------
void TArchonGUI::changeImageMode(int mode)
{
	imageScroll->setMode(mode);
}
//---------------------------------------------------------------------------
void TArchonGUI::setRawZoom(double zoom)
{
//	ZoomLabel->setText(QString("Zoom: %1x").arg(zoom));
	rawImageScroll->setZoom(zoom);
}
//---------------------------------------------------------------------------
void TArchonGUI::rawZoomInClick()
{
	setRawZoom(rawImageScroll->zoom() * 2.0);
}
//---------------------------------------------------------------------------
void TArchonGUI::rawZoom1Click()
{
	setRawZoom(1.0);
}
//---------------------------------------------------------------------------
void TArchonGUI::rawZoomOutClick()
{
	setRawZoom(rawImageScroll->zoom() / 2.0);
}
//---------------------------------------------------------------------------
void TArchonGUI::rawImageMouseXY(int x, int y, unsigned sample)
{
	if (twTabs->currentIndex() == 10)
		imageXYLabel->setText(QString("X: %1  Y: %2  Value: %3").arg(x).arg(y).arg(sample));
}
//---------------------------------------------------------------------------
void TArchonGUI::rawGainChange(int value)
{
	rawImageScroll->setGain(exp(double(value) / 200.0));
}
//---------------------------------------------------------------------------
void TArchonGUI::rawOffsetChange(int value)
{
	rawImageScroll->setOffset(double(value));
}
//---------------------------------------------------------------------------
void TArchonGUI::resetRawGainOffset()
{
	sbRawGain->setValue(0);
	sbRawOffset->setValue(0);
}
//---------------------------------------------------------------------------
void TArchonGUI::newFrame()
{
	int i, newframe, newindex;

	newframe = -1;
	newindex = -1;
	// Lock the frame buffers and find the newest available frame
	archon->frameMutex.lock();
	for (i = 0; i < archon->frames.count(); i++)
		if (!archon->frames[i].Locked && (archon->frames[i].Frame > newframe))
		{
			newframe = archon->frames[i].Frame;
			newindex = i;
		}
	// Is this the same as the currently displayed frame?
	if (newframe == displayframe)
	{
		archon->frameMutex.unlock();
		return;
	}
	// Release old display frame and lock new display frame
	if (newindex >= 0)
	{
		if (displayindex >= 0)
		{
			archon->frames[displayindex].Locked = false;
			updateDiffStats(displayindex, newindex);
		}
		archon->frames[newindex].Locked = true;
		displayindex = newindex;
		displayframe = newframe;
	}
	// Did we find a new frame to render?
	if (newindex >= 0)
	{
		archon->frameMutex.unlock();
		frameLabel->setText(QString("Frame: %1").arg(displayframe));
		imageScroll->setFrame(&archon->frames[displayindex]);
		updateStats();
		updatePlots();
		rawImageScroll->setFrame(&archon->frames[displayindex]);
		updateRawStats();
		updateRawPlots();
		if (cbSaveAll->isChecked() || (savecount > 0))
			saveFrame();
		if (savecount > 0)
			savecount--;
	}
	else
		archon->frameMutex.unlock();
}
//---------------------------------------------------------------------------
void TArchonGUI::statChanged(int x1, int y1, int x2, int y2)
{
	statX1 = qMin(x1, x2);
	statY1 = qMin(y1, y2);
	statX2 = qMax(x1, x2);
	statY2 = qMax(y1, y2);
	updateStats();
	updatePlots();
}
//---------------------------------------------------------------------------
void TArchonGUI::noiseChanged(int x1, int y1, int x2, int y2)
{
	noiseX1 = qMin(x1, x2);
	noiseY1 = qMin(y1, y2);
	noiseX2 = qMax(x1, x2);
	noiseY2 = qMax(y1, y2);
	updateStats();
}
//---------------------------------------------------------------------------
void TArchonGUI::plotChanged(int hplot, int vplot)
{
	m_hplot = hplot;
	m_vplot = vplot;
	updatePlots();
}
//---------------------------------------------------------------------------
void TArchonGUI::plotChanged()
{
	updatePlots();
}
//---------------------------------------------------------------------------
void TArchonGUI::updateStats()
{
	int x, y, w, h, x1, y1, x2, y2;
	double mean, std, z, var, sigmean, signal, dr;
	QString s;
	TFrameBuffer *frame = imageScroll->frame();
	unsigned short *buf;
	unsigned *buf32;
	QVector<double> vx, vy;

	if ((frame == NULL) || (frame->isEmpty()))
		return;
	buf = frame->Data;
	buf32 = (unsigned *)buf;
	w = frame->width();
	h = frame->height();
	vx.resize(65536);
	vy.resize(65536);
	for (x = 0; x < 65536; x++)
		vx[x] = x;

	// Signal stats
	x1 = qBound(0, statX1, w - 1);
	x2 = qBound(0, statX2, w - 1);
	y1 = qBound(0, statY1, h - 1);
	y2 = qBound(0, statY2, h - 1);
	mean = 0.0;
	if (frame->isHDR())
		for (y = y1; y <= y2; y++)
			for (x = x1; x <= x2; x++)
				mean += buf32[y * w + x] >> 12;
	else
		for (y = y1; y <= y2; y++)
			for (x = x1; x <= x2; x++)
				mean += buf[y * w + x];
	mean /= (x2 - x1 + 1) * (y2 - y1 + 1);
	std = 0.0;
	if (frame->isHDR())
		for (y = y1; y <= y2; y++)
			for (x = x1; x <= x2; x++)
			{
				z = (buf32[y * w + x] >> 12) - mean;
				std += z * z;
			}
	else
		for (y = y1; y <= y2; y++)
			for (x = x1; x <= x2; x++)
			{
				z = buf[y * w + x] - mean;
				std += z * z;
			}
	std /= (x2 - x1 + 1) * (y2 - y1 + 1);
	var = std;
	if (std > 0.0)
		std = sqrt(std);
	s = "Signal Mean: " + flt(mean, 0, 1) + "  Std: " + flt(std, 0, 2) + "  Var: " + flt(var, 0, 2);
	statsLabel->setText(s);
	sigmean = mean;

	// Noise stats
	x1 = qBound(0, noiseX1, w - 1);
	x2 = qBound(0, noiseX2, w - 1);
	y1 = qBound(0, noiseY1, h - 1);
	y2 = qBound(0, noiseY2, h - 1);
	mean = 0.0;
	if (frame->isHDR())
		for (y = y1; y <= y2; y++)
			for (x = x1; x <= x2; x++)
				mean += buf32[y * w + x] >> 12;
	else
		for (y = y1; y <= y2; y++)
			for (x = x1; x <= x2; x++)
				mean += buf[y * w + x];
	mean /= (x2 - x1 + 1) * (y2 - y1 + 1);
	std = 0.0;
	if (frame->isHDR())
		for (y = y1; y <= y2; y++)
			for (x = x1; x <= x2; x++)
			{
				z = (buf32[y * w + x] >> 12) - mean;
				std += z * z;
			}
	else
		for (y = y1; y <= y2; y++)
			for (x = x1; x <= x2; x++)
			{
				z = buf[y * w + x] - mean;
				std += z * z;
			}
	std /= (x2 - x1 + 1) * (y2 - y1 + 1);
	if (std > 0.0)
		std = sqrt(std);
	s = "Noise Mean: " + flt(mean, 0, 1) + "  Std: " + flt(std, 0, 2);
	noiseLabel->setText(s);

	signal = sigmean - mean;
	if (std > 0.0)
		dr = 20 * log10(signal / std);
	else
		dr = 0.0;
	s = "Signal: " + flt(signal, 0, 2) + "  Noise: " + flt(std, 0, 2) + "  DR: " + flt(dr, 0, 1) + " dB  DV: " + flt(dv, 0, 1);
	DRLabel->setText(s);
}
//---------------------------------------------------------------------------
void TArchonGUI::updateDiffStats(int prev, int next)
{
	QString s;
	TFrameBuffer *frame1 = &archon->frames[prev];
	TFrameBuffer *frame2 = &archon->frames[next];
	unsigned short *buf1, *buf2;
	unsigned *buf1_32, *buf2_32;
	int i, x, y, w, h, x1, y1, x2, y2;
	double signalmean, diffmean, diffvar, z, noisemean;
	double ymin, ymax;

	if (frame1->isEmpty() || frame2->isEmpty() ||
		(frame1->width() != frame2->width()) ||
		(frame1->height() != frame2->height()) ||
		(frame1->isHDR() != frame2->isHDR()))
	{
		diffStatsLabel->setText("Diff Var: -");
		dv = 0;
		return;
	}
	w = frame1->width();
	h = frame1->height();
	buf1 = frame1->Data;
	buf2 = frame2->Data;
	buf1_32 = (unsigned *)buf1;
	buf2_32 = (unsigned *)buf2;
	x1 = qBound(0, statX1, w-1);
	x2 = qBound(0, statX2, w-1);
	y1 = qBound(0, statY1, h-1);
	y2 = qBound(0, statY2, h-1);
	signalmean = 0.0;
	diffmean = 0.0;
	diffvar = 0.0;
	if (frame1->isHDR())
		for (y = y1; y <= y2; y++)
			for (x = x1; x <= x2; x++)
			{
				signalmean += double(buf1_32[y * w + x] >> 12);
				diffmean += double(buf1_32[y * w + x] >> 12) - double(buf2_32[y * w + x] >> 12);
			}
	else
		for (y = y1; y <= y2; y++)
			for (x = x1; x <= x2; x++)
			{
				signalmean += double(buf1[y * w + x]);
				diffmean += double(buf1[y * w + x]) - double(buf2[y * w + x]);
			}
	signalmean /= (x2 - x1 + 1) * (y2 - y1 + 1);
	diffmean /= (x2 - x1 + 1) * (y2 - y1 + 1);
	if (frame1->isHDR())
		for (y = y1; y <= y2; y++)
			for (x = x1; x <= x2; x++)
			{
				z = double(buf1_32[y * w + x] >> 12) - double(buf2_32[y * w + x] >> 12) - diffmean;
				diffvar += z*z;
			}
	else
		for (y = y1; y <= y2; y++)
			for (x = x1; x <= x2; x++)
			{
				z = double(buf1[y * w + x]) - double(buf2[y * w + x]) - diffmean;
				diffvar += z*z;
			}
	diffvar /= 2.0 * (x2 - x1 + 1) * (y2 - y1 + 1);
	s = "Diff Var: " + flt(diffvar, 0, 1);
	diffStatsLabel->setText(s);
	dv = diffvar;

	// Are we doing PTC calculations?
	if (ptccount == 0)
		return;

	ptccount--;
	// Calculate noise mean
	x1 = qBound(0, noiseX1, w - 1);
	x2 = qBound(0, noiseX2, w - 1);
	y1 = qBound(0, noiseY1, h - 1);
	y2 = qBound(0, noiseY2, h - 1);
	noisemean = 0.0;
	if (frame1->isHDR())
		for (y = y1; y <= y2; y++)
			for (x = x1; x <= x2; x++)
				noisemean += buf1_32[y * w + x] >> 12;
	else
		for (y = y1; y <= y2; y++)
			for (x = x1; x <= x2; x++)
				noisemean += buf1[y * w + x];
	noisemean /= (x2 - x1 + 1) * (y2 - y1 + 1);
	ptcmean += signalmean - noisemean;
	ptcvar += diffvar;

	// Are we done doing PTC calculations?
	if (ptccount != 0)
		return;

	ptcmean /= ptctotal;
	ptcvar /= ptctotal;
	for (i = 0; i < ptcx.count(); i++)
		if (ptcx[i] > ptcmean)
			break;
	ptcx.insert(i,ptcmean);
	ptcy.insert(i,ptcvar);
	PTCCurve->setSamples(ptcx,ptcy);
	PTCPlot->setAxisScale(QwtPlot::xBottom,ptcx[0],ptcx[ptcx.count()-1]);
	ymin = ptcy[0];
	ymax = ptcy[0];
	for (i = 1; i < ptcy.count(); i++)
	{
		ymin = qMin(ptcy[i], ymin);
		ymax = qMax(ptcy[i], ymax);
	}
	PTCPlot->setAxisScale(QwtPlot::yLeft,ymin,ymax);
	PTCZoomer->setZoomBase();
	PTCPlot->replot();
}
//---------------------------------------------------------------------------
void TArchonGUI::updatePlots()
{
	int i, j, w, h, x1, y1, x2, y2;
	bool imagechange = false;
	bool hdr;
	double mean;
	unsigned *data32;
//	QVector<double> x,y;
	TFrameBuffer *frame = imageScroll->frame();

	if ((frame == NULL) || (frame->isEmpty()))
		return;

	// Check for an image size change
	w = frame->width();
	h = frame->height();
	hdr = frame->isHDR();
	if ((w != lastw) || (h != lasth) || (hdr != lasthdr))
	{
		imagechange = true;
		lastw = w;
		lasth = h;
		lasthdr = hdr;
	}
	data32 = (unsigned *)frame->Data;

	// Check for valid plot lines
	m_hplot = qMin(m_hplot, h - 1);
	m_hplot = qMax(m_hplot, 0);
	m_vplot = qMin(m_vplot, w - 1);
	m_vplot = qMax(m_vplot, 0);

	// Get valid signal area coordinates
	x1 = qBound(0, statX1, w - 1);
	x2 = qBound(0, statX2, w - 1);
	y1 = qBound(0, statY1, h - 1);
	y2 = qBound(0, statY2, h - 1);

	// Update horizontal plot
	hx.resize(w);
	hy.resize(w);
	if (hdr)
		for (i = 0; i < w; i++)
		{
			hx[i] = i;
			if (!cbHAvgCheckBox->isChecked())
				hy[i] = data32[m_hplot * w + i] >> 12;
			else
			{
				mean = 0.0;
				for (j = y1; j <= y2; j++)
					mean += data32[j * w + i] >> 12;
				mean /= (y2 - y1 + 1);
				hy[i] = mean;
			}
		}
	else
		for (i = 0; i < w; i++)
		{
			hx[i] = i;
			if (!cbHAvgCheckBox->isChecked())
				hy[i] = frame->Data[m_hplot * w + i];
			else
			{
				mean = 0.0;
				for (j = y1; j <= y2; j++)
					mean += frame->Data[j * w + i];
				mean /= (y2 - y1 + 1);
				hy[i] = mean;
			}
		}
	HCurve->setSamples(hx, hy);
	if (imagechange)
	{
		HPlot->setAxisScale(QwtPlot::xBottom, 0, w - 1);
		if (hdr)
			HPlot->setAxisScale(QwtPlot::yLeft, 0, 1048575);
		else
			HPlot->setAxisScale(QwtPlot::yLeft, 0, 65535);
		HZoomer->setZoomBase();
	}
	HPlot->replot();

	// Update vertical plot
	vx.resize(h);
	vy.resize(h);
	if (hdr)
		for (i = 0; i < h; i++)
		{
			vx[i] = i;
			if (!cbVAvgCheckBox->isChecked())
				vy[i] = data32[i * w + m_vplot] >> 12;
			else
			{
				mean = 0.0;
				for (j = x1; j <= x2; j++)
					mean += data32[i * w + j] >> 12;
				mean /= (x2 - x1 + 1);
				vy[i] = mean;
			}
		}
	else
		for (i = 0; i < h; i++)
		{
			vx[i] = i;
			if (!cbVAvgCheckBox->isChecked())
				vy[i] = frame->Data[i * w + m_vplot];
			else
			{
				mean = 0.0;
				for (j = x1; j <= x2; j++)
					mean += frame->Data[i * w + j];
				mean /= (x2 - x1 + 1);
				vy[i] = mean;
			}
		}
	VCurve->setSamples(vx, vy);
	if (imagechange)
	{
		VPlot->setAxisScale(QwtPlot::xBottom, 0, h-1);
		if (hdr)
			VPlot->setAxisScale(QwtPlot::yLeft, 0, 1048575);
		else
			VPlot->setAxisScale(QwtPlot::yLeft, 0, 65535);
		VZoomer->setZoomBase();
	}
	VPlot->replot();
}
//---------------------------------------------------------------------------
void TArchonGUI::snapPTC()
{
	ptccount = lePTCCount->text().toInt();
	ptccount = qMax(1, ptccount);
	ptctotal = ptccount;
	ptcmean = 0.0;
	ptcvar = 0.0;
}
//---------------------------------------------------------------------------
void TArchonGUI::resetPTC()
{
	ptcx.clear();
	ptcy.clear();
	PTCCurve->setSamples(ptcx,ptcy);
	PTCPlot->replot();
}
//---------------------------------------------------------------------------
void TArchonGUI::savePTC()
{
	FILE *fout = fopen("ptc.txt","w");
	fprintf(fout,"Signal\tVariance\n");
	for (int i = 0; i < ptcx.count(); i++)
		fprintf(fout,"%0.6lf\t%0.6lf\n",ptcx[i],ptcy[i]);
	fclose(fout);
}
//---------------------------------------------------------------------------
void TArchonGUI::saveHPlot()
{
	FILE *fout = fopen("hplot.txt","w");
	fprintf(fout,"Pixel\tSignal\n");
	for (int i = 0; i < hx.count(); i++)
		fprintf(fout,"%0.0lf\t%0.0lf\n",hx[i],hy[i]);
	fclose(fout);
}
//---------------------------------------------------------------------------
void TArchonGUI::saveVPlot()
{
	FILE *fout = fopen("vplot.txt","w");
	fprintf(fout,"Pixel\tSignal\n");
	for (int i = 0; i < vx.count(); i++)
		fprintf(fout,"%0.0lf\t%0.0lf\n",vx[i],vy[i]);
	fclose(fout);
}
//---------------------------------------------------------------------------
void TArchonGUI::openFrame()
{
	int i, w, h, size, highestframe, highestindex, lowestframe, lowestindex;
	bool ok;
	QByteArray ba;
	QRegularExpression regex("_(\\d+)x");
	QRegularExpressionMatch match;

	QString filename = QFileDialog::getOpenFileName(this,
		"Load raw image file", lastfilename,
		"RAW Image Files (*.raw)");
	if (filename.isEmpty()) return;
	lastfilename = filename;
	filenameLabel->setText(filename);
	QFile file(filename);
	if (!file.open(QIODevice::ReadOnly))
	{
		QMessageBox::warning(this, "Error", "Error opening file for read", QMessageBox::Ok);
		return;
	}
	size = file.size() / sizeof(unsigned short);
	w = -1;
	match = regex.match(filename);
	if (match.hasMatch())
		w = match.captured(1).toInt();
	while ((w <= 0) || (size % w))
	{
		w = QInputDialog::getInt(this, "Enter raw image width in pixels", "Width:", w, 0,
			2147483647, 1, &ok);
		if (!ok)
		{
			file.close();
			return;
		}
	}
	h = size / w;

	highestframe = -1;
	highestindex = 0;
	archon->frameMutex.lock();
	for (i = 0; i < archon->frames.count(); i++)
	{
		highestframe = qMax(archon->frames[i].Frame, highestframe);
		highestindex = i;
	}
	lowestframe = highestframe;
	lowestindex = highestindex;
	for (i = 0; i < archon->frames.count(); i++)
	{
		if (archon->frames[i].Locked)
			continue;
		if (archon->frames[i].Frame < lowestframe)
		{
			lowestframe = archon->frames[i].Frame;
			lowestindex = i;
		}
	}
	archon->frames[lowestindex].setSize(w, h, false);
	archon->frames[lowestindex].Frame = highestframe + 1;
	size *= sizeof(unsigned short);
	if (file.read((char *)archon->frames[lowestindex].Data, size) != size)
	{
		QMessageBox::warning(this, "Error", "Error reading file", QMessageBox::Ok);
		file.close();
		archon->frameMutex.unlock();
		return;
	}
	archon->frameMutex.unlock();
	file.close();
	newFrame();
}
//---------------------------------------------------------------------------
bool TArchonGUI::openFrame(QString filename)
{
	int i, w, h, size, highestframe, highestindex, lowestframe, lowestindex;
	bool ok;
	QRegularExpression regex("_(\\d+)x");
	QRegularExpressionMatch match;

	if (filename.isEmpty()) return false;
	lastfilename = filename;
	filenameLabel->setText(filename);
	QFile file(filename);
	if (!file.open(QIODevice::ReadOnly))
		return false;
	size = file.size() / sizeof(unsigned short);
	w = -1;
	match = regex.match(filename);
	if (match.hasMatch())
		w = match.captured(1).toInt();
	while ((w <= 0) || (size % w))
	{
		w = QInputDialog::getInt(this, "Enter raw image width in pixels", "Width:", w, 0,
			2147483647, 1, &ok);
		if (!ok)
		{
			file.close();
			return false;
		}
	}
	h = size / w;

	highestframe = -1;
	highestindex = 0;
	archon->frameMutex.lock();
	for (i = 0; i < archon->frames.count(); i++)
	{
		highestframe = qMax(archon->frames[i].Frame, highestframe);
		highestindex = i;
	}
	lowestframe = highestframe;
	lowestindex = highestindex;
	for (i = 0; i < archon->frames.count(); i++)
	{
		if (archon->frames[i].Locked)
			continue;
		if (archon->frames[i].Frame < lowestframe)
		{
			lowestframe = archon->frames[i].Frame;
			lowestindex = i;
		}
	}
	archon->frames[lowestindex].setSize(w, h, false);
	archon->frames[lowestindex].Frame = highestframe + 1;
	size *= sizeof(unsigned short);
	if (file.read((char *)archon->frames[lowestindex].Data, size) != size)
	{
		QMessageBox::warning(this, "Error", "Error reading file", QMessageBox::Ok);
		file.close();
		archon->frameMutex.unlock();
		return false;
	}
	archon->frameMutex.unlock();
	file.close();
	newFrame();

	return true;
}
//---------------------------------------------------------------------------
void TArchonGUI::openHDRFrame()
{
	int i, w, h, size;
	bool ok;
	QByteArray ba;
	QRegularExpression regex("_(\\d+)x");
	QRegularExpressionMatch match;

	QString filename = QFileDialog::getOpenFileName(this,
		"Load raw image file", lastfilename,
		"RAW Image Files (*.raw)");
	if (filename.isEmpty()) return;
	lastfilename = filename;
	filenameLabel->setText(filename);
	QFile file(filename);
	if (!file.open(QIODevice::ReadOnly))
	{
		QMessageBox::warning(this, "Error", "Error opening file for read", QMessageBox::Ok);
		return;
	}
	size = file.size() / sizeof(quint32);
	w = -1;
	match = regex.match(filename);
	if (match.hasMatch())
		w = match.captured(1).toInt();
	do
	{
		w = QInputDialog::getInt(this, "Enter raw image width in pixels", "Width:", w, 0,
			2147483647, 1, &ok);
		if (!ok)
		{
			file.close();
			return;
		}
	} while ((w <= 0) || (size % w));
	h = size / w;

	archon->frameMutex.lock();
	for (i = 0; i < archon->frames.count(); i++)
	{
		archon->frames[i].Locked = false;
		archon->frames[i].Frame = -1;
	}
	displayframe = 0;
	displayindex = 0;
	archon->frames[displayindex].Locked = true;
	archon->frames[displayindex].Frame = 0;
	archon->frames[displayindex].setSize(w, h, true);
	size *= sizeof(quint32);
	if (file.read((char *)archon->frames[displayindex].Data, size) != size)
	{
		QMessageBox::warning(this, "Error", "Error reading file", QMessageBox::Ok);
		file.close();
		return;
	}
	frameLabel->setText(QString("Frame: %1").arg(displayframe));
	imageScroll->setFrame(&archon->frames[displayindex]);
	archon->frameMutex.unlock();
	updateStats();
	updatePlots();
	file.close();
}
//---------------------------------------------------------------------------
void TArchonGUI::saveFrame()
{
	int w, h, size;
	unsigned short *buf;
	QString s;

	if (displayindex < 0)
		return;
	w = archon->frames[displayindex].width();
	h = archon->frames[displayindex].height();
	buf = archon->frames[displayindex].Data;
	// Create file name
	s = leBaseFilename->text() + QString("_%1x%2_%3.raw").arg(w).arg(h).arg(displayframe);
	// Save file
	QFile file(s);
	if (!file.open(QIODevice::WriteOnly))
	{
		QMessageBox::warning(this, "Error", "Error opening save file for write", QMessageBox::Ok);
		return;
	}
	if (archon->frames[displayindex].isHDR())
		size = w * h * sizeof(quint32);
	else
		size = w * h * sizeof(quint16);
	if (file.write((char *)buf, size) != size)
		QMessageBox::warning(this, "Error", "Error writing to save file", QMessageBox::Ok);
	file.close();
}
//---------------------------------------------------------------------------
void TArchonGUI::saveSequence()
{
	bool ok;
	savecount = leSaveCount->text().toInt(&ok);
	if (!ok || (savecount < 0))
		savecount = 0;
}
//---------------------------------------------------------------------------
void TArchonGUI::rawStatChanged(int x1, int y1, int x2, int y2)
{
	rawStatX1 = qMin(x1, x2);
	rawStatY1 = qMin(y1, y2);
	rawStatX2 = qMax(x1, x2);
	rawStatY2 = qMax(y1, y2);
	updateRawStats();
	updateRawPlots();
}
//---------------------------------------------------------------------------
void TArchonGUI::rawNoiseChanged(int x1, int y1, int x2, int y2)
{
	rawNoiseX1 = qMin(x1, x2);
	rawNoiseY1 = qMin(y1, y2);
	rawNoiseX2 = qMax(x1, x2);
	rawNoiseY2 = qMax(y1, y2);
	updateRawStats();
}
//---------------------------------------------------------------------------
void TArchonGUI::rawPlotChanged(int hplot, int vplot)
{
	m_rawhplot = hplot;
	m_rawvplot = vplot;
	updateRawPlots();
}
//---------------------------------------------------------------------------
void TArchonGUI::rawPlotChanged()
{
	updateRawPlots();
}
//---------------------------------------------------------------------------
void TArchonGUI::updateRawStats()
{
	int x, y, w, h, x1, y1, x2, y2;
	double mean, std, z, var;
	QString s;
	TFrameBuffer *frame = rawImageScroll->frame();
	unsigned short *buf;
	QVector<double> vx, vy;

	if ((frame == NULL) || (frame->isRawEmpty()))
		return;
	buf = frame->RawData;
	w = frame->rawwidth();
	h = frame->rawheight();
	vx.resize(65536);
	vy.resize(65536);
	for (x = 0; x < 65536; x++)
		vx[x] = x;

	// Signal stats
	x1 = qBound(0, rawStatX1, w - 1);
	x2 = qBound(0, rawStatX2, w - 1);
	y1 = qBound(0, rawStatY1, h - 1);
	y2 = qBound(0, rawStatY2, h - 1);
	mean = 0.0;
	for (y = y1; y <= y2; y++)
		for (x = x1; x <= x2; x++)
			mean += buf[y * w + x];
	mean /= (x2 - x1 + 1) * (y2 - y1 + 1);
	std = 0.0;
	for (y = y1; y <= y2; y++)
		for (x = x1; x <= x2; x++)
		{
			z = buf[y * w + x] - mean;
			std += z * z;
		}
	std /= (x2 - x1 + 1) * (y2 - y1 + 1);
	var = std;
	if (std > 0.0)
		std = sqrt(std);
	s = "Signal Mean: " + flt(mean, 0, 1) + "  Std: " + flt(std, 0, 2) + "  Var: " + flt(var, 0, 2);
	rawStatsLabel->setText(s);

	// Noise stats
	x1 = qBound(0, rawNoiseX1, w - 1);
	x2 = qBound(0, rawNoiseX2, w - 1);
	y1 = qBound(0, rawNoiseY1, h - 1);
	y2 = qBound(0, rawNoiseY2, h - 1);
	mean = 0.0;
	for (y = y1; y <= y2; y++)
		for (x = x1; x <= x2; x++)
			mean += buf[y * w + x];
	mean /= (x2 - x1 + 1) * (y2 - y1 + 1);
	std = 0.0;
	for (y = y1; y <= y2; y++)
		for (x = x1; x <= x2; x++)
		{
			z = buf[y * w + x] - mean;
			std += z * z;
		}
	std /= (x2 - x1 + 1) * (y2 - y1 + 1);
	if (std > 0.0)
		std = sqrt(std);
	s = "Noise Mean: " + flt(mean, 0, 1) + "  Std: " + flt(std, 0, 2);
	rawNoiseLabel->setText(s);
}
//---------------------------------------------------------------------------
void TArchonGUI::updateRawPlots()
{
	int i, j, w, h, x1, y1, x2, y2;
	bool imagechange = false;
	double mean;
//	QVector<double> x,y;
	TFrameBuffer *frame = rawImageScroll->frame();

	if ((frame == NULL) || (frame->isRawEmpty()))
		return;

	// Check for an image size change
	w = frame->rawwidth();
	h = frame->rawheight();
	if ((w != lastraww) || (h != lastrawh))
	{
		imagechange = true;
		lastraww = w;
		lastrawh = h;
	}

	// Check for valid plot lines
	m_rawhplot = qMin(m_rawhplot, h - 1);
	m_rawhplot = qMax(m_rawhplot, 0);
	m_rawvplot = qMin(m_rawvplot, w - 1);
	m_rawvplot = qMax(m_rawvplot, 0);

	// Get valid signal area coordinates
	x1 = qBound(0, rawStatX1, w - 1);
	x2 = qBound(0, rawStatX2, w - 1);
	y1 = qBound(0, rawStatY1, h - 1);
	y2 = qBound(0, rawStatY2, h - 1);

	// Update horizontal plot
	rawhx.resize(w);
	rawhy.resize(w);
	for (i = 0; i < w; i++)
	{
		rawhx[i] = i;
		if (!cbRawHAvgCheckBox->isChecked())
			rawhy[i] = frame->RawData[m_rawhplot * w + i];
		else
		{
			mean = 0.0;
			for (j = y1; j <= y2; j++)
				mean += frame->RawData[j * w + i];
			mean /= (y2 - y1 + 1);
			rawhy[i] = mean;
		}
	}
	rawHCurve->setSamples(rawhx, rawhy);
	if (imagechange)
	{
		rawHPlot->setAxisScale(QwtPlot::xBottom, 0, w - 1);
		rawHPlot->setAxisScale(QwtPlot::yLeft, 0, 65535);
		rawHZoomer->setZoomBase();
	}
	rawHPlot->replot();

	// Update vertical plot
	rawvx.resize(h);
	rawvy.resize(h);
	for (i = 0; i < h; i++)
	{
		rawvx[i] = i;
		if (!cbRawVAvgCheckBox->isChecked())
			rawvy[i] = frame->RawData[i * w + m_rawvplot];
		else
		{
			mean = 0.0;
			for (j = x1; j <= x2; j++)
				mean += frame->RawData[i * w + j];
			mean /= (x2 - x1 + 1);
			rawvy[i] = mean;
		}
	}
	rawVCurve->setSamples(rawvx, rawvy);
	if (imagechange)
	{
		rawVPlot->setAxisScale(QwtPlot::xBottom,0,h-1);
		rawVPlot->setAxisScale(QwtPlot::yLeft,0,65535);
		rawVZoomer->setZoomBase();
	}
	rawVPlot->replot();
}
//---------------------------------------------------------------------------
void TArchonGUI::saveRawHPlot()
{
	FILE *fout = fopen("rawhplot.txt", "w");
	fprintf(fout,"Pixel\tSignal\n");
	for (int i = 0; i < rawhx.count(); i++)
		fprintf(fout,"%0.0lf\t%0.0lf\n", rawhx[i], rawhy[i]);
	fclose(fout);
}
//---------------------------------------------------------------------------
void TArchonGUI::saveRawVPlot()
{
	FILE *fout = fopen("rawvplot.txt", "w");
	fprintf(fout,"Pixel\tSignal\n");
	for (int i = 0; i < rawvx.count(); i++)
		fprintf(fout,"%0.0lf\t%0.0lf\n", rawvx[i], rawvy[i]);
	fclose(fout);
}
//---------------------------------------------------------------------------
void TArchonGUI::saveRawFrame()
{
	int w, h, size;
	unsigned short *buf;
	QString s;

	if (displayindex < 0)
		return;
	w = archon->frames[displayindex].rawwidth();
	h = archon->frames[displayindex].rawheight();
	buf = archon->frames[displayindex].RawData;
	// Create file name
	s = leBaseFilename->text() + QString("_%1x%2_%3_raw.raw").arg(w).arg(h).arg(displayframe);
	// Save file
	QFile file(s);
	if (!file.open(QIODevice::WriteOnly))
	{
		QMessageBox::warning(this, "Error", "Error opening save file for write", QMessageBox::Ok);
		return;
	}
	size = w * h * sizeof(unsigned short);
	if (file.write((char *)buf, size) != size)
		QMessageBox::warning(this, "Error", "Error writing to save file", QMessageBox::Ok);
	file.close();
}
//---------------------------------------------------------------------------
void TArchonGUI::testButton()
{
	int e;

	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	parseUI();
	archon->getResult();
	archon->setConfig(config);
	e = archon->getResult();
	if (!e)
	{
		archon->command("LOADPARAM", "EXPOSURES");
		archon->getResult();
	}
}
//---------------------------------------------------------------------------
void TArchonGUI::applyNet()
{
	if (!connected)
	{
		logMessage("Archon not connected.");
		return;
	}
	parseUI();
	archon->getResult();
	archon->setConfig(config);
	int e = archon->getResult();
	if (!e)
	{
		archon->command("APPLYNET");
		archon->getResult();
	}
}
//---------------------------------------------------------------------------
void addFITSHeader(QFile &file, QString key, QString value, QString comment)
{
	file.write(qPrintable(QString("%1= %2 / %3").arg(key, -8).arg(value, 20).arg(comment, -48)), 80);
}
//---------------------------------------------------------------------------
void addFITSHeaderL(QFile &file, QString key, QString value, QString comment)
{
	file.write(qPrintable(QString("%1= %2 / %3").arg(key, -8).arg(value, -20).arg(comment, -48)), 80);
}
//---------------------------------------------------------------------------
void endFITSHeader(QFile &file, int lines)
{
	file.write(qPrintable(QString("%1").arg("END", -80)), 80);
	for (lines = 35 - lines; lines > 0; lines--)
		file.write(qPrintable(QString("%1").arg(" ", -80)), 80);
}
//---------------------------------------------------------------------------
void TArchonGUI::saveFITS()
{
	int i, x, y, w, h, linesize, headerlines;
	quint16 *buf, *linebuf;
	quint32 *dbuf, *dlinebuf;
	char pad[2880];
	QString s;
	bool hdr;

	if (displayindex < 0)
		return;
	w = archon->frames[displayindex].width();
	h = archon->frames[displayindex].height();
	buf = archon->frames[displayindex].Data;
	dbuf = (quint32 *)buf;
	hdr = archon->frames[displayindex].isHDR();

	// Fill FITS padding with zeroes
	for (y = 0; y < 2880; y++)
		pad[y] = 0;
	// Create file name
	s = leBaseFilename->text() + QString("_%1x%2_%3.fits").arg(w).arg(h).arg(displayframe);
	// Save file
	QFile file(s);
	if (!file.open(QIODevice::WriteOnly))
	{
		QMessageBox::warning(this, "Error", "Error opening FITS file for write", QMessageBox::Ok);
		return;
	}
	linesize = w * 2;
	if (hdr)
		linesize *= 2;
	// Write primary FITS header
	headerlines = 0;
	addFITSHeader(file, "SIMPLE", "T", "Conform to FITS standard"); headerlines++;
	if (hdr)
	{
		addFITSHeader(file, "BITPIX", "32", "Unsigned long data"); headerlines++;
	}
	else
	{
		addFITSHeader(file, "BITPIX", "16", "Unsigned short data"); headerlines++;
	}
	addFITSHeader(file, "NAXIS", "2", "Number of axes"); headerlines++;
	addFITSHeader(file, "NAXIS1", QString::number(w), "Image width"); headerlines++;
	addFITSHeader(file, "NAXIS2", QString::number(h), "Image height"); headerlines++;
	if (hdr)
	{
		addFITSHeader(file, "BZERO", "2147483648", "Offset for unsigned long"); headerlines++;
	}
	else
	{
		addFITSHeader(file, "BZERO", "32768", "Offset for unsigned short"); headerlines++;
	}
	addFITSHeader(file, "BSCALE", "1", "Default scaling factor"); headerlines++;
	endFITSHeader(file, headerlines);
	// Write image data (byte order must be swapped)
	if (hdr)
	{
		dlinebuf = new quint32[w];
		for (y = 0; y < h; y++)
		{
			for (x = 0; x < w; x++)
				dlinebuf[x] = qToBigEndian((quint32)(dbuf[x] ^ 0x80000000));
			dbuf += w;
			if (file.write((char *)dlinebuf, linesize) != linesize)
				goto error;
		}
		delete[] dlinebuf;
		// Pad to end of FITS block
		i = 2880 - (w * h * 4) % 2880;
		if (i != 2880)
		{
			if (file.write(pad, i) != i)
				goto error;
		}
	}
	else
	{
		linebuf = new quint16[w];
		for (y = 0; y < h; y++)
		{
			for (x = 0; x < w; x++)
				linebuf[x] = qToBigEndian((quint16)(buf[x] ^ 0x8000));
			buf += w;
			if (file.write((char *)linebuf, linesize) != linesize)
				goto error;
		}
		delete[] linebuf;
		// Pad to end of FITS block
		i = 2880 - (w * h * 2) % 2880;
		if (i != 2880)
		{
			if (file.write(pad, i) != i)
				goto error;
		}
	}

	file.close();
	return;
error:
	QMessageBox::warning(this, "Error", "Error writing to FITS file", QMessageBox::Ok);
	file.close();
}

//---------------------------------------------------------------------------
void TArchonGUI::openFITS()
{
	int i, w, h, size, remaining, highestframe, highestindex, lowestframe, lowestindex;
	bool hdr;
	QByteArray ba, key, value;
	quint16 *p;
	quint32 *dp;

	QString filename = QFileDialog::getOpenFileName(this,
		"Load FITS image file", lastfilename,
		"FITS Image Files (*.fits)");
	if (filename.isEmpty()) return;
	lastfilename = filename;
	filenameLabel->setText(filename);
	QFile file(filename);
	if (!file.open(QIODevice::ReadOnly))
	{
		QMessageBox::warning(this, "Error", "Error opening file for read", QMessageBox::Ok);
		return;
	}
	remaining = file.size();
	key.clear();
	h = 0;
	w = 0;
	hdr = false;
	while (key != "END")
	{
		if (remaining < 2880)
		{
			QMessageBox::warning(this, "Error", "Error reading FITS headers", QMessageBox::Ok);
			return;
		}
		ba = file.read(2880);
		remaining -= 2880;
		for (i = 0; i < 2880; i += 80)
		{
			key = ba.mid(i, 8).simplified();
			if (key == "END")
				break;
			value = ba.mid(i + 10, 70).split('/')[0].simplified();
			if (key == "END")
				break;
			if (key == "BITPIX")
			{
				if (value == "16")
					hdr = false;
				else if (value == "32")
					hdr = true;
				else
				{
					QMessageBox::warning(this, "Error", "Unknown BITPIX value", QMessageBox::Ok);
					return;
				}
			}
			if (key == "NAXIS1")
			{
				w = value.toInt();
				if (w <= 0)
				{
					QMessageBox::warning(this, "Error", "Illegal width", QMessageBox::Ok);
					return;
				}
			}
			if (key == "NAXIS2")
			{
				h = value.toInt();
				if (h <= 0)
				{
					QMessageBox::warning(this, "Error", "Illegal height", QMessageBox::Ok);
					return;
				}
			}
		}
	}
	size = w * h * 2;
	if (hdr)
		size *= 2;
	if (remaining < size)
	{
		QMessageBox::warning(this, "Error", "Unexpected end of file", QMessageBox::Ok);
		return;
	}

	highestframe = -1;
	highestindex = 0;
	archon->frameMutex.lock();
	for (i = 0; i < archon->frames.count(); i++)
	{
		highestframe = qMax(archon->frames[i].Frame, highestframe);
		highestindex = i;
	}
	lowestframe = highestframe;
	lowestindex = highestindex;
	for (i = 0; i < archon->frames.count(); i++)
	{
		if (archon->frames[i].Locked)
			continue;
		if (archon->frames[i].Frame < lowestframe)
		{
			lowestframe = archon->frames[i].Frame;
			lowestindex = i;
		}
	}
	archon->frames[lowestindex].setSize(w, h, hdr);
	archon->frames[lowestindex].Frame = highestframe + 1;
	if (file.read((char *)archon->frames[lowestindex].Data, size) != size)
	{
		QMessageBox::warning(this, "Error", "Error reading file", QMessageBox::Ok);
		file.close();
		archon->frameMutex.unlock();
		return;
	}
	archon->frameMutex.unlock();
	file.close();
	if (hdr)
	{
		dp = (quint32 *)archon->frames[lowestindex].Data;
		for (i = 0; i < w * h; i++)
			dp[i] = qFromBigEndian(dp[i]) ^ 0x80000000;
	}
	else
	{
		p = (quint16 *)archon->frames[lowestindex].Data;
		for (i = 0; i < w * h; i++)
			p[i] = qFromBigEndian(p[i]) ^ 0x8000;
	}
	newFrame();
}
