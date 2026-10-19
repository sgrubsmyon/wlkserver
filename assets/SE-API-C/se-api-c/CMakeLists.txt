# library, to be linked with

include_directories(include)
include_directories(../se-api-ex-c/include)

file(GLOB SOURCE "src/*.c" "../se-api-ex-c/src/*.c")

add_library(se-api-c-lib STATIC ${SOURCE_COMMON} ${SOURCE})

# dynamic library
add_library(se-api-c SHARED ${SOURCE_COMMON} ${SOURCE})

target_compile_definitions(se-api-c PUBLIC SE_EXPORT)

if(WIN32)
	# dynamic library stdcall
	add_library(se-api-c-stdcall SHARED ${SOURCE_COMMON} ${SOURCE})

	target_compile_definitions(se-api-c-stdcall PUBLIC SE_EXPORT SE_STDCALL)
endif()
