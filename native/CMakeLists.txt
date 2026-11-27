cmake_minimum_required(VERSION 3.22)
project(ReadvancedAndroidAudio LANGUAGES C CXX)
if(NOT ANDROID OR NOT ANDROID_ABI STREQUAL "arm64-v8a")
  message(FATAL_ERROR "This candidate is Android ARM64 only")
endif()
if(NOT IS_DIRECTORY "${SOLOUD_SOURCE}/src/core")
  message(FATAL_ERROR "Provide the pinned official SoLoud checkout")
endif()
set(S "${SOLOUD_SOURCE}/src")
# Lists follow official contrib/src.cmake; keep all C API audio sources, not stubs.
file(GLOB CORE CONFIGURE_DEPENDS "${S}/core/*.cpp")
file(GLOB FILTER CONFIGURE_DEPENDS "${S}/filter/*.cpp")
set(AUDIO
  ay/chipplayer.cpp ay/sndbuffer.cpp ay/sndchip.cpp ay/sndrender.cpp ay/soloud_ay.cpp
  monotone/soloud_monotone.cpp noise/soloud_noise.cpp
  openmpt/soloud_openmpt.cpp openmpt/soloud_openmpt_dll.c
  sfxr/soloud_sfxr.cpp
  speech/darray.cpp speech/klatt.cpp speech/resonator.cpp speech/soloud_speech.cpp speech/tts.cpp
  tedsid/sid.cpp tedsid/soloud_tedsid.cpp tedsid/ted.cpp
  vic/soloud_vic.cpp vizsn/soloud_vizsn.cpp
  wav/dr_impl.cpp wav/soloud_wav.cpp wav/soloud_wavstream.cpp wav/stb_vorbis.c)
list(TRANSFORM AUDIO PREPEND "${S}/audiosource/")
add_library(soloud SHARED ${CORE} ${FILTER} ${AUDIO}
  "${S}/c_api/soloud_c.cpp"
  "${S}/backend/miniaudio/soloud_miniaudio.cpp")
target_include_directories(soloud PRIVATE "${SOLOUD_SOURCE}/include")
target_compile_features(soloud PRIVATE cxx_std_11)
target_compile_definitions(soloud PRIVATE WITH_MINIAUDIO)
target_link_libraries(soloud PRIVATE log android dl m)
target_link_options(soloud PRIVATE "-Wl,--no-undefined" "-Wl,-z,max-page-size=16384")
set_target_properties(soloud PROPERTIES OUTPUT_NAME soloud)
