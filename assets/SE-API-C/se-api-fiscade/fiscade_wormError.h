/*
 * wormError.h
 */

#ifndef SE_API_FISCADE_WORMERROR_H_
#define SE_API_FISCADE_WORMERROR_H_

       	/*
        Found at https://github.com/fiskaltrust/middleware/blob/main/scu-de/src/fiskaltrust.Middleware.SCU.DE.Swissbit/Interop/NativeFunctionPointer.cs

        Error codes.

        All methods that can fail return a @ref WormError to indicate if they
        completed successfully. A return value of @ref WORM_ERROR_NOERROR means
        the method succeeded without an error. All other values indicate an
        error condition, which usually stems from a usage error and can not
        be handled by the caller in a meaningful way.
        */
        enum WormError
        {
            /* No error. */
            WORM_ERROR_NOERROR = 0,

            /* Invalid input parameter. */
            WORM_ERROR_INVALID_PARAMETER = 1,

            /* No TSE was found at the provided path. */
            WORM_ERROR_NO_WORM_CARD = 2,

            /* IO Error. */
            WORM_ERROR_IO = 3,

            /* Operation timed out. */
            WORM_ERROR_TIMEOUT = 4,

            /* Out of memory. */
            WORM_ERROR_OUTOFMEM = 5,

            /* Invalid Response from TSE. */
            WORM_ERROR_INVALID_RESPONSE = 6,

            /* The TSE Store is full. */
            WORM_ERROR_STORE_FULL_INTERNAL = 7,

            /* A command was not acknowledged, i.e. it was ignored by the card.
              This happens if two commands are sent at the same time or if a command is
              not allowed in the current state.
            */
            WORM_ERROR_RESPONSE_MISSING = 8,

            /* TSE not initialized. */
            WORM_ERROR_EXPORT_NOT_INITIALIZED = 9,

            /* Export Failed. */
            WORM_ERROR_EXPORT_FAILED = 10,

            /* Incremental Export: invalid state. */
            WORM_ERROR_INCREMENTAL_EXPORT_INVALID_STATE = 11,

            /* Incremental Export: no new data. */
            WORM_ERROR_INCREMENTAL_EXPORT_NO_DATA = 12,

            /* A power cycle occurred during command execution. */
            WORM_ERROR_POWER_CYCLE_DETECTED = 13,

            /* The firmware update was not properly applied. */
            WORM_ERROR_FIRMWARE_UPDATE_NOT_APPLIED = 14,

            /* Failed to start the background thread for keeping the TSE awake. */
            WORM_ERROR_THREAD_START_FAILED = 15,

            /** Firmware Update: No update is available for the TSE. */
            WORM_ERROR_FWU_NOT_AVAILABLE = 26,

            /* Lowest error code that might be raised from the TSE. */
            WORM_ERROR_FROM_CARD_FIRST = 0x1000,

            /* Unspecified, internal processing error. */
            WORM_ERROR_UNKNOWN = 0x1001,

            /* Time not set. */
            WORM_ERROR_NO_TIME_SET = 0x1002,

            /* No transaction in progress. */
            WORM_ERROR_NO_TRANSACTION_IN_PROGRESS = 0x1004,

            /* Wrong command length. */
            WORM_ERROR_INVALID_CMD_SYNTAX = 0x1005,

            /* @deprecated Use @ref WORM_ERROR_INVALID_CMD_SYNTAX instead. */
            WORM_ERROR_WRONG_LENGTH = WORM_ERROR_INVALID_CMD_SYNTAX,

            /* Not enough data written during transaction. */
            WORM_ERROR_NOT_ENOUGH_DATA_WRITTEN = 0x1006,

            /* Invalid Parameter. */
            WORM_ERROR_TSE_INVALID_PARAMETER = 0x1007,

            /* Given transaction is not started. */
            WORM_ERROR_TRANSACTION_NOT_STARTED = 0x1008,

            /* Maximum parallel transactions reached. */
            WORM_ERROR_MAX_PARALLEL_TRANSACTIONS = 0x1009,

            /* Certificate expired. */
            WORM_ERROR_CERTIFICATE_EXPIRED = 0x100a,

            /* No last transaction to fetch. */
            WORM_ERROR_NO_LAST_TRANSACTION = 0x100c,

            /* Command not allowed in current state. */
            WORM_ERROR_CMD_NOT_ALLOWED = 0x100d,

            /* Signatures exceeded. */
            WORM_ERROR_TRANSACTION_SIGNATURES_EXCEEDED = 0x100e,

            /* Not authorized. */
            WORM_ERROR_NOT_AUTHORIZED = 0x100f,

            /* Maximum registered clients reached. */
            WORM_ERROR_MAX_REGISTERED_CLIENTS_REACHED = 0x1010,

            /* Client not registered. */
            WORM_ERROR_CLIENT_NOT_REGISTERED = 0x1011,

            /* Failed to delete, data not completely exported. */
            WORM_ERROR_EXPORT_UNACKNOWLEDGED_DATA = 0x1012,

            /* Failed to deregister, client has unfinished transactions. */
            WORM_ERROR_CLIENT_HAS_UNFINISHED_TRANSACTIONS = 0x1013,

            /* Failed to decommission, TSE has unfinished transactions. */
            WORM_ERROR_TSE_HAS_UNFINISHED_TRANSACTIONS = 0x1014,

            /* Wrong state, there is no response to fetch. */
            WORM_ERROR_TSE_NO_RESPONSE_TO_FETCH = 0x1015,

            /* Wrong state, ongoing Filtered Export must be finished before this command
               is allowed. */
            WORM_ERROR_NOT_ALLOWED_EXPORT_IN_PROGRESS = 0x1016,

            /* Operation failed, not enough remaining capacity in TSE Store. */
            WORM_ERROR_STORE_FULL = 0x1017,

            /* Wrong state, changed PUK required. */
            WORM_ERROR_WRONG_STATE_NEEDS_PUK_CHANGE = 0x1050,

            /* Wrong state, changed PIN required. */
            WORM_ERROR_WRONG_STATE_NEEDS_PIN_CHANGE = 0x1051,

            /* Wrong state, active CTSS interface required. */
            WORM_ERROR_WRONG_STATE_NEEDS_ACTIVE_CTSS = 0x1053,

            /* @deprecated Use @ref WORM_ERROR_WRONG_STATE_NEEDS_ACTIVE_CTSS instead. */
            WORM_ERROR_WRONG_STATE_NEEDS_ACTIVE_ERS =
                WORM_ERROR_WRONG_STATE_NEEDS_ACTIVE_CTSS,

            /* Wrong state, self test must be run first. */
            WORM_ERROR_WRONG_STATE_NEEDS_SELF_TEST = 0x1054,

            /* Wrong state, passed self test required. */
            WORM_ERROR_WRONG_STATE_NEEDS_SELF_TEST_PASSED = 0x1055,

            /* Firmware Update: Integrity check failed. */
            WORM_ERROR_FWU_INTEGRITY_FAILURE = 0x1061,

            /* Firmware Update: Decryption failed. */
            WORM_ERROR_FWU_DECRYPTION_FAILURE = 0x1062,

            /* Firmware Update: Wrong format. */
            WORM_ERROR_FWU_WRONG_FORMAT = 0x1064,

            /* Firmware Update: Internal error. */
            WORM_ERROR_FWU_INTERNAL_ERROR = 0x1065,

            /* Firmware Update: downgrade prohibited. */
            WORM_ERROR_FWU_DOWNGRADE_PROHIBITED = 0x1067,

            /* TSE already initialized. */
            WORM_ERROR_TSE_ALREADY_INITIALIZED = 0x10FD,

            /* TSE decommissioned. */
            WORM_ERROR_TSE_DECOMMISSIONED = 0x10FE,

            /* TSE not initialized. */
            WORM_ERROR_TSE_NOT_INITIALIZED = 0x10FF,

            /* Authentication failed. */
            WORM_ERROR_AUTHENTICATION_FAILED = 0x1100,

            /* PIN is blocked. */
            WORM_ERROR_AUTHENTICATION_PIN_BLOCKED = 0x1201,

            /* Given user is not authenticated. */
            WORM_ERROR_AUTHENTICATION_USER_NOT_LOGGED_IN = 0x1202,

            /* Self test of FW failed. */
            WORM_ERROR_SELF_TEST_FAILED_FW = 0x1300,

            /* Self test of CSP failed. */
            WORM_ERROR_SELF_TEST_FAILED_CSP = 0x1310,

            /* Self test of RNG failed. */
            WORM_ERROR_SELF_TEST_FAILED_RNG = 0x1320,

            /* Firmware Update: Base FW update error. */
            WORM_ERROR_FWU_BASE_FW_ERROR = 0x1400,

            /* Firmware Update: FW Extension update error. */
            WORM_ERROR_FWU_FWEXT_ERROR = 0x1500,

            /* Firmware Update: CSP update error. */
            WORM_ERROR_FWU_CSP_ERROR = 0x1600,

            /* Filtered Export: no export in progress. */
            WORM_ERROR_EXPORT_NONE_IN_PROGRESS = 0x2001,

            /* Filtered Export: no new data, keep polling. */
            WORM_ERROR_EXPORT_RETRY = 0x2002,

            /* Filtered Export: no matching entries, export would be empty. */
            WORM_ERROR_EXPORT_NO_DATA_AVAILABLE = 0x2003,

            /* Command not found. */
            WORM_ERROR_CMD_NOT_FOUND = 0xf000,

            /* Signature creation error. */
            WORM_ERROR_SIG_ERROR = 0xff00,

            /* Highest error code that might be raised from the TSE. */
            WORM_ERROR_FROM_CARD_LAST = 0xFFFF
        };

#endif /* SE_API_FISCADE_WORMERROR_H_ */
