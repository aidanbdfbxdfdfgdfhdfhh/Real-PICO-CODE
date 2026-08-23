import asyncio
import gc
import machine
import network

import ota
import wifi

from machine import Pin


PORT = 80
AUTO_UPDATE_SECONDS = 60
BUILD_ID = "dashboard-v6"

led = Pin("LED", Pin.OUT)
blink_enabled = False
manual_led = True
update_running = False
last_update_result = "Not checked since startup"
webrepl_state = "Not started"
led.on()


try:
    import webrepl
    from secrets import WEBREPL_PASSWORD

    webrepl.start(password=WEBREPL_PASSWORD)
    webrepl_state = "Running on port 8266"
    print("WebREPL file management is running on port 8266")
except Exception as error:
    webrepl_state = "Unavailable"
    print("WebREPL could not start:", error)


def _wlan():
    return network.WLAN(network.STA_IF)


def _status_values():
    wlan = _wlan()
    connected = wlan.isconnected()
    ip_address = wlan.ifconfig()[0] if connected else "Not connected"

    try:
        signal = str(wlan.status("rssi")) + " dBm"
    except Exception:
        signal = "Unknown"

    return connected, ip_address, signal


def _page(message=""):
    connected, ip_address, signal = _status_values()
    local_version = ota.get_local_version()
    led_state = "Blinking" if blink_enabled else ("On" if manual_led else "Off")
    wifi_state = "Connected" if connected else "Disconnected"
    update_state = "Checking" if update_running else "Ready"

    message_html = ""
    if message:
        message_html = '<div class="message">{}</div>'.format(message)

    return """<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Pico WH Control</title>
  <style>
    body {{ font-family: sans-serif; background: #10151c; color: #eef3f8;
           max-width: 720px; margin: auto; padding: 18px; }}
    h1 {{ margin-bottom: 4px; }}
    .sub {{ color: #9fb0c0; margin-top: 0; }}
    .card {{ background: #1a2430; border: 1px solid #334355;
            border-radius: 12px; margin: 14px 0; padding: 16px; }}
    .version-card {{ background: #173727; border: 2px solid #55d68b;
                     text-align: center; }}
    .version-number {{ color: #7dffaf; font-size: 42px; font-weight: bold;
                       margin: 6px 0; }}
    .build {{ color: #b9c7d4; font-family: monospace; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .value {{ color: #78dba9; font-weight: bold; }}
    button {{ width: 100%; padding: 13px; border: 0; border-radius: 9px;
             background: #2878d0; color: white; font-size: 16px; }}
    button.stop {{ background: #bc3f4a; }}
    button.warn {{ background: #b97818; }}
    form {{ margin: 0; }}
    .message {{ background: #263d32; border: 1px solid #3b7757;
               border-radius: 9px; padding: 11px; margin-top: 14px; }}
    footer {{ color: #8191a1; font-size: 13px; margin-top: 20px; }}
  </style>
</head>
<body>
  <h1>Pico WH Control</h1>
  <p class="sub">Local management website</p>
  {message}

  <section class="card version-card">
    <div>INSTALLED SOFTWARE</div>
    <div class="version-number">VERSION {version}</div>
    <div class="build">Build: {build_id}</div>
  </section>

  <section class="card">
    <h2>Status</h2>
    <p>Wi-Fi: <span class="value">{wifi_state}</span></p>
    <p>IP: <span class="value">{ip}</span></p>
    <p>Signal: <span class="value">{signal}</span></p>
    <p>LED: <span class="value">{led_state}</span></p>
    <p>Updater: <span class="value">{update_state}</span></p>
    <p>Last check: <span class="value">{last_update}</span></p>
    <p>File management: <span class="value">{webrepl_state}</span></p>
  </section>

  <section class="card">
    <h2>Onboard LED</h2>
    <div class="grid">
      <form method="post" action="/led/on"><button>Turn on</button></form>
      <form method="post" action="/led/off"><button class="stop">Turn off</button></form>
      <form method="post" action="/blink/start"><button>Start blinking</button></form>
      <form method="post" action="/blink/stop"><button class="stop">Stop blinking</button></form>
    </div>
  </section>

  <section class="card">
    <h2>System</h2>
    <div class="grid">
      <form method="post" action="/update"><button>Check for update</button></form>
      <form method="post" action="/standby"><button class="warn">Standby</button></form>
      <form method="post" action="/restart"><button class="stop">Restart Pico</button></form>
      <form method="get" action="/"><button>Refresh status</button></form>
    </div>
  </section>

  <footer>Keep this page on your trusted home network. Standby keeps Wi-Fi on.</footer>
</body>
</html>""".format(
        message=message_html,
        wifi_state=wifi_state,
        ip=ip_address,
        signal=signal,
        version=local_version,
        build_id=BUILD_ID,
        led_state=led_state,
        update_state=update_state,
        last_update=last_update_result,
        webrepl_state=webrepl_state,
    )


