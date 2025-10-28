#ifndef ARCHON_H
#define ARCHON_H

// Optionally enable factory AD clamp level calibration
#define ENABLE_AD_CALIBRATION 0

#include <QString>
#include <QStringList>
#include <QMap>
#include <QVariant>
#include <QThread>
#include <QMutex>
#include <QTcpSocket>
#include "frames.h"

// Burst length in bytes for flash PROM reads/writes and frame buffer reads/writes
#define BURST_LEN 1024

// Raw mode block size in bytes
#define RAW_BLOCK_SIZE 2048

#define BACKPLANE_TYPE_NONE 0
#define BACKPLANE_TYPE_X12 1
#define BACKPLANE_TYPE_X16 2
#define BACKPLANE_TYPE_UNKNOWN 3

#define MAX_MODULES 16

#define MOD_TYPE_NONE 0
#define MOD_TYPE_DRIVER 1
#define MOD_TYPE_AD 2
#define MOD_TYPE_LVBIAS 3
#define MOD_TYPE_HVBIAS 4
#define MOD_TYPE_HEATER 5
#define MOD_TYPE_ATLAS 6
#define MOD_TYPE_HS 7
#define MOD_TYPE_HVXBIAS 8
#define MOD_TYPE_LVXBIAS 9
#define MOD_TYPE_LVDS 10
#define MOD_TYPE_HEATERX 11
#define MOD_TYPE_XVBIAS 12
#define MOD_TYPE_ADF 13
#define MOD_TYPE_ADX 14
#define MOD_TYPE_ADLN 15
#define MOD_TYPE_DRIVERX 16
#define MOD_TYPE_ADM 17
#define MOD_TYPE_UNKNOWN 18

typedef QMap<QString, QString> RMap;

enum POWER_STATES {PWR_UNKNOWN, PWR_NOT_CONFIGURED, PWR_OFF, PWR_INTERMEDIATE, PWR_ON, PWR_STANDBY};

enum {CONTROL_COUNT = 6};

QString hex(unsigned x, int w);
QString flt(double d, int w, int p);
QString sci(double d, int w, int p);

class Archon : public QThread
{
	Q_OBJECT
public:
	Archon(QObject *parent = 0);
	~Archon();
	void init();
	int command(const QString &cmd);
	int command(const QString &cmd, const QString &params);
	int command(const QString &cmd, const QStringList &params);
	int getResult();
	void getSystem(RMap &map);
	void getStatus(RMap &map);
	void setConfig(RMap &map);
	QVector<TFrameBuffer> frames;
	QMutex frameMutex;
signals:
	void logMessage(const QString &msg);
	void progressMessage(const QString &msg, int newstep, int newtotal);
	void msgSystem(const RMap &data);
	void msgStatus(const RMap &data);
	void msgFrameStatus(const RMap &data);
	void msgConnected(bool connected);
	void newFrame();
protected:
	void run();
private:
	// Thread control
	QMutex mutex;
	bool Abort;
	bool CommandInProgress;
	int CommandResult;
	QString NewCommand;
	QString NewParameter;
	QStringList NewParameters;
	RMap NewConfig;
	// Interface I/O
	QTcpSocket *socket;
	QString addr;
	int port;
	int openInterface();
	int closeInterface();
	int interfaceCommand(QString cmd, QString &response, int timeout, bool log = true);
	int interfaceBinaryCommand(QString cmd, QByteArray &response, int timeout, bool log = true);
	int interfaceBinaryCommand(QString cmd, char *response, int length, int timeout, bool log = true);
	void interfaceFlush();
	bool connected;
	int msgref;
	int last_msgref;
	// Commands
	int getSystem();
	int getStatus();
	int getFrameStatus(bool quiet);
	int lockFrame(QString &param);
	int lockNewestFrame();
	int fetchFrame();
	int flash(QStringList &params);
	int verify(QStringList &params);
	int reboot();
	int warmboot();
	int flashactiveconfig();
	int erasestoredconfig();
	int flashMod(QStringList &params);
	int verifyMod(QStringList &params);
	int readMCS(QString filename, const int flash_size, QByteArray &ba);
	int writeConfig();
	int applyAll();
	int powerOn();
	int powerOff();
	int pollOn();
	int pollOff();
	int loadTiming();
	int loadParams();
	int loadParam(QString paramName);
	int resetTiming();
	int holdTiming();
	int releaseTiming();
	int applySystem();
	int applyCDS();
	int applyModule(QString slot);
	int applyDIO(QString slot);
	int direct(QString cmd);
	int applyNet();
	int atlasMove(QStringList params);
	// Error handling
	QString error_message;
	int error_line;
	// Status
	RMap system;
	RMap status;
	RMap frameStatus;
	RMap config;
};

#endif // ARCHON_H
