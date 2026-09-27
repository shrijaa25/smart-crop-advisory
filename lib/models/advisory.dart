import 'package:flutter/material.dart';
import '../theme/app_colors.dart';

enum AdvisoryStatus { good, medium, attention, alert }

class Advisory {
  final IconData icon;
  final String title;
  final String summary;
  final AdvisoryStatus status;

  const Advisory({
    required this.icon,
    required this.title,
    required this.summary,
    required this.status,
  });

  Color get color {
    switch (status) {
      case AdvisoryStatus.good:      return AppColors.good;
      case AdvisoryStatus.medium:    return AppColors.warning;
      case AdvisoryStatus.attention: return AppColors.attention;
      case AdvisoryStatus.alert:     return AppColors.danger;
    }
  }

  String get statusLabel {
    switch (status) {
      case AdvisoryStatus.good:      return 'Good';
      case AdvisoryStatus.medium:    return 'Medium';
      case AdvisoryStatus.attention: return 'Attention';
      case AdvisoryStatus.alert:     return 'Alert';
    }
  }
}