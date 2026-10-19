/*
 * fiscade_wormApi.h
 */

#ifndef SE_API_FISCADE_FISCADE_WORMAPI_H_
#define SE_API_FISCADE_FISCADE_WORMAPI_H_

        /* extracted from https://github.com/fiskaltrust/middleware/raw/refs/heads/main/scu-de/src/fiskaltrust.Middleware.SCU.DE.Swissbit/Interop/NativeWormAPI.cs */

        WORMAPI const char *WORMAPI_CALL worm_getVersion(void);
        WORMAPI const char* WORMAPI_CALL worm_signatureAlgorithm(void);
        WORMAPI const char* WORMAPI_CALL worm_logTimeFormat(void);

        WORMAPI WormError WORMAPI_CALL worm_init(WormContext** context, const char* mountPoint);
        WORMAPI WormError WORMAPI_CALL worm_cleanup(WormContext* context);

        WORMAPI WormInfo *WORMAPI_CALL worm_info_new(WormContext* context);
        WORMAPI void WORMAPI_CALL worm_info_free(WormInfo* info);
        WORMAPI WormError WORMAPI_CALL worm_info_read(WormInfo* info);
        WORMAPI void WORMAPI_CALL worm_info_customizationIdentifier(const WormInfo* info, const unsigned char** id, int* idLength);
        WORMAPI int WORMAPI_CALL worm_info_isDevelopmentFirmware(const WormInfo* info);
        WORMAPI uint32_t WORMAPI_CALL worm_info_capacity(const WormInfo* info);
        WORMAPI uint32_t WORMAPI_CALL worm_info_size(const WormInfo* info);
        WORMAPI int WORMAPI_CALL worm_info_hasValidTime(const WormInfo* info);
        WORMAPI int WORMAPI_CALL worm_info_hasPassedSelfTest(const WormInfo* info);
        WORMAPI int WORMAPI_CALL worm_info_isCtssInterfaceActive(const WormInfo* info);
        WORMAPI int WORMAPI_CALL worm_info_isExportEnabledIfCspTestFails(const WormInfo* info);
        WORMAPI WormInitializationState WORMAPI_CALL worm_info_initializationState(const WormInfo* info);
        WORMAPI int WORMAPI_CALL worm_info_isDataImportInProgress(const WormInfo* info);
        WORMAPI int WORMAPI_CALL worm_info_hasChangedPuk(const WormInfo* info);
        WORMAPI int WORMAPI_CALL worm_info_hasChangedAdminPin(const WormInfo* info);
        WORMAPI int WORMAPI_CALL worm_info_hasChangedTimeAdminPin(const WormInfo* info);
        WORMAPI uint32_t WORMAPI_CALL worm_info_timeUntilNextSelfTest(const WormInfo* info);
        WORMAPI uint32_t WORMAPI_CALL worm_info_startedTransactions(const WormInfo* info);
        WORMAPI uint32_t WORMAPI_CALL worm_info_maxStartedTransactions(const WormInfo* info);
        WORMAPI uint32_t WORMAPI_CALL worm_info_createdSignatures(const WormInfo* info);
        WORMAPI uint32_t WORMAPI_CALL worm_info_maxSignatures(const WormInfo* info);
        WORMAPI uint32_t WORMAPI_CALL worm_info_remainingSignatures(const WormInfo* info);
        WORMAPI uint32_t WORMAPI_CALL worm_info_maxTimeSynchronizationDelay(const WormInfo* info);
        WORMAPI uint32_t WORMAPI_CALL worm_info_maxUpdateDelay(const WormInfo* info);
        WORMAPI void WORMAPI_CALL worm_info_tsePublicKey(const WormInfo* info, const unsigned char** publicKey,worm_uint *publicKeyLength);
        WORMAPI void WORMAPI_CALL worm_info_tseSerialNumber(const WormInfo* info, const unsigned char** serialNumber,worm_uint *serialNumberLength);
        WORMAPI const char* WORMAPI_CALL worm_info_tseDescription(const WormInfo* info);
        WORMAPI uint32_t WORMAPI_CALL worm_info_registeredClients(const WormInfo* info);
        WORMAPI uint32_t WORMAPI_CALL worm_info_maxRegisteredClients(const WormInfo* info);
        WORMAPI worm_uint WORMAPI_CALL worm_info_certificateExpirationDate(const WormInfo* info);
        WORMAPI worm_uint WORMAPI_CALL worm_info_tarExportSizeInSectors(const WormInfo* info);
        WORMAPI uint64_t worm_info_tarExportSize(const WormInfo* info);
        WORMAPI uint32_t WORMAPI_CALL worm_info_hardwareVersion(const WormInfo* info);
        WORMAPI uint32_t WORMAPI_CALL worm_info_softwareVersion(const WormInfo* info);
        WORMAPI const char* WORMAPI_CALL worm_info_formFactor(const WormInfo* info);

        WORMAPI WormError WORMAPI_CALL worm_flash_health_summary(
            WormContext* context, uint32_t* uncorrectableEccErrors,
            uint8_t* percentageRemainingSpareBlocks,
            uint8_t* percentageRemainingEraseCounts,
            uint8_t* percentageRemainingTenYearsDataRetention);
        WORMAPI int WORMAPI_CALL worm_flash_health_needs_replacement(
            uint32_t uncorrectableEccErrors, uint8_t percentageRemainingSpareBlocks,
            uint8_t percentageRemainingEraseCounts);

        WORMAPI WormError WORMAPI_CALL worm_tse_factoryReset(WormContext* context);

        WORMAPI WormError WORMAPI_CALL worm_tse_setup(
            WormContext* context, const unsigned char* credentialSeed,
            int credentialSeedLength, const unsigned char* adminPuk,
            int adminPukLength, const unsigned char* adminPin,
            int adminPinLength, const unsigned char* timeAdminPin,
            int timeAdminPinLength, const char* clientId);

        WORMAPI WormError WORMAPI_CALL worm_tse_ctss_enable(WormContext* context);
        WORMAPI WormError WORMAPI_CALL worm_tse_ctss_disable(WormContext* context);

        WORMAPI WormError WORMAPI_CALL worm_tse_initialize(WormContext* context);
        WORMAPI WormError WORMAPI_CALL worm_tse_decommission(WormContext* context);

        WORMAPI WormError WORMAPI_CALL worm_tse_updateTime(WormContext* context, worm_uint timestamp);

        WORMAPI WormError WORMAPI_CALL worm_tse_firmwareUpdate_transfer(
            WormContext* context, uint32_t chunkOffset, const unsigned char* chunkData,
            int chunkLength);
        WORMAPI WormError WORMAPI_CALL worm_tse_firmwareUpdate_apply(WormContext* context, uint32_t fwSize);

        WORMAPI WormError WORMAPI_CALL worm_tse_enableExportIfCspTestFails(WormContext* context);
        WORMAPI WormError WORMAPI_CALL worm_tse_disableExportIfCspTestFails(WormContext* context);

        WORMAPI WormError WORMAPI_CALL worm_tse_runSelfTest(WormContext* context, const char* clientId);

        WORMAPI WormError WORMAPI_CALL worm_tse_registerClient(WormContext* context, const char* clientId);
        WORMAPI WormError WORMAPI_CALL worm_tse_deregisterClient(WormContext* context, const char* clientId);
        WORMAPI WormError WORMAPI_CALL worm_tse_listRegisteredClients(WormContext* context, int toSkip, WormRegisteredClients* clients);

        WORMAPI WormError WORMAPI_CALL worm_user_login(WormContext* context,
                                                   WormUserId id,
                                                   const unsigned char* pin,
                                                   int pinLength,
                                                   int* remainingRetries);
        WORMAPI WormError WORMAPI_CALL worm_user_logout(WormContext* context, WormUserId id);
        WORMAPI WormError WORMAPI_CALL worm_user_unblock(WormContext* context, WormUserId id, const unsigned char* puk,
                      int pukLength, const unsigned char* newPin, int newPinLength,
                      int* remainingRetries);
        WORMAPI WormError WORMAPI_CALL worm_user_change_puk(
        WormContext* context, const unsigned char* puk, int pukLength,
        const unsigned char* newPuk, int newPukLength, int* remainingRetries);
        WORMAPI WormError WORMAPI_CALL worm_user_change_pin(
        WormContext* context, WormUserId id, const unsigned char* pin,
        int pinLength, const unsigned char* newPin, int newPinLength,
        int* remainingRetries);

        WORMAPI WormError WORMAPI_CALL worm_user_deriveInitialCredentials(
        WormContext* context, const unsigned char* seed, int seedLength,
        unsigned char* initialAdminPuk, int initialAdminPukLength,
        unsigned char* initialAdminPin, int initialAdminPinLength,
        unsigned char* initialTimeAdminPin, int initialTimeAdminPinLength);

        WORMAPI WormError WORMAPI_CALL worm_transaction_start(
            WormContext* context, const char* clientId,
            const unsigned char* processData, worm_uint processDataLength,
            const char* processType, WormTransactionResponse* response);
        WORMAPI WormError WORMAPI_CALL worm_transaction_update(
        WormContext* context, const char* clientId, worm_uint transactionNumber,
        const unsigned char* processData, worm_uint processDataLength,
        const char* processType, WormTransactionResponse* response);
        WORMAPI WormError WORMAPI_CALL worm_transaction_finish(
        WormContext* context, const char* clientId, worm_uint transactionNumber,
        const unsigned char* processData, worm_uint processDataLength,
        const char* processType, WormTransactionResponse* response);

        WORMAPI WormError WORMAPI_CALL worm_transaction_lastResponse(WormContext* context, const char* clientId, WormTransactionResponse* response);

        WORMAPI WormError WORMAPI_CALL worm_transaction_listStartedTransactions(
        WormContext* context, const char* clientId, int toSkip,
        worm_uint* transactionNumbers, int transactionNumbersLength,
        int* storedTransactionNumbers);

        WORMAPI WormTransactionResponse * WORMAPI_CALL worm_transaction_response_new(WormContext* context);
        WORMAPI void WORMAPI_CALL worm_transaction_response_free(WormTransactionResponse* response);
        WORMAPI worm_uint WORMAPI_CALL worm_transaction_response_logTime(const WormTransactionResponse* response);
        WORMAPI void WORMAPI_CALL worm_transaction_response_serialNumber(const WormTransactionResponse* response, const unsigned char** serialNumber,worm_uint* serialNumberLength);
        WORMAPI worm_uint WORMAPI_CALL worm_transaction_response_signatureCounter(const WormTransactionResponse* response);
        WORMAPI void WORMAPI_CALL worm_transaction_response_signature(const WormTransactionResponse* response, const unsigned char** signature,
        worm_uint* signatureLength);
        WORMAPI worm_uint WORMAPI_CALL worm_transaction_response_transactionNumber(const WormTransactionResponse* response);

        WORMAPI WormEntry * WORMAPI_CALL worm_entry_new(WormContext* context);
        WORMAPI void WORMAPI_CALL worm_entry_free(WormEntry* entry);
        WORMAPI WormError WORMAPI_CALL worm_entry_iterate_first(WormEntry* entry);
        WORMAPI WormError WORMAPI_CALL worm_entry_iterate_last(WormEntry* entry);
        WORMAPI WormError WORMAPI_CALL worm_entry_iterate_id(WormEntry* entry, uint32_t id);
        WORMAPI WormError WORMAPI_CALL worm_entry_iterate_next(WormEntry* entry);
        WORMAPI int WORMAPI_CALL worm_entry_isValid(const WormEntry* entry);
        WORMAPI uint32_t WORMAPI_CALL worm_entry_id(const WormEntry* entry);
        WORMAPI WormEntryType WORMAPI_CALL worm_entry_type(const WormEntry* entry);
        WORMAPI worm_uint WORMAPI_CALL worm_entry_logMessageLength(const WormEntry* entry);
        WORMAPI WormError WORMAPI_CALL worm_entry_readLogMessage(const WormEntry* entry, unsigned char* msg, worm_uint msgLength);
        WORMAPI worm_uint WORMAPI_CALL worm_entry_processDataLength(const WormEntry* entry);
        WORMAPI WormError WORMAPI_CALL worm_entry_readProcessData(const WormEntry* entry, worm_uint offset,
                               unsigned char* data, worm_uint dataLength);

        WORMAPI WormError WORMAPI_CALL worm_getLogMessageCertificate(WormContext* context, unsigned char* certificate,
                                  uint32_t* certificateLength);

        WORMAPI WormError WORMAPI_CALL worm_export_tar(WormContext* context,
                                               WormExportTarCallback callback,
                                               void* callbackData);
        WORMAPI WormError WORMAPI_CALL worm_export_tar_incremental(
        WormContext* context, const unsigned char* lastState, int lastStateSize,
        unsigned char* newState, int newStateSize, uint64_t* firstSignatureCounter,
        uint64_t* lastSignatureCounter, WormExportTarIncrementalCallback callback,
        void* callbackData);
        WORMAPI WormError WORMAPI_CALL worm_export_tar_filtered_time(
        WormContext* context, worm_uint startDate, worm_uint endDate,
        const char* clientId, WormExportTarCallback callback, void* callbackData);
        WORMAPI WormError WORMAPI_CALL worm_export_tar_filtered_transaction(
        WormContext* context, worm_uint transactionNumberStart,
        worm_uint transactionNumberEnd, const char* clientId,
        WormExportTarCallback callback, void* callbackData);

        WORMAPI WormError WORMAPI_CALL worm_export_deleteStoredData(WormContext* context);



#endif /* SE_API_FISCADE_FISCADE_WORMAPI_H_ */
