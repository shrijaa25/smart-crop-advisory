import 'package:flutter/material.dart';
import '../models/advisory.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';
import '../theme/app_spacing.dart';

class AdvisoryCard extends StatelessWidget {
  final Advisory advisory;
  final VoidCallback? onTap;

  const AdvisoryCard({super.key, required this.advisory, this.onTap});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(AppSpace.radiusCard),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppSpace.radiusCard),
        child: Container(
          padding: const EdgeInsets.all(AppSpace.lg),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppSpace.radiusCard),
            border: Border.all(color: AppColors.border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                Container(
                  width: 36, height: 36,
                  decoration: BoxDecoration(
                    color: advisory.color.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(advisory.icon, color: advisory.color, size: 18),
                ),
                const SizedBox(width: AppSpace.md),
                Expanded(child: Text(advisory.title, style: AppText.label)),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: advisory.color.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    advisory.statusLabel,
                    style: AppText.label
                        .copyWith(color: advisory.color, fontSize: 13),
                  ),
                ),
              ]),
              const SizedBox(height: AppSpace.md),
              Text(advisory.summary, style: AppText.small),
              const SizedBox(height: AppSpace.md),
              Row(children: [
                Text('View Details',
                    style: AppText.label.copyWith(color: AppColors.primary)),
                const SizedBox(width: 4),
                const Icon(Icons.arrow_forward, size: 16, color: AppColors.primary),
              ]),
            ],
          ),
        ),
      ),
    );
  }
}