#ifndef ARCHONGUI_H
#define ARCHONGUI_H

#include <QMainWindow>
#include <QTcpSocket>
#include <QTimer>
#include <QPushButton>
#include <QPlainTextEdit>
#include <QLineEdit>
#include <QLabel>
#include <QTime>
#include <QList>
#include <QVBoxLayout>
#include <QStatusBar>
#include <QMenuBar>
#include <QCheckBox>
#include <QTableWidget>
#include <QListWidget>
#include <QComboBox>

#include "qwt_plot.h"
#include "qwt_plot_curve.h"
#include "qwt_plot_panner.h"
#include "qwt_plot_zoomer.h"
#include "qwt_symbol.h"

#include "updatetimer.h"
#include "archon.h"
#include "simpleprogress.h"
#include "powerwidget.h"
#include "imagescrollwidget.h"
#include "modules.h"

class TModule;

class TArchonGUI : public QMainWindow
{
	Q_OBJECT
public:
	TArchonGUI(QString loadFilename, QWidget *parent = 0);
	~TArchonGUI();
	QTabWidget *waveformTabs() {return twModuleSignalTabs;}
	QTabWidget *vcpuTabs() {return twModuleVCPUTabs;}
	QTabWidget *systemTabs() {return twTabs;}
	void applyModule(int slot);
	void applyModuleDIO(int slot);
	void moduleCommand(int slot, QString cmd, QStringList params);
	void direct(QString cmd);
	RMap system;
	RMap status;
	RMap frameStatus;
	RMap config;
public slots:
	void openFile();
	void saveFile();
	void openNiceFile();
	void saveNiceFile();
	void showAbout();
	void testButton();
	void applyAll();
	void applyCDS();
	void loadTiming();
	void loadParameters();
	void test();
	void resetTiming();
	void holdTiming();
	void releaseTiming();
	void fetchFrame(int frame);
	void newFrame();
	void powerOn();
	void powerOff();
	void pollOn();
	void pollOff();
	void applySystem();
	void connectClicked();
	void flashClicked();
	void verifyClicked();
	void rebootClicked();
	void warmbootClicked();
	void flashActiveConfigClicked();
	void eraseStoredConfigClicked();
	void flashModuleClicked();
	void verifyModuleClicked();
	void poll();
	void logMessage(const QString& msg);
	void progressMessage(const QString& msg, int newstep, int newtotal);
	void msgSystem(const RMap& data);
	void msgStatus(const RMap& data);
	void msgFrameStatus(const RMap& data);
	void msgConnected(const bool connected);
	void stateChanged();
	void clockChanged();
	void stateUp();
	void stateDown();
	void stateAdd();
	void stateDelete();
	void stateDuplicate();
	void zoomInClick();
	void zoom1Click();
	void zoomOutClick();
	void zoomFitClick();
	void imageMouseXY(int x, int y, unsigned sample);
	void plotChanged(int hplot, int vplot);
	void plotChanged();
	void statChanged(int x1, int y1, int x2, int y2);
	void noiseChanged(int x1, int y1, int x2, int y2);
	void gainChange(int value);
	void offsetChange(int value);
	void resetGainOffset();
	void fitGainOffset();
	void changeImageMode(int mode);
	void snapPTC();
	void resetPTC();
	void savePTC();
	void saveHPlot();
	void saveVPlot();
	void openFrame();
	bool openFrame(QString filename);
	void openHDRFrame();
	void openFITS();
	void saveFrame();
	void saveFITS();
	void saveSequence();
	void rawZoomInClick();
	void rawZoom1Click();
	void rawZoomOutClick();
	void rawImageMouseXY(int x, int y, unsigned sample);
	void rawPlotChanged(int hplot, int vplot);
	void rawPlotChanged();
	void rawStatChanged(int x1, int y1, int x2, int y2);
	void rawNoiseChanged(int x1, int y1, int x2, int y2);
	void rawGainChange(int value);
	void rawOffsetChange(int value);
	void resetRawGainOffset();
	void saveRawHPlot();
	void saveRawVPlot();
	void saveRawFrame();
	void applyNet();
private:
	// Menu items
	QAction *actionOpen;
	QAction *actionSave;
	QAction *actionOpenNice;
	QAction *actionSaveNice;
	QAction *actionExit;
	QAction *actionAbout;
	QAction *actionFlash;
	QAction *actionVerify;
	QAction *actionReboot;
	QAction *actionWarmboot;
	QAction *actionFlashBackplane;
	QAction *actionFlashCode;
	QAction *actionFlashConfig;
	QAction *actionFlashActiveConfig;
	QAction *actionEraseStoredConfig;
	QAction *actionModuleFlash;
	QAction *actionModuleVerify;
	QAction *actionFlashModule[MAX_MODULES];
	QActionGroup *agModules;
	QString sConfigFilename;
	QString GUIVersion;

