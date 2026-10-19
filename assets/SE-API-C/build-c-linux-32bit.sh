[ -e build ] && echo "please remove old build dir first" && exit 1

set -e

cmake -DCMAKE_CXX_FLAGS=-m32 -DCMAKE_C_FLAGS=-m32 -B build
cmake --build build

[ -e se-api-java-native ] && cp bin/libse-msc-io_*.so se-api-java-native/
[ -e se-api-impl/dll ] && cp bin/libse-msc-io_*.so se-api-impl/dll/
[ -e ../SE-API/dll ] && cp bin/libse-msc-io_linux-x86-64.so ../SE-API/dll/libse-msc-io_linux-x86.so
[ -e ../SE-API/dll ] && cp bin/libse-api-c-jna-wrapper_linux-x86-64.so ../SE-API/dll/libse-api-c-jna-wrapper_linux-x86.so

exit 0
