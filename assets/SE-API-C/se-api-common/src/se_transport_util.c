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
  * @file se_transport_util.c
  *
  * @brief Transport layer utilities for the cryptovision SE-API and _extended_ SE_API.
  *
  * @addtogroup   SE-API-common
  */

#ifdef _WIN32
#	include <Windows.h>
#else 
#	define _BSD_SOURCE
#	define _DEFAULT_SOURCE
#	include <sys/time.h>
#	include <unistd.h>
#	include <string.h>
#endif

#include <se_memory_util.h>
#include <se_transport_util.h>

#ifdef _WIN32

/* ------------------------------------------------------------------------- */
int64_t se_currentTimeMillis()
{
	FILETIME ft_now;
	GetSystemTimeAsFileTime(&ft_now); /* UTC in num of 100-nanosecond intervals */
	LONGLONG ll_now = (LONGLONG) ft_now.dwLowDateTime + ((LONGLONG) (ft_now.dwHighDateTime) << 32LL);
	return ll_now / 10000;
}

/* ------------------------------------------------------------------------- */
void se_sleep(uint32_t milliseconds)
{
	Sleep(milliseconds);
}

#else  /* not _WIN32 */

/* ------------------------------------------------------------------------- */
int64_t se_currentTimeMillis(void)
{
	struct timeval te;
	int64_t milliseconds, M = 1000;

	gettimeofday(&te, NULL);												/* get current time */
	milliseconds = ((int64_t)te.tv_sec * M) + ((int64_t)te.tv_usec / M);	/* calculate milliseconds */
	return milliseconds;
}

/* ------------------------------------------------------------------------- */
void se_sleep(uint32_t milliseconds)
{
	usleep(milliseconds * 1000);
}

#endif

/* ------------------------------------------------------------------------- */
se_result_t se_tarAllocExportBuffer(uint8_t** response, uint32_t* responseLength,
	uint64_t tarRawLength, uint32_t tarPadding)
{
	/* allocate response buffer (add 1024 byte tar-format zero padding) */
	const uint32_t length = (uint32_t) tarRawLength + tarPadding;

	if((uint64_t) length != (tarRawLength + tarPadding))
		return ErrorAllocationfailed;

	if((*response = (uint8_t*) se_malloc(length)) == NULL)
		return ErrorAllocationfailed;

	memset(*response + length - tarPadding, 0, tarPadding);
	*responseLength = length;

	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
se_result_t streamTarPadding(FILE* stream)
{
	uint8_t tar_padding[2 * 512];
	uint32_t tar_padding_size = sizeof(tar_padding);

	memset(tar_padding, 0, tar_padding_size);
	if(tar_padding_size != fwrite(tar_padding, sizeof(uint8_t), tar_padding_size, stream))
		return ErrorStreamWrite;

	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
se_result_t writeTarPadding(se_writer_t writer,
	se_handle_t handle, uint64_t totalDataLength)
{
	uint8_t tar_padding[2 * 512];
	uint32_t tar_padding_size = sizeof(tar_padding);

	memset(tar_padding, 0, tar_padding_size);
	if(tar_padding_size != writer(tar_padding, tar_padding_size, totalDataLength, handle))
		return ErrorCallback;

	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
se_result_t se_byteArrayToInt16(int16_t* val,
	const uint8_t* array,
	uint32_t arrayLength)
{
	/* NOTE: no NULL parameter checks */
	if(arrayLength == 0 || arrayLength > sizeof(int16_t))
		return ErrorTSEResponseDataInvalid;
	{
		uint32_t i;
		int16_t number = 0;
		for(i = 0; i < arrayLength; ++i) {
			number <<= 8;
			number |= array[i];
		}
		*val = number;
	}
	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
se_result_t se_byteArrayToUint32(uint32_t* val,
	const uint8_t* array,
	uint32_t arrayLength)
{
	/* NOTE: no NULL parameter checks */
	if(arrayLength == 0 || arrayLength > sizeof(uint32_t))
		return ErrorTSEResponseDataInvalid;
	{
		uint32_t i;
		uint32_t number = 0;
		for(i = 0; i < arrayLength; ++i) {
			number <<= 8;
			number |= array[i];
		}
		*val = number;
	}
	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
se_result_t se_byteArrayToInt64(int64_t* val,
	const uint8_t* array,
	uint32_t arrayLength)
{
	/* NOTE: no NULL parameter checks */
	if(arrayLength == 0 || arrayLength > sizeof(int64_t))
		return ErrorTSEResponseDataInvalid;
	{
		uint32_t i;
		int64_t number = 0;
		for(i = 0; i < arrayLength; ++i) {
			number <<= 8;
			number |= array[i];
		}
		*val = number;
	}
	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
void se_uint16ToByteArray(uint8_t* out,
	uint16_t val)
{
	/* NOTE: no NULL parameter checks */
	out[0] = (uint8_t) ((val >> 8) & 0xFF);
	out[1] = (uint8_t) (val & 0xFF);
}

/* ------------------------------------------------------------------------- */
void se_uint32ToByteArray(uint8_t* out,
	uint32_t val)
{
	/* NOTE: no NULL parameter checks */
	out[0] = (uint8_t) ((val >> 24) & 0xFF);
	out[1] = (uint8_t) ((val >> 16) & 0xFF);
	out[2] = (uint8_t) ((val >> 8) & 0xFF);
	out[3] = (uint8_t) (val & 0xFF);
}

/* ------------------------------------------------------------------------- */
void se_uint64ToByteArray(uint8_t* out,
	uint64_t val)
{
	/* NOTE: no NULL parameter checks */
	uint32_t i, j;
	for(i = sizeof(uint64_t) - 1, j = 0; j < sizeof(uint64_t); --i, ++j)
		out[j] = (uint8_t) ((val >> (8 * i)) & 0xff);
}
