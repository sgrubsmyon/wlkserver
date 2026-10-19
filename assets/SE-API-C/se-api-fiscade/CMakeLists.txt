include_directories(../se-api-c/include)
include_directories(../se-api-ex-c/include)
include_directories(.)

add_library(se-api-c-fiscade_${LIBRARY_SUFFIX} SHARED fiscade.c)

# target_compile_options(se-api-c-fiscade_${LIBRARY_SUFFIX} PUBLIC "-ffile-prefix-map=${CMAKE_CURRENT_LIST_DIR}/=/")
target_compile_definitions(se-api-c-fiscade_${LIBRARY_SUFFIX} PUBLIC FISCADE)

target_link_libraries(se-api-c-fiscade_${LIBRARY_SUFFIX} se-api-c-lib)
