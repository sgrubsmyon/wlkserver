/*
 * Copyright (c) 2019-2023
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
  * @file se_transport_ex.h
  *
  * @brief Transport layer definitions for the cryptovision _extended_ SE-API - used by the "standard" SE-API as well.
  *
  * @addtogroup SE-API-extended
  *
  * @{
  */

#ifndef SE_TRANSPORT_H
#define SE_TRANSPORT_H

#ifndef NULL
#	define NULL ((void *)0)
#endif

#include <stdint.h>

#include <stdio.h>
#include <stdlib.h>

#include <se_types_ex.h>
#include <se_result_t.h>
#include <se_callback_t.h>

/**
* TSE transport mode config.
*/

#define SE_DEFAULT_IO_TIMEOUT		10000						/**< time to answer from the TSE (milliseconds) */
#define SE_DEFAULT_IO_READDELAY		10							/**< time between polls of the TSE (milliseconds) */


/**
* Useful TSE status codes (refer se_check_result()-func).
*/

/* requested command response length (LE) */
#define SE_LE_0						((uint16_t) 0x0000)
#define SE_NO_LE					((uint16_t) 0xffff)

/* TSE returned status codes */
#define SE_EXPORT_DATA				((int16_t) 0x9000)
#define SE_COMMUNICTION_FAILED		((int16_t) 0x8000)
#define SE_COMMAND_DATA_INVALID		((int16_t) 0x8001)
#define SE_RESPONSE_DATA_INVALID	((int16_t) 0x8002)

/* MSC transport internal used */
#define SE_WAIT_FOR_RESPONSE		((uint16_t) 0xffff)
#define SE_SD_TIMEOUT				((uint16_t) 0xff45)
#define SE_SD_ERROR_MASK			((uint16_t) 0xff00)
#define SE_SD_ERROR_ID_MASK			((uint16_t) 0x00ff)

/* additional status codes defined for se_transport layer */
#define SE_ERROR_TIMEOUT			((int16_t) 0x8100)
#define SE_ERROR_STREAM_WRITE		((int16_t) 0x8101)
#define SE_BUFFER_TOO_SMALL			((int16_t) 0x8102)
#define SE_ALLOCATION_FAILED		((int16_t) 0x8103)
#define SE_ERROR_CALLBACK			((int16_t) 0x8104)

