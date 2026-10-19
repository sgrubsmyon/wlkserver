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
 * @file se_api.c
 * @brief SE-API implementation - directly calling the _extended_ SE-API functions.
 */

#include <se_api_ex.h>
#include <se_api.h>


/* ------------------------------------------------------------------------- */
/* Global variables                                                          */
/* ------------------------------------------------------------------------- */

se_ctx_t g_se_ctx;		 /**< global SE-API context object of the opened TSE */


/* ------------------------------------------------------------------------- */
/* Local variables                                                           */
/* ------------------------------------------------------------------------- */

static const char*		SE_API_C_VERSION_STR	= "cryptovision SE-API-C v3.1.3";	/**< current SE-API-C implementation version */
static const uint8_t	SE_API_C_VERSION[]		= { 0x03, 0x01, 0x03 };				/**< current SE-API-C implementation version */

/**
 * - DllMain to close open TSE handle before unload
 * - additional helpers (useful for API testing only)
 */
#if VBA_MAGIC

static int m_mallocCount = 0, m_freeCount = 0;

static void SE_STDCALL myFree(void* memBlock)
{
	{
		uint64_t address = (uint64_t)memBlock;
		printf("[myFree: called at address 0x%08X%08X]\n",
			(uint32_t)(address >> 32), (uint32_t)(address & SE_MAX_UINT32));
	}
	++m_freeCount;
	free(memBlock);
}

/* ------------------------------------------------------------------------- */
static void* SE_STDCALL myMalloc(size_t size)
{
	void* memBlock = malloc(size);
	if (memBlock != NULL)
	{
		uint64_t address = (uint64_t)memBlock;
		printf("[myMalloc: allocated 0x%04X byte at address 0x%08X%08X]\n",
			(uint32_t)size, (uint32_t)(address >> 32), (uint32_t)(address & SE_MAX_UINT32));
	}
	else
		printf("[myMalloc: failed to allocate 0x%04X byte]\n", (uint32_t)size);

	++m_mallocCount;
	return memBlock;
}

BOOL WINAPI DllMain(
	HINSTANCE hinstDLL,  // handle to DLL module
	DWORD fdwReason,     // reason for calling function
	LPVOID lpvReserved )  // reserved
{
	// Perform actions based on the reason for calling.
	switch (fdwReason)
	{
	case DLL_PROCESS_ATTACH:
		// Initialize once for each new process.
		// Return FALSE to fail DLL load.
//		if (se_setAllocator(myMalloc, myFree) != ExecutionOk)
//			return FALSE;
		break;

	case DLL_THREAD_ATTACH:
		// Do thread-specific initialization.
		break;

	case DLL_THREAD_DETACH:
		// Do thread-specific cleanup.
		break;

	case DLL_PROCESS_DETACH:

		if (lpvReserved != NULL)
		{
			break; // do not do cleanup if process termination scenario
		}

		// Perform any necessary cleanup.
//		printf("[myMalloc count = %i, myFree count = %i -> %s]\n", m_mallocCount, m_freeCount, (m_mallocCount == m_freeCount ? "equal" : "Oops, not equal!"));
//		m_mallocCount = m_freeCount = 0;
		se_close();
		break;
	}
	return TRUE;  // Successful DLL_PROCESS_ATTACH.
}

SE_API_IMPL(errno_t, se_fopen_s)(FILE** stream, const char* filename, const char* mode)
{
	SE_EXPORT_METHOD;

	return fopen_s(stream, filename, mode);
}

SE_API_IMPL(int, se_fclose)(FILE* stream)
{
	SE_EXPORT_METHOD;

	return fclose(stream);
}
#endif

/* ------------------------------------------------------------------------- */
/* se_api.h functions                                                        */
/* ------------------------------------------------------------------------- */

