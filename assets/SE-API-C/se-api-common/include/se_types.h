/*
 * Copyright (c) 2020-2023
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
  * @file se_types.h
  *
  * @brief Type definitions for the cryptovision SE-API and _extended_ SE_API.
  *
  * @addtogroup   SE-API-common
  * @brief        Definitions and Interface Functions used in both the cryptovision SE-API and the cryptovision _extended_ SE-API.
  *
  * @{
  */

#ifndef SE_TYPES_H
#define SE_TYPES_H

#include <stdint.h>

/**
 * Represents the PIN states of the TSE.
 *
 * The values defined for each PIN are bit-masks.\n
 * They may be combined by the "bit-wise or" operator (|).
 */
typedef enum SePinStateFlags {
	stateInitialized				= 0x00,		/**<  ALL PINs have been initialized          */
	adminPinTransportState			= 0x01,		/**<  the Admin PIN is in transport state     */
	adminPukTransportState			= 0x02,		/**<  the Admin PUK is in transport state     */
	timeAdminPinTransportState		= 0x04,		/**<  the TimeAdmin PIN is in transport state */
	timeAdminPukTransportState		= 0x08		/**<  the TimeAdmin PUK is in transport state */
} se_pin_state_flags_t;

/**
* Represents the supported time formats of the TSE.
*/
typedef enum SeSyncVariants {
	noInput							= 0x00,		/**<  the time format is undefined            */
	utcTime							= 0x01,		/**<  the TSE uses UTC time format            */
	generalizedTime					= 0x02,		/**<  the TSE uses "generalized time" format  */
	unixTime						= 0x03		/**<  the TSE uses Unix time format           */
} se_sync_variants_t;

/**
* Represents the variants that are supported by the Secure Element to update transactions.
*/
typedef enum SeUpdateVariants {
	signedUpdate = 0,               /**<  the TSE supports signed updates only              */
	unsignedUpdate,                 /**<  the TSE supports UNsigned updates only            */
	signedAndUnsignedUpdate         /**<  the TSE supports BOTH signed and unsigned updates */
} se_update_t;

/**
* Represents the result of an authentication attempt.
*/
typedef enum SeAuthenticationResult {
	authenticationOk = 0,           /**<  the authentication has been successful            */
	authenticationFailed,           /**<  the authentication has failed                     */
	authenticationPinIsBlocked,     /**<  the PIN entry for the userId is blocked           */
	authenticationUnknownUserId,    /**<  the userId passed is not managed by the SE API    */
	authenticationError             /**<  some unspecified error occurred during execution  */
} se_authentication_result_t;

/**
* Represents the result of the unblock process.
*/
typedef enum SeUnblockResult {
	unblockOk = 0,                  /**<  the PIN was successfully unblocked                */
	unblockFailed,                  /**<  the unblocking of the PIN failed                  */
	unblockPinIsBlocked,            /**<  the PUK provided is blocked                       */
	unblockUnknownUserId,           /**<  the userId passed is not managed by the SE API    */
	unblockError                    /**<  some unspecified error occurred during execution  */
} se_unblock_result_t;

/**
* Represents the Life Cycle State (LCS) of the TSE.
*/
typedef enum SeLCS {
	lcsUnknown = 0,                 /**<  the LCS is unknown									*/
	lcsNotInitialized,              /**<  the TSE has not yet been initialized					*/
	lcsNoTime,                      /**<  the TSE time has not yet been set						*/
	lcsActive,                      /**<  the TSE is active (ready for transactions)			*/
	lcsDeactivated,                 /**<  the TSE has been deactivated							*/
	lcsDisabled,                    /**<  the TSE has been disabled								*/
	lcsSeError,						/**<  Secure Element not available \n since 2.4.0			*/
	lcsSleep,						/**<  device was powered down (by OS or card reader) \n since 2.4.0 */
	lcsClosed						/**<  device handle was closed \n since 2.4.0				*/
} se_lcs_t;

/**
* TSE version.
* @since v2.4.1
*/
typedef enum SeTSEVersion
{
	version1 = 1,
	version2,
	version2_1

} se_tse_version_t;

/**
* Return value type for the selfTest function.
*/
typedef struct SeSelfTestResult
{
	uint8_t		completed;				/**<  indicates whether or not testing was completed during given maximum runtime */
	uint8_t		errorsFound;			/**<  indicates if any errors have been found during current test sequence */
	uint32_t	level;					/**<  abstract level of device status, see <a href="https://support.cryptovision.com/tse/">online FAQ</a> */
	uint32_t	counters[4];			/**<  number of errors of different type, see <a href="https://support.cryptovision.com/tse/">online FAQ</a> */
	uint32_t	logLength;				/**<  length of the log */
	uint8_t*	log;					/**<  error log to be analyzed by manufacturer */
} se_self_test_result_t;				/*	  KEEP the tight fit of the comment-close string above; otherwise Doxygen will add loads of line breaks!!	*/

/**
* Common return values for all Secure Element's transaction functions.
*/
#define SE_TRANSACTION_RESULT()																															\
	int64_t		logTime;				/**<  time at which the data were signed*/																		\
	uint8_t		*serialNumber;			/**<  serial number of the signature key; buffer has to freed by the function caller [@ref se_free()]*/			\
	uint32_t	serialNumberLength;		/**<  length of the serial number*/																				\
	uint32_t	signatureCounter;		/**<  value of the signature counter*/																			\
	uint8_t		*signatureValue;		/**<  the signature over the transaction data; buffer has to freed by the function caller [@ref se_free()]*/	\
	uint32_t	signatureValueLength;	/**<  length of the signature*/
										/*	  KEEP the tight fit of the comment-close string above; otherwise Doxygen will add loads of line breaks!!	*/
/**
* Return value type for the Secure Element's startTransaction function.
*/
typedef struct SeStartTransactionResult
{
	SE_TRANSACTION_RESULT()
	uint32_t transactionNumber;			/**<  (new) transaction number assigned*/
} se_start_transaction_result_t;		/*	  KEEP the tight fit of the comment-close string above; otherwise Doxygen will add loads of line breaks!!	*/

/**
* Return value type for the Secure Element's updateTransaction function.
*/
typedef struct SeUpdateTransactionResult
{
	SE_TRANSACTION_RESULT()
} se_update_transaction_result_t;

/**
* Return value type for the Secure Element's finishTransaction function.
*/
typedef struct SeFinishTransactionResult
{
	SE_TRANSACTION_RESULT()
} se_finish_transaction_result_t;

#endif  /* SE_TYPES_H */

/** @}  SE-API  */
