/////////////////////////////////////////////////////////////////////////////////
// reflexcontrol: Control program for the STA Reflex CCD controller
//
// Copyright 2011 Semiconductor Technology Associates, Inc.  All rights reserved.
//
// Redistribution and use in source and binary forms, with or without modification, are
// permitted provided that the following conditions are met:
//
//    1. Redistributions of source code must retain the above copyright notice, this list of
//       conditions and the following disclaimer.
//
//    2. Redistributions in binary form must reproduce the above copyright notice, this list
//       of conditions and the following disclaimer in the documentation and/or other materials
//       provided with the distribution.
//
// THIS SOFTWARE IS PROVIDED BY SEMICONDUCTOR TECHNOLOGY ASSOCIATES, INC. "AS IS" AND ANY
// EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
// MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL
// SEMICONDUCTOR TECHNOLOGY ASSOCIATES, INC. OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
// INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
// LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
// OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
// CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
// WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
//
/////////////////////////////////////////////////////////////////////////////////

#include "simpleprogress.h"
#include <QPainter>
#include <QPaintEvent>

SimpleProgress::SimpleProgress(QWidget *parent) : QWidget(parent)
{
	step = 0;
	total = 1;
	margin = 1;
}

void SimpleProgress::paintEvent(QPaintEvent *pe)
{
	QPainter p(this);
	QBrush brush(palette().color(QPalette::Active,QPalette::Highlight));
	QRect r(pe->rect());
	int delta = int((1.0-float(step)/float(total))*(r.width()-2*margin));
	p.setPen(Qt::NoPen);
	p.setBrush(brush);
	p.drawRect(r.adjusted(margin,margin,-delta-margin,-margin));
}

void SimpleProgress::setProgress(const int newstep,const int newtotal)
{
	total = qMax(newtotal,1);
	step = qMin(qMax(newstep,0),total);
	update();
}
