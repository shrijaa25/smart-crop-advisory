class WeatherNow {
  final int tempC;
  final int humidity;
  final int rainChance;
  final int windKmh;
  final String condition;

  const WeatherNow({
    required this.tempC,
    required this.humidity,
    required this.rainChance,
    required this.windKmh,
    required this.condition,
  });
}