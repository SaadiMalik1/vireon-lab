CXX = g++
CXXFLAGS = -std=c++11 -O2 -Wall -pthread
LDFLAGS = -pthread

TARGET = cpp_firmware_test
SRC = cpp_firmware_test.cpp

all: $(TARGET)

$(TARGET): $(SRC)
	$(CXX) $(CXXFLAGS) $(SRC) -o $(TARGET) $(LDFLAGS)

clean:
	rm -f $(TARGET)
