# native test se-api-c-test
include_directories(../se-api-ex-c/include)

add_executable(se-api-ex-c-test se_api_ex_test.c)

target_link_libraries(se-api-ex-c-test se-api-ex-c-lib)
