/*
 * Copyright (c) 2020
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
  * @file se_parse_certificate.c
  *
  * @brief Part of minimal demo of the cryptovision SE-API for "C".
  */

#include <stdio.h>
#include <string.h>

#include <se_result_t.h>
#include <se_memory_util.h>


/* ------------------------------------------------------------------------- */
static int hexToInt(char c)
{
	if(c >= '0' && c <= '9')
		return (c - '0');
	else if(c >= 'a' && c <= 'f')
		return (c - 'a' + 10);
	else if(c >= 'A' && c <= 'F')
		return (c - 'A' + 10);

	return -1;
}

/* ------------------------------------------------------------------------- */
static uint32_t hexToByte(const char *hex, uint32_t hexLength, uint8_t *out)
{
	/* NOTE: no parameter validation, hexLength is expected to be even > 0 */
	int tmp1, tmp2;
	uint32_t i, out_len = 0;

	for(i = 0; i < hexLength; i += 2)
	{
		if((tmp1 = hexToInt(hex[i])) == -1)
			return 0;
		if((tmp2 = hexToInt(hex[i + 1])) == -1)
			return 0;

		out[out_len++] = (((uint8_t)tmp1) << 4) | ((uint8_t)tmp2);
	}

	return out_len;
}

/* ------------------------------------------------------------------------- */
static uint32_t getCertLen(const uint8_t *cert)
{
	/* NOTE: no parameter validation */
	uint32_t pos = 0;
	if(cert[0] == 0x30)
		pos = 1;	/* X.509 */
	else if(cert[0] == 0x7f && cert[1] == 0x21)
		pos = 2;	/* CVC */

	if(pos != 0)
	{
		uint8_t b = cert[pos++];
		if(b <= 0x7f)
			return ((uint32_t)b) + pos;
		if(b == 0x81)
			return ((uint32_t)cert[pos]) + pos + 1;
		if(b == 0x82)
			return ((((uint32_t)cert[pos]) << 8) | cert[pos + 1]) + pos + 2;
	}

	return 0;
}

/**
* Parse a certificate from a TSE returned tar-archive of certificates according to BSI-TR-03151.
* No allocations of output parameters, returned is the pointer to the certificate in the tar-archive and the certificate's length.
* ASSUMPTION: All certificates of the tar-archive are DER encoded (PEM format is not supported).
*
* @param[in] serialNumberKey
*                ID of the key [REQUIRED]
* @param[in] serialNumberLength
*                length of the serialNumberKey [REQUIRED]
* @param[in] certificatesTarArchive
*                tar-archive of certificates [REQUIRED]
* @param[in] certificatesTarArchiveLength
*                length of tar-archive of certificates [REQUIRED]
* @param[out] certificate
*                pointer to the certificate in the tar-archive (or NULL if not found) [REQUIRED]
* @param[out] certificateLength
*                length of certificate (or 0 if not found) [REQUIRED]
*
* @return @ref ExecutionOk                  certificate found
* @return @ref ErrorMissingParameter        required parameter is NULL
* @return @ref ErrorFunctionNotSupported	serialNumberLength unsupported (hash value of length 20 up to 64 byte expected)
* @return @ref ErrorAllocationfailed		failed to allocate internal buffer
* @return @ref ErrorExportCertFailed		certificate not found (format error)
*/
se_result_t se_parseCertificate(const uint8_t *serialNumberKey,
	uint32_t serialNumberLength,
	const uint8_t *certificatesTarArchive,
	uint32_t certificatesTarArchiveLength,
	uint8_t **certificate,
	uint32_t *certificateLength)
{
	if(serialNumberKey == NULL
	|| certificatesTarArchive == NULL
	|| certificate == NULL
	|| certificateLength == NULL)
		return ErrorMissingParameter;

	/* hash value of length 20 up to 64 byte supported as key serial number */
	if(serialNumberLength < 20 || serialNumberLength > 64)
		return ErrorFunctionNotSupported;
	
	*certificate = NULL;
	*certificateLength = 0;
	{		
		uint8_t* serno_buf;
		int certificate_found;
		uint32_t pos = 0, TAR_BLOCK_SIZE = 512;
		se_result_t result = ErrorExportCertFailed;

		if((serno_buf = (uint8_t*)se_malloc(serialNumberLength)) == NULL)
			return ErrorAllocationfailed;

		/* parse certificate from tar-archive */
		while((pos + TAR_BLOCK_SIZE) < certificatesTarArchiveLength) 
		{
			/* check if the zero-padding block of the tar-archive is reached */
			if(*(certificatesTarArchive + pos) == 0)
				break;

			/* expect certificate file name according to TR-03151 (e.g. [key_serno_string]_X509.cer),
			   convert serial number part of current file name from string to byte array */
			if(hexToByte((char*)(certificatesTarArchive + pos), 2 * serialNumberLength, serno_buf) != serialNumberLength)
				break;

			/* check if serial number matches with file name */
			certificate_found = memcmp(serialNumberKey, serno_buf, serialNumberLength) == 0 ? 1 : 0;

			/* skip certificate file header block and check if at least one block follows */
			pos += TAR_BLOCK_SIZE;
			if((pos + TAR_BLOCK_SIZE) >= certificatesTarArchiveLength)
				break;
			{
				/* get certificate length */
				uint32_t cert_len = getCertLen(certificatesTarArchive + pos);
				if(cert_len == 0 || (pos + cert_len) >= certificatesTarArchiveLength)
					break;

				/* if certificate found, stop and return first match */
				if(certificate_found != 0)
				{
					*certificate = (uint8_t*)(certificatesTarArchive + pos);
					*certificateLength = cert_len;
					result = ExecutionOk;
					break;
				}

				/* certificate not found, skip certificate blocks */
				pos += TAR_BLOCK_SIZE * ((cert_len + TAR_BLOCK_SIZE - 1) / TAR_BLOCK_SIZE);
			}
		}

		se_free(serno_buf);
		return result;
	}
}
