/*
 * Copyright (c) 2019-2020
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
  * @file se_callback_t.h
  *
  * @brief Callback definitions for the cryptovision SE-API and _extended_ SE_API.
  *
  * SE-API data export functions writer-callback and handle type definitions,
  * allowing the user to redirect the TSE output of exported data to some
  * external buffer, stream, network connection,... you name it.
  * @see se_exportDataViaCallback()
  * @see se_exportMoreDataViaCallback()
  *
  * @addtogroup SE-API-common
  *
  * @{
  */

#ifndef SE_CALLBACK_T_H
#define SE_CALLBACK_T_H

#include <stdint.h>

#include <se_define.h>

/**
 *  Handle type to allow marking a specific export function.
 *
 *  This handle will be passed to every call of @ref se_writer_t;\n
 *  it is not used / interpreted / validated by the SE-API.
 */
typedef void* se_handle_t;

/**
 *  Data export writer callback.
 *
 *  This callback function will be called for every block of data exported from the TSE.
 *
 *  @param [in]  data
 *                  points to the current data block exported from the TSE
 *  @param [in]  dataLength
 *                  length of the current data block exported from the TSE
 *  @param [in]  totalDataLength
 *                  total length of the data exported from the TSE
 *  @param [in]  handle
 *                  handle to allow the user to diversify the handling of different export processes
 *
 *  @return      number of bytes (numWritten) processed by the callback:\n
 *                  if numWritten == dataLength   -> no error -> the calling export data function continues\n
 *                  if numWritten != dataLength   -> error    -> the calling export data function aborts with ErrorCallback
 */
typedef uint32_t (SE_STDCALL *se_writer_t) (const uint8_t* data, uint32_t dataLength, uint64_t totalDataLength, se_handle_t handle);


#endif  /* SE_CALLBACK_T_H */

/** @}  SE-API  */
