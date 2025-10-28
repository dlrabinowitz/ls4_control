#include "frames.h"
#include <qglobal.h>
#include <stdlib.h>

TFrameBuffer::TFrameBuffer()
{
	Data = 0;
	RawData = 0;
	Frame = -1;
	m_width = 0;
	m_height = 0;
	m_rawwidth = 0;
	m_rawheight = 0;
	Locked = false;
	m_hdr = false;
}

TFrameBuffer::TFrameBuffer(const TFrameBuffer& other)
{
	int words;

	Locked = false;
	if (other.Data == 0)
	{
		Data = 0;
	}
	else
	{
		m_width = other.m_width;
		m_height = other.m_height;
		m_rawwidth = other.m_rawwidth;
		m_rawheight = other.m_rawheight;
		Frame = other.Frame;
		m_hdr = other.m_hdr;
		words = m_width * m_height * (m_hdr ? 2 : 1);
		Data = (unsigned short *)malloc(words * sizeof(unsigned short));
		if (Data != 0)
			for (int i = 0; i < words; i++)
				Data[i] = other.Data[i];
		RawData = (unsigned short *)malloc(m_rawwidth * m_rawheight * sizeof(unsigned short));
		if (RawData != 0)
			for (int i = 0; i < m_rawwidth * m_rawheight; i++)
				RawData[i] = other.RawData[i];
	}
	// This is an empty frame
	if (Data == 0)
	{
		m_width = 0;
		m_height = 0;
		Frame = -1;
	}
	if (RawData == 0)
	{
		m_rawwidth = 0;
		m_rawheight = 0;
	}
}

TFrameBuffer & TFrameBuffer::operator=(const TFrameBuffer& other)
{
	int i, words;

	// No self assignment
	if (this == &other)
		return *this;
	Locked = false;
	// Other frame is empty
	if (other.Data == 0)
	{
		if (Data)
		{
			free(Data);
			Data = 0;
		}
	}
	// Other frame is the same size as us, so just copy pixel data
	else if ((m_width * m_height == other.m_width * other.m_height) && (m_hdr == other.m_hdr))
	{
		words = m_width * m_height * (m_hdr ? 2 : 1);
		for (i = 0; i < words; i++)
			Data[i] = other.Data[i];
		m_width = other.m_width;
		m_height = other.m_height;
		Frame = other.Frame;
	}
	// Other frame is a different size than we are, so reallocate buffer to match
	else
	{
		m_width = other.m_width;
		m_height = other.m_height;
		Frame = other.Frame;
		m_hdr = other.m_hdr;
		if (Data)
			free(Data);
		words = m_width * m_height * (m_hdr ? 2 : 1);
		Data = (unsigned short *)malloc(words * sizeof(unsigned short));
		if (Data != NULL)
			for (i = 0; i < words; i++)
				Data[i] = other.Data[i];
	}
	if (Data == 0)
	{
		m_width = 0;
		m_height = 0;
		Frame = -1;
	}
	// Other frame is empty
	if (other.RawData == 0)
	{
		if (RawData)
		{
			free(RawData);
			RawData = 0;
		}
	}
	// Other frame is the same size as us, so just copy pixel data
	else if (m_rawwidth * m_rawheight == other.m_rawwidth * other.m_rawheight)
	{
		for (i = 0; i < m_rawwidth * m_rawheight; i++)
			RawData[i] = other.RawData[i];
		m_rawwidth = other.m_rawwidth;
		m_rawheight = other.m_rawheight;
	}
	// Other frame is a different size than we are, so reallocate buffer to match
	else
	{
		m_rawwidth = other.m_rawwidth;
		m_rawheight = other.m_rawheight;
		if (RawData)
			free(RawData);
		RawData = (unsigned short *)malloc(m_rawwidth * m_rawheight * sizeof(unsigned short));
		if (RawData != NULL)
			for (i = 0; i < m_rawwidth * m_rawheight; i++)
				RawData[i] = other.RawData[i];
	}
	if (RawData == 0)
	{
		m_rawwidth = 0;
		m_rawheight = 0;
	}
	return *this;
}

TFrameBuffer::~TFrameBuffer()
{
	if (Data)
		free(Data);
	Data = 0;
	if (RawData)
		free(RawData);
	RawData = 0;
}

int TFrameBuffer::setSize(int width, int height, bool hdr)
{
	// Are we already at the correct size?
	if ((m_width == width) && (m_height == height) && (m_hdr == hdr) && Data)
		return 0;
	// Avoid illegal parameters
	width = qMax(0, width);
	height = qMax(0, height);
	// Was an empty frame requested?
	if ((width == 0) || (height == 0))
	{
		width = 0;
		height = 0;
		if (Data)
			free(Data);
		Data = 0;
	}
	// Do we need to (re)allocate the buffer?
	else if ((m_width * m_height != width * height) || (m_hdr != hdr))
	{
		if (Data)
			free(Data);
		Data = (unsigned short *)malloc(width * height * sizeof(unsigned short) * (hdr ? 2 : 1));
	}
	m_width = width;
	m_height = height;
	m_hdr = hdr;
	Frame = -1;
	if (Data == 0)
		return -1;
	else
		return 0;
}

int TFrameBuffer::width()
{
	return m_width;
}

int TFrameBuffer::height()
{
	return m_height;
}

bool TFrameBuffer::isEmpty()
{
	return (Data == 0);
}

int TFrameBuffer::setRawSize(int rawwidth, int rawheight)
{
	// Are we already at the correct size?
	if ((m_rawwidth == rawwidth) && (m_rawheight == rawheight) && RawData)
		return 0;
	// Avoid illegal parameters
	rawwidth = qMax(0, rawwidth);
	rawheight = qMax(0, rawheight);
	// Was an empty frame requested?
	if ((rawwidth == 0) || (rawheight == 0))
	{
		rawwidth = 0;
		rawheight = 0;
		if (RawData)
			free(RawData);
		RawData = 0;
	}
	// Do we need to (re)allocate the buffer?
	else if (m_rawwidth * m_rawheight != rawwidth * rawheight)
	{
		if (RawData)
			free(RawData);
		RawData = (unsigned short *)malloc(rawwidth * rawheight * sizeof(unsigned short));
	}
	m_rawwidth = rawwidth;
	m_rawheight = rawheight;
	if ((RawData == 0) && (rawwidth != 0))
		return -1;
	else
		return 0;
}

int TFrameBuffer::rawwidth()
{
	return m_rawwidth;
}

int TFrameBuffer::rawheight()
{
	return m_rawheight;
}

bool TFrameBuffer::isRawEmpty()
{
	return (RawData == 0);
}

bool TFrameBuffer::isHDR()
{
	return m_hdr;
}
