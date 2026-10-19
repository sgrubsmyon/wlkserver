/*
 * Copyright (c) 2019-2024
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
  * @file se_api_ex_test.c
  *
  * @brief Minimal demo of the cryptovision _extended_ SE-API for "C".
  *
  * The test demonstrates the access of more than one TSE with the
  * extended SE-API-EX-C using one context object for each TSE device.
  *
  * Reduced functionality, see NOTE at main function!
  */

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include <se_api_ex.h>
#include <se_memory_util.h>
#include <se_transport_util.h>

/**
* Test configuration.
*/

#define EXPORT_ALL_LOGS_TEST	1


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

uint32_t* m_openTransactions;
uint32_t m_openTransactionsLength;

se_start_transaction_result_t m_startTransactionResult;
se_update_transaction_result_t m_updateTransactionResult;
se_finish_transaction_result_t m_finishTransactionResult;


/**
* Callback related variables.
*/

FILE* m_callbackStream = NULL;
int m_writerCount = 0;


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
			printf("[myWriter(handle 0x%08X%08X): Total export length = 0x%08X%08X byte]\n",
				(uint32_t)(handle_value >> 32), (uint32_t)(handle_value & SE_MAX_UINT32),
				(uint32_t)(totalDataLength >> 32), (uint32_t)(totalDataLength & SE_MAX_UINT32));
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
			printf("[myWriter(handle 0x%08X%08X): 0x%04X of 0x%04X byte data processed from address 0x%08X%08X]\n",
				(uint32_t)(handle_value >> 32), (uint32_t)(handle_value & SE_MAX_UINT32), data_written, dataLength,
				(uint32_t)(address >> 32), (uint32_t)(address & SE_MAX_UINT32));
		}
		else
			printf("[myWriter(handle 0x%08X%08X): Failed to process 0x%04X byte from address 0x%08X%08X]\n", 
				(uint32_t)(handle_value >> 32), (uint32_t)(handle_value & SE_MAX_UINT32), dataLength,
				(uint32_t)(address >> 32), (uint32_t)(address & SE_MAX_UINT32));
	}

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
int64_t getTimestamp()
{
	return (int64_t)(time(NULL));
}

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

	api_version = se_getApiVersionEx(&apiVersionLength);
	if(apiVersionLength != 2) return 1;

	impl_version = se_getImplementationVersionEx(&implVersionLength);
	if(implVersionLength != 3) return 1;

	printf("=> SE-API version string: '%s', version array: [%i.%i]\n",
		se_getApiVersionStringEx(), api_version[0], api_version[1]);
	printf("=> SE-API-EX-C implementation version string: '%s', version array: [%i.%i.%i]\n",
		se_getImplementationVersionStringEx(), impl_version[0], impl_version[1], impl_version[2]);

	return 0;
}

/* ------------------------------------------------------------------------- */
int getTseIdentifier(se_ctx_t* ctx)
{
	se_result_t result;

	uint8_t is_ES;
	uint32_t tse_id_len = 0;
	const uint8_t *tse_id = NULL;
	const char *firmware = NULL;

	/** Get TSE unique identifier */
	tse_id = se_getUniqueIdEx(ctx, &tse_id_len);
	if(tse_id == NULL) return 1;

	/** Get TSE firmware identifier */
	firmware = se_getFirmwareIdEx(ctx);
	if(firmware == NULL) return 1;

	/** Get TSE certification identifier */
	if((result = se_getCertificationIdEx(ctx, PARAM_BUFFER(m_certificationId))) != ExecutionOk)
		return printError(result, "se_getCertificationIdEx", 0);
	{
		uint32_t i;
		char buf[32];

		printf("=> TSE hardware version: %d\n", se_getHardwareVersionEx(ctx));

		printf("=> TSE unique identifier: ");
		for(i = 0; i < tse_id_len; ++i)
			printf("%02X", (int)(tse_id[i])); /* byte2hex */

		printf("\n=> TSE firmware identifier: %s\n", firmware);

		memset(buf, 0, sizeof(buf));
		if(m_certificationIdLength < sizeof(buf))
			memcpy(buf, m_certificationId, m_certificationIdLength);

		printf("=> TSE certification identifier: %s\n", buf);
	}

	/** engineering sample check (avoid running of this test for productive samples)*/
	result = se_isEngineeringSampleEx(ctx, &is_ES);
	if(result != ExecutionOk)
		return printError(result, "se_isEngineeringSampleEx", 0);

	if(is_ES != 1)
	{
		printf("=> Refusing to run test on productive TSE - hack the source to continue.\n\n");
		return 1;
	}

	printf("\n");
	return 0;
}

