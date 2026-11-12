#include <WiFiClientSecure.h>

// Country code, including this is advisable
#define SPOTIFY_MARKET "US"

// Network addressing uses DHCP; Wi-Fi credentials belong in local env.h.

unsigned long currentTime = millis();
unsigned long previousTime = 0;
const long timeoutTime = 2000;

struct SimpleDevice
{
    char name[SPOTIFY_DEVICE_NAME_CHAR_LENGTH];
    char id[SPOTIFY_DEVICE_ID_CHAR_LENGTH];
    bool isActive;
};
#define MAX_DEVICES 6
SimpleDevice deviceList[MAX_DEVICES];
int numberOfDevices = -1;

WiFiClientSecure client;