async def _send(writer, body, status="200 OK"):
    data = body.encode("utf-8")
    header = (
        "HTTP/1.1 {}\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        "Content-Length: {}\r\n"
        "Connection: close\r\n\r\n"
    ).format(status, len(data))

    writer.write(header.encode("utf-8"))
    writer.write(data)
    await writer.drain()

    writer.close()
    try:
        await writer.wait_closed()
    except Exception:
        pass


async def _restart_later():
    await asyncio.sleep(0.5)
    machine.reset()


async def _check_update_later():
    global last_update_result, update_running

    await asyncio.sleep(0.2)
    update_running = True

    try:
        wlan = _wlan()
        if not wlan.isconnected():
            wlan = wifi.connect()

        if wlan is None or not wlan.isconnected():
            last_update_result = "Failed: Wi-Fi is disconnected"
            return

        local_version = ota.get_local_version()

        try:
            remote_version = ota._download_text(ota.VERSION_URL).strip()
        except Exception as error:
            print("Update check failed:", error)
            last_update_result = "Failed to contact GitHub"
            return

        if not ota._valid_version(remote_version):
            last_update_result = "Failed: GitHub version is invalid"
            return

        if remote_version == local_version:
            last_update_result = "Up to date: version {}".format(local_version)
            return

        last_update_result = "Installing version {}".format(remote_version)
        if not ota.update(remote_version):
            last_update_result = "Failed to install version {}".format(remote_version)
    finally:
        update_running = False
        gc.collect()


async def _handle_request(reader, writer):
    global blink_enabled, manual_led

    try:
        request_line = await reader.readline()
        if not request_line:
            await _send(writer, _page(), "400 Bad Request")
            return

        parts = request_line.decode("utf-8").strip().split()
        if len(parts) != 3:
            await _send(writer, _page(), "400 Bad Request")
            return

        method, path, protocol = parts

        # Read and discard the remaining HTTP headers.
        while True:
            line = await reader.readline()
            if not line or line == b"\r\n":
                break

        message = ""

        if method == "POST" and path == "/led/on":
            blink_enabled = False
            manual_led = True
            led.on()
            message = "LED turned on"
        elif method == "POST" and path == "/led/off":
            blink_enabled = False
            manual_led = False
            led.off()
            message = "LED turned off"
        elif method == "POST" and path == "/blink/start":
            blink_enabled = True
            message = "LED blinking started"
        elif method == "POST" and path == "/blink/stop":
            blink_enabled = False
            manual_led = False
            led.off()
            message = "LED blinking stopped"
        elif method == "POST" and path == "/standby":
            blink_enabled = False
            manual_led = False
            led.off()
            message = "Pico is in standby; management Wi-Fi remains on"
        elif method == "POST" and path == "/update":
            if not update_running:
                asyncio.create_task(_check_update_later())
                message = "Update check started"
            else:
                message = "An update check is already running"
        elif method == "POST" and path == "/restart":
            asyncio.create_task(_restart_later())
            message = "Pico is restarting"
        elif method != "GET" or path != "/":
            await _send(writer, _page("Unknown command"), "404 Not Found")
            return

        await _send(writer, _page(message))
    except Exception as error:
        print("Web request failed:", error)
        try:
            await _send(writer, _page("Request failed"), "500 Internal Server Error")
        except Exception:
            try:
                writer.close()
            except Exception:
                pass


async def _blink_task():
    global manual_led

    while True:
        if blink_enabled:
            led.toggle()
            manual_led = bool(led.value())
            await asyncio.sleep(0.5)
        else:
            await asyncio.sleep(0.1)


async def _automatic_update_task():
    while True:
        await asyncio.sleep(AUTO_UPDATE_SECONDS)
        await _check_update_later()


async def main():
    connected, ip_address, signal = _status_values()
    if not connected:
        raise RuntimeError("WiFi must be connected before starting the website")

    server = await asyncio.start_server(_handle_request, "0.0.0.0", PORT)
    print("Pico management website: http://{}/".format(ip_address))

    asyncio.create_task(_blink_task())
    asyncio.create_task(_automatic_update_task())

    while True:
        await asyncio.sleep(3600)


try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()