/* ------------------------------------------------------------------------- */
int firstBootTest(se_ctx_t* ctx)
{
	se_result_t result;

	se_pin_state_flags_t pin_state;
	se_authentication_result_t authResult;

	int16_t tries_remaining;
	uint32_t max_clients, max_transactions;

	printf("=> firstBootTest: START\n");

	/** Get PIN states in order to check if this is a new TSE
	*  This MUST be done to ensure your TSE's key has not been used before! */
	if((result = se_getPinStatusEx(ctx, &pin_state)) != ExecutionOk)
		return printError(result, "se_getPinStatusEx", 0);

	if(pin_state == stateInitialized)
	{
		int i;

		/** Get the serial number of the available key */
		if((result = se_exportSerialNumbersEx(ctx, PARAM_BUFFER(m_serialNumbers))) != ExecutionOk)
			return printError(result, "se_exportSerialNumbersEx", 0);

		/** NOTE: No proper BER or DER decoding in this test program; assumption:
		the serial number is a 32-byte-hashvalue encoded as OCTETSTRING at offset 4. */
		if(m_serialNumbersLength < 38 || m_serialNumbers[4] != 0x04 || m_serialNumbers[5] != 0x20)
			return printError(m_serialNumbersLength, "SerialNumbers encoding", "unexpected");

		printf(" => PINs already initialized, TSE is in use.\n");
		printf(" => Key serial number: ");
		for(i = 0; i < 32; ++i) printf("%02X", (int)(m_serialNumbers[i+6])); /* byte2hex */
		printf("\n=> firstBootTest: SKIPPED\n");
		return 0;
	}

	/** Initialize PIN and PUK values for Admin and TimeAdmin */
	/** PUK values cannot be changed once initialized */
	if((result = se_initializePinValuesEx(ctx, PARAM_BA(m_adminPin), PARAM_BA(m_adminPuk), PARAM_BA(m_timeAdminPin), PARAM_BA(m_timeAdminPuk))) != ExecutionOk)
		return printError(result, "se_initializePinValuesEx", 0);

	/** Authenticate the Admin role with the newly set Admin PIN in order to get the rights to initialize the TSE */
	/** Timeouts apply: Admin is automatically logged out after 10 minutes. */
	if((result = se_authenticateUserEx(ctx, PARAM_STR(Admin), PARAM_BA(m_adminPin), &authResult, &tries_remaining)) != ExecutionOk)
		return printError(result, "se_authenticateUserEx", 0);

	if(authResult != authenticationOk)
	{
		printError((int) authResult, "Admin authentication", "authentication failed");
		printf(" => Tries remaining = %i\n", tries_remaining);
		return 1;
	}

	/** Initialize the TSE for operational use (signing of transaction data) */
	if((result = se_initializeEx(ctx)) != ExecutionOk)
		return printError(result, "se_initializeEx", 0);

	/** Authenticate TimeAdmin and set the system time. This MUST be done on every power-up */
	/** Timeouts apply: TimeAdmin is automatically logged out after 2 seconds. */
	if((result = se_authenticateUserEx(ctx, PARAM_STR(TimeAdmin), PARAM_BA(m_timeAdminPin), &authResult, &tries_remaining)) != ExecutionOk)
		return printError(result, "se_authenticateUserEx", 0);

	if(authResult != authenticationOk)
	{
		printError((int) authResult, "TimeAdmin authentication", "authentication failed");
		printf(" => Tries remaining = %i\n", tries_remaining);
		return 1;
	}

	if((result = se_updateTimeEx(ctx, getTimestamp())) != ExecutionOk)
		return printError(result, "se_updateTimeEx", 0);

	if((result = se_logOutEx(ctx, PARAM_STR(TimeAdmin))) != ExecutionOk)
		return printError(result, "se_logOutEx", "TimeAdmin logout failed");

	/** Get the maximum number of possible ERS (cash registers) that are usable */
	if((result = se_getMaxNumberOfClientsEx(ctx, &max_clients)) != ExecutionOk)
		return printError(result, "se_getMaxNumberOfClientsEx", 0);

	/** default 128 */
	if(128 != max_clients)
		return printError(max_clients, "MaxNumberOfClients", "128 expected");

	/** Get the maximum number of possible open transactions */
	if((result = se_getMaxNumberOfTransactionsEx(ctx, &max_transactions)) != ExecutionOk)
		return printError(result, "se_getMaxNumberOfTransactionsEx", 0);

	/** Get the serial numbers of the available keys */
	if((result = se_exportSerialNumbersEx(ctx, PARAM_BUFFER(m_serialNumbers))) != ExecutionOk)
		return printError(result, "se_exportSerialNumbersEx", 0);

	/** NOTE: No proper BER or DER decoding in this test programm; assumption: 
	the serial number is a 32-byte-hashvalue encoded as OCTETSTRING at offset 4. */
	if(m_serialNumbersLength < 38 || m_serialNumbers[4] != 0x04 || m_serialNumbers[5] != 0x20)
		return printError(m_serialNumbersLength, "SerialNumbers encoding", "unexpected");

	/** Configure the TSE to use the ERS "clientID" */
	if((result = se_registerClientEx(ctx, PARAM_STR(clientId))) != ExecutionOk)
		return printError(result, "se_registerClientEx", 0);

	if((result = se_deactivateTSEEx(ctx)) != ExecutionOk)
		return printError(result, "se_deactivateTSEEx", 0);

	if((result = se_activateTSEEx(ctx)) != ExecutionOk)
		return printError(result, "se_activateTSEEx", 0);

	if((result = se_logOutEx(ctx, PARAM_STR(Admin))) != ExecutionOk)
		return printError(result, "se_logOutEx", "Admin logout failed");

	printf("=> firstBootTest: STOP\n");

	return 0;
}

