const int photoSensorPin = A0;
int photoSensorValue = 0; 

void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);
}

void loop() {
  // put your main code here, to run repeatedly:
  photoSensorValue = analogRead(photoSensorPin);
  delay(1000);
  Serial.print("Raw sensor value: ");
  Serial.println(photoSensorValue);
}
