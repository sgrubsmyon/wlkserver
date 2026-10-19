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
  * @file se_api_test.c
  *
  * @brief Minimal demo of the cryptovision SE-API for "C".
  */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <se_api.h>
#include <se_memory_util.h>
#include <se_transport_util.h>


/**
* External functions.
*/

extern se_result_t se_parseCertificate(const uint8_t *serialNumberKey,
	uint32_t serialNumberLength,
	const uint8_t *certificatesTarArchive,
	uint32_t certificatesTarArchiveLength,
	uint8_t **certificate,
	uint32_t *certificateLength);


/**
* Test configuration.
*/

#ifndef TEST_TOOL
#define TEST_TOOL						0
#endif
#if		TEST_TOOL
#ifndef USE_MEMORY_CALLBACKS
#define USE_MEMORY_CALLBACKS			0
#endif
#define CHECK_INTEGRITY					SE_NO_INTEGRITY_CHECK
#else
#define CHECK_INTEGRITY					SE_DO_CHECK_INTEGRITY
#endif

#ifndef EXPORT_TOOL
#define EXPORT_TOOL						0
#else
#ifndef DO_DELETE
#define DO_DELETE						0
#endif
#endif
#if		EXPORT_TOOL || TEST_TOOL
uint32_t m_signature_counter;
#endif

#define EXPORT_ALL_LOGS_TEST			1
#define EXPORT_FILTERED_LOGS_TEST		1

#ifndef USE_MEMORY_CALLBACKS
#define USE_MEMORY_CALLBACKS			1
#endif

#define DELETE_LOGS_UP_TO_TEST			0
#define DISABLE_TSE_TEST				0


/**
* Useful macros for function parameters.
*/

#define PARAM_BA(ba) ba, (uint32_t) sizeof(ba)
#define PARAM_STR(str) #str, (uint32_t) strlen(#str)
#define PARAM_STR2BA(str) (const uint8_t*)(#str), (uint32_t) strlen(#str)
#define PARAM_BUFFER(buf) &(buf), &(buf##Length)


/**
* Used PIN/PUK values.
*/

uint8_t m_adminPin[]     = { 0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08 };
uint8_t m_adminPuk[]     = { 0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0a };
uint8_t m_timeAdminPin[] = { 0x32,0x32,0x32,0x32,0x32,0x32,0x32,0x32 };				/* = "22222222" */
uint8_t m_timeAdminPuk[] = { 0x73,0x6f,0x6d,0x65,0x74,0x68,0x69,0x6e,0x67,0x21 };	/* = "something!" */


/**
* Return parameters of the SE-API that contain allocated buffers to be freed.
*/

char* m_certificationId;
uint32_t m_certificationIdLength;

uint8_t* m_serialNumbers;
uint32_t m_serialNumbersLength;

uint8_t* m_publicKey;
uint32_t m_publicKeyLength;

uint8_t* m_lastLogMessage;
uint32_t m_lastLogMessageLength;

uint8_t* m_logMessages;
uint32_t m_logMessagesLength;

uint8_t* m_certificates;
uint32_t m_certificatesLength;

uint8_t* m_ersMapping;
uint32_t m_ersMappingLength;

uint8_t* m_signatureAlgorithm;
uint32_t m_signatureAlgorithmLength;

uint32_t* m_openTransactions;
uint32_t m_openTransactionsLength;

uint64_t m_totalExportSize;

se_start_transaction_result_t m_startTransactionResult;
se_update_transaction_result_t m_updateTransactionResult;
se_finish_transaction_result_t m_finishTransactionResult;

/**
* Callback related variables.
*/

FILE* m_callbackStream = NULL;
int m_abort = 0, m_mallocCount = 0, m_freeCount = 0, m_writerCount = 0;


/**
* Optional memory management functions.
* @see se_malloc and se_free definition in se_memory_util.h
*/

/* ------------------------------------------------------------------------- */
void* SE_STDCALL myMalloc(size_t size)
{
	void* memBlock = malloc(size);
	if(memBlock != NULL)
	{
		uint64_t address = (uint64_t) memBlock;
		printf("[myMalloc: allocated 0x%04X byte at address 0x%08X%08X]\n",
			(uint32_t) size, (uint32_t)(address >> 32), (uint32_t)(address & SE_MAX_UINT32));
	}
	else
		printf("[myMalloc: failed to allocate 0x%04X byte]\n", (uint32_t) size);

	++m_mallocCount;
	return memBlock;
}

/* ------------------------------------------------------------------------- */
void SE_STDCALL myFree(void* memBlock)
{
	{
		uint64_t address = (uint64_t) memBlock;
		printf("[myFree: called at address 0x%08X%08X]\n",
			(uint32_t)(address >> 32), (uint32_t)(address & SE_MAX_UINT32));
	}
	++m_freeCount;
	free(memBlock);
}

/**
* Helper function.
*/

/* ------------------------------------------------------------------------- */
int64_t getTimestamp()
{
	return (int64_t)(time(NULL));
}

/** --------------------------------------------------------------------------- 
* Optional data export callback function.
*  @see se_writer_t definition in se_callback_t.h
*
* For simplicity, this sample callback implements an export data redirection
* into a file stream which maybe done by calling an ExportToStream function
* of the SE-API.
* An intended use case is for example to push the exported data block to a
* network connection if the memory of the TSE host system is limited.
*/
uint32_t SE_STDCALL myStreamWriter(const uint8_t* data, uint32_t dataLength, uint64_t totalDataLength, se_handle_t handle)
{
	uint32_t data_written = 0;
	{
		static uint64_t total_len;
		uint64_t address = (uint64_t) data;
		uint64_t handle_value = (uint64_t) handle;

		/* store/check the total data length of the current export process */
		if(m_writerCount == 0)
		{
			total_len = totalDataLength;
#			if(EXPORT_TOOL == 0 && TEST_TOOL == 0)
			{
				printf("[myWriter(handle 0x%08X%08X): Total export length = 0x%08X%08X byte]\n",
					(uint32_t)(handle_value >> 32), (uint32_t)(handle_value & SE_MAX_UINT32),
					(uint32_t)(totalDataLength >> 32), (uint32_t)(totalDataLength & SE_MAX_UINT32));
			}
#			endif
		}
		else if(total_len != totalDataLength)
		{
			printf("[myWriter(handle 0x%08X%08X): Inconsistent total export length = 0x%08X%08X byte]\n",
				(uint32_t)(handle_value >> 32), (uint32_t)(handle_value & SE_MAX_UINT32),
				(uint32_t)(totalDataLength >> 32), (uint32_t)(totalDataLength & SE_MAX_UINT32));
		}

		/* write data to callback file stream if present */
		if(m_callbackStream != NULL)
		{
			data_written = (uint32_t) fwrite(data, sizeof(uint8_t), dataLength, m_callbackStream);
#			if(EXPORT_TOOL == 0 && TEST_TOOL == 0)
			{
				printf("[myWriter(handle 0x%08X%08X): 0x%04X of 0x%04X byte data processed from address 0x%08X%08X]\n",
					(uint32_t)(handle_value >> 32), (uint32_t)(handle_value & SE_MAX_UINT32), data_written, dataLength,
					(uint32_t)(address >> 32), (uint32_t)(address & SE_MAX_UINT32));
			}
#			endif
		}
		else
			printf("[myWriter(handle 0x%08X%08X): Failed to process 0x%04X byte from address 0x%08X%08X]\n", 
				(uint32_t)(handle_value >> 32), (uint32_t)(handle_value & SE_MAX_UINT32), dataLength,
				(uint32_t)(address >> 32), (uint32_t)(address & SE_MAX_UINT32));

#		if(EXPORT_TOOL == 1 || TEST_TOOL == 1)
		{
			static int64_t last;
			static uint64_t written;
			if(m_writerCount == 0)
			{
				last = getTimestamp();
				written = 0;
			}
			written += dataLength;
			if(getTimestamp() - last > 10 || written == total_len)
			{
				printf("%.2f%%\n", (float) 100*written/total_len);
				last = getTimestamp();
			}
		}
#		endif
	}

	/* return 0 for the abort export test (if the returned length of the data processed is not equal 
	   to the input data length, the calling exportViaCallback function will stop with ErrorCallback) */
	if(++m_writerCount == m_abort)
		return 0;

	return data_written;
}


/**
* Buffer init/free functions.
*/

