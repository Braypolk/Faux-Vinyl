#include <WiFiClientSecure.h>

// Country code, including this is advisable
#define SPOTIFY_MARKET "US";

// WiFi settings
const char ssid[] = "";
const char password[] = "";

// Spotify settings
const char clientId[] = "";
const char clientSecret[] = "";
const char SPOTIFY_REFRESH_TOKEN[] = "";


IPAddress local_IP(192, 168, 0, 218);
IPAddress gateway(192, 168, 0, 1);
IPAddress subnet(255, 255, 255, 0);
IPAddress primaryDNS(8, 8, 8, 8);   // optional
IPAddress secondaryDNS(8, 8, 4, 4); // optional

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