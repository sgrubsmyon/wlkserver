/*
 * Copyright (c) 2019-2025
 * cv cryptovision GmbH
 * Munscheidstr. 14
 * 45886 Gelsenkirchen
 * Germany
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

/**
* @file se_msc_transport_ex.c
* @brief MSC (Mass Storage Class) transport adapter implementation - used by the "standard" SE-API as well.
*/

#include <string.h>

#include <se_transport_ex.h>
#include <se_transport_util.h>

#include <se_msc_transport_ex.h>

/* ------------------------------------------------------------------------- */
/* JNA_MSC_EXPORT definition for exported MSC functions                      */
/* ------------------------------------------------------------------------- */

/* can be checked by calling Java code */
#define MSC_VERSION 5

#if 0 || defined(DUMP_RAW)
#	undef	DUMP
#	define	DUMP
#	define	DUMP_RAW
#endif

#ifdef DUMP
	static FILE* debuglog_file = NULL;
	static int debug_log_counter = 0;
#	ifndef DUMP_MAX
#		define _DUMP_MAX(x) (x)
#	else
#		define _DUMP_MAX(x) (DUMP_MAX < x ? DUMP_MAX : x)
#	endif
#	ifndef DUMP_MAX_LINES
#		define DUMP_MAX_LINES 0
#	endif
#	ifndef DUMP_RAW
#		define DUMP_ERR_RAW
#	endif
#	define 	DUMP_ERROR(x) dump_error(x)
#else
#	define 	DUMP_ERROR(x)
#endif

#if defined(_WIN32)
#	include <Windows.h>
#	if defined(JNA_MSC_TRANSPORT)
#		define JNA_MSC_EXPORT __declspec(dllexport)
#	endif
#else
#	include <sys/types.h>
#	include <sys/stat.h>
#	include <unistd.h>
#	include <string.h>
#	include <fcntl.h>
#	include <errno.h>
#	if !defined(__O_DIRECT) && defined(O_DIRECT)
#		define __O_DIRECT O_DIRECT
#	elif defined(__APPLE__)
/*		needs additional fcntl, see below */
#		define __O_DIRECT O_SYNC
#	endif
#	if defined(JNA_MSC_TRANSPORT)
#		define JNA_MSC_EXPORT __attribute__ ((visibility ("default")))
#	endif
#endif

#if !defined(JNA_MSC_EXPORT)
#    define  JNA_MSC_EXPORT
#endif


/* ------------------------------------------------------------------------- */
/* External functions                                                        */
/* ------------------------------------------------------------------------- */

extern se_result_t se_map_io_result_error(int16_t io_result);


/* ------------------------------------------------------------------------- */
/* Local functions (forward declarations)                                    */
/* ------------------------------------------------------------------------- */

static se_result_t setSuspendMode(io_handle_t hTSE, uint16_t mode, uint32_t* lastOSError);
static se_result_t clearFile(io_handle_t hTSE, uint32_t* lastOSError);
static se_result_t readRetry(io_handle_t hTSE, int64_t maxTimeMillis, uint32_t readdelay, uint32_t* lastOSError);

/* ------------------------------------------------------------------------- */
/* Local definitions                                                         */
/* ------------------------------------------------------------------------- */

#define SE_MSC_ALIGNED_BUFFER_SIZE		0x2400		/**< 9k = 8k + 2*BLOCK_SIZE local buffer for sector aligned read of TSE-IO.bin content */
#define SE_MSC_RESPONSE_BUFFER_SIZE		0x2000		/**< 8k local buffer for read blocks of TSE-IO.bin content */

#if defined(__ANDROID__)
#define MODE_DIRECT						       0
#define MODE_CREATE						       1

static uint32_t	IO_MODE					= MODE_DIRECT;	/**< enable Android 11 workaround with MODE_CREATE */
#endif

static uint32_t BLOCK_SIZE				= 0x0200;	/**< 512 byte block size for aligned write of TSE-IO.bin content */
static uint32_t	READ_SIZE				= 0x2000;	/**< 8k block size for aligned read of TSE-IO.bin content */

static uint16_t SE_CONTINUE				= 0x5344;	/**< wake up SE controller from suspend mode */
static uint16_t SE_SUSPEND				= 0x5345;	/**< set SE controller to suspend mode */

/* ------------------------------------------------------------------------- */
uint8_t MSC_HEADER[] = {
	(uint8_t) 0x41, (uint8_t) 0x64, (uint8_t) 0x56, (uint8_t) 0x61, (uint8_t) 0x6e, (uint8_t) 0x63, (uint8_t) 0x45, (uint8_t) 0x44,
	(uint8_t) 0x20, (uint8_t) 0x53, (uint8_t) 0x65, (uint8_t) 0x43, (uint8_t) 0x75, (uint8_t) 0x52, (uint8_t) 0x65, (uint8_t) 0x20,
	(uint8_t) 0x53, (uint8_t) 0x44, (uint8_t) 0x2f, (uint8_t) 0x4d, (uint8_t) 0x4d, (uint8_t) 0x43, (uint8_t) 0x20, (uint8_t) 0x43,
	(uint8_t) 0x41, (uint8_t) 0x72, (uint8_t) 0x64, (uint8_t) 0x01
};

