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
 
#define _GNU_SOURCE
#define _DEFAULT_SOURCE

#include <assert.h>
#include <stdlib.h>
#include <string.h>

#include <time.h>

#include <se_api_ex.h>
#include <se_memory_util.h>


#include <se_types_ex.h>
#include <se_transport_ex.h>

#ifdef __cplusplus
extern "C" {
#endif

#include <fiscade.h>

/* ------------------------------------------------------------------------- */
int64_t getTimestamp()
{
	return (int64_t)(time(NULL));
}

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

WormError toWormError_i(se_result_t result) {
	switch (result) {
		case ExecutionOk: 								return WORM_ERROR_NOERROR;
		case ErrorMissingParameter:						return WORM_ERROR_INVALID_PARAMETER;
		case ErrorFunctionNotSupported:					return WORM_ERROR_CMD_NOT_FOUND;
		case ErrorAllocationfailed:						return WORM_ERROR_OUTOFMEM;
		case ErrorFileNotFound:							return WORM_ERROR_NO_WORM_CARD;
		case ErrorSECommunicationFailed:				return WORM_ERROR_UNKNOWN;
		case ErrorTSECommandDataInvalid:				return WORM_ERROR_TSE_INVALID_PARAMETER;
		case ErrorTSEResponseDataInvalid:				return WORM_ERROR_INVALID_RESPONSE;
		case ErrorTSEUnknownError:						return WORM_ERROR_UNKNOWN;
		case ErrorStreamWrite:							return WORM_ERROR_EXPORT_UNACKNOWLEDGED_DATA;
		case ErrorIO:									return WORM_ERROR_IO;
		case ErrorTSETimeout:							return WORM_ERROR_TIMEOUT;
		case ErrorBufferTooSmall:						return WORM_ERROR_OUTOFMEM;
		case ErrorCallback:								return WORM_ERROR_EXPORT_FAILED;
		case ErrorTSEFirmwareVersion:					return WORM_ERROR_FIRMWARE_UPDATE_NOT_APPLIED;
		case ErrorTransport:							return WORM_ERROR_INVALID_CMD_SYNTAX;
		case ErrorNoStartup:							return WORM_ERROR_POWER_CYCLE_DETECTED;
		case ErrorNoStorage:							return WORM_ERROR_STORE_FULL;
		case ErrorResponseHeader:						return WORM_ERROR_TSE_NO_RESPONSE_TO_FETCH;
		case ErrorStaleIO:								return WORM_ERROR_RESPONSE_MISSING;
		case ErrorResponseTooBig:						return WORM_ERROR_TSE_NO_RESPONSE_TO_FETCH;
		case ErrorAuthenticationFailed:					return WORM_ERROR_AUTHENTICATION_FAILED;
		case ErrorUnblockFailed:						return WORM_ERROR_AUTHENTICATION_FAILED;
		case ErrorRetrieveLogMessageFailed:				return WORM_ERROR_UNKNOWN;
		case ErrorStorageFailure:						return WORM_ERROR_STORE_FULL_INTERNAL;
		case ErrorUpdateTimeFailed:						return WORM_ERROR_UNKNOWN;
		case ErrorParameterMismatch:					return WORM_ERROR_TSE_INVALID_PARAMETER;
		case ErrorIdNotFound:							return WORM_ERROR_CLIENT_NOT_REGISTERED;
		case ErrorNoSuchKey:							return WORM_ERROR_TSE_INVALID_PARAMETER;
		case ErrorERSalreadyMapped:						return WORM_ERROR_TSE_INVALID_PARAMETER;
		case ErrorNoERS:								return WORM_ERROR_CLIENT_NOT_REGISTERED;
		case ErrorNoKey:								return WORM_ERROR_TSE_INVALID_PARAMETER;
		case ErrorTransactionNumberNotFound:			return WORM_ERROR_TSE_INVALID_PARAMETER;
		case ErrorNoDataAvailable:						return WORM_ERROR_EXPORT_NO_DATA_AVAILABLE;
		case ErrorTooManyRecords:						return WORM_ERROR_INVALID_PARAMETER;
		case ErrorStartTransactionFailed:				return WORM_ERROR_UNKNOWN;
		case ErrorUpdateTransactionFailed:				return WORM_ERROR_UNKNOWN;
		case ErrorFinishTransactionFailed:				return WORM_ERROR_UNKNOWN;
		case ErrorRestoreFailed:						return WORM_ERROR_UNKNOWN;
		case ErrorStoringInitDataFailed:				return WORM_ERROR_UNKNOWN;
		case ErrorExportCertFailed:						return WORM_ERROR_UNKNOWN;
		case ErrorNoLogMessage:							return WORM_ERROR_TSE_NO_RESPONSE_TO_FETCH;
		case ErrorReadingLogMessage:					return WORM_ERROR_TSE_NO_RESPONSE_TO_FETCH;
		case ErrorNoTransaction:						return WORM_ERROR_UNKNOWN;
		case ErrorSeApiNotInitialized:					return WORM_ERROR_TSE_NOT_INITIALIZED;
		case ErrorSeApiDeactivated:						return WORM_ERROR_WRONG_STATE_NEEDS_ACTIVE_CTSS;
		case ErrorSeApiNotDeactivated:					return WORM_ERROR_CMD_NOT_ALLOWED;
		case ErrorTimeNotSet:							return WORM_ERROR_NO_TIME_SET;
		case ErrorCertificateExpired:					return WORM_ERROR_CERTIFICATE_EXPIRED;
		case ErrorSecureElementDisabled:				return WORM_ERROR_TSE_DECOMMISSIONED;
		case ErrorUserNotAuthorized:					return WORM_ERROR_NOT_AUTHORIZED;
		case ErrorUserNotAuthenticated:					return WORM_ERROR_AUTHENTICATION_USER_NOT_LOGGED_IN;
		case ErrorDescriptionNotSetByManufacturer:		return WORM_ERROR_UNKNOWN;
		case ErrorDescriptionSetByManufacturer:			return WORM_ERROR_TSE_INVALID_PARAMETER;
		case ErrorExportSerialNumbersFailed:			return WORM_ERROR_UNKNOWN;
		case ErrorGetMaxNumberOfClientsFailed:			return WORM_ERROR_UNKNOWN;
		case ErrorGetCurrentNumberOfClientsFailed:		return WORM_ERROR_UNKNOWN;
		case ErrorGetMaxNumberTransactionsFailed:		return WORM_ERROR_UNKNOWN;
		case ErrorGetCurrentNumberOfTransactionsFailed: return WORM_ERROR_UNKNOWN;
		case ErrorGetSupportedUpdateVariantsFailed:		return WORM_ERROR_UNKNOWN;
		case ErrorDeleteStoredDataFailed:				return WORM_ERROR_UNKNOWN;
		case ErrorUnexportedStoredData:					return WORM_ERROR_EXPORT_UNACKNOWLEDGED_DATA;
		case ErrorSigningSystemOperationDataFailed:		return WORM_ERROR_UNKNOWN;
		case ErrorUserIdNotManaged:						return WORM_ERROR_UNKNOWN;
		case ErrorUserIdNotAuthenticated:				return WORM_ERROR_AUTHENTICATION_USER_NOT_LOGGED_IN;
		case ErrorDisableSecureElementFailed:			return WORM_ERROR_UNKNOWN;
		case ErrorSelftestFailed:						return WORM_ERROR_SELF_TEST_FAILED_FW;
		default:										return WORM_ERROR_UNKNOWN;
	}
}

WormError toWormError(se_ctx_t* ctx, se_result_t result) {
	uint32_t io = 0;
	if(result == ErrorIO && ctx != NULL)
		io = se_getOsStatusOfErrorIOEx(ctx);

	WormError r = toWormError_i(result);
#if DEBUG
	if(result != ExecutionOk)
		printf("toWormError 0x%04X / %s (%d) -> 0x%04X / %d\n", result, errorToString(result), io, r, r);
#endif

	return r;
}

/* ------------------------------------------------------------------------- */
WORMAPI const char* WORMAPI_CALL worm_getVersion(void)
{
	return se_getImplementationVersionStringEx();
}
WORMAPI const char* WORMAPI_CALL worm_signatureAlgorithm(void)
{
	// FIXME: no context - can't query TSE (but it is fix for all known versions)
	return "ECDSA-SHA256";
}
WORMAPI const char* WORMAPI_CALL worm_logTimeFormat(void)
{
	// FIXME: no context - can't query TSE (but it is fix for all known versions)
	return "unixTime";
}

WORMAPI WormError WORMAPI_CALL worm_init(WormContext** context, const char* mountPoint)
{
#if DEBUG
	printf("hello cv %s\n", mountPoint);
#endif

	*context = se_malloc(sizeof(WormContext));
	if(*context == NULL)
		return toWormError(NULL, ErrorAllocationfailed);

	(*context)->se = se_malloc(sizeof(se_ctx_t));
	if((*context)->se == NULL)
		return toWormError(NULL, ErrorAllocationfailed);

	(*context)->lastTransactionResponse = NULL;

	return toWormError((*context)->se, se_openDirect2Ex((*context)->se, mountPoint, 0, 0, SE_DO_CHECK_INTEGRITY));
}

WORMAPI WormError WORMAPI_CALL worm_cleanup(WormContext* context)
{
	if(context)
	{
		se_free(context->se);
		if(context->lastTransactionResponse)
		{
			se_free(context->lastTransactionResponse->serialNumber);
			se_free(context->lastTransactionResponse->signature);
		}
	}
	se_free(context);
	return WORM_ERROR_NOERROR;
}

WORMAPI WormInfo* WORMAPI_CALL worm_info_new(WormContext* context)
{
	WormInfo* info = se_malloc(sizeof(WormInfo));
	if(info == NULL)
		return NULL;

	info->context = context;

	return info;
}
WORMAPI void WORMAPI_CALL worm_info_free(WormInfo* info)
{
	se_free(info);
}
WORMAPI WormError WORMAPI_CALL worm_info_read(WormInfo* info)
{
	se_result_t result = ExecutionOk;

	info->customizationIdentifier = strdup("cryptovision");

	if((result = se_getPinStatusEx(info->context->se, &info->pin_state)) != ExecutionOk)
		return toWormError(info->context->se, result);

	info->timeSyncInterval = 1800;
	if((result = se_getTimeSyncIntervalEx(info->context->se, &info->timeSyncInterval)) != ExecutionOk && result != ErrorSeApiNotInitialized)
		return toWormError(info->context->se, result);

	info->signatureCounter = 0;
	if((result = se_getSignatureCounter1Ex(info->context->se, &info->signatureCounter)) != ExecutionOk && result != ErrorSeApiNotInitialized)
		return toWormError(info->context->se, result);

	if((result = se_getLifeCycleStateEx(info->context->se, &info->lcs)) != ExecutionOk)
		return toWormError(info->context->se, result);

	if((result = se_isEngineeringSampleEx(info->context->se, &info->isEngineeringSample)) != ExecutionOk)
		return toWormError(info->context->se, result);

	if((result = se_getTotalLogMemoryEx(info->context->se, &info->sizeOfMemory)) != ExecutionOk)
		return toWormError(info->context->se, result);

	if((result = se_getAvailableLogMemoryEx(info->context->se, &info->freeMemory)) != ExecutionOk)
		return toWormError(info->context->se, result);

	info->maxNumberTransactions = 320;
	if((result = se_getMaxNumberOfTransactionsEx(info->context->se, &info->maxNumberTransactions)) != ExecutionOk && result != ErrorSeApiNotInitialized)
		return toWormError(info->context->se, result);

	info->currentNumberTransactions = 0;
	if((result = se_getCurrentNumberOfTransactionsEx(info->context->se, &info->currentNumberTransactions)) != ExecutionOk && result != ErrorSeApiNotInitialized)
		return toWormError(info->context->se, result);

	info->publicKey = NULL;
	info->publicKeyLength = 0;
	if((result = se_exportPublicKeyEx(info->context->se, NULL, 0, &info->publicKey, &info->publicKeyLength)) != ExecutionOk && result != ErrorSeApiNotInitialized)
		return toWormError(info->context->se, result);

	info->serialNumber = NULL;
	info->serialNumberLength = 0;
	if((result = se_exportSerialNumbersEx(info->context->se, &info->serialNumber, &info->serialNumberLength)) != ExecutionOk && result != ErrorSeApiNotInitialized)
		return toWormError(info->context->se, result);

	if((result = se_getCertificationIdEx(info->context->se, &info->description, &info->descriptionLength)) != ExecutionOk)
		return toWormError(info->context->se, result);
	// cut off the year
	info->descriptionLength -= 5;
	info->description[info->descriptionLength] = '\0';

	info->numberOfClients = 0;
	// this is not what this API is expected to do:
	// if((result = se_getCurrentNumberOfClientsEx(info->context->se, &info->numberOfClients)) != ExecutionOk)
	//	return toWormError(info->context->se, result);
	// but:
	char** clientsData = NULL;
	uint32_t clientsLength = 0;
	if((result = se_listClientsEx(info->context->se, &clientsData, &info->numberOfClients)) != ExecutionOk && result != ErrorSECommunicationFailed)
		return toWormError(info->context->se, result);
	else if(result != ErrorSECommunicationFailed)
		se_free(*clientsData);

	info->maxNumberOfClients = 128;
	if((result = se_getMaxNumberOfClientsEx(info->context->se, &info->maxNumberOfClients)) != ExecutionOk && result != ErrorSeApiNotInitialized)
		return toWormError(info->context->se, result);

	info->expirationDate = 0;
	if((result = se_getCertificateExpirationDate1Ex(info->context->se, &info->expirationDate)) != ExecutionOk && result != ErrorSeApiNotInitialized)
		return toWormError(info->context->se, result);

	info->exportSize = 0;
	if((result = se_getExportSize1Ex(info->context->se, 0, 0, &info->exportSize)) != ExecutionOk && result != ErrorSeApiNotInitialized)
		return toWormError(info->context->se, result);

	info->formFactor = "uSD";

	return WORM_ERROR_NOERROR;
}
WORMAPI void WORMAPI_CALL worm_info_customizationIdentifier(const WormInfo* info, const unsigned char** id, int* idLength)
{
	*id = (const unsigned char*) (info->customizationIdentifier);
	*idLength = strlen(info->customizationIdentifier);
}
WORMAPI int WORMAPI_CALL worm_info_isDevelopmentFirmware(const WormInfo* info)
{
	return info->isEngineeringSample;
}
WORMAPI uint32_t WORMAPI_CALL worm_info_capacity(const WormInfo* info)
{
	// NOTE: "*4" somehow maps to comparable values - "in blocks"
	return info->sizeOfMemory * 4 / 512;
}
WORMAPI uint32_t WORMAPI_CALL worm_info_size(const WormInfo* info)
{
	// NOTE: "*4" somehow maps to comparable values - "in blocks"
	return info->freeMemory * 4 / 512;
}
WORMAPI int WORMAPI_CALL worm_info_hasValidTime(const WormInfo* info)
{
	// FIXME: we don't know exactly here...
	return info->lcs != lcsNoTime;
}

WORMAPI int WORMAPI_CALL worm_info_hasPassedSelfTest(const WormInfo* info)
{
	// FIXME: we currently can't get here if the initial selftest during open failed
	return 1;
}
WORMAPI int WORMAPI_CALL worm_info_isCtssInterfaceActive(const WormInfo* info)
{
	return info->lcs == lcsNoTime || info->lcs == lcsActive;
}
WORMAPI int WORMAPI_CALL worm_info_isExportEnabledIfCspTestFails(const WormInfo* info)
{
	return 1;
}
WORMAPI WormInitializationState WORMAPI_CALL worm_info_initializationState(const WormInfo* info)
{
	switch(info->lcs) {
	case lcsDisabled: return Decommissioned;
	case lcsNotInitialized: return Uninitialized;
	case lcsNoTime:
	case lcsActive:
	case lcsDeactivated: return Initialized;
	default: return InitStateUnknown;
	}
}
WORMAPI int WORMAPI_CALL worm_info_isDataImportInProgress(const WormInfo* info)
{
	// no import implemented
	return 0;
}
WORMAPI int WORMAPI_CALL worm_info_hasChangedPuk(const WormInfo* info)
{
	// combination of both cryptovision TSE PUKs' states
	return ((info->pin_state & adminPukTransportState) == 0) && ((info->pin_state & timeAdminPukTransportState) == 0);
}
WORMAPI int WORMAPI_CALL worm_info_hasChangedAdminPin(const WormInfo* info)
{
	return (info->pin_state & adminPinTransportState) == 0;
}
WORMAPI int WORMAPI_CALL worm_info_hasChangedTimeAdminPin(const WormInfo* info)
{
	return (info->pin_state & timeAdminPinTransportState) == 0;
}
WORMAPI uint32_t WORMAPI_CALL worm_info_timeUntilNextSelfTest(const WormInfo* info)
{
	// no explicit selftest needed
	return UINT32_MAX;
}
WORMAPI uint32_t WORMAPI_CALL worm_info_startedTransactions(const WormInfo* info)
{
	return info->currentNumberTransactions;
}
WORMAPI uint32_t WORMAPI_CALL worm_info_maxStartedTransactions(const WormInfo* info)
{
	return info->maxNumberTransactions;
}
WORMAPI uint32_t WORMAPI_CALL worm_info_createdSignatures(const WormInfo* info)
{
	return info->signatureCounter;
}
WORMAPI uint32_t WORMAPI_CALL worm_info_maxSignatures(const WormInfo* info)
{
	return MAX_SIGNATURES;
}
WORMAPI uint32_t WORMAPI_CALL worm_info_remainingSignatures(const WormInfo* info)
{
	if(info->signatureCounter > MAX_SIGNATURES)
		return 0;
	else
		return MAX_SIGNATURES - info->signatureCounter;
}
WORMAPI uint32_t WORMAPI_CALL worm_info_maxTimeSynchronizationDelay(const WormInfo* info)
{
	return info->timeSyncInterval;
}
WORMAPI uint32_t WORMAPI_CALL worm_info_maxUpdateDelay(const WormInfo* info)
{
	return 45;
}
WORMAPI void WORMAPI_CALL worm_info_tsePublicKey(const WormInfo* info, const unsigned char** publicKey, worm_uint *publicKeyLength)
{
	*publicKey = info->publicKey;
	*publicKeyLength = info->publicKeyLength;
}
WORMAPI void WORMAPI_CALL worm_info_tseSerialNumber(const WormInfo* info, const unsigned char** serialNumber,worm_uint *serialNumberLength)
{
	*serialNumber = (info->serialNumber) ? info->serialNumber + 6 : NULL;
	*serialNumberLength = (info->serialNumber) ? 32 : 0;
}
WORMAPI const char* WORMAPI_CALL worm_info_tseDescription(const WormInfo* info)
{
	return info->description;
}
WORMAPI uint32_t WORMAPI_CALL worm_info_registeredClients(const WormInfo* info)
{
	return info->numberOfClients;
}
WORMAPI uint32_t WORMAPI_CALL worm_info_maxRegisteredClients(const WormInfo* info)
{
	return info->maxNumberOfClients;
}
WORMAPI worm_uint WORMAPI_CALL worm_info_certificateExpirationDate(const WormInfo* info)
{
	return info->expirationDate;
}
WORMAPI worm_uint WORMAPI_CALL worm_info_tarExportSizeInSectors(const WormInfo* info)
{
	return info->exportSize / 512;
}
WORMAPI uint64_t worm_info_tarExportSize(const WormInfo* info)
{
	return info->exportSize;
}
WORMAPI uint32_t WORMAPI_CALL worm_info_hardwareVersion(const WormInfo* info)
{
	se_tse_version_t version = se_getHardwareVersionEx(info->context->se);
	return version == version1 ? 0x010000 : 0x020000;
}
WORMAPI uint32_t WORMAPI_CALL worm_info_softwareVersion(const WormInfo* info)
{
	se_tse_version_t version = se_getHardwareVersionEx(info->context->se);
	return version == version1 ? 0x010000 : version == version2 ? 0x020000 : 0x020100;
}
WORMAPI const char* WORMAPI_CALL worm_info_formFactor(const WormInfo* info)
{
	return info->formFactor;
}

WORMAPI WormError WORMAPI_CALL worm_flash_health_summary(
			WormContext* context, uint32_t* uncorrectableEccErrors,
			uint8_t* percentageRemainingSpareBlocks,
			uint8_t* percentageRemainingEraseCounts,
			uint8_t* percentageRemainingTenYearsDataRetention)
{
	se_result_t result = ExecutionOk;

	uint32_t wearIndicator = 0;
	if((result = se_getWearIndicatorEx(context->se, &wearIndicator)) != ExecutionOk)
		return toWormError(context->se, result);

	// this is only a very rough mapping
	if(uncorrectableEccErrors)                   *uncorrectableEccErrors = 0;
	if(percentageRemainingSpareBlocks)           *percentageRemainingSpareBlocks = 100;
	if(percentageRemainingEraseCounts)           *percentageRemainingEraseCounts = 100 - wearIndicator;
	if(percentageRemainingTenYearsDataRetention) *percentageRemainingTenYearsDataRetention = 100 - wearIndicator;

	return WORM_ERROR_NOERROR;
}
WORMAPI int WORMAPI_CALL worm_flash_health_needs_replacement(
	uint32_t uncorrectableEccErrors, uint8_t percentageRemainingSpareBlocks,
	uint8_t percentageRemainingEraseCounts)
{
	return percentageRemainingEraseCounts < 2;
}

WORMAPI WormError WORMAPI_CALL worm_tse_factoryReset(WormContext* context)
{
	fprintf(stderr, "NOTE: factory reset only implemented in Java - use cv tools!\n");
	return WORM_ERROR_UNKNOWN;
}

/*
 * https://support.gastro-mis.de/support/solutions/articles/36000170390-erste-schritte-bei-der-anbindung

Die Setup-Methode ist eine Hilfsmethode die folgenden Aufrufe beinhaltet:

worm_user_change_puk
worm_user_change_pin
worm_tse_ers_enable
worm_tse_registerClient
worm_tse_runSelfTest
worm_tse_initialize
*/
WORMAPI WormError WORMAPI_CALL worm_tse_setup(
			WormContext* context, const unsigned char* credentialSeed,
			int credentialSeedLength, const unsigned char* adminPuk,
			int adminPukLength, const unsigned char* adminPin,
			int adminPinLength, const unsigned char* timeAdminPin,
			int timeAdminPinLength, const char* clientId)
{
	se_result_t result = ExecutionOk;

	if((result = se_initializePinValuesEx(context->se, adminPin, adminPinLength, adminPuk, adminPukLength, timeAdminPin, timeAdminPinLength, adminPuk, adminPukLength)) != ExecutionOk)
		return toWormError(context->se, result);

	se_authentication_result_t authenticationResult;
	int16_t remainingRetries = 0;
	if((result = se_authenticateUserEx(context->se, "Admin", 5, adminPin, adminPinLength, &authenticationResult, &remainingRetries)) != ExecutionOk)
		return toWormError(context->se, result);

	if((result = se_initializeEx(context->se)) != ExecutionOk)
		return toWormError(context->se, result);

	if((result = se_updateTimeEx(context->se, getTimestamp())) != ExecutionOk)
		return toWormError(context->se, result);

	if((result = se_registerClientEx(context->se, clientId, strlen(clientId))) != ExecutionOk)
		return toWormError(context->se, result);

	return WORM_ERROR_NOERROR;
}

WORMAPI WormError WORMAPI_CALL worm_tse_ctss_enable(WormContext* context)
{
	return toWormError(context->se, se_activateTSEEx(context->se));
}
WORMAPI WormError WORMAPI_CALL worm_tse_ctss_disable(WormContext* context)
{
	return toWormError(context->se, se_deactivateTSEEx(context->se));
}

WORMAPI WormError WORMAPI_CALL worm_tse_initialize(WormContext* context)
{
	return toWormError(context->se, se_initializeEx(context->se));
}
WORMAPI WormError WORMAPI_CALL worm_tse_decommission(WormContext* context)
{
	return toWormError(context->se, se_disableSecureElementEx(context->se));
}

WORMAPI WormError WORMAPI_CALL worm_tse_updateTime(WormContext* context, worm_uint timestamp)
{
	return toWormError(context->se, se_updateTimeEx(context->se, timestamp));
}

WORMAPI WormError WORMAPI_CALL worm_tse_firmwareUpdate_transfer(
	WormContext* context, uint32_t chunkOffset, const unsigned char* chunkData,
	int chunkLength)
{
	// use cryptovision tools to apply cryptovision updates...
	return WORM_ERROR_UNKNOWN;
}
WORMAPI WormError WORMAPI_CALL worm_tse_firmwareUpdate_apply(WormContext* context, uint32_t fwSize)
{
	// use cryptovision tools to apply cryptovision updates...
	return WORM_ERROR_UNKNOWN;
}

WORMAPI WormError WORMAPI_CALL worm_tse_enableExportIfCspTestFails(WormContext* context)
{
	return WORM_ERROR_NOERROR;
}
WORMAPI WormError WORMAPI_CALL worm_tse_disableExportIfCspTestFails(WormContext* context)
{
	// not applicable - always enabled
	return WORM_ERROR_UNKNOWN;
}

WORMAPI WormError WORMAPI_CALL worm_tse_runSelfTest(WormContext* context, const char* clientId)
{
	// we can implement something here - but is it useful?

	se_result_t result = ExecutionOk;

	se_self_test_result_t testresult;
	if((result = se_selfTestEx(context->se, 10, &testresult)) != ExecutionOk)
		return toWormError(context->se, result);

	if(testresult.errorsFound)
		return WORM_ERROR_SELF_TEST_FAILED_FW;
	else
		return WORM_ERROR_NOERROR;
}

WORMAPI WormError WORMAPI_CALL worm_tse_registerClient(WormContext* context, const char* clientId)
{
	return toWormError(context->se, se_registerClientEx(context->se, clientId, strlen(clientId)));
}
WORMAPI WormError WORMAPI_CALL worm_tse_deregisterClient(WormContext* context, const char* clientId)
{
	return toWormError(context->se, se_deregisterClientEx(context->se, clientId, strlen(clientId)));
}
WORMAPI WormError WORMAPI_CALL worm_tse_listRegisteredClients(WormContext* context, int toSkip, WormRegisteredClients* clients)
{
	se_result_t result = ExecutionOk;

	char** clientsData = NULL;
	uint32_t clientsLength = 0;
	if((result = se_listClientsEx(context->se, &clientsData, &clientsLength)) != ExecutionOk)
		return toWormError(context->se, result);

	if(toSkip >= clientsLength)
	{
		se_free(clientsData);
		return WORM_ERROR_INVALID_PARAMETER;
	}

	if(clientsLength > toSkip + 16)
		clientsLength = toSkip + 16;
	clients->amount = clientsLength - toSkip;
	for(int i = toSkip; i < clientsLength; i++)
	{
		memcpy(&clients->clientIds[i][0], clientsData[i], strlen(clientsData[i])+1);
		se_free(clientsData[i]);
	}

	return WORM_ERROR_NOERROR;
}

const char* user(WormUserId id)
{
	switch (id) {
		case WORM_USER_ADMIN: return "Admin";
		case WORM_USER_TIME_ADMIN: return "TimeAdmin";
		default: return NULL;
	}
}

WORMAPI WormError WORMAPI_CALL worm_user_login(WormContext* context,
			WormUserId id, const unsigned char* pin, int pinLength,
			int* remainingRetries)
{
	se_result_t result = ExecutionOk;
	se_authentication_result_t authenticationResult;
	int16_t triesLeft = 0;

	result = se_authenticateUserEx(context->se, user(id), strlen(user(id)), pin, pinLength, &authenticationResult, &triesLeft);
	if(remainingRetries)
		*remainingRetries = triesLeft;

	switch(authenticationResult)
	{
	case authenticationUnknownUserId:
	case authenticationError: return WORM_ERROR_UNKNOWN;
	case authenticationFailed: return WORM_ERROR_AUTHENTICATION_FAILED;
	case authenticationPinIsBlocked: return WORM_ERROR_AUTHENTICATION_PIN_BLOCKED;
	case authenticationOk: break;
	}

	return toWormError(context->se, result);
}
WORMAPI WormError WORMAPI_CALL worm_user_logout(WormContext* context, WormUserId id)
{
	return toWormError(context->se, se_logOutEx(context->se, user(id), strlen(user(id))));
}
WORMAPI WormError WORMAPI_CALL worm_user_unblock(WormContext* context, WormUserId id, const unsigned char* puk,
			int pukLength, const unsigned char* newPin, int newPinLength,
			int* remainingRetries)
{
	se_result_t result = ExecutionOk;
	se_unblock_result_t unblockResult;

	result = se_unblockUserEx(context->se, user(id), strlen(user(id)), puk, pukLength, newPin, newPinLength, &unblockResult);

	switch(unblockResult)
	{
	case unblockUnknownUserId:
	case unblockError:
	case unblockFailed: return WORM_ERROR_UNKNOWN;
	case unblockPinIsBlocked: return WORM_ERROR_AUTHENTICATION_PIN_BLOCKED;
	case unblockOk: break;
	}

	if(remainingRetries)
		*remainingRetries =
				unblockResult == unblockPinIsBlocked ? 0 :
				unblockResult == unblockFailed ? 1 : // FIXME: this is somehow close but might be off either way!
				unblockResult == unblockOk ? 5 :
					-1; // we simply don't know...

	return toWormError(context->se, result);
}
WORMAPI WormError WORMAPI_CALL worm_user_change_puk(
			WormContext* context, const unsigned char* puk, int pukLength,
			const unsigned char* newPuk, int newPukLength, int* remainingRetries)
{
	// not available - PUK cannot be changed, only initialized once

	se_result_t result = ExecutionOk;

	if((result = se_initializePukEx(context->se, "Admin", 5, newPuk, newPukLength)) != ExecutionOk)
		return toWormError(context->se, result);

	if((result = se_initializePukEx(context->se, "TimeAdmin", 9, newPuk, newPukLength)) != ExecutionOk)
		return toWormError(context->se, result);

	return WORM_ERROR_NOERROR;
}
WORMAPI WormError WORMAPI_CALL worm_user_change_pin(
			WormContext* context, WormUserId id, const unsigned char* pin,
			int pinLength, const unsigned char* newPin, int newPinLength,
			int* remainingRetries)
{
	// not available - use unblock()
	return WORM_ERROR_UNKNOWN;
}

WORMAPI WormError WORMAPI_CALL worm_user_deriveInitialCredentials(
			WormContext* context, const unsigned char* seed, int seedLength,
			unsigned char* initialAdminPuk, int initialAdminPukLength,
			unsigned char* initialAdminPin, int initialAdminPinLength,
			unsigned char* initialTimeAdminPin, int initialTimeAdminPinLength)
{
	// PUK cannot be changed once set - what to do here? - will not be used in changePuk()
	memset(initialAdminPuk, '0', initialAdminPukLength);

	// those are completely useless... - you cannot use worm_user_change_pin()!
	memset(initialAdminPin, '0', initialAdminPinLength);
	memset(initialTimeAdminPin, '0', initialTimeAdminPinLength);

	return WORM_ERROR_NOERROR;
}

// FIXME: better read it later on from storage...
void cacheResponse(WormContext* context, WormTransactionResponse* response, const char* clientId)
{
	if(context->lastTransactionResponse == NULL)
	{
		context->lastTransactionResponse = worm_transaction_response_new(context);
		if(context->lastTransactionResponse == NULL)
			// failed
			return;

		context->lastTransactionResponse->serialNumber = se_malloc(response->serialNumberLength);
		context->lastTransactionResponse->signature = se_malloc(response->signatureLength + 6);
	}

	WormTransactionResponse* c = context->lastTransactionResponse;

	memcpy(c->serialNumber, response->serialNumber, response->serialNumberLength);
	memcpy(c->signature, response->signature, response->signatureLength);
	c->logTime = response->logTime;
	c->serialNumberLength = response->serialNumberLength;
	c->signatureCounter = response->signatureCounter;
	c->signatureLength = response->signatureLength;
	c->transactionNumber = response->transactionNumber;

	strncpy(context->lastClientId, clientId, sizeof(context->lastClientId));
}
WORMAPI WormError WORMAPI_CALL worm_transaction_start(
			WormContext* context, const char* clientId,
			const unsigned char* processData, worm_uint processDataLength,
			const char* processType, WormTransactionResponse* response)
{
	se_result_t result = ExecutionOk;

	se_start_transaction_result_t transactionResult;
	if((result = se_startTransactionEx(context->se, clientId, strlen(clientId), processData, processDataLength, processType, strlen(processType), NULL, 0, &transactionResult)) != ExecutionOk)
		return toWormError(context->se, result);

	response->logTime = transactionResult.logTime;
	response->serialNumber = transactionResult.serialNumber;
	response->serialNumberLength = transactionResult.serialNumberLength;
	response->signature = transactionResult.signatureValue;
	response->signatureLength = transactionResult.signatureValueLength;
	response->signatureCounter = transactionResult.signatureCounter;
	response->transactionNumber = transactionResult.transactionNumber;

	cacheResponse(context, response, clientId);

	return WORM_ERROR_NOERROR;
}
WORMAPI WormError WORMAPI_CALL worm_transaction_update(
			WormContext* context, const char* clientId, worm_uint transactionNumber,
			const unsigned char* processData, worm_uint processDataLength,
			const char* processType, WormTransactionResponse* response)
{
	se_result_t result = ExecutionOk;

	se_update_transaction_result_t transactionResult;
	if((result = se_updateTransactionEx(context->se, clientId, strlen(clientId), transactionNumber, processData, processDataLength, processType, strlen(processType), &transactionResult)) != ExecutionOk)
		return toWormError(context->se, result);

	response->logTime = transactionResult.logTime;
	response->serialNumber = transactionResult.serialNumber;
	response->serialNumberLength = transactionResult.serialNumberLength;
	response->signature = transactionResult.signatureValue;
	response->signatureLength = transactionResult.signatureValueLength;
	response->signatureCounter = transactionResult.signatureCounter;
	response->transactionNumber = transactionNumber;

	cacheResponse(context, response, clientId);

	return WORM_ERROR_NOERROR;
}
WORMAPI WormError WORMAPI_CALL worm_transaction_finish(
			WormContext* context, const char* clientId, worm_uint transactionNumber,
			const unsigned char* processData, worm_uint processDataLength,
			const char* processType, WormTransactionResponse* response)
{
	se_result_t result = ExecutionOk;

	se_finish_transaction_result_t transactionResult;
	if((result = se_finishTransactionEx(context->se, clientId, strlen(clientId), transactionNumber, processData, processDataLength, processType, strlen(processType), NULL, 0, &transactionResult)) != ExecutionOk)
		return toWormError(context->se, result);

	response->logTime = transactionResult.logTime;
	response->serialNumber = transactionResult.serialNumber;
	response->serialNumberLength = transactionResult.serialNumberLength;
	response->signature = transactionResult.signatureValue;
	response->signatureLength = transactionResult.signatureValueLength;
	response->signatureCounter = transactionResult.signatureCounter;
	response->transactionNumber = transactionNumber;

	cacheResponse(context, response, clientId);

	return WORM_ERROR_NOERROR;
}

WORMAPI WormError WORMAPI_CALL worm_transaction_lastResponse(WormContext* context, const char* clientId, WormTransactionResponse* response)
{
	/* not what is meant here...
	uint8_t* logMessage = NULL;
	uint32_t logMessageLength;

	se_result_t result = ExecutionOk;
	if((result = se_readLogMessageEx(context, &logMessage, &logMessageLength)) != ExecutionOk)
		return toWormError(context, result);
	*/

	if(   (clientId != NULL && strlen(clientId) != 0 && (strlen(context->lastClientId) != strlen(clientId) || strcmp(context->lastClientId, clientId) != 0))
		|| response == NULL)
		return WORM_ERROR_INVALID_PARAMETER;

	WormTransactionResponse* c = context->lastTransactionResponse;

	response->logTime = c->logTime;
	response->serialNumberLength = c->serialNumberLength;
	response->signatureCounter = c->signatureCounter;
	response->signatureLength = c->signatureLength;
	response->transactionNumber = c->transactionNumber;

	memcpy(response->serialNumber, c->serialNumber, c->serialNumberLength);
	memcpy(response->signature, c->signature, c->signatureLength);

	return WORM_ERROR_NOERROR;
}

WORMAPI WormError WORMAPI_CALL worm_transaction_listStartedTransactions(
			WormContext* context, const char* clientId, int toSkip,
			worm_uint* transactionNumbers, int transactionNumbersLength,
			int* storedTransactionNumbers)
{
	if(clientId && strlen(clientId))
		// FIXME: unimplemented by cryptovision
		return WORM_ERROR_UNKNOWN;

	se_result_t result = ExecutionOk;

	uint32_t* numbers = NULL;
	uint32_t transactionNumbersLen = 0;
	if((result = se_getOpenTransactionsEx(context->se, &numbers, &transactionNumbersLen)) != ExecutionOk)
		return toWormError(context->se, result);

	if(toSkip >= transactionNumbersLen)
	{
		se_free(numbers);
		return WORM_ERROR_INVALID_PARAMETER;
	}

	if(transactionNumbersLen > toSkip + transactionNumbersLength)
		transactionNumbersLen = toSkip + transactionNumbersLength;
	*storedTransactionNumbers = transactionNumbersLen - toSkip;
	for(int i = toSkip; i < transactionNumbersLen; i++)
		transactionNumbers[i] = numbers[i];

	return WORM_ERROR_NOERROR;
}

WORMAPI WormTransactionResponse* WORMAPI_CALL worm_transaction_response_new(WormContext* context)
{
	WormTransactionResponse* response = se_malloc(sizeof(WormTransactionResponse));
	if(response == NULL)
		return NULL;

	memset(response, 0, sizeof(WormTransactionResponse));

	return response;
}
WORMAPI void WORMAPI_CALL worm_transaction_response_free(WormTransactionResponse* response)
{
	se_free(response);
}
WORMAPI worm_uint WORMAPI_CALL worm_transaction_response_logTime(const WormTransactionResponse* response)
{
	return response->logTime;
}
WORMAPI void WORMAPI_CALL worm_transaction_response_serialNumber(const WormTransactionResponse* response, const unsigned char** serialNumber,worm_uint* serialNumberLength)
{
	if(*serialNumberLength >= response->serialNumberLength)
	{
		memcpy(serialNumber, response->serialNumber, response->serialNumberLength);
		*serialNumberLength = response->serialNumberLength;
	}
}
WORMAPI worm_uint WORMAPI_CALL worm_transaction_response_signatureCounter(const WormTransactionResponse* response)
{
	return response->signatureCounter;
}
WORMAPI void WORMAPI_CALL worm_transaction_response_signature(const WormTransactionResponse* response, const unsigned char** signature, worm_uint* signatureLength)
{
	if(*signatureLength >= response->signatureLength)
	{
		memcpy(signature, response->signature, response->signatureLength);
		*signatureLength = response->signatureLength;
	}
}
WORMAPI worm_uint WORMAPI_CALL worm_transaction_response_transactionNumber(const WormTransactionResponse* response)
{
	return response->transactionNumber;
}

WORMAPI WormEntry* WORMAPI_CALL worm_entry_new(WormContext* context)
{
	WormEntry* entry = se_malloc(sizeof(WormEntry));
	if(entry == NULL)
		return NULL;

	memset(entry, 0, sizeof(WormEntry));
	entry->context = context;

	return entry;
}
WORMAPI void WORMAPI_CALL worm_entry_free(WormEntry* entry)
{
	se_free(entry->logMessage);
	se_free(entry);

}
uint32_t blen(uint8_t* p)
{
	p++;
	if((*p & 0x80) == 0)
		return *p;
	if((*p & 0x7F) == 1)
		return *(p+1);
	if((*p & 0x7F) == 2)
		return (*(p+1) << 8) + *(p+2);

	return -1;
}
uint8_t* val(uint8_t* p)
{
	p++;
	if((*p & 0x80) == 0)
		p++;
	else
		p += 1 + (*p & 0x7F);

	return p;
}
uint8_t* skip(uint8_t* p)
{
	return val(p) + blen(p);
}

void worm_entry_from_log(WormEntry* entry, uint8_t* data, uint32_t len)
{
	data += 512;
	uint8_t* p = data;

	len = blen(p);
	p = val(p); // into sequence

	len += p - data;

	entry->logMessage = se_malloc(len);
	memcpy(entry->logMessage, data, len);
	entry->msgLength = len;

	p = skip(p); // skip version
	p = skip(p); // skip type
	entry->type = *(p-1) - 1;

	// certified data...
	if(entry->type == WORM_ENTRY_TYPE_TRANSACTION)
	{
		while(*p != 0x82)
			p = skip(p);

		entry->processData = p;
		entry->processDataLength = blen(p);
	}
	while(*p != 0x04)
		p = skip(p);

	p = skip(p); // skip serial
	p = skip(p); // skip signature alg
	if(entry->type == WORM_ENTRY_TYPE_SE_AUDIT_LOG_MESSAGE)
		p = skip(p); // skip audit data
	uint8_t clen = blen(p);
	p = val(p);
	entry->id = 0;
	while(clen--)
	{
		entry->id <<= 8;
		entry->id = *p;
		p++;
	}

	entry->isValid = 1;
}
WORMAPI WormError WORMAPI_CALL worm_entry_iterate_first(WormEntry* entry)
{
	return worm_entry_iterate_id(entry, 1);
}
WORMAPI WormError WORMAPI_CALL worm_entry_iterate_last(WormEntry* entry)
{
	se_result_t result = ExecutionOk;

	uint32_t signatureCounter = 0;

	if((result = se_getSignatureCounter1Ex(entry->context->se, &signatureCounter)) != ExecutionOk)
		return toWormError(entry->context->se, result);

	return worm_entry_iterate_id(entry, signatureCounter);
}
WORMAPI WormError WORMAPI_CALL worm_entry_iterate_id(WormEntry* entry, uint32_t id)
{
	se_result_t result = ExecutionOk;

	uint8_t* data = NULL;
	uint32_t exportedDataLength = 0;

	if((result = se_exportMoreDataEx(entry->context->se, NULL, 0, id-1, 1, &data, &exportedDataLength)) != ExecutionOk)
		return toWormError(entry->context->se, result);

	data += 8*512;
	exportedDataLength -= 8*512;
	worm_entry_from_log(entry, data, exportedDataLength);

	return WORM_ERROR_NOERROR;
}
WORMAPI WormError WORMAPI_CALL worm_entry_iterate_next(WormEntry* entry)
{
	if(entry->isValid == 0)
		return WORM_ERROR_INVALID_PARAMETER;

	return worm_entry_iterate_id(entry, entry->id+1);
}

WORMAPI int WORMAPI_CALL worm_entry_isValid(const WormEntry* entry)
{
	return entry->isValid;
}
WORMAPI uint32_t WORMAPI_CALL worm_entry_id(const WormEntry* entry)
{
	return entry->id;
}
WORMAPI WormEntryType WORMAPI_CALL worm_entry_type(const WormEntry* entry)
{
	return entry->type;
}
WORMAPI worm_uint WORMAPI_CALL worm_entry_logMessageLength(const WormEntry* entry)
{
	return entry->msgLength;
}
WORMAPI WormError WORMAPI_CALL worm_entry_readLogMessage(const WormEntry* entry, unsigned char* msg, worm_uint msgLength)
{
	if(msgLength != entry->msgLength)
		return WORM_ERROR_INVALID_PARAMETER;
	memcpy(msg, entry->logMessage, msgLength);
	return WORM_ERROR_NOERROR;
}
WORMAPI worm_uint WORMAPI_CALL worm_entry_processDataLength(const WormEntry* entry)
{
	return entry->processDataLength;
}
WORMAPI WormError WORMAPI_CALL worm_entry_readProcessData(const WormEntry* entry, worm_uint offset, unsigned char* data, worm_uint dataLength)
{
	if(offset + dataLength > entry->processDataLength)
		return WORM_ERROR_INVALID_PARAMETER;
	memcpy(data, entry->logMessage + offset, dataLength);
	return WORM_ERROR_NOERROR;
}

WORMAPI WormError WORMAPI_CALL worm_getLogMessageCertificate(WormContext* context, unsigned char* certificate, uint32_t* certificateLength)
{
	se_result_t result = ExecutionOk;

	uint8_t* certificateData = NULL;
	uint32_t certificateDataLength = 0;
	if((result = se_getCertificateEx(context->se, &certificateData, &certificateDataLength)) != ExecutionOk)
		return toWormError(context->se, result);

	if(certificateDataLength > *certificateLength && certificate)
		return WORM_ERROR_INVALID_PARAMETER;

	*certificateLength = certificateDataLength;
	if(certificate)
		memcpy(certificate, certificateData, certificateDataLength);

	return WORM_ERROR_NOERROR;
}

typedef struct callBackHelper {
	WormExportTarCallback* callback;
	WormExportTarIncrementalCallback* callbackInc;
	void* data;
	uint32_t processedBlocks;
} callBackHelper;

uint32_t writer(const uint8_t* data, uint32_t dataLength, uint64_t totalDataLength, se_handle_t handle)
{
	callBackHelper* helper = handle;
	int result = -1;
	if(helper->callback)
		result = helper->callback(data, dataLength, helper->data);
	else if(helper->callbackInc)
		result = helper->callbackInc(data, dataLength, helper->processedBlocks, totalDataLength/512, helper->data);

	if(result == 0)
	{
		helper->processedBlocks += dataLength / 512;
		return dataLength;
	}
	else
		return 0;
}

WORMAPI WormError WORMAPI_CALL worm_export_tar(WormContext* context, WormExportTarCallback callback, void* callbackData)
{
	se_result_t result = ExecutionOk;

	callBackHelper h = { callback, NULL, callbackData };

	if((result = se_exportMoreDataViaCallbackEx(context->se, NULL, 0, 0, 0, writer, &h)) != ExecutionOk)
		return toWormError(context->se, result);

	return WORM_ERROR_NOERROR;
}
WORMAPI WormError WORMAPI_CALL worm_export_tar_incremental(
			WormContext* context,
			const unsigned char* lastState, int lastStateSize,
			unsigned char* newState, int newStateSize,
			uint64_t* firstSignatureCounter, uint64_t* lastSignatureCounter,
			WormExportTarIncrementalCallback callback,
			void* callbackData)
{
	se_result_t result = ExecutionOk;

	uint32_t prevSigCounter = 0;
	uint32_t numSignatures = 0;
	uint32_t minSigCounter = 0;
	uint32_t maxSigCounter = 0;
	if(lastState)
	{
		if(lastStateSize < sizeof(prevSigCounter))
			return WORM_ERROR_INVALID_PARAMETER;
		else
			prevSigCounter = *((uint32_t*) lastState);
	}

	if(newState)
		if(newStateSize < sizeof(prevSigCounter))
			return WORM_ERROR_INVALID_PARAMETER;

	if(newState || lastSignatureCounter)
	{
		if((result = se_getMaxSignatureCounterEx(context->se, &maxSigCounter)) != ExecutionOk)
			return WORM_ERROR_INCREMENTAL_EXPORT_INVALID_STATE;
		if(newState)
			*((uint32_t*) newState) = maxSigCounter;
		if(lastSignatureCounter)
			*lastSignatureCounter = maxSigCounter;
	}

	if(firstSignatureCounter)
	{
		if((result = se_getMinSignatureCounterEx(context->se, &minSigCounter)) != ExecutionOk)
			return WORM_ERROR_INCREMENTAL_EXPORT_INVALID_STATE;
		*firstSignatureCounter = minSigCounter;
	}

	callBackHelper h = { NULL, callback, callbackData };

	if((result = se_exportMoreDataViaCallbackEx(context->se, NULL, 0, prevSigCounter, 0, writer, &h)) != ExecutionOk)
	{
		if(result == ErrorIdNotFound)
			return WORM_ERROR_INCREMENTAL_EXPORT_NO_DATA;
		else
			return toWormError(context->se, result);
	}

	return WORM_ERROR_NOERROR;
}

WORMAPI WormError WORMAPI_CALL worm_export_tar_filtered_time(
			WormContext* context, worm_uint startDate, worm_uint endDate,
			const char* clientId, WormExportTarCallback callback, void* callbackData)
{
	se_result_t result = ExecutionOk;

	callBackHelper h = { callback, NULL, callbackData };

	if((result = se_exportDataViaCallbackEx(context->se, NULL, 0, SE_MAX_UINT32, 0, SE_MAX_UINT32, startDate, endDate, 0, writer, &h)) != ExecutionOk)
		return toWormError(context->se, result);

	return WORM_ERROR_NOERROR;
}

WORMAPI WormError WORMAPI_CALL worm_export_tar_filtered_transaction(
			WormContext* context, worm_uint transactionNumberStart,
			worm_uint transactionNumberEnd, const char* clientId,
			WormExportTarCallback callback, void* callbackData)
{
	se_result_t result = ExecutionOk;

	callBackHelper h = { callback, NULL, callbackData };

	if((result = se_exportDataViaCallbackEx(context->se, NULL, 0, SE_MAX_UINT32, transactionNumberStart, transactionNumberEnd, 0, SE_MAX_TIME, 0, writer, &h)) != ExecutionOk)
		return toWormError(context->se, result);

	return WORM_ERROR_NOERROR;

}

WORMAPI WormError WORMAPI_CALL worm_export_deleteStoredData(WormContext* context)
{
	return toWormError(context->se, se_deleteStoredDataEx(context->se));
}

#ifdef __cplusplus
}
#endif