/* ------------------------------------------------------------------------- */
int operationalTest(se_ctx_t* ctx)
{
	se_result_t result;

	char buf[32];

	se_lcs_t lcs;
	se_update_t variants;

	uint32_t time_sync_interval;
	se_sync_variants_t time_sync_variant;
	int64_t start_time, expiration_date;

	int16_t tries_remaining;
	se_authentication_result_t authResult;

	uint32_t transactions;
	uint32_t max_clients, max_transactions, wearIndicator;

	uint64_t available_log_memory, total_log_memory;

	printf("=> operationalTest: START\n");

	/** TSE v2 temperature readings and self test */
	if(se_getHardwareVersionEx(ctx) >= version2)
	{
		uint32_t	temperature;

		if((result = se_getTemperatureEx(ctx, &temperature)) != ExecutionOk)
			return printError(result, "se_getTemperatureEx", 0);
		printf(" => Raw TSE core temperature = %u\n", temperature);

		if((result = se_getTemperature1Ex(ctx, 3329, &temperature)) != ExecutionOk)
			return printError(result, "se_getTemperature1Ex", 0);
		printf(" => TSE core temperature, assuming 3.329 V supply voltage (Kingston reader) = %.1f C +/-3K\n", (float) temperature/10);

		printf(" => Run TSE selftest ...\n");
		{
			int i;
			int32_t	millis;
			int64_t	start_time, total_time;

			se_self_test_result_t selfTestResult;

			/** run self test for at most 10 seconds: */
			start_time = se_currentTimeMillis();
			for(i = 1; i <= 10; i++)
			{
				selfTestResult.log = NULL;

				/** run self test for at most 1 second */
				result = se_selfTestEx(ctx, 1, &selfTestResult);

				/** free allocated log (not handled in this sample) */
				if(selfTestResult.log)
					se_free(selfTestResult.log);

				if(result != ExecutionOk)
					return printError(result, "se_selfTest", 0);
				if(selfTestResult.completed != 0)
					break;
				if(selfTestResult.errorsFound != 0)
					printf("  => Problems known to be present after %i. call\n", i);
			}
			total_time = se_currentTimeMillis() - start_time;
			millis = (int32_t)total_time;

			printf("  => Selftest completed  =  %s\n", (selfTestResult.completed ? "YES" : "NO"));
			printf("  => Selftest has errors =  %s\n", (selfTestResult.errorsFound ? "YES" : "NO"));
			printf("  => Selftest runtime    =  %i ms\n", (millis == total_time ? millis : 0));
		}
	}

	/** Get the maximum number of possible ERS (cash registers) that are usable */
	if((result = se_getMaxNumberOfClientsEx(ctx, &max_clients)) != ExecutionOk)
		return printError(result, "se_getMaxNumberOfClientsEx", 0);

	/** default 128 */
	if(128 != max_clients)
		return printError(max_clients, "MaxNumberOfClients", "128 expected");

	/** Get the maximum number of possible open transactions */
	if((result = se_getMaxNumberOfTransactionsEx(ctx, &max_transactions)) != ExecutionOk)
		return printError(result, "se_getMaxNumberOfTransactionsEx", 0);

	/** Get update variants */
	if((result = se_getSupportedTransactionUpdateVariantsEx(ctx, &variants)) != ExecutionOk)
		return printError(result, "se_getSupportedTransactionUpdateVariantsEx", 0);

	if(variants != signedUpdate)
	{
		printError((int) variants, "Update variant", "unexpected");
		return 1;
	}

	/** Get TSE supported time formats */
	if((result = se_getTimeSyncVariantEx(ctx, &time_sync_variant)) != ExecutionOk)
		return printError(result, "se_getTimeSyncVariantEx", 0);

	/** Expected time sync variant is unixTime */
	if(time_sync_variant != unixTime)
	{
		printError((int) time_sync_variant, "supported time format", "not unixTime");
		return 1;
	}

	/** Get TSE update time interval */
	if((result = se_getTimeSyncIntervalEx(ctx, &time_sync_interval)) != ExecutionOk)
		return printError(result, "se_getTimeSyncIntervalEx", 0);

	/** Get wear indicator */
	if((result = se_getWearIndicatorEx(ctx, &wearIndicator)) != ExecutionOk)
		return printError(result, "se_getWearIndicatorEx", 0);

	/** see se_api_test.c for additional tests: */
		/** Signature counter tests - not fully supported before TSE v2, expect some ErrorFunctionNotSupported */
		/** get TSE signing certificate file, no TAR, see se_exportCertificates for TSE v1 */

	/** Get current transactions */
	if((result = se_getCurrentNumberOfTransactionsEx(ctx, &transactions)) != ExecutionOk)
		return printError(result, "se_getCurrentNumberOfTransactionsEx", 0);

	/** see se_api_test.c for additional tests: */
		/** Get currently active ERS (cash registers) */
		/** Get signature algorithm OID */

	/** Authenticate TimeAdmin and set the system time. This MUST be done on every power-up */
	/** Timeouts apply: TimeAdmin is automatically logged out after 2 seconds. */
	if((result = se_authenticateUserEx(ctx, PARAM_STR(TimeAdmin), PARAM_BA(m_timeAdminPin), &authResult, &tries_remaining)) != ExecutionOk)
		return printError(result, "se_authenticateUserEx", 0);

	if(authResult != authenticationOk)
	{
		printError((int) authResult, "TimeAdmin authentication", "authentication failed");
		printf(" => Tries remaining = %i\n", tries_remaining);
		return 1;
	}

	/** Set time and logout TimeAdmin */
	start_time = getTimestamp();
	if((result = se_updateTimeEx(ctx, start_time)) != ExecutionOk)
		return printError(result, "se_updateTimeEx", 0);

	if((result = se_logOutEx(ctx, PARAM_STR(TimeAdmin))) != ExecutionOk)
		/** Timeouts apply: TimeAdmin is automatically logged out after 2 seconds. */
		return printError(result, "se_logOutEx", "TimeAdmin logout failed");

	/** Get TSE life cycle state */
	if((result = se_getLifeCycleStateEx(ctx, &lcs)) != ExecutionOk)
		return printError(result, "se_getLifeCycleStateEx", 0);

	if(lcs != lcsActive)
	{
		printError((int) lcs, "life cycle state", "not Active");
		return 1;
	}

	/** check certificate expiration date */
	if((result = se_getCertificateExpirationDateEx(ctx, m_serialNumbers + 6, 32, &expiration_date)) != ExecutionOk)
		return printError(result, "se_getCertificateExpirationDateEx", 0);

	if(start_time > expiration_date)
	{
		printf(" => Certificate expired\n");
		printf("=> operationalTest: STOP\n");
		return 1;
	}

	/** get public key */
	if((result = se_exportPublicKeyEx(ctx, m_serialNumbers + 6, 32, PARAM_BUFFER(m_publicKey))) != ExecutionOk)
		return printError(result, "se_exportPublicKeyEx", 0);

	/** see se_api_test.c for additional tests: */
		/** TimeAdmin PIN unblock test */
		/** test ERS mapping */

	/** Start, update, finish transaction */
	{
		uint32_t num_tansactions = transactions;
		uint32_t transaction_counter;

		/* NOTE: maximum total command length is 8156 byte (8k - 36 byte MSC header) */
		uint8_t process_data[8096];
		memset(process_data, 42, sizeof(process_data));

		/** Start new transaction for ERS "clientId" */
		if((result = se_startTransactionEx(ctx, PARAM_STR(clientId), NULL, 0, PARAM_STR(processType), PARAM_STR2BA(additionalData), &m_startTransactionResult)) != ExecutionOk)
			return printError(result, "se_startTransactionEx", 0);

		if((result = se_getCurrentNumberOfTransactionsEx(ctx, &transactions)) != ExecutionOk)
			return printError(result, "se_getCurrentNumberOfTransactionsEx", 0);

		if(transactions != (num_tansactions + 1))
		{
			printError(transactions, "Number of transactions ", "unexpected");
			return 1;
		}

		/** Update transaction for ERS "clientId" */
		if((result = se_updateTransactionEx(ctx, PARAM_STR(clientId), m_startTransactionResult.transactionNumber, PARAM_BA(process_data), PARAM_STR(processType), &m_updateTransactionResult)) != ExecutionOk)
			return printError(result, "se_updateTransactionEx", 0);

		if((result = se_getCurrentNumberOfTransactionsEx(ctx, &transactions)) != ExecutionOk)
			return printError(result, "se_getCurrentNumberOfTransactionsEx", 0);

		if(transactions != (num_tansactions + 1))
		{
			printError(transactions, "Number of transactions ", "unexpected");
			return 1;
		}

		/** Get last log messages */
		if((result = se_readLogMessageEx(ctx, PARAM_BUFFER(m_lastLogMessage))) != ExecutionOk)
			return printError(result, "se_readLogMessageEx", 0);

		/** Get open transactions */
		if((result = se_getOpenTransactionsEx(ctx, PARAM_BUFFER(m_openTransactions))) != ExecutionOk)
			return printError(result, "se_getOpenTransactionsEx", 0);
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
		if((result = se_finishTransactionEx(ctx, PARAM_STR(clientId), m_startTransactionResult.transactionNumber, PARAM_STR2BA(processData), PARAM_STR(processType), PARAM_STR2BA(additionalData), &m_finishTransactionResult)) != ExecutionOk)
			return printError(result, "se_finishTransactionEx", 0);

		if((result = se_getCurrentNumberOfTransactionsEx(ctx, &transactions)) != ExecutionOk)
			return printError(result, "se_getCurrentNumberOfTransactionsEx", 0);

		if(transactions != num_tansactions)
		{
			printError(transactions, "Number of transactions ", "unexpected");
			return 1;
		}

		if((result = se_getTransactionCounterEx(ctx, &transaction_counter)) != ExecutionOk)
			return printError(result, "se_getTransactionCounterEx", 0);

		if(transaction_counter != m_startTransactionResult.transactionNumber)
		{
			printError(transaction_counter, "Transactions counter ", "unexpected");
			return 1;
		}
	}

	/** see se_api_test.c for additional tests: */
		/** get last signature counter */
		/** Filtered export data tests */
		/** Export certificates (tar) */
		/** Write certificates to tar-file */

	/** get total log memory */
	if((result = se_getTotalLogMemoryEx(ctx, &total_log_memory)) != ExecutionOk)
		return printError(result, "se_getTotalLogMemoryEx", 0);

	printf(" => Total log memory = 0x%08X%08X\n",
		(uint32_t)(total_log_memory >> 32), (uint32_t)(total_log_memory & SE_MAX_UINT32));

	/** get available log memory */
	if((result = se_getAvailableLogMemoryEx(ctx, &available_log_memory)) != ExecutionOk)
		return printError(result, "se_getAvailableLogMemoryEx", 0);

	printf(" => Available log memory = 0x%08X%08X\n",
		(uint32_t)(available_log_memory >> 32), (uint32_t)(available_log_memory & SE_MAX_UINT32));

	/** Unfiltered export data test */
#	if(EXPORT_ALL_LOGS_TEST != 0)
	{
		int i;
		/** see se_api_test.c for additional tests: */
			/** Export all transaction logs to tar-file via stream */
			/** Aborted export test (abort after 3 export callbacks) */

		char file_name[256];
		{
			memset(file_name, 0, sizeof(file_name));
			strcat(file_name, "exportViaCallback_TSE_");
			for(i = 0; i < ctx->serialNrLength; ++i)
			{
				sprintf(buf, "%02X", (int)(ctx->serialNr[i])); /* byte2hex */
				strcat(file_name, buf);
			}
			strcat(file_name, ".tar");
		}
		for(i = 0; i < EXPORT_ALL_LOGS_TEST; ++i)
		{
			/** Export all transaction logs to tar-file via callback */
			se_handle_t my_handle = (se_handle_t) 42;
			se_writer_t my_writer = myStreamWriter;

			printf(" => exportAll via callback: START\n");
			{
				/* full export test*/
				FILE* stream = fopen(file_name, "wb+");
				if(stream != NULL)
				{
					printf(" => Export target file '%s' has been opened\n", file_name);

					m_writerCount = 0;
					m_callbackStream = stream;

					result = se_exportDataViaCallbackEx(ctx, NULL, 0, SE_MAX_UINT32, 0, SE_MAX_UINT32, 0, SE_MAX_TIME, 0, my_writer, my_handle);
					fclose(stream);
					if(result != ExecutionOk)
						return printError(result, "se_exportDataViaCallbackEx", 0);
				}
			}
			printf(" => exportAll via callback: STOP\n");
		}
	}
#	endif

	/** Authenticate Admin - Timeouts apply: Admin is automatically logged out after 10 minutes. */
	if((result = se_authenticateUserEx(ctx, PARAM_STR(Admin), PARAM_BA(m_adminPin), &authResult, &tries_remaining)) != ExecutionOk)
		return printError(result, "se_authenticateUserEx", 0);

	if(authResult != authenticationOk)
	{
		printError((int) authResult, "Admin authentication", "authentication failed");
		printf(" => Tries remaining = %i\n", tries_remaining);
		return 1;
	}

	/** see se_api_test.c for additional tests: */
		/** Delete all logs up to finishTransaction signature counter (= StartT.counter + 2) */
		/** Disable TSE: this is irreversible - except for development samples !!! */

	if((result = se_logOutEx(ctx, PARAM_STR(Admin))) != ExecutionOk)
		return printError(result, "se_logOutEx", "Admin logout failed");

	printf("=> operationalTest: STOP\n");

	return 0;
}

