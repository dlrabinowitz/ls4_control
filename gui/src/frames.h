#ifndef FRAMES_H
#define FRAMES_H

// Frame buffer structure, used to hold individual captured frames
class TFrameBuffer
{
public:
	TFrameBuffer();
	TFrameBuffer(const TFrameBuffer& other);
	TFrameBuffer &operator=(const TFrameBuffer& other);
	~TFrameBuffer();
	bool NewFlag;				// Flag set by producer thread if this frame is valid
	int Frame;					// Frame #
	unsigned short *Data;		// Frame data storage
	unsigned short *RawData;	// Raw frame data storage
	bool Locked;				// Flag set if this frame is locked for reading or writing
	int width();
	int height();
	int setSize(int width, int height, bool hdr);
	int rawwidth();
	int rawheight();
	int setRawSize(int rawwidth, int rawheight);
	bool isEmpty();
	bool isRawEmpty();
	bool isHDR();
private:
	int m_width;				// Line length in samples
	int m_height;				// Line count in samples
	int m_rawwidth;				// Raw line length in samples
	int m_rawheight;			// Raw line count in samples
	bool m_hdr;					// Flag set if samples are 32 bit instead of 16 bit
};

#endif // FRAMES_H
