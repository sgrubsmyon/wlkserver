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
  * @file se_result_t.h
  *
  * @brief Return code definitions for the cryptovision SE-API and _extended_ SE_API.
  *
  * @addtogroup SE-API-common
  *
  * @{
  */

#ifndef SE_RESULT_T_H
#define SE_RESULT_T_H

/**
* TSE errors and return codes.
* The table specifies the numerical value (in @x{hexadecimal} / decimal notation) and a descriptive text for the error.
*/
typedef enum SeReturnCode
{
	ExecutionOk							= 0,            /**< (@x{0x0000} /     0) - no error */

	ErrorMissingParameter				= 0x1000,		/**< (@x{0x1000} /  4096) - a mandatory input parameter is NULL */
	ErrorFunctionNotSupported,							/**< (@x{0x1001} /  4097) - the function is not supported */
	ErrorAllocationfailed,								/**< (@x{0x1002} /  4098) - the memory allocation for an output parameter failed */
	ErrorFileNotFound,									/**< (@x{0x1003} /  4099) - transport I/O configuration file not found */
	ErrorSECommunicationFailed,							/**< (@x{0x1004} /  4100) - communication with Secure Element failed */
	ErrorTSECommandDataInvalid,							/**< (@x{0x1005} /  4101) - invalid TSE command data */
	ErrorTSEResponseDataInvalid,						/**< (@x{0x1006} /  4102) - invalid TSE response data */
	ErrorTSEUnknownError,								/**< (@x{0x1007} /  4103) - unknown TSE error code */
	ErrorStreamWrite,									/**< (@x{0x1008} /  4104) - write to output stream failed */
	ErrorIO,											/**< (@x{0x1009} /  4105) - transport I/O connection error */
	ErrorTSETimeout,									/**< (@x{0x100A} /  4106) - transport I/O timeout error */
	ErrorBufferTooSmall,								/**< (@x{0x100B} /  4107) - transport I/O buffer too small */
	ErrorCallback,										/**< (@x{0x100C} /  4108) - callback function failed (e.g.\ se_writer_t export data callback) */
	ErrorTSEFirmwareVersion,							/**< (@x{0x100D} /  4109) - TSE firmware incompatible with API version */
	ErrorTransport,										/**< (@x{0x100E} /  4110) - data fragmentation on transport layer */
	ErrorNoStartup,										/**< (@x{0x100F} /  4111) - TSE start command no called */
	ErrorNoStorage,										/**< (@x{0x1010} /  4112) - Transaction operation not allowed due to low log memory or no more ERS mappings available */
	ErrorResponseHeader,								/**< (@x{0x1011} /  4113) - transport I/O invalid response header */
	ErrorStaleIO,										/**< (@x{0x1012} /  4114) - transport I/O response with command header */
	ErrorResponseTooBig,								/**< (@x{0x1013} /  4115) - didn't read all of response data */
	ErrorSelftestFailed,								/**< (@x{0x1014} /  4116) - some hardware test failed during se_open*(). Device is open! */

	ErrorAuthenticationFailed			= 0x2000,		/**< (@x{0x2000} /  8192) - return value for the SE API function authenticateUser, authentication failed */
	ErrorUnblockFailed,									/**< (@x{0x2001} /  8193) - return value for the SE API function unblockUser, unblock failed */

	ErrorRetrieveLogMessageFailed		= 0x3000,		/**< (@x{0x3000} / 12288) - the retrieving of the log message parts that have been created by Secure Element most recently failed */
	ErrorStorageFailure,								/**< (@x{0x3001} / 12289) - storing of the log message in the storage failed */
	ErrorUpdateTimeFailed,								/**< (@x{0x3002} / 12290) - the execution of the Secure Element functionality for setting the time failed */
	ErrorParameterMismatch,								/**< (@x{0x3003} / 12291) - there is a mismatch regarding the particular parameters that have been provided in the context of the export of stored data */
	ErrorIdNotFound,									/**< (@x{0x3004} / 12292) - no data has been found for the provided clientID in the context of the export of stored data */
	ErrorNoSuchKey,										/**< (@x{0x3005} / 12293) - unknown key serial number (hash of public key) */
	ErrorERSalreadyMapped,								/**< (@x{0x3006} / 12294) - the serial number of an ERS is already mapped to a signature key */
	ErrorNoERS,											/**< (@x{0x3007} / 12295) - unknown ERS */
	ErrorNoKey,											/**< (@x{0x3008} / 12296) - unknown signature key */
	ErrorTransactionNumberNotFound,						/**< (@x{0x3009} / 12297) - no data has been found for the provided transaction number(s) in the context of the export of stored data */
	ErrorNoDataAvailable,								/**< (@x{0x300A} / 12298) - no data has been found for the provided selection in the context of the export of stored data */
	ErrorTooManyRecords,								/**< (@x{0x300B} / 12299) - the amount of requested records exceeds the passed value for the maximum number of records in the context of the export of stored data */
	ErrorStartTransactionFailed,						/**< (@x{0x300C} / 12300) - the execution of the Secure Element functionality to start a transaction failed */
	ErrorUpdateTransactionFailed,						/**< (@x{0x300D} / 12301) - the execution of the Secure Element functionality for updating a transaction failed */
	ErrorFinishTransactionFailed,						/**< (@x{0x300E} / 12302) - the execution of the Secure Element functionality for finishing a transaction failed */
	ErrorRestoreFailed,									/**< (@x{0x300F} / 12303) - the restore process in the context of a restoring from a backup in form of exported data failed */
	ErrorStoringInitDataFailed,							/**< (@x{0x3010} / 12304) - the storing of the initialization data during the commissioning of the SE API by the application operator failed */
	ErrorExportCertFailed,								/**< (@x{0x3011} / 12305) - the collection of the certificates for the export failed */
	ErrorNoLogMessage,									/**< (@x{0x3012} / 12306) - no log message parts have been found in the Secure Element */
	ErrorReadingLogMessage,								/**< (@x{0x3013} / 12307) - the retrieving of the log message parts that have been created from Secure Element most recently failed */
	ErrorNoTransaction,									/**< (@x{0x3014} / 12308) - no transaction is known to be open under the provided transaction number */
	ErrorSeApiNotInitialized,							/**< (@x{0x3015} / 12309) - the SE has not been initialized */
	ErrorSeApiDeactivated,								/**< (@x{0x3016} / 12310) - the SE is temporary deactivated */
	ErrorSeApiNotDeactivated,							/**< (@x{0x3017} / 12311) - the SE is not deactivated */
	ErrorTimeNotSet,									/**< (@x{0x3018} / 12312) - the managed data/time in the Secure Element has not been updated after the initialization of the SE API or a period of absence of current for the Secure Element */
	ErrorCertificateExpired,							/**< (@x{0x3019} / 12313) - the certificate with the public key for the verification of the appropriate type of log messages is expired */
	ErrorSecureElementDisabled,							/**< (@x{0x301A} / 12314) - SE API functions are invoked although the Secure Element has been disabled */
	ErrorUserNotAuthorized,								/**< (@x{0x301B} / 12315) - the user who has invoked a restricted SE API function is not authorized to execute this function */
	ErrorUserNotAuthenticated,							/**< (@x{0x301C} / 12316) - the user who has invoked a restricted SE API function has not the status "authenticated" */
	ErrorDescriptionNotSetByManufacturer,				/**< (@x{0x301D} / 12317) - the function initialize has been invoked without a value for the input parameter description although the description of the SE API has not been set by the manufacturer */
	ErrorDescriptionSetByManufacturer,					/**< (@x{0x301E} / 12318) - the function initialize has been invoked with a value for the input parameter description although the description of the SE API has been set by the manufacturer */
	ErrorExportSerialNumbersFailed,						/**< (@x{0x301F} / 12319) - collection of the serial number(s) failed */
	ErrorGetMaxNumberOfClientsFailed,					/**< (@x{0x3020} / 12320) - determination of the maximum number of clients that could use the SE API simultaneously failed */
	ErrorGetCurrentNumberOfClientsFailed,				/**< (@x{0x3021} / 12321) - determination of the current number of clients using the SE API failed */
	ErrorGetMaxNumberTransactionsFailed,				/**< (@x{0x3022} / 12322) - determination of the maximum number of transactions that can be managed simultaneously failed */
	ErrorGetCurrentNumberOfTransactionsFailed,			/**< (@x{0x3023} / 12323) - determination of the number of currently opened transactions failed */
	ErrorGetSupportedUpdateVariantsFailed,				/**< (@x{0x3024} / 12324) - identification of the supported variant(s) for updating transactions failed */
	ErrorDeleteStoredDataFailed,						/**< (@x{0x3025} / 12325) - deletion of the data from the storage failed */
	ErrorUnexportedStoredData,							/**< (@x{0x3026} / 12326) - deletion of data from the storage failed because the storage contains data that has not been exported */
	ErrorSigningSystemOperationDataFailed,				/**< (@x{0x3027} / 12327) - determination of the log message parts for the system operation data by the Secure Element failed */
	ErrorUserIdNotManaged,								/**< (@x{0x3028} / 12328) - userId is not managed by the SE API */
	ErrorUserIdNotAuthenticated,						/**< (@x{0x3029} / 12329) - userId has not the status authenticated */
	ErrorDisableSecureElementFailed,					/**< (@x{0x302A} / 12330) - deactivation of the Secure Element failed */
	
	ErrorClassSD						= 0x4000,		/**< any value from @x{0x4000} to @x{0x40FF} (16384 to 16640) indicates an unexpected error from the SD card transport adapter */

	ErrorClassFirmwareUpdate			= 0x5000		/**< any value from @x{0x5000} to @x{0x52FF} (20480 to 21247) indicates an unexpected error in firmware update */
} se_result_t;

#endif  /* SE_RESULT_T_H */

/** @}  SE-API  */
