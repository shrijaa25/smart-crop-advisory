import 'package:flutter/material.dart';
import '../models/crop.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';
import '../theme/app_spacing.dart';
import 'health_badge.dart';

class CropCard extends StatelessWidget {
  final Crop crop;
  final VoidCallback? onTap;

  const CropCard({super.key, required this.crop, this.onTap});

  @override
  Widget build(BuildContext context) {
    return Material(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(AppSpace.radiusCard),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(AppSpace.radiusCard),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(AppSpace.radiusCard),
            border: Border.all(color: AppColors.border),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ---- Image ----
              ClipRRect(
                borderRadius: const BorderRadius.vertical(
                  top: Radius.circular(AppSpace.radiusCard),
                ),
                child: Image.network(
                  crop.imageUrl,
                  height: 150,
                  width: double.infinity,
                  fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Container(
                    height: 150,
                    color: AppColors.primaryLight,
                    child: const Center(
                      child: Icon(Icons.image_not_supported_outlined,
                          size: 36, color: AppColors.primary),
                    ),
                  ),
                ),
              ),

              // ---- Info ----
              Padding(
                padding: const EdgeInsets.all(AppSpace.lg),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Text(crop.emoji, style: const TextStyle(fontSize: 20)),
                      const SizedBox(width: 8),
                      Expanded(child: Text(crop.name, style: AppText.h3)),
                    ]),
                    const SizedBox(height: 4),
                    Text(crop.farmName, style: AppText.small),
                    const SizedBox(height: AppSpace.md),
                    Text('Day ${crop.dayNumber} • ${crop.stage}',
                        style: AppText.bodyMuted),
                    const SizedBox(height: AppSpace.md),
                    HealthBadge(
                      level: crop.health,
                      label: crop.healthLabel,
                      compact: true,
                    ),
                    const SizedBox(height: AppSpace.lg),
                    SizedBox(
                      width: double.infinity,
                      child: OutlinedButton.icon(
                        onPressed: onTap,
                        icon: const Icon(Icons.arrow_forward, size: 16),
                        label: const Text('View Crop'),
                        style: OutlinedButton.styleFrom(
                          foregroundColor: AppColors.primary,
                          side: const BorderSide(color: AppColors.border),
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          shape: RoundedRectangleBorder(
                            borderRadius:
                                BorderRadius.circular(AppSpace.radiusBtn),
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}