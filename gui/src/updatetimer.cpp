#include "updatetimer.h"

// This code is used to generate a simple polling signal.  It replaces
// using a QTimer, because QTimer consumed significant CPU resources
// at sporadic intervals.

TUpdateTimer::TUpdateTimer(QObject *parent) : QThread(parent)
{
	thread_exit = false;
}

TUpdateTimer::~TUpdateTimer()
{
	if (isRunning())
	{
		thread_exit = true;
		wait();
	}
}

void TUpdateTimer::startUpdateTimer(int interval)
// interval: polling interval in milliseconds
{
	updateInterval = interval;
	start();
}

void TUpdateTimer::stopUpdateTimer()
{
	thread_exit = true;
	wait();
}

void TUpdateTimer::run()
{
	while (!thread_exit)
	{
		msleep(updateInterval);
		emit update();
	}
}

