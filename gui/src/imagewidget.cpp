#include "imagewidget.h"
#include <QPainter>
#include <QPaintEvent>
#include <QString>

ImageWidget::ImageWidget(QWidget *parent, bool raw) : QWidget(parent)
{
    int i;

    m_image = NULL;
    m_frame = NULL;
    m_zoom = 1.0;
    m_hplot = 0;
    m_vplot = 0;
    statX1 = 0;
    statY1 = 0;
    statX2 = 0;
    statY2 = 0;
    noiseX1 = 0;
    noiseY1 = 0;
    noiseX2 = 0;
    noiseY2 = 0;
    lastx = 0;
    lasty = 0;
    rightDown = false;
    middleDown = false;
    m_gain = 1.0;
    m_offset = 0.0;
    m_raw = raw;
    for (i = 0; i < 65536; i++)
        grayscale[i] = qRgb(i / 256, i / 256, i / 256);
    for (i = 0; i < 1048576; i++)
        grayscalehdr[i] = qRgb(i / 4096, i / 4096, i / 4096);
    setFixedSize(0,0);
    setMouseTracking(true);
}

ImageWidget::~ImageWidget()
{
    if (m_image)
        delete m_image;
}

void ImageWidget::paintEvent(QPaintEvent *pe)
{
    QPainter p(this);
    QRgb *scanline;
    int x,y,w,h,l,t,r,b,iy,ix,iw,ih,ix2,iy2;
    int x1,y1,x2,y2;
    quint32 *data32;
    quint32 m32;
    quint16 m16;

    l = pe->rect().left();
    t = pe->rect().top();
    r = pe->rect().right();
    b = pe->rect().bottom();
    w = pe->rect().width();
    h = pe->rect().height();

    // Do we need to resize our internal image?
    if (m_image && ((m_image->width() < w) || (m_image->height() < h)))
    {
        delete m_image;
        m_image = NULL;
    }
    if (m_image == NULL)
        m_image = new QImage(w,h,QImage::Format_RGB32);
    // Render visible part of image
    if (m_frame == NULL)
        return;
    if (!m_raw && m_frame->isEmpty())
        return;
    if (m_raw && m_frame->isRawEmpty())
        return;
    if (m_raw)
    {
        iw = m_frame->rawwidth();
        ih = m_frame->rawheight();
        for (y = t; y <= b; y++)
        {
            iy = int(y / m_zoom);
            scanline = (QRgb *)m_image->scanLine(y-t);
            for (x=l;x<=r;x++)
            {
                ix = int(x / m_zoom);
                scanline[x-l] = grayscale[m_frame->RawData[iy * iw + ix]];
            }
        }
    }
    else
    {
        iw = m_frame->width();
        ih = m_frame->height();
        if (!m_frame->isHDR())
        {
            // Nearest
            if ((m_zoom >= 1.0) || (m_mode == 0))
            {
                for (y = t; y <= b; y++)
                {
                    iy = int(y / m_zoom);
                    scanline = (QRgb *)m_image->scanLine(y-t);
                    for (x=l;x<=r;x++)
                    {
                        ix = int(x / m_zoom);
                        scanline[x-l] = grayscale[m_frame->Data[iy * iw + ix]];
                    }
                }
            }
            // Max
            else if (m_mode == 1)
            {
                for (y = t; y <= b; y++)
                {
                    scanline = (QRgb *)m_image->scanLine(y-t);
                    iy = int(y / m_zoom);
                    iy2 = int((y + 1) / m_zoom);
                    for (x=l;x<=r;x++)
                    {
                        ix = int(x / m_zoom);
                        ix2 = int((x + 1) / m_zoom);
                        m16 = m_frame->Data[iy * iw + ix];
                        for (y2 = iy; y2 < iy2; y2++)
                            for (x2 = ix; x2 < ix2; x2++)
                                m16 = qMax(m16, m_frame->Data[y2 * iw + x2]);
                        scanline[x-l] = grayscale[m16];
                    }
                }
            }
            // Min
            else
            {
                for (y = t; y <= b; y++)
                {
                    scanline = (QRgb *)m_image->scanLine(y-t);
                    iy = int(y / m_zoom);
                    iy2 = int((y + 1) / m_zoom);
                    for (x=l;x<=r;x++)
                    {
                        ix = int(x / m_zoom);
                        ix2 = int((x + 1) / m_zoom);
                        m16 = m_frame->Data[iy * iw + ix];
                        for (y2 = iy; y2 < iy2; y2++)
                            for (x2 = ix; x2 < ix2; x2++)
                                m16 = qMin(m16, m_frame->Data[y2 * iw + x2]);
                        scanline[x-l] = grayscale[m16];
                    }
                }
            }
        }
        else
        {
            data32 = (quint32 *)m_frame->Data;
            // Nearest
            if ((m_zoom >= 1.0) || (m_mode == 0))
            {
                for (y = t; y <= b; y++)
                {
                    iy = int(y / m_zoom);
                    scanline = (QRgb *)m_image->scanLine(y-t);
                    for (x=l;x<=r;x++)
                    {
                        ix = int(x / m_zoom);
                        scanline[x-l] = grayscalehdr[data32[iy * iw + ix] >> 12];
                    }
                }
            }
            // Max
            else if (m_mode == 1)
            {
                for (y = t; y <= b; y++)
                {
                    scanline = (QRgb *)m_image->scanLine(y-t);
                    iy = int(y / m_zoom);
                    iy2 = int((y + 1) / m_zoom);
                    for (x=l;x<=r;x++)
                    {
                        ix = int(x / m_zoom);
                        ix2 = int((x + 1) / m_zoom);
                        m32 = data32[iy * iw + ix];
                        for (y2 = iy; y2 < iy2; y2++)
                            for (x2 = ix; x2 < ix2; x2++)
                                m32 = qMax(m32, data32[y2 * iw + x2]);
                        scanline[x-l] = grayscalehdr[m32];
                    }
                }
            }
            // Min
            else
            {
                for (y = t; y <= b; y++)
                {
                    scanline = (QRgb *)m_image->scanLine(y-t);
                    iy = int(y / m_zoom);
                    iy2 = int((y + 1) / m_zoom);
                    for (x=l;x<=r;x++)
                    {
                        ix = int(x / m_zoom);
                        ix2 = int((x + 1) / m_zoom);
                        m32 = data32[iy * iw + ix];
                        for (y2 = iy; y2 < iy2; y2++)
                            for (x2 = ix; x2 < ix2; x2++)
                                m32 = qMin(m32, data32[y2 * iw + x2]);
                        scanline[x-l] = grayscalehdr[m32];
                    }
                }
            }
        }
    }
    p.drawImage(pe->rect().topLeft(), *m_image);

    // Horizontal plot indicator
    if ((m_hplot >= 0) && (m_hplot < ih))
    {
        p.setPen(Qt::red);
        p.drawLine(0, int((m_hplot + 0.5) * m_zoom), width(), int((m_hplot + 0.5) * m_zoom));
    }
    // Vertical plot indicator
    if ((m_vplot >= 0) && (m_vplot < iw))
    {
        p.setPen(Qt::blue);
        p.drawLine(int((m_vplot + 0.5) * m_zoom), 0, int((m_vplot + 0.5) * m_zoom), height());
    }
    // Signal statistics box
    x1 = int((qMin(statX1, statX2) + 0.01) * m_zoom);
    x2 = int((qMax(statX1, statX2) + 0.99) * m_zoom);
    y1 = int((qMin(statY1, statY2) + 0.01) * m_zoom);
    y2 = int((qMax(statY1, statY2) + 0.99) * m_zoom);
    p.setPen(Qt::green);
    p.drawRect(x1, y1, x2 - x1 + 1, y2 - y1 + 1);
    // Noise statistics box
    x1 = int((qMin(noiseX1, noiseX2) + 0.01) * m_zoom);
    x2 = int((qMax(noiseX1, noiseX2) + 0.99) * m_zoom);
    y1 = int((qMin(noiseY1, noiseY2) + 0.01) * m_zoom);
    y2 = int((qMax(noiseY1, noiseY2) + 0.99) * m_zoom);
    p.setPen(Qt::yellow);
    p.drawRect(x1, y1, x2 - x1 + 1, y2 - y1 + 1);
}