/* ------------------------------------------------------------------------- */
void initOutputBuffers()
{
	m_certificationId = NULL;
	m_serialNumbers = NULL;
	m_publicKey = NULL;
	m_lastLogMessage = NULL;
	m_logMessages = NULL;
	m_certificates = NULL;
	m_ersMapping = NULL;
	m_signatureAlgorithm = NULL;
	m_openTransactions = NULL;

	m_startTransactionResult.serialNumber = NULL;
	m_startTransactionResult.signatureValue = NULL;

	m_updateTransactionResult.serialNumber = NULL;
	m_updateTransactionResult.signatureValue = NULL;

	m_finishTransactionResult.serialNumber = NULL;
	m_finishTransactionResult.signatureValue = NULL;
}

/* ------------------------------------------------------------------------- */
void freeOutputBuffers()
{
	if(m_certificationId)
		se_free(m_certificationId);
	if(m_serialNumbers)
		se_free(m_serialNumbers);
	if(m_publicKey)
		se_free(m_publicKey);
	if(m_lastLogMessage)
		se_free(m_lastLogMessage);
	if(m_logMessages)
		se_free(m_logMessages);
	if(m_certificates)
		se_free(m_certificates);
	if(m_ersMapping)
		se_free(m_ersMapping);
	if(m_signatureAlgorithm)
		se_free(m_signatureAlgorithm);
	if(m_openTransactions)
		se_free(m_openTransactions);
	
	if(m_startTransactionResult.serialNumber)
		se_free(m_startTransactionResult.serialNumber);
	if(m_startTransactionResult.signatureValue)
		se_free(m_startTransactionResult.signatureValue);

	if(m_updateTransactionResult.serialNumber)
		se_free(m_updateTransactionResult.serialNumber);
	if(m_updateTransactionResult.signatureValue)
		se_free(m_updateTransactionResult.signatureValue);

	if(m_finishTransactionResult.serialNumber)
		se_free(m_finishTransactionResult.serialNumber);
	if(m_finishTransactionResult.signatureValue)
		se_free(m_finishTransactionResult.signatureValue);
}


/**
* Helper functions.
*/

/* ------------------------------------------------------------------------- */
const char* errorToString(se_result_t error_code)
{
	switch(error_code)
	{
	case ErrorMissingParameter:						return "ErrorMissingParameter";
	case ErrorFunctionNotSupported:					return "ErrorFunctionNotSupported";
	case ErrorAllocationfailed:						return "ErrorAllocationfailed";
	case ErrorFileNotFound:							return "ErrorFileNotFound";
	case ErrorSECommunicationFailed:				return "ErrorSECommunicationFailed";
	case ErrorTSECommandDataInvalid:				return "ErrorTSECommandDataInvalid";
	case ErrorTSEResponseDataInvalid:				return "ErrorTSEResponseDataInvalid";
	case ErrorTSEUnknownError:						return "ErrorTSEUnknownError";
	case ErrorStreamWrite:							return "ErrorStreamWrite";
	case ErrorIO:									return "ErrorIO";
	case ErrorTSETimeout:							return "ErrorTSETimeout";
	case ErrorBufferTooSmall:						return "ErrorBufferTooSmall";
	case ErrorCallback:								return "ErrorCallback";
	case ErrorTSEFirmwareVersion:					return "ErrorTSEFirmwareVersion";
	case ErrorTransport:							return "ErrorTransport";
	case ErrorNoStartup:							return "ErrorNoStartup";
	case ErrorNoStorage:							return "ErrorNoStorage";
	case ErrorResponseHeader:						return "ErrorResponseHeader";
	case ErrorStaleIO:								return "ErrorStaleIO";
	case ErrorResponseTooBig:						return "ErrorResponseTooBig";
	case ErrorAuthenticationFailed:					return "ErrorAuthenticationFailed";
	case ErrorUnblockFailed:						return "ErrorUnblockFailed";
	case ErrorRetrieveLogMessageFailed:				return "ErrorRetrieveLogMessageFailed";
	case ErrorStorageFailure:						return "ErrorStorageFailure";
	case ErrorUpdateTimeFailed:						return "ErrorUpdateTimeFailed";
	case ErrorParameterMismatch:					return "ErrorParameterMismatch";
	case ErrorIdNotFound:							return "ErrorIdNotFound";
	case ErrorNoSuchKey:							return "ErrorNoSuchKey";
	case ErrorERSalreadyMapped:						return "ErrorERSalreadyMapped";
	case ErrorNoERS:								return "ErrorNoERS";
	case ErrorNoKey:								return "ErrorNoKey";
	case ErrorTransactionNumberNotFound:			return "ErrorTransactionNumberNotFound";
	case ErrorNoDataAvailable:						return "ErrorNoDataAvailable";
	case ErrorTooManyRecords:						return "ErrorTooManyRecords";
	case ErrorStartTransactionFailed:				return "ErrorStartTransactionFailed";
	case ErrorUpdateTransactionFailed:				return "ErrorUpdateTransactionFailed";
	case ErrorFinishTransactionFailed:				return "ErrorFinishTransactionFailed";
	case ErrorRestoreFailed:						return "ErrorRestoreFailed";
	case ErrorStoringInitDataFailed:				return "ErrorStoringInitDataFailed";
	case ErrorExportCertFailed:						return "ErrorExportCertFailed";
	case ErrorNoLogMessage:							return "ErrorNoLogMessage";
	case ErrorReadingLogMessage:					return "ErrorReadingLogMessage";
	case ErrorNoTransaction:						return "ErrorNoTransaction";
	case ErrorSeApiNotInitialized:					return "ErrorSeApiNotInitialized";
	case ErrorSeApiDeactivated:						return "ErrorSeApiDeactivated";
	case ErrorSeApiNotDeactivated:					return "ErrorSeApiNotDeactivated";
	case ErrorTimeNotSet:							return "ErrorTimeNotSet";
	case ErrorCertificateExpired:					return "ErrorCertificateExpired";
	case ErrorSecureElementDisabled:				return "ErrorSecureElementDisabled";
	case ErrorUserNotAuthorized:					return "ErrorUserNotAuthorized";
	case ErrorUserNotAuthenticated:					return "ErrorUserNotAuthenticated";
	case ErrorDescriptionNotSetByManufacturer:		return "ErrorDescriptionNotSetByManufacturer";
	case ErrorDescriptionSetByManufacturer:			return "ErrorDescriptionSetByManufacturer";
	case ErrorExportSerialNumbersFailed:			return "ErrorExportSerialNumbersFailed";
	case ErrorGetMaxNumberOfClientsFailed:			return "ErrorGetMaxNumberOfClientsFailed";
	case ErrorGetCurrentNumberOfClientsFailed:		return "ErrorGetCurrentNumberOfClientsFailed";
	case ErrorGetMaxNumberTransactionsFailed:		return "ErrorGetMaxNumberTransactionsFailed";
	case ErrorGetCurrentNumberOfTransactionsFailed: return "ErrorGetCurrentNumberOfTransactionsFailed";
	case ErrorGetSupportedUpdateVariantsFailed:		return "ErrorGetSupportedUpdateVariantsFailed";
	case ErrorDeleteStoredDataFailed:				return "ErrorDeleteStoredDataFailed";
	case ErrorUnexportedStoredData:					return "ErrorUnexportedStoredData";
	case ErrorSigningSystemOperationDataFailed:		return "ErrorSigningSystemOperationDataFailed";
	case ErrorUserIdNotManaged:						return "ErrorUserIdNotManaged";
	case ErrorUserIdNotAuthenticated:				return "ErrorUserIdNotAuthenticated";
	case ErrorDisableSecureElementFailed:			return "ErrorDisableSecureElementFailed";
	case ErrorSelftestFailed:						return "ErrorSelftestFailed";
	default:										return "unknown";
	}
}

/* ------------------------------------------------------------------------- */
int printError(se_result_t result, const char* function, const char* detail)
{
	if(function == 0)
		return -1;
	{
		const char* error = errorToString(result);
		printf(" => ERROR: %s result: 0x%08X = %s, detail: %s\n",
			function, result, error, (detail != 0 ? detail : ""));
	}
	return 1;
}


/**
* Test functions.
*/

/* ------------------------------------------------------------------------- */
int getApiVersion()
{
	const uint8_t *api_version, *impl_version;
	uint32_t apiVersionLength, implVersionLength;

	api_version = se_getApiVersion(&apiVersionLength);
	if(apiVersionLength != 2) return 1;

	impl_version = se_getImplementationVersion(&implVersionLength);
	if(implVersionLength != 3) return 1;

	printf("=> SE-API version string: '%s', version array: [%i.%i]\n",
		se_getApiVersionString(), api_version[0], api_version[1]);
	printf("=> SE-API-C implementation version string: '%s', version array: [%i.%i.%i]\n",
		se_getImplementationVersionString(), impl_version[0], impl_version[1], impl_version[2]);

	return 0;
}

