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
  * @file se_define.h
  *
  * @brief Macro definitions for the cryptovision SE-API and _extended_ SE_API.
  *
  * @addtogroup SE-API-common
  *
  * @{
  */

#ifndef SE_DEFINE_H
#define SE_DEFINE_H

/**
* NULL pointer definition
*/
#ifndef NULL
#	define NULL ((void *)0)
#endif

/**
* Macros used for function definitions and declarations
*/
#if defined(SE_STDCALL)
#	undef	SE_STDCALL
#	if defined(_WIN32)
#		define	SE_STDCALL __stdcall
#	endif
#endif

#if defined(SE_EXPORT) && defined(SE_EXPORT_EX)
#   error define SE_EXPORT or SE_EXPORT_EX
#endif

#if defined(SE_EXPORT)
#	undef	SE_EXPORT
#	if defined(_WIN32)
#		if !defined(SE_STDCALL)
#			define	SE_EXPORT __declspec(dllexport)
#		else
#			define	SE_EXPORT_METHOD __pragma(comment(linker, "/export:" __FUNCTION__ "=" __FUNCDNAME__))
#		endif
#	else
#		define	SE_EXPORT __attribute__ ((visibility ("default")))
#	endif
#   define  SE_API_COMMON_IMPL(rval, name)  SE_API_IMPL(rval, name)
#   define  SE_API_COMMON_DECL(rval, name)  SE_API_DECL(rval, name)
#   define  SE_EXPORT_COMMON_METHOD         SE_EXPORT_METHOD

#elif defined(SE_EXPORT_EX)
#	undef	SE_EXPORT_EX
#	if defined(_WIN32)
#		if !defined(SE_STDCALL)
#			define	SE_EXPORT_EX __declspec(dllexport)
#		else
#			define	SE_EXPORT_EX_METHOD __pragma(comment(linker, "/export:" __FUNCTION__ "=" __FUNCDNAME__))
#		endif
#	else
#		define	SE_EXPORT_EX __attribute__ ((visibility ("default")))
#	endif
#   define  SE_API_COMMON_IMPL(rval, name)  SE_API_EX_IMPL(rval, name)
#   define  SE_API_COMMON_DECL(rval, name)  SE_API_EX_DECL(rval, name)
#   define  SE_EXPORT_COMMON_METHOD         SE_EXPORT_EX_METHOD

#else
#   define  SE_API_COMMON_IMPL(rval, name)  SE_API_IMPL(rval, name)
#   define  SE_API_COMMON_DECL(rval, name)  SE_API_DECL(rval, name)
#   define  SE_EXPORT_COMMON_METHOD         SE_EXPORT_METHOD

#endif

#if !defined(SE_STDCALL)
#	define   SE_STDCALL
#endif

#if !defined(SE_EXPORT)
#	define   SE_EXPORT
#endif

#if !defined(SE_EXPORT_METHOD)
#	define   SE_EXPORT_METHOD
#endif

#if !defined(SE_EXPORT_EX)
#	define   SE_EXPORT_EX
#endif

#if !defined(SE_EXPORT_EX_METHOD)
#	define   SE_EXPORT_EX_METHOD
#endif

#if !defined(SE_API_IMPL)
#	define   SE_API_IMPL(rval, name)	rval SE_STDCALL name
#endif

#if !defined(SE_API_DECL)
#	define   SE_API_DECL(rval, name)	SE_EXPORT SE_API_IMPL(rval, name)
#endif

#if !defined(SE_API_EX_IMPL)
#	define   SE_API_EX_IMPL(rval, name)	rval SE_STDCALL name
#endif

#if !defined(SE_API_EX_DECL)
#	define   SE_API_EX_DECL(rval, name)	SE_EXPORT_EX SE_API_EX_IMPL(rval, name)
#endif

/**
* Constants used by se_openDirect1()-function.
* @ref se_openDirect1
*/
#define SE_MAX_RESPONSE_4k			4096						/**< TSE maximum response size of 4k */
#define SE_MAX_RESPONSE_8k			8192						/**< TSE maximum response size of 8k */

/**
* Constants used by se_openDirect2()-function.
* @ref se_openDirect2
*/
#define SE_DO_CHECK_INTEGRITY			1						/**< TSE performs some internal tests for up to 5 sec */
#define SE_NO_INTEGRITY_CHECK			0						/**< TSE skips internal tests - ignored before TSE v2.1 */

/**
* Constants used by se_updateTime()-function and se_exportData[ToStream/ViaCallback]()-functions for optional parameters.
* @ref se_updateTime
* @ref se_exportData
* @ref se_exportDataToStream
* @ref se_exportDataViaCallback
*/
#if !defined(SE_MAX_UINT32)
#	define   SE_MAX_UINT32			((uint32_t) 0xFFFFFFFF)
#endif

#if !defined(SE_MAX_UPDATE_TIME)
#	define   SE_MAX_UPDATE_TIME		((int64_t)  0xF48648F0)		/**< 4102441200 = 01.01.2121 */
#endif

#if !defined(SE_MAX_TIME)
#	define   SE_MAX_TIME			((int64_t)  0xFFFFFFFF)
#endif

/**
* Success value for se_getOsStatusOfErrorIO()-function (no execution error detected).
*/
#if !defined(SE_OS_OK)
#	define   SE_OS_OK				((uint32_t)	0)
#endif

#endif  /* SE_DEFINE_H */

/** @}  SE-API  */
