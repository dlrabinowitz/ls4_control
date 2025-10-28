#ifndef IMAGEWIDGET_H
#define IMAGEWIDGET_H

#include <QWidget>
#include <QImage>
#include <QColor>
#include <QMouseEvent>
#include "frames.h"

class ImageWidget : public QWidget
{
    Q_OBJECT
public:
    ImageWidget(QWidget *parent, bool raw);
    ~ImageWidget();
    void setFrame(TFrameBuffer *frame);
    TFrameBuffer *frame();
    void setZoom(double zoom);
    double zoom();
    void setGain(double gain);
    void setOffset(double offset);
    void setLUT(double gain, double offset);
    void setMode(int mode);
signals:
    void mousexy(int x, int y, unsigned sample);
    void plotChanged(int hplot, int vplot);
    void statChanged(int x1, int y1, int x2, int y2);
    void noiseChanged(int x1, int y1, int x2, int y2);
protected:
    virtual void mouseMoveEvent(QMouseEvent *event);
    virtual void mousePressEvent(QMouseEvent *event);
    virtual void mouseReleaseEvent(QMouseEvent *event);
    void paintEvent(QPaintEvent *pe);
private:
    void reportPixelValue(int x, int y);
    QImage *m_image;
    QRgb grayscale[65536];
    QRgb grayscalehdr[1048576];
    TFrameBuffer *m_frame;
    double m_zoom;
    int m_hplot;
    int m_vplot;
    int statX1;
    int statY1;
    int statX2;
    int statY2;
    int noiseX1;
    int noiseY1;
    int noiseX2;
    int noiseY2;
    int lastx,lasty;
    bool rightDown;
    bool middleDown;
    double m_gain;
    double m_offset;
    bool m_raw;
    int m_mode;
};

#endif // IMAGEWIDGET_H
