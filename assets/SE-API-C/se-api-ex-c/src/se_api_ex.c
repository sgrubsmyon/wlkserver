/*
 * Copyright (c) 2019-2026
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
* @file se_api_ex.c
* @brief _Extended_ SE-API implementation - used by the "standard" SE-API as well.
*/

#include <string.h>

#include <se_transport_ex.h>
#include <se_memory_util.h>
#include <se_transport_util.h>

#include <se_api_ex.h>


/* ------------------------------------------------------------------------- */
/* Local definitions                                                         */
/* ------------------------------------------------------------------------- */

/**
* TSE, SE-API and SE-API-C implementation version buffers and constants.
*/

static const char*		SE_API_VERSION_STR			= "cryptovision SE-API v3.1";			/**< current SE-API version */
static const uint8_t	SE_API_VERSION[]			= { 0x03, 0x01 };						/**< current SE-API version */
static const char*		SE_API_EX_C_VERSION_STR		= "cryptovision SE-API-EX-C v3.1.3";	/**< current SE-API-EX-C implementation version */
static const uint8_t	SE_API_EX_C_VERSION[]		= { 0x03, 0x01, 0x03 };					/**< current SE-API-EX-C implementation version */

/**
* TSE command identifiers.
*/
typedef enum SeCommand
{
	Start					= 0x0000,

	GetPinStates			= 0x0001,
	InitializePins			= 0x0002,

	AuthenticateUser		= 0x0003,
	UnblockUser				= 0x0004,
	Logout					= 0x0005,

	Initialize				= 0x0006,
	UpdateTime				= 0x0007,
	GetSerialNumbers		= 0x0008,
	RegisterClient			= 0x0009,	/*	TCFKA	MapERStoKey	*/

	StartTransaction		= 0x000A,
	UpdateTransaction		= 0x000B,
	FinishTransaction		= 0x000C,

	ExportData				= 0x000D,
	GetCertificates			= 0x000E,
	ReadLogMessage			= 0x000F,
	Erase					= 0x0010,

	GetConfigData			= 0x0011,
	GetStatus				= 0x0012,

	Lock					= 0x0013,	/*	TCFKA	Deactivate	*/
	Unlock					= 0x0014,	/*	TCFKA	Activate	*/
	Disable					= 0x0015,

	/* new in SE-API version 2.0 */
	ExportMoreData			= 0x0016,
	GetERSMappings			= 0x0017,
	GetKeyData				= 0x0018,
	GetWearIndicator		= 0x0019,

	/* new in SE-API version 2.1 */
	DeleteUpTo				= 0x001B,
	Shutdown				= 0x00FF,

	/* new in SE-API version 2.4.0 */
	FirmwareUpdate			= 0x0063,
	/* new in SE-API version 3.0.0 */
	SelfTest				= 0x0064,
	ListClients				= 0x001C
} se_command_t;

/**
* TSE command/response data types.
*/
typedef enum SeDataType
{
	DataTypeByte			= 0x01,
	DataTypeByteArray		= 0x02,
	DataTypeShort			= 0x03,
	DataTypeString			= 0x04,
	DataTypeUInt32Array		= 0x05
} se_data_t;

/**
* TSE config data identifiers.
*/
typedef enum SeConfigDataID
{
	Version					= 0x0000,
	SignatureAlgorithm		= 0x0001,
	SupportedUpdateVariants = 0x0002,
	MaxKeys					= 0x0003,
	MaxClients				= 0x0004,
	MaxTransactions			= 0x0005,
	TimeSyncInterval		= 0x0006,
	SupportedTimeFormats	= 0x0007,
	CertificationId         = 0x0008
} se_config_data_id_t;

/**
* TSE status info identifiers.
*/
typedef enum SeStatusID
{
	NumClients				= 0x0000,
	NumTransactions			= 0x0001,
	OpenTransactions		= 0x0002,
	TransactionCounter		= 0x0003,
	LifeCycleState			= 0x0004,
	TotalMemory				= 0x0005,
	AvailableMemory			= 0x0006,
	MinCounter				= 0x0007,	/** < @since 2.4.0, not available on TSE v1  */
	MaxCounter				= 0x0008,	/** < @since 2.4.0, not available on TSE v1  */
	NextCounter				= 0x0009,	/** < @since 2.4.0, not available on TSE v1  */
	Temperature				= 0x000A    /** < @since 3.0.0, not available on TSE v1  */
} se_status_id_t;

/**
* TSE key data identifiers.
*/
typedef enum SeKeyDataID
{
	SignatureCounter		= 0x0000,
	ExpirationDate			= 0x0001,
	PublicKey				= 0x0002,
	Certificate				= 0x0003
} se_key_data_id_t;

/**
* SE-API command constants.
*/

#define			SE_CMD_HEADER_SIZE				6
#define			SE_CMD_HEADER_LENGTH_OFFSET		4

#define			SE_MAX_CMD_DATA					(SE_CMD_BUF_SIZE - 36)		/**< Maximum command length is 8156 byte (8k - 36 byte MSC header) */
#define			SE_MAX_SIZE_STRING				512

/**
* SE-API implementation types and definitions.
*/

typedef enum
{
	case1 = 0,
	case2,
	case3,
	case4
} se_command_case_t;

typedef struct
{
	se_data_t			dataType;
	const uint8_t*		data;
	uint32_t			dataLength;
} se_data_obj_array_t;

typedef enum
{
	toBuffer = 0,
	toStream,
	viaCallback
} se_export_mode_t;

typedef struct
{
	se_export_mode_t	mode;
	uint8_t**			buffer;
	uint32_t*			bufferLength;
	FILE*				stream;
	se_writer_t			writer;
	se_handle_t			handle;
} se_export_output_t;

/**
* TSE i/o file name.
*/

#define	SE_MSC_IO_FILE	"TSE-IO.bin"



/* ------------------------------------------------------------------------- */
/* Local functions                                                           */
/* ------------------------------------------------------------------------- */


/* ------------------------------------------------------------------------- */
static int isFirmwareV1(se_ctx_t* ctx)
{
	return ((ctx != NULL) && (ctx->firmwareVersion == version1)) ? 1 : 0;
}

/* ------------------------------------------------------------------------- */
static uint16_t buildCmdHeader(uint8_t* cmdBuf,
	se_command_t command)
{
	/* TSE command header = 5C 54 CC CC LL LL */

	/* add 5C 54 = "\T" */
	cmdBuf[0] = (uint8_t)(0x5C);
	cmdBuf[1] = (uint8_t)(0x54);

	/* add command CC CC */
	cmdBuf[2] = (uint8_t)(command >> 8);
	cmdBuf[3] = (uint8_t)(command & 0xFF);

	/* reset command length LL LL (filled later) */
	cmdBuf[4] = (uint8_t)(0x00);
	cmdBuf[5] = (uint8_t)(0x00);

	return SE_CMD_HEADER_SIZE;
}

/* ------------------------------------------------------------------------- */
static void setCmdDataLength(uint8_t* cmdBuf,
	uint16_t length)
{
	/* set command length LL LL */
	cmdBuf[SE_CMD_HEADER_LENGTH_OFFSET + 0] = (uint8_t)(length >> 8);
	cmdBuf[SE_CMD_HEADER_LENGTH_OFFSET + 1] = (uint8_t)(length & 0xFF);
}

