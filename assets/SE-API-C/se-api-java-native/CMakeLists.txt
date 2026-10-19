# loadable library se-msc-io

include_directories(../se-api-ex-c/include)

file(GLOB SOURCE ../se-api-ex-c/src/*transport_ex.c)

add_library(se-msc-io_${LIBRARY_SUFFIX} SHARED ${SOURCE_COMMON} ${SOURCE})

target_compile_definitions(se-msc-io_${LIBRARY_SUFFIX} PUBLIC JNA_MSC_TRANSPORT)