/* ------------------------------------------------------------------------- */
int getTseIdentifier(uint8_t* is_ES)
{
	se_result_t result;

	uint32_t tse_id_len = 0;
	const uint8_t *tse_id = NULL;
	const char *firmware = NULL;

	/** Get TSE unique identifier */
	tse_id = se_getUniqueId(&tse_id_len);
	if(tse_id == NULL) return 1;

	/** Get TSE firmware identifier */
	firmware = se_getFirmwareId();
	if(firmware == NULL) return 1;

	/** Get TSE certification identifier */
	if((result = se_getCertificationId(PARAM_BUFFER(m_certificationId))) != ExecutionOk)
		return printError(result, "se_getCertificationId", 0);
	{
		uint32_t i;
		char buf[32];

		se_tse_version_t version = se_getHardwareVersion();
		const char* versionString = version == version1 ? "v1"
				:					version == version2 ? "v2"
						:			version == version2_1 ? "v2.1"
								:   "unknown";
		printf("=> TSE hardware version: %s\n", versionString);

		printf("=> TSE unique identifier: ");
		for(i = 0; i < tse_id_len; ++i)
			printf("%02X", (int)(tse_id[i])); /* byte2hex */

		if(firmware)
			printf("\n=> TSE firmware identifier: %s\n", firmware);

		memset(buf, 0, sizeof(buf));
		if(m_certificationIdLength < sizeof(buf))
			memcpy(buf, m_certificationId, m_certificationIdLength);

		if(m_certificationIdLength)
			printf("=> TSE certification identifier: %s\n", buf);

		printf("\n");
	}

	/** engineering sample check (avoid running of this test for productive samples)*/
	result = se_isEngineeringSample(is_ES);
	if(result != ExecutionOk)
		return printError(result, "se_isEngineeringSample", 0);


	if(*is_ES)
	{
		printf("=> Running on Engineering-Sample\n\n");
	}
	else
	{
		printf("=> Running on productive TSE\n\n");
	}

	return 0;
}

/* ------------------------------------------------------------------------- */
int firstBootTest()
{
	se_result_t result;

	se_pin_state_flags_t pin_state;
	se_authentication_result_t authResult;

	int16_t tries_remaining;
	uint32_t max_clients, max_transactions;

	printf("=> firstBootTest: START\n");

	/** Get PIN states in order to check if this is a new TSE
	*  This MUST be done to ensure your TSE's key has not been used before! */
	if((result = se_getPinStatus(&pin_state)) != ExecutionOk)
		return printError(result, "se_getPinStatus", 0);

	if(pin_state == stateInitialized)
	{
		int i;

		/** Get the serial number of the available key */
		if((result = se_exportSerialNumbers(PARAM_BUFFER(m_serialNumbers))) != ExecutionOk)
			return printError(result, "se_exportSerialNumbers", 0);

		/** NOTE: No proper BER or DER decoding in this test program; assumption:
		the serial number is a 32-byte-hashvalue encoded as OCTETSTRING at offset 4. */
		if(m_serialNumbersLength < 38 || m_serialNumbers[4] != 0x04 || m_serialNumbers[5] != 0x20)
			return printError(m_serialNumbersLength, "SerialNumbers encoding", "unexpected");

		printf(" => PINs already initialized, TSE is in use.\n");
		printf(" => TSE serial number: ");
		for(i = 0; i < 32; ++i) printf("%02X", (int)(m_serialNumbers[i+6])); /* byte2hex */
		printf("\n=> firstBootTest: SKIPPED\n");
		return 0;
	}

	/** PUK values cannot be changed once initialized */
	result = se_initializePuk(PARAM_STR(Admin), PARAM_BA(m_adminPuk));
	if(result != ExecutionOk)
		return printError(result, "se_initializePuk", "Admin");

	{
		se_unblock_result_t unblockResult;
		result = se_unblockUser(PARAM_STR(Admin), PARAM_BA(m_adminPuk), PARAM_BA(m_adminPin), &unblockResult);
		if(result != ExecutionOk)
			return printError(result, "se_unblockUser", "Admin");

		/** PUK values cannot be changed once initialized */
		result = se_initializePuk(PARAM_STR(TimeAdmin), PARAM_BA(m_timeAdminPuk));
		if(result != ExecutionOk)
			return printError(result, "se_initializePuk", "TimeAdmin");

		result = se_unblockUser(PARAM_STR(TimeAdmin), PARAM_BA(m_timeAdminPuk), PARAM_BA(m_timeAdminPin), &unblockResult);
		if(result != ExecutionOk)
			return printError(result, "se_unblockUser", "TimeAdmin");
	}

	/** Authenticate the Admin role with the newly set Admin PIN in order to get the rights to initialize the TSE */
	/** Timeouts apply: Admin is automatically logged out after 10 minutes. */
	if((result = se_authenticateUser(PARAM_STR(Admin), PARAM_BA(m_adminPin), &authResult, &tries_remaining)) != ExecutionOk)
		return printError(result, "se_authenticateUser", 0);

	if(authResult != authenticationOk)
	{
		printError((int) authResult, "Admin authentication", "authentication failed");
		printf(" => Tries remaining = %i\n", tries_remaining);
		return 1;
	}

	/** Initialize the TSE for operational use (signing of transaction data) */
	if((result = se_initialize()) != ExecutionOk)
		return printError(result, "se_initialize", 0);

	/** Authenticate TimeAdmin and set the system time. This MUST be done on every power-up */
	/** Timeouts apply: TimeAdmin is automatically logged out after 2 seconds. */
	if((result = se_authenticateUser(PARAM_STR(TimeAdmin), PARAM_BA(m_timeAdminPin), &authResult, &tries_remaining)) != ExecutionOk)
		return printError(result, "se_authenticateUser", 0);

	if(authResult != authenticationOk)
	{
		printError((int) authResult, "TimeAdmin authentication", "authentication failed");
		printf(" => Tries remaining = %i\n", tries_remaining);
		return 1;
	}

	if((result = se_updateTime(getTimestamp())) != ExecutionOk)
		return printError(result, "se_updateTime", 0);

	if((result = se_logOut(PARAM_STR(TimeAdmin))) != ExecutionOk)
		return printError(result, "se_logOut", "TimeAdmin logout failed");

	/** Get the maximum number of possible ERS (cash registers) that are usable */
	if((result = se_getMaxNumberOfClients(&max_clients)) != ExecutionOk)
		return printError(result, "se_getMaxNumberOfClients", 0);

	/** default 128 */
	if(128 != max_clients)
		return printError(max_clients, "MaxNumberOfClients", "128 expected");

	/** Get the maximum number of possible open transactions */
	if((result = se_getMaxNumberOfTransactions(&max_transactions)) != ExecutionOk)
		return printError(result, "se_getMaxNumberOfTransactions", 0);

	/** Get the serial numbers of the available keys */
	if((result = se_exportSerialNumbers(PARAM_BUFFER(m_serialNumbers))) != ExecutionOk)
		return printError(result, "se_exportSerialNumbers", 0);

	/** NOTE: No proper BER or DER decoding in this test programm; assumption: 
	the serial number is a 32-byte-hashvalue encoded as OCTETSTRING at offset 4. */
	if(m_serialNumbersLength < 38 || m_serialNumbers[4] != 0x04 || m_serialNumbers[5] != 0x20)
		return printError(m_serialNumbersLength, "SerialNumbers encoding", "unexpected");

	/** Configure the TSE to use the ERS "clientID" */
	if((result = se_registerClient(PARAM_STR(clientId))) != ExecutionOk)
		return printError(result, "se_registerClient", 0);

	if((result = se_lockTransactionLogging()) != ExecutionOk)
		return printError(result, "se_lockTransactionLogging", 0);

	if((result = se_unlockTransactionLogging()) != ExecutionOk)
		return printError(result, "se_unlockTransactionLogging", 0);

	if((result = se_logOut(PARAM_STR(Admin))) != ExecutionOk)
		return printError(result, "se_logOut", "Admin logout failed");

	printf("=> firstBootTest: STOP\n");

	return 0;
}