/* ------------------------------------------------------------------------- */
static se_result_t appendCmdData(uint8_t* cmdBuf,
	uint16_t* offset,
	se_data_t dataType,
	const uint8_t* data,
	uint32_t dataLength)
{
	uint32_t pos = *offset;

	/* check max data length */
	if((pos + dataLength) > SE_MAX_CMD_DATA)
		return ErrorTSECommandDataInvalid;

	/* append type */
	cmdBuf[pos++] = (uint8_t)(dataType);

	/* append length */
	cmdBuf[pos++] = (uint8_t)(dataLength >> 8);
	cmdBuf[pos++] = (uint8_t)(dataLength & 0xFF);

	/* append data */
	switch(dataType)
	{
	case DataTypeByte:
		if(dataLength != 1)
			return ErrorTSECommandDataInvalid;
		break;

	case DataTypeByteArray:
		break;

	case DataTypeShort:
		if(dataLength != 2)
			return ErrorTSECommandDataInvalid;
		break;

	case DataTypeString:
		if(dataLength > SE_MAX_SIZE_STRING)
			return ErrorTSECommandDataInvalid;
		break;

	default:
		break;
	}

	if(data != NULL && dataLength != 0)
		memcpy(cmdBuf + pos, data, dataLength);
	*offset = (uint16_t)(pos + dataLength);

	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
static se_result_t buildCmd(se_ctx_t* ctx, 
	se_command_t command,
	const se_data_obj_array_t* dataObjects,
	uint32_t numOfDataObjects,
	uint16_t le)
{
	if(ctx == NULL)
		return ErrorMissingParameter;
	{
		se_result_t result;

		uint32_t i;
		uint16_t cmd_len;
		uint8_t* cmdBuf = ctx->cmdBuf;

		/* clear last command from buffer */
		memset(cmdBuf, 0, ctx->cmdBufUsed);
		ctx->cmdBufUsed = 0;

		/* build command data */
		cmd_len = buildCmdHeader(cmdBuf, command);
		for(i = 0; i < numOfDataObjects; ++i)
			if((result = appendCmdData(cmdBuf, &cmd_len, dataObjects[i].dataType, dataObjects[i].data, dataObjects[i].dataLength)) != ExecutionOk)
				return result;

		ctx->cmdBufUsed = cmd_len;
		setCmdDataLength(cmdBuf, (uint16_t)(cmd_len - SE_CMD_HEADER_SIZE));

		/* set LE */
		ctx->cmdLE = le;

		return ExecutionOk;
	}
}

/* ------------------------------------------------------------------------- */
static se_result_t sendCmd(se_ctx_t* ctx, 
	se_command_t command,
	se_command_case_t command_case,
	const se_data_obj_array_t* dataObjects,
	uint32_t numOfDataObjects,
	uint16_t le)
{
	se_result_t result;

	/* command parameter check (NOTE: no LE checks) */
	switch(command_case)
	{
	case case1:
	case case2:
		if(dataObjects != NULL || numOfDataObjects != 0)
			return ErrorParameterMismatch;
		break;

	case case3:
	case case4:
		if(dataObjects == NULL || numOfDataObjects == 0)
			return ErrorMissingParameter;
		break;

	default:
		return ErrorParameterMismatch;
	}

	/* build command data */
	if((result = buildCmd(ctx, command, dataObjects, numOfDataObjects, le)) != ExecutionOk)
		return result;

	/* clear last response */
	memset(ctx->responseBuf, 0, ctx->responseBufUsed);
	ctx->responseBufUsed = SE_RESPONSE_BUF_SIZE;
	/* "stored" inside responseBuf */
	ctx->selfTestLog = NULL;
	ctx->selfTestLogLength = 0;

	/* transmit command data */
	if((result = se_transportSendEx(ctx)) != ExecutionOk)
		return result;

	/* command response check (NOTE: no LE checks) */
	switch(command_case)
	{
	case case1:
	case case3:
		if(ctx->responseBufUsed != 0)
			return ErrorTSEResponseDataInvalid;
		break;
	case case2:
	case case4:
		if(le != SE_LE_0 && ctx->responseBufUsed == 0)
			return ErrorTSEResponseDataInvalid;
		break;
	}

	return result;
}

/* ------------------------------------------------------------------------- */
static se_result_t sendCase1Cmd(se_ctx_t* ctx,
	se_command_t command)
{
	/* no command data present, no response data expect */
	return sendCmd(ctx, command, case1, NULL, 0, SE_NO_LE);
}

/* ------------------------------------------------------------------------- */
static se_result_t sendCase2Cmd(se_ctx_t* ctx,
	se_command_t command)
{
	/* no command data present, response data expect */
	return sendCmd(ctx, command, case2, NULL, 0, SE_LE_0);
}

/* ------------------------------------------------------------------------- */
static se_result_t sendCase3Cmd(se_ctx_t* ctx,
	se_command_t command,
	const se_data_obj_array_t* dataObjects,
	uint32_t numOfDataObjects)
{
	/* command data present, no response data expect */
	return sendCmd(ctx, command, case3, dataObjects, numOfDataObjects, SE_NO_LE);
}

/* ------------------------------------------------------------------------- */
static se_result_t sendCase4Cmd(se_ctx_t* ctx,
	se_command_t command,
	const se_data_obj_array_t* dataObjects,
	uint32_t numOfDataObjects)
{
	/* command data present, response data expect */
	return sendCmd(ctx, command, case4, dataObjects, numOfDataObjects, SE_LE_0);
}

/* ------------------------------------------------------------------------- */
static se_result_t getResponseObjects(se_ctx_t* ctx,
	se_data_obj_array_t* dataObjects,
	uint32_t* numOfDataObjects,
	uint32_t numOfOptionalObjects)
{
	uint32_t pos = 0, obj_count = 0;
	const uint8_t* responseBuf = ctx->responseBuf;
	const uint32_t responseBufUsed = ctx->responseBufUsed;

	while(pos < responseBufUsed)
	{
		se_data_t data_type;
		uint32_t data_length;

		if(pos + 3 > responseBufUsed || obj_count > *numOfDataObjects)
			return ErrorTSEResponseDataInvalid;
		{
			/* get and validate expected response object type */
			data_type = (se_data_t)responseBuf[pos];
			if(data_type != dataObjects[obj_count].dataType)
				return ErrorTSEResponseDataInvalid;

			/* get response object length */
			data_length = ((uint32_t)responseBuf[pos + 1] << 8) | responseBuf[pos + 2];

			/* validate response object length (buffer size check) */
			pos += 3;
			if(pos + data_length > responseBufUsed)
				return ErrorTSEResponseDataInvalid;

			/* validate response object length */
			switch(data_type)
			{
			case DataTypeByte:
				if(data_length != 1)
					return ErrorTSEResponseDataInvalid;
				break;

			case DataTypeByteArray:
				break;

			case DataTypeShort:
				if(data_length != 2)
					return ErrorTSEResponseDataInvalid;
				break;

			case DataTypeString:
				break;

			case DataTypeUInt32Array:
				if(data_length % sizeof(uint32_t) != 0)
					return ErrorTSEResponseDataInvalid;
				break;

			default:
				return ErrorTSEResponseDataInvalid;
			}
		
			dataObjects[obj_count].data = responseBuf + pos;
			dataObjects[obj_count].dataLength = data_length;

			obj_count++;
			pos += data_length;
		}
	}

	if(pos != responseBufUsed || obj_count + numOfOptionalObjects < *numOfDataObjects)
		return ErrorTSEResponseDataInvalid;

	*numOfDataObjects = obj_count;

	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
static se_result_t getByteArray(se_ctx_t* ctx,
	uint8_t **array,
	uint32_t *arrayLength,
	se_command_t command,
	const se_data_obj_array_t* dataObjects,
	uint32_t numOfDataObjects,
	uint32_t zeroPaddingSize)
{
	if(array == NULL || arrayLength == NULL)
		return ErrorMissingParameter;
	{
		se_result_t result = dataObjects == NULL
			? sendCase2Cmd(ctx, command)
			: sendCase4Cmd(ctx, command, dataObjects, numOfDataObjects);

		if(result == ExecutionOk)
		{
			/* 1 response object of type ByteArray expected */
			se_data_obj_array_t response_obj[1];
			uint32_t num_response_obj = sizeof(response_obj) / sizeof(se_data_obj_array_t);

			response_obj[0].dataType = DataTypeByteArray;	/* array */

			if((result = getResponseObjects(ctx, response_obj, &num_response_obj, 0)) == ExecutionOk)
			{
				uint32_t data_length = response_obj[0].dataLength;
				uint32_t out_length  = data_length + zeroPaddingSize;
				if(out_length == 0)
				{
					*array = NULL;
					*arrayLength = 0;
					return ExecutionOk;
				}

				/* allocate and return array buffer */
				if((*array = (uint8_t*) se_malloc(out_length)) == NULL)
					return ErrorAllocationfailed;

				/* add optional zero padding to TSE output */
				if(zeroPaddingSize != 0) memset(*array + data_length, 0, zeroPaddingSize);

				*arrayLength = out_length;
				memcpy(*array, response_obj[0].data, data_length);
			}
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
static se_result_t initCtxSerialNumber(se_ctx_t* ctx)
{
	if(ctx == NULL)
		return ErrorMissingParameter;
	{
		se_result_t result = ExecutionOk;
		if(ctx->serialNrKeyLength == 0)
		{
			uint8_t *tmpNr = NULL;
			const uint32_t offsetSerialNrKey = 6;
			const uint32_t sizeSerialNrKey = SE_SERIAL_BUF_SIZE;

			/* fetch serial number only for TSEv1 - v2 doesn't need it at all */
			if(!isFirmwareV1(ctx))
				return ExecutionOk;

			result = getByteArray(ctx, &tmpNr, &ctx->serialNrKeyLength, GetSerialNumbers, NULL, 0, 0);
			if(result == ExecutionOk && ctx->serialNrKeyLength >= (offsetSerialNrKey + sizeSerialNrKey)) {
				memcpy(ctx->serialNrKey, tmpNr + offsetSerialNrKey, sizeSerialNrKey);
				ctx->serialNrKeyLength = sizeSerialNrKey;
			}

			if(tmpNr != NULL)
				se_free(tmpNr);
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
static se_result_t checkSerialNumberKey(se_ctx_t* ctx,
	const uint8_t **serialNumberKey,
	uint32_t *serialNumberLength)
{
	se_result_t result = ExecutionOk;

	if((result = initCtxSerialNumber(ctx)) != ExecutionOk)
		return result;

	if(isFirmwareV1(ctx) && *serialNumberKey == NULL && *serialNumberLength == 0)
	{
		*serialNumberKey    = ctx->serialNrKey;
		*serialNumberLength = ctx->serialNrKeyLength;
	}

	return result;
}

/* ------------------------------------------------------------------------- */
static se_result_t getKeyNumber(se_ctx_t* ctx, 
	uint32_t *value32,
	int64_t *timeValue,
	se_key_data_id_t valueId,
	const uint8_t* keyId,
	uint32_t keyIdLength)
{
	if(value32 == NULL && timeValue == NULL)
		return ErrorMissingParameter;
	if(value32 != NULL && timeValue != NULL)
		return ErrorParameterMismatch;
	{
		se_result_t result;
		se_data_obj_array_t data_obj[2];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		/* 2 data objects: valueId as Short and keyId as ByteArray */
		uint8_t id_array[2];
		se_uint16ToByteArray(id_array, valueId);

		/* handle serial number parameter */
		if((result = checkSerialNumberKey(ctx, &keyId, &keyIdLength)) != ExecutionOk)
			return result;

		data_obj[0].dataType = DataTypeShort;
		data_obj[0].data = id_array;
		data_obj[0].dataLength = sizeof(id_array);

		data_obj[1].dataType	= DataTypeByteArray;
		data_obj[1].data		= keyId;
		data_obj[1].dataLength	= keyIdLength;

		if((result = sendCase4Cmd(ctx, GetKeyData, data_obj, num_data_obj)) == ExecutionOk)
		{
			/* 1 response object of type ByteArray expected */
			se_data_obj_array_t response_obj[1];
			uint32_t num_response_obj = sizeof(response_obj) / sizeof(se_data_obj_array_t);

			response_obj[0].dataType = DataTypeByteArray;	/* value */

			if((result = getResponseObjects(ctx, response_obj, &num_response_obj, 0)) == ExecutionOk)
			{
				if(value32 != NULL)
					return se_byteArrayToUint32(value32, response_obj[0].data, response_obj[0].dataLength);
				else
					return se_byteArrayToInt64(timeValue, response_obj[0].data, response_obj[0].dataLength);
			}
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
static se_result_t getNumber(se_ctx_t* ctx, 
	uint32_t *value32,
	uint64_t *value64,
	se_command_t command, 
	uint16_t valueId)
{
	if(value32 == NULL && value64 == NULL)
		return ErrorMissingParameter;
	if(value32 != NULL && value64 != NULL)
		return ErrorParameterMismatch;
	{
		se_result_t result;
		se_data_obj_array_t data_obj[1];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		/* 1 data object: valueId as Short */
		uint8_t id_array[2];
		se_uint16ToByteArray(id_array, valueId);

		data_obj[0].dataType = DataTypeShort;
		data_obj[0].data = id_array;
		data_obj[0].dataLength = sizeof(id_array);

		if((result = sendCase4Cmd(ctx, command, data_obj, num_data_obj)) == ExecutionOk)
		{
			/* 1 response object of type ByteArray expected */
			se_data_obj_array_t response_obj[1];
			uint32_t num_response_obj = sizeof(response_obj) / sizeof(se_data_obj_array_t);

			response_obj[0].dataType = DataTypeByteArray;	/* value */

			if((result = getResponseObjects(ctx, response_obj, &num_response_obj, 0)) == ExecutionOk)
			{
				if(value32 != NULL)
					return se_byteArrayToUint32(value32, response_obj[0].data, response_obj[0].dataLength);
				else
					return se_byteArrayToInt64((int64_t*) value64, response_obj[0].data, response_obj[0].dataLength);
			}
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
static se_result_t getConfigNumber(se_ctx_t* ctx, 
	uint32_t *value,
	se_config_data_id_t valueId)
{
	if(valueId != (uint16_t) valueId)
		return ErrorParameterMismatch;

	return getNumber(ctx, value, NULL, GetConfigData, (uint16_t) valueId);
}

/* ------------------------------------------------------------------------- */
static se_result_t getStatusNumber(se_ctx_t* ctx, 
	uint32_t *value,
	se_status_id_t valueId)
{
	if(valueId != (uint16_t) valueId)
		return ErrorParameterMismatch;

	return getNumber(ctx, value, NULL, GetStatus, (uint16_t) valueId);
}

/* ------------------------------------------------------------------------- */
static se_result_t getLongStatusNumber(se_ctx_t* ctx, 
	uint64_t *value,
	se_status_id_t valueId)
{
	if(valueId != (uint16_t) valueId)
		return ErrorParameterMismatch;

	return getNumber(ctx, NULL, value, GetStatus, (uint16_t)valueId);
}

/* ------------------------------------------------------------------------- */
static se_result_t getString(se_ctx_t* ctx, 
	char **cstr,
	uint32_t *cstrLength,
	se_command_t command,
	const se_data_obj_array_t* dataObjects,
	uint32_t numOfDataObjects)
{
	if(cstr == NULL || cstrLength == NULL)
		return ErrorMissingParameter;
	{
		se_result_t result = dataObjects == NULL
			? sendCase2Cmd(ctx, command)
			: sendCase4Cmd(ctx, command, dataObjects, numOfDataObjects);

		if(result == ExecutionOk)
		{
			/* 1 response object of type String expected */
			se_data_obj_array_t response_obj[1];
			uint32_t num_response_obj = sizeof(response_obj) / sizeof(se_data_obj_array_t);

			response_obj[0].dataType = DataTypeString;	/* string */

			if((result = getResponseObjects(ctx, response_obj, &num_response_obj, 0)) == ExecutionOk)
			{
				uint32_t data_length = response_obj[0].dataLength;
				if(data_length == 0)
				{
					*cstr = NULL;
					*cstrLength = 0;
					return ExecutionOk;
				}

				/* allocate and return string (not null terminated) */
				if((*cstr = (char*) se_malloc(data_length)) == NULL)
					return ErrorAllocationfailed;

				*cstrLength = data_length;
				memcpy(*cstr, response_obj[0].data, data_length);
			}
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
static se_result_t checkExportOutput(se_export_output_t output)
{
	switch(output.mode)
	{
	case toBuffer:
		if(output.buffer == NULL || output.bufferLength == NULL)
			return ErrorMissingParameter;
		break;

	case toStream:
		if(output.stream == NULL)
			return ErrorMissingParameter;
		break;

	case viaCallback:
		if(output.writer == NULL)
			return ErrorMissingParameter;
		break;

	default:
		return ErrorParameterMismatch;
	}

	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
static se_result_t doExportData(se_ctx_t* ctx, 
	se_command_t command,
	const se_data_obj_array_t* dataObjects,
	uint32_t numOfDataObjects, 
	se_export_output_t output)
{
	se_result_t result;

	/* build command data */
	if((result = buildCmd(ctx, command, dataObjects, numOfDataObjects, SE_LE_0)) != ExecutionOk)
		return result;

	switch(output.mode)
	{
	case toBuffer:
		/* transmit command data, write response to output buffer (incl. buffer allocation) */
		return se_transportSendAndWriteEx(ctx, output.buffer, output.bufferLength);

	case toStream:
		/* transmit command data, write response to output stream */
		return se_transportSendAndStreamEx(ctx, output.stream);

	case viaCallback:
		/* transmit command data, process response with callback function and handle */
		return se_transportSendAndWriteViaCallbackEx(ctx, output.writer, output.handle);

	default:
		return ErrorParameterMismatch;
	}
}

/* ------------------------------------------------------------------------- */
static se_result_t exportData(se_ctx_t* ctx, 
	const char *clientId,
	uint32_t clientIdLength,
	uint32_t transactionNumber,
	uint32_t startTransactionNumber,
	uint32_t endTransactionNumber,
	int64_t startDate,
	int64_t endDate,
	int32_t maximumNumberRecords,
	se_export_output_t output)
{
	se_result_t result;

	/* check export mode parameter */
	if((result = checkExportOutput(output)) != ExecutionOk)
		return result;

	/* check time parameter */
	if(startDate > SE_MAX_TIME || endDate > SE_MAX_TIME) /* maximum 32 bit */
		return ErrorParameterMismatch;

	/* export data */
	{
		se_data_obj_array_t data_obj[7];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		uint8_t transaction_number[sizeof(uint32_t)];
		uint8_t start_transaction_number[sizeof(uint32_t)];
		uint8_t end_transaction_number[sizeof(uint32_t)];
		uint8_t start_date[sizeof(uint64_t)];
		uint8_t end_date[sizeof(uint64_t)];
		uint8_t maximum_number_records[sizeof(uint32_t)];

		se_uint32ToByteArray(transaction_number, transactionNumber);
		se_uint32ToByteArray(start_transaction_number, startTransactionNumber);
		se_uint32ToByteArray(end_transaction_number, endTransactionNumber);
		se_uint64ToByteArray(start_date, (uint64_t)startDate);
		se_uint64ToByteArray(end_date, (uint64_t)endDate);
		se_uint32ToByteArray(maximum_number_records, maximumNumberRecords);

		data_obj[0].dataType = DataTypeString;
		data_obj[0].data = (uint8_t*)clientId;
		data_obj[0].dataLength = clientId != NULL ? clientIdLength : 0;

		data_obj[1].dataType = DataTypeByteArray;
		data_obj[1].data = transaction_number;
		data_obj[1].dataLength = sizeof(transaction_number);

		data_obj[2].dataType = DataTypeByteArray;
		data_obj[2].data = start_transaction_number;
		data_obj[2].dataLength = sizeof(start_transaction_number);

		data_obj[3].dataType = DataTypeByteArray;
		data_obj[3].data = end_transaction_number;
		data_obj[3].dataLength = sizeof(end_transaction_number);

		data_obj[4].dataType = DataTypeByteArray;
		data_obj[4].data = start_date;
		data_obj[4].dataLength = sizeof(start_date);

		data_obj[5].dataType = DataTypeByteArray;
		data_obj[5].data = end_date;
		data_obj[5].dataLength = sizeof(end_date);

		data_obj[6].dataType = DataTypeByteArray;
		data_obj[6].data = maximum_number_records;
		data_obj[6].dataLength = sizeof(maximum_number_records);

		return doExportData(ctx, ExportData, data_obj, num_data_obj, output);
	}
}

/* ------------------------------------------------------------------------- */
static se_result_t exportMoreData(se_ctx_t* ctx, 
	const uint8_t *serialNumberKey,
	uint32_t serialNumberLength,
	uint32_t previousSignatureCounter,
	int32_t maximumNumberRecords,
	se_export_output_t output)
{
	se_result_t result;

	/* check export mode parameter */
	if((result = checkExportOutput(output)) != ExecutionOk)
		return result;

	/* check serial number parameter */
	if((result = checkSerialNumberKey(ctx, &serialNumberKey, &serialNumberLength)) != ExecutionOk)
		return result;

	/* export data */
	{
		se_data_obj_array_t data_obj[3];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		uint8_t signature_counter[sizeof(uint32_t)];
		uint8_t maximum_number_records[sizeof(uint32_t)];

		se_uint32ToByteArray(signature_counter, previousSignatureCounter);
		se_uint32ToByteArray(maximum_number_records, maximumNumberRecords);

		data_obj[0].dataType = DataTypeByteArray;
		data_obj[0].data = serialNumberKey;
		data_obj[0].dataLength = serialNumberLength;

		data_obj[1].dataType = DataTypeByteArray;
		data_obj[1].data = signature_counter;
		data_obj[1].dataLength = sizeof(signature_counter);

		data_obj[2].dataType = DataTypeByteArray;
		data_obj[2].data = maximum_number_records;
		data_obj[2].dataLength = sizeof(maximum_number_records);

		return doExportData(ctx, ExportMoreData, data_obj, num_data_obj, output);
	}
}

/* ------------------------------------------------------------------------- */
static se_result_t initContext(se_ctx_t* ctx, uint32_t timeout)
{
	if(ctx == NULL)
		return ErrorMissingParameter;

	/* init TSE i/o members */
	ctx->iOHandle = HANDLEToIoHandle(INVALID_HANDLE_VALUE);
	ctx->iOTimeout = timeout != 0 ? timeout : SE_DEFAULT_IO_TIMEOUT;

	/* init buffers */
	ctx->versionLength = ctx->serialNrLength = ctx->serialNrKeyLength = 0;
	memset(ctx->version, 0, SE_VERSION_BUF_SIZE);
	memset(ctx->serialNr, 0, SE_SERIAL_BUF_SIZE);
	memset(ctx->serialNrKey, 0, SE_SERIAL_BUF_SIZE);

	ctx->cmdBufUsed = ctx->responseBufUsed = 0;
	memset(ctx->cmdBuf, 0, SE_CMD_BUF_SIZE);
	memset(ctx->responseBuf, 0, SE_RESPONSE_BUF_SIZE);

	/* other members */
	ctx->totalDataLength = 0;
	ctx->lastOSError = SE_OS_OK; /* = 0 */
	ctx->firmwareVersion = 0;
	ctx->needsTarPadding = 0;
	ctx->selfTestLog = NULL;
	ctx->selfTestLogLength = 0;

	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
static se_result_t startDevice(se_ctx_t* ctx, uint32_t maxResponse, uint8_t checkIntegrity)
{
	se_result_t result;
	se_data_obj_array_t data_obj[3];

	const uint32_t num_data_obj = maxResponse == SE_MAX_RESPONSE_4k ? 3 : 2;
	data_obj[num_data_obj-2].dataType = DataTypeByteArray;
	data_obj[num_data_obj-2].data = SE_API_EX_C_VERSION;
	data_obj[num_data_obj-2].dataLength = sizeof(SE_API_EX_C_VERSION);

	data_obj[num_data_obj-1].dataType = DataTypeByte;
	data_obj[num_data_obj-1].data = &checkIntegrity;
	data_obj[num_data_obj-1].dataLength = sizeof(checkIntegrity);

	if(maxResponse == SE_MAX_RESPONSE_4k)
	{
		uint8_t maxResponse_array[2];
		se_uint16ToByteArray(maxResponse_array, maxResponse);

		data_obj[0].dataType = DataTypeShort;
		data_obj[0].data = maxResponse_array;
		data_obj[0].dataLength = sizeof(maxResponse_array);
	}

	if ((result = sendCase4Cmd(ctx, Start, data_obj, num_data_obj)) != ExecutionOk)
		return result;
	
	{
		/* 1 response object of type String and 1 of type ByteArray expected */
		se_data_obj_array_t response_obj[5];
		uint32_t num_response_obj = sizeof(response_obj) / sizeof(se_data_obj_array_t);

		response_obj[0].dataType = DataTypeString;		/* tse_version */
		response_obj[1].dataType = DataTypeByteArray;	/* tse_serial */
		response_obj[2].dataType = DataTypeString;		/* tse_mark */
		response_obj[3].dataType = DataTypeByte;	    /* selftest result */
		response_obj[4].dataType = DataTypeByteArray;	/* selftest data */

		if((result = getResponseObjects(ctx, response_obj, &num_response_obj, 3)) != ExecutionOk)
			return result;
		{
			/* store firmware version, init V1 flag */
			uint32_t length = response_obj[0].dataLength;
			if(length > SE_VERSION_BUF_SIZE - 1)
				length = SE_VERSION_BUF_SIZE - 1;
			memcpy(ctx->version, response_obj[0].data, length);
			memset(ctx->version + length, 0, SE_VERSION_BUF_SIZE - length);
			ctx->versionLength = length;
			ctx->firmwareVersion = se_getHardwareVersionEx(ctx);

			/** once we know the hardware version, check if parameter is supported (or ignored) */
			if (maxResponse == SE_MAX_RESPONSE_4k && ctx->firmwareVersion == version1)
				return ErrorTSECommandDataInvalid;

			/* store TSE serial number */
			length = response_obj[1].dataLength;
			if(length > SE_SERIAL_BUF_SIZE)
				length = SE_SERIAL_BUF_SIZE;
			memcpy(ctx->serialNr, response_obj[1].data, length);
			memset(ctx->serialNr + length, 0, SE_SERIAL_BUF_SIZE - length);
			ctx->serialNrLength = length;

			/* version check (API 2.0 is not compatible with API v1.0 TSE firmware) */
			{
				const char	*api1_fw_version_1	= "f44a9e", 
							*api1_fw_version_2	= "aee640",
							*api1_fw_version_3	=  "52376",
							*api1_fw_version_4	= "462076",
							*api1_fw_version_5	= "056817",
							*api1_fw_version_6	= "379178",
							*api1_fw_version_7	= "430527",
							*api1_fw_version_8	= "966416",
							*api1_fw_version_9	= "021148",
							*api1_fw_version_10	= "932479";

				if(strstr(ctx->version, api1_fw_version_1)	!= NULL
				|| strstr(ctx->version, api1_fw_version_2)	!= NULL
				|| strstr(ctx->version, api1_fw_version_3)	!= NULL
				|| strstr(ctx->version, api1_fw_version_4)	!= NULL
				|| strstr(ctx->version, api1_fw_version_5)	!= NULL
				|| strstr(ctx->version, api1_fw_version_6)	!= NULL
				|| strstr(ctx->version, api1_fw_version_7)	!= NULL
				|| strstr(ctx->version, api1_fw_version_8)	!= NULL
				|| strstr(ctx->version, api1_fw_version_9)	!= NULL
				|| strstr(ctx->version, api1_fw_version_10) != NULL)
					return ErrorTSEFirmwareVersion;
			}
			/* version check (API 2.1 is not fully compatible with API v2.0 TSE firmware) */
			{
				const char *api2_fw_version = "52376";
				if(strstr(ctx->version, api2_fw_version) != NULL)
					return ErrorTSEFirmwareVersion;
			}
			/* handle export data transport encoding change */
			ctx->needsTarPadding = se_getHardwareVersionEx(ctx) < version2 ? 1 : 0;
			{
					const char *fw_version_oneRelease = "187185",
						  *fw_version_anotherRelease1 = "351252";

					if(strstr(ctx->version, fw_version_oneRelease) != NULL
					|| strstr(ctx->version, fw_version_anotherRelease1) != NULL)
						ctx->needsTarPadding = 1;
			}

			if((result = initCtxSerialNumber(ctx)) == ErrorSeApiNotInitialized || result == ErrorSeApiDeactivated)
				return ExecutionOk;
		}

		if(num_response_obj > 3 && response_obj[3].data[0] != 0)
		{
			if(num_response_obj > 4)
			{
				ctx->selfTestLog = response_obj[4].data;
				ctx->selfTestLogLength = response_obj[4].dataLength;
			}
			return ErrorSelftestFailed;
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
static void getDevicePath(const char* inputPath, char* devicePath, uint32_t devicePathLength)
{
	memset(devicePath, 0, devicePathLength);
	if(inputPath == NULL)
		return;
	{
		const size_t input_len = strlen(inputPath);
		const size_t max_len = devicePathLength - 1;

		if(input_len > max_len)
			return;

		memcpy(devicePath, inputPath, input_len);
		{
			const char* io_file = SE_MSC_IO_FILE;
			const size_t io_file_len = strlen(io_file);

			/* if provided path ends with "TSE-IO.bin": do not touch it */
			if(input_len >= io_file_len)
				if(memcmp(inputPath + input_len - io_file_len, io_file, io_file_len) == 0)
				{
#if BLOCK_DEV
					/* TSE-IO.bin is invalid in BLOCK_DEV mode */
					*devicePath = '\x00';
#endif
					return;
				}

#if BLOCK_DEV
			/* done, don't append anything */
			return;
#endif

			if(input_len + io_file_len + 2 > max_len)
				return;

			/* add "TSE-IO.bin" to provided path */
#		ifdef _WIN32
			strcat(devicePath, "\\");
#		else
			strcat(devicePath, "/");
#		endif
			strcat(devicePath, io_file);
		}
	}
}

/* ------------------------------------------------------------------------- */
static se_result_t openFileStream(FILE** stream, const char* fileName)
{
	if(fileName == NULL)
		return ErrorMissingParameter;

	if((*stream = fopen(fileName, "wb")) == NULL)
		return ErrorStreamWrite;

	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
static uint32_t SE_STDCALL dummyWriter(const uint8_t* data, uint32_t dataLength, uint64_t totalDataLength, se_handle_t handle)
{
	return 0; /* => 0 byte processed => will trigger ErrorCallback + Abort of Export */
}


/* ------------------------------------------------------------------------- */
/* se_api_ex.h functions                                                        */
/* ------------------------------------------------------------------------- */

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(const se_tse_version_t, se_getHardwareVersionEx)(se_ctx_t* ctx)
{
	SE_EXPORT_EX_METHOD;
	{
		const char *fw_version1_oneRelease = "240346",
			  *fw_version1_anotherRelease1 = "425545",
			  *fw_version1_anotherRelease2 = "793041";

		const char *fw_version2_oneRelease = "187185",
			  *fw_version2_anotherRelease1 = "892375",
			  *fw_version2_anotherRelease2 = "565701";

		return(strstr(ctx->version, fw_version1_oneRelease) != NULL
			|| strstr(ctx->version, fw_version1_anotherRelease1) != NULL
			|| strstr(ctx->version, fw_version1_anotherRelease2) != NULL) ? version1

			: (strstr(ctx->version, fw_version2_oneRelease) != NULL
			|| strstr(ctx->version, fw_version2_anotherRelease1) != NULL
			|| strstr(ctx->version, fw_version2_anotherRelease2) != NULL) ? version2

			: version2_1;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_isEngineeringSampleEx)(se_ctx_t* ctx, uint8_t* isES)
{
	SE_EXPORT_METHOD;

	if(isES == NULL)
		return ErrorMissingParameter;

#	if 1
	{
		se_result_t result;

		char* certificationId = NULL;
		uint32_t certificationIdLength;

		result = se_getCertificationIdEx(ctx, &certificationId, &certificationIdLength);
		if(result == ExecutionOk)
		{
			certificationId[certificationIdLength - 1] = '\x00';	/* cuts last character, ok... */
			*isES = strstr(certificationId, "-0000-") != NULL;
		}

		if(certificationId != NULL)
			se_free(certificationId);

		return result;
	}
#	else
	// no-IO implementation:
	{
		const char *fw_version_v1 = "425545",
			       *fw_version_v2 = "565701";

		*isES = (strstr(ctx->version, fw_version_v1) == NULL
			  && strstr(ctx->version, fw_version_v2) == NULL);

		return ExecutionOk;

	}
#	endif
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(const char*, se_getApiVersionStringEx)()
{
	SE_EXPORT_EX_METHOD;
		
	return SE_API_VERSION_STR;
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(const uint8_t*, se_getApiVersionEx)(uint32_t *versionLength)
{
	SE_EXPORT_EX_METHOD;
	{
		if(versionLength == NULL)
			return NULL;

		*versionLength = sizeof(SE_API_VERSION);
		return SE_API_VERSION;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(const char*, se_getImplementationVersionStringEx)()
{
	SE_EXPORT_EX_METHOD;

	return SE_API_EX_C_VERSION_STR;
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(const uint8_t*, se_getImplementationVersionEx)(uint32_t *versionLength)
{
	SE_EXPORT_EX_METHOD;
	{
		if(versionLength == NULL)
			return NULL;

		*versionLength = sizeof(SE_API_EX_C_VERSION);
		return SE_API_EX_C_VERSION;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(const uint8_t*, se_getUniqueIdEx)(se_ctx_t* ctx, 
	uint32_t *idLength)
{
	SE_EXPORT_EX_METHOD;
	{
		if(idLength == NULL || ctx->serialNrLength == 0)
			return NULL;

		*idLength = ctx->serialNrLength;
		return ctx->serialNr;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getTemperatureEx)(se_ctx_t* ctx,
		uint32_t *temp)
{
	SE_EXPORT_EX_METHOD;
	{
		se_result_t result;
		uint8_t id_array[2];
		se_data_obj_array_t data_obj[1];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		if(temp == NULL)
			return ErrorMissingParameter;

		/* valueId as Short */
		se_uint16ToByteArray(id_array, Temperature);

		data_obj[0].dataType = DataTypeShort;
		data_obj[0].data = id_array;
		data_obj[0].dataLength = sizeof(id_array);

		if((result = sendCase4Cmd(ctx, GetStatus, data_obj, num_data_obj)) == ExecutionOk)
		{
			/* 1 response object of type ByteArray expected */
			se_data_obj_array_t response_obj[1];
			uint32_t num_response_obj = sizeof(response_obj) / sizeof(se_data_obj_array_t);

			response_obj[0].dataType = DataTypeShort;	/* value */

			if((result = getResponseObjects(ctx, response_obj, &num_response_obj, 0)) == ExecutionOk)
				return se_byteArrayToUint32(temp, response_obj[0].data, response_obj[0].dataLength);
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getTemperature1Ex)(se_ctx_t* ctx, uint32_t vcc,
		uint32_t *temp)
{
	SE_EXPORT_EX_METHOD;
	{
		se_result_t result;
		uint8_t id_array[2];
		uint8_t vcc_array[2];
		se_data_obj_array_t data_obj[2];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		if(temp == NULL)
			return ErrorMissingParameter;
		if(vcc < 2500 || vcc > 4000)
			return ErrorParameterMismatch;

		/* valueId as Short */
		se_uint16ToByteArray(id_array, Temperature);

		data_obj[0].dataType = DataTypeShort;
		data_obj[0].data = id_array;
		data_obj[0].dataLength = sizeof(id_array);

		se_uint16ToByteArray(vcc_array, vcc);

		data_obj[1].dataType = DataTypeShort;
		data_obj[1].data = vcc_array;
		data_obj[1].dataLength = sizeof(vcc_array);

		if((result = sendCase4Cmd(ctx, GetStatus, data_obj, num_data_obj)) == ExecutionOk)
		{
			/* 1 response object of type ByteArray expected */
			se_data_obj_array_t response_obj[2];
			uint32_t num_response_obj = sizeof(response_obj) / sizeof(se_data_obj_array_t);

			response_obj[0].dataType = DataTypeShort;	/* value */
			response_obj[1].dataType = DataTypeShort;	/* value */

			if((result = getResponseObjects(ctx, response_obj, &num_response_obj, 0)) == ExecutionOk)
				return se_byteArrayToUint32(temp, response_obj[1].data, response_obj[1].dataLength);
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getCertificationIdEx)(se_ctx_t* ctx, 
	char **certificationId,
	uint32_t *certificationIdLength)
{
	SE_EXPORT_EX_METHOD;
	{
		se_data_obj_array_t data_obj[1];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		uint8_t id_array[2];
		se_uint16ToByteArray(id_array, (uint16_t) CertificationId);

		data_obj[0].dataType = DataTypeShort;
		data_obj[0].data = id_array;
		data_obj[0].dataLength = sizeof(id_array);

		/* return allocated output string */
		return getString(ctx, certificationId, certificationIdLength, GetConfigData, data_obj, num_data_obj);
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(const char*, se_getFirmwareIdEx)(se_ctx_t* ctx)
{
	SE_EXPORT_EX_METHOD;
	{
		if(ctx->versionLength == 0)
			return NULL;

		return ctx->version;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getLifeCycleStateEx)(se_ctx_t* ctx, 
	se_lcs_t *lcs)
{
	SE_EXPORT_EX_METHOD;
	{
		uint32_t number;
		se_result_t result;

		if ((result = getStatusNumber(ctx, &number, LifeCycleState)) != ExecutionOk) {
			if (result == ErrorNoStartup)
				*lcs = (se_lcs_t)lcsSleep;
			else if (result == ErrorIO)
				*lcs = (se_lcs_t)lcsClosed;
			else
				return result;
		}
		else {
			*lcs = (se_lcs_t)number;
		}
		return ExecutionOk;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_openEx)(se_ctx_t* ctx, 
	const char *configFileName)
{
	SE_EXPORT_EX_METHOD;
	{
		se_result_t result;
		char device_path_buf[256];
		uint32_t timeout = SE_DEFAULT_IO_TIMEOUT;
		uint32_t maxResponse = SE_MAX_RESPONSE_8k;
		uint8_t checkIntegrity = SE_DO_CHECK_INTEGRITY;

		if((result = initContext(ctx, timeout)) != ExecutionOk)
			return result;

		/* TODO: Parse config file, get devicePath and timeout */
		getDevicePath("", device_path_buf, sizeof(device_path_buf));

		/* Open transport channel */
		if((result = se_transportOpenEx(ctx, device_path_buf)) != ExecutionOk)
			return result;

		/* Send command Start and store version and serial */
		result = startDevice(ctx, maxResponse, checkIntegrity);
		if(result != ExecutionOk)
		{
			se_transportCloseEx(ctx);
			return result;
		}

		return ExecutionOk;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_openDirect2Ex)(se_ctx_t* ctx,
	const char *devicePath, uint32_t timeout, uint32_t maxResponse, uint8_t checkIntegrity)
{
	SE_EXPORT_EX_METHOD;
	{
		se_result_t result;
		char device_path_buf[256];
		if (!maxResponse)
			maxResponse = SE_MAX_RESPONSE_8k;
		else if (maxResponse != SE_MAX_RESPONSE_8k && maxResponse != SE_MAX_RESPONSE_4k)
			return ErrorParameterMismatch;

		if ((result = initContext(ctx, timeout)) != ExecutionOk)
			return result;

		getDevicePath(devicePath, device_path_buf, sizeof(device_path_buf));

		/* Open transport channel */
		if ((result = se_transportOpenEx(ctx, device_path_buf)) != ExecutionOk)
			return result;

		/* Send command Start and store version and serial */
		result = startDevice(ctx, maxResponse, checkIntegrity);
		if (result != ExecutionOk && result != ErrorSelftestFailed)
		{
			se_transportCloseEx(ctx);
			return result;
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_openDirect1Ex)(se_ctx_t* ctx,
	const char *devicePath, uint32_t timeout, uint32_t maxResponse)
{
	SE_EXPORT_EX_METHOD;
	{
		return se_openDirect2Ex(ctx, devicePath, timeout, maxResponse, SE_DO_CHECK_INTEGRITY);
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_openDirectEx)(se_ctx_t* ctx,
	const char *devicePath, uint32_t timeout)
{
	SE_EXPORT_EX_METHOD;
	{
		return se_openDirect2Ex(ctx, devicePath, timeout, SE_MAX_RESPONSE_8k, SE_DO_CHECK_INTEGRITY);
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_reopenEx)(se_ctx_t* ctx,
	const char *devicePath, uint32_t timeout)
{
	SE_EXPORT_EX_METHOD;
	{
		return se_reopen2Ex(ctx, devicePath, timeout, SE_MAX_RESPONSE_8k, SE_DO_CHECK_INTEGRITY);
	}
}

SE_API_EX_IMPL(se_result_t, se_reopen2Ex)(se_ctx_t* ctx,
	const char *devicePath, uint32_t timeout, uint32_t maxResponse, uint8_t checkIntegrity)
{
	SE_EXPORT_EX_METHOD;
	{
		se_result_t result;

		/* result ignored */
		se_closeEx(ctx);

		if((result = se_openDirect2Ex(ctx, devicePath, timeout, maxResponse, checkIntegrity)) != ExecutionOk)
			return result;

		return ExecutionOk;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_closeEx)(se_ctx_t* ctx)
{
	SE_EXPORT_EX_METHOD;
	{
		se_result_t result_shutdown	= sendCase1Cmd(ctx, Shutdown);
		se_result_t result_close	= se_transportCloseEx(ctx);

		return result_shutdown == ExecutionOk ? result_close : result_shutdown;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_selfTestEx)(se_ctx_t* ctx,
		uint32_t maxDuration,
		se_self_test_result_t* testresult)
{
	SE_EXPORT_EX_METHOD;
	{
		se_result_t result;
		se_data_obj_array_t data_obj[1];
		uint8_t array[4];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		if(testresult == NULL)
			return ErrorMissingParameter;

		se_uint32ToByteArray(array, maxDuration);

		data_obj[0].dataType = DataTypeByteArray;
		data_obj[0].data = array;
		data_obj[0].dataLength = sizeof(array);

		if((result = sendCase4Cmd(ctx, SelfTest, data_obj, num_data_obj)) == ExecutionOk)
		{
			/* 1 response object of type ByteArray expected */
			se_data_obj_array_t response_obj[5];
			uint32_t num_response_obj = sizeof(response_obj) / sizeof(se_data_obj_array_t);

			response_obj[0].dataType = DataTypeByte;
			response_obj[1].dataType = DataTypeByte;
			response_obj[2].dataType = DataTypeByte;
			response_obj[3].dataType = DataTypeUInt32Array;
			response_obj[4].dataType = DataTypeByteArray;

			if((result = getResponseObjects(ctx, response_obj, &num_response_obj, 0)) == ExecutionOk)
			{
				int i;
				uint32_t a = sizeof(testresult->counters)/sizeof(testresult->counters[0]);
				uint32_t b = sizeof(testresult->counters)/sizeof(testresult->counters[0]) * sizeof(uint32_t);
				testresult->completed = response_obj[0].data[0] != 0;
				testresult->errorsFound = response_obj[1].data[0] != 0;
				testresult->level = response_obj[2].data[0];
				if(a == b)
					return ErrorDescriptionNotSetByManufacturer;
				if(response_obj[3].dataLength != sizeof(testresult->counters)/sizeof(testresult->counters[0]) * sizeof(uint32_t))
					return ErrorTSEResponseDataInvalid;
				for(i = 0; i < sizeof(testresult->counters)/sizeof(testresult->counters[0]); i++)
				{
					result = se_byteArrayToUint32(&testresult->counters[i], response_obj[3].data + i*sizeof(uint32_t), sizeof(uint32_t));
					if(result != ExecutionOk)
						return result;
				}
				testresult->logLength = response_obj[4].dataLength;
				if((testresult->log = (uint8_t*) se_malloc(testresult->logLength)) == NULL)
					return ErrorAllocationfailed;
				memcpy(testresult->log, response_obj[4].data, testresult->logLength);
			}
		}
		return result;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getPinStatusEx)(se_ctx_t* ctx, 
	se_pin_state_flags_t* pinState)
{
	SE_EXPORT_EX_METHOD;

	if(pinState == NULL)
		return ErrorMissingParameter;
	{
		se_result_t result;

		if((result = sendCase2Cmd(ctx, GetPinStates)) == ExecutionOk)
		{
			/* 1 response object of type ByteArray expected */
			se_data_obj_array_t response_obj[1];
			uint32_t num_response_obj = sizeof(response_obj) / sizeof(se_data_obj_array_t);
			response_obj[0].dataType = DataTypeByteArray;	/* pinState */

			if((result = getResponseObjects(ctx, response_obj, &num_response_obj, 0)) == ExecutionOk)
			{
				result = ErrorTSEResponseDataInvalid;
				if(response_obj[0].dataLength == 4)
				{
					const uint8_t* data = response_obj[0].data;
					*pinState = stateInitialized;
					if(data[0] != 0) *pinState |= adminPinTransportState;
					if(data[1] != 0) *pinState |= adminPukTransportState;
					if(data[2] != 0) *pinState |= timeAdminPinTransportState;
					if(data[3] != 0) *pinState |= timeAdminPukTransportState;
					result = ExecutionOk;
				}
			}
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_initializePinValuesEx)(se_ctx_t* ctx, 
	const uint8_t *adminPin,
	uint32_t adminPinLength,
	const uint8_t *adminPuk,
	uint32_t adminPukLength,
	const uint8_t *timeAdminPin,
	uint32_t timeAdminPinLength,
	const uint8_t *timeAdminPuk,
	uint32_t timeAdminPukLength)
{
	SE_EXPORT_EX_METHOD;
	{
		se_result_t result;

		if((adminPuk     == NULL && adminPin     != NULL)
		|| (timeAdminPuk == NULL && timeAdminPin != NULL))
			return ErrorTSECommandDataInvalid;

		if(adminPuk != NULL)
		{
			result = se_initializePukEx(ctx, "Admin", strlen("Admin"), adminPuk, adminPukLength);
			if(result != ExecutionOk)
				return result;
			if(adminPin != NULL)
			{
				se_unblock_result_t unblockResult;
				result = se_unblockUserEx(ctx, "Admin", strlen("Admin"), adminPuk, adminPukLength, adminPin, adminPinLength, &unblockResult);
				if(result != ExecutionOk)
					return result;
			}
		}

		if(timeAdminPuk != NULL)
		{
			result = se_initializePukEx(ctx, "TimeAdmin", strlen("TimeAdmin"), timeAdminPuk, timeAdminPukLength);
			if(result != ExecutionOk)
				return result;
			if(timeAdminPin != NULL)
			{
				se_unblock_result_t unblockResult;
				result = se_unblockUserEx(ctx, "TimeAdmin", strlen("TimeAdmin"), timeAdminPuk, timeAdminPukLength, timeAdminPin, timeAdminPinLength, &unblockResult);
				if(result != ExecutionOk)
					return result;
			}
		}

		return ExecutionOk;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_initializePukEx)(se_ctx_t* ctx, const char *userId, uint32_t userIdLength, const uint8_t *puk, uint32_t pukLength)
{
	SE_EXPORT_EX_METHOD;

	if(userId == NULL || puk == NULL)
		return ErrorMissingParameter;

	if(isFirmwareV1(ctx))
	{
		se_data_obj_array_t data_obj[4];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		if(strstr(userId, "Admin") == userId){
			
			data_obj[0].dataType = DataTypeByteArray;
			data_obj[0].data = puk;
			data_obj[0].dataLength = pukLength;

			data_obj[1].dataType = DataTypeByteArray;
			data_obj[1].data = NULL;
			data_obj[1].dataLength = 0;

			data_obj[2].dataType = DataTypeByteArray;
			data_obj[2].data = NULL;
			data_obj[2].dataLength = 0;

			data_obj[3].dataType = DataTypeByteArray;
			data_obj[3].data = NULL;
			data_obj[3].dataLength = 0;

			return sendCase3Cmd(ctx, InitializePins, data_obj, num_data_obj);			
		}
		else if(strstr(userId, "TimeAdmin") == userId)
		{
			data_obj[0].dataType = DataTypeByteArray;
			data_obj[0].data = NULL;
			data_obj[0].dataLength =  0;

			data_obj[1].dataType = DataTypeByteArray;
			data_obj[1].data = NULL;
			data_obj[1].dataLength = 0;

			data_obj[2].dataType = DataTypeByteArray;
			data_obj[2].data = puk;
			data_obj[2].dataLength = pukLength;

			data_obj[3].dataType = DataTypeByteArray;
			data_obj[3].data = NULL;
			data_obj[3].dataLength = 0;

			return sendCase3Cmd(ctx, InitializePins, data_obj, num_data_obj);
		}
		else
			return ErrorTSECommandDataInvalid;
	}
	else
	{
		se_data_obj_array_t data_obj[2];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		data_obj[0].dataType = DataTypeString;
		data_obj[0].data = (uint8_t*) userId;
		data_obj[0].dataLength = userIdLength;

		data_obj[1].dataType = DataTypeByteArray;
		data_obj[1].data = puk;
		data_obj[1].dataLength = pukLength;

		return sendCase3Cmd(ctx, InitializePins, data_obj, num_data_obj);
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_initializeEx)(se_ctx_t* ctx)
{
	SE_EXPORT_EX_METHOD;

	return sendCase1Cmd(ctx, Initialize);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_initialize1Ex)(se_ctx_t* ctx, 
	const char* description)
{
	SE_EXPORT_EX_METHOD;
	{
		if(description == NULL)
			return se_initializeEx(ctx);

		return ErrorDescriptionSetByManufacturer;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_deactivateTSEEx)(se_ctx_t* ctx)
{
	SE_EXPORT_EX_METHOD;

	return sendCase1Cmd(ctx, Lock);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_activateTSEEx)(se_ctx_t* ctx)
{
	SE_EXPORT_EX_METHOD;

	return sendCase1Cmd(ctx, Unlock);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_lockTransactionLoggingEx)(se_ctx_t* ctx)
{
	SE_EXPORT_EX_METHOD;

	return sendCase1Cmd(ctx, Lock);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_unlockTransactionLoggingEx)(se_ctx_t* ctx)
{
	SE_EXPORT_EX_METHOD;

	return sendCase1Cmd(ctx, Unlock);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_mapERStoKeyEx)(se_ctx_t* ctx, 
	const char *clientId,
	uint32_t clientIdLength,
	const uint8_t *serialNumberKey,
	uint32_t serialNumberLength)
{
	SE_EXPORT_EX_METHOD;

	if(clientId == NULL)
		return ErrorMissingParameter;

	if(clientIdLength > 30)
		return ErrorTSECommandDataInvalid;

	/* No serial number means to remove the mapping.
	   Require both the pointer and the length being zero. */
	if(serialNumberKey == NULL && serialNumberLength != 0)
		return ErrorTSECommandDataInvalid;

	{
		se_data_obj_array_t data_obj[2];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		data_obj[0].dataType = DataTypeString;
		data_obj[0].data = (uint8_t*)clientId;
		data_obj[0].dataLength = clientIdLength;

		data_obj[1].dataType = DataTypeByteArray;
		data_obj[1].data = serialNumberKey;
		data_obj[1].dataLength = serialNumberLength;

		return sendCase3Cmd(ctx, RegisterClient, data_obj, num_data_obj);
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_unmapERSEx)(se_ctx_t* ctx,
	const char* clientId,
	uint32_t clientIdLength)
{
	SE_EXPORT_EX_METHOD;

	return se_mapERStoKeyEx(ctx, clientId, clientIdLength, NULL, 0);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_registerClientEx)(se_ctx_t* ctx,
	const char* clientId,
	uint32_t clientIdLength)
{
	SE_EXPORT_EX_METHOD;
	{
		uint8_t null_key[32];
		uint32_t serialNumberLength;

		const uint8_t* serialNumberKey = null_key;
		if(isFirmwareV1(ctx))
		{
			serialNumberKey = NULL;
			serialNumberLength = 0;
		}
		else
		{
			serialNumberLength = sizeof(null_key);
			memset(null_key, 0, serialNumberLength);
		}

		checkSerialNumberKey(ctx, &serialNumberKey, &serialNumberLength);
		return se_mapERStoKeyEx(ctx, clientId, clientIdLength, serialNumberKey, serialNumberLength);
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_deregisterClientEx)(se_ctx_t* ctx,
	const char* clientId,
	uint32_t clientIdLength)
{
	SE_EXPORT_EX_METHOD;

	return se_mapERStoKeyEx(ctx, clientId, clientIdLength, NULL, 0);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_updateTimeEx)(se_ctx_t* ctx, 
	int64_t unixTime)
{
	SE_EXPORT_EX_METHOD;

	if(unixTime > SE_MAX_UPDATE_TIME) /* 4102441200 = 01.01.2121 */
		return ErrorUpdateTimeFailed;
	{
		se_data_obj_array_t data_obj[1];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		uint8_t time_val[sizeof(uint64_t)];
		se_uint64ToByteArray(time_val, (uint64_t)unixTime);

		data_obj[0].dataType	= DataTypeByteArray;
		data_obj[0].data		= time_val;
		data_obj[0].dataLength	= sizeof(time_val);

		return sendCase3Cmd(ctx, UpdateTime, data_obj, num_data_obj);
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_disableSecureElementEx)(se_ctx_t* ctx)
{
	SE_EXPORT_EX_METHOD;

	return sendCase1Cmd(ctx, Disable);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_startTransactionEx)(se_ctx_t* ctx, 
	const char *clientId,
	uint32_t clientIdLength,
	const uint8_t *processData,
	uint32_t processDataLength,
	const char *processType,
	uint32_t processTypeLength,
	const uint8_t *additionalData,
	uint32_t additionalDataLength,
	se_start_transaction_result_t* transactionResult)
{
	SE_EXPORT_EX_METHOD;

	if(clientId == NULL || transactionResult == NULL)
		return ErrorMissingParameter;
	{
		se_result_t result;
		se_data_obj_array_t data_obj[4];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		data_obj[0].dataType = DataTypeString;
		data_obj[0].data = (uint8_t*) clientId;
		data_obj[0].dataLength = clientIdLength;

		data_obj[1].dataType = DataTypeByteArray;
		data_obj[1].data = processData;
		data_obj[1].dataLength = processData != NULL ? processDataLength : 0;

		data_obj[2].dataType = DataTypeString;
		data_obj[2].data = (uint8_t*) processType;
		data_obj[2].dataLength = processType != NULL ? processTypeLength : 0;

		data_obj[3].dataType = DataTypeByteArray;
		data_obj[3].data = additionalData;
		data_obj[3].dataLength = additionalData != NULL ? additionalDataLength : 0;

		if((result = sendCase4Cmd(ctx, StartTransaction, data_obj, num_data_obj)) == ExecutionOk)
		{
			/* 5 response objects of type ByteArray expected */
			se_data_obj_array_t response_obj[5];
			uint32_t num_response_obj = sizeof(response_obj) / sizeof(se_data_obj_array_t);

			response_obj[0].dataType = DataTypeByteArray;	/* transactionNumber */
			response_obj[1].dataType = DataTypeByteArray;	/* signatureCounter */
			response_obj[2].dataType = DataTypeByteArray;	/* logTime */
			response_obj[3].dataType = DataTypeByteArray;	/* signatureValue */
			response_obj[4].dataType = DataTypeByteArray;	/* serialNumber */

			if((result = getResponseObjects(ctx, response_obj, &num_response_obj, 0)) == ExecutionOk)
			{
				if((result = se_byteArrayToUint32(&(transactionResult->transactionNumber), response_obj[0].data, response_obj[0].dataLength)) != ExecutionOk)
					return result;
				if((result = se_byteArrayToUint32(&(transactionResult->signatureCounter), response_obj[1].data, response_obj[1].dataLength)) != ExecutionOk)
					return result;
				if((result = se_byteArrayToInt64(&(transactionResult->logTime), response_obj[2].data, response_obj[2].dataLength)) != ExecutionOk)
					return result;

				/* allocate and return signatureValue buffer */
				transactionResult->signatureValueLength = response_obj[3].dataLength;
				if((transactionResult->signatureValue = (uint8_t*) se_malloc(transactionResult->signatureValueLength)) == NULL)
					return ErrorAllocationfailed;
				memcpy(transactionResult->signatureValue, response_obj[3].data, transactionResult->signatureValueLength);

				/* allocate and return serialNumber buffer */
				transactionResult->serialNumberLength = response_obj[4].dataLength;
				if((transactionResult->serialNumber = (uint8_t*) se_malloc(transactionResult->serialNumberLength)) == NULL)
					return ErrorAllocationfailed;
				memcpy(transactionResult->serialNumber, response_obj[4].data, transactionResult->serialNumberLength);
			}
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_updateTransactionEx)(se_ctx_t* ctx, 
	const char *clientId,
	uint32_t clientIdLength,
	uint32_t transactionNumber,
	const uint8_t *processData,
	uint32_t processDataLength,
	const char *processType,
	uint32_t processTypeLength,
	se_update_transaction_result_t* transactionResult)
{
	SE_EXPORT_EX_METHOD;

	if(clientId == NULL || processData == NULL || transactionResult == NULL)
		return ErrorMissingParameter;
	{
		se_result_t result;
		se_data_obj_array_t data_obj[4];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		uint8_t transaction_number[sizeof(uint32_t)];
		se_uint32ToByteArray(transaction_number, transactionNumber);

		data_obj[0].dataType = DataTypeByteArray;
		data_obj[0].data = transaction_number;
		data_obj[0].dataLength = sizeof(transaction_number);

		data_obj[1].dataType = DataTypeString;
		data_obj[1].data = (uint8_t*) clientId;
		data_obj[1].dataLength = clientIdLength;

		data_obj[2].dataType = DataTypeByteArray;
		data_obj[2].data = processData;
		data_obj[2].dataLength = processDataLength;

		data_obj[3].dataType = DataTypeString;
		data_obj[3].data = (uint8_t*) processType;
		data_obj[3].dataLength = processType != NULL ? processTypeLength : 0;

		if((result = sendCase4Cmd(ctx, UpdateTransaction, data_obj, num_data_obj)) == ExecutionOk)
		{
			/* 4 response objects of type ByteArray expected */
			se_data_obj_array_t response_obj[4];
			uint32_t num_response_obj = sizeof(response_obj) / sizeof(se_data_obj_array_t);

			response_obj[0].dataType = DataTypeByteArray;	/* signatureCounter */
			response_obj[1].dataType = DataTypeByteArray;	/* logTime */
			response_obj[2].dataType = DataTypeByteArray;	/* signatureValue */
			response_obj[3].dataType = DataTypeByteArray;	/* serialNumber */

			if((result = getResponseObjects(ctx, response_obj, &num_response_obj, 0)) == ExecutionOk)
			{
				if((result = se_byteArrayToUint32(&(transactionResult->signatureCounter), response_obj[0].data, response_obj[0].dataLength)) != ExecutionOk)
					return result;
				if((result = se_byteArrayToInt64(&(transactionResult->logTime), response_obj[1].data, response_obj[1].dataLength)) != ExecutionOk)
					return result;

				/* allocate and return signatureValue buffer */
				transactionResult->signatureValueLength = response_obj[2].dataLength;
				if((transactionResult->signatureValue = (uint8_t*) se_malloc(transactionResult->signatureValueLength)) == NULL)
					return ErrorAllocationfailed;
				memcpy(transactionResult->signatureValue, response_obj[2].data, transactionResult->signatureValueLength);

				/* allocate and return serialNumber buffer */
				transactionResult->serialNumberLength = response_obj[3].dataLength;
				if((transactionResult->serialNumber = (uint8_t*) se_malloc(transactionResult->serialNumberLength)) == NULL)
					return ErrorAllocationfailed;
				memcpy(transactionResult->serialNumber, response_obj[3].data, transactionResult->serialNumberLength);
			}
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_finishTransactionEx)(se_ctx_t* ctx, 
	const char *clientId,
	uint32_t clientIdLength,
	uint32_t transactionNumber,
	const uint8_t *processData,
	uint32_t processDataLength,
	const char *processType,
	uint32_t processTypeLength,
	const uint8_t *additionalData,
	uint32_t additionalDataLength,
	se_finish_transaction_result_t* transactionResult)
{
	SE_EXPORT_EX_METHOD;

	if(clientId == NULL || processData == NULL || transactionResult == NULL)
		return ErrorMissingParameter;
	{
		se_result_t result;
		se_data_obj_array_t data_obj[5];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		uint8_t transaction_number[sizeof(uint32_t)];
		se_uint32ToByteArray(transaction_number, transactionNumber);

		data_obj[0].dataType = DataTypeByteArray;
		data_obj[0].data = transaction_number;
		data_obj[0].dataLength = sizeof(transaction_number);

		data_obj[1].dataType = DataTypeString;
		data_obj[1].data = (uint8_t*)clientId;
		data_obj[1].dataLength = clientIdLength;

		data_obj[2].dataType = DataTypeByteArray;
		data_obj[2].data = processData;
		data_obj[2].dataLength = processDataLength;

		data_obj[3].dataType = DataTypeString;
		data_obj[3].data = (uint8_t*) processType;
		data_obj[3].dataLength = processType != NULL ? processTypeLength : 0;

		data_obj[4].dataType = DataTypeByteArray;
		data_obj[4].data = additionalData;
		data_obj[4].dataLength = additionalData != NULL ? additionalDataLength : 0;

		if((result = sendCase4Cmd(ctx, FinishTransaction, data_obj, num_data_obj)) == ExecutionOk)
		{
			/* 4 response objects of type ByteArray expected */
			se_data_obj_array_t response_obj[4];
			uint32_t num_response_obj = sizeof(response_obj) / sizeof(se_data_obj_array_t);

			response_obj[0].dataType = DataTypeByteArray;	/* signatureCounter */
			response_obj[1].dataType = DataTypeByteArray;	/* logTime */
			response_obj[2].dataType = DataTypeByteArray;	/* signatureValue */
			response_obj[3].dataType = DataTypeByteArray;	/* serialNumber */

			if((result = getResponseObjects(ctx, response_obj, &num_response_obj, 0)) == ExecutionOk)
			{
				if((result = se_byteArrayToUint32(&(transactionResult->signatureCounter), response_obj[0].data, response_obj[0].dataLength)) != ExecutionOk)
					return result;
				if((result = se_byteArrayToInt64(&(transactionResult->logTime), response_obj[1].data, response_obj[1].dataLength)) != ExecutionOk)
					return result;

				/* allocate and return signatureValue buffer */
				transactionResult->signatureValueLength = response_obj[2].dataLength;
				if((transactionResult->signatureValue = (uint8_t*) se_malloc(transactionResult->signatureValueLength)) == NULL)
					return ErrorAllocationfailed;
				memcpy(transactionResult->signatureValue, response_obj[2].data, transactionResult->signatureValueLength);

				/* allocate and return serialNumber buffer */
				transactionResult->serialNumberLength = response_obj[3].dataLength;
				if((transactionResult->serialNumber = (uint8_t*) se_malloc(transactionResult->serialNumberLength)) == NULL)
					return ErrorAllocationfailed;
				memcpy(transactionResult->serialNumber, response_obj[3].data, transactionResult->serialNumberLength);
			}
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getOpenTransactionsEx)(se_ctx_t* ctx, 
	uint32_t **transactionNumbers,
	uint32_t *transactionNumbersLength)
{
	SE_EXPORT_EX_METHOD;

	if(transactionNumbers == NULL || transactionNumbersLength == NULL)
		return ErrorMissingParameter;
	{
		se_result_t result;
		se_data_obj_array_t data_obj[1];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		uint8_t id_array[2];
		se_uint16ToByteArray(id_array, (uint16_t)OpenTransactions);

		data_obj[0].dataType = DataTypeShort;
		data_obj[0].data = id_array;
		data_obj[0].dataLength = sizeof(id_array);

		if((result = sendCase4Cmd(ctx, GetStatus, data_obj, num_data_obj)) == ExecutionOk)
		{
			/* 1 response object of type UInt32Array expected */
			se_data_obj_array_t response_obj[1];
			uint32_t num_response_obj = sizeof(response_obj) / sizeof(se_data_obj_array_t);

			response_obj[0].dataType = DataTypeUInt32Array;		/* transactionNumbers */

			if((result = getResponseObjects(ctx, response_obj, &num_response_obj, 0)) == ExecutionOk)
			{
				/* allocate and return array buffer */
				uint32_t buf_len = response_obj[0].dataLength;
				if(buf_len == 0)
				{
					*transactionNumbers = NULL;
					*transactionNumbersLength = 0;
					return ExecutionOk;
				}

				if((*transactionNumbers = (uint32_t*) se_malloc(buf_len)) == NULL)
					return ErrorAllocationfailed;
				{
					uint32_t* array_ptr = *transactionNumbers;
					uint32_t i, array_len = buf_len / sizeof(uint32_t);

					*transactionNumbersLength = array_len;
					for(i = 0; i < array_len; ++i)
						se_byteArrayToUint32(array_ptr + i, response_obj[0].data + sizeof(uint32_t) * i, sizeof(uint32_t));
				}
			}
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_exportDataEx)(se_ctx_t* ctx, 
	const char *clientId,
	uint32_t clientIdLength,
	uint32_t transactionNumber,
	uint32_t startTransactionNumber,
	uint32_t endTransactionNumber,
	int64_t startDate,
	int64_t endDate,
	int32_t maximumNumberRecords,
	uint8_t **exportedData,
	uint32_t *exportedDataLength)
{
	SE_EXPORT_EX_METHOD;
	{
		se_export_output_t output;
		output.mode = toBuffer;
		output.buffer = exportedData;
		output.bufferLength = exportedDataLength;

		return exportData(ctx, clientId, clientIdLength, transactionNumber, startTransactionNumber, endTransactionNumber, startDate, endDate, maximumNumberRecords, output);
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getExportSizeEx)(se_ctx_t* ctx,
	const char *clientId,
	uint32_t clientIdLength,
	uint32_t transactionNumber,
	uint32_t startTransactionNumber,
	uint32_t endTransactionNumber,
	int64_t startDate,
	int64_t endDate,
	uint64_t *exportedDataLength)
{
	SE_EXPORT_EX_METHOD;

	if(exportedDataLength == NULL)
		return ErrorMissingParameter;

	*exportedDataLength = 0;
	{
		se_result_t result;
	
		se_export_output_t output;
		output.mode = viaCallback;
		output.writer = dummyWriter;
		output.handle = (se_handle_t)0;

		result = exportData(ctx, clientId, clientIdLength, transactionNumber, startTransactionNumber, endTransactionNumber, startDate, endDate, 0, output);
		if(result != ErrorCallback)
			return result;

		*exportedDataLength = ctx->totalDataLength;
	}
	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getExportSize1Ex)(se_ctx_t* ctx, uint32_t previousSignatureCounter, uint32_t maximumNumberRecords, uint64_t *exportedDataLength)
{
	SE_EXPORT_EX_METHOD;

	if(exportedDataLength == NULL)
		return ErrorMissingParameter;

	*exportedDataLength = 0;
	{
		se_result_t result;
		se_export_output_t output;
		const uint8_t* serialNumberKey = NULL;
		uint32_t serialNumberLength = 0;

		/* handle serial number parameter */
		if((result = checkSerialNumberKey(ctx, &serialNumberKey, &serialNumberLength)) != ExecutionOk)
			return result;

		output.mode = viaCallback;
		output.writer = dummyWriter;
		output.handle = (se_handle_t)0;

		result = exportMoreData(ctx, serialNumberKey, serialNumberLength, previousSignatureCounter, maximumNumberRecords, output);
		if(result != ErrorCallback)
			return result;

		*exportedDataLength = ctx->totalDataLength;
	}
	return ExecutionOk;
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_exportDataToStreamEx)(se_ctx_t* ctx, 
	const char *clientId,
	uint32_t clientIdLength,
	uint32_t transactionNumber,
	uint32_t startTransactionNumber,
	uint32_t endTransactionNumber,
	int64_t startDate,
	int64_t endDate,
	int32_t maximumNumberRecords,
	FILE *stream)
{
	SE_EXPORT_EX_METHOD;
	{
		se_export_output_t output;
		output.mode = toStream;
		output.stream = stream;

		return exportData(ctx, clientId, clientIdLength, transactionNumber, startTransactionNumber, endTransactionNumber, startDate, endDate, maximumNumberRecords, output);
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_exportDataToFileEx)(se_ctx_t* ctx, 
	const char *clientId,
	uint32_t clientIdLength,
	uint32_t transactionNumber,
	uint32_t startTransactionNumber,
	uint32_t endTransactionNumber,
	int64_t startDate,
	int64_t endDate,
	int32_t maximumNumberRecords,
	const char *fileName)
{
	SE_EXPORT_EX_METHOD;
	{
		FILE* stream;
		se_result_t result = openFileStream(&stream, fileName);
		if(result == ExecutionOk)
		{
			result = se_exportDataToStreamEx(ctx, clientId, clientIdLength, transactionNumber, startTransactionNumber, endTransactionNumber, startDate, endDate, maximumNumberRecords, stream);
			fclose(stream);
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_exportDataViaCallbackEx)(se_ctx_t* ctx, 
	const char *clientId,
	uint32_t clientIdLength,
	uint32_t transactionNumber,
	uint32_t startTransactionNumber,
	uint32_t endTransactionNumber,
	int64_t startDate,
	int64_t endDate,
	int32_t maximumNumberRecords,
	se_writer_t writer,
	se_handle_t handle)
{
	SE_EXPORT_EX_METHOD;
	{
		se_export_output_t output;
		output.mode = viaCallback;
		output.writer = writer;
		output.handle = handle;

		return exportData(ctx, clientId, clientIdLength, transactionNumber, startTransactionNumber, endTransactionNumber, startDate, endDate, maximumNumberRecords, output);
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_exportMoreDataEx)(se_ctx_t* ctx, 
	const uint8_t *serialNumberKey,
	uint32_t serialNumberLength,
	uint32_t previousSignatureCounter,
	int32_t maximumNumberRecords,
	uint8_t **exportedData,
	uint32_t *exportedDataLength)
{
	SE_EXPORT_EX_METHOD;
	{
		se_export_output_t output;
		output.mode = toBuffer;
		output.buffer = exportedData;
		output.bufferLength = exportedDataLength;

		return exportMoreData(ctx, serialNumberKey, serialNumberLength, previousSignatureCounter, maximumNumberRecords, output);
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_exportMoreDataToStreamEx)(se_ctx_t* ctx, 
	const uint8_t *serialNumberKey,
	uint32_t serialNumberLength,
	uint32_t previousSignatureCounter,
	int32_t maximumNumberRecords,
	FILE *stream)
{
	SE_EXPORT_EX_METHOD;
	{
		se_export_output_t output;
		output.mode = toStream;
		output.stream = stream;

		return exportMoreData(ctx, serialNumberKey, serialNumberLength, previousSignatureCounter, maximumNumberRecords, output);
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_exportMoreDataToFileEx)(se_ctx_t* ctx, 
	const uint8_t *serialNumberKey,
	uint32_t serialNumberLength,
	uint32_t previousSignatureCounter,
	int32_t maximumNumberRecords,
	const char *fileName)
{
	SE_EXPORT_EX_METHOD;
	{
		FILE* stream;
		se_result_t result = openFileStream(&stream, fileName);
		if(result == ExecutionOk)
		{
			result = se_exportMoreDataToStreamEx(ctx, serialNumberKey, serialNumberLength, previousSignatureCounter, maximumNumberRecords, stream);
			fclose(stream);
		}
		return result;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_exportMoreDataViaCallbackEx)(se_ctx_t* ctx, 
	const uint8_t *serialNumberKey,
	uint32_t serialNumberLength,
	uint32_t previousSignatureCounter,
	int32_t maximumNumberRecords,
	se_writer_t writer,
	se_handle_t handle)
{
	SE_EXPORT_EX_METHOD;
	{
		se_export_output_t output;
		output.mode = viaCallback;
		output.writer = writer;
		output.handle = handle;

		return exportMoreData(ctx, serialNumberKey, serialNumberLength, previousSignatureCounter, maximumNumberRecords, output);
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_deleteStoredDataUpToEx)(se_ctx_t* ctx,
	const uint8_t* serialNumberKey,
	uint32_t serialNumberLength,
	uint32_t signatureCounter)
{
	SE_EXPORT_EX_METHOD;
	{
		se_result_t result;
		se_data_obj_array_t data_obj[2];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		uint8_t signature_counter[sizeof(uint32_t)];
		se_uint32ToByteArray(signature_counter, signatureCounter);

		/* handle serial number parameter */
		if((result = checkSerialNumberKey(ctx, &serialNumberKey, &serialNumberLength)) != ExecutionOk)
			return result;

		data_obj[0].dataType = DataTypeByteArray;
		data_obj[0].data = serialNumberKey;
		data_obj[0].dataLength = serialNumberLength;

		data_obj[1].dataType = DataTypeByteArray;
		data_obj[1].data = signature_counter;
		data_obj[1].dataLength = sizeof(signature_counter);

		return sendCase3Cmd(ctx, DeleteUpTo, data_obj, num_data_obj);
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_exportCertificatesEx)(se_ctx_t* ctx, 
	uint8_t **certificates,
	uint32_t *certificatesLength)
{
	SE_EXPORT_EX_METHOD;
	{
		/* return allocated output array with 2*512 zero byte tar-format padding */
		uint32_t tar_padding_size = ctx->needsTarPadding ? 1024 : 0;
		return getByteArray(ctx, certificates, certificatesLength, GetCertificates, NULL, 0, tar_padding_size);
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getCertificateEx)(se_ctx_t* ctx,
	uint8_t **certificate,
	uint32_t *certificateLength)
{
	SE_EXPORT_EX_METHOD;

	/* TSEv1 would timeout waiting for key serial number */
	if(isFirmwareV1(ctx))
		return ErrorFunctionNotSupported;

	{
		se_data_obj_array_t data_obj[1];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		uint8_t id_array[2];
		se_uint16ToByteArray(id_array, (uint16_t) Certificate);

		data_obj[0].dataType = DataTypeShort;
		data_obj[0].data = id_array;
		data_obj[0].dataLength = sizeof(id_array);

		return getByteArray(ctx, certificate, certificateLength, GetKeyData, data_obj, num_data_obj, 0);
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getCertificateExpirationDateEx)(se_ctx_t* ctx, 
	const uint8_t *serialNumberKey,
	uint32_t serialNumberLength,
	int64_t *expirationDate)
{
	SE_EXPORT_EX_METHOD;

	return getKeyNumber(ctx, NULL, expirationDate, ExpirationDate, serialNumberKey, serialNumberLength);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getCertificateExpirationDate1Ex)(se_ctx_t* ctx,
	int64_t *expirationDate)
{
	SE_EXPORT_EX_METHOD;

	return getKeyNumber(ctx, NULL, expirationDate, ExpirationDate, NULL, 0);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getERSMappingsEx)(se_ctx_t* ctx, 
	uint8_t **mappingData,
	uint32_t *mappingDataLength)
{
	SE_EXPORT_EX_METHOD;
	{
		/* return allocated output array, no zero byte padding */
		se_result_t result = getByteArray(ctx, mappingData, mappingDataLength, GetERSMappings, NULL, 0, 0);
		if(*mappingDataLength == 2 + 1 + 0x7F && (*mappingData)[1] == 0x7F)
			memmove(*mappingData + 2, *mappingData + 3, ((*mappingDataLength)--)-3);
		else if(*mappingDataLength == 3 + 1 + 0xFF && (*mappingData)[2] == 0xFF)
			memmove(*mappingData + 3, *mappingData + 4, ((*mappingDataLength)--)-4);

		return result;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_listClientsEx)(se_ctx_t* ctx,
	char ***clients,
	uint32_t *clientsLength)
{
	SE_EXPORT_EX_METHOD;

	if (isFirmwareV1 (ctx))
		return ErrorFunctionNotSupported;

	{
		/* return allocated output array, no zero byte padding */
		se_result_t result = sendCase2Cmd(ctx, ListClients);

		if(result == ExecutionOk)
		{
			/* determine number of response objects */
			uint32_t pos = 0, obj_count = 0;
			const uint8_t* responseBuf = ctx->responseBuf;
			const uint32_t responseBufUsed = ctx->responseBufUsed;
			while(pos < responseBufUsed)
			{
				se_data_t data_type;
				uint32_t data_length;
				if(pos + 3 > responseBufUsed)
					return ErrorTSEResponseDataInvalid;
				{
					/* get and validate expected response object type */
					data_type = (se_data_t)responseBuf[pos];
					if(data_type != DataTypeString)
						return ErrorTSEResponseDataInvalid;
					/* get response object length */
					data_length = ((uint32_t)responseBuf[pos + 1] << 8) | responseBuf[pos + 2];
					/* validate response object length (buffer size check) */
					pos += 3;
					if(pos + data_length > responseBufUsed)
						return ErrorTSEResponseDataInvalid;
					obj_count++;
					pos += data_length;
				}
			}
			*clientsLength = obj_count;
			*clients = NULL;
			/* allocate and arrange returned objects */
			if(obj_count > 0)
			{
				uint32_t	i;
				se_data_obj_array_t* dataObjects;

				dataObjects = (se_data_obj_array_t*)se_malloc(obj_count * sizeof(se_data_obj_array_t));
				for(i = 0; i < obj_count; i++)
					dataObjects[i].dataType = DataTypeString;

				result = getResponseObjects(ctx, dataObjects, &obj_count, 0);

				*clients = (char**)se_malloc(obj_count * sizeof(char*));
				for(i = 0; i < obj_count; i++)
				{
					(*clients)[i] = (char*)se_malloc((dataObjects[i].dataLength+1)*sizeof(char));
					memcpy((*clients)[i], dataObjects[i].data, dataObjects[i].dataLength);
					(*((*clients)[i] + dataObjects[i].dataLength)) = '\0';
				}

				se_free(dataObjects);
			}
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_readLogMessageEx)(se_ctx_t* ctx, 
	uint8_t **logMessage,
	uint32_t *logMessageLength)
{
	SE_EXPORT_EX_METHOD;

	/* return allocated output array, no zero byte padding */
	return getByteArray(ctx, logMessage, logMessageLength, ReadLogMessage, NULL, 0, 0);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_exportSerialNumbersEx)(se_ctx_t* ctx,
	uint8_t **serialNumbers,
	uint32_t *serialNumbersLength)
{
	SE_EXPORT_EX_METHOD;

	/* return allocated output array, no zero byte padding */
	return getByteArray(ctx, serialNumbers, serialNumbersLength, GetSerialNumbers, NULL, 0, 0);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getMaxNumberOfClientsEx)(se_ctx_t* ctx, 
	uint32_t *maxNumberClients)
{
	SE_EXPORT_EX_METHOD;

	return getConfigNumber(ctx, maxNumberClients, MaxClients);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getCurrentNumberOfClientsEx)(se_ctx_t* ctx, 
	uint32_t *currentNumberClients)
{
	SE_EXPORT_EX_METHOD;

	return getStatusNumber(ctx, currentNumberClients, NumClients);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getMaxNumberOfTransactionsEx)(se_ctx_t* ctx, 
	uint32_t *maxNumberTransactions)
{
	SE_EXPORT_EX_METHOD;

	return getConfigNumber(ctx, maxNumberTransactions, MaxTransactions);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getCurrentNumberOfTransactionsEx)(se_ctx_t* ctx, 
	uint32_t *currentNumberTransactions)
{
	SE_EXPORT_EX_METHOD;

	return getStatusNumber(ctx, currentNumberTransactions, NumTransactions);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getTransactionCounterEx)(se_ctx_t* ctx, 
	uint32_t *transactionCounter)
{
	SE_EXPORT_EX_METHOD;

	return getStatusNumber(ctx, transactionCounter, TransactionCounter);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getMinSignatureCounterEx)(se_ctx_t* ctx,
	uint32_t *minSignatureCounter)
{
	SE_EXPORT_EX_METHOD;

	if (isFirmwareV1 (ctx))
		return ErrorFunctionNotSupported;

	return getStatusNumber(ctx, minSignatureCounter, MinCounter);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getMaxSignatureCounterEx)(se_ctx_t* ctx,
	uint32_t *maxSignatureCounter)
{
	SE_EXPORT_EX_METHOD;

	if (isFirmwareV1 (ctx))
		return ErrorFunctionNotSupported;

	return getStatusNumber(ctx, maxSignatureCounter, MaxCounter);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getNextSignatureCounterEx)(se_ctx_t* ctx,
	uint32_t *nextSignatureCounter)
{
	SE_EXPORT_EX_METHOD;

	if (isFirmwareV1 (ctx))
		return ErrorFunctionNotSupported;

	return getStatusNumber(ctx, nextSignatureCounter, NextCounter);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getTotalLogMemoryEx)(se_ctx_t* ctx, 
	uint64_t *sizeOfMemory)
{
	SE_EXPORT_EX_METHOD;

	return getLongStatusNumber(ctx, sizeOfMemory, TotalMemory);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getAvailableLogMemoryEx)(se_ctx_t* ctx, 
	uint64_t *sizeOfMemory)
{
	SE_EXPORT_EX_METHOD;

	return getLongStatusNumber(ctx, sizeOfMemory, AvailableMemory);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getSignatureCounterEx)(se_ctx_t* ctx, 
	const uint8_t *serialNumberKey,
	uint32_t serialNumberLength,
	uint32_t *signatureCounter)
{
	SE_EXPORT_EX_METHOD;

	return getKeyNumber(ctx, signatureCounter, NULL, SignatureCounter, serialNumberKey, serialNumberLength);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getSignatureCounter1Ex)(se_ctx_t* ctx,
	uint32_t *signatureCounter)
{
	SE_EXPORT_EX_METHOD;

	return getKeyNumber(ctx, signatureCounter, NULL, SignatureCounter, NULL, 0);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getSupportedTransactionUpdateVariantsEx)(se_ctx_t* ctx, 
	se_update_t *supportedUpdateVariants)
{
	SE_EXPORT_EX_METHOD;
	{
		uint32_t number;
		se_result_t result;
		if((result = getConfigNumber(ctx, &number, SupportedUpdateVariants)) != ExecutionOk)
			return result;

		*supportedUpdateVariants = (se_update_t)number;
		return ExecutionOk;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getTimeSyncVariantEx)(se_ctx_t* ctx, 
	se_sync_variants_t *supportedSyncVariant)
{
	SE_EXPORT_EX_METHOD;
	{
		uint32_t number;
		se_result_t result;
		if((result = getConfigNumber(ctx, &number, SupportedTimeFormats)) != ExecutionOk)
			return result;

		*supportedSyncVariant = (se_sync_variants_t)number;
		return ExecutionOk;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getSignatureAlgorithmEx)(se_ctx_t* ctx, 
	uint8_t **signatureAlgorithm,
	uint32_t *signatureAlgorithmLength)
{
	SE_EXPORT_EX_METHOD;
	{
		se_data_obj_array_t data_obj[1];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		uint8_t id_array[2];
		se_uint16ToByteArray(id_array, (uint16_t) SignatureAlgorithm);

		data_obj[0].dataType = DataTypeShort;
		data_obj[0].data = id_array;
		data_obj[0].dataLength = sizeof(id_array);

		/* return allocated output array, no zero byte padding */
		return getByteArray(ctx, signatureAlgorithm, signatureAlgorithmLength, GetConfigData, data_obj, num_data_obj, 0);
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getTimeSyncIntervalEx)(se_ctx_t* ctx, 
	uint32_t *timeSyncInterval)
{
	SE_EXPORT_EX_METHOD;

	return getConfigNumber(ctx, timeSyncInterval, TimeSyncInterval);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_deleteStoredDataEx)(se_ctx_t* ctx)
{
	SE_EXPORT_EX_METHOD;

	return sendCase1Cmd(ctx, Erase);
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_authenticateUserEx)(se_ctx_t* ctx, 
	const char *userId,
	uint32_t userIdLength,
	const uint8_t *pin,
	uint32_t pinLength,
	se_authentication_result_t *authenticationResult,
	int16_t *remainingRetries)
{
	SE_EXPORT_EX_METHOD;

	if(userId == NULL || pin == NULL || authenticationResult == NULL || remainingRetries == NULL)
		return ErrorMissingParameter;
	{
		se_result_t result;
		se_data_obj_array_t data_obj[2];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		data_obj[0].dataType = DataTypeString;
		data_obj[0].data = (uint8_t*)userId;
		data_obj[0].dataLength = userIdLength;

		data_obj[1].dataType = DataTypeByteArray;
		data_obj[1].data = pin;
		data_obj[1].dataLength = pinLength;

		if((result = sendCase4Cmd(ctx, AuthenticateUser, data_obj, num_data_obj)) == ExecutionOk)
		{
			/* 1 response object of type Byte and 1 of type Short expected */
			se_data_obj_array_t response_obj[2];
			uint32_t num_response_obj = sizeof(response_obj) / sizeof(se_data_obj_array_t);

			response_obj[0].dataType = DataTypeByte;	/* authenticationResult */
			response_obj[1].dataType = DataTypeShort;	/* remainingRetries */

			if((result = getResponseObjects(ctx, response_obj, &num_response_obj, 0)) == ExecutionOk)
			{
				*authenticationResult = (se_authentication_result_t)(response_obj[0].data[0]);
				if((result = se_byteArrayToInt16(remainingRetries, response_obj[1].data, response_obj[1].dataLength)) != ExecutionOk)
					return result;
			}
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_logOutEx)(se_ctx_t* ctx, 
	const char *userId,
	uint32_t userIdLength)
{
	SE_EXPORT_EX_METHOD;

	if(userId == NULL)
		return ErrorMissingParameter;
	{
		se_data_obj_array_t data_obj[1];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		data_obj[0].dataType = DataTypeString;
		data_obj[0].data = (uint8_t*)userId;
		data_obj[0].dataLength = userIdLength;

		return sendCase3Cmd(ctx, Logout, data_obj, num_data_obj);
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_unblockUserEx)(se_ctx_t* ctx, 
	const char *userId,
	uint32_t userIdLength,
	const uint8_t *puk,
	uint32_t pukLength,
	const uint8_t *newPin,
	uint32_t newPinLength,
	se_unblock_result_t *unblockResult)
{
	SE_EXPORT_EX_METHOD;

	if(userId == NULL || puk == NULL || newPin == NULL || unblockResult == NULL)
		return ErrorMissingParameter;
	{
		se_result_t result;
		se_data_obj_array_t data_obj[3];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		data_obj[0].dataType = DataTypeString;
		data_obj[0].data = (uint8_t*) userId;
		data_obj[0].dataLength = userIdLength;

		data_obj[1].dataType = DataTypeByteArray;
		data_obj[1].data = puk;
		data_obj[1].dataLength = pukLength;

		data_obj[2].dataType = DataTypeByteArray;
		data_obj[2].data = newPin;
		data_obj[2].dataLength = newPinLength;

		if((result = sendCase4Cmd(ctx, UnblockUser, data_obj, num_data_obj)) == ExecutionOk)
		{
			/* 1 response object of type Byte expected */
			se_data_obj_array_t response_obj[1];
			uint32_t num_response_obj = sizeof(response_obj) / sizeof(se_data_obj_array_t);

			response_obj[0].dataType = DataTypeByte;	/* unblockResult */

			if((result = getResponseObjects(ctx, response_obj, &num_response_obj, 0)) == ExecutionOk)
				*unblockResult = (se_unblock_result_t)(response_obj[0].data[0]);
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_getWearIndicatorEx)(se_ctx_t* ctx, 
	uint32_t* wearIndicator)
{
	SE_EXPORT_EX_METHOD;

	if(wearIndicator == NULL)
		return ErrorMissingParameter;
	{
		se_result_t result;

		if((result = sendCase2Cmd(ctx, GetWearIndicator)) == ExecutionOk)
		{
			se_data_obj_array_t response_obj[1];			/* 1 response object of type Short expected */
			uint32_t num_response_obj = sizeof(response_obj) / sizeof(se_data_obj_array_t);
			response_obj[0].dataType = DataTypeShort;		/* wearIndicator */

			if((result = getResponseObjects(ctx, response_obj, &num_response_obj, 0)) == ExecutionOk)
				result = se_byteArrayToUint32(wearIndicator, response_obj[0].data, response_obj[0].dataLength);
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_exportPublicKeyEx)(se_ctx_t* ctx, 
	const uint8_t* serialNumberKey,
	uint32_t serialNumberLength,
	uint8_t** exportedPublicKey,
	uint32_t* exportedPublicKeyLength)
{
	SE_EXPORT_EX_METHOD;

	if(exportedPublicKey == NULL || exportedPublicKeyLength == NULL)
		return ErrorMissingParameter;
	{
		se_result_t result;
		se_data_obj_array_t data_obj[2];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		/* 2 data objects: valueId (PublicKey) as Short and serialNumberKey as ByteArray */
		uint8_t id_array[2];
		se_uint16ToByteArray(id_array, PublicKey);

		/* handle serial number parameter */
		if((result = checkSerialNumberKey(ctx, &serialNumberKey, &serialNumberLength)) != ExecutionOk)
			return result;

		data_obj[0].dataType	= DataTypeShort;
		data_obj[0].data		= id_array;
		data_obj[0].dataLength	= sizeof(id_array);

		data_obj[1].dataType	= DataTypeByteArray;
		data_obj[1].data		= serialNumberKey;
		data_obj[1].dataLength	= serialNumberLength;

		/* fetch public key from TSE, returned array will be allocated with no zero byte padding */
		result = getByteArray(ctx, exportedPublicKey, exportedPublicKeyLength, GetKeyData, data_obj, num_data_obj, 0);
		if(result != ExecutionOk)
			return result;

		/* the public key may be returned from TSE at a fixed offset in a TLV object of fixed length */
		{
			const size_t PUK_SIZE			=  65; /* 256 Bit uncompressed EC public point */
			const size_t PUK_OFFSET			= 188;
			const size_t ENCODED_PUK_SIZE	= 254;

			/* if the public key is encoded, return only the public key value (incl. re-allocation of output) */
			if(*exportedPublicKeyLength == ENCODED_PUK_SIZE)
			{
				uint8_t* puk;
				if((puk = (uint8_t*) se_malloc(PUK_SIZE)) == NULL)
					return ErrorAllocationfailed;

				memcpy(puk, *exportedPublicKey + PUK_OFFSET, PUK_SIZE);
				se_free(*exportedPublicKey);

				*exportedPublicKey = puk;
				*exportedPublicKeyLength = PUK_SIZE;
			}
		}

		return result;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(se_result_t, se_updateFirmwareEx)(se_ctx_t* ctx, 
	const uint8_t* binary, 
	uint32_t binaryLength)
{
	SE_EXPORT_EX_METHOD;

	if(binary == NULL)
		return ErrorMissingParameter;
	{
		se_result_t result;
		se_data_obj_array_t data_obj[2];
		const uint32_t num_data_obj = sizeof(data_obj) / sizeof(se_data_obj_array_t);

		const uint8_t* part = 0;
		uint32_t offset = 0, part_len;
		uint8_t offset_array[sizeof(uint32_t)];

		/* send firmware binary in 4k blocks with offset value */
		data_obj[0].dataType = DataTypeByteArray;	/* offset object */
		data_obj[1].dataType = DataTypeByteArray;	/* data object */

		while(offset < binaryLength) 
		{
			part = binary + offset;
			part_len = SE_MIN(binaryLength - offset, 4096);
			se_uint32ToByteArray(offset_array, offset);

			data_obj[0].data = offset_array;
			data_obj[0].dataLength = sizeof(uint32_t);

			data_obj[1].data = part;
			data_obj[1].dataLength = part_len;

			if((result = sendCase4Cmd(ctx, FirmwareUpdate, data_obj, num_data_obj)) != ExecutionOk)
				return result;

			offset += part_len;
		}

		/* final command with empty block and offset object (timeout min 5 sec required) */
		{
			const uint32_t min_timeout = 5000, current_timeout = ctx->iOTimeout;
			if(current_timeout < min_timeout)
				ctx->iOTimeout = min_timeout;	/* modify timeout for final command */

			data_obj[0].data = NULL;
			data_obj[0].dataLength = 0;

			data_obj[1].data = NULL;
			data_obj[1].dataLength = 0;

			result = sendCase4Cmd(ctx, FirmwareUpdate, data_obj, num_data_obj);
			ctx->iOTimeout = current_timeout;	/* reset timeout */

			if(result == ExecutionOk) 
			{			
				/* 1 response object of type Short expected */
				se_data_obj_array_t response_obj[1];
				uint32_t num_response_obj = sizeof(response_obj) / sizeof(se_data_obj_array_t);

				response_obj[0].dataType = DataTypeShort;	/* short */

				if((result = getResponseObjects(ctx, response_obj, &num_response_obj, 0)) == ExecutionOk)
				{
					int16_t shrt = 0;
					if((result = se_byteArrayToInt16(&shrt, response_obj[0].data, response_obj[0].dataLength)) != ExecutionOk)
						return result;

					if(shrt > 0) {
						if(shrt < 0x100)
							shrt |= ErrorClassFirmwareUpdate;
						else if(shrt > 0x2000 && shrt < 0x2100)
							shrt = ErrorClassFirmwareUpdate | 0x200 | (shrt & 0xFF);
						else
							shrt = ErrorClassFirmwareUpdate | 0x200;

						return (se_result_t)shrt;
					}
				}
			}
		}

		/* in case of success, wait for new firmware to be properly booted */
		if(result == ExecutionOk)
			se_sleep(500);

		return result;
	}
}

/* ------------------------------------------------------------------------- */
SE_API_EX_IMPL(uint32_t, se_getOsStatusOfErrorIOEx)(se_ctx_t* ctx)
{
	SE_EXPORT_EX_METHOD;
	{
		uint32_t error_code = ctx->lastOSError;
		ctx->lastOSError = SE_OS_OK; /* reset context error code */
		return error_code;
	}
}
