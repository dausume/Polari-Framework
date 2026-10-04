# The ESP32-C3 template's top-level CMake file (sc-3). ESP-IDF REQUIRES CMake as its build system; the firmware itself is
# C only (RULE 2). Rendered into a project by `pol board gen c3 --variant …`; built by `pol board build c3` through the
# prf-esp-engines worker (ESP-IDF v5.5.5, FreeRTOS inside).
cmake_minimum_required(VERSION 3.16)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
# the FreeRTOS trace hooks: main/polari_trace.h is force-included into EVERY C file of the build (the kernel included),
# so the kernel's own empty trace macros never apply (C files only — never the assembler sources)
idf_build_set_property(COMPILE_OPTIONS "$<$<COMPILE_LANGUAGE:C>:-include;${CMAKE_CURRENT_LIST_DIR}/main/polari_trace.h>" APPEND)
project(polari_c3)
