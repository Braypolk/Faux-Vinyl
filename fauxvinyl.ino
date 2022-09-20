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
bool reloaded = false;

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
  reloaded = false;
  Serial.println(device.isActive);
  String itemCharArr = "spotify:" + server.arg(0) + ":" + server.arg(1);
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
    int lr = 99;
    int tv = 99;
    for (int i = 0; i < numberOfDevices; i++)
    {
      SimpleDevice device = deviceList[i];

      // if a device is playing, continue playing on that device
      if (device.isActive)
      {
        sendInfo(device);
        return;
      }
      else {
        if (strcmp(device.name, "Living Room") == 0)
        {
          lr = i;
        }
        else if (strcmp(device.name, "Living Room TV") == 0)
        {
          tv = i;
        }
      }
    }

    // play on tv if available, then try the receiver, then try turning on the receiver
    if (tv != 99)
    {
      sendInfo(deviceList[tv]);
    }
    else if (lr != 99){
      sendInfo(deviceList[lr]);
    }
    else
    {
      if (!reloaded)
      {
        reloaded = true;
        server.send(200, "text/html", "<script>const req = new XMLHttpRequest(); req.open('GET', 'http://192.168.0.244/YamahaExtendedControl/v1/main/setPower?power=on', 'false'); req.send(null); const req2 = new XMLHttpRequest(); req2.open('GET', 'http://192.168.0.244/YamahaExtendedControl/v1/main/setInput?input=spotify', 'false'); req2.send(null); setTimeout(() => {location.reload();}, 1000);</script>");
      }
      else
      {
        server.send(200, "text/plain", "Receiver should be on but still isn't picked up. Play manually and it should work again");
      }
    }
    server.send(403, "text/plain", "Something went wrong when choosing a device");
  }
}

void runTest() {
  server.send(200, "text/plain", "Server is running");
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
