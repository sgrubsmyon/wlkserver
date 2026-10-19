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
  * @file se_transport_util.h
  *
  * @brief Transport layer utilities for the cryptovision SE-API and _extended_ SE_API.
  *
  * @addtogroup SE-API-common
  *
  * @{
  */

#ifndef SE_TRANSPORT_UTIL_H
#define SE_TRANSPORT_UTIL_H

#include <stdint.h>

#include <stdio.h>
#include <stdlib.h>

#include <se_result_t.h>
#include <se_callback_t.h>

#define SE_MIN(a, b) ((a) <= (b) ? (a) : (b))

#ifdef __cplusplus
extern "C" {
#endif  

int64_t	se_currentTimeMillis(void);

void se_sleep(uint32_t milliseconds);

se_result_t se_tarAllocExportBuffer(uint8_t** response,
	uint32_t* responseLength,
	uint64_t tarRawLength,
	uint32_t tarPadding);

se_result_t streamTarPadding(FILE* stream);

se_result_t writeTarPadding(se_writer_t writer,
	se_handle_t handle, uint64_t totalDataLength);

se_result_t se_byteArrayToInt16(int16_t* val,
	const uint8_t* array,
	uint32_t arrayLength);

se_result_t se_byteArrayToUint32(uint32_t* val,
	const uint8_t* array,
	uint32_t arrayLength);

se_result_t se_byteArrayToInt64(int64_t* val,
	const uint8_t* array,
	uint32_t arrayLength);

void se_uint16ToByteArray(uint8_t* out,
	uint16_t val);

void se_uint32ToByteArray(uint8_t* out,
	uint32_t val);

void se_uint64ToByteArray(uint8_t* out,
	uint64_t val);

#ifdef __cplusplus
} /* extern "C" */
#endif  

#endif  /* SE_TRANSPORT_UTIL_H */

/** @}  SE-API  */
