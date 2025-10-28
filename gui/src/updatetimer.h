#ifndef UPDATETIMER_H
#define UPDATETIMER_H

#include <QThread>

class TUpdateTimer : public QThread
{
	Q_OBJECT
public:
	TUpdateTimer(QObject *parent = 0);
	~TUpdateTimer();
	void startUpdateTimer(int interval);
	void stopUpdateTimer();
signals:
	void update();
protected:
	virtual void run();
private:
	int updateInterval;
	volatile bool thread_exit;	// Command thread to exit
};

#endif