void testReport(int64_t	start_time, se_self_test_result_t* selfTestResult, uint32_t* cntr)
{
	int64_t	total_time;
	int32_t	millis;
	int i;

	total_time = se_currentTimeMillis() - start_time;
	millis = (int32_t)total_time;

	printf("\n  => Selftest completed  =  %s\n", (selfTestResult->completed ? "YES" : "NO"));
	printf("  => Selftest has errors =  %s\n", (selfTestResult->errorsFound ? "YES" : "NO"));
	printf("  => Selftest runtime    =  %i ms\n", (millis == total_time ? millis : 0));
	if(selfTestResult->errorsFound)
	{
		printf("  => Selftest counters   =  [ %d, %d, %d, %d ]\n", cntr[0], cntr[1], cntr[2], cntr[3]);
		printf("  => Selftest log        =  ");
		for (i = 0; i < selfTestResult->logLength; i++)
			printf("%02X", selfTestResult->log[i]);
		printf("\n");
	}
}

int selfTest(void)
{
	se_result_t result;
	printf(" => Running TSE selftest ...\n    ");
	{
		int i;
		int64_t	start_time;

		se_self_test_result_t selfTestResult;
		selfTestResult.log = NULL;
		uint32_t* cntr = selfTestResult.counters;
		uint8_t reportedProblems = 0;

		/** run self test for at most 10 seconds: */
		start_time = se_currentTimeMillis();
		for(i = 1; i <= 10 || TEST_TOOL; i++)
		{
			if(selfTestResult.log)
				se_free(selfTestResult.log);
			selfTestResult.log = NULL;

			/** run self test for at most 1 second */
			result = se_selfTest(1, &selfTestResult);

			if(result != ExecutionOk)
				return printError(result, "se_selfTest", 0);
			if(selfTestResult.completed != 0)
				break;
			if(selfTestResult.errorsFound != 0 && reportedProblems != cntr[0] + cntr[1] + cntr[2] + cntr[3])
			{
				printf("\n  => Problems known to be present after %i. call\n", i);
				reportedProblems = cntr[0] + cntr[1] + cntr[2] + cntr[3];
				testReport(start_time, &selfTestResult, cntr);
			}
			else
			{
				printf(".");
				fflush(stdout);
			}
		}
		testReport(start_time, &selfTestResult, cntr);
		if(selfTestResult.log)
			se_free(selfTestResult.log);
	}
	return 0;
}
/* ------------------------------------------------------------------------- */
int operationalTest()
{
	int rv;
	se_result_t result;

	se_lcs_t lcs;
	se_update_t variants;

	uint32_t time_sync_interval;
	se_sync_variants_t time_sync_variant;
	int64_t start_time, expiration_date;

	int16_t tries_remaining;
	se_unblock_result_t unblockResult;
	se_authentication_result_t authResult;

	uint32_t transactions;
	uint32_t max_clients, max_transactions, wearIndicator;
	uint32_t minSignatureCounter, maxSignatureCounter, nextSignatureCounter = 2;

	uint32_t numClients;

	uint64_t available_log_memory, total_log_memory;

	printf("=> operationalTest: START\n");

	/** TSE v2 temperature readings and self test */
	if(se_getHardwareVersion() >= version2)
	{
		uint32_t	temperature;

		if((result = se_getTemperature(&temperature)) != ExecutionOk)
			return printError(result, "se_getTemperature", 0);
		printf(" => Raw TSE core temperature = %u\n", temperature);

		if((result = se_getTemperature1(3329, &temperature)) != ExecutionOk)
			return printError(result, "se_getTemperature1", 0);
		printf(" => TSE core temperature, assuming 3.329 V supply voltage (Kingston reader) = %.1f C +/-3K\n", (float) temperature/10);

		rv = selfTest();
		if(rv != 0)
			return rv;
	}

	/** Get the maximum number of possible ERS (cash registers) that are usable */
	if ((result = se_getMaxNumberOfClients(&max_clients)) != ExecutionOk)
		return printError(result, "se_getMaxNumberOfClients", 0);

	/** default 128 */
	if (128 != max_clients)
		return printError(max_clients, "MaxNumberOfClients", "128 expected");

	/** Get the maximum number of possible open transactions */
	if ((result = se_getMaxNumberOfTransactions(&max_transactions)) != ExecutionOk)
		return printError(result, "se_getMaxNumberOfTransactions", 0);

	/** Get update variants */
	if ((result = se_getSupportedTransactionUpdateVariants(&variants)) != ExecutionOk)
		return printError(result, "se_getSupportedTransactionUpdateVariants", 0);

	if (variants != signedUpdate)
	{
		printError((int) variants, "Update variant", "unexpected");
		return 1;
	}

	/** Get TSE supported time formats */
	if ((result = se_getTimeSyncVariant(&time_sync_variant)) != ExecutionOk)
		return printError(result, "se_getTimeSyncVariant", 0);

	/** Expected time sync variant is unixTime */
	if (time_sync_variant != unixTime)
	{
		printError((int) time_sync_variant, "supported time format", "not unixTime");
		return 1;
	}

	/** Get TSE update time interval */
	if ((result = se_getTimeSyncInterval(&time_sync_interval)) != ExecutionOk)
		return printError(result, "se_getTimeSyncInterval", 0);

	/** Get wear indicator */
	if ((result = se_getWearIndicator(&wearIndicator)) != ExecutionOk)
		return printError(result, "se_getWearIndicator", 0);

	/** Signature counter tests - not fully supported before TSE v2, expect some ErrorFunctionNotSupported */
	{
		/** Get min signature counter  */
		if ((result = se_getMinSignatureCounter(&minSignatureCounter)) != ExecutionOk && result != ErrorFunctionNotSupported)
			return printError(result, "se_getMinSignatureCounter", 0);

		/** Expected min signature counter value >= 1 */
		if (result == ExecutionOk && minSignatureCounter < 1)
		{
			printError(minSignatureCounter, "minSignatureCounter value ", "less than 1");
			return 1;
		}

		/** Get max signature counter  */
		if ((result = se_getMaxSignatureCounter(&maxSignatureCounter)) != ExecutionOk && result != ErrorFunctionNotSupported)
			return printError(result, "se_getMaxSignatureCounter", 0);

		/** Expected max signature counter value >= minSignatureCounter */
		if (result == ExecutionOk && maxSignatureCounter < minSignatureCounter)
		{
			printError(maxSignatureCounter, "maxSignatureCounter value ", "less than minSignatureCounter");
			return 1;
		}

		/** Get next signature counter  */
		if ((result = se_getNextSignatureCounter(&nextSignatureCounter)) != ExecutionOk && result != ErrorFunctionNotSupported)
			return printError(result, "se_getNextSignatureCounter", 0);

		/** expected nextSignatureCounter >= minSignatureCounter && <= maxSignatureCounter */
		if (result == ExecutionOk && (nextSignatureCounter < minSignatureCounter || nextSignatureCounter > maxSignatureCounter))
		{
			printError(nextSignatureCounter, "nextSignatureCounter value ", " invalid value");
			return 1;
		}

		/** Export one log to tar-file via stream */
		{
			FILE* stream = fopen("tseOneTransactionLog.tar", "wb+");
			if (stream != NULL)
			{
				result = se_exportMoreDataToStream(m_serialNumbers + 6, 32, nextSignatureCounter - 1, 1, stream);
				fclose(stream);
				if (result != ExecutionOk)
					return printError(result, "se_exportMoreDataToStream", 0);
			}
		}

		/** Get next signature counter after export */
		if ((result = se_getNextSignatureCounter(&nextSignatureCounter)) != ExecutionOk && result != ErrorFunctionNotSupported)
			return printError(result, "se_getNextSignatureCounter", 0);

		/** expected nextSignatureCounter >= minSignatureCounter && <= maxSignatureCounter */
		if (result == ExecutionOk && (nextSignatureCounter < minSignatureCounter || nextSignatureCounter > maxSignatureCounter))
		{
			printError(nextSignatureCounter, "nextSignatureCounter value ", " invalid value");
			return 1;
		}
	}

	/** get TSE signing certificate file, no TAR, see se_exportCertificates for TSE v1 */
	if (se_getHardwareVersion() == version2)
	{
		if ((result = se_getCertificate(PARAM_BUFFER(m_certificates))) != ExecutionOk)
			return printError(result, "se_getCertificate", 0);
		se_free(m_certificates);
        m_certificates = NULL;
	}

	/** Get current transactions */
	if((result = se_getCurrentNumberOfTransactions(&transactions)) != ExecutionOk)
		return printError(result, "se_getCurrentNumberOfTransactions", 0);

	/** Get currently active ERS (cash registers) */
	if ((result = se_getCurrentNumberOfClients(&numClients)) != ExecutionOk)
		return printError(result, "se_getCurrentNumberOfClients", 0);

	/** Get signature algorithm OID */
	if ((result = se_getSignatureAlgorithm(PARAM_BUFFER(m_signatureAlgorithm))) != ExecutionOk)
		return printError(result, "se_getSignatureAlgorithm", 0);

	/** Authenticate TimeAdmin and set the system time. This MUST be done on every power-up */
	/** Timeouts apply: TimeAdmin is automatically logged out after 2 seconds. */
	if ((result = se_authenticateUser(PARAM_STR(TimeAdmin), PARAM_BA(m_timeAdminPin), &authResult, &tries_remaining)) != ExecutionOk)
		return printError(result, "se_authenticateUser", 0);

	if (authResult != authenticationOk)
	{
		printError((int) authResult, "TimeAdmin authentication", "authentication failed");
		printf(" => Tries remaining = %i\n", tries_remaining);
		return 1;
	}

	/** Set time and logout TimeAdmin */
	start_time = getTimestamp();
	if ((result = se_updateTime(start_time)) != ExecutionOk)
		return printError(result, "se_updateTime", 0);

	if ((result = se_logOut(PARAM_STR(TimeAdmin))) != ExecutionOk)
		return printError(result, "se_logOut", "TimeAdmin logout failed");

	/** Get TSE life cycle state */
	if ((result = se_getLifeCycleState(&lcs)) != ExecutionOk)
		return printError(result, "se_getLifeCycleState", 0);

	if (lcs != lcsActive)
	{
		printError((int) lcs, "life cycle state", "not Active");
		return 1;
	}

	/** check certificate expiration date */
	if ((result = se_getCertificateExpirationDate1(&expiration_date)) != ExecutionOk)
		return printError(result, "se_getCertificateExpirationDate1", 0);

	if (start_time > expiration_date)
	{
		printf(" => Certificate expired\n");
		printf("=> operationalTest: STOP\n");
		return 1;
	}

	/** get public key */
	if ((result = se_exportPublicKey(m_serialNumbers + 6, 32, PARAM_BUFFER(m_publicKey))) != ExecutionOk)
		return printError(result, "se_exportPublicKey", 0);

	/** TimeAdmin PIN unblock test */
	{
		uint8_t wrong_pin[] = { 0x2a,0x2a,0x2a,0x2a,0x2a,0x2a,0x2a,0x2a };
		uint8_t wrong_puk[] = { 0x2a,0x2a,0x2a,0x2a,0x2a,0x2a,0x2a,0x2a,0x2a,0x2a };

		/** wrong pin try 1 */
		if ((result = se_authenticateUser(PARAM_STR(TimeAdmin), PARAM_BA(wrong_pin), &authResult, &tries_remaining)) != ExecutionOk)
			return printError(result, "se_authenticateUser", 0);

		if (authResult != authenticationFailed || tries_remaining != 2)
		{
			printError((int) authResult, "TimeAdmin authentication", "unexpected result for wrong pin try 1");
			printf(" => Tries remaining = %i\n", tries_remaining);
			return 1;
		}

		/** wrong pin try 2 */
		if ((result = se_authenticateUser(PARAM_STR(TimeAdmin), PARAM_BA(wrong_pin), &authResult, &tries_remaining)) != ExecutionOk)
			return printError(result, "se_authenticateUser", 0);

		if (authResult != authenticationFailed || tries_remaining != 1)
		{
			printError((int) authResult, "TimeAdmin authentication", "unexpected result for wrong pin try 2");
			printf(" => Tries remaining = %i\n", tries_remaining);
			return 1;
		}

		/** wrong pin try 3 */
		if ((result = se_authenticateUser(PARAM_STR(TimeAdmin), PARAM_BA(wrong_pin), &authResult, &tries_remaining)) != ExecutionOk)
			return printError(result, "se_authenticateUser", 0);

		if (authResult != authenticationFailed || tries_remaining != 0)
		{
			printError((int) authResult, "TimeAdmin authentication", "unexpected result for wrong pin try 3");
			printf(" => Tries remaining = %i\n", tries_remaining);
			return 1;
		}

		/** try 4 with correct pin */
		if ((result = se_authenticateUser(PARAM_STR(TimeAdmin), PARAM_BA(m_timeAdminPin), &authResult, &tries_remaining)) != ExecutionOk)
			return printError(result, "se_authenticateUser", 0);

		if (authResult != authenticationPinIsBlocked || tries_remaining != 0)
		{
			printError((int) authResult, "TimeAdmin authentication", "unexpected result for correct pin try 4");
			printf(" => Tries remaining = %i\n", tries_remaining);
			return 1;
		}

		/** unblock try 1 with wrong puk */
		if ((result = se_unblockUser(PARAM_STR(TimeAdmin), PARAM_BA(wrong_puk), PARAM_BA(m_timeAdminPin), &unblockResult)) != ExecutionOk)
			return printError(result, "se_unblockUser", 0);

		if (unblockResult != unblockFailed)
		{
			printError((int) unblockResult, "TimeAdmin unblock", "unexpected result for unblock pin try 1");
			return 1;
		}

		/** unblock try 2 with correct puk */
		if ((result = se_unblockUser(PARAM_STR(TimeAdmin), PARAM_BA(m_timeAdminPuk), PARAM_BA(m_timeAdminPin), &unblockResult)) != ExecutionOk)
			return printError(result, "se_unblockUser", 0);

		if (unblockResult != unblockOk)
		{
			printError((int) unblockResult, "TimeAdmin unblock", "unexpected result for unblock pin try 2");
			return 1;
		}
	}

	/** test ERS mapping */
	{
		char** clients = NULL;
		uint32_t clientsLength;

		/** authenticate Admin - only needed for TSE v1 **/
		if (se_getHardwareVersion() == version1)
			if((result = se_authenticateUser(PARAM_STR(Admin), PARAM_BA(m_adminPin), &authResult, &tries_remaining)) != ExecutionOk)
				return printError(result, "se_authenticateUser", 0);

		/** make sure mapping is deleted*/
		se_deregisterClient(PARAM_STR(clientId));

		/** Get current ERS mapping, listClients not supported before v2 */
		if (se_getHardwareVersion() == version2)
		{
			if ((result = se_listClients(&clients, &clientsLength)) != ExecutionOk)
				return printError(result, "se_listClients", 0);
			if(result == ExecutionOk && clientsLength)
			{
				int i = 0;
				for(i = 0; i < clientsLength; i++)
					se_free(clients[i]);
				se_free(clients);
			}
		}
		else if (se_getHardwareVersion() == version1)
		{
			if((result = se_getERSMappings(PARAM_BUFFER(m_ersMapping))) != ExecutionOk)
				return printError(result, "se_getERSMappings", 0);
		}

		if ((result = se_registerClient(PARAM_STR(clientId))) != ExecutionOk)
			return printError(result, "se_registerClient", 0);

		if ((result = se_listClients(&clients, &clientsLength)) != ExecutionOk && result != ErrorFunctionNotSupported)
			return printError(result, "se_listClients", 0);
		if(result == ExecutionOk && clientsLength)
		{
			int i = 0;
			for(i = 0; i < clientsLength; i++)
				se_free(clients[i]);
			se_free(clients);
		}

		if ((result = se_deregisterClient(PARAM_STR(clientId))) != ExecutionOk)
			return printError(result, "se_deregisterClient", 0);

		/** Configure the TSE to use the ERS "clientID" */
		if ((result = se_registerClient(PARAM_STR(clientId))) != ExecutionOk)
			return printError(result, "se_registerClient", 0);

		if (se_getHardwareVersion() == version1)
			if((result = se_logOut(PARAM_STR(Admin))) != ExecutionOk)
				return printError(result, "se_logOut", "Admin logout failed");
	}

	/** Start, update, finish transaction */
	{
		uint32_t num_tansactions = transactions;
		uint32_t transaction_counter;
		uint32_t signature_counter;

		/* NOTE: maximum total command length is 8156 byte (8k - 36 byte MSC header) */
		uint8_t process_data[8096];
		memset(process_data, 42, sizeof(process_data));

		/** Start new transaction for ERS "clientId" */
		if((result = se_startTransaction(PARAM_STR(clientId), NULL, 0, PARAM_STR(processType), PARAM_STR2BA(additionalData), &m_startTransactionResult)) != ExecutionOk)
			return printError(result, "se_startTransaction", 0);

		if((result = se_getCurrentNumberOfTransactions(&transactions)) != ExecutionOk)
			return printError(result, "se_getCurrentNumberOfTransactions", 0);

		if(transactions != (num_tansactions + 1))
		{
			printError(transactions, "Number of transactions ", "unexpected");
			return 1;
		}

		/** Update transaction for ERS "clientId" */
		if((result = se_updateTransaction(PARAM_STR(clientId), m_startTransactionResult.transactionNumber, PARAM_BA(process_data), PARAM_STR(processType), &m_updateTransactionResult)) != ExecutionOk)
			return printError(result, "se_updateTransaction", 0);

		if((result = se_getCurrentNumberOfTransactions(&transactions)) != ExecutionOk)
			return printError(result, "se_getCurrentNumberOfTransactions", 0);

		if(transactions != (num_tansactions + 1))
		{
			printError(transactions, "Number of transactions ", "unexpected");
			return 1;
		}

		/** Get last log message */
		if((result = se_readLogMessage(PARAM_BUFFER(m_lastLogMessage))) != ExecutionOk)
			return printError(result, "se_readLogMessage", 0);

		/** Get open transactions */
		if((result = se_getOpenTransactions(PARAM_BUFFER(m_openTransactions))) != ExecutionOk)
			return printError(result, "se_getOpenTransactions", 0);
		{
			uint32_t i;
			for(i = 0; i < m_openTransactionsLength && m_openTransactions[i] != m_startTransactionResult.transactionNumber; ++i) {}
			if(i == m_openTransactionsLength)
			{
				printError(0, "Transactions found", "open transaction not found");
				return 1;
			}
		}

		/** Finish transaction for ERS "clientId" */
		if((result = se_finishTransaction(PARAM_STR(clientId), m_startTransactionResult.transactionNumber, PARAM_STR2BA(processData), PARAM_STR(processType), PARAM_STR2BA(additionalData), &m_finishTransactionResult)) != ExecutionOk)
			return printError(result, "se_finishTransaction", 0);

		if((result = se_getCurrentNumberOfTransactions(&transactions)) != ExecutionOk)
			return printError(result, "se_getCurrentNumberOfTransactions", 0);

		if(transactions != num_tansactions)
		{
			printError(transactions, "Number of transactions ", "unexpected");
			return 1;
		}

		if((result = se_getTransactionCounter(&transaction_counter)) != ExecutionOk)
			return printError(result, "se_getTransactionCounter", 0);

		if(transaction_counter != m_startTransactionResult.transactionNumber)
		{
			printError(transaction_counter, "Transactions counter ", "unexpected");
			return 1;
		}

		/** get last signature counter */
		if ((result = se_getSignatureCounter1(&signature_counter)) != ExecutionOk)
			return printError(result, "se_getSignatureCounter1", 0);

		if (signature_counter != m_finishTransactionResult.signatureCounter)
		{
			printError(signature_counter, "Signature counter ", "unexpected");
			return 1;
		}

		/** Filtered export data tests */
#		if(EXPORT_FILTERED_LOGS_TEST != 0)
		{
			/** Export the logs of this transaction */
			uint32_t tnum = m_startTransactionResult.transactionNumber;
			if((result = se_exportData(PARAM_STR(clientId), tnum, tnum, tnum, 0, SE_MAX_TIME, 0, PARAM_BUFFER(m_logMessages))) != ExecutionOk)
				return printError(result, "se_exportData", 0);

			/** get Export size*/
			if ((result = se_getExportSize(PARAM_STR(clientId), tnum, tnum, tnum, 0, SE_MAX_TIME, &m_totalExportSize)) != ExecutionOk)
				return printError(result, "se_getExportSize", 0);

			/** length of exported data*/
			if (m_logMessagesLength == 0) {
				printError(m_logMessagesLength, "exported data length", "unexpected");
				return 1;
			}

			/** test export size using last signature counter*/
			{
				if ((result = se_getExportSize1(0, 0, &m_totalExportSize)) != ExecutionOk)
					return printError(result, "se_getExportSize1", 0);

				/** length of exported data*/
				if (m_totalExportSize == 0)
				{
					printError(m_totalExportSize, "exported data length", "unexpected");
					return 1;
				}
			}

			/** Write the logs to tar-file */
			if(m_logMessages != 0 && m_logMessagesLength > 0)
			{
				FILE* stream = fopen("tseTransactionLogs.tar", "wb+");
				if(stream != NULL)
				{
					fwrite(m_logMessages, sizeof(uint8_t), m_logMessagesLength, stream);
					fclose(stream);
				}
			}
		}
		{
			/** Export all logs from startTransaction signature counter */

			/** NOTE: No proper BER or DER decoding in this test programm; assumption:
			the serial number is a 32-byte-hashvalue encoded as OCTETSTRING at offset 4. */
			if((result = se_exportMoreDataToFile(m_serialNumbers + 6, 32, m_startTransactionResult.signatureCounter, 0, "tseAllTransactionLogsFromCounter.tar")) != ExecutionOk)
				return printError(result, "se_exportMoreDataToFile", 0);
		}
#		endif
	}

	/** Export certificates (tar) */
	if((result = se_exportCertificates(PARAM_BUFFER(m_certificates))) != ExecutionOk)
		return printError(result, "se_exportCertificates", 0);

	/** Write certificates to tar-file */
	if(m_certificates != 0 && m_certificatesLength > 0)
	{
		FILE* stream = fopen("tseCertificates.tar", "wb+");
		if(stream != NULL)
		{
			fwrite(m_certificates, sizeof(uint8_t), m_certificatesLength, stream);
			fclose(stream);
		}

		/* parse certificate from tar-archive */
		{
			uint8_t *cert;
			uint32_t cert_len;

			if((result = se_parseCertificate(m_serialNumbers + 6, 32, m_certificates, m_certificatesLength, &cert, &cert_len)) != ExecutionOk)
				return printError(result, "parseCertificate", "certificate not found");
		}
	}

	/** get total log memory */
	if ((result = se_getTotalLogMemory(&total_log_memory)) != ExecutionOk)
		return printError(result, "se_getTotalLogMemory", 0);

	printf(" => Total log memory = 0x%08X%08X\n",
			(uint32_t)(total_log_memory >> 32), (uint32_t)(total_log_memory & SE_MAX_UINT32));

	/** get available log memory */
	if ((result = se_getAvailableLogMemory(&available_log_memory)) != ExecutionOk)
		return printError(result, "se_getAvailableLogMemory", 0);

	printf(" => Available log memory = 0x%08X%08X\n",
			(uint32_t)(available_log_memory >> 32), (uint32_t)(available_log_memory & SE_MAX_UINT32));

	/** Unfiltered export data test */
#	if(EXPORT_ALL_LOGS_TEST != 0)
	{
		int i;
		for(i = 0; i < EXPORT_ALL_LOGS_TEST; ++i)
		{
			/** Export all transaction logs to tar-file via stream */
			printf(" => exportAll via stream: START\n");
			{
				FILE* stream = fopen("tseAllTransactionLogs.tar", "wb+");
				if(stream != NULL)
				{
					result = se_exportDataToStream(NULL, 0, SE_MAX_UINT32, 0, SE_MAX_UINT32, 0, SE_MAX_TIME, 0, stream);
					fclose(stream);
					if(result != ExecutionOk)
						return printError(result, "se_exportDataToStream", 0);
				}
			}
			printf(" => exportAll via stream: STOP\n");
		}

		for(i = 0; i < EXPORT_ALL_LOGS_TEST; ++i)
		{
			/** Export all transaction logs to tar-file via callback */
			se_handle_t my_handle = (se_handle_t) 42;
			se_writer_t my_writer = myStreamWriter;

			printf(" => exportAll via callback: START\n");
			{
				/** Aborted export test (abort after 3 export callbacks) */
				FILE* stream = fopen("tseAllTransactionLogsViaCallback.tar", "wb+");
				if(stream != NULL)
				{
					m_abort = 3;
					m_writerCount = 0;
					m_callbackStream = stream;

					result = se_exportDataViaCallback(NULL, 0, SE_MAX_UINT32, 0, SE_MAX_UINT32, 0, SE_MAX_TIME, 0, my_writer, my_handle);
					fclose(stream);
					if(result != ErrorCallback)
						return printError(result, "se_exportDataViaCallback", 0);
				}
			}
			printf(" => exportAll via callback aborted: RE-START\n");
			{
				/* full export test*/
				FILE* stream = fopen("tseAllTransactionLogsViaCallback.tar", "wb+");
				if(stream != NULL)
				{
					m_abort = 0;
					m_writerCount = 0;
					m_callbackStream = stream;

					result = se_exportDataViaCallback(NULL, 0, SE_MAX_UINT32, 0, SE_MAX_UINT32, 0, SE_MAX_TIME, 0, my_writer, my_handle);
					fclose(stream);
					if(result != ExecutionOk)
						return printError(result, "se_exportDataViaCallback", 0);
				}
			}
			printf(" => exportAll via callback: STOP\n");
		}
	}
#	endif

	/** Authenticate Admin - Timeouts apply: Admin is automatically logged out after 10. */
	if((result = se_authenticateUser(PARAM_STR(Admin), PARAM_BA(m_adminPin), &authResult, &tries_remaining)) != ExecutionOk)
		return printError(result, "se_authenticateUser", 0);

	if(authResult != authenticationOk)
	{
		printError((int) authResult, "Admin authentication", "authentication failed");
		printf(" => Tries remaining = %i\n", tries_remaining);
		return 1;
	}

#	if(DELETE_LOGS_UP_TO_TEST != 0)
	{
		/** Delete all logs up to finishTransaction signature counter (= StartT.counter + 2) */
		if((result = se_deleteStoredDataUpTo(m_serialNumbers + 6, 32, (uint32_t)(m_startTransactionResult.signatureCounter + 2))) != ExecutionOk)
			return printError(result, "se_deleteStoredDataUpTo", 0);

		/** TSEv2 creates log on deletion. Create one log on v1 */
		if (se_getHardwareVersion() == version1)
			if((result = se_updateTime(getTimestamp())) != ExecutionOk)
				return printError(result, "se_updateTime", 0);

		/** Export all (remaining) data */
		if((result = se_exportDataToFile(NULL, 0, SE_MAX_UINT32, 0, SE_MAX_UINT32, 0, SE_MAX_TIME, 0, "deleteme.tar")) != ExecutionOk)
			return printError(result, "se_exportData", 0);

		/** Delete all logs */
		if((result = se_deleteStoredData()) != ExecutionOk)
			return printError(result, "se_deleteStoredData", 0);
	}
#	endif

#	if(DISABLE_TSE_TEST != 0)
	{
		/** Disable TSE: this is irreversible - except for development samples !!! */
		if((result = se_disableSecureElement()) != ExecutionOk)
			return printError(result, "se_disableSecureElement", 0);
	}
#	else

	if((result = se_logOut(PARAM_STR(Admin))) != ExecutionOk)
		return printError(result, "se_logOut", "Admin logout failed");
#	endif

	printf("=> operationalTest: STOP\n");

	return 0;
}

