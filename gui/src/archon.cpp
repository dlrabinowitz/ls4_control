#include "archon.h"
#include <QTime>
#include <QMetaType>
#include <QFile>
#include <QFileInfo>
#ifdef Q_OS_WIN
	#define WIN32_LEAN_AND_MEAN
	#include <windows.h>
#endif
#define LOGERROR(msg) do {error_message = msg; error_line = __LINE__; goto error;} while (0)
#if QT_VERSION < 0x050400
	#define QElapsedTimer QTime
#endif
QString hex(unsigned x, int w)
{
	return QString("%1").arg(x, w, 16, QChar('0')).toUpper();
}
QString flt(double d, int w, int p)
{
	return QString("%1").arg(d, w, 'f', p);
}
QString sci(double d, int w, int p)
{
	return QString("%1").arg(d, w, 'E', p);
}
//---------------------------------------------------------------------------
Archon::Archon(QObject *parent)
		: QThread(parent)
{
	qRegisterMetaType<RMap>("RMap");
	Abort = false;
	CommandInProgress = false;
	CommandResult = 0;
	connected = false;
	msgref = 0;
}
//---------------------------------------------------------------------------
Archon::~Archon()
{
	mutex.lock();
	Abort = true;
	mutex.unlock();
	wait();
}
//---------------------------------------------------------------------------
void Archon::run()
{
	int result = 0;
	bool ok;
	QString cmd;
	QString param;
	QStringList params;

	socket = new QTcpSocket();

	forever
	{
		// Record last command result, and check for a new command
		mutex.lock();
		if (Abort)
		{
			mutex.unlock();
			closeInterface();
			return;
		}
		CommandResult = result;
		cmd = NewCommand.toUpper();
		NewCommand.clear();
		param = NewParameter;
		NewParameter.clear();
		params = NewParameters;
		NewParameters.clear();
		CommandInProgress = !cmd.isEmpty();
		if (cmd == "CONFIG")
		{
			config = NewConfig;
			cmd.clear();
		}
		mutex.unlock();

		if (!cmd.isEmpty())
		{
			if (cmd == "SYSTEM")
				result = getSystem();
			else if (cmd == "STATUS")
				result = getStatus();
			else if (cmd == "FRAME")
				result = getFrameStatus(false);
			else if (cmd == "LOCK")
				result = lockFrame(param);
			else if (cmd == "LOCKNEWEST")
				result = lockNewestFrame();
			else if (cmd == "FETCH")
				result = fetchFrame();
			else if (cmd == "CONNECT")
			{
				addr = params.value(0);
				port = params.value(1).toInt(&ok);
				if ((!ok) || (port < 0) || (port > 65535))
				{
					result = 1;
					emit logMessage(QString("Error parsing port (%1)").arg(params.value(1)));
				}
				else
					result = openInterface();
			}
			else if (cmd == "DISCONNECT")
				result = closeInterface();
			else if (cmd == "FLASH")
				result = flash(params);
			else if (cmd == "VERIFY")
				result = verify(params);
			else if (cmd == "REBOOT")
				result = reboot();
			else if (cmd == "WARMBOOT")
				result = warmboot();
			else if (cmd == "FLASHACTIVECONFIG")
				result = flashactiveconfig();
			else if (cmd == "ERASESTOREDCONFIG")
				result = erasestoredconfig();
			else if (cmd == "FLASHMOD")
				result = flashMod(params);
			else if (cmd == "VERIFYMOD")
				result = verifyMod(params);
			else if (cmd == "APPLYALL")
				result = applyAll();
			else if (cmd == "POWERON")
				result = powerOn();
			else if (cmd == "POWEROFF")
				result = powerOff();
			else if (cmd == "POLLON")
				result = pollOn();
			else if (cmd == "POLLOFF")
				result = pollOff();
			else if (cmd == "LOADTIMING")
				result = loadTiming();
			else if (cmd == "LOADPARAMS")
				result = loadParams();
			else if (cmd == "LOADPARAM")
				result = loadParam(param);
			else if (cmd == "RESETTIMING")
				result = resetTiming();
			else if (cmd == "HOLDTIMING")
				result = holdTiming();
			else if (cmd == "RELEASETIMING")
				result = releaseTiming();
			else if (cmd == "APPLYSYSTEM")
				result = applySystem();
			else if (cmd == "APPLYCDS")
				result = applyCDS();
			else if (cmd == "APPLYMOD")
				result = applyModule(param);
			else if (cmd == "APPLYDIO")
				result = applyDIO(param);
			else if (cmd == "DIRECT")
				result = direct(param);
			else if (cmd == "APPLYNET")
				result = applyNet();
			else if (cmd == "ATLASMOVE")
				result = atlasMove(params);
			else
			{
				result = 1;
				emit logMessage(QString("Unknown command received (%1)").arg(cmd));
			}
			cmd.clear();
		}

		// Sleep and clear spurious messages before checking for next command
		msleep(10);
		interfaceFlush();
	}
}
//---------------------------------------------------------------------------
void Archon::init()
{
	// Start communication thread
	start();
}
//---------------------------------------------------------------------------
int Archon::command(const QString &cmd)
{
	mutex.lock();
	if (CommandInProgress)
	{
		mutex.unlock();
		return 1;
	}
	CommandInProgress = true;
	NewCommand = cmd;
	NewParameters.clear();
	mutex.unlock();
	return 0;
}
//---------------------------------------------------------------------------
int Archon::command(const QString &cmd, const QString &param)
{
	mutex.lock();
	if (CommandInProgress)
	{
		mutex.unlock();
		return 1;
	}
	CommandInProgress = true;
	NewCommand = cmd;
	NewParameter = param;
	mutex.unlock();
	return 0;
}
//---------------------------------------------------------------------------
int Archon::command(const QString &cmd, const QStringList &params)
{
	mutex.lock();
	if (CommandInProgress)
	{
		mutex.unlock();
		return 1;
	}
	CommandInProgress = true;
	NewCommand = cmd;
	NewParameters = params;
	mutex.unlock();
	return 0;
}
//---------------------------------------------------------------------------
int Archon::getResult()
{
	int i;

	forever
	{
		mutex.lock();
		if (!CommandInProgress)
		{
			i = CommandResult;
			mutex.unlock();
			return i;
		}
		mutex.unlock();
		msleep(50);
	}
}
//---------------------------------------------------------------------------
void Archon::getStatus(RMap &map)
{
	forever
	{
		mutex.lock();
		if (!CommandInProgress)
		{
			mutex.unlock();
			map = status;
			return;
		}
		mutex.unlock();
		msleep(50);
	}
}
//---------------------------------------------------------------------------
void Archon::setConfig(RMap &map)
{
	forever
	{
		mutex.lock();
		if (!CommandInProgress)
		{
			CommandInProgress = true;
			NewCommand = "CONFIG";
			NewParameters.clear();
			NewConfig = map;
			mutex.unlock();
			return;
		}
		mutex.unlock();
		msleep(50);
	}
}
//---------------------------------------------------------------------------
int Archon::openInterface()
{
	// Close interface if already open
	closeInterface();
	// Open communication interface
	socket->connectToHost(addr, port);
	if (!socket->waitForConnected(1000))
		LOGERROR("Error connecting");
	connected = true;
	emit msgConnected(true);
	return 0;

	error:
	emit logMessage("! openInterface: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::closeInterface()
{
	// Close any open connection
	if (connected)
	{
		socket->disconnectFromHost();
		if (socket->state() != QAbstractSocket::UnconnectedState)
		{
			if (!socket->waitForDisconnected(1000))
				socket->abort();
		}
		emit msgConnected(false);
	}
	socket->close();

	connected = false;
	return 0;
}
//---------------------------------------------------------------------------
int Archon::interfaceCommand(QString cmd, QString &response, int timeout, bool log)
{
	QByteArray ba;
	QElapsedTimer t;
	QString s;
	bool ok;

	// Open communications interface if necessary
	if (!connected || (socket->state() != QAbstractSocket::ConnectedState))
	{
		if (openInterface())
			LOGERROR("Error opening communications interface");
	}

	// Process command
	if (!cmd.isEmpty())
	{
		socket->readAll();
		last_msgref = msgref;
		msgref = (msgref + 1) & 0xFF;
		cmd.prepend(">" + hex(last_msgref, 2));
		cmd.append("\n");
		ba = cmd.toLatin1();
		socket->write(ba);
		if (!socket->flush())
			if (!socket->waitForBytesWritten(timeout))
				LOGERROR("Error writing to socket");
		if (log)
			emit logMessage(cmd.trimmed());
	}

	// Get response
	response.clear();
	t.start();
	forever
	{
		// Check for a timeout
		if (t.elapsed() > timeout)
			LOGERROR("Timeout waiting for response");
		// Check for a reply
		if (socket->canReadLine())
		{
			response = socket->readLine().trimmed();
			// Check that this reply matches the command we sent
			if ((response.length() >= 3) && (response.mid(1, 2).toInt(&ok, 16) == last_msgref))
			{
				if (response[0] == '<')
				{
					response.remove(0, 3);
					break;
				}
				else if (response[0] == '?')
					LOGERROR("Error parsing command");
			}
		}
		else
			socket->waitForReadyRead(10);
	}
	if (log)
		emit logMessage(response);
	return 0;

	error:
	emit logMessage("! interfaceCommand: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::interfaceBinaryCommand(QString cmd, QByteArray &response, int timeout, bool log)
{
	QByteArray ba;
	QElapsedTimer t;
	QString s;
	bool ok, gotPreamble;

	// Open communications interface if necessary
	if (!connected || (socket->state() != QAbstractSocket::ConnectedState))
	{
		if (openInterface())
			LOGERROR("Error opening communications interface");
	}

	// Process command
	if (!cmd.isEmpty())
	{
		socket->readAll();
		last_msgref = msgref;
		msgref = (msgref + 1) & 0xFF;
		cmd.prepend(">" + hex(last_msgref, 2));
		cmd.append("\n");
		ba = cmd.toLatin1();
		socket->write(ba);
		if (!socket->flush())
			if (!socket->waitForBytesWritten(timeout))
				LOGERROR("Error writing to socket");
		if (log)
			emit logMessage(cmd.trimmed());
	}

	// Get response
	response.clear();
	t.start();
	gotPreamble = false;
	forever
	{
		// Check for a timeout
		if (t.elapsed() > timeout)
			LOGERROR("Timeout waiting for response");
		// Check for a reply
		if ((socket->bytesAvailable() >= 4) || socket->waitForReadyRead(10))
		{
			if (!gotPreamble && (socket->bytesAvailable() >= 4))
			{
				response = socket->read(4);
				// Check that this reply matches the command we sent
				if ((response[0] == '<') && (response.mid(1, 2).toInt(&ok, 16) == last_msgref) && (response[3] == ':'))
				{
					response.clear();
					gotPreamble = true;
				}
				else
					LOGERROR("Error parsing binary response preamble");
			}
			if (gotPreamble)
			{
				response.append(socket->read(BURST_LEN - response.length()));
				if (response.length() == BURST_LEN)
					break;
			}
		}
	}
	if (log)
		emit logMessage(QString("Received %1 bytes").arg(response.length()));
	return 0;

	error:
	emit logMessage("! interfaceBinaryCommand: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::interfaceBinaryCommand(QString cmd, char *response, int length, int timeout, bool log)
{
	QByteArray ba;
	QString s;
	QElapsedTimer t;
	qint64 e, pos, bufpos;
	bool ok, gotPreamble;
	int i;
	char buf[BURST_LEN];

	// Open communications interface if necessary
	if (!connected || (socket->state() != QAbstractSocket::ConnectedState))
	{
		if (openInterface())
			LOGERROR("Error opening communications interface");
	}

	// Process command
	if (!cmd.isEmpty())
	{
		socket->readAll();
		last_msgref = msgref;
		msgref = (msgref + 1) & 0xFF;
		cmd.prepend(">" + hex(last_msgref, 2));
		cmd.append("\n");
		ba = cmd.toLatin1();
		socket->write(ba);
		if (!socket->flush())
			if (!socket->waitForBytesWritten(timeout))
				LOGERROR("Error writing to socket");
		if (log)
			emit logMessage(cmd.trimmed());
	}

	// Get response
	ba.clear();
	pos = 0;
	bufpos = 0;
	gotPreamble = false;
	t.start();
	forever
	{
		// Check for a timeout
		if (t.elapsed() > timeout)
			LOGERROR("Timeout waiting for response");
		// Check for a reply
		if ((socket->bytesAvailable() >= 4) || socket->waitForReadyRead(10))
		{
			if (!gotPreamble && (socket->bytesAvailable() >= 4))
			{
				ba = socket->read(4);
				// Check that this reply matches the command we sent
				if ((ba[0] == '<') && (ba.mid(1, 2).toInt(&ok, 16) == last_msgref) && (ba[3] == ':'))
					gotPreamble = true;
				else
					LOGERROR("Error parsing binary response preamble");
			}
			if (gotPreamble)
			{
				e = socket->read(buf + bufpos, BURST_LEN - bufpos);
				if (e > 0)
				{
					pos += e;
					bufpos += e;
					t.start();
				}
				if (bufpos == BURST_LEN)
				{
					i = qMin(BURST_LEN, length);
					memcpy(response, buf, i);
					response += i;
					length -= i;
					bufpos = 0;
					if (length == 0)
						break;
					else
						gotPreamble = false;
				}
			}
		}
	}
	if (log)
		emit logMessage(QString("Received %1 bytes").arg(pos));
	return 0;

	error:
	emit logMessage("! interfaceBinaryCommand: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
void Archon::interfaceFlush()
{
	if (!connected || (socket->state() != QAbstractSocket::ConnectedState))
		return;
	socket->waitForReadyRead(10);
	socket->readAll();
}
//---------------------------------------------------------------------------
int Archon::getSystem()
{
	QString s, field;
	QStringList tokens, fields;

	system.clear();
	interfaceFlush();
	if (interfaceCommand("SYSTEM", s, 1000, false))
		LOGERROR("Error reading system configuration");
	fields = s.split(' ');
	foreach (field, fields)
	{
		tokens = field.split('=');
		if (tokens.count() != 2)
			LOGERROR("Error reading system configuration");
		system.insert(tokens[0], tokens[1]);
	}
	emit msgSystem(system);
	return 0;

	error:
	emit logMessage("! getSystem: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	emit msgSystem(system);
	return 1;
}
//---------------------------------------------------------------------------
int Archon::getStatus()
{
	QString s, field;
	QStringList tokens, fields;
	int i, logs;

	status.clear();
	interfaceFlush();
	if (interfaceCommand("STATUS", s, 1000, false))
		LOGERROR("Error reading status");
	fields = s.split(' ');
	foreach (field, fields)
	{
		tokens = field.split('=');
		if (tokens.count() != 2)
			LOGERROR("Error reading status");
		status.insert(tokens[0], tokens[1]);
	}
	emit msgStatus(status);
	logs = status.value("LOG", "-").toInt();
	for (i = 0; i < logs; i++)
	{
		if (interfaceCommand("FETCHLOG", s, 1000, false))
			LOGERROR("Error reading log message");
		emit logMessage(s);
	}
	return 0;

	error:
	emit logMessage("! getStatus: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	emit msgStatus(status);
	return 1;
}
//---------------------------------------------------------------------------
int Archon::getFrameStatus(bool quiet)
{
	QString s, field;
	QStringList tokens, fields;

	frameStatus.clear();
	interfaceFlush();
	if (interfaceCommand("FRAME", s, 1000, false))
		LOGERROR("Error reading frame status");
	fields = s.split(' ');
	foreach (field, fields)
	{
		tokens = field.split('=');
		if (tokens.count() != 2)
			LOGERROR("Error reading frame status");
		frameStatus.insert(tokens[0], tokens[1]);
	}
	if (!quiet)
		emit msgFrameStatus(frameStatus);
	return 0;

	error:
	emit logMessage("! getFrameStatus: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	emit msgStatus(frameStatus);
	return 1;
}
//---------------------------------------------------------------------------
int Archon::lockFrame(QString &param)
{
	QString s;

	if ((param != "1") && (param != "2") && (param != "3"))
		LOGERROR("Invalid frame buffer");
	s = "LOCK" + param;
	if (interfaceCommand(s, s, 1000, false))
		LOGERROR("Error locking frame buffer");
	return 0;

	error:
	emit logMessage("! lockFrame: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::lockNewestFrame()
{
	int i, buf;
	QString s;
	unsigned frames[3];

	if (getFrameStatus(true))
		goto error;
	frames[0] = frameStatus.value("BUF1FRAME", "-").toUInt();
	frames[1] = frameStatus.value("BUF2FRAME", "-").toUInt();
	frames[2] = frameStatus.value("BUF3FRAME", "-").toUInt();
	buf = 0;
	for (i = 1; i < 3; i++)
		if (frames[i] > frames[buf])
			buf = i;
	s = "LOCK" + QString::number(buf + 1);
	if (interfaceCommand(s, s, 1000, false))
		LOGERROR("Error locking frame buffer");
	return 0;

	error:
	emit logMessage("! lockFrame: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::readMCS(QString filename, const int flash_size, QByteArray &ba)
{
	QFile file;
	QTextStream ts;
	QString s;
	int i, segaddr, addr, recordtype, len;
	bool ok;
	unsigned u;

	// Open file
	file.setFileName(filename);
	if (!file.open(QIODevice::ReadOnly))
		LOGERROR("Error opening file");
	ts.setDevice(&file);
	// Allocate memory
	ba.fill(0xFF, flash_size);
	segaddr = 0;
	// Read file
	while (!ts.atEnd())
	{
		s = ts.readLine();
		if (s.startsWith(':'))
		{
			len = s.mid(1, 2).toInt(&ok, 16);
			if (!ok)
				LOGERROR("Error reading file");
			addr = s.mid(3, 4).toInt(&ok, 16);
			if (!ok)
				LOGERROR("Error reading file");
			recordtype = s.mid(7, 2).toInt(&ok, 16);
			if (!ok)
				LOGERROR("Error reading file");
			s.remove(0, 9);
			if (recordtype == 0)
			{
				addr += segaddr;
				if (addr + len > flash_size)
					LOGERROR("File too large");
				for (i = 0; i < len; i++)
				{
					u = s.left(2).toUInt(&ok, 16);
					s.remove(0, 2);
					if (!ok)
						LOGERROR("Error reading file");
					ba[addr++] = (unsigned char)u;
				}
			}
			else if (recordtype == 4)
			{
				u = s.left(4).toUInt(&ok, 16);
				segaddr = u << 16;
			}
		}
	}
	return 0;

	error:
	emit logMessage("! readMCS: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	emit msgStatus(status);
	return 1;
}

//---------------------------------------------------------------------------
int Archon::flash(QStringList &params)
{
	QByteArray ba;
	QString s, t;
	int i, line, type, rev;
	const int line_size = BURST_LEN;
	const int sector_size = 65536;
	int flash_size, lines, fwstart, fwend, codestart, codeend, configstart, configend, sectors;
	bool blank;
	bool flashBackplane = params.value(1) == "1";
	bool flashCode = params.value(2) == "1";
	bool flashConfig = params.value(3) == "1";
	QFileInfo fi;

	// Expected base filename
	type = system.value("BACKPLANE_TYPE").toInt();
	if ((type <= BACKPLANE_TYPE_NONE) || (type >= BACKPLANE_TYPE_UNKNOWN))
		LOGERROR("Empty or unknown backplane");
	t = "archonbackplane";
	if (type == BACKPLANE_TYPE_X16)
	{
		t += "x16";
		flash_size = 32 * 1024 * 1024;
		sectors = 512;
		fwstart = 0;
		fwend = 256;
		codestart = 256;
		codeend = 320;
		configstart = 384;
		configend = 448;
	}
	else
	{
		flash_size = 16 * 1024 * 1024;
		sectors = 256;
		fwstart = 0;
		fwend = 128;
		codestart = 128;
		codeend = 192;
		configstart = 192;
		configend = 256;
	}
	lines = flash_size / line_size;
	t += "rev";
	rev = system.value("BACKPLANE_REV").toInt();
	t += QLatin1Char('a' + rev);
	fi.setFile(params.value(0));
	s = fi.baseName();
	if (!s.startsWith(t))
		LOGERROR("Firmware filename does not match backplane");

	interfaceFlush();

	// Load PROM file
	if (readMCS(params.value(0), flash_size, ba))
		LOGERROR("Error reading MCS file");

	// Disable polling to speed up flash operation
	if (interfaceCommand("BIASPOLLOFF", s, 1000, false))
		LOGERROR("Error disabling bias polling");

	// Erase PROM
	if (flashBackplane)
	{
		for (i = fwstart; i < fwend; i++)
		{
			emit progressMessage("Erasing PROM... (this can take up to 10 minutes)", i, sectors);
			s = "ERASE" + hex(i * 0x10000, 8) + "00010000";
			if (interfaceCommand(s, s, 3000, false))
				LOGERROR("Error erasing PROM");
		}
	}
	if (flashCode)
	{
		for (i = codestart; i < codeend; i++)
		{
			emit progressMessage("Erasing PROM... (this can take up to 10 minutes)", i, sectors);
			s = "ERASE" + hex(i * 0x10000, 8) + "00010000";
			if (interfaceCommand(s, s, 3000, false))
				LOGERROR("Error erasing PROM");
		}
	}
	if (flashConfig)
	{
		for (i = configstart; i < configend; i++)
		{
			emit progressMessage("Erasing PROM... (this can take up to 10 minutes)", i, sectors);
			s = "ERASE" + hex(i * 0x10000, 8) + "00010000";
			if (interfaceCommand(s, s, 3000, false))
				LOGERROR("Error erasing PROM");
		}
	}

	// Write each BURST_LEN byte line
	for (line = 0; line < lines; line++)
	{
		mutex.lock();
		if (Abort)
		{
			mutex.unlock();
			LOGERROR("Flash aborted!");
		}
		mutex.unlock();
		emit progressMessage("Flashing PROM...", line, lines);
		// Skip blank lines (all 0xFF)
		blank = true;
		for (i = 0; i < line_size; i++)
			if (ba[line * line_size + i] != char(0xFF))
			{
				blank = false;
				break;
			}
		if (blank)
			continue;
		// Skip lines we're not flashing
		if ((!flashBackplane) && (line * line_size >= fwstart * sector_size) && (line * line_size < fwend * sector_size))
			continue;
		if ((line * line_size >= fwend * sector_size) && (line * line_size < codestart * sector_size))
			continue;
		if ((!flashCode) && (line * line_size >= codestart * sector_size) && (line * line_size < codeend * sector_size))
			continue;
		if ((line * line_size >= codeend * sector_size) && (line * line_size < configstart * sector_size))
			continue;
		if ((!flashConfig) && (line * line_size >= configstart * sector_size) && (line * line_size < configend * sector_size))
			continue;
		if (line * line_size >= configend * sector_size)
			continue;
		if (type == BACKPLANE_TYPE_X16)
			s = "FLASH" + hex(line * line_size, 8);
		else
			s = "FLASH" + hex((line * line_size) >> 8, 4);
		for (i = 0; i < line_size; i++)
			s.append(hex((unsigned char)ba[line * line_size + i], 2));
		if (interfaceCommand(s, s, 1000, false))
			LOGERROR(QString("Error flashing line (address 0x%1").arg(line * line_size, 0, 16));
	}
	emit progressMessage("Idle", 0, 1);
	if (verify(params))
		LOGERROR("Verify failed");

	emit logMessage("PROM flashed successfully");
	// Reenable polling
	interfaceCommand("BIASPOLLON", s, 1000, false);
	return 0;

	error:
	emit logMessage(QString("! flash: %1 (%2:%3)").arg(error_message).arg(__FILE__).arg(error_line));
	emit progressMessage("Idle", 0, 1);
	// Reenable polling
	interfaceCommand("BIASPOLLON", s, 1000, false);
	return 1;
}
//---------------------------------------------------------------------------
int Archon::verify(QStringList &params)
{
	QByteArray ba, response;
	QString s;
	int i, j, line, group, type;
	const int line_size = BURST_LEN;
	const int group_size = 256;
	const int sector_size = 65536;
	int flash_size, fwstart, fwend, codestart, codeend, configstart, configend, groups;
	bool flashBackplane = params.value(1) == "1";
	bool flashCode = params.value(2) == "1";
	bool flashConfig = params.value(3) == "1";

	type = system.value("BACKPLANE_TYPE").toInt();
	if ((type <= BACKPLANE_TYPE_NONE) || (type >= BACKPLANE_TYPE_UNKNOWN))
		LOGERROR("Empty or unknown backplane");
	if (type == BACKPLANE_TYPE_X16)
	{
		flash_size = 32 * 1024 * 1024;
		fwstart = 0;
		fwend = 256;
		codestart = 256;
		codeend = 320;
		configstart = 384;
		configend = 448;
	}
	else
	{
		flash_size = 16 * 1024 * 1024;
		fwstart = 0;
		fwend = 128;
		codestart = 128;
		codeend = 192;
		configstart = 192;
		configend = 256;
	}
	groups = flash_size / line_size / group_size;

	interfaceFlush();

	// Load PROM file
	if (readMCS(params.value(0), flash_size, ba))
		LOGERROR("Error reading MCS file");

	// Disable polling to speed up verify operation
	if (interfaceCommand("BIASPOLLOFF", s, 1000, false))
		LOGERROR("Error disabling bias polling");

	// Verify each group of BURST_LEN byte lines
	for (group = 0; group < groups; group++)
	{
		mutex.lock();
		if (Abort)
		{
			mutex.unlock();
			LOGERROR("Verify aborted!");
		}
		mutex.unlock();
		line = group * group_size;
		emit progressMessage("Verifying PROM...", group, groups);
		// Skip lines we're not verifying
		if ((!flashBackplane) && (line * line_size >= fwstart * sector_size) && (line * line_size < fwend * sector_size))
			continue;
		if ((line * line_size >= fwend * sector_size) && (line * line_size < codestart * sector_size))
			continue;
		if ((!flashCode) && (line * line_size >= codestart * sector_size) && (line * line_size < codeend * sector_size))
			continue;
		if ((line * line_size >= codeend * sector_size) && (line * line_size < configstart * sector_size))
			continue;
		if ((!flashConfig) && (line * line_size >= configstart * sector_size) && (line * line_size < configend * sector_size))
			continue;
		if (line * line_size >= configend * sector_size)
			continue;
		if (type == BACKPLANE_TYPE_X16)
			s = "VERIFY" + hex(line * line_size, 8) + hex(group_size, 8);
		else
			s = "VERIFY" + hex((line * line_size) >> 8, 4) + hex(group_size, 4);
		for (i = 0; i < group_size; i++)
		{
			line = group * group_size + i;
			if (i)
				s.clear();
			if (interfaceBinaryCommand(s, response, 2000, false) || (response.length() != line_size))
				LOGERROR(QString("Error reading data to verify (address 0x%1)").arg(line * line_size, 0, 16));
			for (j = 0; j < line_size; j++)
			{
				if (ba[line * line_size + j] != response[j])
					LOGERROR(QString("Error verifying data (address 0x%1)").arg((line * line_size) + j, 0, 16));
			}
		}
	}
	emit logMessage("PROM verified successfully");
	emit progressMessage("Idle", 0, 1);
	// Reenable polling
	interfaceCommand("BIASPOLLON", s, 1000, false);
	return 0;

error:
	emit logMessage(QString("! verify: %1 (%2:%3)").arg(error_message).arg(__FILE__).arg(error_line));
	emit progressMessage("Idle", 0, 1);
	// Reenable polling
	interfaceCommand("BIASPOLLON", s, 1000, false);
	return 1;
}
//---------------------------------------------------------------------------
int Archon::reboot()
{
	QString s;

	interfaceCommand("REBOOT", s, 1000, false);
	return 0;
}
//---------------------------------------------------------------------------
int Archon::warmboot()
{
	QString s;

	interfaceCommand("WARMBOOT", s, 1000, false);
	return 0;
}
//---------------------------------------------------------------------------
int Archon::flashactiveconfig()
{
	QString s;

	interfaceCommand("FLASHACTIVECONFIG", s, 60000, false);
	return 0;
}
//---------------------------------------------------------------------------
int Archon::erasestoredconfig()
{
	QString s;

	interfaceCommand("ERASESTOREDCONFIG", s, 60000, false);
	return 0;
}
//---------------------------------------------------------------------------
int Archon::flashMod(QStringList &params)
{
	QByteArray ba;
	QString s, t;
	int i, line, id;
	const int line_size = BURST_LEN;
	int flash_size = 1024 * 1024;
	int lines = flash_size / line_size;
	bool blank;
	int module = params.value(1, "-1").toInt();
	QFileInfo fi;

	if ((module < 0) || (module >= MAX_MODULES))
		LOGERROR("Module number out of range");

	// Expected base filename
	id = system.value(QString("MOD%1_TYPE").arg(module + 1)).toInt();
	if ((id <= MOD_TYPE_NONE) || (id >= MOD_TYPE_UNKNOWN))
		LOGERROR("Empty or unknown module");
	switch (id)
	{
	case MOD_TYPE_DRIVER:
		t = "archondriver"; break;
	case MOD_TYPE_DRIVERX:
		t = "archondriverx"; break;
	case MOD_TYPE_AD:
		t = "archonad"; break;
	case MOD_TYPE_ADF:
		t = "archonadf"; break;
	case MOD_TYPE_ADLN:
		t = "archonadln"; break;
	case MOD_TYPE_ADM:
		flash_size = 4 * 1024 * 1024;
		lines = flash_size / line_size;
		t = "archonadm"; break;
	case MOD_TYPE_ADX:
		flash_size = 8 * 1024 * 1024;
		lines = flash_size / line_size;
		t = "archonadx"; break;
	case MOD_TYPE_LVBIAS:
		t = "archonlvbias"; break;
	case MOD_TYPE_HVBIAS:
		t = "archonhvbias"; break;
	case MOD_TYPE_HEATER:
		t = "archonheater"; break;
	case MOD_TYPE_ATLAS:
		t = "archonatlas"; break;
	case MOD_TYPE_HS:
		t = "archonhs"; break;
	case MOD_TYPE_HVXBIAS:
		t = "archonhvxbias"; break;
	case MOD_TYPE_LVXBIAS:
		t = "archonlvxbias"; break;
	case MOD_TYPE_LVDS:
		t = "archonlvds"; break;
	case MOD_TYPE_HEATERX:
		t = "archonheaterx"; break;
	case MOD_TYPE_XVBIAS:
		t = "archonxvbias"; break;
	}
	t += "rev";
	id = system.value(QString("MOD%1_REV").arg(module + 1)).toInt();
	t += QLatin1Char('a' + id);
	fi.setFile(params.value(0));
	s = fi.baseName();
	if (!s.startsWith(t))
		LOGERROR("Firmware filename does not match module");

	interfaceFlush();

	// Load PROM file
	if (readMCS(params.value(0), flash_size, ba))
		LOGERROR("Error reading MCS file");

	// Disable polling to speed up flash operation
	if (interfaceCommand("BIASPOLLOFF", s, 1000, false))
		LOGERROR("Error disabling bias polling");

	// Erase PROM
	emit progressMessage("Erasing PROM... (this can take a few minutes)", 0, 1);
	s = "ERASEMOD" + hex(module, 2);
	if (interfaceCommand(s, s, 200000, false))
		LOGERROR("Error erasing PROM");

	// Write each BURST_LEN byte line
	for (line = 0; line < lines; line++)
	{
		mutex.lock();
		if (Abort)
		{
			mutex.unlock();
			LOGERROR("Flash aborted!");
		}
		mutex.unlock();
		emit progressMessage("Flashing PROM...", line, lines);
		// Skip blank lines (all 0xFF)
		blank = true;
		for (i = 0; i < line_size; i++)
			if (ba[line * line_size + i] != char(0xFF))
			{
				blank = false;
				break;
			}
		if (blank)
			continue;
		s = "FLASHMOD" + hex(module, 2) + hex((line * line_size) >> 8, 4);
		for (i = 0; i < line_size; i++)
			s.append(hex((unsigned char)ba[line * line_size + i], 2));
		if (interfaceCommand(s, s, 1000, false))
			LOGERROR(QString("Error flashing line (address 0x%1").arg(line * line_size, 0, 16));
	}
	emit progressMessage("Idle", 0, 1);
	if (verifyMod(params))
		LOGERROR("Verify failed");

	emit logMessage("PROM flashed successfully");
	// Reenable polling
	interfaceCommand("BIASPOLLON", s, 1000, false);
	return 0;

	error:
	emit logMessage(QString("! flashMod: %1 (%2:%3)").arg(error_message).arg(__FILE__).arg(error_line));
	emit progressMessage("Idle", 0, 1);
	// Reenable polling
	interfaceCommand("BIASPOLLON", s, 1000, false);
	return 1;
}
//---------------------------------------------------------------------------
int Archon::verifyMod(QStringList &params)
{
	QByteArray ba, response;
	QString s;
	int i, j, line, group, id;
	const int line_size = BURST_LEN;
	const int group_size = 16;
	int flash_size = 1024 * 1024;
	int groups = flash_size / line_size / group_size;
	int module = params.value(1, "-1").toInt();

	if ((module < 0) || (module >= MAX_MODULES))
		LOGERROR("Module number out of range");

	interfaceFlush();

	// Adjust flash size if necessary
	id = system.value(QString("MOD%1_TYPE").arg(module + 1)).toInt();
	if ((id <= MOD_TYPE_NONE) || (id >= MOD_TYPE_UNKNOWN))
		LOGERROR("Empty or unknown module");
	switch (id)
	{
	case MOD_TYPE_ADX:
		flash_size = 8 * 1024 * 1024;
		groups = flash_size / line_size / group_size;
		break;
	case MOD_TYPE_ADM:
		flash_size = 4 * 1024 * 1024;
		groups = flash_size / line_size / group_size;
		break;
	}

	// Load PROM file
	if (readMCS(params.value(0), flash_size, ba))
		LOGERROR("Error reading MCS file");

	// Disable polling to speed up verify operation
	if (interfaceCommand("BIASPOLLOFF", s, 1000, false))
		LOGERROR("Error disabling bias polling");

	// Verify each group of BURST_LEN byte lines
	for (group = 0; group < groups; group++)
	{
		mutex.lock();
		if (Abort)
		{
			mutex.unlock();
			LOGERROR("Verify aborted!");
		}
		mutex.unlock();
		line = group * group_size;
		emit progressMessage("Verifying PROM...", group, groups);
		s = "VERIFYMOD" + hex(module, 2) + hex((line * line_size) >> 8, 4) + hex(group_size, 4);
		for (i = 0; i < group_size; i++)
		{
			line = group * group_size + i;
			if (i)
				s.clear();
			if (interfaceBinaryCommand(s, response, 2000, false) || (response.length() != line_size))
				LOGERROR(QString("Error reading data to verify (address 0x%1)").arg(line * line_size, 0, 16));
			for (j = 0; j < line_size; j++)
			{
				if (ba[line * line_size + j] != response[j])
					LOGERROR(QString("Error verifying data (address 0x%1)").arg((line * line_size) + j, 0, 16));
			}
		}
	}
	emit logMessage("PROM verified successfully");
	emit progressMessage("Idle", 0, 1);
	// Reenable polling
	interfaceCommand("BIASPOLLON", s, 1000, false);
	return 0;

error:
	emit logMessage(QString("! verifyMod: %1 (%2:%3)").arg(error_message).arg(__FILE__).arg(error_line));
	emit progressMessage("Idle", 0, 1);
	// Reenable polling
	interfaceCommand("BIASPOLLON", s, 1000, false);
	return 1;
}
//---------------------------------------------------------------------------
int Archon::fetchFrame()
{
	QString s;
	int i;
	unsigned lines;
	const int line_size = BURST_LEN;
	unsigned chunk, chunks;
	const int chunk_size = 1024 * BURST_LEN;
	int framew, frameh, frame_size, bytes_remaining;
	int rawblocks, rawlines, rawsize, rawoffset;
	int samplemode;
	int oldestframe, oldestindex;
	unsigned framenum, baseaddr;
	unsigned rbuf;
	char *p;

	// Get current locked frame buffer for reading
	oldestframe = -1;
	oldestindex = -1;
	if (getFrameStatus(true))
		goto error;
	rbuf = frameStatus.value("RBUF", "-").toInt();
	if ((rbuf < 1) || (rbuf > 3))
		LOGERROR("Invalid buffer");
	framenum = frameStatus.value(QString("BUF%1FRAME").arg(rbuf), "-").toUInt();
	if (rbuf == 1)
		baseaddr = frameStatus.value("BUF1BASE", "2684354560").toUInt();	// 0xA0000000
	else if (rbuf == 2)
		baseaddr = frameStatus.value("BUF2BASE", "3221225472").toUInt();	// 0xC0000000
	else
		baseaddr = frameStatus.value("BUF3BASE", "3758096384").toUInt();	// 0xE0000000
	framew = frameStatus.value(QString("BUF%1WIDTH").arg(rbuf), "-").toUInt();
	frameh = frameStatus.value(QString("BUF%1HEIGHT").arg(rbuf), "-").toUInt();
	samplemode = frameStatus.value(QString("BUF%1SAMPLE").arg(rbuf), "-").toInt();
	if (samplemode)
		frame_size = 4 * framew * frameh;
	else
		frame_size = 2 * framew * frameh;
	lines = (frame_size + line_size - 1) / line_size;
	chunks = (frame_size + chunk_size - 1) / chunk_size;
	rawblocks = frameStatus.value(QString("BUF%1RAWBLOCKS").arg(rbuf), "-").toUInt();
	rawlines = frameStatus.value(QString("BUF%1RAWLINES").arg(rbuf), "-").toUInt();
	rawsize = rawblocks * rawlines * RAW_BLOCK_SIZE;
	rawoffset = frameStatus.value(QString("BUF%1RAWOFFSET").arg(rbuf), "-").toUInt();

	// Ignore empty frames
	if ((framenum == 0) || (framew <= 0) || (frameh <= 0))
		return 0;

	// Find oldest unlocked frame buffer to overwrite
	frameMutex.lock();
	for (i = 0; i < frames.count(); i++)
	{
		// We're only interested in framebuffers we can lock, and that can store the image
		if (!frames[i].Locked)
		{
			if ((oldestindex == -1) || (frames[i].Frame < oldestframe))
			{
				// Frame the correct size?
				if (frames[i].isEmpty() || (frames[i].width() != framew) || (frames[i].height() != frameh) || (frames[i].isHDR() != samplemode))
					// Resize framebuffer
					if (frames[i].setSize(framew, frameh, samplemode))
					{
						// Failed to allocate the memory, so don't use this buffer
						emit logMessage("Warning, failed to allocate an image buffer");
						continue;
					}
				if ((frames[i].rawwidth() != rawblocks * RAW_BLOCK_SIZE / 2) || (frames[i].rawheight() != rawlines))
					if (frames[i].setRawSize(rawblocks * RAW_BLOCK_SIZE / 2, rawlines))
					{
						// Failed to allocate the memory, so don't use this buffer
						emit logMessage("Warning, failed to allocate a raw image buffer");
						continue;
					}
				// This is the first unlocked frame we've found
				oldestframe = frames[i].Frame;
				oldestindex = i;
			}
		}
	}
	// Did we find a framebuffer to fill?
	if (oldestindex < 0)
	{
		frameMutex.unlock();
		LOGERROR("Dropped frame, no buffer available to fill");
	}
	frames[oldestindex].Locked = true;
	frames[oldestindex].Frame = framenum;
	frameMutex.unlock();

	// Read frame chunk_size bytes at a time
	bytes_remaining = frame_size;
	s = "FETCH" + hex(baseaddr, 8) + hex(lines, 8);
	p = (char *)frames[oldestindex].Data;
	for (chunk = 0; chunk < chunks; chunk++)
	{
		mutex.lock();
		if (Abort)
		{
			frameMutex.lock();
			frames[oldestindex].Locked = false;
			frameMutex.unlock();
			mutex.unlock();
			LOGERROR("Fetch aborted!");
		}
		mutex.unlock();
		emit progressMessage("Fetching frame...", chunk, chunks);
		if (interfaceBinaryCommand(s, p, qMin(bytes_remaining, chunk_size), 1000, false))
			LOGERROR(QString("Error fetching frame data (address 0x%1)").arg(baseaddr + (chunk * chunk_size), 0, 16));
		s.clear();
		bytes_remaining -= qMin(bytes_remaining, chunk_size);
		p += chunk_size;
	}
	// Read raw frame chunk_size bytes at a time
	bytes_remaining = rawsize;
	lines = (rawsize + line_size - 1) / line_size;
	chunks = (rawsize + chunk_size - 1) / chunk_size;
	s = "FETCH" + hex(baseaddr + rawoffset, 8) + hex(lines, 8);
	p = (char *)frames[oldestindex].RawData;
	for (chunk = 0; chunk < chunks; chunk++)
	{
		mutex.lock();
		if (Abort)
		{
			frameMutex.lock();
			frames[oldestindex].Locked = false;
			frameMutex.unlock();
			mutex.unlock();
			LOGERROR("Fetch aborted!");
		}
		mutex.unlock();
		emit progressMessage("Fetching raw frame...", chunk, chunks);
		if (interfaceBinaryCommand(s, p, qMin(bytes_remaining, chunk_size), 1000, false))
			LOGERROR(QString("Error fetching raw frame data (address 0x%1)").arg(baseaddr + (rawoffset + chunk * chunk_size), 0, 16));
		s.clear();
		bytes_remaining -= qMin(bytes_remaining, chunk_size);
		p += chunk_size;
	}
	// Unlock frame buffer
	if (interfaceCommand("LOCK0", s, 1000, false))
		LOGERROR("Error unlocking frame buffer");
	// Notify world of new frame
	frameMutex.lock();
	frames[oldestindex].Locked = false;
	frameMutex.unlock();
	emit newFrame();
	emit progressMessage("Idle", 0, 1);
	return 0;

error:
	frameMutex.lock();
	if (oldestindex >= 0)
		frames[oldestindex].Locked = false;
	frameMutex.unlock();
	emit logMessage(QString("! fetchFrame: %1 (%2:%3)").arg(error_message).arg(__FILE__).arg(error_line));
	emit progressMessage("Idle", 0, 1);
	return 1;
}
//---------------------------------------------------------------------------
int Archon::writeConfig()
{
	int line;
	QString s;
	RMap::const_iterator i;

	interfaceFlush();
	if (interfaceCommand("POLLOFF", s, 1000, false))
		LOGERROR("Error disabling polling");
	if (interfaceCommand("CLEARCONFIG", s, 1000, false))
		LOGERROR("Error clearing configuration");
	line = 0;
	i = config.begin();
	while (i != config.end())
	{
		s = QString("WCONFIG%1%2=%3").arg(line, 4, 16, QChar('0')).toUpper().arg(i.key()).arg(i.value());
//		logMessage(s);
		if (interfaceCommand(s, s, 1000, false))
			LOGERROR("Error setting configuration");
		++i;
		line++;
	}
	if (interfaceCommand("POLLON", s, 1000, false))
		LOGERROR("Error enabling polling");
	return 0;

error:
	interfaceCommand("POLLON", s, 1000, false);
	emit logMessage("! writeConfig: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::applyAll()
{
	QString s;

	if (writeConfig())
		return 1;
	if (interfaceCommand("APPLYALL", s, 30000, false))
		LOGERROR("Error during apply all");
	return 0;

error:
	emit logMessage("! applyAll: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::applyNet()
{
	QString s;

	if (writeConfig())
		return 1;
	if (interfaceCommand("APPLYNET", s, 1000, false))
		LOGERROR("Error during apply net");
	return 0;

error:
	emit logMessage("! applyNet: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::powerOn()
{
	QString s;

	if (interfaceCommand("POWERON", s, 30000, false))
		LOGERROR("Error powering on");
	return 0;

error:
	emit logMessage("! powerOn: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::powerOff()
{
	QString s;

	if (interfaceCommand("POWEROFF", s, 30000, false))
		LOGERROR("Error powering off");
	return 0;

error:
	emit logMessage("! powerOff: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::pollOn()
{
	QString s;

	if (interfaceCommand("BIASPOLLON", s, 1000, false))
		LOGERROR("Error enabling bias polling");
	return 0;

error:
	emit logMessage("! pollOn: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::pollOff()
{
	QString s;

	if (interfaceCommand("BIASPOLLOFF", s, 1000, false))
		LOGERROR("Error disabling bias polling");
	return 0;

error:
	emit logMessage("! pollOff: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::loadTiming()
{
	QString s;

	if (writeConfig())
		return 1;
	if (interfaceCommand("LOADTIMING", s, 5000, false))
		LOGERROR("Error loading timing");
	return 0;

error:
	emit logMessage("! loadTiming: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::loadParams()
{
	QString s;

	if (writeConfig())
		return 1;
	if (interfaceCommand("LOADPARAMS", s, 1000, false))
		LOGERROR("Error loading timing parameters");
	return 0;

error:
	emit logMessage("! loadParams: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::loadParam(QString paramName)
{
	QString s;

	if (writeConfig())
		return 1;
	if (interfaceCommand(QString("LOADPARAM ") + paramName, s, 1000, false))
		LOGERROR("Error loading timing parameter");
	return 0;

error:
	emit logMessage("! loadParam: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::resetTiming()
{
	QString s;

	if (interfaceCommand("RESETTIMING", s, 1000, false))
		LOGERROR("Error resetting timing");
	return 0;

error:
	emit logMessage("! resetTiming: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::holdTiming()
{
	QString s;

	if (interfaceCommand("HOLDTIMING", s, 1000, false))
		LOGERROR("Error holding timing");
	return 0;

error:
	emit logMessage("! holdTiming: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::releaseTiming()
{
	QString s;

	if (interfaceCommand("RELEASETIMING", s, 1000, false))
		LOGERROR("Error releasing timing");
	return 0;

error:
	emit logMessage("! releaseTiming: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::applySystem()
{
	QString s;

	if (writeConfig())
		return 1;
	if (interfaceCommand("APPLYSYSTEM", s, 1000, false))
		LOGERROR("Error applying system settings");
	return 0;

error:
	emit logMessage("! applySystem: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::applyCDS()
{
	QString s;

	if (writeConfig())
		return 1;
	if (interfaceCommand("APPLYCDS", s, 1000, false))
		LOGERROR("Error applying CDS / deinterlacing");
	return 0;

error:
	emit logMessage("! applyCDS: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::applyModule(QString slot)
{
	int i;
	bool ok;
	QString s;

	i = slot.toInt(&ok);
	if (!ok)
		LOGERROR("Error parsing slot");
	if (writeConfig())
		return 1;
	s = "APPLYMOD" + hex(i, 2);
	if (interfaceCommand(s, s, 10000, false))
		LOGERROR("Error applying module settings");
	return 0;

error:
	emit logMessage("! applyModule: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::applyDIO(QString slot)
{
	int i;
	bool ok;
	QString s;

	i = slot.toInt(&ok);
	if (!ok)
		LOGERROR("Error parsing slot");
	if (writeConfig())
		return 1;
	s = "APPLYDIO" + hex(i, 2);
	if (interfaceCommand(s, s, 10000, false))
		LOGERROR("Error applying module DIO settings");
	return 0;

error:
	emit logMessage("! applyDIO: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::direct(QString cmd)
{
	QString s;

	if (interfaceCommand(cmd, s, 1000, false))
		LOGERROR("Error during direct command");
	return 0;

error:
	emit logMessage("! direct: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
//---------------------------------------------------------------------------
int Archon::atlasMove(QStringList params)
{
	int i;
	bool ok;
	QString s;

	i = params.value(0).toInt(&ok);
	if (!ok)
		LOGERROR("Error parsing slot");
	s = "ATLASMOVE" + hex(i, 2);
	s = s + " " + params.value(1) + " " + params.value(2);
	if (interfaceCommand(s, s, 1000, false))
		LOGERROR("Error commanding picomotor move");
	return 0;

error:
	emit logMessage("! atlasMove: " + error_message + QString(" (%1:%2)").arg(__FILE__).arg(error_line));
	return 1;
}