/* ------------------------------------------------------------------------- */
SE_API_IMPL(const se_tse_version_t, se_getHardwareVersion)()
{
	SE_EXPORT_METHOD;

	return se_getHardwareVersionEx(&g_se_ctx);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_isEngineeringSample)(uint8_t* isES)
{
	SE_EXPORT_METHOD;

	return se_isEngineeringSampleEx(&g_se_ctx, isES);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(const char*, se_getApiVersionString)()
{
	SE_EXPORT_METHOD;

	return se_getApiVersionStringEx();
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(const uint8_t*, se_getApiVersion)(uint32_t *versionLength)
{
	SE_EXPORT_METHOD;

	return se_getApiVersionEx(versionLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(const char*, se_getImplementationVersionString)()
{
	SE_EXPORT_METHOD;

	return SE_API_C_VERSION_STR;
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(const uint8_t*, se_getImplementationVersion)(uint32_t *versionLength)
{
	SE_EXPORT_METHOD;

	if(versionLength == NULL)
		return NULL;

	*versionLength = sizeof(SE_API_C_VERSION);
	return SE_API_C_VERSION;
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(const uint8_t*, se_getUniqueId)(uint32_t *idLength)
{
	SE_EXPORT_METHOD;

	return se_getUniqueIdEx(&g_se_ctx, idLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getTemperature)(uint32_t *temp)
{
	SE_EXPORT_METHOD;

	return se_getTemperatureEx(&g_se_ctx, temp);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getTemperature1)(uint32_t vcc, uint32_t *temp)
{
	SE_EXPORT_METHOD;

	return se_getTemperature1Ex(&g_se_ctx, vcc, temp);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getCertificationId)(char **certificationId,
	uint32_t *certificationIdLength)
{
	SE_EXPORT_METHOD;

	return se_getCertificationIdEx(&g_se_ctx, certificationId, certificationIdLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(const char*, se_getFirmwareId)()
{
	SE_EXPORT_METHOD;

	return se_getFirmwareIdEx(&g_se_ctx);
}

SE_API_IMPL(se_result_t, se_updateFirmware)(const uint8_t* binary, uint32_t binaryLength)
{
	SE_EXPORT_METHOD;

	return se_updateFirmwareEx(&g_se_ctx, binary, binaryLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getLifeCycleState)(se_lcs_t *lcs)
{
	SE_EXPORT_METHOD;

	return se_getLifeCycleStateEx(&g_se_ctx, lcs);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_open)(const char *configFileName)
{
	SE_EXPORT_METHOD;

	return se_openEx(&g_se_ctx, configFileName);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_openDirect)(const char *devicePath, uint32_t timeout)
{
	SE_EXPORT_METHOD;

	return se_openDirectEx(&g_se_ctx, devicePath, timeout);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_openDirect1)(const char *devicePath, uint32_t timeout, uint32_t maxResponse)
{
	SE_EXPORT_METHOD;

	return se_openDirect1Ex(&g_se_ctx, devicePath, timeout, maxResponse);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_openDirect2)(const char *devicePath, uint32_t timeout, uint32_t maxResponse, uint8_t checkIntegrity)
{
	SE_EXPORT_METHOD;

	return se_openDirect2Ex(&g_se_ctx, devicePath, timeout, maxResponse, checkIntegrity);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_reopen)(const char *devicePath, uint32_t timeout)
 {
	SE_EXPORT_METHOD;

	return se_reopenEx(&g_se_ctx, devicePath, timeout);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_reopen2)(const char *devicePath, uint32_t timeout, uint32_t maxResponse, uint8_t checkIntegrity)
{
	SE_EXPORT_METHOD;

	return se_reopen2Ex(&g_se_ctx, devicePath, timeout, maxResponse, checkIntegrity);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_close)()
{
	SE_EXPORT_METHOD;

	return se_closeEx(&g_se_ctx);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_selfTest)(uint32_t maxDuration,
		se_self_test_result_t* result)
{
	SE_EXPORT_METHOD;

	return se_selfTestEx(&g_se_ctx, maxDuration, result);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getPinStatus)(se_pin_state_flags_t* pinState)
{
	SE_EXPORT_METHOD;

	return se_getPinStatusEx(&g_se_ctx, pinState);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_initializePinValues)(const uint8_t *adminPin,
	uint32_t adminPinLength,
	const uint8_t *adminPuk,
	uint32_t adminPukLength,
	const uint8_t *timeAdminPin,
	uint32_t timeAdminPinLength,
	const uint8_t *timeAdminPuk,
	uint32_t timeAdminPukLength)
{
	SE_EXPORT_METHOD;

	return se_initializePinValuesEx(&g_se_ctx, adminPin, adminPinLength, adminPuk, adminPukLength, timeAdminPin, timeAdminPinLength, timeAdminPuk, timeAdminPukLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_initializePuk)(const char *userId, uint32_t userIdLength, const uint8_t *puk, uint32_t pukLength)
{
	SE_EXPORT_METHOD;

	return se_initializePukEx(&g_se_ctx, userId, userIdLength, puk, pukLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_initialize)()
{
	SE_EXPORT_METHOD;

	return se_initializeEx(&g_se_ctx);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_initialize1)(const char* description)
{
	SE_EXPORT_METHOD;

	return se_initialize1Ex(&g_se_ctx, description);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_deactivateTSE)()
{
	SE_EXPORT_METHOD;

	return se_deactivateTSEEx(&g_se_ctx);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_activateTSE)()
{
	SE_EXPORT_METHOD;

	return se_activateTSEEx(&g_se_ctx);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_lockTransactionLogging)()
{
	SE_EXPORT_METHOD;

	return se_lockTransactionLoggingEx(&g_se_ctx);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_unlockTransactionLogging)()
{
	SE_EXPORT_METHOD;

	return se_unlockTransactionLoggingEx(&g_se_ctx);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_mapERStoKey)(const char *clientId,
	uint32_t clientIdLength,
	const uint8_t *serialNumberKey,
	uint32_t serialNumberLength)
{
	SE_EXPORT_METHOD;

	return se_mapERStoKeyEx(&g_se_ctx, clientId, clientIdLength, serialNumberKey, serialNumberLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_unmapERS)(const char* clientId,
	uint32_t clientIdLength)
{
	SE_EXPORT_METHOD;

	return se_unmapERSEx(&g_se_ctx, clientId, clientIdLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_registerClient)(const char *clientId,
	uint32_t clientIdLength
)
{
	SE_EXPORT_METHOD;

	return se_registerClientEx(&g_se_ctx, clientId, clientIdLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_deregisterClient)(const char* clientId,
	uint32_t clientIdLength)
{
	SE_EXPORT_METHOD;

	return se_deregisterClientEx(&g_se_ctx, clientId, clientIdLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_updateTime)(int64_t unixTime)
{
	SE_EXPORT_METHOD;

	return se_updateTimeEx(&g_se_ctx, unixTime);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_disableSecureElement)()
{
	SE_EXPORT_METHOD;

	return se_disableSecureElementEx(&g_se_ctx);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_startTransaction)(const char *clientId,
	uint32_t clientIdLength,
	const uint8_t *processData,
	uint32_t processDataLength,
	const char *processType,
	uint32_t processTypeLength,
	const uint8_t *additionalData,
	uint32_t additionalDataLength,
	se_start_transaction_result_t* transactionResult)
{
	SE_EXPORT_METHOD;

	return se_startTransactionEx(&g_se_ctx, clientId, clientIdLength, processData, processDataLength, processType, processTypeLength, additionalData, additionalDataLength, transactionResult);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_updateTransaction)(const char *clientId,
	uint32_t clientIdLength,
	uint32_t transactionNumber,
	const uint8_t *processData,
	uint32_t processDataLength,
	const char *processType,
	uint32_t processTypeLength,
	se_update_transaction_result_t* transactionResult)
{
	SE_EXPORT_METHOD;

	return se_updateTransactionEx(&g_se_ctx, clientId, clientIdLength, transactionNumber, processData, processDataLength, processType, processTypeLength, transactionResult);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_finishTransaction)(const char *clientId,
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
	SE_EXPORT_METHOD;

	return se_finishTransactionEx(&g_se_ctx, clientId, clientIdLength, transactionNumber, processData, processDataLength, processType, processTypeLength, additionalData, additionalDataLength, transactionResult);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getOpenTransactions)(uint32_t **transactionNumbers,
	uint32_t *transactionNumbersLength)
{
	SE_EXPORT_METHOD;

	return se_getOpenTransactionsEx(&g_se_ctx, transactionNumbers, transactionNumbersLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_exportData)(const char *clientId,
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
	SE_EXPORT_METHOD;

	return se_exportDataEx(&g_se_ctx, clientId, clientIdLength, transactionNumber, startTransactionNumber, endTransactionNumber, startDate, endDate, maximumNumberRecords, exportedData, exportedDataLength);
}


/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getExportSize)(const char *clientId,
	uint32_t clientIdLength,
	uint32_t transactionNumber,
	uint32_t startTransactionNumber,
	uint32_t endTransactionNumber,
	int64_t startDate,
	int64_t endDate,
	uint64_t *exportedDataLength)
{
	SE_EXPORT_METHOD;

	return se_getExportSizeEx(&g_se_ctx, clientId, clientIdLength, transactionNumber, startTransactionNumber, endTransactionNumber, startDate, endDate, exportedDataLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getExportSize1)(uint32_t previousSignatureCounter, uint32_t maximumNumberRecords, uint64_t *exportedDataLength)
{
	SE_EXPORT_METHOD;

	return se_getExportSize1Ex(&g_se_ctx, previousSignatureCounter, maximumNumberRecords, exportedDataLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_exportDataToStream)(const char *clientId,
	uint32_t clientIdLength,
	uint32_t transactionNumber,
	uint32_t startTransactionNumber,
	uint32_t endTransactionNumber,
	int64_t startDate,
	int64_t endDate,
	int32_t maximumNumberRecords,
	FILE *stream)
{
	SE_EXPORT_METHOD;

	return se_exportDataToStreamEx(&g_se_ctx, clientId, clientIdLength, transactionNumber, startTransactionNumber, endTransactionNumber, startDate, endDate, maximumNumberRecords, stream);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_exportDataToFile)(const char *clientId,
	uint32_t clientIdLength,
	uint32_t transactionNumber,
	uint32_t startTransactionNumber,
	uint32_t endTransactionNumber,
	int64_t startDate,
	int64_t endDate,
	int32_t maximumNumberRecords,
	const char *fileName)
{
	SE_EXPORT_METHOD;

	return se_exportDataToFileEx(&g_se_ctx, clientId, clientIdLength, transactionNumber, startTransactionNumber, endTransactionNumber, startDate, endDate, maximumNumberRecords, fileName);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_exportDataViaCallback)(const char *clientId,
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
	SE_EXPORT_METHOD;

	return se_exportDataViaCallbackEx(&g_se_ctx, clientId, clientIdLength, transactionNumber, startTransactionNumber, endTransactionNumber, startDate, endDate, maximumNumberRecords, writer, handle);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_exportMoreData)(const uint8_t *serialNumberKey,
	uint32_t serialNumberLength,
	uint32_t previousSignatureCounter,
	int32_t maximumNumberRecords,
	uint8_t **exportedData,
	uint32_t *exportedDataLength)
{
	SE_EXPORT_METHOD;

	return se_exportMoreDataEx(&g_se_ctx, serialNumberKey, serialNumberLength, previousSignatureCounter, maximumNumberRecords, exportedData, exportedDataLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_exportMoreDataToStream)(const uint8_t *serialNumberKey,
	uint32_t serialNumberLength,
	uint32_t previousSignatureCounter,
	int32_t maximumNumberRecords,
	FILE *stream)
{
	SE_EXPORT_METHOD;

	return se_exportMoreDataToStreamEx(&g_se_ctx, serialNumberKey, serialNumberLength, previousSignatureCounter, maximumNumberRecords, stream);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_exportMoreDataToFile)(const uint8_t *serialNumberKey,
	uint32_t serialNumberLength,
	uint32_t previousSignatureCounter,
	int32_t maximumNumberRecords,
	const char *fileName)
{
	SE_EXPORT_METHOD;

	return se_exportMoreDataToFileEx(&g_se_ctx, serialNumberKey, serialNumberLength, previousSignatureCounter, maximumNumberRecords, fileName);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_exportMoreDataViaCallback)(const uint8_t *serialNumberKey,
	uint32_t serialNumberLength,
	uint32_t previousSignatureCounter,
	int32_t maximumNumberRecords,
	se_writer_t writer,
	se_handle_t handle)
{
	SE_EXPORT_METHOD;

	return se_exportMoreDataViaCallbackEx(&g_se_ctx, serialNumberKey, serialNumberLength, previousSignatureCounter, maximumNumberRecords, writer, handle);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_deleteStoredDataUpTo)(const uint8_t *serialNumberKey,
	uint32_t serialNumberLength,
	uint32_t signatureCounter)
{
	SE_EXPORT_METHOD;

	return se_deleteStoredDataUpToEx(&g_se_ctx, serialNumberKey, serialNumberLength, signatureCounter);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_exportCertificates)(uint8_t **certificates,
	uint32_t *certificatesLength)
{
	SE_EXPORT_METHOD;

	return se_exportCertificatesEx(&g_se_ctx, certificates, certificatesLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getCertificate)(uint8_t **certificate,
	uint32_t *certificateLength)
{
	SE_EXPORT_METHOD;

	return se_getCertificateEx(&g_se_ctx, certificate, certificateLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getCertificateExpirationDate)(const uint8_t *serialNumberKey,
	uint32_t serialNumberLength,
	int64_t *expirationDate)
{
	SE_EXPORT_METHOD;

	return se_getCertificateExpirationDateEx(&g_se_ctx, serialNumberKey, serialNumberLength, expirationDate);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getCertificateExpirationDate1)(int64_t *expirationDate)
{
	SE_EXPORT_METHOD;

	return se_getCertificateExpirationDate1Ex(&g_se_ctx, expirationDate);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getERSMappings)(uint8_t **mappingData,
	uint32_t *mappingDataLength)
{
	SE_EXPORT_METHOD;

	return se_getERSMappingsEx(&g_se_ctx, mappingData, mappingDataLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_listClients)(char ***clients,
	uint32_t *clientsLength)
{
	SE_EXPORT_METHOD;

	return se_listClientsEx(&g_se_ctx, clients, clientsLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_readLogMessage)(uint8_t **logMessage,
	uint32_t *logMessageLength)
{
	SE_EXPORT_METHOD;

	return se_readLogMessageEx(&g_se_ctx, logMessage, logMessageLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_exportSerialNumbers)(uint8_t **serialNumbers,
	uint32_t *serialNumbersLength)
{
	SE_EXPORT_METHOD;

	return se_exportSerialNumbersEx(&g_se_ctx, serialNumbers, serialNumbersLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getMaxNumberOfClients)(uint32_t *maxNumberClients)
{
	SE_EXPORT_METHOD;

	return se_getMaxNumberOfClientsEx(&g_se_ctx, maxNumberClients);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getCurrentNumberOfClients)(uint32_t *currentNumberClients)
{
	SE_EXPORT_METHOD;

	return se_getCurrentNumberOfClientsEx(&g_se_ctx, currentNumberClients);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getMaxNumberOfTransactions)(uint32_t *maxNumberTransactions)
{
	SE_EXPORT_METHOD;

	return se_getMaxNumberOfTransactionsEx(&g_se_ctx, maxNumberTransactions);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getCurrentNumberOfTransactions)(uint32_t *currentNumberTransactions)
{
	SE_EXPORT_METHOD;

	return se_getCurrentNumberOfTransactionsEx(&g_se_ctx, currentNumberTransactions);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getTransactionCounter)(uint32_t *transactionCounter)
{
	SE_EXPORT_METHOD;

	return se_getTransactionCounterEx(&g_se_ctx, transactionCounter);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getMinSignatureCounter)(uint32_t* minSignatureCounter)
{
	SE_EXPORT_METHOD;

	return se_getMinSignatureCounterEx(&g_se_ctx, minSignatureCounter);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getMaxSignatureCounter)(uint32_t* maxSignatureCounter)
{
	SE_EXPORT_METHOD;

	return se_getMaxSignatureCounterEx(&g_se_ctx, maxSignatureCounter);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getNextSignatureCounter)(uint32_t* nextSignatureCounter)
{
	SE_EXPORT_METHOD;

	return se_getNextSignatureCounterEx(&g_se_ctx, nextSignatureCounter);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getTotalLogMemory)(uint64_t *sizeOfMemory)
{
	SE_EXPORT_METHOD;

	return se_getTotalLogMemoryEx(&g_se_ctx, sizeOfMemory);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getAvailableLogMemory)(uint64_t *sizeOfMemory)
{
	SE_EXPORT_METHOD;

	return se_getAvailableLogMemoryEx(&g_se_ctx, sizeOfMemory);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getSignatureCounter)(const uint8_t *serialNumberKey,
	uint32_t serialNumberLength,
	uint32_t *signatureCounter)
{
	SE_EXPORT_METHOD;

	return se_getSignatureCounterEx(&g_se_ctx, serialNumberKey, serialNumberLength, signatureCounter);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getSignatureCounter1)(uint32_t *signatureCounter)
{
	SE_EXPORT_METHOD;

	return se_getSignatureCounter1Ex(&g_se_ctx, signatureCounter);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getSupportedTransactionUpdateVariants)(se_update_t *supportedUpdateVariants)
{
	SE_EXPORT_METHOD;

	return se_getSupportedTransactionUpdateVariantsEx(&g_se_ctx, supportedUpdateVariants);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getTimeSyncVariant)(se_sync_variants_t *supportedSyncVariant)
{
	SE_EXPORT_METHOD;

	return se_getTimeSyncVariantEx(&g_se_ctx, supportedSyncVariant);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getSignatureAlgorithm)(uint8_t **signatureAlgorithm,
	uint32_t *signatureAlgorithmLength)
{
	SE_EXPORT_METHOD;

	return se_getSignatureAlgorithmEx(&g_se_ctx, signatureAlgorithm, signatureAlgorithmLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getTimeSyncInterval)(uint32_t *timeSyncInterval)
{
	SE_EXPORT_METHOD;

	return se_getTimeSyncIntervalEx(&g_se_ctx, timeSyncInterval);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_deleteStoredData)()
{
	SE_EXPORT_METHOD;

	return se_deleteStoredDataEx(&g_se_ctx);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_authenticateUser)(const char *userId,
	uint32_t userIdLength,
	const uint8_t *pin,
	uint32_t pinLength,
	se_authentication_result_t *authenticationResult,
	int16_t *remainingRetries)
{
	SE_EXPORT_METHOD;

	return se_authenticateUserEx(&g_se_ctx, userId, userIdLength, pin, pinLength, authenticationResult, remainingRetries);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_logOut)(const char *userId,
	uint32_t userIdLength)
{
	SE_EXPORT_METHOD;

	return se_logOutEx(&g_se_ctx, userId, userIdLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_unblockUser)(const char *userId,
	uint32_t userIdLength,
	const uint8_t *puk,
	uint32_t pukLength,
	const uint8_t *newPin,
	uint32_t newPinLength,
	se_unblock_result_t *unblockResult)
{
	SE_EXPORT_METHOD;

	return se_unblockUserEx(&g_se_ctx, userId, userIdLength, puk, pukLength, newPin, newPinLength, unblockResult);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_getWearIndicator)(uint32_t* wearIndicator)
{
	SE_EXPORT_METHOD;

	return se_getWearIndicatorEx(&g_se_ctx, wearIndicator);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(se_result_t, se_exportPublicKey)(const uint8_t* serialNumberKey,
	uint32_t serialNumberLength,
	uint8_t** exportedPublicKey,
	uint32_t* exportedPublicKeyLength)
{
	SE_EXPORT_METHOD;

	return se_exportPublicKeyEx(&g_se_ctx, serialNumberKey, serialNumberLength, exportedPublicKey, exportedPublicKeyLength);
}

/* ------------------------------------------------------------------------- */
SE_API_IMPL(uint32_t, se_getOsStatusOfErrorIO)()
{
	SE_EXPORT_METHOD;

	return se_getOsStatusOfErrorIOEx(&g_se_ctx);
}