/* ------------------------------------------------------------------------- */
#if EXPORT_TOOL || TEST_TOOL
int exportAll()
{
	se_result_t result;

	uint32_t tse_id_len = 0;
	const uint8_t *tse_id = NULL;
	const char *firmware = NULL;

	se_lcs_t lcs;

	char filename[200] = "ExportAll";

#	if TEST_TOOL
	printf("=> exporting all data - you can cancel at any time.\n");
#	endif
	printf("=> run Export: START\n\n");


	/** Get TSE unique identifier */
	tse_id = se_getUniqueId(&tse_id_len);
	if(tse_id == NULL) return 1;

	/** Get TSE firmware identifier */
	firmware = se_getFirmwareId();
	if(firmware == NULL) return 1;

	/** Get TSE life cycle state */
	if ((result = se_getLifeCycleState(&lcs)) != ExecutionOk)
		return printError(result, "se_getLifeCycleState", 0);

	if(lcs == lcsNotInitialized)
	{
		printf(" => TSE not yet initialized, nothing to export.\n");
		return 0;
	}

	if(lcs != lcsSeError)
	{
		int i;

		if((result = se_exportSerialNumbers(PARAM_BUFFER(m_serialNumbers))) != ExecutionOk)
			return printError(result, "se_exportSerialNumbers", 0);

		sprintf(filename+strlen(filename), "_Serial-");
		for(i = 0; i < 32; ++i)
			sprintf(filename+strlen(filename), "%02X", (int)(m_serialNumbers[i+6])); /* byte2hex */

		sprintf(filename+strlen(filename), "_ID-");
		for(i = 0; i < tse_id_len; ++i)
			sprintf(filename+strlen(filename), "%02X", (int)(tse_id[i])); /* byte2hex */

		if(lcs != lcsDisabled)
		{
			if ((result = se_getSignatureCounter1(&m_signature_counter)) != ExecutionOk)
				return printError(result, "se_getSignatureCounter1", 0);

			sprintf(filename+strlen(filename), "_Sig-%u", m_signature_counter);
		}

		sprintf(filename+strlen(filename), "_Firmware-%.6s", firmware);
	}

	sprintf(filename+strlen(filename), ".tar");

	{
		if ((result = se_getExportSize1(0, 0, &m_totalExportSize)) != ExecutionOk)
			return printError(result, "se_getExportSize1", 0);

		FILE* stream = fopen(filename, "wb+");
		if(stream == NULL)
			return 1;

		printf(" => Exporting %llu kb to %s\n", m_totalExportSize/1024, filename);

		m_callbackStream = stream;
		result = se_exportMoreDataViaCallback(NULL, 0, 0, 0, myStreamWriter, NULL);
		fclose(stream);
		if(result != ExecutionOk)
			return printError(result, "se_exportDataViaCallback", 0);
	}

	printf("=> Export successful\n");

	return 0;
}
#if DO_DELETE
int deleteExported(const char* adminPin)
{
	se_authentication_result_t authResult;
	int16_t tries_remaining;
	se_result_t result;

	printf("=> run deleteExported: START\n\n");

	/** Authenticate Admin - Timeouts apply: Admin is automatically logged out after 10. */
	if((result = se_authenticateUser(PARAM_STR(Admin), (const uint8_t*) adminPin, strlen(adminPin), &authResult, &tries_remaining)) != ExecutionOk)
		return printError(result, "se_authenticateUser", 0);

	if(authResult != authenticationOk)
	{
		printError((int) authResult, "Admin authentication", "authentication failed");
		printf(" => Tries remaining = %i\n", tries_remaining);
		return 1;
	}

	printf("=> delete up Signature Counter %u\n", m_signature_counter);

	/** Delete all logs up to finishTransaction signature counter (= StartT.counter + 2) */
	if((result = se_deleteStoredDataUpTo(m_serialNumbers + 6, 32, m_signature_counter)) != ExecutionOk)
		return printError(result, "se_deleteStoredDataUpTo", 0);

	printf("=> run deleteExported: SUCCESS\n\n");

	return 0;
}
#endif // DO_DELETE

