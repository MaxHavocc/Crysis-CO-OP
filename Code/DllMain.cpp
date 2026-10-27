/*************************************************************************
Crytek Source File.
Copyright (C), Crytek Studios, 2001-2007.
-------------------------------------------------------------------------
Description: 	Dll Entry point to capture dll instance handle (needed for loading of embedded resources)

-------------------------------------------------------------------------
History:
- 01:11:2007: Created by Marco Koegler
*************************************************************************/
#include "StdAfx.h"
#if defined(WIN32) && !defined(XENON)
#include <windows.h>
#include <crtdbg.h>

void* g_hInst = 0;

static void CustomInvalidParameterHandler(
	const wchar_t* expression,
	const wchar_t* function,
	const wchar_t* file,
	unsigned int line,
	uintptr_t pReserved)
{
	// Suppress CRT abortion dialog on benign format/parameter discrepancies
	if (gEnv && gEnv->pLog)
	{
		gEnv->pLog->LogWarning("[CRT Intercepted] %ls in %ls (%ls:%u)",
			expression ? expression : L"unknown",
			function ? function : L"unknown",
			file ? file : L"unknown",
			line);
	}
}

BOOL APIENTRY DllMain ( HINSTANCE hInst, DWORD reason, LPVOID reserved )
{
	if ( reason == DLL_PROCESS_ATTACH )
	{
		g_hInst = hInst;
		_set_invalid_parameter_handler(CustomInvalidParameterHandler);
		_CrtSetReportMode(_CRT_ASSERT, 0);
		_CrtSetReportMode(_CRT_ERROR, 0);
	}
	return TRUE;
}
#endif