uint8_t MSC_DEADBEEF[] = {
	(uint8_t) 0xde, (uint8_t) 0xad, (uint8_t) 0xbe, (uint8_t) 0xef
};


#ifdef DUMP
/* ------------------------------------------------------------------------- */
static void dump(const char* msg, const uint8_t* data, uint32_t length) {
	uint32_t i;
	if (DUMP_MAX_LINES && debug_log_counter > DUMP_MAX_LINES) {
		fprintf(debuglog_file, ".");
		return;
	}
    if(debuglog_file == NULL)
        return;
    fprintf(debuglog_file, "%s", msg);
	for (i = 0; i < length; i++)
		fprintf(debuglog_file, "%02X", *(data + i));
	fprintf(debuglog_file, "\n");
	debug_log_counter++;
	// fflush(stdout);
}

static void dump_error(const uint32_t code) {
	uint32_t i;
    if(debuglog_file == NULL)
        return;
    fprintf(debuglog_file, "err > %04X\n", code);
	// fflush(stdout);
}
#endif

/* ------------------------------------------------------------------------- */
/* Platform specific MSC functions                                           */
/* ------------------------------------------------------------------------- */

#if defined(_WIN32)

/* ------------------------------------------------------------------------- */
static void osGetLastError(uint32_t* lastOSError)
{
	DUMP_ERROR((uint32_t) GetLastError());
	if(lastOSError != NULL)
		if(*lastOSError == SE_OS_OK)	/* "first-last-error" behavior */
			*lastOSError = (uint32_t) GetLastError();
}

/* ------------------------------------------------------------------------- */
io_handle_t osOpenFile(const char* fileName,
	uint32_t* lastOSError)
{
	HANDLE hTSE = CreateFile(fileName, GENERIC_READ | GENERIC_WRITE, 0, NULL,
		OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL | FILE_FLAG_NO_BUFFERING, NULL);

	if(hTSE == INVALID_HANDLE_VALUE)
	{
#ifdef DUMP
		dump(__func__, NULL, 0);
#endif
		osGetLastError(lastOSError);
	}

	return HANDLEToIoHandle(hTSE);
}

/* ------------------------------------------------------------------------- */
#ifdef DUMP
static FILE* osOpenDebugLog(const char* fileName)
{
	return fopen(fileName, "a+");
}
#endif

/* ------------------------------------------------------------------------- */
void osCloseFile(io_handle_t hTSE,
	uint32_t* lastOSError)
{
	if(!CloseHandle(IoHandleToHANDLE(hTSE)))
	{
#ifdef DUMP
		dump(__func__, NULL, 0);
#endif
		osGetLastError(lastOSError);
	}
}

/* ------------------------------------------------------------------------- */
#ifdef DUMP
static void osCloseDebugLog(FILE* f)
{
	fclose(f);
}
#endif