/* ------------------------------------------------------------------------- */
#if TEST_TOOL
int runTests()
{
	se_result_t result;

	uint32_t tse_id_len = 0;
	const uint8_t *tse_id = NULL;
	const char *firmware = NULL;
	se_pin_state_flags_t pin_state;
	uint32_t wearIndicator;
	uint64_t available_log_memory, total_log_memory;
	uint32_t	temperature;
	uint32_t transactions, transaction_counter;

	se_lcs_t lcs;

	printf("=> run Tests: START\n\n");

	/** Get PIN states in order to check if this is a new TSE */
	if((result = se_getPinStatus(&pin_state)) != ExecutionOk)
		return printError(result, "se_getPinStatus", 0);

	printf("=> PIN states:\n");
	printf(" =>     Admin PUK = %s\n", pin_state & adminPukTransportState ? "uninitialized" : "  initialized");
	printf(" =>     Admin PIN = %s\n", pin_state & adminPinTransportState ? "uninitialized" : "  initialized");
	printf(" => TimeAdmin PUK = %s\n", pin_state & timeAdminPukTransportState ? "uninitialized" : "  initialized");
	printf(" => TimeAdmin PIN = %s\n", pin_state & timeAdminPinTransportState ? "uninitialized" : "  initialized");

	if(se_getHardwareVersion() < version2)
	{
		printf("=> ERROR: TSE v1 not supported\n");
		return 1;
	}

	printf("=> TSE life Cycle State:\n");
/** Get TSE life cycle state */
	if ((result = se_getLifeCycleState(&lcs)) != ExecutionOk)
		return printError(result, "se_getLifeCycleState", 0);

	switch(lcs)
	{
	case lcsUnknown:        printf(" => ERROR: the LCS is unknown"); break;
	case lcsNotInitialized: printf(" => the TSE has not yet been initialized"); break;
	case lcsNoTime:         printf(" => all OK, but the TSE time has not yet been set by this test"); break;
	case lcsActive:         printf(" => the TSE is active and the time has been set (ready for transactions)"); break;
	case lcsDeactivated:    printf(" => the TSE has been deactivated"); break;
	case lcsDisabled:       printf(" => the TSE has been disabled"); break;
	case lcsSeError:        printf(" => ERROR: Secure Element not available"); break;
	case lcsSleep:          printf(" => ERROR: device was powered down (by OS or card reader)"); break;
	case lcsClosed:         printf(" => ERROR: device handle was closed"); break;
	}
	printf("\n");

	if(lcs > lcsNotInitialized)
	{
		int i;

		/** Get the serial number of the available key */
		if((result = se_exportSerialNumbers(PARAM_BUFFER(m_serialNumbers))) != ExecutionOk)
			return printError(result, "se_exportSerialNumbers", 0);

		/** NOTE: No proper BER or DER decoding in this test program; assumption:
		the serial number is a 32-byte-hashvalue encoded as OCTETSTRING at offset 4. */
		if(m_serialNumbersLength < 38 || m_serialNumbers[4] != 0x04 || m_serialNumbers[5] != 0x20)
			return printError(m_serialNumbersLength, "SerialNumbers encoding", "unexpected");

		printf("=> TSE serial number: ");
		for(i = 0; i < 32; ++i) printf("%02X", (int)(m_serialNumbers[i+6])); /* byte2hex */
		printf("\n");

		if(lcs != lcsDisabled)
		{
			if ((result = se_getSignatureCounter1(&m_signature_counter)) != ExecutionOk)
				return printError(result, "se_getSignatureCounter1", 0);
			printf("=> Current signature counter: %d\n", m_signature_counter);
		}

		/** get total log memory */
		if ((result = se_getTotalLogMemory(&total_log_memory)) != ExecutionOk)
			return printError(result, "se_getTotalLogMemory", 0);
		printf("=> Total log memory = 0x%08X%08X\n",
				(uint32_t)(total_log_memory >> 32), (uint32_t)(total_log_memory & SE_MAX_UINT32));

		/** get available log memory */
		if ((result = se_getAvailableLogMemory(&available_log_memory)) != ExecutionOk)
			return printError(result, "se_getAvailableLogMemory", 0);
		printf("=> Available log memory = 0x%08X%08X\n",
				(uint32_t)(available_log_memory >> 32), (uint32_t)(available_log_memory & SE_MAX_UINT32));

		/** Get wear indicator */
		if ((result = se_getWearIndicator(&wearIndicator)) != ExecutionOk)
			return printError(result, "se_getWearIndicator", 0);
		printf("=> Wear indicator: %d\n", wearIndicator);


		if((result = se_getTemperature(&temperature)) != ExecutionOk)
			return printError(result, "se_getTemperature", 0);
		printf("=> Raw TSE core temperature = %u\n", temperature);

		if((result = se_getTemperature1(3329, &temperature)) != ExecutionOk)
			return printError(result, "se_getTemperature1", 0);
		printf("=> TSE core temperature, assuming 3.329 V supply voltage (Kingston reader) = %.1f C +/-3K\n", (float) temperature/10);

		if((result = se_getCurrentNumberOfTransactions(&transactions)) != ExecutionOk)
			return printError(result, "se_getCurrentNumberOfTransactions", 0);
		printf("=> Number of open transactions: %d\n", transactions);

		if((result = se_getTransactionCounter(&transaction_counter)) != ExecutionOk)
			return printError(result, "se_getTransactionCounter", 0);
		printf("=> Current transaction number: %d\n", transaction_counter);
	}

	printf("=> Starting selftest ... this might take long, you can cancel at any time.\n");
	selfTest();

	printf("\n=> run Tests: DONE\n\n");

	return 0;
}
#endif // TEST_TOOL
#endif // EXPORT_TOOL || TEST_TOOL

