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
 * @file se_transport_ex.c
 *
 * @brief Transport layer for the cryptovision _extended_ SE-API - used by the "standard" SE-API as well.
 */

#include <se_transport_ex.h>
#include <se_msc_transport_ex.h>

/* ------------------------------------------------------------------------- */
/* Local definitions / functions                                             */
/* ------------------------------------------------------------------------- */

/* ------------------------------------------------------------------------- */
se_result_t se_map_io_result_error(int16_t io_result)
{
	switch(io_result)
	{
	/* TSE returned status codes */
	case (int16_t)0x8000:		return ErrorSECommunicationFailed;
	case (int16_t)0x8001:		return ErrorTSECommandDataInvalid;
	case (int16_t)0x8002:		return ErrorTSEResponseDataInvalid;
	case (int16_t)0x8003:		return ErrorSigningSystemOperationDataFailed;
	case (int16_t)0x8004:		return ErrorRetrieveLogMessageFailed;
	case (int16_t)0x8005:		return ErrorStorageFailure;
	case (int16_t)0x8006:		return ErrorSecureElementDisabled;
	case (int16_t)0x8007:		return ErrorUserNotAuthorized;
	case (int16_t)0x8008:		return ErrorUserNotAuthenticated;
	case (int16_t)0x8009:		return ErrorSeApiNotInitialized;
	case (int16_t)0x800A:		return ErrorUpdateTimeFailed;
	case (int16_t)0x800B:		return ErrorUserIdNotManaged;
	case (int16_t)0x800C:		return ErrorStartTransactionFailed;
	case (int16_t)0x800D:		return ErrorCertificateExpired;
	case (int16_t)0x800E:		return ErrorNoTransaction;
	case (int16_t)0x800F:		return ErrorUpdateTransactionFailed;
	case (int16_t)0x8010:		return ErrorFinishTransactionFailed;
	case (int16_t)0x8011:		return ErrorTimeNotSet;
	case (int16_t)0x8012:		return ErrorNoERS;
	case (int16_t)0x8013:		return ErrorNoKey;
	case (int16_t)0x8014:		return ErrorSeApiNotDeactivated;
	case (int16_t)0x8015:		return ErrorNoDataAvailable;
	case (int16_t)0x8016:		return ErrorTooManyRecords;
	case (int16_t)0x8017:		return ErrorUnexportedStoredData;
	case (int16_t)0x8018:		return ErrorParameterMismatch;
	case (int16_t)0x8019:		return ErrorIdNotFound;
	case (int16_t)0x801A:		return ErrorTransactionNumberNotFound;
	case (int16_t)0x801B:		return ErrorSeApiDeactivated;
	case (int16_t)0x801C:		return ErrorTransport;
	case (int16_t)0x801D:		return ErrorNoStartup;
	case (int16_t)0x801E:		return ErrorNoStorage;
	case (int16_t)0x801F:		return ErrorSelftestFailed;

	/* Additional status codes defined for se_transport layer */
	case SE_ERROR_TIMEOUT:		return ErrorTSETimeout;
	case SE_ERROR_STREAM_WRITE:	return ErrorStreamWrite;
	case SE_BUFFER_TOO_SMALL:	return ErrorBufferTooSmall;
	case SE_ALLOCATION_FAILED:	return ErrorAllocationfailed;
	case SE_ERROR_CALLBACK:		return ErrorCallback;
	default:					return ErrorTSEUnknownError;
	}
}

/* ------------------------------------------------------------------------- */
se_result_t se_check_result(int16_t io_result)
{
	if(io_result >= 0)
		return ExecutionOk;
	{
		const se_result_t result = se_map_io_result_error(io_result);
		if(result != ErrorTSEUnknownError)
			return result;
	}

	/* handle unknown TSE error, like SE_EXPORT_DATA */
	switch(io_result)
	{
	case SE_EXPORT_DATA:		return ExecutionOk;
	default:					return ErrorSigningSystemOperationDataFailed;
	}
}


/* ------------------------------------------------------------------------- */
/* se_transport_ex.h functions                                               */
/* ------------------------------------------------------------------------- */

/* ------------------------------------------------------------------------- */
se_result_t se_transportOpenEx(se_ctx_t* ctx, 
	const char *devicePath)
{
	if(ctx == NULL)
		return ErrorMissingParameter;

	ctx->iOHandle = HANDLEToIoHandle(INVALID_HANDLE_VALUE);
	return se_mscTransportOpenEx(ctx, devicePath);
}

/* ------------------------------------------------------------------------- */
se_result_t se_transportCloseEx(se_ctx_t* ctx)
{
	if(ctx == NULL)
		return ErrorMissingParameter;
	{
		se_result_t result = se_mscTransportCloseEx(ctx);
		ctx->iOHandle = HANDLEToIoHandle(INVALID_HANDLE_VALUE);
		return result;
	}
}

/* ------------------------------------------------------------------------- */
se_result_t se_transportSendEx(se_ctx_t* ctx)
{
	if(ctx == NULL)
		return ErrorMissingParameter;
	
	return se_mscTransportTransmitEx(ctx);
}

/* ------------------------------------------------------------------------- */
se_result_t se_transportSendAndWriteEx(se_ctx_t* ctx,
	uint8_t** response,
	uint32_t* responseLength)
{
	if(ctx == NULL || response == NULL || responseLength == NULL)
		return ErrorMissingParameter;

	return se_mscTransportTransmitAndWriteEx(ctx, response, responseLength);
}

/* ------------------------------------------------------------------------- */
se_result_t se_transportSendAndStreamEx(se_ctx_t* ctx,
	FILE* stream)
{
	if(ctx == NULL || stream == NULL)
		return ErrorMissingParameter;

	return se_mscTransportTransmitAndStreamEx(ctx, stream);
}

/* ------------------------------------------------------------------------- */
se_result_t se_transportSendAndWriteViaCallbackEx(se_ctx_t* ctx,
	se_writer_t writer,
	se_handle_t handle)
{
	if(ctx == NULL || writer == NULL)
		return ErrorMissingParameter;

	return se_mscTransportTransmitAndWriteViaCallbackEx(ctx, writer, handle);
}