#ifdef __cplusplus
extern "C" {
#endif  

	/**
	* Open TSE transport I/O connection.
	* @param[in,out]  ctx
	*                   context handle object for the TSE to be opened [REQUIRED]\n
	*                   upon return the @ref SeCtx.iOHandle "iOHandle" member references the TSE (or INVALID_HANDLE_VALUE)
	* @param[in]      devicePath
	*                   path to the TSE [REQUIRED]\n
	*                   for more information, please see @ref TLConfiguration
	*
	* @return @ref ExecutionOk      execution of the function has been successful
	* @return @ref ErrorIO          open connection failed
	*/
	se_result_t se_transportOpenEx(se_ctx_t* ctx, 
		const char *devicePath);

	/**
	* Close TSE transport IO connection.
	* @param[in,out]  ctx
	*                   context handle object of the TSE to be closed [REQUIRED]\n
	*                   upon return the @ref SeCtx.iOHandle "iOHandle" member will be reset
	*
	* @return @ref ExecutionOk      execution of the function has been successful
	* @return @ref ErrorIO          close connection failed
	*/
	se_result_t se_transportCloseEx(se_ctx_t* ctx);

	/**
	* TSE transport send and receive function.
	*   Data to be sent to the TSE is to be provided in the @ref SeCtx "context":
	*   * @ref SeCtx.cmdBuf          "cmdBuf":           command data to send [REQUIRED]
	*   * @ref SeCtx.cmdBufUsed      "cmdBufUsed":       length of the data to send [REQUIRED]
	*   * @ref SeCtx.cmdLE           "cmdLE":            requested response length, use SE_NO_LE if not applicable [REQUIRED]
	*   * @ref SeCtx.responseBuf     "responseBuf":      buffer for the response to be received [REQUIRED]
	*   * @ref SeCtx.responseBufUsed "responseBufUsed":  size of ctx.responseBuf in byte [REQUIRED]
	*
	*   Data received from the TSE is returned via the @ref SeCtx "context" in a similar manner:
	*   * @ref SeCtx.responseBuf     "responseBuf":      response received from the TSE at offset 0
	*   * @ref SeCtx.responseBufUsed "responseBufUsed":  size of response received (number of bytes)
	*
	* @param[in,out] ctx
	*                  context handle object of the TSE to access [REQUIRED]
	*
	* @return @ref ExecutionOk      execution of the function has been successful
	* @return @ref ErrorIO          connection failed
	* @return otherwise             command specific error
	*/
	se_result_t se_transportSendEx(se_ctx_t* ctx);

	/**
	* TSE transport send and write function for se_exportData()-function.
	*   Data to be sent to the TSE is to be provided in the @ref SeCtx "context":
	*   * @ref SeCtx.cmdBuf          "cmdBuf":           command data to send [REQUIRED]
	*   * @ref SeCtx.cmdBufUsed      "cmdBufUsed":       length of the data to send [REQUIRED]
	*   * @ref SeCtx.cmdLE           "cmdLE":            requested response length, use SE_NO_LE if not applicable [REQUIRED]
	*
	*   Data received from the TSE is returned via @p response and @p responseLength.
	*
	* @param[in]    ctx
	*                 context handle object of the TSE to access [REQUIRED]
	* @param[out]   response
	*                 buffer allocated for the response received [REQUIRED];\n
	*                 the buffer must be freed by the caller
	* @param[out]   responseLength
	*                 length of the buffer allocated for the response received [REQUIRED]
	*
	* @return @ref ExecutionOk      execution of the function has been successful
	* @return @ref ErrorIO          connection failed
	* @return otherwise             command specific error
	*/
	se_result_t se_transportSendAndWriteEx(se_ctx_t* ctx,
		uint8_t** response,
		uint32_t* responseLength);

	/**
	* TSE transport send and write function for se_exportDataToStream()-function.
	*   Data to be sent to the TSE is to be provided in the @ref SeCtx "context":
	*   * @ref SeCtx.cmdBuf          "cmdBuf":           command data to send [REQUIRED]
	*   * @ref SeCtx.cmdBufUsed      "cmdBufUsed":       length of the data to send [REQUIRED]
	*   * @ref SeCtx.cmdLE           "cmdLE":            requested response length, use SE_NO_LE if not applicable [REQUIRED]
	*
	*   Data received from the TSE is written to the @p stream.
	*
	* @param[in]    ctx
	*                 context handle object of the TSE to access [REQUIRED]
	* @param[in]    stream
	*                 open output stream for the command response [REQUIRED]
	*
	* @return @ref ExecutionOk      execution of the function has been successful
	* @return @ref ErrorIO          connection failed
	* @return otherwise             command specific error
	*/
	se_result_t se_transportSendAndStreamEx(se_ctx_t* ctx,
		FILE* stream);

	/**
	* TSE transport send and write function for se_exportDataViaCallback()-function.
	*   Data to be sent to the TSE is to be provided in the @ref SeCtx "context":
	*   * @ref SeCtx.cmdBuf          "cmdBuf":           command data to send [REQUIRED]
	*   * @ref SeCtx.cmdBufUsed      "cmdBufUsed":       length of the data to send [REQUIRED]
	*   * @ref SeCtx.cmdLE           "cmdLE":            requested response length, use SE_NO_LE if not applicable [REQUIRED]
	*
	*   Data received from the TSE is passed to the @p writer.
	*
	* @param[in]    ctx
	*                 context handle object of the TSE to access [REQUIRED]
	* @param[in]    writer
	*			      address of "writer" callback (@ref se_writer_t)
	* @param[in]    handle
	*                 parameter to pass to @p writer; not further specified here!
	*
	* @return @ref ExecutionOk      execution of the function has been successful
	* @return @ref ErrorIO          connection failed
	* @return otherwise             command specific error
	*/
	se_result_t se_transportSendAndWriteViaCallbackEx(se_ctx_t* ctx,
		se_writer_t writer,
		se_handle_t handle);


#ifdef __cplusplus
} /* extern "C" */
#endif  

#endif  /* SE_TRANSPORT_H */

/** @}  SE-API-extended  */