/* ------------------------------------------------------------------------- */
int main(int argc, char* argv[])
{
	int test_result = 0;
	const char* devicePath;
	uint32_t timeout = 0; /* 0 = default (10s since API v3) */

	if(argc < 2)
	{
		printf("Usage: use the TSE device path as input (example 'E:')\n");
		return 0;
	}
	devicePath = (const char*) argv[1];
	
	printf("--- se_api_test START ---\n\n");

	if((test_result = getApiVersion()) != 0)
		return test_result;

	printf("=> device Path: %s\n", devicePath);
	printf("=> device Mode: %s\n", "MSC");

	/* initialize SE-API returned buffers used by the test functions */
	initOutputBuffers();

	/* initialize SE-API memory management functions */
	/* NOTE: OPTIONAL, default behavior is the usage of malloc() and free() */
#	if(USE_MEMORY_CALLBACKS != 0)
	{
		if(se_setAllocator(myMalloc, myFree) != ExecutionOk)
			return 1;
	}
#	endif
			
	/* TSE accessing tests */
	printf("\n");
	{
		se_result_t result;
		const char* pin;

		/* open SE transport IO (sends the Start command to the TSE) */
		result = se_openDirect2(devicePath, timeout, SE_MAX_RESPONSE_8k, CHECK_INTEGRITY);
		if(result == ErrorSelftestFailed)
		{
			printError(result, "se_openDirect2", 0);
		}
		else if(result != ExecutionOk)
		{
			printError(result, "se_openDirect2", 0);
			if(result == ErrorIO) printf("[OS error code = 0x%08X]\n", se_getOsStatusOfErrorIO());
			++test_result;
		}

		uint8_t is_ES;
		if(test_result == 0) test_result += getTseIdentifier(&is_ES);

#		if(TEST_TOOL == 1)
		if(test_result == 0) test_result += runTests();
		if(test_result == 0) test_result += exportAll();
#		else
#		if(EXPORT_TOOL == 1)
		{
#			if(DO_DELETE)
				if(argc < 3)
				{
					printf("Usage: add the Admin PIN!\n");
					return -1;
				}
				pin = (const char*) argv[2];
#endif
			if(test_result == 0) test_result += exportAll();
#			if(DO_DELETE)
				if(test_result == 0) test_result += deleteExported(pin);
#endif
		}
#		else
		{
			/* run SE-API test functions */
			if(test_result == 0 && is_ES != 1)
			{
				printf(" => Refusing to run test on productive TSE - hack the source to continue.\n");
				return 1;
			}

			if(test_result == 0) test_result += firstBootTest();
			if(test_result == 0) test_result += operationalTest();
		
			/** test reopen */
			if (test_result == 0)
			{
				uint32_t counter;

				/** try to reopen connection */
				if ((result = se_reopen2(devicePath, timeout, SE_MAX_RESPONSE_8k, CHECK_INTEGRITY)) != ExecutionOk)
				{
					printError(result, "se_reopen", 0);
					if (result == ErrorIO) printf("[OS error code = 0x%08X]\n", se_getOsStatusOfErrorIO());
					++test_result;
				}
				/** check if TSE is operational */
				if ((result = se_getMinSignatureCounter(&counter)) != ExecutionOk && result != ErrorFunctionNotSupported)
					return printError(result, "se_getMinSignatureCounter after reopen", 0);
			}
		}
#		endif
#		endif

		/* close SE transport IO */
		if((result = se_close()) != ExecutionOk)
		{
			printError(result, "se_close", 0);
			if(result == ErrorIO) printf("[OS error code = 0x%08X]\n", se_getOsStatusOfErrorIO());
			++test_result;
		}
	}

	/* free SE-API returned buffers used by the test functions */
	freeOutputBuffers();

	/* print result */
	printf("\n");
#	if(EXPORT_TOOL == 0 && TEST_TOOL == 0)
	{
		printf("[myWriter count (last export) = %i]\n", m_writerCount);
	}
#	endif
#	if(USE_MEMORY_CALLBACKS == 1)
	{
		printf("[myMalloc count = %i, myFree count = %i -> %s]\n", m_mallocCount, m_freeCount, (m_mallocCount == m_freeCount ? "equal" : "Oops, not equal!"));
	}
#	endif
	printf("=> Test result = %i (%s)\n", test_result, test_result == 0 ? "OK" : "Failed");
	printf("\n--- se_api_test STOP ---\n");

	return test_result;
}
