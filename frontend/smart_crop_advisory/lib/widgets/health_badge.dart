import 'package:flutter/material.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';

enum HealthLevel { good, warning, attention, danger }

class HealthBadge extends StatelessWidget {
  final HealthLevel level;
  final String label;
  final bool compact;

  const HealthBadge({
    super.key,
    required this.level,
    required this.label,
    this.compact = false,
  });

  Color get _color {
    switch (level) {
      case HealthLevel.good:      return AppColors.good;
      case HealthLevel.warning:   return AppColors.warning;
      case HealthLevel.attention: return AppColors.attention;
      case HealthLevel.danger:    return AppColors.danger;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? 10 : 12,
        vertical: compact ? 4 : 6,
      ),
      decoration: BoxDecoration(
        color: _color.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8, height: 8,
            decoration: BoxDecoration(color: _color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 8),
          Text(
            label,
            style: AppText.label.copyWith(color: _color, fontSize: compact ? 13 : 15),
          ),
        ],
      ),
    );
  }
}