	// Status and configuration
	bool system_valid;
	int mod_count;
	void parseSystem();
	void parseStatus();
	void parseFrameStatus();
	TUpdateTimer *updateTimer;
	int parseUI();
	void updateUI();
	QLabel *StatusLabel;
	SimpleProgress *spProgress;

	// System
	QTabWidget *twTabs;
	int fixedTabs;
	TModule *modules[MAX_MODULES];
	QLineEdit *leAddress;
	QPushButton *connectButton;
	QPlainTextEdit *telog;
	PowerWidget *wPower;
	QLabel *status_valid;
	QLabel *status_count;
	QLabel *fan_speed;
	QLabel *fan_speed_label;
	QLabel *ext_clock_present;
	QLabel *ext_clock_present_label;
	QLabel *backplane_type;
	QLabel *backplane_rev;
	QLabel *backplane_ver;
	QLabel *backplane_id;
	QLabel *backplane_temp;
	QLabel *mod_slot[MAX_MODULES];
	QLabel *mod_type[MAX_MODULES];
	QLabel *mod_rev[MAX_MODULES];
	QLabel *mod_ver[MAX_MODULES];
	QLabel *mod_id[MAX_MODULES];
	QLabel *mod_temp[MAX_MODULES];
	QLabel *rbuf;
	QLabel *wbuf;
	QLabel *bufframes[3];
	QLabel *bufwidths[3];
	QLabel *bufheights[3];
	QLabel *bufpixels[3];
	QLabel *buflines[3];
	QLabel *bufrawblocks[3];
	QLabel *bufrawlines[3];
	QLabel *bufstate[3];
	QCheckBox *cbAutoFetch;
	QCheckBox *cbTrigOutForce;
	QCheckBox *cbTrigOutLevel;
	QCheckBox *cbTrigOutInvert;
	QCheckBox *cbTrigOutPower;
	QCheckBox *cbTrigInEnable;
	QCheckBox *cbTrigInInvert;
	QCheckBox *cbTrigInEdge;
	QCheckBox *cbExternalClock;
	QCheckBox *cbFanDisable;
	QCheckBox *cbApplyAll;
	QCheckBox *cbPowerOn;
	QLineEdit *leBaseFilename;
	QLineEdit *lePTCCount;
	QLineEdit *leSaveCount;
	QCheckBox *cbSaveAll;
	QLabel *power_id;
	QLabel *power_flags;
	QLabel *p2v5_v;
	QLabel *p2v5_i;
	QLabel *p5v_v;
	QLabel *p5v_i;
	QLabel *p6v_v;
	QLabel *p6v_i;
	QLabel *n6v_v;
	QLabel *n6v_i;
	QLabel *p17v_v;
	QLabel *p17v_i;
	QLabel *n17v_v;
	QLabel *n17v_i;
	QLabel *p35v_v;
	QLabel *p35v_i;
	QLabel *n35v_v;
	QLabel *n35v_i;
	QLabel *p100v_v;
	QLabel *p100v_i;
	QLabel *n100v_v;
	QLabel *n100v_i;
	QLabel *user_v;
	QLabel *user_i;
	QLabel *heater_v;
	QLabel *heater_i;

	// Archon simulator DACs
	QLineEdit *leDACA;
	QLineEdit *leDACB;

	// Network configuration
	QLineEdit *leIP;

	// Timing
	QTabWidget *twModuleSignalTabs;
	QPlainTextEdit *teScript;
	QListWidget *lwStates;
	QPlainTextEdit *teParameters;
	QPlainTextEdit *teConstants;
	QCheckBox *control_clock[CONTROL_COUNT];
	QCheckBox *control_keep[CONTROL_COUNT];
	bool clock_lock;

	// VCPU
	QTabWidget *twModuleVCPUTabs;

