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
  * @file se_api.h
  *
  * @brief Data type and functional definitions for the cryptovision SE-API.
  *
  * @addtogroup   SE-API
  * @brief        The cryptovision standard SE-API - providing access to **a single** TSE.
  *
  * The standard version of the SE-API provides access to a single TSE within a process (program).
  *
  * @note   The standard SE-API uses the @ref SE-API-extended "extended SE-API" with a single static context.
  *
  * @{
  */

#ifndef SE_API_H
#define SE_API_H

#include <stdint.h>

#include <stdio.h>
#include <stdlib.h>

#include <se_define.h>
#include <se_types.h>
#include <se_result_t.h>
#include <se_callback_t.h>


#ifdef __cplusplus
extern "C" {
#endif  

/**
 * - DllMain to close open TSE handle before unload
 * - additional helpers (useful for API testing only)
 */
#if defined(_WIN32) 
#define do_expand(val)  val ## 1
#define expand(val)     do_expand(val)
#if (expand(SE_STDCALL) == 1)
#define VBA_MAGIC 1
#ifndef _DEBUG /* debug assertions kill fwrite... - only export in release build */
	SE_API_DECL(errno_t, se_fopen_s)(FILE** stream, const char* filename, const char* mode);
	SE_API_DECL(int, se_fclose)(FILE* stream);
#endif
#endif
#endif

	/**
	* Get version of TSE.
	* @return     TSE version.
	* @since v2.4.1
	*/
	SE_API_DECL(const se_tse_version_t, se_getHardwareVersion)();

	/**
	* Check if device is an engineering samples.
	* @param[out] isES
	*                1 if factory reset is available.
	* @return @ref ExecutionOk                  execution of the function has been successful
	* @since v3.0
	*/
	SE_API_DECL(se_result_t, se_isEngineeringSample)(uint8_t* isES);

	/**
	* Get version strings of SE-API-C.
	* @return     SE-API-C version string (null terminated)
	* @since v2.0
	*/
	SE_API_DECL(const char*, se_getApiVersionString)();

	/**
	* Get version of SE-API-C.
	* @param[out] versionLength
	*                length of the returned version byte array [REQUIRED]
	*
	* @return     Pointer to SE-API-C version byte array; NULL if versionLength == NULL.
	* @since v2.0
	*/
	SE_API_DECL(const uint8_t*, se_getApiVersion)(uint32_t *versionLength);

	/**
	* Get version strings of SE-API-C implementation.
	* @return     SE-API-C implementation version string (null terminated)
	* @since v2.0
	*/
	SE_API_DECL(const char*, se_getImplementationVersionString)();

	/**
	* Get version of SE-API-C implementation.
	* @param[out] versionLength
	*                length of the returned version byte array [REQUIRED]
	*
	* @return     Pointer to SE-API-C implementation version byte array; NULL if versionLength == NULL.
	* @since v2.0
	*/
	SE_API_DECL(const uint8_t*, se_getImplementationVersion)(uint32_t *versionLength);

	/**
	* Get an identifier guaranteed to be unambiguous for every cryptovision TSE.
	* @param[out] idLength
	*                length of the returned identifier byte array [REQUIRED]
	*
	* @return     Pointer to identifier byte array; NULL if idLength == NULL or TSE connection not open.
	* @since v2.1
	*/
	SE_API_DECL(const uint8_t*, se_getUniqueId)(uint32_t *idLength);

	/**
	* Get raw TSE core temperature value.
	* @param[out] temp
	*                raw TSE core temperature value
	*
	* @return @ref ExecutionOk                  execution of the function has been successful
	* @since v3.0
	*/
	SE_API_DECL(se_result_t, se_getTemperature)(uint32_t *temp);

	/**
	* Get TSE core temperature in °C if vcc was given correctly.
	* @param[in]  vcc
	*                exact µSD supply voltage in mV
	* @param[out] temp
	*                core temperature in 0.1 °C, +/- 3K
	*
	* @return @ref ExecutionOk                  execution of the function has been successful
	* @since v3.0
	*/
	SE_API_DECL(se_result_t, se_getTemperature1)(uint32_t vcc, uint32_t *temp);

	/**
	* Get certification ID as assigned by BSI ("BSI-K-TR-0374-2019" for cryptovision TSE).
	* @param[out] certificationId
	*                Returned identifier string (not null terminated) [REQUIRED]\n
	*                If successfully executed, the buffer has to freed by the function caller [@ref se_free()].
	* @param[out] certificationIdLength
	*                length of the returned identifier string [REQUIRED]
	*
	* @return @ref ExecutionOk                  execution of the function has been successful
	* @return @ref ErrorSECommunicationFailed   Secure Element communication failed
	* @since v2.1
	*/
	SE_API_DECL(se_result_t, se_getCertificationId)(char **certificationId,
		uint32_t *certificationIdLength);

	/**
	* Get firmware identifier of a cryptovision TSE.
	* @return     TSE firmware version string (null terminated) or NULL if TSE connection not open.
	* @since v2.1
	*/
	SE_API_DECL(const char*, se_getFirmwareId)();

	/**
	* Apply firmware update to TSE.
	* @param[in] binary
	*				 firmware image
	* @param[in] binaryLength
	*				 size of firmware image (bytes)
	*
	* Requires IO timeout of at least 5000ms.
	* Requires Admin authentication.
	* Requires lcsActive or lcsNoTime
	* Recommends time set.
	* 
	* @throws ExcecutionOk
	* @throws ErrorStorageFailure
	* @throws ErrorSeApiNotInitialized
	* @throws ErrorCertificateExpired
	* @throws ErrorSecureElementDisabled
	* @throws ErrorUserNotAuthorized
	* @throws ErrorUserNotAuthenticated
	* @throws ErrorFirmwareUpdateFailed
	* @since v2.4.0
	*/
	SE_API_DECL(se_result_t, se_updateFirmware)(const uint8_t* binary, uint32_t binaryLength);

	/**
	* Get TSE life cycle state.
	* @param[out] lcs
	*                life cycle state of TSE [REQUIRED].
	*
	* @return @ref ExecutionOk                  execution of the function has been successful
	* @return @ref ErrorSECommunicationFailed   Secure Element communication failed
	* @since v2.0
	*/
	SE_API_DECL(se_result_t, se_getLifeCycleState)(se_lcs_t *lcs);

	/**
	* Open TSE transport I/O connection.
	*
	* @note   The config file parser is not (yet) implemented.\n
	*         Please use @ref se_openDirect() instead.
	*
	* @param[in] configFileName
	*                configuration file name for the I/O transport.
    *
    * @return @ref ExecutionOk              execution of the function has been successful
	* @return @ref ErrorFileNotFound        configuration file not found
	* @return @ref ErrorIO                  close connection failed
	*/
	SE_API_DECL(se_result_t, se_open)(const char *configFileName);

	/**
	* Open TSE transport I/O connection.
	*
	* @param[in]      devicePath
	*                   path to the TSE [REQUIRED]\n
	*                   for more information, please see @ref TLConfiguration
	* @param[in]      timeout
    *                   time-out value (milliseconds) [OPTIONAL]\n
    *                   if zero, the @ref SE_DEFAULT_IO_TIMEOUT is used\n
	*                   for more information, please see @ref TLConfiguration
    *
    * @return @ref ExecutionOk  execution of the function has been successful
    * @return @ref ErrorIO      failed to open the device
	*
    * @see se_transportOpen ()
	*/
	SE_API_DECL(se_result_t, se_openDirect)(const char *devicePath, uint32_t timeout);

	/**
	* Open TSE transport I/O connection.
	*
	* @param[in]      devicePath
	*                   path to the TSE [REQUIRED]\n
	*                   for more information, please see @ref TLConfiguration
	* @param[in]      timeout
	*                   time-out value (milliseconds) [OPTIONAL]\n
	*                   if zero, the @ref SE_DEFAULT_IO_TIMEOUT is used\n
	*                   for more information, please see @ref TLConfiguration
	* @param[in]      maxResponse
	*                   maximum response size sent by the TSE [OPTIONAL]\n
	*                   if zero, @ref SE_MAX_RESPONSE_8k is used\n
	*                   response size can be reduced from 8k to 4k (@ref SE_MAX_RESPONSE_4k)\n
	*                   no other values supported, TSEv2 only
	*
	* @return @ref ExecutionOk            execution of the function has been successful
	* @return @ref ErrorIO                failed to open the device
	* @return @ref ErrorParameterMismatch maxResponse invalid
	*
	* @since v2.4.1
	*/
	SE_API_DECL(se_result_t, se_openDirect1)(const char *devicePath, uint32_t timeout, uint32_t maxResponse);

	/**
	* Open TSE transport I/O connection.
	*
	* @param[in]      devicePath
	*                   path to the TSE [REQUIRED]\n
	*                   for more information, please see @ref TLConfiguration
	* @param[in]      timeout
	*                   time-out value (milliseconds) [OPTIONAL]\n
	*                   if zero, the @ref SE_DEFAULT_IO_TIMEOUT is used\n
	*                   for more information, please see @ref TLConfiguration
	* @param[in]      maxResponse
	*                   maximum response size sent by the TSE [OPTIONAL]\n
	*                   if zero, @ref SE_MAX_RESPONSE_8k is used\n
	*                   response size can be reduced from 8k to 4k (@ref SE_MAX_RESPONSE_4k)\n
	*                   no other values supported, TSEv2 only
	* @param[in]      checkIntegrity
	*                   enable/disable TSE internal initial integrity check\n
	*                   @ref SE_DO_CHECK_INTEGRITY or @ref SE_NO_INTEGRITY_CHECK \n
	*                   ignored before TSE v2.1\n
	*                   check takes up to about 5 seconds
	*
	* @return @ref ExecutionOk            execution of the function has been successful
	* @return @ref ErrorIO                failed to open the device
	* @return @ref ErrorParameterMismatch maxResponse invalid
	*
	* @since v3.1.0
	*/
	SE_API_DECL(se_result_t, se_openDirect2)(const char *devicePath, uint32_t timeout, uint32_t maxResponse, uint8_t checkIntegrity);

	/**
	* Reinitialize connection to TSE device.
	*
	* Can be used in lcsSleep or lcsClosed.
	* This might or might not power cycle or reset the device.
	*
	* @param[in]      devicePath
	*                   path to the TSE [REQUIRED]\n
	*                   for more information, please see @ref TLConfiguration
	* @param[in]      timeout
    *                   time-out value (milliseconds) [REQUIRED but ignored]\n
	*                   for more information, please see @ref TLConfiguration
	*
	* @note This will discard any previously set maxResponse setting! See @ref se_reopen2.
	*
	* @return @ref ExecutionOk					execution of the function has been successful
	* @return @ref ErrorIO						failed to open or close the devicei
	*
	* @since 2.4.0
	*/
	SE_API_DECL(se_result_t, se_reopen)(const char *devicePath, uint32_t timeout);

	/**
	* Reinitialize connection to TSE device.
	*
	* Can be used in lcsSleep or lcsClosed.
	* This might or might not power cycle or reset the device.
	*
	* @param[in]      devicePath
	*                   path to the TSE [REQUIRED]\n
	*                   for more information, please see @ref TLConfiguration
	* @param[in]      timeout
    *                   time-out value (milliseconds) [REQUIRED but ignored]\n
	*                   for more information, please see @ref TLConfiguration
	* @param[in]      maxResponse
	*                   maximum response size sent by the TSE [OPTIONAL]\n
	*                   if zero, @ref SE_MAX_RESPONSE_8k is used\n
	*                   response size can be reduced from 8k to 4k (@ref SE_MAX_RESPONSE_4k)\n
	*                   no other values supported, TSEv2 only
	* @param[in]      checkIntegrity
	*                   enable/disable TSE internal initial integrity check\n
	*                   @ref SE_DO_CHECK_INTEGRITY or @ref SE_NO_INTEGRITY_CHECK \n
	*                   ignored before TSE v2.1\n
	*                   check takes up to about 5 seconds
	*
	* @return @ref ExecutionOk					execution of the function has been successful
	* @return @ref ErrorIO						failed to open or close the devicei
	*
	* @since 3.1.0
	*/
	SE_API_DECL(se_result_t, se_reopen2)(const char *devicePath, uint32_t timeout, uint32_t maxResponse, uint8_t checkIntegrity);

	/**
	* Close TSE transport IO connection.
	*
    * @return @ref ExecutionOk if the execution of the function has been successful.
    * @return @ref ErrorIO failed to close the device
	*/
	SE_API_DECL(se_result_t, se_close)();

	/**
	* Start extended device self test.
	* Test runtime can be limited to not block the device for too long. Return value indicates if more
	* testing needs to done for full coverage. Device will continue testing on next call but start from
	* beginning after @ref se_openDirect() or @ref se_reopen().
	* @param[in] maxDuration
	*                intended test runtime in seconds [REQUIRED]
	* @param[out] result
	*                most recent test result
	*/
	SE_API_DECL(se_result_t, se_selfTest)(uint32_t maxDuration,
		se_self_test_result_t* result);

	/**
	* Get TSE PIN object status.
	* @param[out] pinState
	*                PIN state flags result buffer [REQUIRED].
	*
	* @return "PIN in transport state" per Admin PIN, Admin PUK, TimeAdmin PIN, TimeAdmin PUK.
	*
    * @return @ref ExecutionOk                  execution of the function has been successful
    * @return @ref ErrorSECommunicationFailed   Secure Element communication failed
	*/
	SE_API_DECL(se_result_t, se_getPinStatus)(se_pin_state_flags_t *pinState);

	/**
	* Initialized TSE pin objects.
	*
	* @note  The length of either PIN must be exactly  8 bytes.
	* @note  The length of either PUK must be exactly 10 bytes.
	* @note  PUK values cannot be changed once initialized.
	*
	* @param[in] adminPin
	*                Admin PIN value or NULL (PIN not touched)
	* @param[in] adminPinLength
	*                length of Admin PIN value: 8 (length) or 0 (PIN not touched)
	* @param[in] adminPuk
	*                Admin PUK value or NULL (PUK not touched)
	* @param[in] adminPukLength
	*                length of Admin PUK value: 10 (length) or 0 (PUK not touched)
	* @param[in] timeAdminPin
	*                TimeAdmin PIN value or NULL (PIN not touched)
	* @param[in] timeAdminPinLength
	*                length of TimeAdmin PIN value: 8 (length) or 0 (PIN not touched)
	* @param[in] timeAdminPuk
	*                TimeAdmin PUK value or NULL (PUK not touched)
	* @param[in] timeAdminPukLength
	*                length of TimeAdmin PUK value: 10 (length) or 0 (PUK not touched)
	*
    * @return @ref ExecutionOk                  execution of the function has been successful
    * @return @ref ErrorTSECommandDataInvalid   invalid TSE command data
    * @return @ref ErrorSECommunicationFailed   Secure Element communication failed
    *
	* @deprecated Use {@link se_initializePuk()} and {@link se_unblockUser()} instead to avoid communication timeouts.
	*/
	SE_API_DECL(se_result_t, se_initializePinValues)(const uint8_t *adminPin,
		uint32_t adminPinLength,
		const uint8_t *adminPuk,
		uint32_t adminPukLength,
		const uint8_t *timeAdminPin,
		uint32_t timeAdminPinLength,
		const uint8_t *timeAdminPuk,
		uint32_t timeAdminPukLength);

	/**
	* The function initialize starts the initialization of the SE API by the operator of the corresponding application.
	*
	* @note  An additional function with a different set of parameters exists:\n
	*        please see {@link se_initialize1()}.
	*
    * @return @ref ExecutionOk                              execution of the function has been successful
    * @return @ref ErrorSigningSystemOperationDataFailed    determination of the log message parts for the system operation data by the Secure Element failed
	* @return @ref ErrorStoringInitDataFailed               storing of the data for the description of the SE API failed
	* @return @ref ErrorRetrieveLogMessageFailed            execution of the Secure Element functionality to retrieve log message parts has failed
	* @return @ref ErrorStorageFailure                      storing of the log message failed
	* @return @ref ErrorCertificateExpired                  the certificate with the public key for the verification of the appropriate type of log messages is expired.
	*                                                       Even if a certificate expired, the log message parts are created by the Secure Element and stored by the SE API.
	* @return @ref ErrorSecureElementDisabled               the Secure Element has been disabled
	* @return @ref ErrorUserNotAuthorized                   the user who has invoked the function initialize is not authorized to execute this function
	* @return @ref ErrorUserNotAuthenticated                the user who has invoked the function initialize has not the status authenticated
	* @return @ref ErrorDescriptionNotSetByManufacturer     the function initializeDescriptionSet has been invoked without a value for the input parameter
	*                                                       description although the description of the SE API has not been set by the manufacturer
	* @return @ref ErrorDescriptionSetByManufacturer        the function has been invoked with a value for the input parameter description
	*                                                       although the description of the SE API has been set by the manufacturer
	* @return @ref ErrorSECommunicationFailed				the TSE has already been initialized
	*/
	SE_API_DECL(se_result_t, se_initialize)();

	/**
	* The function initialize starts the initialization of the SE API by the operator of the corresponding application.
	*
	* The initialization data in form of the description of the SE API is passed by the input parameter description.\n
	* The description of the SE API MUST NOT have been set by the manufacturer.
	*
	* @note  An additional function with a different set of parameters exists:\n
	*        please see {@link se_initialize()}.
	*
	* @param[in] description
	*                description of SE-API or NULL
	*
	* @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorSigningSystemOperationDataFailed    determination of the log message parts for the system operation data by the Secure Element failed
	* @return @ref ErrorStoringInitDataFailed               storing of the data for the description of the SE API failed
	* @return @ref ErrorRetrieveLogMessageFailed            execution of the Secure Element functionality to retrieve log message parts has failed
	* @return @ref ErrorStorageFailure                      storing of the log message failed
	* @return @ref ErrorCertificateExpired                  the certificate with the public key for the verification of the appropriate type of log messages is expired.
	*                                                       Even if a certificate expired, the log message parts are created by the Secure Element and stored by the SE API.
	* @return @ref ErrorSecureElementDisabled               the Secure Element has been disabled
	* @return @ref ErrorUserNotAuthorized                   the user who has invoked the function initialize is not authorized to execute this function
	* @return @ref ErrorUserNotAuthenticated                the user who has invoked the function initialize has not the status authenticated
	* @return @ref ErrorDescriptionNotSetByManufacturer     the function initializeDescriptionSet has been invoked without a value for the input parameter
	*                                                       description although the description of the SE API has not been set by the manufacturer
	* @return @ref ErrorDescriptionSetByManufacturer        the function has been invoked with a value for the input parameter description
	*                                                       although the description of the SE API has been set by the manufacturer
	* @return @ref ErrorSECommunicationFailed				the TSE has already been initialized
	* @since v2.1
	*/
	SE_API_DECL(se_result_t, se_initialize1)(const char* description);

	/**
	* This command can be used to temporarily deactivate the TSE.
	* It is meant to be used as protection of an entirely personalized TSE (i.e. with PINs assigned and ERSs mapped) during transport.
	* The function requires Admin Authentication and time set.
    *
    * @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorUserNotAuthorized                   the user who has invoked the function deactivateTSE is not authorized to execute this function
	* @return @ref ErrorUserNotAuthenticated                the user who has invoked the function deactivateTSE has not the status authenticated
	* @return @ref ErrorSeApiDeactivated                    TSE is already deactivated
	* @return @ref ErrorTimeNotSet							the managed data/time in the Secure Element has not been updated after the initialization of the SE API
	*                                                       or a period of absence of current for the Secure Element
	*
	* @deprecated Now defined by BSI as {@link se_lockTransactionLogging()}.
	*/
	SE_API_DECL(se_result_t, se_deactivateTSE)();

	/**
	* This command works identically to the @ref se_initialize() command.
	* It is meant to enable an entirely personalized TSE (i.e. with PINs assigned and ERSs mapped) after final installation in the ERS.
	* The function requires Admin Authentication.
    *
    * @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorUserNotAuthorized                   the user who has invoked the function deactivateTSE is not authorized to execute this function
	* @return @ref ErrorUserNotAuthenticated                the user who has invoked the function deactivateTSE has not the status authenticated
	* @return @ref ErrorSeApiNotDeactivated                 already activated
	*
	* @deprecated Now defined by BSI as {@link se_unlockTransactionLogging()}.
	*/
	SE_API_DECL(se_result_t, se_activateTSE)();

	/**
	* Requires Admin authentication.
	* Requires time set.
	* 
	* @return @ref ErrorUserNotAuthorized
	* @return @ref ErrorUserNotAuthenticated
	* @return @ref ErrorSeApiDeactivated
	* @return @ref ErrorTimeNotSet
	*
	* @since 2.4.0
	* 
	*/
	SE_API_DECL(se_result_t, se_lockTransactionLogging)();

	/**
	* Requires Admin authentication.
	*
	* @return @ref ErrorUserNotAuthorized
	* @return @ref ErrorUserNotAuthenticated
	* @return @ref ErrorSeApiNotDeactivated
	*
	* @since 2.4.0
	*
	*/
	SE_API_DECL(se_result_t, se_unlockTransactionLogging)();

	/**
	* Initialize PUK value if still in transport state.
	*
	* @note  PUK values cannot be changed once initialized.
	* 
	* @param[in] userId
	*          user ID of the PUK to be set.\n
	*          Valid user IDs are "Admin" and "TimeAdmin" (no quotes).
	* @param[in] userIdLength
	*          length of user ID.  
	* @param[in] puk 
	*		    new PUK byte array.
	* @param[in] pukLength
	*          length of puk byte array. must be 10 bytes.
	*
	* @return @ref ErrorUserIdNotManaged
	* @return @ref ErrorSECommunicationFailed e.g. PUK already initialized
	* @return @ref ErrorTSECommandDataInvalid e.g. wrong length
	*
	* @since 2.4.0
	*
	*/
	SE_API_DECL(se_result_t, se_initializePuk)(const char *userId, uint32_t userIdLength, const uint8_t *puk, uint32_t pukLength);

	/**
	* Map the serial number of an ERS to a signature key.
	* This assigns an existing private key to a client (cash register).<br>
    * Function is also used to delete such a mapping.
	* @param[in] clientId
	*                serial number of the ERS [REQUIRED]
	* @param[in] clientIdLength
	*                length of the array that represents the clientId (1 to 30) [REQUIRED]
	* @param[in] serialNumberKey
	*                ID of the key to be mapped (SHA256 hash value of the public key);<br>
	*                when <code>NULL</code> the client-mapping will be removed
	* @param[in] serialNumberLength
	*                length of the array that represents the serialNumberKey  [REQUIRED];<br>
	*                when zero (0) the client-mapping will be removed
    *
    * @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorSigningSystemOperationDataFailed    determination of the log message parts for the system operation data by the Secure Element failed
	* @return @ref ErrorStoringInitDataFailed               storing of the data for the description of the SE API failed
	* @return @ref ErrorRetrieveLogMessageFailed            execution of the Secure Element functionality to retrieve log message parts has failed
	* @return @ref ErrorStorageFailure                      storing of the log message has failed
	* @return @ref ErrorCertificateExpired                  the certificate with the public key for the verification of the appropriate type of log messages is expired.
	*                                                       Even if a certificate expired, the log message parts are created by the Secure Element and stored by the SE API.
	* @return @ref ErrorSecureElementDisabled               the Secure Element has been disabled
	* @return @ref ErrorUserNotAuthorized                   TSEv1 only - the user who has invoked the function is not authorized to execute this function
	* @return @ref ErrorUserNotAuthenticated                TSEv1 only - the user who has invoked the function has not the status authenticated
	* @return @ref ErrorNoSuchKey                           unknown serialNumberKey
	* @return @ref ErrorSECommunicationFailed               when <code>serialNumberKey == NULL</code>: clientId not mapped (TSE v1)
	* @return @ref ErrorNoERS                               when <code>serialNumberKey == null</code>: clientId not mapped
	* @return @ref ErrorERSalreadyMapped                    the serial number of an ERS is already mapped to a signature key
	*
	* @deprecated Use {@link se_registerClient()} instead.
	*/
	SE_API_DECL(se_result_t, se_mapERStoKey)(const char *clientId,
		uint32_t clientIdLength,
		const uint8_t *serialNumberKey,
		uint32_t serialNumberLength);

	/**
	* Delete a serial number mapping of an ERS.
	* @param[in] clientId
	*                serial number of the ERS [REQUIRED]
	* @param[in] clientIdLength
	*                length of the array that represents the clientId (1 to 30) [REQUIRED]
	*
	* @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorSigningSystemOperationDataFailed    determination of the log message parts for the system operation data by the Secure Element failed
	* @return @ref ErrorStoringInitDataFailed               storing of the data for the description of the SE API failed
	* @return @ref ErrorRetrieveLogMessageFailed            execution of the Secure Element functionality to retrieve log message parts has failed
	* @return @ref ErrorStorageFailure                      storing of the log message has failed
	* @return @ref ErrorCertificateExpired                  the certificate with the public key for the verification of the appropriate type of log messages is expired.
	*                                                       Even if a certificate expired, the log message parts are created by the Secure Element and stored by the SE API.
	* @return @ref ErrorSecureElementDisabled               the Secure Element has been disabled
	* @return @ref ErrorUserNotAuthorized                   TSEv1 only - the user who has invoked the function is not authorized to execute this function
	* @return @ref ErrorUserNotAuthenticated                TSEv1 only - the user who has invoked the function has not the status authenticated
	* @return @ref ErrorSECommunicationFailed               clientId / ERS serial number is not mapped (TSE v1)
	* @return @ref ErrorNoERS                               clientId / ERS serial number is not mapped
	*
	* @deprecated Use {@link se_deregisterClient()} instead.
	*/
	SE_API_DECL(se_result_t, se_unmapERS)(const char* clientId, uint32_t clientIdLength);

	/**
	* Register a clientId
	* This assigns an existing private key to a client (cash register).<br>
	* Function is also used to delete such a mapping.
	*
	* @param[in] clientId
	*                serial number of the ERS [REQUIRED]
	* @param[in] clientIdLength
	*                length of the array that represents the clientId (1 to 30) [REQUIRED]
	*
	* @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorSigningSystemOperationDataFailed    determination of the log message parts for the system operation data by the Secure Element failed
	* @return @ref ErrorStoringInitDataFailed               storing of the data for the description of the SE API failed
	* @return @ref ErrorRetrieveLogMessageFailed            execution of the Secure Element functionality to retrieve log message parts has failed
	* @return @ref ErrorStorageFailure                      storing of the log message has failed
	* @return @ref ErrorCertificateExpired                  the certificate with the public key for the verification of the appropriate type of log messages is expired.
	*                                                       Even if a certificate expired, the log message parts are created by the Secure Element and stored by the SE API.
	* @return @ref ErrorSeApiNotInitialized                 the SE API has not been initialized
	* @return @ref ErrorTimeNotSet                          the managed data/time in the Secure Element has not been updated after the initialization of the SE API
	*                                                       or a period of absence of current for the Secure Element
	* @return @ref ErrorSecureElementDisabled               the Secure Element has been disabled
	* @return @ref ErrorERSalreadyMapped                    the serial number of an ERS is already mapped to a signature key
	*
	* @since 2.4.0
	*/
	SE_API_DECL(se_result_t, se_registerClient)(const char *clientId, uint32_t clientIdLength);

	/**
	* Delete a clientId registration
	* This assigns an existing private key to a client (cash register).<br>
	* Function is also used to delete such a mapping.
	*
	* @param[in] clientId
	*                serial number of the ERS [REQUIRED]
	* @param[in] clientIdLength
	*                length of the array that represents the clientId (1 to 30) [REQUIRED]
	*
	* @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorSigningSystemOperationDataFailed    determination of the log message parts for the system operation data by the Secure Element failed
	* @return @ref ErrorStoringInitDataFailed               storing of the data for the description of the SE API failed
	* @return @ref ErrorRetrieveLogMessageFailed            execution of the Secure Element functionality to retrieve log message parts has failed
	* @return @ref ErrorStorageFailure                      storing of the log message has failed
	* @return @ref ErrorCertificateExpired                  the certificate with the public key for the verification of the appropriate type of log messages is expired.
	*                                                       Even if a certificate expired, the log message parts are created by the Secure Element and stored by the SE API.
	* @return @ref ErrorSeApiNotInitialized                 the SE API has not been initialized
	* @return @ref ErrorTimeNotSet                          the managed data/time in the Secure Element has not been updated after the initialization of the SE API
	*                                                       or a period of absence of current for the Secure Element
	* @return @ref ErrorSecureElementDisabled               the Secure Element has been disabled
	* @return @ref ErrorERSalreadyMapped                    the serial number of an ERS is already mapped to a signature key
	*
	* @since 2.4.0
	*/
	SE_API_DECL(se_result_t, se_deregisterClient)(const char *clientId, uint32_t clientIdLength);

	/**
	* The function updateTime updates the current date/time that is maintained by the Secure Element by passing a new date/time value
	* @param[in] unixTime
	*                new 64-bit Unix Time value for the date/time maintained by the Secure Element [REQUIRED; unixTime <= SE_MAX_UPDATE_TIME]
    *
    * @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorUpdateTimeFailed                    execution of the Secure Element functionality to set the time has failed
	* @return @ref ErrorRetrieveLogMessageFailed            execution of the Secure Element functionality to retrieve log message parts has failed
	* @return @ref ErrorStorageFailure                      storing of the log message has failed
	* @return @ref ErrorSeApiDeactivated                    TSEv1 only - TSE is already deactivated
	* @return @ref ErrorCertificateExpired                  the certificate with the public key for the verification of the appropriate type of log messages is expired.
	*                                                       Even if a certificate expired, the log message parts are created by the Secure Element and stored by the SE API.
	* @return @ref ErrorSecureElementDisabled               the Secure Element has been disabled
	* @return @ref ErrorUserNotAuthorized                   the user who has invoked the function updateTime is not authorized to execute this function
	* @return @ref ErrorUserNotAuthenticated                the user who has invoked the function updateTime has not the status authenticated
	*/
	SE_API_DECL(se_result_t, se_updateTime)(int64_t unixTime);

	/**
	* The function disableSecureElement disables the Secure Element in a way that none of its functionality can be used anymore
    *
    * @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorDisableSecureElementFailed          the deactivation of the Secure Element failed
	* @return @ref ErrorTimeNotSet                          the managed data/time in the Secure Element has not been updated after the initialization of the SE API
	*                                                       or a period of absence of current for the Secure Element
	* @return @ref ErrorRetrieveLogMessageFailed            execution of the Secure Element functionality to retrieve log message parts has failed
	* @return @ref ErrorStorageFailure                      storing of the data of the log message has failed
	* @return @ref ErrorCertificateExpired                  the certificate with the public key for the verification of the appropriate type of log messages is expired.
	*                                                       Even if a certificate expired, the log message parts are created by the Secure Element and stored by the SE API.
	* @return @ref ErrorSecureElementDisabled               the Secure Element has been disabled
	* @return @ref ErrorUserNotAuthorized                   the user who has invoked the function disableSecureElement is not authorized to execute this function
	* @return @ref ErrorUserNotAuthenticated                the user who has invoked the function disableSecureElement has not the status authenticated
	*/
	SE_API_DECL(se_result_t, se_disableSecureElement)();

	/**
	* Starts a new transaction
	* @param[in] clientId
	*                represents the ID of the application that has invoked the function [REQUIRED]
	* @param[in] clientIdLength
	*                length of the array that represents the clientId  [REQUIRED]
	* @param[in] processData
	*                represents all the necessary information regarding the initial state of the process [REQUIRED]\n
	*                A NULL pointer will be accepted, to allow for the contradicting requirement from the DSFinV-K \cite DSFinV-K, which allows / demands processData to be "empty".
	* @param[in] processDataLength
	*                length of the array that represents the processData [REQUIRED]\n
	*                A value of 0 (zero) will be accepted, to allow for the contradicting requirement from the DSFinV-K \cite DSFinV-K, which allows / demands processData to be "empty".
	* @param[in] processType
	*                identifies the type of the transaction as defined by the application.
	*                This string MUST NOT contain more than 100 characters [OPTIONAL]
	* @param[in] processTypeLength
	*                length of the string that represents the processType.
	*                If a null pointer is passed for the parameter processType, the value for the length SHALL be 0 [REQUIRED]
	* @param[in] additionalData
	*                RFU and must not be used according to TR-03151 [OPTIONAL]
	* @param[in] additionalDataLength
	*                length of the array that represents the additionalData.
	*                If a null pointer is passed for the parameter additionalData, the value for the length SHALL be 0 [REQUIRED]
	* @param[out] transactionResult
	*                result of the transaction
    *
    * @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorStartTransactionFailed              the execution of the Secure Element functionality to start a transaction failed
	* @return @ref ErrorRetrieveLogMessageFailed            the execution of the Secure Element functionality to retrieve log message parts has failed
	* @return @ref ErrorStorageFailure                      storing of the log message failed
	* @return @ref ErrorSeApiNotInitialized                 the SE API has not been initialized
	* @return @ref ErrorSeApiDeactivated                    TSE locked for transaction logging
	* @return @ref ErrorTimeNotSet                          the managed data/time in the Secure Element has not been updated after the initialization of the SE API
	*                                                       or a period of absence of current for the Secure Element
	* @return @ref ErrorCertificateExpired                  the certificate with the public key for the verification of the appropriate type of log messages is expired.
	*                                                       Even if a certificate expired, the log message parts are created by the Secure Element and stored by the SE API.
	* @return @ref ErrorSecureElementDisabled               the Secure Element has been disabled
	*/
	SE_API_DECL(se_result_t, se_startTransaction)(const char *clientId,
		uint32_t clientIdLength,
		const uint8_t *processData,
		uint32_t processDataLength,
		const char *processType,
		uint32_t processTypeLength,
		const uint8_t *additionalData,
		uint32_t additionalDataLength,
		se_start_transaction_result_t* transactionResult);

	/**
	* Updates an open transaction
	* @param[in] clientId
	*                represents the ID of the application that has invoked the function [REQUIRED]
	* @param[in] clientIdLength
	*                length of the array that represents the clientId  [REQUIRED]
	* @param[in] transactionNumber
	*                parameter is used to unambiguously identify the current transaction [REQUIRED]
	* @param[in] processData
	*                represents all the new information regarding the state of the process since the start
	*                of the corresponding transaction or its latest update [REQUIRED]
	* @param[in] processDataLength
	*                length of the array that represents the processData [REQUIRED]
	* @param[in] processType
	*                identifies the type of the transaction as defined by the application.
	*                This string MUST NOT contain more than 100 characters [OPTIONAL]
	* @param[in] processTypeLength
	*                length of the string that represents the processType.
	*                If a null pointer is passed for the parameter processType, the value for the length SHALL be 0 [REQUIRED]
	* @param[out] transactionResult
	*                result of the transaction
    *
    * @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorUpdateTransactionFailed             the execution of the Secure Element functionality to update a transaction failed
	* @return @ref ErrorRetrieveLogMessageFailed            the execution of the Secure Element functionality to retrieve log message parts has failed
	* @return @ref ErrorStorageFailure                      storing of the log message failed
	* @return @ref ErrorNoTransaction                       no transaction is known to be open under the provided transaction number
	* @return @ref ErrorSeApiNotInitialized                 the SE API has not been initialized
	* @return @ref ErrorSeApiDeactivated                    TSE locked for transaction logging
	* @return @ref ErrorTimeNotSet                          the managed data/time in the Secure Element has not been updated after the initialization of the SE API
	*                                                       or a period of absence of current for the Secure Element
	* @return @ref ErrorCertificateExpired                  the certificate with the public key for the verification of the appropriate type of log messages is expired.
	*                                                       Even if a certificate expired, the log message parts are created by the Secure Element and stored by the SE API.
	* @return @ref ErrorSecureElementDisabled               the Secure Element has been disabled
	*/
	SE_API_DECL(se_result_t, se_updateTransaction)(const char *clientId,
		uint32_t clientIdLength,
		uint32_t transactionNumber,
		const uint8_t *processData,
		uint32_t processDataLength,
		const char *processType,
		uint32_t processTypeLength,
		se_update_transaction_result_t* transactionResult);

	/**
	* Finishes an open transaction
	* @param[in] clientId
	*                represents the ID of the application that has invoked the function [REQUIRED]
	* @param[in] clientIdLength
	*                length of the array that represents the clientId  [REQUIRED]
	* @param[in] transactionNumber
	*                parameter is used to unambiguously identify the current transaction [REQUIRED]
	* @param[in] processData
	*                represents all the information regarding the final state of the process [REQUIRED]
	* @param[in] processDataLength
	*                length of the array that represents the processData [REQUIRED]
	* @param[in] processType
	*                identifies the type of the transaction as defined by the application
	*                This string MUST NOT contain more than 100 characters [OPTIONAL]
	* @param[in] processTypeLength
	*                length of the string that represents the processType.
	*                If a null pointer is passed for the parameter processType, the value for the length SHALL be 0 [REQUIRED]
	* @param[in] additionalData
	*                RFU and must not be used according to TR-03151 [OPTIONAL]
	* @param[in] additionalDataLength
	*                length of the array that represents the additionalData.
	*                If a null pointer is passed for the parameter additionalData, the value for the length SHALL be 0 [REQUIRED]
	* @param[out] transactionResult
	*                result of the transaction
    *
    * @return @ref ExecutionOk                              execution of the function has been successful
    * @return @ref ErrorFinishTransactionFailed             the execution of the Secure Element functionality to finish a transaction failed
    * @return @ref ErrorRetrieveLogMessageFailed            the execution of the Secure Element functionality to retrieve log message parts has failed
    * @return @ref ErrorStorageFailure                      storing of the log message failed
    * @return @ref ErrorNoTransaction                       no transaction is known to be open under the provided transaction number
    * @return @ref ErrorSeApiNotInitialized                 the SE API has not been initialized
	* @return @ref ErrorSeApiDeactivated                    TSE locked for transaction logging
    * @return @ref ErrorTimeNotSet                          the managed data/time in the Secure Element has not been updated after the initialization of the SE API
    *                                                       or a period of absence of current for the Secure Element
    * @return @ref ErrorCertificateExpired                  the certificate with the public key for the verification of the appropriate type of log messages is expired.
    *                                                       Even if a certificate expired, the log message parts are created by the Secure Element and stored by the SE API.
    * @return @ref ErrorSecureElementDisabled               the Secure Element has been disabled
	*/
	SE_API_DECL(se_result_t, se_finishTransaction)(const char *clientId,
		uint32_t clientIdLength,
		uint32_t transactionNumber,
		const uint8_t *processData,
		uint32_t processDataLength,
		const char *processType,
		uint32_t processTypeLength,
		const uint8_t *additionalData,
		uint32_t additionalDataLength,
		se_finish_transaction_result_t* transactionResult);

	/**
	* Get a list of dangling ("open") SE transactions.
	* @param[out] transactionNumbers
	*                array that represents the list of transactions [REQUIRED]\n
	*                If successfully executed, the buffer has to freed by the function caller [@ref se_free()].
	* @param[out] transactionNumbersLength
	*                length of the array that represents the list of transactions
    *
    * @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorSeApiNotInitialized                 the SE API has not been initialized
	* @return @ref ErrorSeApiDeactivated                    TSEv1 only
	* @return @ref ErrorTimeNotSet                          the managed data/time in the Secure Element has not been updated after the initialization of the SE API
	*                                                       or a period of absence of current for the Secure Element
	* @return @ref ErrorSecureElementDisabled               the Secure Element has been disabled
	*/
	SE_API_DECL(se_result_t, se_getOpenTransactions)(uint32_t **transactionNumbers,
		uint32_t *transactionNumbersLength);

	/**
	* Get size of tar file exported by {@link se_exportData()} methods.
	*
	* Use <code>null</code> to mark optional parameters as undefined.
	*
	* @note  An additional function with a different set of parameters exists:\n
	*        please see {@link se_getExportSize1()}.
	* @note  Function parameters match those in {@link se_exportData()}.\n
	*
	* @param[in]	clientId				ID of the ERS to export data for
	* @param[in]	clientIdLength			length of the array that represents the clientId 
	* @param[in]	transactionNumber		single transaction number to export
	* @param[in]	startTransactionNumber	start of transaction number range to export
	* @param[in]	endTransactionNumber	end of transaction number range to export
	* @param[in]	startDate				start of date range to export
	* @param[in]	endDate					end of date range to export
	* @param[out]   exportedDataLength        length of the array that represents the exportedData [REQUIRED]
	*
	* @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorIdNotFound
	* @return @ref ErrorTransactionNumberNotFound
	* @return @ref ErrorNoDataAvailable
	* @return @ref ErrorParameterMismatch
	* @return @ref ErrorSeApiNotInitialized
	* @return @ref ErrorSeApiDeactivated TSE v1 only
	* @since 2.4.0
	*/
	SE_API_DECL(se_result_t, se_getExportSize)(const char *clientId,
		uint32_t clientIdLength,
		uint32_t transactionNumber, 
		uint32_t startTransactionNumber, 
		uint32_t endTransactionNumber, 
		int64_t startDate,
		int64_t endDate,
		uint64_t *exportedDataLength);

	/**
	* Get size of tar file exported by {@link se_exportMoreData()}.
	*
	* @note  An additional function with a different set of parameters exists:\n
	*        please see {@link se_getExportSize()}.
	* @note  Function parameters match those in {@link se_exportMoreData()}.
	*
	* @param[in] 	previousSignatureCounter			last seen signature counter
	* @param[in]	maximumNumberRecords				max. number of records to export
	* @param[out]   exportedDataLength					length of the array that represents the exportedData [REQUIRED]
	*
	* @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorSeApiNotInitialized
	* @return @ref ErrorSeApiDeactivated					TSEv1 only
	* @return @ref ErrorNoSuchKey
	* @return @ref ErrorIdNotFound
	* @since 2.4.0
	*/
	SE_API_DECL(se_result_t, se_getExportSize1)(uint32_t previousSignatureCounter, 
		uint32_t maximumNumberRecords, 
		uint64_t *exportedDataLength);

	/**
	* Exports the transaction log messages, containing the process and protocol data, that are relevant for a certain
	* interval of transactions. The transaction log messages in this interval SHALL correspond to the passed clientId.
	* Additionally, the function SHALL export all system log messages and audit log messages whose signature counters
	* are contained in the interval determined either by transaction number or by date. A combination is not supported.
	* 
	* According to BSI TR-03151 \cite TR-03151
	* 1. If transactionNumber has been provided, neither startDate nor endDate SHALL be provided.
	* 2. If startTransactionNumber and endTransactionNumber have been provided, neither startDate nor endDate SHALL be provided.
	* 3. If provided, startDate and/or endDate MUST be valid date/time values.
	* 4. If startDate and endDate have been provided, endDate MUST lay after startDate.
	* 5. If a startDate and/or endDate have been provided, transactionNumber MUST NOT be provided.
	*
	* Furthermore, additional files that are needed to verify the signatures, included in the log messages, are exported.
	* @param[in] clientId
	*                ID of a client application that has used the API to log transactions.
	*                Only transaction log messages that corresponds to the clientId are relevant for the export [REQUIRED]
	* @param[in] clientIdLength
	*                length of the array that represents the clientId  [REQUIRED]
	* @param[in] transactionNumber
	*                defines the transaction number of relevant log messages [OPTIONAL] (SE_MAX_UINT32 for undefined)
	* @param[in] startTransactionNumber
	*                defines the transaction number (inclusive) regarding the start of the interval of relevant log messages [OPTIONAL] (0 for undefined)
	* @param[in] endTransactionNumber
	*                defines the transaction number (inclusive) regarding the end of the interval of relevant log messages [OPTIONAL] (SE_MAX_UINT32 for undefined)
	* @param[in] startDate
	*                defines the starting time (inclusive, 64 bit Unix Time) for the period in that the relevant log messages have been created [OPTIONAL] (0 for undefined).
	* @param[in] endDate
	*                defines the end time (inclusive, 64 bit Unix Time) for the period in that relevant log messages have been created [OPTIONAL] (SE_MAX_TIME for undefined).
	* @param[in] maximumNumberRecords
	*                if the value of this parameter is not 0, the function SHALL only return the log messages if the number
	*                of relevant records is less or equal to the number of maximum records.
	*                If the value of the parameter is 0, the function SHALL return all selected log messages [REQUIRED]
	* @param[out] exportedData
	*                selected log messages and additional files needed to verify the signatures included in the log messages [REQUIRED]\n
	*                If successfully executed, the buffer has to freed by the function caller [@ref se_free()].
	* @param[out] exportedDataLength
	*                length of the array that represents the exportedData [REQUIRED]
    *
    * @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorParameterMismatch                   mismatch in parameters of the function
	* @return @ref ErrorNoDataAvailable                     no data has been found for the provided selection
	* @return @ref ErrorTransactionNumberNotFound           no data has been found for the provided transaction numbers
	* @return @ref ErrorIdNotFound                          no data has been found for the provided clientId
	* @return @ref ErrorSeApiDeactivated                    TSEv1 only
	* @return @ref ErrorTooManyRecords                      the amount of requested records exceeds the parameter maximumNumberRecords
	* @return @ref ErrorSeApiNotInitialized                 the SE API has not been initialized
	*/
	SE_API_DECL(se_result_t, se_exportData)(const char *clientId,
		uint32_t clientIdLength,
		uint32_t transactionNumber,
		uint32_t startTransactionNumber,
		uint32_t endTransactionNumber,
		int64_t startDate,
		int64_t endDate,
		int32_t maximumNumberRecords,
		uint8_t **exportedData,
		uint32_t *exportedDataLength);

	/**
	* Exports the transaction log messages to a FILE stream.
	*
	* \note For common parameters, parameter evaluation, and return values see @ref se_exportData.
    *
	* @param[in]  clientId
	* @param[in]  clientIdLength
	* @param[in]  transactionNumber
	* @param[in]  startTransactionNumber
	* @param[in]  endTransactionNumber
	* @param[in]  startDate
	* @param[in]  endDate
	* @param[in]  maximumNumberRecords
	* @param[in]  stream
	*                output stream to store the selected log messages and additional files to [REQUIRED]
	*/
	SE_API_DECL(se_result_t, se_exportDataToStream)(const char *clientId,
		uint32_t clientIdLength,
		uint32_t transactionNumber,
		uint32_t startTransactionNumber,
		uint32_t endTransactionNumber,
		int64_t startDate,
		int64_t endDate,
		int32_t maximumNumberRecords,
		FILE *stream);

	/**
	* Exports the transaction log messages to a named file.
	* 
	* \note For common parameters, parameter evaluation, and return values see @ref se_exportData.
    *
	* @param[in]  clientId
	* @param[in]  clientIdLength
	* @param[in]  transactionNumber
	* @param[in]  startTransactionNumber
	* @param[in]  endTransactionNumber
	* @param[in]  startDate
	* @param[in]  endDate
	* @param[in]  maximumNumberRecords
	* @param[in]  fileName
	*                name of export file (existing files will be overwritten) [REQUIRED]
	*
	* @since v2.1
	*/
	SE_API_DECL(se_result_t, se_exportDataToFile)(const char *clientId,
		uint32_t clientIdLength,
		uint32_t transactionNumber,
		uint32_t startTransactionNumber,
		uint32_t endTransactionNumber,
		int64_t startDate,
		int64_t endDate,
		int32_t maximumNumberRecords,
		const char *fileName);

	/**
	* Exports the transaction log messages by means of a callback function.
	*
	* \note For common parameters, parameter evaluation, and return values see @ref se_exportData.
	* 
	* @param[in]  clientId
	* @param[in]  clientIdLength
	* @param[in]  transactionNumber
	* @param[in]  startTransactionNumber
	* @param[in]  endTransactionNumber
	* @param[in]  startDate
	* @param[in]  endDate
	* @param[in]  maximumNumberRecords
	* @param [in] writer
	*                address of the "writer" callback @ref se_writer_t()
	* @param [in] handle
	*                parameter to pass to writer; see: @ref se_handle_t
	*
	* @since v2.0
	*/
	SE_API_DECL(se_result_t, se_exportDataViaCallback)(const char *clientId,
		uint32_t clientIdLength,
		uint32_t transactionNumber,
		uint32_t startTransactionNumber,
		uint32_t endTransactionNumber,
		int64_t startDate,
		int64_t endDate,
		int32_t maximumNumberRecords,
		se_writer_t writer,
		se_handle_t handle);

	/**
	* Continue data export, e.g. immediately after last seen log entry...
	* @param[in] serialNumberKey
	*                ID of the key used in previous log entry (SHA256 hash value of the public key). \n
	*				 Since 2.4.0: A NULL pointer selects the @ref TSEPrimaryKey
	* @param[in] serialNumberLength
	*                length of the array that represents the serialNumberKey  [REQUIRED]
	* @param[in] previousSignatureCounter
	*                last seen signature counter [REQUIRED]
	* @param[in] maximumNumberRecords
	*                if the value of this parameter is not 0, the function SHALL only return the log messages if the number
	*                of relevant records is less or equal to the number of maximum records.
	*                If the value of the parameter is 0, the function SHALL return all selected log messages [REQUIRED]
	* @param[out] exportedData
	*                selected log messages and additional files needed to verify the signatures included in the log messages [REQUIRED]\n
	*                If successfully executed, the buffer has to freed by the function caller [@ref se_free()].
	* @param[out] exportedDataLength
	*                length of the array that represents the exportedData [REQUIRED]
    *
    * @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorParameterMismatch                   mismatch in parameters of the function
	* @return @ref ErrorNoDataAvailable                     no data has been found for the provided selection
	* @return @ref ErrorIdNotFound                          no data has been found for the provided clientId
	* @return @ref ErrorTooManyRecords                      the amount of requested records exceeds the parameter maximumNumberRecords
	* @return @ref ErrorSeApiNotInitialized                 the SE API has not been initialized
	* @since v2.0
	*/
	SE_API_DECL(se_result_t, se_exportMoreData)(const uint8_t *serialNumberKey,
		uint32_t serialNumberLength,
		uint32_t previousSignatureCounter,
		int32_t maximumNumberRecords,
		uint8_t **exportedData,
		uint32_t *exportedDataLength);

	/**
	* Continue data export, e.g. immediately after last seen log entry..., to a FILE stream.
	*
	* \note For common parameters, parameter evaluation, and return values see @ref se_exportMoreData.
    *
	* @param[in]  serialNumberKey
	* @param[in]  serialNumberLength
	* @param[in]  previousSignatureCounter
	* @param[in]  maximumNumberRecords
	* @param[in]  stream
	*                output stream to store the selected log messages and additional files to [REQUIRED]
    *
	* @since v2.0
	*/
	SE_API_DECL(se_result_t, se_exportMoreDataToStream)(const uint8_t *serialNumberKey,
		uint32_t serialNumberLength,
		uint32_t previousSignatureCounter,
		int32_t maximumNumberRecords,
		FILE *stream);

	/**
	* Continue data export, e.g. immediately after last seen log entry..., to a named file.
	*
	* \note For common parameters, parameter evaluation, and return values see @ref se_exportMoreData.
    *
	* @param[in]  serialNumberKey
	* @param[in]  serialNumberLength
	* @param[in]  previousSignatureCounter
	* @param[in]  maximumNumberRecords
	* @param[in]  fileName
	*                name of export file (existing files will be overwritten) [REQUIRED]
    *
	* @since v2.1
	*/
	SE_API_DECL(se_result_t, se_exportMoreDataToFile)(const uint8_t *serialNumberKey,
		uint32_t serialNumberLength,
		uint32_t previousSignatureCounter,
		int32_t maximumNumberRecords,
		const char *fileName);

	/**
	* Continue data export, e.g. immediately after last seen log entry..., by means of a callback function.
	*
	* \note For common parameters, parameter evaluation, and return values see @ref se_exportMoreData.
    *
	* @param[in]  serialNumberKey
	* @param[in]  serialNumberLength
	* @param[in]  previousSignatureCounter
	* @param[in]  maximumNumberRecords
	* @param [in] writer
	*			     address of "writer" callback (see @ref se_writer_t)
	* @param [in] handle
	*                parameter to pass to writer; not further specified here!
	*
	* @since v2.0
	*/
	SE_API_DECL(se_result_t, se_exportMoreDataViaCallback)(const uint8_t *serialNumberKey,
		uint32_t serialNumberLength,
		uint32_t previousSignatureCounter,
		int32_t maximumNumberRecords,
		se_writer_t writer,
		se_handle_t handle);

	/**
	* Delete all log data up to a specific signature counter
	* @param[in] serialNumberKey
	*                ID of the key used in previous log entry (SHA256 hash value of the public key). \n
	*				 Since 2.4.0: A NULL pointer selects the @ref TSEPrimaryKey
	* @param[in] serialNumberLength
	*                length of the array that represents the serialNumberKey  [REQUIRED]
	* @param[in] signatureCounter
	*                highest signature counter to delete [REQUIRED]
	*
	* @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorParameterMismatch                   mismatch in parameters of the function
	* @return @ref ErrorNoDataAvailable                     no data has been found for the provided selection
	* @return @ref ErrorSeApiNotInitialized                 the SE API has not been initialized
	* @since v2.1
	*/
	SE_API_DECL(se_result_t, se_deleteStoredDataUpTo)(const uint8_t *serialNumberKey,
		uint32_t serialNumberLength,
		uint32_t signatureCounter);

	/**
	* Exports the certificates of the certificate chains. These certificates belong to
	* the public keys of the key pairs that are used for the creation of signature values in log messages
	* @param[out] certificates
	*                the TAR archive that contains all certificates that are necessary for the verification of log messages.
	*                The format of the TAR archive and the contained certificates SHALL conform to BSI TR-03151 [REQUIRED]\n
	*                If successfully executed, the buffer has to freed by the function caller [@ref se_free()].
	* @param[out] certificatesLength
	*                length of the array that represent the certificate(s) [REQUIRED]
	*
	* @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorExportCertFailed                    the collection of the certificates for the export failed
	* @return @ref ErrorSeApiNotInitialized                 the SE API has not been initialized
	* @return @ref ErrorSeApiDeactivated                    TSEv1 only
	*/
	SE_API_DECL(se_result_t, se_exportCertificates)(uint8_t **certificates,
		uint32_t *certificatesLength);

	/**
	* Export TSE signing certificate file.
	* 
	* @param[out] certificate
	*                Output for TSE signing certificate file [REQUIRED]\n
	*                If successfully executed, the buffer has to freed by the function caller [@ref se_free()].
	* @param[out] certificateLength
	*                length of the array that represent the certificate [REQUIRED]
	*
	* @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorSeApiNotInitialized                 the SE API has not been initialized
	*
	* @since 2.4.0, not available on TSE v1.
	*/
	SE_API_DECL(se_result_t, se_getCertificate)(uint8_t **certificate,
		uint32_t *certificateLength);

	/**
	* Supplies the expiration date of a certificate
	*
	* @note  An additional function with a different set of parameters exists:\n
	*        please see {@link se_getCertificateExpirationDate1()}.
	*
	* @param[in] serialNumberKey
	*                ID of the belonging key  (SHA256 hash value of the public key)
	* @param[in] serialNumberLength
	*                length of the array that represents the serialNumberKey  [REQUIRED]
	* @param[out] expirationDate
	*                certificate expiration date as unixTime [REQUIRED]
	*
	* @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorSeApiNotInitialized                 the SE API has not been initialized
	* @return @ref ErrorSecureElementDisabled               the Secure Element has been disabled
	* @since v2.0
	*/
	SE_API_DECL(se_result_t, se_getCertificateExpirationDate)(const uint8_t *serialNumberKey,
		uint32_t serialNumberLength, 
		int64_t *expirationDate);

	/**
	* Supplies the expiration date of a certificate
	*
	* @note  An additional function with a different set of parameters exists:\n
	*        please see {@link se_getCertificateExpirationDate()}.
	*
	* @param[out] expirationDate
	*                certificate expiration date as unixTime [REQUIRED]
	*
	* @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorSeApiNotInitialized                 the SE API has not been initialized
	* @return @ref ErrorSecureElementDisabled               the Secure Element has been disabled
	* @return @ref ErrorSeApiDeactivated					TSEv1 only
	* @since v2.4.0
	*/
	SE_API_DECL(se_result_t, se_getCertificateExpirationDate1)(int64_t *expirationDate);

	/**
	* Read all mappings of ERS and belonging public key serial number.
	* @param[out] mappingData
	*                Buffer for the returned DER encoded mapping data (sequence of ERS mappings) [REQUIRED]\n
	*                If successfully executed, the buffer has to freed by the function caller [@ref se_free()].
	* @param[out] mappingDataLength
	*                length of DER encoded mapping data [REQUIRED]
	*
    * @return @ref ExecutionOk                              execution of the function has been successful
	* @since v2.0
	*
	* @deprecated For TSE v2 use {@link se_listClients()}.
	*/
	SE_API_DECL(se_result_t, se_getERSMappings)(uint8_t **mappingData,
		uint32_t *mappingDataLength);

	/**
	* List all clients
	* @param[out] clients
	*                Buffer for the returned client list [REQUIRED]\n
	*                If successfully executed, the buffer has to freed by the function caller [@ref se_free()].
	* @param[out] clientsLength
	*                length of clients [REQUIRED]
	*
	* @return @ref ExecutionOk                              execution of the function has been successful
	* @since v2.4.0, not available on TSE v1.
	*/
	SE_API_DECL(se_result_t, se_listClients)(char ***clients,
		uint32_t *clientsLength);

	/**
	* Reads a log message that bases on the last log message parts that have been produced and processed by the Secure Element
	* @param[out] logMessage
	*                contains the last log message that the Secure Element has produced [REQUIRED]\n
	*                If successfully executed, the buffer has to freed by the function caller [@ref se_free()].
	* @param[out] logMessageLength
	*                length of the array that represents the last log message [REQUIRED]
    *
    * @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorNoLogMessage                        no log message parts are found
	* @return @ref ErrorReadingLogMessage                   error while retrieving log message parts
	* @return @ref ErrorSeApiNotInitialized                 the SE API has not been initialized
	* @return @ref ErrorSecureElementDisabled               the Secure Element has been disabled
	*/
	SE_API_DECL(se_result_t, se_readLogMessage)(uint8_t **logMessage,
		uint32_t *logMessageLength);

	/**
	* Exports the serial number(s) of the SE API. A serial number is a hash value of a public key that belongs to a key pair
	* whose private key is used to create signature values of log messages.
	* @param[out] serialNumbers
	*                the serial number(s) of the SE API.
	*                The serial number(s) SHALL be encoded in the TLV structure defined in BSI TR-03151. [REQUIRED]\n
	*                If successfully executed, the buffer has to freed by the function caller [@ref se_free()].
	* @param[out] serialNumbersLength
	*                length of the array that represents the serial number(s) [REQUIRED]
	*
	* @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorExportSerialNumbersFailed           the collection of the serial number(s) failed
	* @return @ref ErrorSeApiNotInitialized                 the SE API has not been initialized
	* @return @ref ErrorSeApiDeactivated                    TSEv1 only
	*/
	SE_API_DECL(se_result_t, se_exportSerialNumbers)(uint8_t **serialNumbers,
		uint32_t *serialNumbersLength);

	/**
	* Supplies the maximal number of clients that can use the functionality to log transactions of the SE API simultaneously
	* @param[out] maxNumberClients
	*                maximum number of clients that can use the functionality to log transactions of the SE API simultaneously [REQUIRED]
	*
	* @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorGetMaxNumberOfClientsFailed         the determination of the maximum number of clients that could use the SE API simultaneously failed
	* @return @ref ErrorSeApiNotInitialized                 the SE API has not been initialized
	* @return @ref ErrorSecureElementDisabled               the Secure Element has been disabled
	* @return @ref ErrorSeApiDeactivated                    TSEv1 only
	*/
	SE_API_DECL(se_result_t, se_getMaxNumberOfClients)(uint32_t *maxNumberClients);

	/**
	* Supplies the number of clients that are currently using the functionality to log transactions of the SE API.
	* @param[out] currentNumberClients
	*                the number of clients that are currently using the functionality of the SE API [REQUIRED]
    *
    * @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorGetMaxNumberOfClientsFailed         the determination of the current number of clients using the SE API failed
	* @return @ref ErrorSeApiNotInitialized                 the SE API has not been initialized
	* @return @ref ErrorSecureElementDisabled               the Secure Element has been disabled
	* @return @ref ErrorSeApiDeactivated                    TSEv1 only
	*/
	SE_API_DECL(se_result_t, se_getCurrentNumberOfClients)(uint32_t *currentNumberClients);

	/**
	* Supplies the maximal number of simultaneously opened transactions that can be managed by the SE API
	* @param[out] maxNumberTransactions
	*                 maximum number of simultaneously opened transactions that can be managed by the SE API [REQUIRED]
    *
    * @return @ref ExecutionOk                              execution of the function has been successful
	* @return @ref ErrorGetMaxNumberTransactionsFailed      the determination of the maximum number of transactions that can be managed simultaneously failed
	* @return @ref ErrorSeApiNotInitialized                 the SE API has not been initialized
	* @return @ref ErrorSecureElementDisabled               the Secure Element has been disabled
	* @return @ref ErrorSeApiDeactivated                    TSEv1 only
	*/
	SE_API_DECL(se_result_t, se_getMaxNumberOfTransactions)(uint32_t *maxNumberTransactions);

	/**
	* Supplies the number of open transactions that are currently managed by the SE API
	* @param[out] currentNumberTransactions
	*                the number of open transactions that are currently managed by the SE API [REQUIRED]
    *
    * @return @ref ExecutionOk                                  execution of the function has been successful
	* @return @ref ErrorGetCurrentNumberOfTransactionsFailed    the determination of the number of open transactions that are currently managed by the SE API failed
	* @return @ref ErrorSeApiNotInitialized                     the SE API has not been initialized
	* @return @ref ErrorSecureElementDisabled                   the Secure Element has been disabled
	*/
	SE_API_DECL(se_result_t, se_getCurrentNumberOfTransactions)(uint32_t *currentNumberTransactions);

	/**
	* Supplies the current transaction counter (last used value)
	* @param[out] transactionCounter
	*                the current transaction counter [REQUIRED]
	*
	* @return @ref ExecutionOk                                  execution of the function has been successful
	* @return @ref ErrorSeApiNotInitialized                     the SE API has not been initialized
	* @return @ref ErrorSecureElementDisabled                   the Secure Element has been disabled
	* @since v2.0
	*/
	SE_API_DECL(se_result_t, se_getTransactionCounter)(uint32_t *transactionCounter);

	/**
	* Supplies size of log memory in bytes
	* @param[out] sizeOfMemory
	*                size of log memory in bytes [REQUIRED]
	*
	* @return @ref ExecutionOk                                  execution of the function has been successful
	* @return @ref ErrorSeApiNotInitialized                     the SE API has not been initialized
	* @return @ref ErrorSecureElementDisabled                   the Secure Element has been disabled
	* @since v2.0
	*/
	SE_API_DECL(se_result_t, se_getTotalLogMemory)(uint64_t *sizeOfMemory);

	/**
	* Supplies size of available log memory in bytes
	* @param[out] sizeOfMemory
	*                size of available log memory in bytes [REQUIRED]
	*
	* @return @ref ExecutionOk                                  execution of the function has been successful
	* @return @ref ErrorSeApiNotInitialized                     the SE API has not been initialized
	* @return @ref ErrorSecureElementDisabled                   the Secure Element has been disabled
	* @since v2.0
	*/
	SE_API_DECL(se_result_t, se_getAvailableLogMemory)(uint64_t *sizeOfMemory);

	/**
	* Supplies the current signature counter (last used value) for the given key
	*
	* @note  An additional function with a different set of parameters exists:\n
	*        please see {@link se_getSignatureCounter1()}.
	*
	* @param[in] serialNumberKey
	*                ID of the key used in previous log entry (SHA256 hash value of the public key)
	* @param[in] serialNumberLength
	*                length of the array that represents the serialNumberKey  [REQUIRED]
	* @param[out] signatureCounter
	*                the current signature counter [REQUIRED]
	*
	* @return @ref ExecutionOk                                  execution of the function has been successful
	* @return @ref ErrorSeApiNotInitialized                     the SE API has not been initialized
	* @return @ref ErrorSecureElementDisabled                   the Secure Element has been disabled
	* @since v2.0
	*/
	SE_API_DECL(se_result_t, se_getSignatureCounter)(const uint8_t *serialNumberKey,
		uint32_t serialNumberLength, 
		uint32_t *signatureCounter);

	/**
	* Supplies the current signature counter (last used value)
	*
	* @note  An additional function with a different set of parameters exists:\n
	*        please see {@link se_getSignatureCounter()}.
	*
	* @param[out] signatureCounter
	*                the current signature counter [REQUIRED]
	*
	* @return @ref ExecutionOk                                  execution of the function has been successful
	* @return @ref ErrorSeApiNotInitialized                     the SE API has not been initialized
	* @return @ref ErrorSecureElementDisabled                   the Secure Element has been disabled
	* @return @ref ErrorSeApiDeactivated						TSEv1 only
	* @since v2.0
	*/
	SE_API_DECL(se_result_t, se_getSignatureCounter1)(uint32_t *signatureCounter);

	/**
	* Supplies the supported variants to update transactions
	* @param[out] supportedUpdateVariants
	*                the supported variant(s) to update a transaction [REQUIRED]
	*
	* @return @ref ExecutionOk                                  execution of the function has been successful
	* @return @ref ErrorGetSupportedUpdateVariantsFailed        the identification of the supported variant(s) to update transactions failed
	* @return @ref ErrorSeApiNotInitialized                     the SE API has not been initialized
	* @return @ref ErrorSecureElementDisabled                   the Secure Element has been disabled
	* @return @ref ErrorSeApiDeactivated						TSEv1 only
	*/
	SE_API_DECL(se_result_t, se_getSupportedTransactionUpdateVariants)(se_update_t *supportedUpdateVariants);

	/**
	* Supplies flags for the supported time formats of the TSE.
	* @param[out] supportedSyncVariant
	*                Buffer for the supported time sync format [REQUIRED]
	*
	* @return @ref ExecutionOk                                  execution of the function has been successful
	* @since v2.0
	*/
	SE_API_DECL(se_result_t, se_getTimeSyncVariant)(se_sync_variants_t *supportedSyncVariant);

	/**
	* Supplies the ASN.1 encoded signature algorithm OID as encoded into signed data.
	* @param[out] signatureAlgorithm
	*                Buffer for signature algorithm OID. [REQUIRED]\n
	*                If successfully executed, the buffer has to freed by the function caller [@ref se_free()].
	* @param[out] signatureAlgorithmLength
	*                length of the signature algorithm OID buffer [REQUIRED]
	*
	* @return @ref ExecutionOk                                  execution of the function has been successful
	* @return @ref ErrorSeApiNotInitialized                     the SE API has not been initialized
	* @return @ref ErrorSecureElementDisabled                   the Secure Element has been disabled
	* @since v2.0
	*/
	SE_API_DECL(se_result_t, se_getSignatureAlgorithm)(uint8_t **signatureAlgorithm,
		uint32_t *signatureAlgorithmLength);

	/**
	* Supplies the proposed update interval for the CSP time base (number of seconds)
	* @param[out] timeSyncInterval
	*                 sync interval in seconds [REQUIRED]
    *
    * @return @ref ExecutionOk                                  execution of the function has been successful
	* @return @ref ErrorSeApiNotInitialized                     the SE API has not been initialized
	* @return @ref ErrorSecureElementDisabled                   the Secure Element has been disabled
	*/
	SE_API_DECL(se_result_t, se_getTimeSyncInterval)(uint32_t *timeSyncInterval);

	/**
	* Deletes all data that is stored in the storage. The function SHALL delete
	* only data that has been exported.
    *
    * @return @ref ExecutionOk                                  execution of the function has been successful
	* @return @ref ErrorDeleteStoredDataFailed                  the deletion of the data from the storage failed
	* @return @ref ErrorUnexportedStoredData                    the deletion of data from the storage failed because the storage contains data that has not been exported
	* @return @ref ErrorSeApiNotInitialized                     the SE API has not been initialized
	* @return @ref ErrorUserNotAuthorized                       the user who has invoked the function deleteStoredData is not authorized to execute this function
	* @return @ref ErrorUserNotAuthenticated                    the user who has invoked the function deleteStoredData has not the status authenticated
	* @return @ref ErrorSigningSystemOperationDataFailed		not on TSE v1 - if system log could not be created
	* @return @ref ErrorStorageFailure							if deletion or (not on TSE v1) storage of system log failed
	*/
	SE_API_DECL(se_result_t, se_deleteStoredData)();

	/**
	* Enables an authorized user or application to authenticate to the SE API for the usage of restricted SE API functions
	*
	* @note   Timeouts apply: TimeAdmin is automatically logged out after 2 seconds, Admin after 10 minutes.
	*
	* @param[in] userId
	*                the ID of the user who or application that wants to be authenticated [REQUIRED]
	* @param[in] userIdLength
	*                the length of the array that represents the userId [REQUIRED]
	* @param[in] pin
	*                the PIN for the authentication [REQUIRED]
	* @param[in] pinLength
	*                the length of the array that represents the pin [REQUIRED]
	* @param[out] authenticationResult
	*                the result of the authentication [REQUIRED]
	* @param[out] remainingRetries
	*                the number of remaining retries to enter a PIN [REQUIRED]
    *
    * @return @ref ExecutionOk                                  execution of the function has been successful
	* @return @ref ErrorAuthenticationFailed                    the authentication attempt has failed
	* @return @ref ErrorSigningSystemOperationDataFailed        the determination of the log message parts for the system operation data by the Secure Element failed
	* @return @ref ErrorRetrieveLogMessageFailed                the execution of the Secure Element functionality to retrieve log message parts has failed
	* @return @ref ErrorStorageFailure                          storing of the data of the log message failed
	* @return @ref ErrorSecureElementDisabled                   the Secure Element has been disabled
	*/
	SE_API_DECL(se_result_t, se_authenticateUser)(const char *userId,
		uint32_t userIdLength,
		const uint8_t *pin,
		uint32_t pinLength,
		se_authentication_result_t *authenticationResult,
		int16_t *remainingRetries);

	/**
	* Enables the log out of an authenticated user or application from the SE API
	* @param[in] userId
	*                the ID of the user who or application that wants to log out from the SE API [REQUIRED]
	* @param[in] userIdLength
	*                the length of the array that represents the userId [REQUIRED]
    *
    * @return @ref ExecutionOk                                  execution of the function has been successful
    * @return @ref ErrorUserIdNotManaged                        the passed userId is not managed by the SE API
    * @return @ref ErrorUserIdNotAuthenticated                  the passed userId has not the status authenticated
    * @return @ref ErrorSigningSystemOperationDataFailed        the determination of the log message parts for the system operation data by the Secure Element failed
    * @return @ref ErrorRetrieveLogMessageFailed                the execution of the Secure Element functionality to retrieve log message parts has failed
    * @return @ref ErrorStorageFailure                          storing of the data of the log message failed
    * @return @ref ErrorSecureElementDisabled                   the Secure Element has been disabled
	*/
	SE_API_DECL(se_result_t, se_logOut)(const char *userId,
		uint32_t userIdLength);

	/**
	* Enables the unblocking for the entry of a PIN and the definition of a new PIN
	* for the authentication of authorized users or applications
	* @note   The new PIN **must** be different from the previous PIN!
	*
	* @param[in] userId
	*                the ID of the user who or application that wants to unblock the corresponding PIN entry [REQUIRED]
	* @param[in] userIdLength
	*                the length of the array that represents the userId [REQUIRED]
	* @param[in] puk
	*                the PUK of the user/application [REQUIRED]
	* @param[in] pukLength
	*                the length of the array that represents the puk [REQUIRED]
	* @param[in] newPin
	*                the new PIN for the user/application [REQUIRED]
	* @param[in] newPinLength
	*                the length of the array that represents the newPin [REQUIRED]
	* @param[out] unblockResult
	*                the result of the unblock procedure [REQUIRED]
    *
    * @return @ref ExecutionOk                                  execution of the function has been successful
    * @return @ref ErrorUnblockFailed                           attempt to unblock the PIN entry has failed
    * @return @ref ErrorSigningSystemOperationDataFailed        the determination of the log message parts for the system operation data by the Secure Element failed
    * @return @ref ErrorRetrieveLogMessageFailed                the execution of the Secure Element functionality to retrieve log message parts has failed
    * @return @ref ErrorStorageFailure                          storing of the data of the log message failed
    * @return @ref ErrorSecureElementDisabled                   the Secure Element has been disabled
	*/
	SE_API_DECL(se_result_t, se_unblockUser)(const char *userId,
		uint32_t userIdLength,
		const uint8_t *puk,
		uint32_t pukLength,
		const uint8_t *newPin,
		uint32_t newPinLength,
		se_unblock_result_t *unblockResult);

	/**
	* Get Wear Indicator
	* @param[out] wearIndicator
	*				For values below 100, typical data retention is more than 10 years. Bigger values indicate shorter data retention, but at least 1 year.
	* @since 2.0
	*/
	SE_API_DECL(se_result_t, se_getWearIndicator)(uint32_t* wearIndicator);

	/**
	* Get Min Signature Counter
	*                
	* @param[out] minSignatureCounter
	*				smallest signature counter stored in log memory.
	* @since 2.4.0, not available on TSE v1
	*/
	SE_API_DECL(se_result_t, se_getMinSignatureCounter)(uint32_t* minSignatureCounter);

	/**
	* Get Max Signature Counter
	*        
	* @param[out] maxSignatureCounter
	*				biggest signature counter stored in log memory.
	* @since 2.4.0, not available on TSE v1
	*/
	SE_API_DECL(se_result_t, se_getMaxSignatureCounter)(uint32_t* maxSignatureCounter);

	/**
	* Get Next Signature Counter
	*
	* @param[out] nextSignatureCounter
	*				next unexported signature counter stored in log memory.
	* @since 2.4.0, not available on TSE v1
	*/
	SE_API_DECL(se_result_t, se_getNextSignatureCounter)(uint32_t* nextSignatureCounter);

	/**
	* Export public key
	* @param[in] serialNumberKey
	*                ID of the key  [REQUIRED]
	* @param[in] serialNumberLength
	*                length of the array that represents the serialNumberKey  [REQUIRED]
	* @param[out] exportedPublicKey
	*                array that contains the requested public key [REQUIRED]\n
	*                If successfully executed, the buffer has to freed by the function caller [@ref se_free()].
	* @param[out] exportedPublicKeyLength
	*                length of the array that represents the exportedPublicKey [REQUIRED]
	* @since 2.0
	*/
	SE_API_DECL(se_result_t, se_exportPublicKey)(const uint8_t* serialNumberKey,
		uint32_t serialNumberLength,
		uint8_t** exportedPublicKey,
		uint32_t* exportedPublicKeyLength);

	/**
	* Get the error code of the first unsuccessful OS function invoked in an SE-API function call which fails with ErrorIO.
	*
	* @note   For TSE access via WIN-API functions, the GetLastError() value of the first unsuccessful WIN-API call is returned.
	* @note   For TSE access via runtime-library functions, the errno value of the first unsuccessful runtime-library call is returned (e.g. for unix/linux OS).
	* @note   A call of this function (fetch error code) or a call of an se_[re]open[Direct]()-function is required to reset the internal stored OS error code to SE_OS_OK.
	*
	* @return @ref SE_OS_OK     no error detected (SE_OS_OK = 0)
	* @return error code        error detected (non zero)
	*
	* @since 2.4.0
	*/
	SE_API_DECL(uint32_t, se_getOsStatusOfErrorIO)();

#ifdef __cplusplus
} /* extern "C" */
#endif  

#endif  /* SE_API_H */

/** @}  SE-API  */
