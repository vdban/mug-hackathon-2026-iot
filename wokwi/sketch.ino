/*
 * Frutiger Aqua Smart Aquarium - ESP32 Wokwi Hardware Simulator
 * MongoDB User Group Vietnam Hackathon 2026 (MongoDB x Datadog)
 *
 * Kết nối trực tiếp tới FastAPI Backend -> MongoDB Time Series + Datadog + Firebase
 * Trên Wokwi VS Code (với wokwi.toml), host.wokwi.internal:8000 trỏ tới localhost:8000.
 * Nếu chạy trên Wokwi Web, thay BACKEND_BASE_URL bằng URL ngrok/Cloudflare Tunnel của bạn.
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <OneWire.h>
#include <DallasTemperature.h>

#define WIFI_SSID "Wokwi-GUEST"
#define WIFI_PASS ""
#define BACKEND_BASE_URL "http://host.wokwi.internal:8000"

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// Pin definitions matching diagram.json
const int PIN_TEMP_DQ   = 4;
const int PIN_TRIG      = 5;
const int PIN_ECHO      = 18;
const int PIN_SW_FAULT  = 19;
const int PIN_POT_PH    = 34;
const int PIN_POT_EC    = 35;
const int PIN_LED_PUMP  = 25;
const int PIN_LED_FLUSH = 26;
const int PIN_LED_ALARM = 27;
const int PIN_BUZZER    = 14;

OneWire oneWire(PIN_TEMP_DQ);
DallasTemperature tempSensors(&oneWire);

bool remoteFaultActive = false;
bool remoteBubblerOn = true;
unsigned long lastTick = 0;

float readWaterLevelPct() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  long duration = pulseIn(PIN_ECHO, HIGH, 25000);
  if (duration == 0) return 88.0;
  float distCm = duration * 0.0343f / 2.0f;
  // Khoảng cách cảm biến tới mặt nước: 4 cm = 98%, 40 cm = 15%
  float pct = 100.0f - ((distCm - 4.0f) * (85.0f / 36.0f));
  if (pct < 10.0f) pct = 10.0f;
  if (pct > 100.0f) pct = 100.0f;
  return pct;
}

void pollSerialBridge() {
  while (Serial.available() > 0) {
    String line = Serial.readStringUntil('\n');
    int idx = line.indexOf("CMD:");
    if (idx >= 0) {
      bool changed = false;
      bool newFault = (line.indexOf("FAULT=1", idx) >= 0);
      if (newFault != remoteFaultActive) {
        remoteFaultActive = newFault;
        changed = true;
        Serial.println(remoteFaultActive
          ? ">>> [LỆNH TỪ WEB] Đã KÍCH HOẠT sự cố giả lập (Kẹt lọc & Tăng pH)!"
          : ">>> [LỆNH TỪ WEB] Đã KHẮC PHỤC sự cố (Xả ngược lọc & Cân bằng pH)!");
      }
      if (line.indexOf("BUBBLER=1", idx) >= 0 && !remoteBubblerOn) {
        remoteBubblerOn = true;
        changed = true;
        Serial.println(">>> [LỆNH TỪ WEB] Máy sục khí Oxy: BẬT");
      } else if (line.indexOf("BUBBLER=0", idx) >= 0 && remoteBubblerOn) {
        remoteBubblerOn = false;
        changed = true;
        Serial.println(">>> [LỆNH TỪ WEB] Máy sục khí Oxy: TẮT");
      }
      if (changed) {
        digitalWrite(PIN_LED_FLUSH, remoteBubblerOn ? HIGH : LOW);
        lastTick = 0;
      }
    }
  }
}

void pollRemoteControlState() {
  if (WiFi.status() != WL_CONNECTED) return;
  HTTPClient http;
  http.begin(String(BACKEND_BASE_URL) + "/api/simulator/state");
  http.setTimeout(1500);
  int code = http.GET();
  if (code == 200) {
    String body = http.getString();
    StaticJsonDocument<512> doc;
    if (deserializeJson(doc, body) == DeserializationError::Ok) {
      const char* f = doc["faults"]["AQUA-TANK-01"];
      remoteFaultActive = (f != nullptr && strlen(f) > 0);
      if (doc["actuators"].containsKey("bubbler_on")) {
        remoteBubblerOn = doc["actuators"]["bubbler_on"];
      }
    }
  }
  http.end();
}

void setup() {
  Serial.begin(115200);
  Serial.setTimeout(30);
  Serial.println("\n=========================================================");
  Serial.println("  HE THONG BE CA THONG MINH FRUTIGER AQUA (AQUA-TANK-01)");
  Serial.println("=========================================================");
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  pinMode(PIN_SW_FAULT, INPUT);
  pinMode(PIN_LED_PUMP, OUTPUT);
  pinMode(PIN_LED_FLUSH, OUTPUT);
  pinMode(PIN_LED_ALARM, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);

  tempSensors.begin();

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("SSD1306 allocation failed");
  } else {
    display.clearDisplay();
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 0);
    display.println("FRUTIGER AQUA ESP32");
    display.println("Connecting WiFi...");
    display.display();
  }

  WiFi.begin(WIFI_SSID, WIFI_PASS);
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < 6) {
    delay(250);
    Serial.print(".");
    retries++;
  }
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected! IP: " + WiFi.localIP().toString());
  } else {
    Serial.println("\nWiFi offline -> Serial Bridge mode ready (RFC2217 port 4000).");
  }
}

void loop() {
  pollSerialBridge();
  if (millis() - lastTick < 2000) return;
  lastTick = millis();

  pollRemoteControlState();

  bool hwFaultSwitch = (digitalRead(PIN_SW_FAULT) == HIGH);
  bool faultActive = hwFaultSwitch || remoteFaultActive;

  tempSensors.requestTemperatures();
  float waterTemp = tempSensors.getTempCByIndex(0);
  if (waterTemp <= -100.0f) waterTemp = 24.5f;

  float waterLevelPct = readWaterLevelPct();
  int rawPh = analogRead(PIN_POT_PH);
  int rawEc = analogRead(PIN_POT_EC);

  float ph = 5.0f + (rawPh / 4095.0f) * 3.5f;
  float ec = 400.0f + (rawEc / 4095.0f) * 1000.0f;
  float pumpFlow = 4.5f;

  if (faultActive) {
    pumpFlow = 0.35f;
    ph = max(ph, 8.15f);
    if (waterLevelPct > 30.0f) waterLevelPct = 28.0f;
  }

  bool isCritical = (pumpFlow < 1.0f || ph > 7.6f || ph < 5.0f);

  digitalWrite(PIN_LED_PUMP, !isCritical ? HIGH : LOW);
  digitalWrite(PIN_LED_FLUSH, remoteBubblerOn ? HIGH : LOW);
  digitalWrite(PIN_LED_ALARM, isCritical ? HIGH : LOW);
  if (isCritical) {
    tone(PIN_BUZZER, 1200, 200);
  } else {
    noTone(PIN_BUZZER);
  }

  // Update Frutiger Aqua HUD on SSD1306 OLED
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("FRUTIGER AQUA TANK-01");
  display.println("---------------------");
  display.printf("Flow : %.2f LPM\n", pumpFlow);
  display.printf("pH   : %.2f\n", ph);
  display.printf("Temp : %.1f C | Lvl:%d%%\n", waterTemp, (int)waterLevelPct);
  display.printf("EC   : %d ppm\n", (int)ec);
  display.println(isCritical ? "STATUS: [CLOG ALERT!]" : "STATUS: [OPTIMAL]");
  display.display();

  // Print clean Vietnamese telemetry over Serial (parsed by Wokwi RFC2217 Bridge -> Backend -> MongoDB + Datadog)
  Serial.printf(
    "[BỂ CÁ TANK-01] Trạng thái: %s | pH: %.2f | TDS: %.0f ppm | Nhiệt độ: %.1f °C | Mực nước: %.1f%% | Lưu lượng lọc: %.2f L/phút | Sục Oxy: %s\n",
    isCritical ? "CẢNH BÁO KẸT LỌC!" : "BÌNH THƯỜNG",
    ph,
    ec,
    waterTemp,
    waterLevelPct,
    pumpFlow,
    remoteBubblerOn ? "BẬT" : "TẮT"
  );

  // Send Telemetry Batch to FastAPI -> MongoDB Time Series + Datadog
  if (WiFi.status() == WL_CONNECTED) {
    StaticJsonDocument<512> batchDoc;
    JsonArray readings = batchDoc.createNestedArray("readings");
    JsonObject r = readings.createNestedObject();
    JsonObject sensor = r.createNestedObject("sensor");
    sensor["id"] = "AQUA-TANK-01";
    sensor["zone"] = "Living Room 1F";
    sensor["crop"] = "Neon Tetra & Guppy";
    sensor["system_type"] = "Canister Bio-Filter";

    r["ph"] = roundf(ph * 100.0f) / 100.0f;
    r["ec_ppm"] = roundf(ec);
    r["water_temp"] = roundf(waterTemp * 10.0f) / 10.0f;
    r["water_level_pct"] = roundf(waterLevelPct * 10.0f) / 10.0f;
    r["pump_flow_lpm"] = pumpFlow;

    String jsonPayload;
    serializeJson(batchDoc, jsonPayload);

    HTTPClient http;
    http.begin(String(BACKEND_BASE_URL) + "/api/telemetry/ingest");
    http.addHeader("Content-Type", "application/json");
    int httpCode = http.POST(jsonPayload);
    Serial.printf("[ESP32] POST /api/telemetry/ingest -> HTTP %d | Flow=%.2f pH=%.2f\n", httpCode, pumpFlow, ph);
    http.end();
  }
}