	// CDS / Deinterlacing
	QLineEdit *shp1;
	QLineEdit *shp2;
	QLineEdit *shd1;
	QLineEdit *shd2;
	QLabel *pclkdelaylabel;
	QLineEdit *pclkdelay;
	QComboBox *samplemode;
	QLineEdit *pixelcount;
	QLineEdit *linecount;
	QComboBox *framemode;
	QCheckBox *bigBuffers;
	QLabel *adxrawlabel;
	QCheckBox *adxraw;
	QLabel *adxcdslabel;
	QCheckBox *adxcds;
	QLabel *linescanlabel;
	QCheckBox *linescan;
	QCheckBox *rawEnable;
	QComboBox *rawsel;
	QLineEdit *rawStartLine;
	QLineEdit *rawEndLine;
	QLineEdit *rawStartPixel;
	QLineEdit *rawSamples;
	QPlainTextEdit *teTapOrder;

	// Image
	void setZoom(double zoom);
	void updateStats();
	void updateDiffStats(int prev, int next);
	void updatePlots();
	ImageScrollWidget *imageScroll;
	QwtPlot *HPlot;
	QwtPlotCurve *HCurve;
	QwtPlotPanner *HPanner;
	QwtPlotZoomer *HZoomer;
	QCheckBox *cbHAvgCheckBox;
	QwtPlot *VPlot;
	QwtPlotCurve *VCurve;
	QwtPlotPanner *VPanner;
	QwtPlotZoomer *VZoomer;
	QCheckBox *cbVAvgCheckBox;
	QwtPlot *PTCPlot;
	QwtPlotCurve *PTCCurve;
	QwtPlotPanner *PTCPanner;
	QwtPlotZoomer *PTCZoomer;
	QwtSymbol *PTCSymbol;
	QCheckBox *cbEnableHistogram;
	QComboBox *imageMode;
	int lastw, lasth;
	bool lasthdr;
	int fetchedframe;
	int displayframe;
	int displayindex;
	int statX1, statY1, statX2, statY2;		// Signal statistics box coordinates
	int noiseX1, noiseY1, noiseX2, noiseY2;	// Noise statistics box coordinates
	int m_hplot,m_vplot;					// Horizontal and vertical line plot coordinates
	int ptccount;							// Number of frames averaged for PTC calculation
	int ptctotal;							// Total number of frames to average for PTC calculation
	double ptcmean,ptcvar;					// Cumulative mean and variance for PTC calculation
	double dv;
	int savecount;
	QVector<double> hx,hy;					// Horizontal plot points
	QVector<double> vx,vy;				// Vertical plot points
	QVector<double> ptcx,ptcy;				// PTC plot points
	QLabel *imageXYLabel;
	QLabel *filenameLabel;
	QLabel *frameLabel;
	QLabel *zoomLabel;
	QLabel *DRLabel;
	QLabel *statsLabel;
	QLabel *diffStatsLabel;
	QLabel *noiseLabel;
	QSlider *sbGain;
	QSlider *sbOffset;
	// Raw Image
	void setRawZoom(double zoom);
	void updateRawStats();
	void updateRawPlots();
	ImageScrollWidget *rawImageScroll;
	QwtPlot *rawHPlot;
	QwtPlotCurve *rawHCurve;
	QwtPlotPanner *rawHPanner;
	QwtPlotZoomer *rawHZoomer;
	QCheckBox *cbRawHAvgCheckBox;
	QwtPlot *rawVPlot;
	QwtPlotCurve *rawVCurve;
	QwtPlotPanner *rawVPanner;
	QwtPlotZoomer *rawVZoomer;
	QCheckBox *cbRawVAvgCheckBox;
	int lastraww, lastrawh;
	int rawStatX1, rawStatY1, rawStatX2, rawStatY2;		// Raw signal statistics box coordinates
	int rawNoiseX1, rawNoiseY1, rawNoiseX2, rawNoiseY2;	// Noise statistics box coordinates
	int m_rawhplot,m_rawvplot;							// Horizontal and vertical line plot coordinates
	QVector<double> rawhx, rawhy;						// Horizontal plot points
	QVector<double> rawvx, rawvy;						// Vertical plot points
	QLabel *rawStatsLabel;
	QLabel *rawNoiseLabel;
	QSlider *sbRawGain;
	QSlider *sbRawOffset;
	// Archon
	bool cmdinprogress;
	bool cmderror;
	int pollstep;
	Archon *archon;
	bool connected;
	QString sPROMFilename;
	QString lastfilename;
};

#endif // ARCHONGUI_H
