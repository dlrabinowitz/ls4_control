#ifndef IMAGESCROLLWIDGET_H
#define IMAGESCROLLWIDGET_H

#include <QScrollArea>
#include <QMouseEvent>
#include "imagewidget.h"

class ImageScrollWidget : public QScrollArea
{
    Q_OBJECT
public:
    ImageScrollWidget(QWidget *parent, bool raw);
    void setFrame(TFrameBuffer *frame);
    TFrameBuffer *frame();
    void setGain(double gain);
    void setOffset(double offset);
    void setZoom(double zoom);
    void setMode(int mode);
    void zoomFit();
    double zoom();
signals:
    void mousexy(int x, int y, unsigned sample);
    void plotChanged(int hplot, int vplot);
    void statChanged(int x1, int y1, int x2, int y2);
    void noiseChanged(int x1, int y1, int x2, int y2);
private:
    ImageWidget *iw;
};

#endif // IMAGESCROLLWIDGET_H
