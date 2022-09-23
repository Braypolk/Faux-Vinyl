#include <SPIFFS.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <WebServer.h>
#include <SpotifyArduino.h>
#include <SpotifyArduinoCert.h>
#include <ArduinoJson.h>
#include "settings.h"
#include "env.h"

#define NUMITEMS(arg) ((unsigned int) (sizeof (arg) / sizeof (arg [0])))

WebServer server(80);
SpotifyArduino spotify(client, clientId, clientSecret, SPOTIFY_REFRESH_TOKEN);
bool reloaded = false;
String music[] = {"playlist:618LE2v4fI3bSBMjczORn1", "album:59YYObx9wFEFG5zVdlfwvf", "album:2jJReDZqTuAxr4R0ItimZc", "album:30v79AzKU1U5Rc7pwmzbkk", "album:1dVw3jSdgZp7PfGhCEo32t", "album:3REUXdj5OPKhuDTrTtCBU0", "album:7DdEbYFPKTZ8KB4z6L4UnQ", "album:77dNyQA0z8dV33M4so4eRY", "album:6trNtQUgC8cgbWcqoMYkOR", "album:4g1ZRSobMefqF6nelkgibi", "album:11ZOyF9bKgnusVD1rUapwv", "album:1mSECpFqHRW6leG4idqTE1", "album:1LOJfNDxQhbpssKx7oM7at", "album:3lng6RAtdksQ2q02Fk5jaB", "album:4JAvwK4APPArjIsOdGoJXX", "album:3CCnGldVQ90c26aFATC1PW", "album:0UMMIkurRUmkruZ3KGBLtG", "album:4XLPYMERZZaBzkJg0mkdvO", "album:6Fr2rQkZ383FcMqFyT7yPr", "album:1yc3Ldus5BkJBVX9mSFMt4", "album:6mUdeDZCsExyJLMdAfDuwh", "album:4yP0hdKOZPNshxUOjY0cZj", "album:0WzOtZBpXvWdNdH7hCJ4qo", "album:5wtE5aLX5r7jOosmPhJhhk", "album:3mH6qwIy9crq0I9YQbOuDf", "album:7gsWAHLeT0w7es6FofOXk1", "album:0FgZKfoU2Br5sHOfvZKTI9", "album:3BoUxfC7YhxNq3TpOfnRif", "album:6wPXUmYJ9mOWrKlLzZ5cCa", "album:3DGQ1iZ9XKUQxAUWjfC34w", "album:2Y9IRtehByVkegoD7TcLfi", "album:6kf46HbnYCZzP6rjvQHYzg", "album:5bfpRtBW7RNRdsm3tRyl3R", "album:5qENHeCSlwWpEzb25peRmQ", "album:5lKlFlReHOLShQKyRv6AL9", "album:6twKQ0EsUJHVlAr6XBylrj", "album:1HiN2YXZcc3EjmVZ4WjfBk", "album:6s84u2TUpR3wdUv4NgKA2j", "album:4VzzEviJGYUtAeSsJlI9QB", "album:7xV2TzoaVc0ycW7fwBwAml"};

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
void sendInfo(SimpleDevice device, String itemCharArr)
{
  reloaded = false;
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
        sendInfo(device, itemCharArr);
        return;
      }
      else
      {
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
      sendInfo(deviceList[tv], itemCharArr);
    }
    else if (lr != 99)
    {
      sendInfo(deviceList[lr], itemCharArr);
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

void randomMusic()
{
  int randNum = random(NUMITEMS(music));
  String itemCharArr = "spotify:" + music[randNum];
  handleTag(itemCharArr);
}

void norm()
{
  String itemCharArr = "spotify:" + server.arg(0) + ":" + server.arg(1);
  handleTag(itemCharArr);
}

void runTest()
{
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

  server.on("/", norm);
  server.on("/random", randomMusic);
  server.on("/test", runTest);
  server.begin();
}

void loop()
{
  server.handleClient();
}
