#include <SPIFFS.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <WebServer.h>
#include <SpotifyArduino.h>
#include <SpotifyArduinoCert.h>
#include <ArduinoJson.h>
#include "settings.h"
#include "env.h"

WebServer server(80);
SpotifyArduino spotify(client, clientId, clientSecret, SPOTIFY_REFRESH_TOKEN);

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

// From url, make correct commands to play item on device
void sendInfo(SimpleDevice device)
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
    server.send(200, "text/html", "<script>window.close()</script>");
  }
  else
  {
    server.send(403, "text/plain", "Something went wrong");
  }
}

void handleTag()
{
  int status = spotify.getDevices(getDeviceCallback);
  if (status == 200)
  {
    int location = 99;
    for (int i = 0; i < numberOfDevices; i++)
    {
      SimpleDevice device = deviceList[i];
      if (strcmp(device.name, "Living Room") == 0)
      {
        location = i;
      }
      // tv will be default playing location if availible
      if (strcmp(device.name, "Living Room TV") == 0)
      {
        location = 99;
        sendInfo(device);
        break;
      }
    }

    // play on living room if availible and living room tv is not
    if (location != 99)
    {
      sendInfo(deviceList[location]);
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
  // If you want to enable some extra debugging
  // uncomment the "#define SPOTIFY_DEBUG" in SpotifyArduino.h

  Serial.println("Refreshing Access Tokens");
  if (!spotify.refreshAccessToken())
  {
    Serial.println("Failed to get access tokens");
  }

  server.on("/", handleTag);
  server.on("/test", runTest);
  server.begin();
}

void loop()
{
  server.handleClient();
}
