[ -e build ] && echo "please remove old build dir first" && exit 1

set -e

cmake -B build
cmake --build build

[ -e se-api-java-native ] && cp bin/libse-msc-io_*.so se-api-java-native/
[ -e se-api-impl/dll ] && cp bin/libse-msc-io_*.so se-api-impl/dll/
[ -e ../SE-API/dll ] && cp bin/libse-msc-io_*.so bin/libse-api-c-jna-wrapper_*.so ../SE-API/dll/

exit 0