void ImageWidget::setFrame(TFrameBuffer *frame)
{
    m_frame = frame;
    if (m_raw)
    {
        if (m_frame && !m_frame->isRawEmpty())
            setFixedSize(int(m_zoom * m_frame->rawwidth()), int(m_zoom * m_frame->rawheight()));
    }
    else
    {
        if (m_frame && !m_frame->isEmpty())
            setFixedSize(int(m_zoom * m_frame->width()), int(m_zoom * m_frame->height()));
    }
    reportPixelValue(lastx, lasty);
    update();
}

TFrameBuffer *ImageWidget::frame()
{
    return m_frame;
}

void ImageWidget::setZoom(double zoom)
{
    if (zoom <= 0)
        return;
    m_zoom = zoom;
    if (m_raw)
    {
        if (m_frame && !m_frame->isRawEmpty())
            setFixedSize(int(m_zoom * m_frame->rawwidth()), int(m_zoom * m_frame->rawheight()));
    }
    else
    {
        if (m_frame && !m_frame->isEmpty())
            setFixedSize(int(m_zoom * m_frame->width()), int(m_zoom * m_frame->height()));
    }
    update();
}

double ImageWidget::zoom()
{
    return m_zoom;
}

void ImageWidget::reportPixelValue(int x, int y)
{
    if (m_raw)
    {
        if (m_frame && !m_frame->isRawEmpty())
        {
            x = qBound(0, x, m_frame->rawwidth() - 1);
            y = qBound(0, y, m_frame->rawheight() - 1);
            emit mousexy(x, y, unsigned(m_frame->RawData[y * m_frame->rawwidth() + x]));
        }
        else
            emit mousexy(x, y, 0);
    }
    else
    {
        if (m_frame && !m_frame->isEmpty())
        {
            x = qBound(0, x, m_frame->width() - 1);
            y = qBound(0, y, m_frame->height() - 1);
            if (m_frame->isHDR())
                emit mousexy(x, y, ((unsigned *)m_frame->Data)[y * m_frame->width() + x] >> 12);
            else
                emit mousexy(x, y, unsigned(m_frame->Data[y * m_frame->width() + x]));
        }
        else
            emit mousexy(x, y, 0);
    }
    lastx = x;
    lasty = y;
}