/** ---------------------------------------------------------------------------
* Main test function.
*
* The test demonstrates the access of more than one TSE with the
* extended SE-API-EX-C using one context object for each TSE device.
*
* PLEASE NOTE:
*
* 1. The simultaneous access of two or more TSEs is out of scope of this sample!
*    The test program is single threaded, it holds an open connection to all input
*    TSEs but will never access more than one TSE at the same time. Nevertheless
*    the SE-API-EX-C is capable of simultaneous usage of TSE devices.
*
* 2. The SE-API-EX-C does NOT provide access synchronization of a single TSE!
*    This will be provided by a "comfort" SE-API (e.g. available in C++). For
*    more information please refer to tse-support.cryptovision.com.
*
* 3. For further functional test samples (e.g. unlocking a PIN, filtered data
*    export, aborted data export, usage of memory management callbacks, ...)
*    please refer to the SE-API-C test program ../se-api-c-test/se_api_test.c.
*/
int main(int argc, char* argv[])
{
	int i, test_result = 0;
	int num_tse = argc - 1;
	se_ctx_t* ctx_buf = NULL;

	if(num_tse < 1)
	{
		printf("Usage: use the TSE device paths separated by spaces as input (example 'E: F: G:')\n");
		return 0;
	}

	printf("--- se_api_ex_test START ---\n\n");

	/* 1. print API and implementation version */
	if((test_result = getApiVersion()) != 0)
		return test_result;

	/* 2. allocate TSE context array (one for each TSE) */
	if((ctx_buf = (se_ctx_t*) se_malloc(num_tse * sizeof(se_ctx_t))) == NULL)
		return printError(ErrorAllocationfailed, "se_malloc", "TSE context array allocation failed");

	/* 3. open and identify all TSEs (global m_certificationId output buffer is used) */
	for(i = 0; i < num_tse; ++i) 
	{
		int test_i_result = 0;
		const char* devicePath = (const char*) argv[i+1];

		/* context of the TSE[i] to be opened */
		se_ctx_t* tse_ctx = ctx_buf + i;

		printf("\n");
		printf("=> open TSE[%i]\n", i);
		printf("=> device Path: %s\n", devicePath);
			
		/* open TSE[i] */
		initOutputBuffers();
		{
			/* open SE transport IO (sends the Start command to the TSE[i]) */
			se_result_t result = se_openDirect2Ex(tse_ctx, devicePath, 0, SE_MAX_RESPONSE_8k, SE_DO_CHECK_INTEGRITY);
			if(result == ErrorSelftestFailed)
			{
				int i;
				printError(result, "se_openDirect2Ex", 0);
				/* in case of failed selftest during open, hex dump binary log, should be sent to backend for later reference */
				printf("Details: ");
				for(i = 0; i < tse_ctx->selfTestLogLength; i++)
					printf("%02X", *(tse_ctx->selfTestLog + i));
				printf("\n");
			}
			else if(result != ExecutionOk)
			{
				printError(result, "se_openDirect2Ex", 0);
				if(result == ErrorIO) printf("[OS error code = 0x%08X]\n", se_getOsStatusOfErrorIOEx(tse_ctx));
				++test_i_result;
			}
		
			/* get TSE Identifiers */
			if(test_i_result == 0) test_i_result += getTseIdentifier(tse_ctx);
		}
		freeOutputBuffers();
		test_result += test_i_result;

		/* print result */
		printf("=> TSE[%i] open result = %i (%s)\n", i, test_i_result, test_i_result == 0 ? "OK" : "Failed");
	}

	/* 4. test all open TSEs (global output buffers are used) */
	if(test_result == 0) 
	{
		for(i = 0; i < num_tse; ++i)
		{
			int test_i_result = 0;
			const char* devicePath = (const char*)argv[i + 1];

			/* context of the opened TSE[i] to be tested */
			se_ctx_t* tse_ctx = ctx_buf + i;

			printf("\n");
			printf("------------------------------------------------------------\n");
			printf("=> test TSE[%i]\n", i);
			printf("=> device Path: %s\n", devicePath);

			/* TSE accessing tests */
			initOutputBuffers();
			{
				/* run SE-API test functions */
				if(test_i_result == 0) test_i_result += firstBootTest(tse_ctx);
				if(test_i_result == 0) test_i_result += operationalTest(tse_ctx);
			}
			freeOutputBuffers();
			test_result += test_i_result;

			/* print result */
			printf("[myWriter count = %i]\n", m_writerCount);
			printf("=> TSE[%i] test result = %i (%s)\n", i, test_i_result, test_i_result == 0 ? "OK" : "Failed");
			printf("------------------------------------------------------------\n");
		}
	}

	/* 5. close all TSEs (no global output buffer usage) */
	for(i = 0; i < num_tse; ++i)
	{
		int test_i_result = 0;
		const char* devicePath = (const char*)argv[i + 1];

		/* context of the opened TSE[i] to be closed */
		se_ctx_t* tse_ctx = ctx_buf + i;

		printf("\n");
		printf("=> close TSE[%i]\n", i);
		printf("=> device Path: %s\n", devicePath);

		/* close TSE[i] */
		{
			se_result_t result;
			if((result = se_closeEx(tse_ctx)) != ExecutionOk)
			{
				printError(result, "se_closeEx", 0);
				if(result == ErrorIO) printf("[OS error code = 0x%08X]\n", se_getOsStatusOfErrorIOEx(tse_ctx));
				++test_i_result;
			}
		}
		test_result += test_i_result;

		/* print result */
		printf("=> TSE[%i] close result = %i (%s)\n", i, test_i_result, test_i_result == 0 ? "OK" : "Failed");
	}

	/* 6. free TSE context array */
	se_free(ctx_buf);

	/* 7. print total test result */
	printf("\n--- se_api_ex_test STOP ---\n\n");
	printf("------------------------------------------------------------\n");
	printf("Total test result = %i (%s)\n", test_result, test_result == 0 ? "OK" : "Failed");
	printf("------------------------------------------------------------\n");

	return test_result;
}
