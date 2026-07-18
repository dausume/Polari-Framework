# Verilated -*- Makefile -*-
# DESCRIPTION: Verilator output: Makefile for building Verilated archive or executable
#
# Execute this makefile from the object directory:
#    make -f Vtop.mk

default: verilated_regblock

### Constants...
# Perl executable (from $PERL, defaults to 'perl' if not set)
PERL = perl
# Python3 executable (from $PYTHON3, defaults to 'python3' if not set)
PYTHON3 = python3
# Path to Verilator kit (from $VERILATOR_ROOT)
VERILATOR_ROOT = /home/user/tools/oss-cad-suite/share/verilator
# SystemC include directory with systemc.h (from $SYSTEMC_INCLUDE)
SYSTEMC_INCLUDE ?=
# SystemC library directory with libsystemc.a (from $SYSTEMC_LIBDIR)
SYSTEMC_LIBDIR ?=

### Switches...
# C++ code coverage  0/1 (from --prof-c)
VM_PROFC = 0
# SystemC output mode?  0/1 (from --sc)
VM_SC = 0
# Legacy or SystemC output mode?  0/1 (from --sc)
VM_SP_OR_SC = $(VM_SC)
# Deprecated
VM_PCLI = 1
# Deprecated: SystemC architecture to find link library path (from $SYSTEMC_ARCH)
VM_SC_TARGET_ARCH = linux

### Vars...
# Design prefix (from --prefix)
VM_PREFIX = Vtop
# Module prefix (from --prefix)
VM_MODPREFIX = Vtop
# User CFLAGS (from -CFLAGS on Verilator command line)
VM_USER_CFLAGS = \
  -fPIC -I/home/user/tools/renode_1.16.1_portable/plugins/IntegrationLibrary -I/home/user/tools/renode_1.16.1_portable/plugins/IntegrationLibrary/src -I/home/user/tools/renode_1.16.1_portable/plugins/IntegrationLibrary/src/communication -I/home/user/tools/renode_1.16.1_portable/plugins/IntegrationLibrary/libs/socket-cpp \

# User LDLIBS (from -LDFLAGS on Verilator command line)
VM_USER_LDLIBS = \

# User .cpp files (from .cpp's on Verilator command line)
VM_USER_CLASSES = \
  Socket \
  TCPClient \
  axilite \
  bus \
  socket_channel \
  renode_bus \
  sim_main \

# User .cpp directories (from .cpp's on Verilator command line)
VM_USER_DIR = \
  .. \
  ../../../../../../../../tools/renode_1.16.1_portable/plugins/IntegrationLibrary/libs/socket-cpp/Socket \
  ../../../../../../../../tools/renode_1.16.1_portable/plugins/IntegrationLibrary/src \
  ../../../../../../../../tools/renode_1.16.1_portable/plugins/IntegrationLibrary/src/buses \
  ../../../../../../../../tools/renode_1.16.1_portable/plugins/IntegrationLibrary/src/communication \

### Default rules...
# Include list of all generated classes
include Vtop_classes.mk
# Include global rules
include $(VERILATOR_ROOT)/include/verilated.mk

### Executable rules... (from --exe)
VPATH += $(VM_USER_DIR)

Socket.o: /home/user/tools/renode_1.16.1_portable/plugins/IntegrationLibrary/libs/socket-cpp/Socket/Socket.cpp 
	$(OBJCACHE) $(CXX) $(CXXFLAGS) $(CPPFLAGS) $(OPT_FAST)  -c -o $@ $<
TCPClient.o: /home/user/tools/renode_1.16.1_portable/plugins/IntegrationLibrary/libs/socket-cpp/Socket/TCPClient.cpp 
	$(OBJCACHE) $(CXX) $(CXXFLAGS) $(CPPFLAGS) $(OPT_FAST)  -c -o $@ $<
axilite.o: /home/user/tools/renode_1.16.1_portable/plugins/IntegrationLibrary/src/buses/axilite.cpp 
	$(OBJCACHE) $(CXX) $(CXXFLAGS) $(CPPFLAGS) $(OPT_FAST)  -c -o $@ $<
bus.o: /home/user/tools/renode_1.16.1_portable/plugins/IntegrationLibrary/src/buses/bus.cpp 
	$(OBJCACHE) $(CXX) $(CXXFLAGS) $(CPPFLAGS) $(OPT_FAST)  -c -o $@ $<
socket_channel.o: /home/user/tools/renode_1.16.1_portable/plugins/IntegrationLibrary/src/communication/socket_channel.cpp 
	$(OBJCACHE) $(CXX) $(CXXFLAGS) $(CPPFLAGS) $(OPT_FAST)  -c -o $@ $<
renode_bus.o: /home/user/tools/renode_1.16.1_portable/plugins/IntegrationLibrary/src/renode_bus.cpp 
	$(OBJCACHE) $(CXX) $(CXXFLAGS) $(CPPFLAGS) $(OPT_FAST)  -c -o $@ $<
sim_main.o: sim_main.cpp 
	$(OBJCACHE) $(CXX) $(CXXFLAGS) $(CPPFLAGS) $(OPT_FAST)  -c -o $@ $<

### Link rules... (from --exe)
verilated_regblock: $(VK_USER_OBJS) $(VK_GLOBAL_OBJS) $(VM_PREFIX)__ALL.a
	$(LINK) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) $(LIBS) $(SC_LIBS) -o $@

# Verilated -*- Makefile -*-
