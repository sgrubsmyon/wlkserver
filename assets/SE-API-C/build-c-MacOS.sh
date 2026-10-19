[ -e build ] && echo "please remove old build dir first" && exit 1

set -e

export PATH=$PATH:/usr/local/bin

mkdir build
cd build
cmake ..
make
cd ..

[ -e se-api-java-native ] && cp bin/libse-msc-io_*.dylib se-api-java-native/
[ -e se-api-impl/dll ] && cp bin/libse-msc-io_*.dylib se-api-impl/dll/
[ -e ../SE-API/dll ] && cp bin/libse-msc-io_*.dylib bin/libse-api-c-jna-wrapper_*.dylib ../SE-API/dll/
