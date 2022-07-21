#include <WiFi.h>
#include <WiFiClient.h>
#include <WebServer.h>
#include <WiFiClientSecure.h>
#include <SpotifyArduino.h>
#include <SpotifyArduinoCert.h>
#include <ArduinoJson.h>
#include "settings.h"

// Country code, including this is advisable
#define SPOTIFY_MARKET "US";

WebServer server(80);
WiFiClientSecure client;

SpotifyArduino spotify(client, clientId, clientSecret, SPOTIFY_REFRESH_TOKEN);

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

bool getDeviceCallback(SpotifyDevice device, int index, int numDevices)
{
  if (index == 0)
  {
    // This is a first device from this batch
    // lets set the number of devices we got back
    if (numDevices < MAX_DEVICES)
    {
      numberOfDevices = numDevices;
    }
    else
    {
      numberOfDevices = MAX_DEVICES;
    }
  }

  // We can't handle anymore than we can fit in our array
  if (index < MAX_DEVICES)
  {
    strncpy(deviceList[index].name, device.name, sizeof(deviceList[index].name)); // DO NOT use deviceList[index].name = device.name, it won't work as you expect!
    deviceList[index].name[sizeof(deviceList[index].name) - 1] = '\0';            // ensures its null terminated

    strncpy(deviceList[index].id, device.id, sizeof(deviceList[index].id));
    deviceList[index].id[sizeof(deviceList[index].id) - 1] = '\0';

    deviceList[index].isActive = device.isActive;

    if (index == MAX_DEVICES - 1)
    {
      return false; // returning false stops it processing any more
    }
    else
    {
      return true;
    }
  }

  // We should never get here
  return false; // returning false stops it processing any more
}

void handleTag()
{
  int status = spotify.getDevices(getDeviceCallback);
  if (status == 200)
  {
    for (int i = 0; i < numberOfDevices; i++)
    {
      SimpleDevice device = deviceList[i];
      if (strcmp(device.name, "Living Room TV") == 0)
      {
        String itemCharArr = "spotify:" + server.arg(0) + ":" + server.arg(1);
        char itemId[itemCharArr.length() + 1];
        itemCharArr.toCharArray(itemId, itemCharArr.length() + 1);
        if (!device.isActive)
        {
          spotify.transferPlayback(device.id, false); // true means to play after transfer
        }
        char body[100];
        sprintf(body, "{\"context_uri\" : \"%s\"}", itemId);
        spotify.toggleShuffle(true);
        if (spotify.playAdvanced(body))
        {
          server.send(200, "text/plain", "Playing " + server.arg(0) + " now");
        }
        else
        {
          server.send(403, "text/plain", "Something went wrong");
        }

        break;
      }
    }
    server.send(200, "text/plain", "Something didn't finish");
  }
}

void setup()
{
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  // Configures static IP address
  if (!WiFi.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS))
  {
    Serial.println("STA Failed to configure");
  }
  WiFi.begin(ssid, password);
  Serial.println("");
  // Wait for connection
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.print("Connected to ");
  Serial.println(ssid);
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
  client.setCACert(spotify_server_cert);
  server.begin();
  // If you want to enable some extra debugging
  // uncomment the "#define SPOTIFY_DEBUG" in SpotifyArduino.h

  Serial.println("Refreshing Access Tokens");
  if (!spotify.refreshAccessToken())
  {
    Serial.println("Failed to get access tokens");
  }

  server.on("/", handleTag);
  Serial.println(WiFi.subnetMask().toString());
  Serial.println(WiFi.gatewayIP().toString());
  Serial.println(WiFi.localIP().toString());
}

void loop()
{
  // WiFiClient client = server.available();   // Listen for incoming clients
  server.handleClient();
}
