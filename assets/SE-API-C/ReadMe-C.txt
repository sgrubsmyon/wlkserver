
Windows
- Tested on Windows 10 64 Bit using Visual Studio 2015 and 2017
- Install CMake (3.15 or higher), select "path-option"

1. open visual studio command prompt
2. run build-c-windows.cmd
3. find the output in the new bin folder

Linux
- Tested on Ubuntu-18.04 (LTS) 64 Bit using GCC7
- Install build-essentials and cmake (3.0.2 or higher)

1. add execute rights to build-c-linux.sh using "chmod a+x build-c-linux.sh"
2. run ./build-c-linux.sh
3. find the output in the new bin folder

Note:
- The SE-API java native library will be copied by the build-script to se-api-java-native.
- On success the folder contains for example
  - libse-msc-io_linux-x86-64.so
  - se-msc-io_win32-x86-64.dll
  - se-msc-io_win32-x86.dll
