import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

enum TaskPriority { high, medium, routine }

class FarmTask {
  final String title;
  final TaskPriority priority;
  bool done;

  FarmTask({required this.title, required this.priority, this.done = false});

  Color get color {
    switch (priority) {
      case TaskPriority.high:    return AppColors.danger;
      case TaskPriority.medium:  return AppColors.attention;
      case TaskPriority.routine: return AppColors.primary;
    }
  }

  String get priorityLabel {
    switch (priority) {
      case TaskPriority.high:    return 'HIGH';
      case TaskPriority.medium:  return 'MEDIUM';
      case TaskPriority.routine: return 'ROUTINE';
    }
  }
}