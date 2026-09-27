import 'package:flutter/material.dart';
import '../../models/crop.dart';
import '../../models/weather.dart';
import '../../models/advisory.dart';
import '../../models/task.dart';
import '../../widgets/health_badge.dart';

class MockData {
  // ---- Farmer ----
  static const farmerName = 'Shrijaa';

  // ---- Farms ----
  static const farms = [
    {
      'id': 'f1',
      'name': 'Green Valley Farm',
      'size': 3.5,
      'soil': 'Black Soil',
    },
  ];   // ← only ONE farms block

  // ---- Crops ----
  static const crops = [
    Crop(
      id: 'c1',
      name: 'Tomato',
      emoji: '🍅',
      imageUrl: 'https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=1200',
      dayNumber: 32,
      stage: 'Flowering',
      health: HealthLevel.good,
      healthLabel: 'Good',
      farmName: 'Green Valley Farm',
    ),
    Crop(
      id: 'c2',
      name: 'Chili',
      emoji: '🌶️',
      imageUrl: 'https://images.unsplash.com/photo-1583258292688-d0213dc5a3a8?w=1200',
      dayNumber: 45,
      stage: 'Vegetative',
      health: HealthLevel.attention,
      healthLabel: 'Needs Attention',
      farmName: 'Green Valley Farm',
    ),
    Crop(
      id: 'c3',
      name: 'Spinach',
      emoji: '🥬',
      imageUrl: 'https://images.unsplash.com/photo-1576045057995-568f588f82fb?w=1200',
      dayNumber: 12,
      stage: 'Seedling',
      health: HealthLevel.good,
      healthLabel: 'Good',
      farmName: 'Green Valley Farm',
    ),
  ];

  // ---- Weather ----
  static const weather = WeatherNow(
    tempC: 28,
    humidity: 78,
    rainChance: 65,
    windKmh: 8,
    condition: 'Partly cloudy',
  );

  // ---- Advisory ----
  static const advisories = [
    Advisory(
      icon: Icons.water_drop_outlined,
      title: 'Irrigation',
      summary: 'Rain expected — delay irrigation by a day',
      status: AdvisoryStatus.medium,
    ),
    Advisory(
      icon: Icons.eco_outlined,
      title: 'Nutrient',
      summary: 'Flowering stage — potassium requirement due',
      status: AdvisoryStatus.attention,
    ),
    Advisory(
      icon: Icons.bug_report_outlined,
      title: 'Crop Protection',
      summary: 'Humidity high — watch for leaf spot',
      status: AdvisoryStatus.medium,
    ),
    Advisory(
      icon: Icons.cloud_outlined,
      title: 'Weather Alert',
      summary: 'Rain 65% expected this evening',
      status: AdvisoryStatus.alert,
    ),
  ];

  // ---- Tasks ----
  static List<FarmTask> tasks = [
    FarmTask(title: 'Inspect lower leaves for spots', priority: TaskPriority.high),
    FarmTask(title: 'Review irrigation advisory', priority: TaskPriority.medium),
    FarmTask(title: 'Upload daily crop photo', priority: TaskPriority.routine),
  ];
}