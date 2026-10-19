[ -e build ] && echo "please remove old build dir first" && exit 1

set -e

rm -rf bin-dump
CFLAGS=-DDUMP=1 cmake -DCMAKE_BUILD_TYPE=Debug $1 -B build
cmake --build build
mv bin bin-dump

rm -rf build
cmake -DCMAKE_BUILD_TYPE=Debug $1 -B build
cmake --build build

# [ -e se-api-java-native ] && cp bin/libse-msc-io_*.so se-api-java-native/
[ -e se-api-impl/dll-debug ] && cp bin/libse-msc-io_*.so se-api-impl/dll-debug/
[ -e ../SE-API/dll-debug ] && cp bin/libse-msc-io_*.so bin/libse-api-c-jna-wrapper_*.so ../SE-API/dll-debug/

exit 0
