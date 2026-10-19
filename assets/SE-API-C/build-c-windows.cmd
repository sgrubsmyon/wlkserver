@echo off
setlocal enabledelayedexpansion

goto main

:build
echo.
echo.
echo ^>^>^>^> Build %1 ^<^<^<^<
echo.
echo.
if not exist %1 (
	mkdir %1
	if not !errorlevel! == 0 (
		goto exit
	)
)
cd %1
cmake -A %1 ../..
cmake --build . --config Debug --parallel
cmake --build . --config Release --parallel
cd ..
if exist ..\se-api-java-native (
	copy ..\bin\%1\Release\se-msc-io*.dll ..\se-api-java-native
)
if exist ..\se-api-impl\dll (
	copy ..\bin\%1\Release\se-msc-io*.dll ..\se-api-impl\dll
)
goto:eof

:main
if exist bin (
	rmdir /s /q bin 2>nul
	if not !errorlevel! == 0 (
		goto main
	)
)
if exist build (
	rmdir /s /q build 2>nul
	if not !errorlevel! == 0 (
		goto main
	)
)

mkdir build
cd build

call :build Win32
call :build x64

cd ..

:exit