void ImageWidget::mouseMoveEvent(QMouseEvent *event)
{
    int x,y;

    // Report image position and pixel value
    x = int(event->x() / m_zoom);
    y = int(event->y() / m_zoom);
    reportPixelValue(x, y);
    // Check for signal box being drawn
    if (rightDown)
    {
        statX2 = x;
        statY2 = y;
        update();
        emit statChanged(statX1, statY1, statX2, statY2);
    }
    // Check for noise box being drawn
    if (middleDown)
    {
        noiseX2 = x;
        noiseY2 = y;
        update();
        emit noiseChanged(noiseX1, noiseY1, noiseX2, noiseY2);
    }
}

void ImageWidget::mousePressEvent(QMouseEvent *event)
{
    int x,y;

    x = int(event->x() / m_zoom);
    y = int(event->y() / m_zoom);
    // Check for start of the signal box
    if (event->button() == Qt::RightButton)
    {
        statX1 = x;
        statY1 = y;
        rightDown = true;
        update();
        emit statChanged(statX1, statY1, statX2, statY2);
    }
    // Check for start of the noise box
    if (event->button() == Qt::MiddleButton)
    {
        noiseX1 = x;
        noiseY1 = y;
        middleDown = true;
        update();
        emit noiseChanged(noiseX1, noiseY1, noiseX2, noiseY2);
    }
}

void ImageWidget::mouseReleaseEvent(QMouseEvent *event)
{
    int x,y;

    x = int(event->x() / m_zoom);
    y = int(event->y() / m_zoom);
    // Check for new plot lines
    if (event->button() == Qt::LeftButton)
    {
        m_hplot = y;
        m_vplot = x;
        update();
        emit plotChanged(m_hplot, m_vplot);
    }
    // Check for signal box being drawn
    if (event->button() == Qt::RightButton)
    {
        statX2 = x;
        statY2 = y;
        rightDown = false;
        update();
        emit statChanged(statX1, statY1, statX2, statY2);
    }
    // Check for noise box being drawn
    if (event->button() == Qt::MiddleButton)
    {
        noiseX2 = x;
        noiseY2 = y;
        middleDown = false;
        update();
        emit noiseChanged(noiseX1, noiseY1, noiseX2, noiseY2);
    }
}

void ImageWidget::setGain(double gain)
{
    m_gain = gain;
    setLUT(m_gain, m_offset);
}

void ImageWidget::setOffset(double offset)
{
    m_offset = offset;
    setLUT(m_gain, m_offset);
}

void ImageWidget::setLUT(double gain, double offset)
{
    int i, y;
    for (i = 0; i < 65536; i++)
    {
        y = qBound(0, int(gain * double(i - offset)), 65535);
        grayscale[i] = qRgb(y / 256, y / 256, y / 256);
    }
    for (i = 0; i < 1048576; i++)
    {
        y = qBound(0, int(gain * double(i - offset * 16)), 1048575);
        grayscalehdr[i] = qRgb(y / 4096, y / 4096, y / 4096);
    }
    update();
}

void ImageWidget::setMode(int mode)
{
    m_mode = qBound(0, mode, 2);
    update();
}
