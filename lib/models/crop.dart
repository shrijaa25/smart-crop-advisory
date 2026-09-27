import '../widgets/health_badge.dart';

class Crop {
  final String id;
  final String name;
  final String emoji;
  final String imageUrl;
  final int dayNumber;
  final String stage;
  final HealthLevel health;
  final String healthLabel;
  final String farmName;   // ← NEW

  const Crop({
    required this.id,
    required this.name,
    required this.emoji,
    required this.imageUrl,
    required this.dayNumber,
    required this.stage,
    required this.health,
    required this.healthLabel,
    required this.farmName, // ← NEW
  });
}