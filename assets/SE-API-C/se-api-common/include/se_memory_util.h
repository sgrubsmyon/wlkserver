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
  * @file se_memory_util.h
  *
  * @brief Memory management utilities for the cryptovision SE-API and _extended_ SE_API.
  *
  * @addtogroup SE-API-common
  *
  * @{
  */

#ifndef SE_MEMORY_UTIL_H
#define SE_MEMORY_UTIL_H

#include <stdint.h>

#include <stdio.h>
#include <stdlib.h>

#include <se_define.h>
#include <se_result_t.h>

/**
* Memory management function pointer type definition.
* @since v2.1: added SE_STDCALL calling convention.
*/

typedef void* (SE_STDCALL *se_malloc_t) (size_t size);
typedef void  (SE_STDCALL *se_free_t)   (void* memBlock);


#ifdef __cplusplus
extern "C" {
#endif  

	/**
	* Free memory allocated by the SE_API functions.
	* Please refer to the function's return parameter description if an output parameter has to be freed.
	*
	* The standard implementation directly uses free();
	* the function does not do any additional parameter tests.
	* @see se_setAllocator()
	* @see se_malloc()
	*
	* @param [in]   memBlock    pointer to memory block to be freed
	*/
	SE_API_COMMON_DECL(void, se_free)(void* memBlock);

	/**
	* Memory allocation function used by the SE_API functions.
	*
	* The standard implementation directly uses malloc();
	* the function does not do any additional parameter tests.
	* @see se_setAllocator()
	* @see se_free()
	*
	* @param [in]  size    size of the block to be allocated
	*
	* @return      address of the allocated block
	*                  if address == NULL   -> error -> the calling SE-API function aborts with ErrorAllocationfailed
	*/
	SE_API_COMMON_DECL(void*, se_malloc)(size_t size);

	/**
	* Change memory allocation and de-allocation functions [OPTIONAL].
	*
	* Both functions have to be set at the same time;
	* specifying NULL pointers for both functions restores the
	* standard behaviour to use malloc() and free();
	* parameters to the _malloc() and _free() functions are as
	* known from malloc() and free().
	* @see se_malloc()
	* @see se_free()
	*
	* @param [in]   _malloc   address of allocation function
	*                         this function will replace malloc()
	* @param [in]   _free     address of DE-allocation function
	*                         this function will replace free()
	*
	* @return                 ExecutionOk - success
	*                         ErrorMissingParameter - exactly one input function is NULL
	*/
	SE_API_COMMON_DECL(se_result_t, se_setAllocator)(se_malloc_t _malloc, se_free_t _free);

#ifdef __cplusplus
} /* extern "C" */
#endif  

#endif  /* SE_MEMORY_UTIL_H */

/** @}  SE-API  */
