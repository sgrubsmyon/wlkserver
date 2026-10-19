/*
 * Copyright (c) 2020-2023
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
  * @file se_types_ex.h
  *
  * @brief Type definitions for the cryptovision _extended_ SE-API.
  *
  * @addtogroup SE-API-extended
  *
  * @{
  */

#ifndef SE_TYPES_EX_H
#define SE_TYPES_EX_H

#include <stdint.h>
#include <se_types.h>

/**
* HANDLE type for TSE i/o file handling.
*/
typedef int io_handle_t;

#if defined(_WIN32)
#	include <Windows.h>
#   define IoHandleToHANDLE(handle) IntToPtr(handle)
#   define HANDLEToIoHandle(handle) PtrToInt(handle)

#else
	typedef io_handle_t HANDLE;
#	define INVALID_HANDLE_VALUE -1	
#   define IoHandleToHANDLE(handle) (handle)
#   define HANDLEToIoHandle(handle) (handle)
#endif

/**
* Buffer sizes used in TSE context object.
*/
#define	SE_VERSION_BUF_SIZE			0x0040						/**< 64 bytes buffer for TSE version, 0 terminated string */
#define	SE_SERIAL_BUF_SIZE			0x0020						/**< 32 bytes buffer for TSE serial, 0 padded, NO string */
#define	SE_CMD_BUF_SIZE				0x2000						/**< 8k TSE command buffer */
#define	SE_RESPONSE_BUF_SIZE		0x8000						/**< 32k TSE response buffer */

/**
* Represents the TSE context object of extended SE-API-C.
*/
typedef struct SeCtx
{
    io_handle_t     	iOHandle;									/**< TSE i/o handle (MSC file handle) */
	uint32_t			iOTimeout;									/**< TSE i/o read timeout in milliseconds */

	char				version			[SE_VERSION_BUF_SIZE];		/**< TSE (firmware) version buffer, 0 terminated string */
	uint32_t			versionLength;								/**< length tseVersion string in bytes */
	

	uint8_t				serialNr		[SE_SERIAL_BUF_SIZE];		/**< TSE serial number buffer, 0 padded, NO string */
	uint32_t			serialNrLength;								/**< length tseSerialNr in bytes */
	uint8_t				serialNrKey		[SE_SERIAL_BUF_SIZE];		/**< Key serial number buffer, NO string */
	uint32_t			serialNrKeyLength;							/**< length key serial number in bytes */

	uint8_t				cmdBuf			[SE_CMD_BUF_SIZE];			/**< TSE command buffer */
	uint32_t			cmdBufUsed;									/**< command length (number of bytes used in cmdBuf) */
	uint16_t			cmdLE;										/**< command LE (expected response length) */

	uint8_t				responseBuf		[SE_RESPONSE_BUF_SIZE];		/**< TSE response buffer */
	uint32_t			responseBufUsed;							/**< response length (size of responseBuf (input), number of bytes used in responseBuf (output)) */
	
	uint64_t			totalDataLength;							/**< total expected response data length (incl. optional TAR padding) of the last TSE command */
	
	uint32_t			lastOSError;								/**< last error of an OS function call (GetLastError() for TSE access via WIN-API, else errno) */

	se_tse_version_t	firmwareVersion;							/**< firmware version */

	uint8_t				needsTarPadding;							/**< indicate tar end-of-archive marker to be added by transport layer */

	const uint8_t*		selfTestLog;								/** < temporary pointer to selftest log from last se_open*() call */
	uint32_t			selfTestLogLength;							/** < length og selftest log */
} se_ctx_t;

#endif  /* SE_TYPES_EX_H */

/** @}  SE-API-extended  */
