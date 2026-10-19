/*
 * Copyright (c) 2019-2021
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
  * @file se_memory_util.c
  *
  * @brief Memmory management utilities for the cryptovision SE-API and _extended_ SE_API.
  *
  * @addtogroup   SE-API-common
  */

#include <stdlib.h>

#include <se_memory_util.h>

/* ------------------------------------------------------------------------- */
/* Local definitions                                                         */
/* ------------------------------------------------------------------------- */

static void* SE_STDCALL		m_malloc(size_t size)	{ return malloc(size);	}
static void  SE_STDCALL		m_free(void* memBlock)	{ free(memBlock);		}

static se_malloc_t			m_malloc_func			= m_malloc;
static se_free_t			m_free_func				= m_free;


/* ------------------------------------------------------------------------- */
/* se_memory_util.h functions                                                */
/* ------------------------------------------------------------------------- */

/* ------------------------------------------------------------------------- */
SE_API_COMMON_IMPL(void*, se_malloc)(size_t size)
{
    SE_EXPORT_COMMON_METHOD;

	return m_malloc_func(size);
}

/* ------------------------------------------------------------------------- */
SE_API_COMMON_IMPL(void, se_free)(void* memBlock)
{
	SE_EXPORT_COMMON_METHOD;

	m_free_func(memBlock);
}

/* ------------------------------------------------------------------------- */
SE_API_COMMON_IMPL(se_result_t, se_setAllocator)(se_malloc_t _malloc, se_free_t _free)
{
    SE_EXPORT_COMMON_METHOD;

	/* required both != NULL or both == NULL */
	if(_malloc != NULL && _free != NULL)
	{
		m_malloc_func = _malloc;
		m_free_func   = _free;
	}
	else if(_malloc == NULL && _free == NULL)
	{
		m_malloc_func = m_malloc;
		m_free_func   = m_free;
	}
	else
		return ErrorMissingParameter;

	return ExecutionOk;
}
