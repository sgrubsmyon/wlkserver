# library, to be linked with

include_directories(include)
file(GLOB SOURCE "src/*.c")

add_library(se-api-ex-c-lib STATIC ${SOURCE_COMMON} ${SOURCE})

# dynamic library
add_library(se-api-ex-c SHARED ${SOURCE_COMMON} ${SOURCE})

target_compile_definitions(se-api-ex-c PUBLIC SE_EXPORT_EX)

if(WIN32)
	# dynamic library stdcall
	add_library(se-api-ex-c-stdcall SHARED ${SOURCE_COMMON} ${SOURCE})

	target_compile_definitions(se-api-ex-c-stdcall PUBLIC SE_EXPORT_EX SE_STDCALL)
endif()
