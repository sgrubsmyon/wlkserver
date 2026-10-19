if(WIN32)
	cmake_minimum_required(VERSION 3.15)
	# MSVC runtime library flags are selected by an abstraction.
	cmake_policy(SET CMP0091 NEW)

else()
	cmake_minimum_required(VERSION 3.0.2)
	if(CMAKE_VERSION VERSION_GREATER  "3.3.1")
		# Honor visibility properties for all target types.
		cmake_policy(SET CMP0063 OLD)
	endif()

endif()

project(se-api-c)

file(GLOB SOURCE_COMMON "se-api-common/src/*.c")
include_directories(se-api-common/include)

if(WIN32)
	set(OUTPUT_PATH ${PROJECT_BINARY_DIR}/../../bin/${CMAKE_GENERATOR_PLATFORM})
	
	# link to static msvsc runtime
	set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")

	add_definitions(-D_CRT_SECURE_NO_WARNINGS)

	# library name extension
	if(${CMAKE_GENERATOR_PLATFORM} STREQUAL "Win32")
		set(LIBRARY_SUFFIX "win32-x86")
	elseif(${CMAKE_GENERATOR_PLATFORM} STREQUAL "x64")
		set(LIBRARY_SUFFIX "win32-x86-64")
	else()
		set(LIBRARY_SUFFIX ${CMAKE_SYSTEM_NAME})
	endif()

elseif(${CMAKE_SYSTEM_NAME} STREQUAL "Linux")
	set(OUTPUT_PATH ${PROJECT_BINARY_DIR}/../bin)

	# -fvisibility=hidden
	set(CMAKE_C_VISIBILITY_PRESET hidden)
	set(CMAKE_VISIBILITY_INLINES_HIDDEN 1)
	
	# additional compiler options
	add_compile_options(-fPIC)

	# library name extension
	string(REPLACE "_" "-" LIBRARY_SUFFIX linux-${CMAKE_HOST_SYSTEM_PROCESSOR})

	# set C Standard to C99
	if(CMAKE_VERSION VERSION_LESS "3.1")
		if(CMAKE_COMPILER_IS_GNUCC)
			# add_compile_options(-std=gnu99)
			set (CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=gnu++11")
			set (CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -std=gnu99")
			# can check C90 compatibility:
			# set (CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -std=c90 -pedantic -Wall")
		endif()
	else()
		# can check C90 compatibility:
		# set (CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -std=c90 -pedantic -Wall")
		set(CMAKE_C_STANDARD 99)
	endif()

elseif(${CMAKE_SYSTEM_NAME} STREQUAL "Darwin")
	message("Platform " ${CMAKE_SYSTEM_NAME} " " ${CMAKE_HOST_SYSTEM_VERSION})
	set(OUTPUT_PATH ${PROJECT_BINARY_DIR}/../bin)
	set(LIBRARY_SUFFIX "darwin")
	if(CMAKE_HOST_SYSTEM_VERSION VERSION_LESS 20)
		message(STATUS "Legacy build system: Build only for x86_64")
		set(CMAKE_OSX_ARCHITECTURES "x86_64")
		set(CMAKE_OSX_DEPLOYMENT_TARGET "10.12")
	else()
		message(STATUS "macOS 11+ build system: universel x64/arm build")
		set(CMAKE_OSX_ARCHITECTURES "arm64;x86_64")
	endif()
else()
	message(FATAL_ERROR "Platform " ${CMAKE_SYSTEM_NAME} " not supported")

endif()

# strip full source path from debug builds:
# -DCMAKE_C_FLAGS="-ffile-prefix-map=$(pwd)/=./"
# add_compile_options("-ffile-prefix-map=${CMAKE_CURRENT_LIST_DIR}/=./")

set(LIBRARY_OUTPUT_PATH ${OUTPUT_PATH})
set(EXECUTABLE_OUTPUT_PATH ${OUTPUT_PATH})

add_subdirectory(se-api-c)
add_subdirectory(se-api-c-test)

if(NOT (${CMAKE_SYSTEM_NAME} STREQUAL "Linux" OR ${CMAKE_SYSTEM_NAME} STREQUAL "Darwin") AND NOT CMAKE_VERSION VERSION_LESS "3.1")
	if(IS_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/se-api-cpp")
		add_subdirectory(se-api-cpp)
	endif()
	if(IS_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/se-api-cpp-test")
		add_subdirectory(se-api-cpp-test)
	endif()
endif()

add_subdirectory(se-api-ex-c)
add_subdirectory(se-api-ex-c-test)

add_subdirectory(se-api-java-native)

if(IS_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/se-api-c-jna-wrapper")
  add_subdirectory(se-api-c-jna-wrapper)
endif()
if(IS_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/se-api-fiscade")
  add_subdirectory(se-api-fiscade)
endif()
if(IS_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/se-api-fiscade-test")
  add_subdirectory(se-api-fiscade-test)
endif()
