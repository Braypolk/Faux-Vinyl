#include <SPIFFS.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <WebServer.h>
#include <SpotifyArduino.h>
#include "spotify_certificates.h"
#include <ArduinoJson.h>
#include "settings.h"
#include "env.h"

#define NUMITEMS(arg) ((unsigned int) (sizeof (arg) / sizeof (arg [0])))

WebServer server(80);
SpotifyArduino spotify(client, clientId, clientSecret, SPOTIFY_REFRESH_TOKEN);

bool getDeviceCallback(SpotifyDevice device, int index, int numDevices)
{
//  Serial.println("in device callback");
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
void sendInfo(SimpleDevice device, String itemCharArr)
{
//  Serial.println("sending info");

  char itemId[itemCharArr.length() + 1];
  itemCharArr.toCharArray(itemId, itemCharArr.length() + 1);
  // transfer playback if device isn't already active
  if (!device.isActive)
  {
    spotify.transferPlayback(device.id, false); // true means to play after transfer
  }

  char body[100];
  sprintf(body, "{\"context_uri\" : \"%s\"}", itemId);
  spotify.toggleShuffle(true);
  if (spotify.playAdvanced(body))
  {
    server.send(200, "text/html", "<h1>Done</h1><script>window.close()</script>");
  }
  else
  {
    server.send(403, "text/plain", "Something went wrong");
  }
}

void handleTag(String itemCharArr)
{
  numberOfDevices = 0;
  if (spotify.getDevices(getDeviceCallback) != 200)
  {
    server.send(503, "text/plain", "Could not read Spotify devices");
    return;
  }
  for (int i = 0; i < numberOfDevices; i++)
  {
    if (deviceList[i].isActive)
    {
      sendInfo(deviceList[i], itemCharArr);
      return;
    }
  }
  for (int i = 0; i < numberOfDevices; i++)
  {
    if (preferredDevice[0] != '\0' && strcmp(deviceList[i].name, preferredDevice) == 0)
    {
      sendInfo(deviceList[i], itemCharArr);
      return;
    }
  }
  if (numberOfDevices == 1)
  {
    sendInfo(deviceList[0], itemCharArr);
    return;
  }
  server.send(503, "text/plain", "Activate a Spotify device or set preferredDevice in env.h");
}

void randomMusic()
{
  int randNum = random(NUMITEMS(music));
  String itemCharArr = music[randNum];
  handleTag(itemCharArr);
}

void norm()
{
  String itemCharArr = "spotify:" + server.arg(0) + ":" + server.arg(1);
  handleTag(itemCharArr);
}

void runTest()
{
  Serial.println("run test");
  server.send(200, "text/plain", "Server is running");
}

void setup()
{
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
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

  server.on("/", norm);
  server.on("/random", randomMusic);
  server.on("/test", runTest);
  server.begin();
}

void loop()
{
  server.handleClient();
}