/* ------------------------------------------------------------------------- */
se_result_t osWrite(io_handle_t hTSE, 
	const uint8_t* alignedData, uint32_t numBlocks,
	uint32_t* lastOSError)
{
	DWORD dwWritten = 0;

#ifdef DUMP_RAW
	dump("raw > ", alignedData, numBlocks * BLOCK_SIZE);
#endif

	if(!WriteFile(IoHandleToHANDLE(hTSE), alignedData, numBlocks * BLOCK_SIZE, &dwWritten, NULL))
	{
#ifdef DUMP_ERR_RAW
		dump("raw > ", alignedData, numBlocks * BLOCK_SIZE);
#endif
#ifdef DUMP
		dump(__func__, NULL, 0);
#endif
		osGetLastError(lastOSError);
		return ErrorIO;
	}
	if(dwWritten != (numBlocks * BLOCK_SIZE))
		return ErrorIO;

	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
se_result_t osRead(io_handle_t hTSE, 
	uint8_t* alignedData,
	uint32_t readLength,
	uint32_t* lastOSError)
{
	DWORD dwRead = 0;

	if(!ReadFile(IoHandleToHANDLE(hTSE), alignedData, readLength, &dwRead, NULL))
	{
#ifdef DUMP
		dump(__func__, NULL, 0);
#endif
		osGetLastError(lastOSError);
		return ErrorIO;
	}

#ifdef DUMP_RAW
	dump("raw < ", alignedData, 48);
#endif

	if(dwRead != readLength)
		return ErrorIO;

	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
se_result_t osSeekBegin(io_handle_t hTSE,
	uint32_t* lastOSError)
{
	if(SetFilePointer(IoHandleToHANDLE(hTSE), 0, NULL, FILE_BEGIN) == INVALID_SET_FILE_POINTER)
	{
#ifdef DUMP
		dump(__func__, NULL, 0);
#endif
		osGetLastError(lastOSError);
		return ErrorIO;
	}
	return ExecutionOk;
}

#else

/* ------------------------------------------------------------------------- */
static void osGetLastError(uint32_t* lastOSError)
{
	DUMP_ERROR((uint32_t) errno);
	if(lastOSError != NULL)
		if(*lastOSError == SE_OS_OK)	/* "first-last-error" behavior */
			*lastOSError = (uint32_t) errno;
}

/* ------------------------------------------------------------------------- */
HANDLE osOpenFile(const char* fileName,
				  uint32_t* lastOSError)
{
	int fd = INVALID_HANDLE_VALUE;
#if defined(__ANDROID__)
	if (IO_MODE == MODE_CREATE)
	{
		remove(fileName);
		fd = open(fileName, O_CREAT | O_EXCL | O_RDWR | __O_DIRECT, S_IRUSR | S_IWUSR);
	}
	else if(IO_MODE == MODE_DIRECT)
#endif
	{
		fd = open(fileName, O_RDWR | __O_DIRECT);
	}

	if(fd == INVALID_HANDLE_VALUE)
	{
#ifdef DUMP
		dump(__func__, NULL, 0);
#endif
		osGetLastError(lastOSError);
	}

#if defined(__APPLE__)
	if(fd != INVALID_HANDLE_VALUE)
		fcntl(fd, F_NOCACHE, 1);
#endif

	return fd;
}

/* ------------------------------------------------------------------------- */
#ifdef DUMP
static FILE* osOpenDebugLog(const char* fileName)
{
	return fopen(fileName, "a+");
}
#endif

/* ------------------------------------------------------------------------- */
void osCloseFile(io_handle_t hTSE,
	uint32_t* lastOSError)
{
	if(close(IoHandleToHANDLE(hTSE)) == INVALID_HANDLE_VALUE)
	{
#ifdef DUMP
		dump(__func__, NULL, 0);
#endif
		osGetLastError(lastOSError);
	}
}

/* ------------------------------------------------------------------------- */
#ifdef DUMP
static void osCloseDebugLog(FILE* f)
{
	fclose(f);
}
#endif

/* ------------------------------------------------------------------------- */
se_result_t osWrite(io_handle_t hTSE, 
	const uint8_t* alignedData, uint32_t numBlocks,
	uint32_t* lastOSError)
{
	ssize_t length;

#ifdef DUMP_RAW
	dump("raw > ", alignedData, numBlocks * BLOCK_SIZE);
#endif

#if defined(__ANDROID__)
	if (IO_MODE == MODE_CREATE)
	{
		length = numBlocks * BLOCK_SIZE;
		if (length > (ssize_t) READ_SIZE)
			return ErrorBufferTooSmall;
		ftruncate(IoHandleToHANDLE(hTSE), 0);
		lseek(IoHandleToHANDLE(hTSE), 0, SEEK_SET);
		numBlocks = READ_SIZE / BLOCK_SIZE;
		memset((uint8_t*) alignedData + length, 0, (size_t)(READ_SIZE - length));
	}
#endif
	length = write(IoHandleToHANDLE(hTSE), alignedData, numBlocks * BLOCK_SIZE);
	if(length != ((ssize_t) numBlocks * (ssize_t) BLOCK_SIZE))
	{
#ifdef DUMP_ERR_RAW
		dump("raw > ", alignedData, numBlocks * BLOCK_SIZE);
#endif
#ifdef DUMP
		dump(__func__, NULL, 0);
#endif
		osGetLastError(lastOSError);
		return ErrorIO;
	}
	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
se_result_t osRead(io_handle_t hTSE, 
	uint8_t* alignedData,
	uint32_t readLength,
	uint32_t* lastOSError)
{
	ssize_t length = read(IoHandleToHANDLE(hTSE), alignedData, readLength);
	if(length != (ssize_t) readLength)
	{
#ifdef DUMP
		dump(__func__, NULL, 0);
#endif
		osGetLastError(lastOSError);
		return ErrorIO;
	}

#ifdef DUMP_RAW
	dump("raw < ", alignedData, 48);
#endif

	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
se_result_t osSeekBegin(io_handle_t hTSE,
	uint32_t* lastOSError)
{
	off_t offset, result;
#if BLOCK_DEV
	offset = 8*1024;
#else
	offset = 0;
#endif

	result = lseek(IoHandleToHANDLE(hTSE), offset, SEEK_SET);
	if(result != offset)
	{
#ifdef DUMP
		dump(__func__, NULL, 0);
#endif
		osGetLastError(lastOSError);
		return ErrorIO;
	}
	return ExecutionOk;
}

#endif


/* ------------------------------------------------------------------------- */
/* Exported MSC functions                                                    */
/* ------------------------------------------------------------------------- */

/* ------------------------------------------------------------------------- */
#if defined(JNA_MSC_TRANSPORT)
JNA_MSC_EXPORT uint32_t getMscVersion(void)
{
	return MSC_VERSION;
}
#endif

/* ------------------------------------------------------------------------- */
JNA_MSC_EXPORT se_result_t mscRawClose(io_handle_t hTSE,
	uint32_t* lastOSError)
{
	if(IoHandleToHANDLE(hTSE) != INVALID_HANDLE_VALUE)
		osCloseFile(hTSE, lastOSError);

	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
JNA_MSC_EXPORT se_result_t mscClose(io_handle_t hTSE,
	uint32_t* lastOSError)
{
	se_result_t result = ErrorIO;

#ifdef DUMP
	if (debuglog_file != NULL) {
		if (DUMP_MAX_LINES && debug_log_counter > DUMP_MAX_LINES)
			fprintf(debuglog_file, "\n");
		fprintf(debuglog_file, "mscClose()\n");
		debug_log_counter = 0;
	}
#endif

	if (IoHandleToHANDLE(hTSE) != INVALID_HANDLE_VALUE)
	{
		result = setSuspendMode(hTSE, SE_SUSPEND, lastOSError);
		osCloseFile(hTSE, lastOSError);
	}

#ifdef DUMP
	if (debuglog_file != NULL) {
		osCloseDebugLog(debuglog_file);
		debuglog_file = NULL;
	}
#endif

	return result;
}

/* ------------------------------------------------------------------------- */
#if defined(__ANDROID__)
JNA_MSC_EXPORT void mscKill(io_handle_t hTSE,
                                    uint32_t* lastOSError)
{

#ifdef DUMP
    if (debuglog_file != NULL) {
		if (DUMP_MAX_LINES && debug_log_counter > DUMP_MAX_LINES)
			fprintf(debuglog_file, "\n");
		fprintf(debuglog_file, "mscKill()\n");
		debug_log_counter = 0;
	}
#endif

    if (IoHandleToHANDLE(hTSE) != INVALID_HANDLE_VALUE)
    {
        osCloseFile(hTSE, lastOSError);
    }

#ifdef DUMP
    if (debuglog_file != NULL) {
		osCloseDebugLog(debuglog_file);
		debuglog_file = NULL;
	}
#endif
}
#endif

/* ------------------------------------------------------------------------- */
#if defined(__ANDROID__)
JNA_MSC_EXPORT void mscSetIOMode(uint32_t mode)
{
	IO_MODE = mode;
}
#endif

/* ------------------------------------------------------------------------- */
JNA_MSC_EXPORT void mscSetIOSize(uint32_t size)
{
	READ_SIZE = size;
}

/* ------------------------------------------------------------------------- */
JNA_MSC_EXPORT se_result_t mscRawOpen(const char* fileName,
	io_handle_t* hTSE,
	uint32_t* lastOSError)
{
	io_handle_t h = HANDLEToIoHandle(INVALID_HANDLE_VALUE);

	if (IoHandleToHANDLE(h = osOpenFile(fileName, lastOSError)) != INVALID_HANDLE_VALUE)
		*hTSE = h;
	else
		return ErrorIO;

	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
JNA_MSC_EXPORT se_result_t mscOpen(const char* fileName,
	io_handle_t* hTSE,
	uint32_t* lastOSError)
{
	{
		se_result_t result;

#ifdef DUMP
		#define MAXPL 256
	    char dbgFileName[MAXPL];
		#ifdef _WIN32
		    snprintf(dbgFileName, MAXPL, "%s/TSE-IO.debug", getenv("TEMP"));
		#else
		    snprintf(dbgFileName, MAXPL, "%s/TSE-IO.debug", getenv("HOME"));
		#endif

		debuglog_file = osOpenDebugLog(dbgFileName);
		debug_log_counter = 0;
		fprintf(debuglog_file, "\nDUMP " __DATE__ " " __TIME__ "\n");
		fprintf(debuglog_file, "mscOpen() ...\n");
#endif

		result = mscRawOpen(fileName, hTSE, lastOSError);
		if (result != ExecutionOk)
			return result;

#if !BLOCK_DEV
		result = clearFile(*hTSE, lastOSError);
#endif

		if(result == ExecutionOk)
			result = setSuspendMode(*hTSE, SE_CONTINUE, lastOSError);

		if (result != ExecutionOk)
		{
			mscClose(*hTSE, lastOSError);
			*hTSE = HANDLEToIoHandle(INVALID_HANDLE_VALUE);
			return result;
		}

		return ExecutionOk;
	}
}

/* ------------------------------------------------------------------------- */
JNA_MSC_EXPORT se_result_t mscRawWrite(io_handle_t hTSE,
	const uint8_t *data, uint32_t length,
	uint32_t* lastOSError)
{
#ifdef DUMP
	dump("msc > ", data, _DUMP_MAX(length));
#endif

	se_result_t result = osSeekBegin(hTSE, lastOSError);
	if(ExecutionOk != result)
		return result;
	{
		uint32_t numBlocks;

		uint8_t	ioBuffer[SE_MSC_ALIGNED_BUFFER_SIZE];
		uint8_t* pAligned = (uint8_t*)((uintptr_t)(ioBuffer + BLOCK_SIZE - 1) & ~((uintptr_t)(BLOCK_SIZE - 1)));

		if(sizeof(ioBuffer) - (pAligned - ioBuffer) < length + BLOCK_SIZE)
			return ErrorBufferTooSmall;

		/* data */
		if(data != NULL && length != 0)
			memcpy(pAligned, data, length);

		/* zero padding */
		numBlocks = (length + BLOCK_SIZE - 1) / BLOCK_SIZE;
		memset(pAligned + length, 0, (size_t) numBlocks * BLOCK_SIZE - length);

		return osWrite(hTSE, pAligned, numBlocks, lastOSError);
	}
}

/* ------------------------------------------------------------------------- */
JNA_MSC_EXPORT se_result_t mscWrite(io_handle_t hTSE,
	const uint8_t *data, uint32_t length, uint16_t le,
	uint32_t* lastOSError)
{
#ifdef DUMP
	if((le == SE_NO_LE ? 0 : le) && debuglog_file && (!DUMP_MAX_LINES || debug_log_counter <= DUMP_MAX_LINES))
		fprintf(debuglog_file, "cmd(%04X) ", le);
	dump("msc > ", data, _DUMP_MAX(length));
#endif

	se_result_t result = osSeekBegin(hTSE, lastOSError);
	if(ExecutionOk != result)
		return result;
	{
		uint32_t numBlocks, offset = 0;

		uint8_t	ioBuffer[SE_MSC_ALIGNED_BUFFER_SIZE];
		uint8_t* pAligned = (uint8_t*)((uintptr_t)(ioBuffer + BLOCK_SIZE - 1) & ~((uintptr_t)(BLOCK_SIZE - 1)));

		if(sizeof(ioBuffer) - (pAligned - ioBuffer) < length + BLOCK_SIZE)
			return ErrorBufferTooSmall;

		/* header */
		memcpy(pAligned + offset, MSC_HEADER, sizeof(MSC_HEADER));
		offset += sizeof(MSC_HEADER);

		/* DEADBEEF */
		memcpy(pAligned + offset, MSC_DEADBEEF, sizeof(MSC_DEADBEEF));
		offset += sizeof(MSC_DEADBEEF);

		/* data length */
		se_uint16ToByteArray(pAligned + offset, (uint16_t) length);
		offset += sizeof(uint16_t);

		/* requested response length */
		{
			uint16_t _le = (le == SE_NO_LE ? 0 : le);
			se_uint16ToByteArray(pAligned + offset, _le);
			offset += sizeof(uint16_t);
		}

		/* data */
		if(data != NULL && length != 0)
		{
			memcpy(pAligned + offset, data, length);
			offset += length;
		}

		/* zero padding */
		numBlocks = (offset + BLOCK_SIZE - 1) / BLOCK_SIZE;
		memset(pAligned + offset, 0, (size_t) numBlocks * BLOCK_SIZE - offset);

		return osWrite(hTSE, pAligned, numBlocks, lastOSError);
	}
}

/* ------------------------------------------------------------------------- */
JNA_MSC_EXPORT se_result_t mscRawRead(io_handle_t hTSE,
	uint8_t *response, uint32_t *responseLength,
	uint32_t* lastOSError)
{
	se_result_t result;

	if(response == NULL || responseLength == NULL)
		return ErrorMissingParameter;

	if((result = osSeekBegin(hTSE, lastOSError)) != ExecutionOk)
		return result;

	{
		uint8_t	ioBuffer[SE_MSC_ALIGNED_BUFFER_SIZE];
		uint8_t* pAligned = (uint8_t*)((uintptr_t)(ioBuffer + BLOCK_SIZE - 1) & ~((uintptr_t)(BLOCK_SIZE - 1)));

		if((result = osRead(hTSE, pAligned, *responseLength, lastOSError)) != ExecutionOk)
			return result;

		memcpy(response, pAligned, *responseLength);

#ifdef DUMP
		dump("msc < ", response, _DUMP_MAX(*responseLength));
#endif
		return ExecutionOk;
	}
}

/* ------------------------------------------------------------------------- */
JNA_MSC_EXPORT se_result_t mscRead(io_handle_t hTSE,
	uint8_t *response, uint32_t *responseLength,
	uint32_t timeout, uint32_t readdelay,
	uint32_t* lastOSError)
{
	se_result_t result;

	if(response == NULL || responseLength == NULL)
		return ErrorMissingParameter;

	if((result = osSeekBegin(hTSE, lastOSError)) != ExecutionOk)
		return result;

	{
		uint32_t offset = 0, length = 0;
		const int64_t maxTimeMillis = se_currentTimeMillis() + timeout;

		uint8_t	ioBuffer[SE_MSC_ALIGNED_BUFFER_SIZE];
		uint8_t* pAligned = (uint8_t*)((uintptr_t)(ioBuffer + BLOCK_SIZE - 1) & ~((uintptr_t)(BLOCK_SIZE - 1)));

		/* read block READ_SIZE */
		for(;;) {
			uint16_t dataLength = 0;
			uint32_t available = 0;

			if((result = osRead(hTSE, pAligned, READ_SIZE, lastOSError)) != ExecutionOk)
				return result;

			offset = 0;

			if(memcmp(pAligned + offset, MSC_HEADER, sizeof(MSC_HEADER)) != 0)
			{
#ifdef DUMP_ERR_RAW
				dump("err < ", pAligned, BLOCK_SIZE);
#endif
				return ErrorResponseHeader;
			}

			offset += sizeof(MSC_HEADER);

			if(memcmp(pAligned + offset, MSC_DEADBEEF, sizeof(MSC_DEADBEEF)) == 0)
			{
#ifdef DUMP_ERR_RAW
				dump("err < ", pAligned, BLOCK_SIZE);
#endif
				return ErrorStaleIO;
			}

			offset += sizeof(MSC_DEADBEEF);

			/* get data length */
			if((result = se_byteArrayToInt16((int16_t *) &dataLength, pAligned + offset, sizeof(dataLength))) != ExecutionOk)
			{
#ifdef DUMP_ERR_RAW
				dump("err < ", pAligned, BLOCK_SIZE);
#endif
				return result;
			}

			/* special case, device still busy, retry with readdelay */
			if(SE_WAIT_FOR_RESPONSE == dataLength)
			{
				if((result = readRetry(hTSE, maxTimeMillis, readdelay, lastOSError)) != ExecutionOk)
					return result;
				else
					continue;
			}

			/* Flash controller detected timeout */
			if(SE_SD_TIMEOUT == dataLength)
			{
#ifdef DUMP_ERR_RAW
				dump("err < ", pAligned, BLOCK_SIZE);
#endif
				return ErrorTSETimeout;
			}
		
			/* other unexpected errors from flash controller */
			if(SE_SD_ERROR_MASK == (dataLength & SE_SD_ERROR_MASK))
			{
#ifdef DUMP_ERR_RAW
				dump("err < ", pAligned, BLOCK_SIZE);
#endif
				return ErrorClassSD | (SE_SD_ERROR_ID_MASK & dataLength);
			}

			/* skip data length */
			offset += sizeof(dataLength);

			/* check response buffer and length, if not enough update to required length */
			length = dataLength;
			if(length > READ_SIZE-offset)
			{
#ifdef DUMP_ERR_RAW
				dump("err < ", pAligned, BLOCK_SIZE);
#endif
				*responseLength = length;
				return ErrorResponseTooBig;
			}
			else if(response != NULL && length > *responseLength)
			{
#ifdef DUMP_ERR_RAW
				dump("err < ", pAligned, BLOCK_SIZE);
#endif
				*responseLength = length;
				return ErrorBufferTooSmall;
			}

			/* set output response length */
			*responseLength = length;

			/* copy available response */
			available = READ_SIZE - offset;
			if(length <= available)
			{
				memcpy(response, pAligned + offset, length);
				memset(pAligned, 0, READ_SIZE);

#ifdef DUMP
				dump("msc < ", response, _DUMP_MAX(*responseLength));
#endif
				return ExecutionOk;
			}

			break;
		}
	}

	return ErrorIO;
}


/* ------------------------------------------------------------------------- */
/* Local functions                                                           */
/* ------------------------------------------------------------------------- */

/* ------------------------------------------------------------------------- */
static se_result_t readRetry(io_handle_t hTSE,
	int64_t maxTimeMillis, uint32_t readdelay,
	uint32_t* lastOSError)
{
	if(se_currentTimeMillis() >= maxTimeMillis) {
#ifdef DUMP
		fprintf(debuglog_file, "timeout\n");
#endif
		return ErrorTSETimeout;
	}
	{
		se_result_t result = osSeekBegin(hTSE, lastOSError);
		if(result != ExecutionOk)
			return result;

		se_sleep(readdelay);
		return ExecutionOk;
	}
}

/* ------------------------------------------------------------------------- */
static se_result_t ignoreStatus(io_handle_t hTSE,
	uint32_t* lastOSError)
{
	uint8_t buf[SE_MSC_RESPONSE_BUFFER_SIZE]; /* 2 would typically be enough, but might well cause ErrorBufferTooSmall in case of (to be ignored) status/data... */
	uint32_t buf_used = sizeof(buf);

	/* read status word (ignored), use default timeout/delay */
	return mscRead(hTSE, buf, &buf_used, SE_DEFAULT_IO_TIMEOUT, SE_DEFAULT_IO_READDELAY, lastOSError);
}

/* ------------------------------------------------------------------------- */
static se_result_t setSuspendMode(io_handle_t hTSE, 
	uint16_t mode,
	uint32_t* lastOSError)
{
	se_result_t result;
	uint8_t buf[2] = { 0, 0 };

	if((result = mscWrite(hTSE, buf, sizeof(buf), mode, lastOSError)) != ExecutionOk)
		return result;

	if((result = ignoreStatus(hTSE, lastOSError)) != ExecutionOk)
		return result;

	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
static se_result_t clearFile(io_handle_t hTSE,
	uint32_t* lastOSError)
{
	se_result_t result = osSeekBegin(hTSE, lastOSError);
	if(ExecutionOk != result)
		return result;
	{
		uint8_t	ioBuffer[SE_MSC_ALIGNED_BUFFER_SIZE];
		uint8_t* pAligned = (uint8_t*)((uintptr_t)(ioBuffer + BLOCK_SIZE - 1) & ~((uintptr_t)(BLOCK_SIZE - 1)));

		memset(pAligned, 0, READ_SIZE);
		return osWrite(hTSE, pAligned, READ_SIZE / BLOCK_SIZE, lastOSError);
	}
}

/* ------------------------------------------------------------------------- */
static se_result_t doAbort(io_handle_t hTSE, 
	se_result_t reason,
	uint32_t* lastOSError)
{
	uint8_t c4 = 0xC4;
	se_result_t result;

	if((result = mscWrite(hTSE, &c4, sizeof(c4), SE_LE_0, lastOSError)) != ExecutionOk)
		return result;

	if((result = ignoreStatus(hTSE, lastOSError)) != ExecutionOk)
		return result;

	return reason;
}

/* ------------------------------------------------------------------------- */
static se_result_t doWriteResponse(io_handle_t hTSE,
	const uint8_t* data, uint32_t dataOffset, uint32_t dataLength,
	uint64_t totalDataLength,
	uint8_t* outBuffer,
	FILE* stream,
	se_writer_t writer,
	se_handle_t handle, 
	uint32_t* lastOSError)
{
	if(dataLength > 0) {
		if(stream != NULL) {
			if(dataLength != fwrite(data + dataOffset, sizeof(uint8_t), dataLength, stream))
				return doAbort(hTSE, ErrorStreamWrite, lastOSError);
		}
		else if(writer != NULL) {
			if(dataLength != writer(data + dataOffset, dataLength, totalDataLength, handle))
				return doAbort(hTSE, ErrorCallback, lastOSError);
		}
		else
			memcpy(outBuffer, data + dataOffset, dataLength);
	}

	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
static se_result_t doTarPadding(FILE* stream,
	se_writer_t writer,
	se_handle_t handle,
	uint64_t totalDataLength)
{
	if(stream != NULL)
		return streamTarPadding(stream);

	if(writer != NULL)
		return writeTarPadding(writer, handle, totalDataLength);

	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
static se_result_t mscTransmitCommand(se_ctx_t* ctx,
	uint8_t** response, uint32_t* responseLength,
	FILE* stream,
	se_writer_t writer,
	se_handle_t handle)
{
	se_result_t result;

	io_handle_t hTSE		= ctx->iOHandle;
	uint32_t	timeout		= ctx->iOTimeout;
	uint32_t*	lastOSError	= &ctx->lastOSError;

	/* reset expected total response data length */
	ctx->totalDataLength = 0;

	/* 1. transmit command */
	{
		if((result = mscWrite(hTSE, ctx->cmdBuf, ctx->cmdBufUsed, ctx->cmdLE, lastOSError)) != ExecutionOk)
			return result;
		
		se_sleep(SE_DEFAULT_IO_READDELAY);
	}

	/* 2. get response */
	{
		int16_t io_result;
		uint8_t	tmp_buffer[SE_MSC_RESPONSE_BUFFER_SIZE];

		uint8_t* out_buffer;
		int64_t  offset, size;
		uint32_t buffer_used, data_offset, data_len;
		uint64_t total_data_len, tar_padding_len = ctx->needsTarPadding ? 1024 : 0;

		int buffer_output		= (response != NULL && responseLength != NULL)	? 1 : 0;	/* response to output buffer (no streaming or callback) */
		int has_output_buffer	= (buffer_output != 0 && *responseLength != 0)	? 1 : 0;	/* output buffer is provided or to be allocated  */
		int add_tar_padding		= (buffer_output == 0 && ctx->needsTarPadding)	? 1 : 0;	/* final tar-padding for streaming or callback case with 1024 zero byte */

		/* 2.1. first TSE response block handling */

		/* 2.1.1 read first response block (including status word and length bytes) */
		buffer_used = sizeof(tmp_buffer);
		if((result = mscRead(hTSE, tmp_buffer, &buffer_used, timeout, SE_DEFAULT_IO_READDELAY, lastOSError)) != ExecutionOk)
			return result;

		/* 2.1.2 get status word (2 response bytes required) */
		if(buffer_used < sizeof(io_result))
			return ErrorTSEResponseDataInvalid;
		if((result = se_byteArrayToInt16(&io_result, tmp_buffer, sizeof(io_result))) != ExecutionOk)
			return doAbort(hTSE, result, lastOSError);

		if(io_result != SE_EXPORT_DATA)						/* result != 9000h */
		{
			/* check status word < 0 => error code */
			if(io_result < 0)
				return se_map_io_result_error(io_result);

			/* CASE: NON EXPORT COMMAND (status word contains 15-bit response length) */
			/* - Response format: LL LL (15 bit length) || Data */

			/* 2.1.3 total response data size is LL LL */
			size = io_result;
			total_data_len = (uint64_t)size;
			data_offset = sizeof(io_result);

			/* 2.1.4 sufficient response buffer is expected to be provided by the caller */
			if(has_output_buffer == 0 || (uint32_t)size > *responseLength)
				return doAbort(hTSE, ErrorBufferTooSmall, lastOSError);
		
			*responseLength = (uint32_t)size;
		}
		else										/* status word == 9000h */
		{
			/* CASE: EXPORT COMMAND */
			/* - Response format: 90 00 LL LL LL LL LL LL LL LL (63 bit length) || Data */

			/* 2.1.3 get total export data size (2 + 8 response bytes required) */
			if(buffer_used < (sizeof(io_result) + sizeof(size)))
				return ErrorTSEResponseDataInvalid;
			if((result = se_byteArrayToInt64(&size, tmp_buffer + sizeof(io_result), sizeof(size))) != ExecutionOk)
				return doAbort(hTSE, result, lastOSError);
			if(size < 0)
				return doAbort(hTSE, ErrorTSEResponseDataInvalid, lastOSError);

			total_data_len = (uint64_t)size + tar_padding_len;
			data_offset = sizeof(io_result) + sizeof(size);

			/* 2.1.4 allocate response buffer if required (includes 1024 byte tar padding) */
			if(buffer_output != 0)
			{
				if(has_output_buffer != 0)
				{
					if(total_data_len > (uint64_t)*responseLength)
						return doAbort(hTSE, ErrorBufferTooSmall, lastOSError);
					else
						*responseLength = total_data_len;
				}
				else if((result = se_tarAllocExportBuffer(response, responseLength, size, tar_padding_len)) != ExecutionOk)
					return doAbort(hTSE, result, lastOSError);
			}
		}
		/* store total response data length in context */
		ctx->totalDataLength = total_data_len;

		/* 2.1.5 write data part of first block to response buffer or stream */
		data_len    = (uint32_t) SE_MIN((int64_t)(buffer_used - data_offset), size);
		out_buffer  = buffer_output != 0 ? *response : NULL;
		if((result  = doWriteResponse(hTSE, tmp_buffer, data_offset, data_len, total_data_len, out_buffer, stream, writer, handle, lastOSError)) != ExecutionOk)
			return result;

		/* 2.2. further TSE response block handling */
		offset = data_len;
		while(offset < size)
		{
			/* 2.2.1 write C5 "get more data" command */
			uint8_t c5 = 0xC5;
			if((result = mscWrite(hTSE, &c5, sizeof(c5), SE_LE_0, lastOSError)) != ExecutionOk)
				return result;

			se_sleep(SE_DEFAULT_IO_READDELAY);

			/* 2.2.2 read more data */
			buffer_used = sizeof(tmp_buffer);
			if((result = mscRead(hTSE, tmp_buffer, &buffer_used, timeout, SE_DEFAULT_IO_READDELAY, lastOSError)) != ExecutionOk)
				return result;

			if(buffer_used == 2 && size-offset > 2)
			{
				if((result = se_byteArrayToInt16(&io_result, tmp_buffer, sizeof(io_result))) != ExecutionOk)
					return doAbort(hTSE, result, lastOSError);
				return se_map_io_result_error(io_result);
			}

			/* 2.2.3 write data part of this block to response buffer or stream */
			data_len   = buffer_used;
			out_buffer = buffer_output != 0 ? (*response + offset) : NULL;
			if((result = doWriteResponse(hTSE, tmp_buffer, 0, data_len, total_data_len, out_buffer, stream, writer, handle, lastOSError)) != ExecutionOk)
				return result;

			offset += data_len;
		}

		/* 2.3. add 1024 byte tar padding if streaming or callback */
		if(add_tar_padding != 0)
			result = doTarPadding(stream, writer, handle, total_data_len);
	}

	return result;
}


/* ------------------------------------------------------------------------- */
/* se_msc_transport_ex.h functions                                           */
/* ------------------------------------------------------------------------- */

/* ------------------------------------------------------------------------- */
se_result_t se_mscTransportOpenEx(se_ctx_t* ctx, 
	const char* fileName)
{
	se_result_t result = mscOpen(fileName, &ctx->iOHandle, &ctx->lastOSError);
#ifdef DUMP
	if(debuglog_file)
		fprintf(debuglog_file, "timeout = %d\n", ctx->iOTimeout);
#endif
	return result;
}

/* ------------------------------------------------------------------------- */
se_result_t se_mscTransportCloseEx(se_ctx_t* ctx)
{
	return mscClose(ctx->iOHandle, &ctx->lastOSError);
}

/* ------------------------------------------------------------------------- */
se_result_t se_mscTransportTransmitEx(se_ctx_t* ctx)
{
	/* CASE: NON EXPORT COMMAND: provided response output buffer will be used; no tar-padding will be added */
	uint8_t* response = ctx->responseBuf;
	uint32_t* responseLength = &ctx->responseBufUsed;
	return mscTransmitCommand(ctx, &response, responseLength, NULL /*stream*/, NULL /*writer*/, NULL /*writer handle*/);
}

/* ------------------------------------------------------------------------- */
se_result_t se_mscTransportTransmitAndWriteEx(se_ctx_t* ctx,
	uint8_t** response,
	uint32_t* responseLength)
{
	/* CASE: EXPORT COMMAND: response buffer will be allocated including 1024 byte tar-padding */
	*response = NULL;
	*responseLength = 0;
	return mscTransmitCommand(ctx, response, responseLength, NULL /*stream*/, NULL /*writer*/, NULL /*writer handle*/);
}

/* ------------------------------------------------------------------------- */
se_result_t se_mscTransportTransmitAndStreamEx(se_ctx_t* ctx,
	FILE* stream)
{
	/* CASE: EXPORT COMMAND: response output stream will include 1024 byte tar-padding */
	return mscTransmitCommand(ctx, NULL /*response*/, NULL /*responseLength*/, stream, NULL /*writer*/, NULL /*writer handle*/);
}

/* ------------------------------------------------------------------------- */
se_result_t se_mscTransportTransmitAndWriteViaCallbackEx(se_ctx_t* ctx,
	se_writer_t writer,
	se_handle_t handle)
{
	/* CASE: EXPORT COMMAND: response output callback write will include 1024 byte tar-padding */
	return mscTransmitCommand(ctx, NULL /*response*/, NULL /*responseLength*/, NULL /*stream*/, writer, handle);
}

