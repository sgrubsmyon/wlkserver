# native test se-api-c-test
include_directories(../se-api-c/include)

add_executable(se-api-c-test se_parse_certificate.c se_api_test.c)
add_executable(export-all se_parse_certificate.c se_api_test.c)
add_executable(export-delete-all se_parse_certificate.c se_api_test.c)
add_executable(tse-test se_parse_certificate.c se_api_test.c)

target_link_libraries(se-api-c-test se-api-c-lib)
target_link_libraries(export-all se-api-c-lib)
target_link_libraries(export-delete-all se-api-c-lib)
target_link_libraries(tse-test se-api-c-lib)

target_compile_definitions(export-all PRIVATE EXPORT_TOOL=1 USE_MEMORY_CALLBACKS=0)
target_compile_definitions(export-delete-all PRIVATE EXPORT_TOOL=1 DO_DELETE=1 USE_MEMORY_CALLBACKS=0)
target_compile_definitions(tse-test PRIVATE TEST_TOOL=1 USE_MEMORY_CALLBACKS=0)
