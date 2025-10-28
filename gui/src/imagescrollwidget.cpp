#include <QScrollBar>
#include "imagescrollwidget.h"

ImageScrollWidget::ImageScrollWidget(QWidget *parent, bool raw) : QScrollArea(parent)
{
    iw = new ImageWidget(0, raw);
    setWidget(iw);
    QObject::connect(iw,SIGNAL(mousexy(int,int,uint)),this,SIGNAL(mousexy(int,int,uint)));
    QObject::connect(iw,SIGNAL(plotChanged(int,int)),this,SIGNAL(plotChanged(int,int)));
    QObject::connect(iw,SIGNAL(statChanged(int,int,int,int)),this,SIGNAL(statChanged(int,int,int,int)));
    QObject::connect(iw,SIGNAL(noiseChanged(int,int,int,int)),this,SIGNAL(noiseChanged(int,int,int,int)));
}

void ImageScrollWidget::setFrame(TFrameBuffer *frame)
{
    iw->setFrame(frame);
}

TFrameBuffer *ImageScrollWidget::frame()
{
    return iw->frame();
}

void ImageScrollWidget::setZoom(double zoom)
{
    int x,y;

    // Keep center pixel centered during zoom operations
    x = int((horizontalScrollBar()->sliderPosition() +
        viewport()->width() / 2) / iw->zoom());
    y = int((verticalScrollBar()->sliderPosition() +
        viewport()->height() / 2) / iw->zoom());
    iw->setZoom(zoom);
    horizontalScrollBar()->setSliderPosition(
        int((x + 0.5) * zoom - viewport()->width() / 2));
    verticalScrollBar()->setSliderPosition(
        int((y + 0.5) * zoom - viewport()->height() / 2));
}

double ImageScrollWidget::zoom()
{
    return iw->zoom();
}

void ImageScrollWidget::zoomFit()
{
    double w, h, vw, vh;
    TFrameBuffer *f = iw->frame();
    if (!f)
        return;
    w = qMax(f->width(), 1);
    h = qMax(f->height(), 1);
    vw = qMax(viewport()->width(), 1);
    vh = qMax(viewport()->height(), 1);
    if ((w / h) > (vw / vh))
        setZoom(vw / w);
    else
        setZoom(vh / h);
}

void ImageScrollWidget::setGain(double gain)
{
    iw->setGain(gain);
}

void ImageScrollWidget::setOffset(double offset)
{
    iw->setOffset(offset);
}

void ImageScrollWidget::setMode(int mode)
{
    iw->setMode(mode);
}
